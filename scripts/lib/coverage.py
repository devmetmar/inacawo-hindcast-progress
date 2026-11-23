"""Day-level inventory coverage for the dashboard (not scientific acceptance)."""

from __future__ import annotations

import calendar
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .catalog import POSTPROCESSED_PRODUCTS

_STATE_CHAR = {
    "PRESENT": "P",
    "MISSING": "M",
    "OUT_OF_SPAN": "O",
    "PARTIAL": "A",
}
_CHAR_STATE = {v: k for k, v in _STATE_CHAR.items()}


def _ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def days_in_year(year: int) -> list[str]:
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    out: list[str] = []
    cur = start
    while cur <= end:
        out.append(_ymd(cur))
        cur += timedelta(days=1)
    return out


def load_day_presence(root: Path, year: int) -> dict[str, Any] | None:
    path = root / "data" / "manifests" / f"day_presence_{year}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_inventory_scan(root: Path) -> dict[str, Any] | None:
    manifests = root / "data" / "manifests"
    if not manifests.is_dir():
        return None
    scans = sorted(manifests.glob("inventory_scan_*.json"))
    if not scans:
        return None
    return json.loads(scans[-1].read_text(encoding="utf-8"))


def catalog_years_from_matrices(
    historical_matrix: list[dict], remaining_matrix: list[dict]
) -> list[int]:
    years = {int(r["year"]) for r in historical_matrix}
    years |= {int(r["year"]) for r in remaining_matrix}
    return sorted(years)


def _contiguous_days(first: str, count: int) -> list[str]:
    if count <= 0:
        return []
    y, m, d = int(first[0:4]), int(first[4:6]), int(first[6:8])
    cur = date(y, m, d)
    out: list[str] = []
    for _ in range(count):
        out.append(_ymd(cur))
        cur += timedelta(days=1)
    return out


def _days_from_span_and_count(
    year: int, span: list[str] | None, count: int
) -> list[str]:
    """Infer present YYYYMMDD lists from inventory year counts + span."""
    expected = days_in_year(year)
    if count <= 0:
        return []
    if count >= len(expected):
        return expected

    year_start, year_end = expected[0], expected[-1]
    if span and len(span) >= 2:
        first = max(span[0], year_start)
        last = min(span[1], year_end)
        if first > last:
            return []
        # Contiguous span matching count (typical partial edge years)
        span_days = _contiguous_days(
            first,
            (
                date(int(last[0:4]), int(last[4:6]), int(last[6:8]))
                - date(int(first[0:4]), int(first[4:6]), int(first[6:8]))
            ).days
            + 1,
        )
        if len(span_days) == count:
            return span_days
        # Prefer start-of-span within year for partial counts
        return _contiguous_days(first, count)[:count]

    return expected[:count]


def _merge_day_lists(*lists: list[str]) -> list[str]:
    """Union YYYYMMDD lists, sorted."""
    merged: set[str] = set()
    for lst in lists:
        merged.update(lst or [])
    return sorted(merged)


def normalize_presence_to_catalog_products(
    presence: dict[str, Any],
) -> dict[str, Any]:
    """Fold disk-only folder keys into catalog products (ocean2d/3d, wrf2d/3d).

    CLS stores ocean2d across ``ocean2d`` + ``ocean2d_with_tm01`` trees; the
    daily table must expose a single ``ocean2d`` product like the catalog.
    """
    out = dict(presence)
    streams_in = presence.get("streams") or {}
    aliases = presence.get("product_aliases") or {}
    streams_out: dict[str, dict[str, list[str]]] = {}

    for stream, block in streams_in.items():
        block = dict(block or {})
        stream_aliases = aliases.get(stream) or {}
        # Apply aliases into canonical keys first (e.g. ocean2d → ocean2d_with_tm01 days)
        for catalog_product, disk_key in stream_aliases.items():
            if disk_key in block and catalog_product != disk_key:
                block[catalog_product] = _merge_day_lists(
                    list(block.get(catalog_product) or []),
                    list(block.get(disk_key) or []),
                )
        # Always merge CLS ocean2d folder split into catalog ocean2d
        if "ocean2d_with_tm01" in block:
            block["ocean2d"] = _merge_day_lists(
                list(block.get("ocean2d") or []),
                list(block.get("ocean2d_with_tm01") or []),
            )
            del block["ocean2d_with_tm01"]
        # Keep only primary catalog products
        streams_out[stream] = {
            p: list(block.get(p) or []) for p in POSTPROCESSED_PRODUCTS
        }

    out["streams"] = streams_out
    out["product_aliases"] = {}
    return out


def synthesize_presence_from_inventory(
    inventory: dict[str, Any], year: int
) -> dict[str, Any]:
    """Build a day_presence-like dict for one year from inventory_scan year counts."""
    cls_streams: dict[str, list[str]] = {}
    # Disk folders may include ocean2d_with_tm01; fold into catalog ocean2d below.
    for product in ("ocean2d", "ocean2d_with_tm01", "ocean3d", "wrf2d", "wrf3d"):
        block = inventory.get(product) or {}
        years = block.get("years") or {}
        count = int(years.get(str(year), years.get(year, 0)) or 0)
        span = block.get("span")
        cls_streams[product] = _days_from_span_and_count(year, span, count)

    # Single catalog ocean2d = legacy tree ∪ with_tm01 continuation
    cls_streams["ocean2d"] = _merge_day_lists(
        cls_streams.get("ocean2d") or [],
        cls_streams.pop("ocean2d_with_tm01", []),
    )

    internal_streams: dict[str, list[str]] = {}
    internal = inventory.get("internal_cawo_post") or {}
    for product in POSTPROCESSED_PRODUCTS:
        block = internal.get(product) or {}
        years = block.get("years") or {}
        count = int(years.get(str(year), years.get(year, 0)) or 0)
        span = block.get("span")
        internal_streams[product] = _days_from_span_and_count(year, span, count)

    raw = {
        "scan_date": inventory.get("scan_date"),
        "basis": "directory_names",
        "source_inventory": "inventory_scan",
        "year": year,
        "synthesized": True,
        "streams": {
            "cls_brazil": cls_streams,
            "internal": internal_streams,
        },
        "product_aliases": {},
    }
    return normalize_presence_to_catalog_products(raw)


def resolve_day_presence(
    root: Path, year: int, inventory: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Prefer explicit day_presence_YYYY.json; else synthesize from inventory scan."""
    explicit = load_day_presence(root, year)
    if explicit is not None:
        return normalize_presence_to_catalog_products(explicit)
    inv = inventory if inventory is not None else load_inventory_scan(root)
    if inv is None:
        return None
    return synthesize_presence_from_inventory(inv, year)


def _present_set(
    presence: dict[str, Any] | None, stream: str, product: str
) -> set[str] | None:
    if not presence:
        return None
    streams = presence.get("streams") or {}
    stream_block = streams.get(stream) or {}
    if product not in stream_block:
        return set()
    return set(stream_block.get(product) or [])


def build_year_day_coverage(
    root: Path,
    year: int,
    *,
    products: tuple[str, ...] | list[str] = POSTPROCESSED_PRODUCTS,
    default_stream: str = "cls_brazil",
    presence: dict[str, Any] | None = None,
    inventory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build inventory day coverage for one calendar year.

    States per day/product: PRESENT | MISSING | OUT_OF_SPAN | PARTIAL (all-required only).
    """
    del default_stream  # API compat
    if presence is None:
        presence = resolve_day_presence(root, year, inventory=inventory)
    expected = days_in_year(year)
    expected_set = set(expected)
    products = list(products)

    by_stream: dict[str, Any] = {}
    for stream in ("cls_brazil", "internal"):
        product_blocks: dict[str, Any] = {}
        for product in products:
            present = _present_set(presence, stream, product)
            if present is None:
                days = [
                    {
                        "date": d,
                        "iso": f"{d[0:4]}-{d[4:6]}-{d[6:8]}",
                        "month": int(d[4:6]),
                        "day": int(d[6:8]),
                        "state": "OUT_OF_SPAN",
                    }
                    for d in expected
                ]
                product_blocks[product] = {
                    "present_count": 0,
                    "missing_count": 0,
                    "out_count": len(expected),
                    "expected_count": len(expected),
                    "days": days,
                    "evidence": "NO_DAY_PRESENCE_FILE",
                }
                continue

            in_year = {d for d in present if d in expected_set}
            if stream == "cls_brazil" and not in_year:
                days = [
                    {
                        "date": d,
                        "iso": f"{d[0:4]}-{d[4:6]}-{d[6:8]}",
                        "month": int(d[4:6]),
                        "day": int(d[6:8]),
                        "state": "OUT_OF_SPAN",
                    }
                    for d in expected
                ]
                product_blocks[product] = {
                    "present_count": 0,
                    "missing_count": 0,
                    "out_count": len(expected),
                    "expected_count": len(expected),
                    "days": days,
                    "evidence": "directory_names",
                }
                continue

            if in_year:
                first = min(in_year)
                last = max(in_year)
            else:
                first = last = None

            days = []
            present_count = missing_count = out_count = 0
            for d in expected:
                if d in in_year:
                    state = "PRESENT"
                    present_count += 1
                elif stream == "internal":
                    state = "MISSING"
                    missing_count += 1
                elif first and last and first <= d <= last:
                    state = "MISSING"
                    missing_count += 1
                elif first and last and (d < first or d > last):
                    state = "OUT_OF_SPAN"
                    out_count += 1
                else:
                    state = "MISSING"
                    missing_count += 1
                days.append(
                    {
                        "date": d,
                        "iso": f"{d[0:4]}-{d[4:6]}-{d[6:8]}",
                        "month": int(d[4:6]),
                        "day": int(d[6:8]),
                        "state": state,
                    }
                )

            product_blocks[product] = {
                "present_count": present_count,
                "missing_count": missing_count,
                "out_count": out_count,
                "expected_count": len(expected),
                "span_first": first,
                "span_last": last,
                "days": days,
                "evidence": (presence or {}).get("basis", "directory_names"),
            }

        all_days = []
        for d in expected:
            states = [
                next(x["state"] for x in product_blocks[p]["days"] if x["date"] == d)
                for p in products
            ]
            if all(s == "PRESENT" for s in states):
                agg = "PRESENT"
            elif all(s == "OUT_OF_SPAN" for s in states):
                agg = "OUT_OF_SPAN"
            elif any(s == "PRESENT" for s in states):
                agg = "PARTIAL"
            else:
                agg = "MISSING"
            all_days.append(
                {
                    "date": d,
                    "iso": f"{d[0:4]}-{d[4:6]}-{d[6:8]}",
                    "month": int(d[4:6]),
                    "day": int(d[6:8]),
                    "state": agg,
                }
            )

        present_all = sum(1 for x in all_days if x["state"] == "PRESENT")
        by_stream[stream] = {
            "products": product_blocks,
            "all_required": {
                "present_count": present_all,
                "expected_count": len(expected),
                "days": all_days,
            },
        }

    available_years = sorted(
        {
            int(p.stem.split("_")[-1])
            for p in (root / "data" / "manifests").glob("day_presence_*.json")
            if p.stem.split("_")[-1].isdigit()
        }
    )

    return {
        "year": year,
        "scan_date": (presence or {}).get("scan_date"),
        "basis": (presence or {}).get("basis", "unknown"),
        "has_presence_file": load_day_presence(root, year) is not None,
        "synthesized": bool((presence or {}).get("synthesized")),
        "available_years": available_years or [year],
        "products": list(products),
        "streams": by_stream,
        "months": [
            {
                "num": m,
                "name": calendar.month_abbr[m],
                "days_in_month": calendar.monthrange(year, m)[1],
            }
            for m in range(1, 13)
        ],
        "disclaimer": (
            "Day calendar shows directory inventory only — "
            "not integrity verified or scientifically accepted."
        ),
    }


def _compact_states(days: list[dict[str, Any]]) -> str:
    return "".join(_STATE_CHAR.get(d["state"], "?") for d in days)


def compact_year_coverage(cov: dict[str, Any]) -> dict[str, Any]:
    """Strip bulky day objects to state strings for client rendering."""
    products = cov["products"]
    streams_out: dict[str, Any] = {}
    for stream, block in cov["streams"].items():
        prod_map = {}
        for product in products:
            pb = block["products"][product]
            prod_map[product] = {
                "states": _compact_states(pb["days"]),
                "present_count": pb["present_count"],
                "missing_count": pb["missing_count"],
                "out_count": pb["out_count"],
                "expected_count": pb["expected_count"],
            }
        ar = block["all_required"]
        streams_out[stream] = {
            "products": prod_map,
            "all_required": {
                "states": _compact_states(ar["days"]),
                "present_count": ar["present_count"],
                "expected_count": ar["expected_count"],
            },
        }
    return {
        "year": cov["year"],
        "scan_date": cov.get("scan_date"),
        "basis": cov.get("basis"),
        "has_presence_file": cov.get("has_presence_file"),
        "synthesized": cov.get("synthesized"),
        "products": products,
        "streams": streams_out,
        "months": cov["months"],
        "disclaimer": cov.get("disclaimer"),
    }


def build_multi_year_day_coverage(
    root: Path,
    years: list[int],
    *,
    default_year: int | None = None,
    products: tuple[str, ...] | list[str] = POSTPROCESSED_PRODUCTS,
) -> dict[str, Any]:
    """Coverage for every catalog year; compact payload for the dashboard."""
    years = sorted(set(int(y) for y in years))
    if not years:
        years = [2015]
    inventory = load_inventory_scan(root)
    if default_year is None:
        default_year = 2015 if 2015 in years else years[-1]
    if default_year not in years:
        default_year = years[0]

    by_year: dict[str, Any] = {}
    full_default = None
    for year in years:
        cov = build_year_day_coverage(
            root, year, products=products, inventory=inventory
        )
        by_year[str(year)] = compact_year_coverage(cov)
        if year == default_year:
            full_default = cov

    assert full_default is not None
    full_default = dict(full_default)
    full_default["available_years"] = years
    full_default["by_year"] = by_year
    full_default["default_year"] = default_year
    return full_default


def attach_day_coverage(
    catalog: dict[str, Any], root: Path, year: int = 2015
) -> dict[str, Any]:
    catalog = dict(catalog)
    years = catalog_years_from_matrices(
        catalog.get("historical_matrix") or [],
        catalog.get("remaining_matrix") or [],
    )
    if not years:
        years = [year]
    catalog["day_coverage"] = build_multi_year_day_coverage(
        root, years, default_year=year if year in years else years[0]
    )
    return catalog


def expand_states(states: str, year: int) -> list[dict[str, Any]]:
    """Test helper: expand compact state string back to day dicts."""
    expected = days_in_year(year)
    out = []
    for i, d in enumerate(expected):
        ch = states[i] if i < len(states) else "?"
        out.append(
            {
                "date": d,
                "iso": f"{d[0:4]}-{d[4:6]}-{d[6:8]}",
                "month": int(d[4:6]),
                "day": int(d[6:8]),
                "state": _CHAR_STATE.get(ch, "MISSING"),
            }
        )
    return out
