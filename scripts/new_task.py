#!/usr/bin/env python3
"""Create a new task YAML stub."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.tracking import dump_yaml  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--stage", required=True, help="workflow stage id")
    parser.add_argument("--owner", default=None)
    parser.add_argument("--priority", default="MEDIUM")
    parser.add_argument("--description", default="")
    args = parser.parse_args()

    if not args.id.startswith("task_"):
        print("id must start with task_", file=sys.stderr)
        return 2

    path = ROOT / "data" / "tasks" / f"{args.id}.yaml"
    if path.exists():
        print(f"Refusing to overwrite {path}", file=sys.stderr)
        return 1

    doc = {
        "id": args.id,
        "title": args.title,
        "description": args.description,
        "workflow_stage_id": args.stage,
        "priority": args.priority,
        "owner": args.owner,
        "reviewer": None,
        "status": "NOT_STARTED",
        "start_date": None,
        "due_date": None,
        "depends_on": [],
        "evidence": [],
        "completion_criteria": [],
        "notes": None,
    }
    path.write_text(dump_yaml(doc), encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
