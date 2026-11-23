#!/usr/bin/env python3
"""Generate a static HTML dashboard from tracking data."""

from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.tracking import TrackingStore, compute_progress  # noqa: E402


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _status_class(status: str) -> str:
    mapping = {
        "COMPLETED": "ok",
        "ACCEPTED": "ok",
        "VERIFIED": "ok",
        "RUNNING": "run",
        "READY": "ready",
        "FAILED": "bad",
        "FAILED_VALIDATION": "bad",
        "BLOCKED": "bad",
        "OPEN": "bad",
        "CANCELLED": "muted",
        "NOT_STARTED": "muted",
        "UNKNOWN": "unk",
        "NOT_VERIFIED": "unk",
        "NOT_VALIDATED": "unk",
        "PROVISIONAL / NOT CONFIRMED": "warn",
    }
    return mapping.get(status, "unk")


def render(store: TrackingStore, progress: dict) -> str:
    rem = sorted(
        [p for p in store.periods if p["stream"] == "remaining_internal"],
        key=lambda p: p["calendar_year"],
    )
    hist = sorted(
        [p for p in store.periods if p["stream"] == "historical_baseline"],
        key=lambda p: p["calendar_year"],
    )

    year_cells = []
    for p in rem:
        st = p["execution_status"]
        year_cells.append(
            f'<div class="year {_status_class(st)}" title="'
            f'exec={_esc(st)} sci={_esc(p["scientific_status"])} '
            f'complete={_esc(p["fully_complete"])}">'
            f'<strong>{p["calendar_year"]}</strong>'
            f'<span>{_esc(st)}</span>'
            f'<span class="sub">{_esc(p["fully_complete"])}</span>'
            f"</div>"
        )

    hist_cells = []
    for p in hist:
        st = p["execution_status"]
        hist_cells.append(
            f'<div class="year {_status_class(st)}" title="historical {_esc(st)}">'
            f'<strong>{p["calendar_year"]}</strong>'
            f'<span>{_esc(st)}</span></div>'
        )

    stage_rows = "".join(
        f"<tr><td>{_esc(s['order'])}</td><td>{_esc(s['name'])}</td>"
        f'<td><span class="pill {_status_class(s["status"])}">{_esc(s["status"])}</span></td>'
        f"<td>{_esc(s.get('notes'))}</td></tr>"
        for s in progress["workflow_stages"]
    )

    issue_rows = "".join(
        f"<tr><td>{_esc(i['id'])}</td><td>{_esc(i['title'])}</td>"
        f"<td>{_esc(i['severity'])}</td><td>{_esc(i['status'])}</td>"
        f"<td>{_esc(i.get('owner'))}</td></tr>"
        for i in progress["open_issues"]
    ) or '<tr><td colspan="5">None recorded</td></tr>'

    metric_rows = "".join(
        f"<tr><td>{_esc(name)}</td><td>{m['matched']}/{m['total']}</td>"
        f"<td>{_esc(m['percent_display'])}</td><td>{_esc(m.get('note'))}</td></tr>"
        for name, m in progress["metrics"].items()
    )

    workload_rows = "".join(
        f"<tr><td>{_esc(mid)}</td><td>{count}</td></tr>"
        for mid, count in progress["workload"].items()
    )

    snap = progress["latest_hpc_snapshot"]
    if snap:
        snap_html = (
            f"<p><strong>{_esc(snap['id'])}</strong> collected "
            f"{_esc(snap['collected_at'])} ({_esc(snap['mode'])}) — "
            f"{len(snap.get('jobs', []))} queue job(s). "
            "Treat as stale if older than operational expectation.</p>"
        )
    else:
        snap_html = "<p class=\"unk\">NONE — no HPC snapshot recorded.</p>"

    overall = (
        "NOT CONFIRMED — overall % suppressed"
        if not progress["scope_confirmed"]
        else _esc(progress["overall_percent"])
    )

    rem_claim = progress["provisional_remaining"] or {}
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>INACAWO Hindcast Progress</title>
  <style>
    :root {{
      --bg: #f4f7fb;
      --ink: #142033;
      --card: #ffffff;
      --line: #d7e0ea;
      --ok: #1b7f4a;
      --run: #0b6e99;
      --ready: #6a5a00;
      --bad: #a11b2b;
      --unk: #5c6775;
      --warn: #9a6700;
      --muted: #7a8694;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--ink); background:
        radial-gradient(circle at top left, #e7eef8, transparent 40%),
        linear-gradient(180deg, #eef3f8, var(--bg));
    }}
    header {{
      padding: 1.5rem 1.75rem 1rem; border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,0.85); backdrop-filter: blur(6px);
    }}
    h1 {{ margin: 0 0 0.35rem; font-size: 1.55rem; }}
    .banner {{
      display: inline-block; margin-top: 0.5rem; padding: 0.35rem 0.7rem;
      border-radius: 0.35rem; font-weight: 600; background: #fff3cd; color: var(--warn);
      border: 1px solid #f0d48a;
    }}
    main {{ padding: 1.25rem 1.75rem 2.5rem; display: grid; gap: 1rem; }}
    .grid {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }}
    section {{
      background: var(--card); border: 1px solid var(--line); border-radius: 0.75rem;
      padding: 1rem 1.1rem; box-shadow: 0 1px 0 rgba(20,32,51,0.03);
    }}
    h2 {{ margin: 0 0 0.75rem; font-size: 1.05rem; }}
    .stat {{ font-size: 1.6rem; font-weight: 700; }}
    .muted {{ color: var(--muted); font-size: 0.9rem; }}
    .years {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(88px, 1fr)); gap: 0.5rem; }}
    .year {{
      border: 1px solid var(--line); border-radius: 0.5rem; padding: 0.45rem;
      display: flex; flex-direction: column; gap: 0.15rem; background: #fbfcfe;
    }}
    .year span {{ font-size: 0.72rem; color: var(--muted); }}
    .year .sub {{ font-size: 0.68rem; }}
    .year.ok {{ border-color: #9fd6b5; background: #eef9f2; }}
    .year.run {{ border-color: #9dcee6; background: #eef7fb; }}
    .year.ready {{ border-color: #e2d48a; background: #fffbeb; }}
    .year.bad {{ border-color: #e3a4ad; background: #fff1f3; }}
    .year.unk, .year.muted {{ border-color: #d5dde6; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
    th, td {{ text-align: left; padding: 0.4rem 0.35rem; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; }}
    .pill {{ padding: 0.1rem 0.45rem; border-radius: 999px; font-size: 0.78rem; background: #eef2f6; }}
    .pill.ok {{ background: #dff3e8; color: var(--ok); }}
    .pill.run {{ background: #dff0f8; color: var(--run); }}
    .pill.bad {{ background: #fde4e8; color: var(--bad); }}
    .pill.unk {{ background: #eef1f4; color: var(--unk); }}
    .pill.warn {{ background: #fff3cd; color: var(--warn); }}
    footer {{ padding: 0 1.75rem 1.5rem; color: var(--muted); font-size: 0.85rem; }}
  </style>
</head>
<body>
  <header>
    <h1>INACAWO Hindcast Progress</h1>
    <div class="muted">Generated {_esc(progress['generated_at'])} · source of truth: data/*.yaml</div>
    <div class="banner">Scope: {_esc(progress['scope_label'])}</div>
  </header>
  <main>
    <div class="grid">
      <section>
        <h2>Overall acceptance</h2>
        <div class="stat">{overall}</div>
        <p class="muted">Uses fully-complete years only when scope is confirmed. Never task-count based.</p>
      </section>
      <section>
        <h2>Provisional remaining window</h2>
        <div class="stat" style="font-size:1.1rem">{_esc(rem_claim.get('start'))} → {_esc(rem_claim.get('end'))}</div>
        <p class="muted">See OPEN_QUESTIONS.md Q1 before treating as final.</p>
      </section>
      <section>
        <h2>Open blockers</h2>
        <div class="stat">{len(progress['open_issues'])}</div>
        <p class="muted">Issues in OPEN / IN_PROGRESS / BLOCKED.</p>
      </section>
      <section>
        <h2>Active HPC runs (tracked)</h2>
        <div class="stat">{len(progress['active_runs'])}</div>
        <p class="muted">From data/runs only — not live SLURM unless snapshotted.</p>
      </section>
    </div>

    <section>
      <h2>Remaining years (provisional)</h2>
      <div class="years">{''.join(year_cells)}</div>
      <p class="muted">Colors reflect execution_status. fully_complete shown as subtitle.</p>
    </section>

    <section>
      <h2>Historical baseline years (inventory status)</h2>
      <div class="years">{''.join(hist_cells)}</div>
      <p class="muted">Not mixed into remaining acceptance % until owner accepts baseline rules.</p>
    </section>

    <section>
      <h2>Progress metrics</h2>
      <table>
        <thead><tr><th>Metric</th><th>Matched/Total</th><th>Display %</th><th>Note</th></tr></thead>
        <tbody>{metric_rows}</tbody>
      </table>
    </section>

    <section>
      <h2>Workflow stages</h2>
      <table>
        <thead><tr><th>#</th><th>Stage</th><th>Status</th><th>Notes</th></tr></thead>
        <tbody>{stage_rows}</tbody>
      </table>
    </section>

    <section>
      <h2>Outstanding issues</h2>
      <table>
        <thead><tr><th>ID</th><th>Title</th><th>Severity</th><th>Status</th><th>Owner</th></tr></thead>
        <tbody>{issue_rows}</tbody>
      </table>
    </section>

    <div class="grid">
      <section>
        <h2>Team workload</h2>
        <table>
          <thead><tr><th>Member</th><th>Open/active items</th></tr></thead>
          <tbody>{workload_rows}</tbody>
        </table>
      </section>
      <section>
        <h2>HPC snapshot</h2>
        {snap_html}
      </section>
    </div>
  </main>
  <footer>
    Evidence-based tracking · UNKNOWN/NOT_VERIFIED means not assumed complete ·
    regenerate with <code>python dashboard/generate.py</code>
  </footer>
</body>
</html>
"""


def main() -> int:
    store = TrackingStore.load(ROOT)
    progress = compute_progress(store)
    out_dir = ROOT / "dashboard" / "public"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "index.html"
    path.write_text(render(store, progress), encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
