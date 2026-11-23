#!/usr/bin/env python3
"""Append an activity log YAML entry."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.tracking import dump_yaml  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--entity-type", required=True)
    parser.add_argument("--entity-id", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--previous-state", default=None)
    parser.add_argument("--new-state", default=None)
    parser.add_argument("--evidence", default=None)
    parser.add_argument("--notes", default=None)
    args = parser.parse_args()

    now = datetime.now().astimezone()
    act_id = f"act_{now.strftime('%Y%m%d_%H%M%S')}"
    path = ROOT / "data" / "activity_log" / f"{act_id}.yaml"
    if path.exists():
        print(f"Refusing to overwrite {path}", file=sys.stderr)
        return 1

    doc = {
        "id": act_id,
        "timestamp": now.isoformat(timespec="seconds"),
        "actor": args.actor,
        "entity_type": args.entity_type,
        "entity_id": args.entity_id,
        "action": args.action,
        "previous_state": args.previous_state,
        "new_state": args.new_state,
        "evidence_reference": args.evidence,
        "notes": args.notes,
    }
    path.write_text(dump_yaml(doc), encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
