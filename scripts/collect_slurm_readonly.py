#!/usr/bin/env python3
"""Optional read-only SLURM snapshot collector.

Safety constraints:
- Never submits, cancels, or modifies jobs.
- Uses only user-scoped, lightweight queries.
- Writes a timestamped YAML snapshot under data/hpc_snapshots/.
"""

from __future__ import annotations

import argparse
import getpass
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.tracking import dump_yaml  # noqa: E402


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user",
        default=getpass.getuser(),
        help="SLURM user to query (default: current user)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned commands without writing",
    )
    args = parser.parse_args()

    for tool in ("squeue", "sacct"):
        if shutil.which(tool) is None:
            print(f"SLURM tool not found: {tool}", file=sys.stderr)
            return 2

    now = datetime.now().astimezone()
    snap_id = f"hpc_{now.strftime('%Y%m%dT%H%M%S')}"

    squeue_cmd = [
        "squeue",
        "-u",
        args.user,
        "-o",
        "%.18i|%.9P|%j|%.2t|%.10M|%.6D",
        "--noheader",
    ]
    # Bounded accounting: today only
    today = now.strftime("%Y-%m-%d")
    sacct_cmd = [
        "sacct",
        "-u",
        args.user,
        "-S",
        today,
        "-n",
        "-X",
        "-o",
        "JobID,JobName,Partition,State,Elapsed,ExitCode",
        "-P",
    ]

    if args.dry_run:
        print(" ".join(squeue_cmd))
        print(" ".join(sacct_cmd))
        return 0

    rc_q, out_q = _run(squeue_cmd)
    rc_a, out_a = _run(sacct_cmd)
    if rc_q != 0:
        print(f"squeue failed ({rc_q}): {out_q}", file=sys.stderr)
        return 1

    jobs = []
    for line in out_q.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 6:
            continue
        jobs.append(
            {
                "job_id": parts[0],
                "partition": parts[1],
                "name": parts[2],
                "state": parts[3],
                "elapsed": parts[4],
                "nodes": parts[5],
            }
        )

    # Include today's sacct rows as notes only (avoid duplicating complex parsing)
    notes = f"sacct_rc={rc_a}; sacct_rows={len(out_a.splitlines()) if out_a else 0}"

    doc = {
        "id": snap_id,
        "collected_at": now.isoformat(timespec="seconds"),
        "collector": "scripts/collect_slurm_readonly.py",
        "mode": "readonly_slurm",
        "hpc_user": args.user,
        "commands_used": [" ".join(squeue_cmd), " ".join(sacct_cmd)],
        "jobs": jobs,
        "notes": notes,
    }

    path = ROOT / "data" / "hpc_snapshots" / f"{snap_id}.yaml"
    path.write_text(dump_yaml(doc), encoding="utf-8")
    print(f"Wrote {path} ({len(jobs)} queue job(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
