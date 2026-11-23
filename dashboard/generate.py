#!/usr/bin/env python3
"""Generate a static catalog-centric HTML dashboard from tracking data."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.catalog import build_catalog_view  # noqa: E402
from lib.tracking import TrackingStore, compute_progress  # noqa: E402

_SENTINELS = frozenset(
    {
        "UNKNOWN",
        "NOT_RECORDED",
        "NOT_VERIFIED",
        "NOT_VALIDATED",
        "NOT_CONFIRMED",
        "None",
        "",
    }
)


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _status_class(status: str) -> str:
    mapping = {
        "COMPLETED": "ok",
        "ACCEPTED": "ok",
        "VERIFIED": "ok",
        "CATALOGUED": "run",
        "CREATED": "ready",
        "EXPECTED": "muted",
        "RUNNING": "run",
        "READY": "ready",
        "FAILED": "bad",
        "FAILED_VALIDATION": "bad",
        "BLOCKED": "bad",
        "MISSING": "bad",
        "INCOMPLETE": "warn",
        "OPEN": "bad",
        "CANCELLED": "muted",
        "NOT_STARTED": "muted",
        "UNKNOWN": "unk",
        "NOT_VERIFIED": "unk",
        "NOT_VALIDATED": "unk",
        "PROVISIONAL / NOT CONFIRMED": "warn",
        "CRITICAL": "bad",
        "HIGH": "warn",
        "MEDIUM": "run",
        "LOW": "muted",
    }
    return mapping.get(status, "unk")


def _pill(status: object) -> str:
    s = "UNKNOWN" if status is None else str(status)
    return f'<span class="pill {_status_class(s)}">{_esc(s)}</span>'


def _cell_text(value: object) -> str:
    """Render a table cell value, muting known sentinel placeholders."""
    if value is None:
        text = "UNKNOWN"
    else:
        text = str(value)
    if text in _SENTINELS or text.upper() in _SENTINELS:
        return f'<span class="sentinel">{_esc(text or "UNKNOWN")}</span>'
    return _esc(text)


def _chips(counts: dict) -> str:
    if not counts:
        return '<span class="muted">none</span>'
    parts = []
    for key in sorted(counts, key=lambda k: str(k)):
        parts.append(
            f'<span class="chip"><span class="chip-k">{_esc(key)}</span>'
            f'<span class="chip-v">{_esc(counts[key])}</span></span>'
        )
    return "".join(parts)


def _matrix_table(
    title: str,
    matrix: list[dict],
    products: list[str],
    origin_label: str,
    day_years: list[int] | None = None,
    section_id: str | None = None,
) -> str:
    if not matrix:
        sid = f' id="{_esc(section_id)}"' if section_id else ""
        return (
            f"<section{sid}>"
            f"<h2>{_esc(title)}</h2><p class='muted'>No periods recorded.</p></section>"
        )
    day_years = day_years or []
    day_attr = ",".join(str(y) for y in day_years)
    headers = "".join(f"<th>{_esc(p)}</th>" for p in products)
    rows = []
    for row in matrix:
        cells = "".join(
            f'<td><button type="button" class="cell {_status_class(row["cells"][p])}" '
            f'data-filter-year="{row["year"]}" data-filter-product="{_esc(p)}" '
            f'data-filter-origin="{_esc(origin_label)}" '
            f'aria-label="{row["year"]} {_esc(p)}: {_esc(row["cells"][p])}" '
            f'title="{row["year"]} {_esc(p)}: {_esc(row["cells"][p])}">'
            f'{_esc(row["cells"][p])}</button></td>'
            for p in products
        )
        rows.append(f'<tr><th scope="row">{row["year"]}</th>{cells}</tr>')
    sid = f' id="{_esc(section_id)}"' if section_id else ""
    return f"""
    <section{sid} data-day-years="{_esc(day_attr)}">
      <h2>{_esc(title)}</h2>
      <p class="muted">Click a cell to filter datasets and jump the day calendar to that year/product. Origin: {_esc(origin_label)}. Matrix = lifecycle overview, not day completeness.</p>
      <div class="table-wrap">
        <table class="matrix">
          <thead><tr><th>Year</th>{headers}</tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
    </section>
    """


def _todo_rows(tasks: list[dict]) -> str:
    if not tasks:
        return '<tr><td colspan="8">None</td></tr>'
    rows = []
    for t in tasks:
        ds_links = []
        for did in t.get("related_dataset_ids") or []:
            ds_links.append(f'<a href="#ds-{_esc(did)}">{_esc(did)}</a>')
        related_html = ", ".join(ds_links) if ds_links else "—"
        rows.append(
            f'<tr id="todo-{_esc(t["id"])}">'
            f"<td>{_esc(t['id'])}</td>"
            f"<td>{_esc(t['title'])}</td>"
            f"<td>{_pill(t.get('priority'))}</td>"
            f"<td>{_pill(t.get('status'))}</td>"
            f"<td>{_cell_text(t.get('owner') or 'UNKNOWN')}</td>"
            f"<td>{_cell_text(t.get('due_date') or 'NOT_RECORDED')}</td>"
            f"<td>{related_html}</td>"
            f"<td>{_cell_text(t.get('last_updated') or t.get('start_date') or 'UNKNOWN')}</td>"
            f"</tr>"
        )
    return "".join(rows)


def _glyph(state: str) -> str:
    return {
        "PRESENT": "✓",
        "MISSING": "·",
        "OUT_OF_SPAN": "–",
        "PARTIAL": "~",
    }.get(state, "?")


def _next_gap_iso(states: str, year: int) -> str:
    """First MISSING else first OUT_OF_SPAN day iso from compact state string."""
    from datetime import date, timedelta

    if not states:
        return "—"
    start = date(int(year), 1, 1)
    for prefer in ("M", "O"):
        idx = states.find(prefer)
        if idx >= 0:
            d = start + timedelta(days=idx)
            return d.isoformat()
    return "—"


def _day_progress_section(catalog: dict) -> str:
    dc = catalog.get("day_coverage")
    if not dc:
        return (
            '<section id="daily-progress">'
            "<h2>Daily inventory</h2>"
            '<p class="muted">No inventory day coverage available yet.</p>'
            "</section>"
        )
    year = int(dc.get("default_year") or dc["year"])
    years = list(dc.get("available_years") or [year])
    years_csv = ",".join(str(y) for y in years)
    products = dc["products"]
    by_year = dc.get("by_year") or {}
    # Ensure default year compact block exists (multi-year builder always sets it)
    if str(year) not in by_year and "streams" in dc:
        # Legacy single-year shape — compact on the fly is not needed if by_year present
        pass

    year_opts = "".join(
        f'<option value="{y}"{" selected" if int(y) == year else ""}>{y}</option>'
        for y in years
    )
    compact_default = by_year.get(str(year)) or {}
    cls_all = (
        ((compact_default.get("streams") or {}).get("cls_brazil") or {}).get(
            "all_required"
        )
        or {}
    )
    int_all = (
        ((compact_default.get("streams") or {}).get("internal") or {}).get(
            "all_required"
        )
        or {}
    )
    next_missing = _next_gap_iso(cls_all.get("states") or "", year)

    payload = {
        "default_year": year,
        "available_years": years,
        "products": products,
        "by_year": by_year,
        "glyphs": {
            "PRESENT": "✓",
            "MISSING": "·",
            "OUT_OF_SPAN": "–",
            "PARTIAL": "~",
        },
        "state_from_char": {
            "P": "PRESENT",
            "M": "MISSING",
            "O": "OUT_OF_SPAN",
            "A": "PARTIAL",
        },
    }
    payload_json = json.dumps(payload, separators=(",", ":")).replace("<", "\\u003c")

    return f"""
    <section id="daily-progress" data-day-years="{_esc(years_csv)}">
      <h2>Daily inventory</h2>
      <p class="banner-inline">{_esc(dc.get("disclaimer") or "Directory inventory by calendar day — not verified or accepted.")}</p>
      <div class="sticky-bar" id="day-controls" role="region" aria-label="Daily inventory filters">
        <label>Year <select id="day-year">{year_opts}</select></label>
        <label>Stream <select id="day-stream">
          <option value="cls_brazil">CLS historical</option>
          <option value="internal">Internal hindcast</option>
        </select></label>
        <label>Product <select id="day-product">
          <option value="all">All products</option>
          {"".join(f'<option value="{_esc(p)}">{_esc(p)}</option>' for p in products)}
        </select></label>
        <span class="muted" id="day-meta">inventory scan · {_esc(dc.get("scan_date") or "UNKNOWN")}</span>
        <p id="day-year-notice" class="day-notice" hidden role="status" aria-live="polite"></p>
      </div>
      <div class="cards kpi-strip" id="day-kpi">
        <div class="card"><div class="label">CLS all-4 present</div>
          <div class="stat" id="kpi-cls">{cls_all.get("present_count", 0)}/{cls_all.get("expected_count", 0)}</div>
          <div class="muted">dirs present</div></div>
        <div class="card"><div class="label">Internal all-4 present</div>
          <div class="stat" id="kpi-int">{int_all.get("present_count", 0)}/{int_all.get("expected_count", 0)}</div>
          <div class="muted">dirs present</div></div>
        <div class="card"><div class="label">Year</div>
          <div class="stat" id="kpi-year">{year}</div>
          <div class="muted">calendar</div></div>
        <div class="card"><div class="label">Next CLS gap</div>
          <div class="stat" id="kpi-gap" style="font-size:1.1rem">{_esc(next_missing)}</div>
          <div class="muted">first missing/out</div></div>
      </div>
      <div class="legend" aria-label="Day state legend">
        <span class="leg PRESENT"><span class="swatch" aria-hidden="true">✓</span> Present</span>
        <span class="leg MISSING"><span class="swatch" aria-hidden="true">·</span> Missing</span>
        <span class="leg OUT_OF_SPAN"><span class="swatch" aria-hidden="true">–</span> Out of span</span>
        <span class="leg PARTIAL"><span class="swatch" aria-hidden="true">~</span> Partial</span>
      </div>
      <div class="table-wrap">
        <table id="day-product-summary" aria-label="Day inventory by catalog product">
          <thead>
            <tr>
              <th>Product</th>
              <th>CLS present</th>
              <th>CLS missing</th>
              <th>CLS out of span</th>
              <th>Internal present</th>
            </tr>
          </thead>
          <tbody id="day-product-summary-body">
            {"".join(
              f"<tr data-product=\"{_esc(p)}\"><td>{_esc(p)}</td>"
              f"<td colspan=\"4\">Loading…</td></tr>"
              for p in products
            )}
          </tbody>
        </table>
      </div>
      <div id="cal-cls" class="cal-stack" data-stream="cls_brazil"></div>
      <div id="cal-internal" class="cal-stack" data-stream="internal" hidden></div>
      <details class="a11y-table">
        <summary>Day table (sample, max 200 rows)</summary>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Date</th><th>Stream</th><th>Product</th><th>State</th></tr></thead>
            <tbody id="day-a11y-body"><tr><td colspan="4">Loading…</td></tr></tbody>
          </table>
        </div>
      </details>
      <script type="application/json" id="day-coverage-data">{payload_json}</script>
    </section>
    """


def render(store: TrackingStore, progress: dict, catalog: dict | None = None) -> str:
    catalog = catalog or build_catalog_view(store)
    summary = catalog["summary"]
    products = summary["matrix_products"]
    dc = catalog.get("day_coverage") or {}
    day_years = list(dc.get("available_years") or ([dc["year"]] if dc.get("year") else []))

    issue_rows = "".join(
        f"<tr><td>{_esc(i['id'])}</td><td>{_esc(i['title'])}</td>"
        f"<td>{_esc(i['severity'])}</td><td>{_esc(i['status'])}</td>"
        f"<td>{_esc(i.get('owner'))}</td></tr>"
        for i in progress["open_issues"]
    ) or '<tr><td colspan="5">None recorded</td></tr>'

    stage_rows = "".join(
        f"<tr><td>{_esc(s['order'])}</td><td>{_esc(s['name'])}</td>"
        f'<td>{_pill(s["status"])}</td>'
        f"<td>{_esc(s.get('notes'))}</td></tr>"
        for s in progress["workflow_stages"]
    )

    metric_rows = "".join(
        f"<tr><td>{_esc(name)}</td><td>{m['matched']}/{m['total']}</td>"
        f"<td>{_esc(m['percent_display'])}</td><td>{_esc(m.get('note'))}</td></tr>"
        for name, m in progress["metrics"].items()
    )

    workload_rows = "".join(
        f"<tr><td>{_esc(mid)}</td><td>{count}</td></tr>"
        for mid, count in progress["workload"].items()
    )

    hpc = progress.get("hpc_snapshot_status") or {"state": "MISSING"}
    snap = progress.get("latest_hpc_snapshot")
    ttl = progress.get("hpc_snapshot_ttl_hours")
    state = hpc.get("state", "MISSING")
    if snap and state in {"FRESH", "STALE"}:
        job_note = (
            f"{len(snap.get('jobs', []))} queue job(s)"
            if state == "FRESH"
            else "job list must not be treated as current"
        )
        snap_html = (
            f'<p>{_pill(state)} TTL={_esc(ttl)}h · {_esc(snap.get("id"))} collected '
            f'{_esc(snap.get("collected_at"))} ({_esc(snap.get("mode"))}) — {job_note}.</p>'
        )
    elif state == "MISSING":
        snap_html = (
            f"<p>{_pill('MISSING')} No usable HPC snapshot recorded. "
            "Not equivalent to zero jobs.</p>"
        )
    else:
        snap_html = f"<p>{_pill(state)} HPC snapshot unavailable (TTL={_esc(ttl)}h).</p>"

    inv_rows = []
    detail_blocks = []
    other_links: list[str] = []

    def _dataset_detail_html(ds: dict) -> str:
        todo_list = "".join(
            f'<li><a href="#todo-{_esc(t["id"])}">{_esc(t["id"])}</a>: '
            f'{_esc(t["title"])} {_pill(t["status"])}</li>'
            for t in ds["todos"]
        ) or "<li>No linked TODOs</li>"
        timeline = "".join(
            f"<li><strong>{_esc(ev['when'])}</strong> — {_esc(ev['label'])}: {_esc(ev['detail'])}</li>"
            for ev in ds["timeline"]
        ) or "<li>No recorded events</li>"
        return f"""
        <details class="dataset-detail" id="ds-{_esc(ds['id'])}"
          data-origin="{_esc(ds['origin'])}" data-product="{_esc(ds['product'])}">
          <summary>
            <strong>{_esc(ds['id'])}</strong>
            {_pill(ds['lifecycle'])}
            <span class="muted">{_esc(ds['origin_label'])} · {_esc(ds['product'])}</span>
          </summary>
          <div class="detail-grid">
            <div>
              <h4>Identity</h4>
              <ul class="kv">
                <li><span>Name</span><span>{_esc(ds['name'])}</span></li>
                <li><span>Origin</span><span>{_esc(ds['origin_label'])}</span></li>
                <li><span>Product</span><span>{_esc(ds['product'])}</span></li>
                <li><span>Period</span><span>{_cell_text(ds['period_start'] or 'UNKNOWN')} → {_cell_text(ds['period_end'] or 'UNKNOWN')} ({_esc(ds['period_basis'] or 'unknown')})</span></li>
                <li><span>Description</span><span>{_esc(ds['description'] or ds['notes'] or '—')}</span></li>
              </ul>
            </div>
            <div>
              <h4>Inventory</h4>
              <ul class="kv">
                <li><span>Path</span><span><code>{_esc(ds['location'])}</code></span></li>
                <li><span>Files</span><span>{_cell_text(ds['file_count'] if ds['file_count'] is not None else 'UNKNOWN')}</span></li>
                <li><span>Size</span><span>{_cell_text(ds['size_human'])}</span></li>
                <li><span>Manifest</span><span>{_cell_text(ds['manifest_ref'] or 'NOT_RECORDED')}</span></li>
                <li><span>Checksum</span><span>{_cell_text(ds['checksum_ref'] or 'NOT_RECORDED')}</span></li>
                <li><span>Last scan</span><span>{_cell_text(ds['last_inventory_scan'])}</span></li>
              </ul>
            </div>
            <div>
              <h4>Lifecycle</h4>
              <ul class="kv">
                <li><span>Status</span><span>{_pill(ds['lifecycle'])}</span></li>
                <li><span>Created</span><span>{_cell_text(ds['created_at'])} <span class="muted">({_esc(ds['created_at_provenance'])})</span></span></li>
                <li><span>Catalogued</span><span>{_cell_text(ds['catalogued_at'])}</span></li>
                <li><span>Verified</span><span>{_cell_text(ds['verified_at'])}</span></li>
                <li><span>Accepted</span><span>{_cell_text(ds['accepted_at'])}</span></li>
                <li><span>Integrity</span><span>{_pill(ds['integrity_status'])}</span></li>
                <li><span>Validation</span><span>{_pill(ds['validation_status'])}</span></li>
              </ul>
            </div>
            <div>
              <h4>Work tracking</h4>
              <ul class="kv">
                <li><span>Owner</span><span>{_cell_text(ds['owner'])}</span></li>
                <li><span>Open TODOs</span><span>{ds['todo_count']}</span></li>
              </ul>
              <ul>{todo_list}</ul>
            </div>
          </div>
          <h4>Timeline</h4>
          <ol class="timeline">{timeline}</ol>
        </details>
            """

    for ds in catalog["datasets"]:
        inv_rows.append(
            "<tr "
            f'data-id="{_esc(ds["id"])}" '
            f'data-origin="{_esc(ds["origin"])}" '
            f'data-origin-label="{_esc(ds["origin_label"])}" '
            f'data-product="{_esc(ds["product"])}" '
            f'data-lifecycle="{_esc(ds["lifecycle"])}" '
            f'data-owner="{_esc(ds["owner"])}" '
            f'data-todos="{ds["todo_count"]}" '
            f'data-period-start="{_esc(ds["period_start"])}" '
            f'data-period-end="{_esc(ds["period_end"])}" '
            f'data-created="{_esc(ds["created_at"])}" '
            f'data-catalogued="{_esc(ds["catalogued_at"])}" '
            f'data-verified="{_esc(ds["verified_at"])}" '
            f'data-search="{_esc(ds["id"])} {_esc(ds["name"])} {_esc(ds["product"])} {_esc(ds["origin_label"])}">'
            f'<td><a href="#ds-{_esc(ds["id"])}">{_esc(ds["id"])}</a><div class="sub">{_esc(ds["name"])}</div></td>'
            f'<td>{_esc(ds["origin_label"])}</td>'
            f'<td>{_esc(ds["product"])}</td>'
            f'<td>{_cell_text(ds["period_start"] or "UNKNOWN")} → {_cell_text(ds["period_end"] or "UNKNOWN")}</td>'
            f'<td>{_pill(ds["lifecycle"])}</td>'
            f'<td>{_cell_text(ds["created_at"])}</td>'
            f'<td>{_cell_text(ds["catalogued_at"])}</td>'
            f'<td>{_cell_text(ds["verified_at"])}</td>'
            f'<td>{_cell_text(ds["file_count"] if ds["file_count"] is not None else "UNKNOWN")}</td>'
            f'<td>{_cell_text(ds["size_human"])}</td>'
            f'<td>{_cell_text(ds["owner"])}</td>'
            f'<td>{ds["todo_count"]}</td>'
            "</tr>"
        )
        detail_blocks.append(_dataset_detail_html(ds))

    for ds in catalog.get("other_datasets") or []:
        other_links.append(
            f'<li><a href="#ds-{_esc(ds["id"])}">{_esc(ds["id"])}</a> '
            f'({_esc(ds["product"])}) {_pill(ds["lifecycle"])}</li>'
        )
        detail_blocks.append(_dataset_detail_html(ds))

    todo_groups = catalog["todo_groups"]
    group_sections = []
    empty_skip = {
        "overdue",
        "due_soon",
        "other",
        "in_progress",
        "blocked",
        "completed_recently",
    }
    for key, label in (
        ("overdue", "Overdue"),
        ("due_soon", "Due soon"),
        ("in_progress", "In progress"),
        ("blocked", "Blocked"),
        ("not_started", "Not started / Ready"),
        ("completed_recently", "Completed"),
        ("other", "Other"),
    ):
        tasks = todo_groups.get(key) or []
        if not tasks and key in empty_skip:
            continue
        group_sections.append(
            f"<h3 id='todos-{key}'>{_esc(label)} ({len(tasks)})</h3>"
            f'<div class="table-wrap"><table>'
            f"<thead><tr><th>ID</th><th>Title</th><th>Priority</th><th>Status</th>"
            f"<th>Owner</th><th>Due</th><th>Datasets</th><th>Updated</th></tr></thead>"
            f"<tbody>{_todo_rows(tasks)}</tbody></table></div>"
        )

    defs = catalog["definitions"]
    defs_html = "".join(
        f"<li><strong>{_esc(k)}</strong>: {_esc(v)}</li>" for k, v in defs.items()
    )

    origin_opts = "".join(
        f'<option value="{_esc(o)}">{_esc(o)}</option>'
        for o in sorted({d["origin"] for d in catalog["datasets"]})
    )
    product_opts = "".join(
        f'<option value="{_esc(p)}">{_esc(p)}</option>'
        for p in sorted({d["product"] for d in catalog["datasets"] if d["product"]})
    )
    life_opts = "".join(
        f'<option value="{_esc(l)}">{_esc(l)}</option>'
        for l in sorted({d["lifecycle"] for d in catalog["datasets"]})
    )
    owners = sorted({d["owner"] for d in catalog["datasets"]})
    if len(owners) > 1:
        owner_opts = "".join(
            f'<option value="{_esc(o)}">{_esc(o)}</option>' for o in owners
        )
        owner_filter = (
            f'<label>Owner<select id="f-owner"><option value="">All</option>'
            f"{owner_opts}</select></label>"
        )
    else:
        owner_filter = '<input type="hidden" id="f-owner" value=""/>'

    day_section = _day_progress_section(catalog)
    hist_matrix = _matrix_table(
        "Year × product — CLS historical (lifecycle overview)",
        catalog["historical_matrix"],
        products,
        "CLS_HISTORICAL",
        day_years,
        section_id="matrices",
    )
    rem_matrix = _matrix_table(
        "Year × product — Internal hindcast (lifecycle overview)",
        catalog["remaining_matrix"],
        products,
        "INTERNAL_HINDCAST",
        day_years,
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>INACAWO Hindcast Catalog &amp; Progress</title>
  <style>
    :root {{
      --bg: #F4F6F8;
      --surface: #FFFFFF;
      --ink: #142033;
      --muted: #5C6775;
      --line: #D0D8E2;
      --present: #0F6B4C;
      --missing: #8A1C2E;
      --out: #E8ECF0;
      --run: #0B6E99;
      --warn: #9A6700;
      --focus: #0B6E99;
      --ok: #0F6B4C;
      --ready: #6a5a00;
      --bad: #8A1C2E;
      --unk: #5C6775;
      --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
      --cell: 15px;
      --header-h: 72px;
      --sticky-h: 52px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(1200px 400px at 10% -10%, #e7eef5 0%, transparent 55%),
        radial-gradient(900px 360px at 90% 0%, #eef6f1 0%, transparent 50%),
        var(--bg);
      line-height: 1.45;
      scroll-padding-top: calc(var(--header-h) + var(--sticky-h));
    }}
    .skip-link {{
      position: absolute; left: -9999px; top: 0; z-index: 100;
      padding: 0.5rem 0.75rem; background: var(--ink); color: #fff;
      text-decoration: none; border-radius: 0 0 0.25rem 0;
    }}
    .skip-link:focus {{ left: 0; }}
    .visually-hidden {{
      position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
      overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0;
    }}
    header {{
      padding: 1rem var(--space-4) 0.85rem;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, #ffffff 0%, #f7fafc 100%);
    }}
    h1 {{ margin: 0 0 var(--space-1); font-size: 1.45rem; letter-spacing: -0.01em; }}
    .site-nav {{
      display: flex; flex-wrap: wrap; gap: 0.25rem;
      padding: 0.45rem var(--space-4);
      border-bottom: 1px solid var(--line);
      background: #ffffffcc;
      backdrop-filter: blur(6px);
      font-size: 0.82rem;
      position: sticky; top: 0; z-index: 30;
    }}
    .site-nav a {{
      text-decoration: none; color: var(--ink);
      padding: 0.35rem 0.65rem; border-radius: 999px; border: 1px solid transparent;
    }}
    .site-nav a:hover {{ background: #eef3f8; border-color: var(--line); }}
    .banner {{
      display: inline-block; margin-top: var(--space-2); padding: 0.28rem 0.6rem;
      border-radius: 0.25rem; font-weight: 650; background: #fff3cd; color: var(--warn);
      border: 1px solid #f0d48a; font-size: 0.85rem;
    }}
    .banner-inline {{
      margin: 0 0 var(--space-3); padding: var(--space-2) var(--space-3);
      background: #eef6fb; border: 1px solid #b7d4e8; border-radius: 0.25rem;
      color: var(--run); font-size: 0.86rem;
    }}
    .sticky-bar {{
      position: sticky; top: 42px; z-index: 20;
      display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: end;
      padding: 0.55rem 0.65rem;
      margin: 0 0 var(--space-3);
      background: #f4f8fb; border: 1px solid var(--line); border-radius: 0.35rem;
    }}
    .sticky-bar label {{
      display: flex; flex-direction: column; gap: 2px;
      font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.03em;
    }}
    .sticky-bar select {{
      min-height: 36px; min-width: 7.5rem; padding: 0.3rem 0.45rem; border: 1px solid var(--line);
      border-radius: 0.25rem; font: inherit; background: #fff; color: var(--ink); cursor: pointer;
    }}
    .sticky-bar select:focus, button:focus-visible, a:focus-visible,
    .filters input:focus, .filters select:focus, summary:focus-visible {{
      outline: 2px solid var(--focus); outline-offset: 2px;
    }}
    .day-notice {{
      flex: 1 1 100%; margin: 0; padding: 0.35rem 0.5rem;
      background: #fff8e8; border: 1px solid #f0d48a; border-radius: 0.25rem;
      color: var(--warn); font-size: 0.82rem; text-transform: none; letter-spacing: 0;
    }}
    #cal-cls, #cal-internal {{ min-height: 8rem; }}
    main {{
      padding: var(--space-3) var(--space-4) 2.5rem; display: grid; gap: 1rem;
      max-width: 1480px; margin: 0 auto;
    }}
    .cards {{ display: grid; gap: var(--space-2); grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }}
    .kpi-strip .stat {{ font-size: 1.35rem; }}
    .card {{
      background: linear-gradient(180deg, #ffffff, #f8fafc);
      border: 1px solid var(--line); border-radius: 0.4rem;
      padding: 0.7rem 0.8rem;
    }}
    .card .stat {{ font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; }}
    .card .label {{ font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }}
    section {{
      background: var(--surface); border: 1px solid var(--line); border-radius: 0.45rem;
      padding: 1rem 1.05rem; box-shadow: 0 1px 0 rgba(20,32,51,0.03);
    }}
    h2 {{
      margin: 0 0 0.75rem; font-size: 1.05rem; letter-spacing: -0.01em;
      padding-bottom: 0.45rem; border-bottom: 1px solid var(--line);
    }}
    h3 {{ margin: 0 0 var(--space-1); font-size: 0.92rem; }}
    h4 {{ margin: 0.35rem 0; font-size: 0.84rem; }}
    .muted {{ color: var(--muted); font-size: 0.86rem; }}
    .sub {{ font-size: 0.76rem; color: var(--muted); }}
    .sentinel {{ color: var(--muted); font-style: italic; font-size: 0.82rem; }}
    .chip-row {{ display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.65rem; align-items: center; }}
    .chip-row .chip-group-label {{ font-size: 0.72rem; color: var(--muted); text-transform: uppercase; margin-right: 0.15rem; }}
    .chip {{
      display: inline-flex; gap: 0.35rem; align-items: baseline;
      padding: 0.15rem 0.45rem; border: 1px solid var(--line); border-radius: 0.25rem;
      background: #f7f9fb; font-size: 0.78rem;
    }}
    .chip-k {{ color: var(--muted); }}
    .chip-v {{ font-weight: 700; }}
    .legend {{ display: flex; flex-wrap: wrap; gap: var(--space-3); margin: 0 0 var(--space-2); font-size: 0.82rem; }}
    .leg {{ display: inline-flex; align-items: center; gap: 0.35rem; }}
    .leg .swatch {{
      display: inline-flex; width: 1.25rem; height: 1.25rem; align-items: center; justify-content: center;
      border: 1px solid var(--line); border-radius: 0.2rem; font-size: 0.75rem; font-weight: 700;
    }}
    .leg.PRESENT .swatch {{ background: #e6f5ee; color: var(--present); border-color: #8fc9ad; }}
    .leg.MISSING .swatch {{ background: #fdecee; color: var(--missing); border-color: #e3a4ad; }}
    .leg.OUT_OF_SPAN .swatch {{ background: var(--out); color: var(--muted); }}
    .leg.PARTIAL .swatch {{ background: #fff6d6; color: var(--ready); }}
    .cal-hint {{ margin: 0 0 var(--space-2); }}
    .cal-stack {{ display: grid; gap: var(--space-3); }}
    .product-cal {{ border: 1px solid var(--line); border-radius: 0.3rem; padding: var(--space-2); }}
    .cal-row {{ display: grid; grid-template-columns: 2.6rem 1fr; gap: var(--space-1); align-items: start; margin-bottom: 2px; }}
    .cal-month {{ font-size: 0.72rem; font-weight: 650; color: var(--muted); padding-top: 2px; }}
    .cal-days {{
      display: grid; grid-template-columns: repeat(31, minmax(var(--cell), 1fr));
      gap: 2px; overflow-x: auto;
    }}
    span.day {{
      min-width: var(--cell); min-height: calc(var(--cell) + 4px);
      padding: 0; border: 1px solid var(--line); border-radius: 2px;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      font: inherit; line-height: 1; background: #f7f9fb; color: var(--ink);
    }}
    span.day .day-num {{ font-size: 0.58rem; color: var(--muted); }}
    span.day .day-glyph {{ font-size: 0.7rem; font-weight: 700; }}
    span.day-present {{ background: #e6f5ee; border-color: #8fc9ad; color: var(--present); }}
    span.day-missing {{ background: #fdecee; border-color: #e3a4ad; color: var(--missing); }}
    span.day-out_of_span {{ background: var(--out); color: var(--muted); }}
    span.day-partial {{ background: #fff6d6; border-color: #e2d48a; color: var(--ready); }}
    .day-pad {{ min-height: calc(var(--cell) + 4px); }}
    @media (prefers-reduced-motion: reduce) {{
      html {{ scroll-behavior: auto; }}
    }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.84rem; }}
    th, td {{ text-align: left; padding: 0.3rem 0.35rem; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; white-space: nowrap; }}
    .matrix {{ font-size: 0.78rem; }}
    .matrix th, .matrix td {{ text-align: center; padding: 0.2rem; }}
    .matrix th[scope="row"] {{ text-align: left; }}
    .pill {{
      display: inline-block; padding: 0.06rem 0.35rem; border-radius: 0.2rem;
      font-size: 0.7rem; font-weight: 600; background: #eef2f6; white-space: nowrap;
    }}
    .pill.ok {{ background: #dff3e8; color: var(--ok); }}
    .pill.run {{ background: #dff0f8; color: var(--run); }}
    .pill.ready {{ background: #fff6d6; color: var(--ready); }}
    .pill.bad {{ background: #fde4e8; color: var(--bad); }}
    .pill.unk {{ background: #eef1f4; color: var(--unk); }}
    .pill.warn {{ background: #fff3cd; color: var(--warn); }}
    .pill.muted {{ background: #eef1f4; color: var(--muted); }}
    button.cell {{
      border: 1px solid var(--line); border-radius: 0.2rem; padding: 0.2rem 0.28rem;
      font-size: 0.65rem; font-weight: 650; cursor: pointer; width: 100%;
      background: #f7f9fb; color: var(--ink);
    }}
    button.cell.ok {{ background: #eef9f2; border-color: #9fd6b5; color: var(--ok); }}
    button.cell.run {{ background: #eef7fb; border-color: #9dcee6; color: var(--run); }}
    button.cell.ready {{ background: #fffbeb; border-color: #e2d48a; color: var(--ready); }}
    button.cell.bad {{ background: #fff1f3; border-color: #e3a4ad; color: var(--bad); }}
    button.cell.warn {{ background: #fff8e8; border-color: #f0d48a; color: var(--warn); }}
    button.cell.unk, button.cell.muted {{ background: #f4f6f8; color: var(--muted); }}
    .filters {{
      display: grid; gap: var(--space-2);
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      margin-bottom: var(--space-2); align-items: end;
    }}
    .filters label {{ display: flex; flex-direction: column; gap: 0.15rem; font-size: 0.72rem; color: var(--muted); }}
    .filters input, .filters select {{
      padding: 0.3rem 0.4rem; border: 1px solid var(--line); border-radius: 0.25rem;
      font: inherit; color: var(--ink); background: #fff; min-height: 36px;
    }}
    .filters .actions {{ display: flex; gap: 0.35rem; }}
    .filters button {{
      padding: 0.3rem 0.55rem; border: 1px solid var(--line); border-radius: 0.25rem;
      background: #f4f7fb; cursor: pointer; font: inherit; min-height: 36px;
    }}
    .detail-grid {{
      display: grid; gap: var(--space-2);
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      margin-top: var(--space-2);
    }}
    .kv {{ list-style: none; padding: 0; margin: 0; }}
    .kv li {{ display: grid; grid-template-columns: 6.5rem 1fr; gap: 0.3rem; padding: 0.12rem 0; font-size: 0.82rem; }}
    .kv li > span:first-child {{ color: var(--muted); }}
    .timeline {{ margin: 0.2rem 0 0; padding-left: 1rem; font-size: 0.82rem; }}
    details.dataset-detail {{
      border: 1px solid var(--line); border-radius: 0.3rem; padding: 0.4rem 0.55rem;
      margin: 0.35rem 0; background: #fbfcfe;
    }}
    details.dataset-detail > summary, details.a11y-table > summary, details.secondary > summary {{ cursor: pointer; }}
    details.secondary {{ margin-top: 0.2rem; background: var(--surface); border: 1px solid var(--line); border-radius: 0.35rem; padding: var(--space-3); }}
    details.dataset-detail.hash-open {{
      border-color: var(--focus); box-shadow: 0 0 0 2px rgba(11,110,153,0.15);
    }}
    tr.hash-open {{ background: #eef6fb; }}
    footer {{ padding: 0 var(--space-4) var(--space-4); color: var(--muted); font-size: 0.8rem; max-width: 1480px; }}
    code {{ font-size: 0.78rem; }}
    a {{ color: var(--run); }}
    #inv-count {{ font-size: 0.84rem; color: var(--muted); margin: 0.2rem 0 0.45rem; }}
    @media (max-width: 768px) {{
      :root {{ --cell: 18px; --header-h: 96px; }}
      main {{ padding: var(--space-2); }}
      .filters {{ grid-template-columns: 1fr 1fr; }}
      .filters .actions {{ grid-column: 1 / -1; }}
      .filters .actions button {{ width: 100%; }}
      .site-nav {{ gap: 0.5rem; }}
    }}
  </style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to catalog</a>
  <header>
    <h1>INACAWO Hindcast Catalog &amp; Progress</h1>
    <div class="muted">Updated {_esc(progress['generated_at'])}</div>
  </header>
  <nav class="site-nav" aria-label="Catalog sections">
    <a href="#overview">Overview</a>
    <a href="#daily-progress">Daily inventory</a>
    <a href="#matrices">Year × product</a>
    <a href="#inventory">Datasets</a>
    <a href="#todos">TODOs</a>
    <a href="#dataset-details">Dataset detail</a>
    <a href="#secondary">Ops / HPC</a>
  </nav>
  <main id="main">
    <section id="overview">
      <h2>Catalog overview</h2>
      <div class="cards">
        <div class="card"><div class="label">Expected cells</div><div class="stat">{summary['expected_year_product_cells']}</div><div class="muted">year × required product</div></div>
        <div class="card"><div class="label">Catalogued</div><div class="stat">{summary['catalogued_datasets']}</div><div class="muted">dataset records</div></div>
        <div class="card"><div class="label">Created (evidenced)</div><div class="stat">{summary['created_evidenced']}</div><div class="muted">created_at recorded</div></div>
        <div class="card"><div class="label">Verified</div><div class="stat">{summary['verified_datasets']}</div><div class="muted">integrity VERIFIED</div></div>
        <div class="card"><div class="label">Accepted</div><div class="stat">{summary['accepted_datasets']}</div><div class="muted">validation ACCEPTED</div></div>
        <div class="card"><div class="label">Incomplete</div><div class="stat">{summary['incomplete_datasets']}</div><div class="muted">lifecycle INCOMPLETE</div></div>
        <div class="card"><div class="label">Open TODOs</div><div class="stat">{summary['outstanding_todos']}</div><div class="muted">tasks not completed</div></div>
      </div>
      <div class="chip-row" aria-label="Counts by origin">
        <span class="chip-group-label">Origins</span>{_chips(summary['by_origin'])}
      </div>
      <div class="chip-row" aria-label="Counts by product">
        <span class="chip-group-label">Products</span>{_chips(summary['by_product'])}
      </div>
      <div class="chip-row" aria-label="Counts by lifecycle">
        <span class="chip-group-label">Lifecycles</span>{_chips(summary['lifecycle_counts'])}
      </div>
    </section>

    {day_section}

    {hist_matrix}
    {rem_matrix}

    <section id="inventory">
      <h2>Dataset inventory</h2>
      <p class="muted">Primary catalog products only: ocean2d, ocean3d, wrf2d, wrf3d (one row each per origin stream as catalogued).</p>
      <div class="filters" id="inv-filters">
        <label>Search<input type="search" id="f-search" placeholder="id, name, product…"/></label>
        <label>Origin<select id="f-origin"><option value="">All</option>{origin_opts}</select></label>
        <label>Product<select id="f-product"><option value="">All</option>{product_opts}</select></label>
        <label>Lifecycle<select id="f-life"><option value="">All</option>{life_opts}</select></label>
        {owner_filter}
        <label>Year<input type="number" id="f-year" placeholder="e.g. 2001" min="1900" max="2100"/></label>
        <label>TODOs<select id="f-todos"><option value="">All</option><option value="yes">Has outstanding</option><option value="no">None open</option></select></label>
        <label>Sort<select id="f-sort">
          <option value="id">Dataset ID</option>
          <option value="created">Created</option>
          <option value="catalogued">Catalogued</option>
          <option value="verified">Verified</option>
          <option value="lifecycle">Lifecycle</option>
        </select></label>
        <div class="actions"><button type="button" id="f-reset">Reset</button></div>
      </div>
      <div id="inv-count" aria-live="polite"></div>
      <div class="table-wrap">
        <table id="inv-table">
          <thead>
            <tr>
              <th>Dataset</th><th>Origin</th><th>Product</th><th>Period</th><th>Status</th>
              <th>Created</th><th>Catalogued</th><th>Verified</th><th>Files</th><th>Size</th><th>Owner</th><th>TODOs</th>
            </tr>
          </thead>
          <tbody>{''.join(inv_rows)}</tbody>
        </table>
      </div>
    </section>

    <section id="todos">
      <h2>TODO / action tracker</h2>
      <p class="muted">Due dates shown only when explicitly recorded. Owners are member IDs from data/team.yaml — never invented names.</p>
      {''.join(group_sections) or '<p class="muted">No open tasks.</p>'}
    </section>

    <section id="dataset-details">
      <h2>Dataset details</h2>
      <p class="muted">Expand a dataset for inventory, lifecycle timeline, evidence fields, and linked TODOs.</p>
      {''.join(detail_blocks)}
    </section>

    <section id="definitions">
      <h2>Metric definitions</h2>
      <ul>{defs_html}</ul>
      <p class="muted">
        Creation, catalog registration, inventory completeness, integrity verification,
        scientific validation, and human acceptance are separate stages and are never
        collapsed into one misleading percentage while scope is provisional.
      </p>
    </section>

    <details class="secondary" id="secondary">
      <summary><strong>Secondary project information</strong> (other datasets, workflow, issues, HPC, workload)</summary>
      <h2 class="visually-hidden">Secondary project information</h2>
      <div>
        <h3>Other datasets (not primary products)</h3>
        <p class="muted">Run dirs, forcing, ROMS rst archive, samples — tracked but excluded from the primary ocean/WRF catalog.</p>
        <ul>{''.join(other_links) or '<li>None</li>'}</ul>
      </div>
      <div style="display:grid;gap:1rem;margin-top:0.75rem">
        <div>
          <h3>Open issues</h3>
          <div class="table-wrap"><table>
            <thead><tr><th>ID</th><th>Title</th><th>Severity</th><th>Status</th><th>Owner</th></tr></thead>
            <tbody>{issue_rows}</tbody>
          </table></div>
        </div>
        <div>
          <h3>Progress metrics (remaining stream)</h3>
          <div class="table-wrap"><table>
            <thead><tr><th>Metric</th><th>Matched/Total</th><th>Display %</th><th>Note</th></tr></thead>
            <tbody>{metric_rows}</tbody>
          </table></div>
        </div>
        <div>
          <h3>Workflow stages</h3>
          <div class="table-wrap"><table>
            <thead><tr><th>#</th><th>Stage</th><th>Status</th><th>Notes</th></tr></thead>
            <tbody>{stage_rows}</tbody>
          </table></div>
        </div>
        <div class="cards" style="grid-template-columns:1fr 1fr">
          <div class="card">
            <h3>Team workload</h3>
            <table><thead><tr><th>Member</th><th>Open/active</th></tr></thead>
            <tbody>{workload_rows}</tbody></table>
          </div>
          <div class="card">
            <h3>HPC snapshot</h3>
            {snap_html}
            <p class="muted">Active tracked runs: {len(progress['active_runs'])}</p>
          </div>
        </div>
      </div>
    </details>
  </main>
  <footer>
    Catalog &amp; inventory tracking · UNKNOWN / NOT_RECORDED = no evidence yet ·
    refresh: <code>python dashboard/generate.py</code>
  </footer>
  <script>
  (function () {{
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    function smoothScroll(el) {{
      if (!el) return;
      el.scrollIntoView({{ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' }});
    }}

    const dayYear = document.getElementById('day-year');
    const dayStream = document.getElementById('day-stream');
    const dayProduct = document.getElementById('day-product');
    const dayNotice = document.getElementById('day-year-notice');
    const calCls = document.getElementById('cal-cls');
    const calInt = document.getElementById('cal-internal');
    const dailySection = document.getElementById('daily-progress');
    const dayYearsAttr = (dailySection && dailySection.getAttribute('data-day-years')) || '';
    const dayYears = dayYearsAttr.split(',').map(function (s) {{ return s.trim(); }}).filter(Boolean);

    let dayData = null;
    const dayDataEl = document.getElementById('day-coverage-data');
    if (dayDataEl) {{
      try {{ dayData = JSON.parse(dayDataEl.textContent); }} catch (err) {{ dayData = null; }}
    }}

    const glyphMap = (dayData && dayData.glyphs) || {{ PRESENT: '✓', MISSING: '·', OUT_OF_SPAN: '–', PARTIAL: '~' }};
    const charState = (dayData && dayData.state_from_char) || {{ P: 'PRESENT', M: 'MISSING', O: 'OUT_OF_SPAN', A: 'PARTIAL' }};

    function setDayNotice(msg) {{
      if (!dayNotice) return;
      if (!msg) {{
        dayNotice.hidden = true;
        dayNotice.textContent = '';
        return;
      }}
      dayNotice.hidden = false;
      dayNotice.textContent = msg;
    }}

    function pad2(n) {{ return n < 10 ? '0' + n : String(n); }}

    function renderProductCal(product, block, year, months) {{
      const states = block.states || '';
      let html = '<article class="product-cal" data-product="' + product + '">';
      html += '<h3>' + product + '</h3>';
      html += '<p class="muted">Present ' + block.present_count + ' · Missing ' + block.missing_count +
        ' · Out of span ' + block.out_count + ' · expected ' + block.expected_count + '</p>';
      let offset = 0;
      months.forEach(function (mmeta) {{
        const dim = mmeta.days_in_month;
        let cells = '';
        for (let d = 1; d <= dim; d++) {{
          const ch = states.charAt(offset) || 'O';
          offset += 1;
          const st = charState[ch] || 'MISSING';
          const iso = year + '-' + pad2(mmeta.num) + '-' + pad2(d);
          cells += '<span class="day day-' + st.toLowerCase() + '" role="img" aria-label="' +
            iso + ' ' + product + ' ' + st + '" title="' + iso + ' ' + product + ': ' + st + '">' +
            '<span class="day-num" aria-hidden="true">' + d + '</span>' +
            '<span class="day-glyph" aria-hidden="true">' + (glyphMap[st] || '?') + '</span></span>';
        }}
        html += '<div class="cal-row"><div class="cal-month">' + mmeta.name + '</div>' +
          '<div class="cal-days" role="group" aria-label="' + product + ' ' + mmeta.name + '">' +
          cells + '</div></div>';
      }});
      html += '</article>';
      return html;
    }}

    function nextGapFromStates(states, year) {{
      if (!states) return '—';
      let idx = states.indexOf('M');
      if (idx < 0) idx = states.indexOf('O');
      if (idx < 0) return '—';
      const start = new Date(Date.UTC(year, 0, 1));
      start.setUTCDate(start.getUTCDate() + idx);
      return start.toISOString().slice(0, 10);
    }}

    function renderYear(year) {{
      if (!dayData || !dayData.by_year) return;
      const cov = dayData.by_year[String(year)];
      if (!cov) {{
        if (calCls) calCls.innerHTML = '<p class="muted">No inventory for ' + year + '.</p>';
        if (calInt) calInt.innerHTML = '';
        return;
      }}
      const products = cov.products || dayData.products || [];
      const months = cov.months || [];
      const cls = (cov.streams || {{}}).cls_brazil || {{}};
      const inn = (cov.streams || {{}}).internal || {{}};
      let clsHtml = '';
      let intHtml = '';
      products.forEach(function (p) {{
        const pb = (cls.products || {{}})[p];
        const ib = (inn.products || {{}})[p];
        if (pb) clsHtml += renderProductCal(p, pb, year, months);
        if (ib) intHtml += renderProductCal(p, ib, year, months);
      }});
      if (calCls) calCls.innerHTML = clsHtml || '<p class="muted">No CLS inventory for ' + year + '.</p>';
      if (calInt) calInt.innerHTML = intHtml || '<p class="muted">No internal inventory for ' + year + '.</p>';

      const summaryBody = document.getElementById('day-product-summary-body');
      if (summaryBody) {{
        let srows = '';
        products.forEach(function (p) {{
          const pb = (cls.products || {{}})[p] || {{}};
          const ib = (inn.products || {{}})[p] || {{}};
          srows += '<tr data-product="' + p + '"><td>' + p + '</td>' +
            '<td>' + (pb.present_count || 0) + '/' + (pb.expected_count || 0) + '</td>' +
            '<td>' + (pb.missing_count || 0) + '</td>' +
            '<td>' + (pb.out_count || 0) + '</td>' +
            '<td>' + (ib.present_count || 0) + '/' + (ib.expected_count || 0) + '</td></tr>';
        }});
        summaryBody.innerHTML = srows || '<tr><td colspan="5">None</td></tr>';
      }}

      const clsAll = cls.all_required || {{}};
      const intAll = inn.all_required || {{}};
      const kpiCls = document.getElementById('kpi-cls');
      const kpiInt = document.getElementById('kpi-int');
      const kpiYear = document.getElementById('kpi-year');
      const kpiGap = document.getElementById('kpi-gap');
      const dayMeta = document.getElementById('day-meta');
      if (kpiCls) kpiCls.textContent = (clsAll.present_count || 0) + '/' + (clsAll.expected_count || 0);
      if (kpiInt) kpiInt.textContent = (intAll.present_count || 0) + '/' + (intAll.expected_count || 0);
      if (kpiYear) kpiYear.textContent = String(year);
      if (kpiGap) kpiGap.textContent = nextGapFromStates(clsAll.states || '', year);
      if (dayMeta) {{
        dayMeta.textContent = (cov.basis || 'directory_names') +
          (cov.synthesized ? ' (from inventory scan)' : '') +
          ' · ' + (cov.scan_date || 'UNKNOWN');
      }}

      // Accessible sample table
      const a11yBody = document.getElementById('day-a11y-body');
      if (a11yBody) {{
        let rows = '';
        let n = 0;
        products.forEach(function (p) {{
          const pb = (cls.products || {{}})[p];
          if (!pb || !pb.states) return;
          const states = pb.states;
          for (let i = 0; i < states.length && n < 200; i++) {{
            const ch = states.charAt(i);
            if (ch === 'O') continue;
            const st = charState[ch] || 'MISSING';
            const dt = new Date(Date.UTC(year, 0, 1));
            dt.setUTCDate(dt.getUTCDate() + i);
            const iso = dt.toISOString().slice(0, 10);
            rows += '<tr><td>' + iso + '</td><td>CLS_HISTORICAL</td><td>' + p + '</td><td>' + st + '</td></tr>';
            n += 1;
          }}
        }});
        a11yBody.innerHTML = rows || '<tr><td colspan="4">None</td></tr>';
      }}
      applyDayFilters();
    }}

    function applyDayFilters() {{
      if (!dayStream || !dayProduct) return;
      const stream = dayStream.value;
      const product = dayProduct.value;
      if (calCls) calCls.hidden = stream !== 'cls_brazil';
      if (calInt) calInt.hidden = stream !== 'internal';
      document.querySelectorAll('.product-cal').forEach(function (art) {{
        const show = product === 'all' || art.getAttribute('data-product') === product;
        art.hidden = !show;
      }});
    }}

    function currentDayYear() {{
      return dayYear ? dayYear.value : (dayData && dayData.default_year);
    }}

    if (dayYear) {{
      dayYear.addEventListener('change', function () {{
        setDayNotice('');
        renderYear(parseInt(dayYear.value, 10));
      }});
    }}
    if (dayStream) dayStream.addEventListener('change', applyDayFilters);
    if (dayProduct) dayProduct.addEventListener('change', applyDayFilters);
    if (dayData) renderYear(parseInt(currentDayYear(), 10));
    else applyDayFilters();

    function syncDailyFromMatrix(year, product, originLabel) {{
      const hasYear = year && dayYears.indexOf(String(year)) !== -1;
      if (!hasYear) {{
        setDayNotice(year ? ('Year ' + year + ' is outside the catalog day range.') : '');
        return false;
      }}
      setDayNotice('');
      if (dayYear) {{
        dayYear.value = String(year);
        renderYear(parseInt(year, 10));
      }}
      if (dayStream) {{
        dayStream.value = originLabel === 'INTERNAL_HINDCAST' ? 'internal' : 'cls_brazil';
      }}
      if (dayProduct && product) {{
        dayProduct.value = product;
      }}
      applyDayFilters();
      return true;
    }}

    const tbody = document.querySelector('#inv-table tbody');
    const countEl = document.getElementById('inv-count');
    const els = {{
      search: document.getElementById('f-search'),
      origin: document.getElementById('f-origin'),
      product: document.getElementById('f-product'),
      life: document.getElementById('f-life'),
      owner: document.getElementById('f-owner'),
      year: document.getElementById('f-year'),
      todos: document.getElementById('f-todos'),
      sort: document.getElementById('f-sort'),
      reset: document.getElementById('f-reset'),
    }};

    function yearInPeriod(start, end, year) {{
      if (!year) return true;
      if (!start || !end || start === 'None' || end === 'None') return false;
      const ys = parseInt(String(start).slice(0, 4), 10);
      const ye = parseInt(String(end).slice(0, 4), 10);
      if (Number.isNaN(ys) || Number.isNaN(ye)) return false;
      return ys <= year && year <= ye;
    }}

    function apply() {{
      if (!tbody || !els.search) return;
      const rows = Array.from(tbody.querySelectorAll('tr'));
      const q = (els.search.value || '').trim().toLowerCase();
      const origin = els.origin ? els.origin.value : '';
      const product = els.product ? els.product.value : '';
      const life = els.life ? els.life.value : '';
      const owner = els.owner ? els.owner.value : '';
      const year = els.year && els.year.value ? parseInt(els.year.value, 10) : null;
      const todos = els.todos ? els.todos.value : '';
      let visible = 0;
      rows.forEach(function (row) {{
        const okSearch = !q || (row.dataset.search || '').toLowerCase().includes(q);
        const okOrigin = !origin || row.dataset.origin === origin;
        const okProduct = !product || row.dataset.product === product;
        const okLife = !life || row.dataset.lifecycle === life;
        const okOwner = !owner || row.dataset.owner === owner;
        const okYear = yearInPeriod(row.dataset.periodStart, row.dataset.periodEnd, year);
        const todoCount = parseInt(row.dataset.todos || '0', 10);
        const okTodos = !todos || (todos === 'yes' ? todoCount > 0 : todoCount === 0);
        const show = okSearch && okOrigin && okProduct && okLife && okOwner && okYear && okTodos;
        row.style.display = show ? '' : 'none';
        if (show) visible += 1;
      }});
      if (countEl) countEl.textContent = visible + ' of ' + rows.length + ' datasets shown';

      if (els.sort) {{
        const key = els.sort.value;
        const sorted = rows.slice().sort(function (a, b) {{
          const av = a.dataset[key] || a.dataset.id || '';
          const bv = b.dataset[key] || b.dataset.id || '';
          if (av === 'UNKNOWN' && bv !== 'UNKNOWN') return 1;
          if (bv === 'UNKNOWN' && av !== 'UNKNOWN') return -1;
          return String(av).localeCompare(String(bv));
        }});
        sorted.forEach(function (r) {{ tbody.appendChild(r); }});
      }}
    }}

    if (tbody && els.search) {{
      Object.keys(els).forEach(function (k) {{
        if (k === 'reset' || !els[k]) return;
        els[k].addEventListener('input', apply);
        els[k].addEventListener('change', apply);
      }});
      if (els.reset) {{
        els.reset.addEventListener('click', function () {{
          if (els.search) els.search.value = '';
          if (els.origin) els.origin.value = '';
          if (els.product) els.product.value = '';
          if (els.life) els.life.value = '';
          if (els.owner) els.owner.value = '';
          if (els.year) els.year.value = '';
          if (els.todos) els.todos.value = '';
          if (els.sort) els.sort.value = 'id';
          if (dayYear && dayData) {{
            dayYear.value = String(dayData.default_year);
            renderYear(parseInt(dayData.default_year, 10));
          }}
          if (dayStream) dayStream.value = 'cls_brazil';
          if (dayProduct) dayProduct.value = 'all';
          applyDayFilters();
          setDayNotice('');
          apply();
        }});
      }}
      apply();
    }}

    document.querySelectorAll('button.cell').forEach(function (btn) {{
      btn.addEventListener('click', function () {{
        const product = btn.getAttribute('data-filter-product') || '';
        const year = btn.getAttribute('data-filter-year') || '';
        const originLabel = btn.getAttribute('data-filter-origin') || '';
        if (els.product) els.product.value = product;
        if (els.year) els.year.value = year;
        if (els.origin) {{
          if (originLabel === 'CLS_HISTORICAL') els.origin.value = 'cls_brazil';
          else if (originLabel === 'INTERNAL_HINDCAST') els.origin.value = 'internal';
          else els.origin.value = '';
        }}
        apply();
        syncDailyFromMatrix(year, product, originLabel);
        const inv = document.getElementById('inv-filters');
        smoothScroll(inv || document.getElementById('inv-table'));
      }});
    }});

    function openFromHash() {{
      const hash = location.hash || '';
      document.querySelectorAll('details.dataset-detail.hash-open').forEach(function (d) {{
        d.classList.remove('hash-open');
      }});
      document.querySelectorAll('tr.hash-open').forEach(function (r) {{
        r.classList.remove('hash-open');
      }});
      if (hash.indexOf('#ds-') === 0) {{
        const el = document.getElementById(hash.slice(1));
        if (el && el.tagName === 'DETAILS') {{
          el.open = true;
          el.classList.add('hash-open');
          const summary = el.querySelector('summary');
          if (summary) summary.focus();
        }}
      }} else if (hash.indexOf('#todo-') === 0) {{
        const row = document.getElementById(hash.slice(1));
        if (row) {{
          row.classList.add('hash-open');
          smoothScroll(row);
        }}
      }} else if (hash === '#secondary') {{
        const sec = document.getElementById('secondary');
        if (sec) sec.open = true;
      }}
    }}
    window.addEventListener('hashchange', openFromHash);
    openFromHash();
  }})();
  </script>
</body>
</html>
"""


def main() -> int:
    store = TrackingStore.load(ROOT)
    progress = compute_progress(store)
    catalog = build_catalog_view(store)
    out_dir = ROOT / "dashboard" / "public"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "index.html"
    path.write_text(render(store, progress, catalog), encoding="utf-8")
    print(f"Wrote {path}")
    print(
        "Catalog summary:",
        {
            "catalogued": catalog["summary"]["catalogued_datasets"],
            "created_evidenced": catalog["summary"]["created_evidenced"],
            "verified": catalog["summary"]["verified_datasets"],
            "incomplete": catalog["summary"]["incomplete_datasets"],
            "todos": catalog["summary"]["outstanding_todos"],
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
