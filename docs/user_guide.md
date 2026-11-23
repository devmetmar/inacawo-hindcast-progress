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

The landing page prioritizes **dataset catalog progress**, not generic project status.

- **PROVISIONAL / NOT CONFIRMED** banner: scope end year not owner-confirmed; overall acceptance % is suppressed.
- Catalog cards count only evidenced records (never treat a missing YAML as complete).
- **UNKNOWN / NOT_RECORDED / NOT_VERIFIED**: no evidence yet — not success.
- Historical and internal year × product matrices are **separate**; one product does not complete a year.
- Click a matrix cell to filter the inventory; expand dataset details for timeline and TODOs.
- Secondary workflow / HPC / workload panels are collapsed by default.

## Registering a dataset

1. Add `data/datasets/dataset_<name>.yaml` conforming to `schemas/dataset.schema.json`.
2. Set `origin` (`cls_brazil` | `internal` | …) and `product` (`ocean2d` / `ocean3d` / `wrf2d` / `wrf3d` / …).
3. Record `catalogued_at` as the catalog registration date (when the YAML was added).
4. Leave `created_at` null unless you have **scientific creation evidence** and document it in `created_at_provenance`. Do **not** use filesystem mtime, git commit time, or HPC start time as creation.
5. Optionally set `lifecycle_status`; otherwise the dashboard derives a conservative status from integrity/validation fields.
6. Link work with `related_task_ids` and/or task `related_dataset_ids`.
7. Store paths as placeholders; keep manifests/checksums as references only — never copy NetCDF into this repo.
8. Validate: `python scripts/validate_data.py` then regenerate the dashboard.

## Recording lifecycle dates and evidence

| Field | Meaning |
|-------|---------|
| `created_at` | When outputs were actually created (evidenced only) |
| `catalogued_at` | When the tracking record was registered |
| `last_inventory_scan` | Last directory/manifest inventory |
| `verified_at` | When integrity verification finished |
| `accepted_at` | When human acceptance was recorded |
| `integrity_status` / `validation_status` | Inventory integrity vs scientific validation |

Log significant changes with `scripts/log_activity.py` so the dataset timeline stays auditable.

## Creating TODOs linked to datasets

1. Add `data/tasks/task_<name>.yaml`.
2. Set `related_dataset_ids`, optional `related_period_ids` / `related_product`.
3. Use real `owner` member IDs from `data/team.yaml` — do not invent names or due dates.
4. Mirror links on the dataset with `related_task_ids` when useful.
5. Status grouping on the dashboard uses task `status` and explicit `due_date` only (no invented overdue).

## What not to do

- Do not edit model/HPC working directories from this workflow.
- Do not mark years complete without evidence.
- Do not invent validation thresholds, creation dates, or team identities.
