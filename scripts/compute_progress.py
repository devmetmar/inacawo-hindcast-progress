#!/usr/bin/env python3
"""Compute evidence-based progress metrics from tracking data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.tracking import TrackingStore, compute_progress  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    store = TrackingStore.load(args.root)
    progress = compute_progress(store)

    if args.json:
        print(json.dumps(progress, indent=2, default=str))
        return 0

    print(f"Generated: {progress['generated_at']}")
    print(f"Scope: {progress['scope_label']}")
    if not progress["scope_confirmed"]:
        rem = progress["provisional_remaining"]
        print(
            f"Provisional remaining: {rem['start']} .. {rem['end']} "
            "(overall % suppressed)"
        )
    else:
        print(f"Overall acceptance %: {progress['overall_percent']}")

    print("\nRemaining execution buckets:")
    for status, years in progress["remaining_execution_buckets"].items():
        if years:
            print(f"  {status}: {len(years)} -> {years}")

    print("\nMetrics (remaining stream):")
    for name, metric in progress["metrics"].items():
        pct = metric["percent_display"]
        print(
            f"  {name}: {metric['matched']}/{metric['total']} "
            f"display={pct} note={metric.get('note')}"
        )

    print(f"\nOpen issues: {len(progress['open_issues'])}")
    for issue in progress["open_issues"]:
        print(f"  - {issue['id']}: {issue['title']} [{issue['severity']}/{issue['status']}]")

    print("\nTeam workload (open/active items):")
    for member_id, count in progress["workload"].items():
        print(f"  {member_id}: {count}")

    snap = progress["latest_hpc_snapshot"]
    if snap:
        print(f"\nLatest HPC snapshot: {snap['id']} at {snap['collected_at']}")
    else:
        print("\nLatest HPC snapshot: NONE")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
