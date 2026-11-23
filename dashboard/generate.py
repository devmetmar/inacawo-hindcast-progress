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
      <p class="muted">Click a cell to filter the inventory. Origin: {_esc(origin_label)}.</p>
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

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>INACAWO Dataset Catalog Progress</title>
  <style>
    :root {{
      --bg: #f0f3f7;
      --ink: #142033;
      --card: #ffffff;
      --line: #d0d8e2;
      --ok: #1b7f4a;
      --run: #0b6e99;
      --ready: #6a5a00;
      --bad: #a11b2b;
      --unk: #5c6775;
      --warn: #9a6700;
      --muted: #6b7785;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #e8eef5, var(--bg));
      line-height: 1.45;
    }}
    header {{
      padding: 1.25rem 1.5rem 1rem;
      border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,0.92);
    }}
    h1 {{ margin: 0 0 0.25rem; font-size: 1.45rem; }}
    .banner {{
      display: inline-block; margin-top: 0.45rem; padding: 0.3rem 0.65rem;
      border-radius: 0.3rem; font-weight: 650; background: #fff3cd; color: var(--warn);
      border: 1px solid #f0d48a;
    }}
    main {{ padding: 1rem 1.5rem 2.5rem; display: grid; gap: 1rem; max-width: 1400px; }}
    .cards {{ display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }}
    .card {{
      background: var(--card); border: 1px solid var(--line); border-radius: 0.55rem;
      padding: 0.75rem 0.85rem;
    }}
    .card .stat {{ font-size: 1.55rem; font-weight: 700; }}
    .card .label {{ font-size: 0.78rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.03em; }}
    section {{
      background: var(--card); border: 1px solid var(--line); border-radius: 0.55rem;
      padding: 0.9rem 1rem;
    }}
    h2 {{ margin: 0 0 0.65rem; font-size: 1.05rem; }}
    h3 {{ margin: 1rem 0 0.4rem; font-size: 0.95rem; }}
    h4 {{ margin: 0.4rem 0; font-size: 0.88rem; }}
    .muted {{ color: var(--muted); font-size: 0.88rem; }}
    .sub {{ font-size: 0.78rem; color: var(--muted); }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.86rem; }}
    th, td {{ text-align: left; padding: 0.35rem 0.4rem; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; white-space: nowrap; }}
    .matrix th, .matrix td {{ text-align: center; }}
    .matrix th[scope="row"] {{ text-align: left; }}
    .pill {{
      display: inline-block; padding: 0.08rem 0.4rem; border-radius: 0.25rem;
      font-size: 0.72rem; font-weight: 600; background: #eef2f6; white-space: nowrap;
    }}
    .pill.ok {{ background: #dff3e8; color: var(--ok); }}
    .pill.run {{ background: #dff0f8; color: var(--run); }}
    .pill.ready {{ background: #fff6d6; color: var(--ready); }}
    .pill.bad {{ background: #fde4e8; color: var(--bad); }}
    .pill.unk {{ background: #eef1f4; color: var(--unk); }}
    .pill.warn {{ background: #fff3cd; color: var(--warn); }}
    .pill.muted {{ background: #eef1f4; color: var(--muted); }}
    button.cell {{
      border: 1px solid var(--line); border-radius: 0.25rem; padding: 0.25rem 0.35rem;
      font-size: 0.68rem; font-weight: 650; cursor: pointer; width: 100%;
      background: #f7f9fb; color: var(--ink);
    }}
    button.cell.ok {{ background: #eef9f2; border-color: #9fd6b5; color: var(--ok); }}
    button.cell.run {{ background: #eef7fb; border-color: #9dcee6; color: var(--run); }}
    button.cell.ready {{ background: #fffbeb; border-color: #e2d48a; color: var(--ready); }}
    button.cell.bad {{ background: #fff1f3; border-color: #e3a4ad; color: var(--bad); }}
    button.cell.warn {{ background: #fff8e8; border-color: #f0d48a; color: var(--warn); }}
    button.cell.unk, button.cell.muted {{ background: #f4f6f8; color: var(--muted); }}
    .filters {{
      display: grid; gap: 0.5rem;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      margin-bottom: 0.75rem; align-items: end;
    }}
    .filters label {{ display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.75rem; color: var(--muted); }}
    .filters input, .filters select {{
      padding: 0.35rem 0.45rem; border: 1px solid var(--line); border-radius: 0.3rem;
      font: inherit; color: var(--ink); background: #fff;
    }}
    .filters .actions {{ display: flex; gap: 0.4rem; }}
    .filters button {{
      padding: 0.35rem 0.65rem; border: 1px solid var(--line); border-radius: 0.3rem;
      background: #f4f7fb; cursor: pointer; font: inherit;
    }}
    .detail-grid {{
      display: grid; gap: 0.75rem;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      margin-top: 0.5rem;
    }}
    .kv {{ list-style: none; padding: 0; margin: 0; }}
    .kv li {{ display: grid; grid-template-columns: 7rem 1fr; gap: 0.35rem; padding: 0.15rem 0; font-size: 0.84rem; }}
    .kv li > span:first-child {{ color: var(--muted); }}
    .timeline {{ margin: 0.25rem 0 0; padding-left: 1.1rem; font-size: 0.84rem; }}
    details.dataset-detail {{
      border: 1px solid var(--line); border-radius: 0.4rem; padding: 0.45rem 0.65rem;
      margin: 0.4rem 0; background: #fbfcfe;
    }}
    details.dataset-detail > summary {{ cursor: pointer; }}
    details.secondary {{ margin-top: 0.25rem; }}
    footer {{ padding: 0 1.5rem 1.5rem; color: var(--muted); font-size: 0.82rem; max-width: 1400px; }}
    code {{ font-size: 0.8rem; }}
    a {{ color: var(--run); }}
    #inv-count {{ font-size: 0.85rem; color: var(--muted); margin: 0.25rem 0 0.5rem; }}
  </style>
</head>
<body>
  <header>
    <h1>INACAWO Dataset Catalog Progress</h1>
    <div class="muted">Generated {_esc(progress['generated_at'])} · source of truth: data/*.yaml</div>
    <div class="banner">Scope: {_esc(progress['scope_label'])}</div>
    <p class="muted" style="margin:0.5rem 0 0">
      Overall acceptance: <strong>{overall}</strong>
      — catalog counts below are evidence-based record counts, not a project completion percentage.
    </p>
  </header>
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
      <p class="muted" style="margin-top:0.75rem">
        Origins: {_esc(json.dumps(summary['by_origin']))}
        · Products: {_esc(json.dumps(summary['by_product']))}
        · Lifecycles: {_esc(json.dumps(summary['lifecycle_counts']))}
      </p>
    </section>

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

    {_matrix_table("Year × product — CLS historical", catalog["historical_matrix"], products, "CLS_HISTORICAL")}
    {_matrix_table("Year × product — Internal hindcast", catalog["remaining_matrix"], products, "INTERNAL_HINDCAST")}

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
        // Map origin label back to origin enum where possible
        if (originLabel === 'CLS_HISTORICAL') els.origin.value = 'cls_brazil';
        else if (originLabel === 'INTERNAL_HINDCAST') els.origin.value = 'internal';
        else els.origin.value = '';
        apply();
        document.getElementById('inv-table').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }});
    }});

    apply();
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
