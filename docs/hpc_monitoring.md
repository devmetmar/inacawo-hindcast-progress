# HPC Monitoring

## Modes

### 1. Manual (default)

Operators record job metadata in `data/runs/*.yaml`:

- `job_id`, `partition`, `hpc_user`
- submission / start / end timestamps
- `exit_code`, `log_locations`
- evidence refs

### 2. Optional read-only collector

```bash
python scripts/collect_slurm_readonly.py
# or
python scripts/collect_slurm_readonly.py --dry-run
```

Writes `data/hpc_snapshots/hpc_YYYYMMDDTHHMMSS.yaml` with `collected_at`.

Queries used:

- `squeue -u <user> ...` (current queue)
- `sacct -u <user> -S <today> ...` (bounded to today)

## Hard constraints

- Never `sbatch`, `scancel`, or mutate jobs from this repository.
- Do not spam accounting queries.
- Dashboard must show snapshot age; absence → `NONE`.
- Tracking must remain usable without HPC connectivity.

## Stale data

A snapshot is informational only. If `collected_at` is old, treat job state as **stale**, not current.
