#!/usr/bin/env python3
"""Validate tracking YAML against schemas and referential integrity rules."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.tracking import TrackingStore, validate_store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root (default: this repo)",
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Treat warnings as errors",
    )
    args = parser.parse_args()

    store = TrackingStore.load(args.root)
    issues = validate_store(store, args.root)
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    for issue in issues:
        print(f"[{issue.level.upper()}] {issue.message}")

    print(
        f"Checked project={store.project.get('id')} "
        f"periods={len(store.periods)} runs={len(store.runs)} "
        f"datasets={len(store.datasets)} tasks={len(store.tasks)} "
        f"issues={len(store.issues)} validations={len(store.validations)}"
    )
    print(f"Summary: {len(errors)} error(s), {len(warnings)} warning(s)")

    if errors or (args.strict_warnings and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
