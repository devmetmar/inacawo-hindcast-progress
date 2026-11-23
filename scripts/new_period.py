#!/usr/bin/env python3
"""Create a new simulation period YAML stub."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.tracking import dump_yaml  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument(
        "--stream",
        choices=["historical_baseline", "remaining_internal"],
        required=True,
    )
    parser.add_argument(
        "--scope-basis",
        choices=["confirmed", "provisional"],
        default="provisional",
    )
    parser.add_argument("--owner", default=None)
    args = parser.parse_args()

    period_id = f"period_{args.year}"
    path = ROOT / "data" / "periods" / f"{period_id}.yaml"
    if path.exists():
        print(f"Refusing to overwrite {path}", file=sys.stderr)
        return 1

    doc = {
        "id": period_id,
        "calendar_year": args.year,
        "start_date": f"{args.year}-01-01",
        "end_date": f"{args.year}-12-31",
        "stream": args.stream,
        "scope_basis": args.scope_basis,
        "execution_status": "NOT_STARTED"
        if args.stream == "remaining_internal"
        else "UNKNOWN",
        "scientific_status": "NOT_VALIDATED"
        if args.stream == "remaining_internal"
        else "UNKNOWN",
        "owner": args.owner,
        "reviewer": None,
        "configuration_id": None,
        "related_run_ids": [],
        "related_dataset_ids": [],
        "fully_complete": "NO" if args.stream == "remaining_internal" else "NOT_VERIFIED",
        "notes": None,
    }
    path.write_text(dump_yaml(doc), encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
