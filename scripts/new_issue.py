#!/usr/bin/env python3
"""Create a new issue/blocker YAML stub."""

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
    parser.add_argument("--severity", default="MEDIUM")
    parser.add_argument("--owner", default=None)
    parser.add_argument("--description", default="")
    args = parser.parse_args()

    if not args.id.startswith("issue_"):
        print("id must start with issue_", file=sys.stderr)
        return 2

    path = ROOT / "data" / "issues" / f"{args.id}.yaml"
    if path.exists():
        print(f"Refusing to overwrite {path}", file=sys.stderr)
        return 1

    doc = {
        "id": args.id,
        "title": args.title,
        "description": args.description,
        "severity": args.severity,
        "impact": None,
        "owner": args.owner,
        "status": "OPEN",
        "resolution": None,
        "related_task_ids": [],
        "related_run_ids": [],
        "related_period_ids": [],
        "evidence": [],
        "notes": None,
    }
    path.write_text(dump_yaml(doc), encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
