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

On **success**, writes `data/hpc_snapshots/hpc_YYYYMMDDTHHMMSS.yaml` with:

- `collected_at` (timezone-aware ISO-8601)
- `collection_ok: true`
- queue jobs from `squeue`

On **squeue failure**, the collector exits non-zero and **does not write** a new snapshot, so the previous successful snapshot remains the latest usable record.

Queries used (read-only):

- `squeue -u <user> ...` (current queue)
- `sacct -u <user> -S <today> ...` (bounded to today)

## TTL / stale classification

Configured by `hpc_snapshot_ttl_hours` in `data/project.yaml` (default **24**).

Classification is computed at **read/display time** by `classify_hpc_snapshot()`:

| State | Meaning |
|-------|---------|
| `FRESH` | Successful snapshot younger than TTL |
| `STALE` | Successful snapshot older than TTL — not current |
| `MISSING` | No usable snapshot |
| `MALFORMED` | Missing/unparseable timestamp |
| `FAILED` | Explicit failed collection record (`collection_ok: false`) |

`MISSING` is **not** the same as “zero jobs.”

Timezone rule: timestamps should include an offset or `Z`. Naive timestamps are interpreted as UTC.

## Hard constraints

- Never `sbatch`, `scancel`, or mutate jobs from this repository.
- Do not spam accounting queries.
- Tracking must remain usable without HPC connectivity.
