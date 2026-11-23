"""Day-level inventory coverage for the dashboard (not scientific acceptance)."""

from __future__ import annotations

import calendar
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .catalog import POSTPROCESSED_PRODUCTS

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


def _present_set(
    presence: dict[str, Any] | None, stream: str, product: str
) -> set[str] | None:
    if not presence:
        return None
    streams = presence.get("streams") or {}
    stream_block = streams.get(stream) or {}
    aliases = (presence.get("product_aliases") or {}).get(stream) or {}
    key = aliases.get(product, product)
    if key not in stream_block and product in stream_block:
        key = product
    if key not in stream_block:
        # Alias-only product with empty list vs missing key
        if key in stream_block:
            return set(stream_block[key] or [])
        # Try raw product
        if product in stream_block:
            return set(stream_block[product] or [])
        return set()
    return set(stream_block.get(key) or [])


def build_year_day_coverage(
    root: Path,
    year: int,
    *,
    products: tuple[str, ...] | list[str] = POSTPROCESSED_PRODUCTS,
    default_stream: str = "cls_brazil",
) -> dict[str, Any]:
    """Build inventory day coverage for one calendar year.

    States per day/product: PRESENT | MISSING | OUT_OF_SPAN.
    OUT_OF_SPAN when the product has no presence evidence intersecting the year
    and no days listed (empty alias list for ocean2d in 2015 CLS).
    """
    presence = load_day_presence(root, year)
    expected = days_in_year(year)
    expected_set = set(expected)
    products = list(products)

    by_stream: dict[str, Any] = {}
    for stream in ("cls_brazil", "internal"):
        product_blocks: dict[str, Any] = {}
        for product in products:
            present = _present_set(presence, stream, product)
            if present is None:
                # No year file — all UNKNOWN-like: treat as OUT_OF_SPAN with note
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
            # CLS with no days this year (e.g. legacy ocean2d after 2001) → OUT_OF_SPAN
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
                    # Remaining-internal year is expected; absent days are MISSING
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

        # Aggregated "all products" present if all four PRESENT same day
        all_days = []
        for d in expected:
            states = [
                next(
                    x["state"]
                    for x in product_blocks[p]["days"]
                    if x["date"] == d
                )
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
        int(p.stem.split("_")[-1])
        for p in (root / "data" / "manifests").glob("day_presence_*.json")
        if p.stem.split("_")[-1].isdigit()
    )

    return {
        "year": year,
        "scan_date": (presence or {}).get("scan_date"),
        "basis": (presence or {}).get("basis", "unknown"),
        "has_presence_file": presence is not None,
        "available_years": available_years or [year],
        "products": list(products),
        "streams": by_stream,
        "months": [
            {"num": m, "name": calendar.month_abbr[m], "days_in_month": calendar.monthrange(year, m)[1]}
            for m in range(1, 13)
        ],
        "disclaimer": (
            "Daily inventory coverage from directory_names evidence only — "
            "not integrity VERIFIED or scientific ACCEPTED."
        ),
    }


def attach_day_coverage(catalog: dict[str, Any], root: Path, year: int = 2015) -> dict[str, Any]:
    catalog = dict(catalog)
    catalog["day_coverage"] = build_year_day_coverage(root, year)
    return catalog
