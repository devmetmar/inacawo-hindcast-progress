#!/usr/bin/env python3
"""Create a new simulation run YAML stub."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.tracking import dump_yaml  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="run id, e.g. run_2015_a01")
    parser.add_argument("--period-id", required=True)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--owner", default=None)
    parser.add_argument("--job-id", default=None)
    args = parser.parse_args()

    if not args.id.startswith("run_"):
        print("id must start with run_", file=sys.stderr)
        return 2

    path = ROOT / "data" / "runs" / f"{args.id}.yaml"
    if path.exists():
        print(f"Refusing to overwrite {path}", file=sys.stderr)
        return 1

    doc = {
        "id": args.id,
        "period_id": args.period_id,
        "attempt_number": args.attempt,
        "simulation_start": args.start,
        "simulation_end": args.end,
        "owner": args.owner,
        "configuration_id": None,
        "hpc_user": "cawohdcst_ft2",
        "partition": None,
        "job_id": args.job_id,
        "submission_time": None,
        "execution_start_time": None,
        "execution_end_time": None,
        "execution_status": "NOT_STARTED",
        "exit_code": None,
        "log_locations": [],
        "restart_checkpoint": None,
        "failure_info": None,
        "retry_of": None,
        "source_revisions": {
            "inacawo_iht": None,
            "inacawo_src": None,
            "inacawo_deps": None,
            "coawst_tarball_sha256": None,
        },
        "input_dataset_ids": [],
        "output_dataset_ids": [],
        "validation_status": "NOT_VALIDATED",
        "evidence": [],
        "notes": None,
    }
    path.write_text(dump_yaml(doc), encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
