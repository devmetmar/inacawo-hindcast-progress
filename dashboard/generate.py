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
    }
    return mapping.get(status, "unk")


def _pill(status: object) -> str:
    s = "UNKNOWN" if status is None else str(status)
    return f'<span class="pill {_status_class(s)}">{_esc(s)}</span>'


def _matrix_table(
    title: str, matrix: list[dict], products: list[str], origin_label: str
) -> str:
    if not matrix:
        return f"<section><h2>{_esc(title)}</h2><p class='muted'>No periods recorded.</p></section>"
    headers = "".join(f"<th>{_esc(p)}</th>" for p in products)
    rows = []
    for row in matrix:
        cells = "".join(
            f'<td><button type="button" class="cell {_status_class(row["cells"][p])}" '
            f'data-filter-year="{row["year"]}" data-filter-product="{_esc(p)}" '
            f'data-filter-origin="{_esc(origin_label)}" '
            f'title="{row["year"]} {_esc(p)}: {_esc(row["cells"][p])}">'
            f'{_esc(row["cells"][p])}</button></td>'
            for p in products
        )
        rows.append(f'<tr><th scope="row">{row["year"]}</th>{cells}</tr>')
    return f"""
    <section>
      <h2>{_esc(title)}</h2>
      <p class="muted">Click a cell to open Daily progress for that year/product and filter inventory. Origin: {_esc(origin_label)}. Lifecycle overview only — not day completeness.</p>
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
            f"<tr>"
            f"<td>{_esc(t['id'])}</td>"
            f"<td>{_esc(t['title'])}</td>"
            f"<td>{_pill(t.get('priority'))}</td>"
            f"<td>{_pill(t.get('status'))}</td>"
            f"<td>{_esc(t.get('owner') or 'UNKNOWN')}</td>"
            f"<td>{_esc(t.get('due_date') or 'NOT_RECORDED')}</td>"
            f"<td>{related_html}</td>"
            f"<td>{_esc(t.get('last_updated') or t.get('start_date') or 'UNKNOWN')}</td>"
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


def _day_calendar_html(product: str, block: dict, months: list[dict]) -> str:
    by_month: dict[int, list[dict]] = {m: [] for m in range(1, 13)}
    for day in block.get("days") or []:
        by_month[int(day["month"])].append(day)
    rows = []
    for mmeta in months:
        m = mmeta["num"]
        cells = []
        for day in by_month.get(m) or []:
            st = day["state"]
            cells.append(
                f'<button type="button" class="day day-{_esc(st.lower())}" '
                f'title="{_esc(day["iso"])} {_esc(product)}: {_esc(st)}" '
                f'aria-label="{_esc(day["iso"])} {_esc(product)} {_esc(st)}">'
                f'<span class="day-num" aria-hidden="true">{day["day"]}</span>'
                f'<span class="day-glyph" aria-hidden="true">{_glyph(st)}</span>'
                f"</button>"
            )
        # pad to days_in_month if incomplete list
        while len(cells) < int(mmeta["days_in_month"]):
            cells.append('<span class="day day-pad" aria-hidden="true"></span>')
        rows.append(
            f'<div class="cal-row">'
            f'<div class="cal-month" id="cal-{_esc(product)}-m{m}">{_esc(mmeta["name"])}</div>'
            f'<div class="cal-days" role="group" aria-label="{_esc(product)} {_esc(mmeta["name"])}">'
            f'{"".join(cells)}</div></div>'
        )
    pc = block.get("present_count", 0)
    mc = block.get("missing_count", 0)
    oc = block.get("out_count", 0)
    ec = block.get("expected_count", 0)
    return (
        f'<article class="product-cal" data-product="{_esc(product)}">'
        f"<h3>{_esc(product)}</h3>"
        f'<p class="muted">PRESENT {pc} · MISSING {mc} · OUT_OF_SPAN {oc} · expected {ec}</p>'
        f'{"".join(rows)}</article>'
    )


def _day_progress_section(catalog: dict) -> str:
    dc = catalog.get("day_coverage")
    if not dc:
        return (
            '<section id="daily-progress">'
            "<h2>Daily inventory coverage</h2>"
            '<p class="muted">No day_presence_*.json loaded — calendar unavailable.</p>'
            "</section>"
        )
    year = dc["year"]
    cls = dc["streams"]["cls_brazil"]
    internal = dc["streams"]["internal"]
    months = dc["months"]
    products = dc["products"]

    cls_cals = "".join(
        _day_calendar_html(p, cls["products"][p], months) for p in products
    )
    int_cals = "".join(
        _day_calendar_html(p, internal["products"][p], months) for p in products
    )

    cls_all = cls["all_required"]
    int_all = internal["all_required"]
    # Next missing day for CLS all-required (first MISSING or after last PRESENT)
    next_missing = "UNKNOWN"
    for day in cls_all["days"]:
        if day["state"] == "MISSING":
            next_missing = day["iso"]
            break
    else:
        for day in cls_all["days"]:
            if day["state"] == "OUT_OF_SPAN":
                next_missing = day["iso"]
                break

    year_opts = "".join(
        f'<option value="{y}"{" selected" if y == year else ""}>{y}</option>'
        for y in dc.get("available_years") or [year]
    )

    # Compact fallback table: non-OUT CLS days for first product ocean2d (via alias span)
    table_rows = []
    for p in products:
        for day in cls["products"][p]["days"]:
            if day["state"] == "OUT_OF_SPAN":
                continue
            table_rows.append(
                f"<tr data-stream=\"cls_brazil\" data-product=\"{_esc(p)}\">"
                f"<td>{_esc(day['iso'])}</td><td>CLS_HISTORICAL</td>"
                f"<td>{_esc(p)}</td><td>{_esc(day['state'])}</td></tr>"
            )
            if len(table_rows) >= 200:
                break
        if len(table_rows) >= 200:
            break

    return f"""
    <div class="sticky-bar" id="day-controls" role="region" aria-label="Daily progress controls">
      <label>Year <select id="day-year" disabled title="Additional years require day_presence_YYYY.json">{year_opts}</select></label>
      <label>Stream <select id="day-stream">
        <option value="cls_brazil">CLS historical</option>
        <option value="internal">Internal hindcast</option>
      </select></label>
      <label>Product <select id="day-product">
        <option value="all">All required</option>
        {"".join(f'<option value="{_esc(p)}">{_esc(p)}</option>' for p in products)}
      </select></label>
      <span class="muted">basis: {_esc(dc.get("basis") or "unknown")} · scan {_esc(dc.get("scan_date") or "UNKNOWN")}</span>
    </div>

    <section id="daily-progress">
      <h2>Daily inventory coverage</h2>
      <p class="banner-inline">{_esc(dc.get("disclaimer"))}</p>
      <div class="cards kpi-strip" id="day-kpi">
        <div class="card"><div class="label">CLS all-4 PRESENT</div>
          <div class="stat">{cls_all["present_count"]}/{cls_all["expected_count"]}</div>
          <div class="muted">inventory only</div></div>
        <div class="card"><div class="label">Internal all-4 PRESENT</div>
          <div class="stat">{int_all["present_count"]}/{int_all["expected_count"]}</div>
          <div class="muted">inventory only</div></div>
        <div class="card"><div class="label">Year</div>
          <div class="stat">{year}</div>
          <div class="muted">calendar days</div></div>
        <div class="card"><div class="label">Next CLS gap day</div>
          <div class="stat" style="font-size:1.1rem">{_esc(next_missing)}</div>
          <div class="muted">first MISSING/OUT</div></div>
      </div>
      <div class="legend" aria-label="Day state legend">
        <span class="leg PRESENT"><span class="swatch" aria-hidden="true">✓</span> PRESENT</span>
        <span class="leg MISSING"><span class="swatch" aria-hidden="true">·</span> MISSING</span>
        <span class="leg OUT_OF_SPAN"><span class="swatch" aria-hidden="true">–</span> OUT_OF_SPAN</span>
        <span class="leg PARTIAL"><span class="swatch" aria-hidden="true">~</span> PARTIAL</span>
      </div>
      <div id="cal-cls" class="cal-stack" data-stream="cls_brazil">{cls_cals}</div>
      <div id="cal-internal" class="cal-stack" data-stream="internal" hidden>{int_cals}</div>
      <details class="a11y-table">
        <summary>Accessible day table (CLS non–OUT_OF_SPAN sample, max 200 rows)</summary>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Date</th><th>Stream</th><th>Product</th><th>State</th></tr></thead>
            <tbody>{"".join(table_rows) or '<tr><td colspan="4">None</td></tr>'}</tbody>
          </table>
        </div>
      </details>
    </section>
    """


def render(store: TrackingStore, progress: dict, catalog: dict | None = None) -> str:
    catalog = catalog or build_catalog_view(store)
    summary = catalog["summary"]
    products = summary["matrix_products"]

    # Secondary operational bits (collapsed)
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

    overall = (
        "NOT CONFIRMED — overall % suppressed"
        if not progress["scope_confirmed"]
        else _esc(progress["overall_percent"])
    )

    # Inventory rows + embedded JSON for client filter
    inv_rows = []
    detail_blocks = []
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
            f'<td>{_esc(ds["period_start"] or "UNKNOWN")} → {_esc(ds["period_end"] or "UNKNOWN")}</td>'
            f'<td>{_pill(ds["lifecycle"])}</td>'
            f'<td>{_esc(ds["created_at"])}</td>'
            f'<td>{_esc(ds["catalogued_at"])}</td>'
            f'<td>{_esc(ds["verified_at"])}</td>'
            f'<td>{_esc(ds["file_count"] if ds["file_count"] is not None else "UNKNOWN")}</td>'
            f'<td>{_esc(ds["size_human"])}</td>'
            f'<td>{_esc(ds["owner"])}</td>'
            f'<td>{ds["todo_count"]}</td>'
            "</tr>"
        )

        todo_list = "".join(
            f'<li><a href="#todo-{_esc(t["id"])}">{_esc(t["id"])}</a>: '
            f'{_esc(t["title"])} {_pill(t["status"])}</li>'
            for t in ds["todos"]
        ) or "<li>No linked TODOs</li>"

        timeline = "".join(
            f"<li><strong>{_esc(ev['when'])}</strong> — {_esc(ev['label'])}: {_esc(ev['detail'])}</li>"
            for ev in ds["timeline"]
        ) or "<li>No recorded events</li>"

        detail_blocks.append(
            f"""
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
                <li><span>Period</span><span>{_esc(ds['period_start'] or 'UNKNOWN')} → {_esc(ds['period_end'] or 'UNKNOWN')} ({_esc(ds['period_basis'] or 'unknown')})</span></li>
                <li><span>Description</span><span>{_esc(ds['description'] or ds['notes'] or '—')}</span></li>
              </ul>
            </div>
            <div>
              <h4>Inventory</h4>
              <ul class="kv">
                <li><span>Path</span><span><code>{_esc(ds['location'])}</code></span></li>
                <li><span>Files</span><span>{_esc(ds['file_count'] if ds['file_count'] is not None else 'UNKNOWN')}</span></li>
                <li><span>Size</span><span>{_esc(ds['size_human'])}</span></li>
                <li><span>Manifest</span><span>{_esc(ds['manifest_ref'] or 'NOT_RECORDED')}</span></li>
                <li><span>Checksum</span><span>{_esc(ds['checksum_ref'] or 'NOT_RECORDED')}</span></li>
                <li><span>Last scan</span><span>{_esc(ds['last_inventory_scan'])}</span></li>
              </ul>
            </div>
            <div>
              <h4>Lifecycle</h4>
              <ul class="kv">
                <li><span>Status</span><span>{_pill(ds['lifecycle'])}</span></li>
                <li><span>Created</span><span>{_esc(ds['created_at'])} <span class="muted">({_esc(ds['created_at_provenance'])})</span></span></li>
                <li><span>Catalogued</span><span>{_esc(ds['catalogued_at'])}</span></li>
                <li><span>Verified</span><span>{_esc(ds['verified_at'])}</span></li>
                <li><span>Accepted</span><span>{_esc(ds['accepted_at'])}</span></li>
                <li><span>Integrity</span><span>{_pill(ds['integrity_status'])}</span></li>
                <li><span>Validation</span><span>{_pill(ds['validation_status'])}</span></li>
              </ul>
            </div>
            <div>
              <h4>Work tracking</h4>
              <ul class="kv">
                <li><span>Owner</span><span>{_esc(ds['owner'])}</span></li>
                <li><span>Open TODOs</span><span>{ds['todo_count']}</span></li>
              </ul>
              <ul>{todo_list}</ul>
            </div>
          </div>
          <h4>Timeline</h4>
          <ol class="timeline">{timeline}</ol>
        </details>
            """
        )

    todo_groups = catalog["todo_groups"]
    group_sections = []
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
        if not tasks and key in {"overdue", "due_soon", "other"}:
            continue
        group_sections.append(
            f"<h3 id='todos-{key}'>{_esc(label)} ({len(tasks)})</h3>"
            f'<div class="table-wrap"><table>'
            f"<thead><tr><th>ID</th><th>Title</th><th>Priority</th><th>Status</th>"
            f"<th>Owner</th><th>Due</th><th>Datasets</th><th>Updated</th></tr></thead>"
            f"<tbody>{_todo_rows(tasks)}</tbody></table></div>"
        )

    # Anchor ids for todos
    todo_anchors = "".join(
        f'<div id="todo-{_esc(t["id"])}" hidden></div>' for t in catalog["all_todos"]
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
    owner_opts = "".join(
        f'<option value="{_esc(o)}">{_esc(o)}</option>'
        for o in sorted({d["owner"] for d in catalog["datasets"]})
    )

    day_section = _day_progress_section(catalog)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>INACAWO Dataset Catalog Progress</title>
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
      --card: var(--surface);
      --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
      --cell: 15px;
      --header-h: 56px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.45;
      scroll-padding-top: calc(var(--header-h) + 48px);
    }}
    header {{
      padding: var(--space-3) var(--space-4);
      border-bottom: 1px solid var(--line);
      background: var(--surface);
    }}
    h1 {{ margin: 0 0 var(--space-1); font-size: 1.35rem; }}
    .banner {{
      display: inline-block; margin-top: var(--space-2); padding: 0.25rem 0.55rem;
      border-radius: 0.25rem; font-weight: 650; background: #fff3cd; color: var(--warn);
      border: 1px solid #f0d48a; font-size: 0.85rem;
    }}
    .banner-inline {{
      margin: 0 0 var(--space-3); padding: var(--space-2) var(--space-3);
      background: #eef6fb; border: 1px solid #b7d4e8; border-radius: 0.25rem;
      color: var(--run); font-size: 0.86rem;
    }}
    .sticky-bar {{
      position: sticky; top: 0; z-index: 20;
      display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: end;
      padding: var(--space-2) var(--space-4);
      background: rgba(244,246,248,0.96); border-bottom: 1px solid var(--line);
      backdrop-filter: blur(4px);
    }}
    .sticky-bar label {{
      display: flex; flex-direction: column; gap: 2px;
      font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.03em;
    }}
    .sticky-bar select {{
      min-height: 36px; padding: 0.3rem 0.45rem; border: 1px solid var(--line);
      border-radius: 0.25rem; font: inherit; background: #fff; color: var(--ink); cursor: pointer;
    }}
    .sticky-bar select:focus, button:focus-visible, a:focus-visible, .filters input:focus, .filters select:focus {{
      outline: 2px solid var(--focus); outline-offset: 2px;
    }}
    main {{ padding: var(--space-3) var(--space-4) 2.5rem; display: grid; gap: var(--space-3); max-width: 1480px; }}
    .cards {{ display: grid; gap: var(--space-2); grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); }}
    .kpi-strip .stat {{ font-size: 1.35rem; }}
    .card {{
      background: var(--surface); border: 1px solid var(--line); border-radius: 0.35rem;
      padding: var(--space-2) var(--space-3);
    }}
    .card .stat {{ font-size: 1.45rem; font-weight: 700; }}
    .card .label {{ font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.03em; }}
    section {{
      background: var(--surface); border: 1px solid var(--line); border-radius: 0.35rem;
      padding: var(--space-3);
    }}
    section.compact {{ padding: var(--space-2) var(--space-3); }}
    h2 {{ margin: 0 0 var(--space-2); font-size: 1.02rem; }}
    h3 {{ margin: 0 0 var(--space-1); font-size: 0.92rem; }}
    h4 {{ margin: 0.35rem 0; font-size: 0.84rem; }}
    .muted {{ color: var(--muted); font-size: 0.86rem; }}
    .sub {{ font-size: 0.76rem; color: var(--muted); }}
    .legend {{ display: flex; flex-wrap: wrap; gap: var(--space-3); margin: 0 0 var(--space-3); font-size: 0.82rem; }}
    .leg {{ display: inline-flex; align-items: center; gap: 0.35rem; }}
    .leg .swatch {{
      display: inline-flex; width: 1.25rem; height: 1.25rem; align-items: center; justify-content: center;
      border: 1px solid var(--line); border-radius: 0.2rem; font-size: 0.75rem; font-weight: 700;
    }}
    .leg.PRESENT .swatch {{ background: #e6f5ee; color: var(--present); border-color: #8fc9ad; }}
    .leg.MISSING .swatch {{ background: #fdecee; color: var(--missing); border-color: #e3a4ad; }}
    .leg.OUT_OF_SPAN .swatch {{ background: var(--out); color: var(--muted); }}
    .leg.PARTIAL .swatch {{ background: #fff6d6; color: var(--ready); }}
    .cal-stack {{ display: grid; gap: var(--space-3); }}
    .product-cal {{ border: 1px solid var(--line); border-radius: 0.3rem; padding: var(--space-2); }}
    .cal-row {{ display: grid; grid-template-columns: 2.6rem 1fr; gap: var(--space-1); align-items: start; margin-bottom: 2px; }}
    .cal-month {{ font-size: 0.72rem; font-weight: 650; color: var(--muted); padding-top: 2px; }}
    .cal-days {{
      display: grid; grid-template-columns: repeat(31, minmax(var(--cell), 1fr));
      gap: 2px; overflow-x: auto;
    }}
    button.day {{
      min-width: var(--cell); min-height: calc(var(--cell) + 4px);
      padding: 0; border: 1px solid var(--line); border-radius: 2px;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      cursor: pointer; font: inherit; line-height: 1; background: #f7f9fb; color: var(--ink);
      transition: background 180ms ease, border-color 180ms ease;
    }}
    button.day .day-num {{ font-size: 0.58rem; color: var(--muted); }}
    button.day .day-glyph {{ font-size: 0.7rem; font-weight: 700; }}
    button.day-present {{ background: #e6f5ee; border-color: #8fc9ad; color: var(--present); }}
    button.day-missing {{ background: #fdecee; border-color: #e3a4ad; color: var(--missing); }}
    button.day-out_of_span {{ background: var(--out); color: var(--muted); }}
    button.day-partial {{ background: #fff6d6; border-color: #e2d48a; color: var(--ready); }}
    .day-pad {{ min-height: calc(var(--cell) + 4px); }}
    @media (prefers-reduced-motion: reduce) {{
      button.day {{ transition: none; }}
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
    details.secondary {{ margin-top: 0.2rem; }}
    footer {{ padding: 0 var(--space-4) var(--space-4); color: var(--muted); font-size: 0.8rem; max-width: 1480px; }}
    code {{ font-size: 0.78rem; }}
    a {{ color: var(--run); }}
    #inv-count {{ font-size: 0.84rem; color: var(--muted); margin: 0.2rem 0 0.45rem; }}
    @media (max-width: 768px) {{
      :root {{ --cell: 18px; }}
      main {{ padding: var(--space-2); }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>INACAWO Dataset Catalog Progress</h1>
    <div class="muted">Generated {_esc(progress['generated_at'])} · source of truth: data/*.yaml</div>
    <div class="banner">Scope: {_esc(progress['scope_label'])}</div>
    <p class="muted" style="margin:0.45rem 0 0">
      Overall acceptance: <strong>{overall}</strong>
      — catalog counts are evidence-based; daily panel is inventory coverage only.
    </p>
  </header>
  {day_section}
  <main>
    <section>
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
      <p class="muted" style="margin-top:0.65rem">
        Origins: {_esc(json.dumps(summary['by_origin']))}
        · Products: {_esc(json.dumps(summary['by_product']))}
        · Lifecycles: {_esc(json.dumps(summary['lifecycle_counts']))}
      </p>
    </section>

    {_matrix_table("Year × product — CLS historical (lifecycle overview)", catalog["historical_matrix"], products, "CLS_HISTORICAL")}
    {_matrix_table("Year × product — Internal hindcast (lifecycle overview)", catalog["remaining_matrix"], products, "INTERNAL_HINDCAST")}

    <section>
      <h2>Dataset inventory</h2>
      <div class="filters" id="inv-filters">
        <label>Search<input type="search" id="f-search" placeholder="id, name, product…"/></label>
        <label>Origin<select id="f-origin"><option value="">All</option>{origin_opts}</select></label>
        <label>Product<select id="f-product"><option value="">All</option>{product_opts}</select></label>
        <label>Lifecycle<select id="f-life"><option value="">All</option>{life_opts}</select></label>
        <label>Owner<select id="f-owner"><option value="">All</option>{owner_opts}</select></label>
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
      <div id="inv-count"></div>
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

    <section>
      <h2>TODO / action tracker</h2>
      <p class="muted">Due dates shown only when explicitly recorded. Owners are member IDs from data/team.yaml — never invented names.</p>
      {''.join(group_sections)}
      {todo_anchors}
    </section>

    <section>
      <h2>Dataset details</h2>
      <p class="muted">Expand a dataset for inventory, lifecycle timeline, evidence fields, and linked TODOs.</p>
      {''.join(detail_blocks)}
    </section>

    <section>
      <h2>Metric definitions</h2>
      <ul>{defs_html}</ul>
      <p class="muted">
        Creation, catalog registration, inventory completeness, integrity verification,
        scientific validation, and human acceptance are separate stages and are never
        collapsed into one misleading percentage while scope is provisional.
      </p>
    </section>

    <details class="secondary">
      <summary><strong>Secondary project information</strong> (workflow, issues, HPC, workload)</summary>
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
    Evidence-based catalog tracking · UNKNOWN / NOT_RECORDED means not assumed complete ·
    regenerate with <code>python dashboard/generate.py</code>
  </footer>
  <script>
  (function () {{
    const tbody = document.querySelector('#inv-table tbody');
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('tr'));
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
      const q = (els.search.value || '').trim().toLowerCase();
      const origin = els.origin.value;
      const product = els.product.value;
      const life = els.life.value;
      const owner = els.owner.value;
      const year = els.year.value ? parseInt(els.year.value, 10) : null;
      const todos = els.todos.value;
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
      countEl.textContent = visible + ' of ' + rows.length + ' datasets shown';

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

    Object.keys(els).forEach(function (k) {{
      if (k === 'reset') return;
      els[k].addEventListener('input', apply);
      els[k].addEventListener('change', apply);
    }});
    els.reset.addEventListener('click', function () {{
      els.search.value = '';
      els.origin.value = '';
      els.product.value = '';
      els.life.value = '';
      els.owner.value = '';
      els.year.value = '';
      els.todos.value = '';
      els.sort.value = 'id';
      apply();
    }});

    document.querySelectorAll('button.cell').forEach(function (btn) {{
      btn.addEventListener('click', function () {{
        const product = btn.getAttribute('data-filter-product') || '';
        const year = btn.getAttribute('data-filter-year') || '';
        const originLabel = btn.getAttribute('data-filter-origin') || '';
        els.product.value = product;
        els.year.value = year;
        if (originLabel === 'CLS_HISTORICAL') els.origin.value = 'cls_brazil';
        else if (originLabel === 'INTERNAL_HINDCAST') els.origin.value = 'internal';
        else els.origin.value = '';
        apply();
        const dayStream = document.getElementById('day-stream');
        const dayProduct = document.getElementById('day-product');
        if (dayStream) {{
          dayStream.value = originLabel === 'INTERNAL_HINDCAST' ? 'internal' : 'cls_brazil';
          dayStream.dispatchEvent(new Event('change'));
        }}
        if (dayProduct && product) {{
          dayProduct.value = product;
          dayProduct.dispatchEvent(new Event('change'));
        }}
        const daily = document.getElementById('daily-progress');
        if (daily) daily.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        else document.getElementById('inv-table').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }});
    }});

    apply();

    const dayStream = document.getElementById('day-stream');
    const dayProduct = document.getElementById('day-product');
    const calCls = document.getElementById('cal-cls');
    const calInt = document.getElementById('cal-internal');
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
    if (dayStream) dayStream.addEventListener('change', applyDayFilters);
    if (dayProduct) dayProduct.addEventListener('change', applyDayFilters);
    applyDayFilters();
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
