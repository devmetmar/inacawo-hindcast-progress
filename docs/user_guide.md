# User Guide

## Who this is for

Scientists and HPC operators tracking INACAWO hindcast progress.

## Daily loop

```bash
export PATH="$HOME/inacawo-deps/miniforge3/envs/hindcast/bin:$PATH"
cd "$HOME/inacawo-hindcast-progress"

# 1) Optional read-only job snapshot
python scripts/collect_slurm_readonly.py

# 2) Register or update YAML entities (prefer helpers)
python scripts/new_run.py --id run_2015_a01 --period-id period_2015 \
  --start 2015-01-01 --end 2015-01-31 --owner member_02

# 3) Validate + metrics + dashboard
python scripts/validate_data.py
python scripts/compute_progress.py
python dashboard/generate.py
```

Open `dashboard/public/index.html` in a browser.

## Updating status safely

1. Change only the relevant YAML entity file.
2. Add evidence references for `verified` / `accepted` claims.
3. Log significant transitions:

```bash
python scripts/log_activity.py \
  --actor member_02 \
  --entity-type run \
  --entity-id run_2015_a01 \
  --action status_change \
  --previous-state RUNNING \
  --new-state COMPLETED \
  --evidence "slurm job 12345"
```

4. Run validators before committing.

## Interpreting the dashboard

- **PROVISIONAL / NOT CONFIRMED** banner: scope end year not owner-confirmed.
- **UNKNOWN / NOT_VERIFIED**: no evidence yet — not success.
- Historical year grid is inventory status, not remaining completion.

## What not to do

- Do not edit model/HPC working directories from this workflow.
- Do not mark years complete without evidence.
- Do not invent validation thresholds.
