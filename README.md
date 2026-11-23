# INACAWO Hindcast Progress Tracking

Operational source of truth for the internal INACAWO hindcast completion effort.

This repository tracks **progress, evidence, issues, and readiness**. It does **not** contain model source, dependencies, or scientific output files.

## Status

- Scope end year: **PROVISIONAL / NOT CONFIRMED** (see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) Q1).
- Do not treat overall completion percentage as authoritative until scope is confirmed.
- Unknown items are shown as `UNKNOWN` or `NOT_VERIFIED` — never assumed complete.
- Dataset locations use placeholders (`$CAWO_HINDCAST_BASE`, `$SCRATCH_HISTORICAL`); resolve them locally — do not commit absolute home/scratch paths.

## Dashboard

`dashboard/public/index.html` is a **catalog-centric** static page (regenerate with `python dashboard/generate.py`):

1. Catalog overview counts (catalogued / created-evidenced / verified / accepted / incomplete / open TODOs)
2. Daily inventory calendars for all catalog years (explicit `day_presence_YYYY.json` or synthesized from inventory scan)
3. Year × product matrices (CLS historical vs internal hindcast, separate)
4. Searchable dataset inventory (origin, product, lifecycle, dates, owners, TODOs)
5. TODO / action tracker linked to datasets
6. Per-dataset detail + timeline
7. Ops / HPC panel (collapsed)

Matrix cells filter datasets and sync the day calendar year/product.

See [docs/user_guide.md](docs/user_guide.md), [CATALOG_DASHBOARD_REDESIGN_REPORT.md](CATALOG_DASHBOARD_REDESIGN_REPORT.md), and [UNKNOWN_DATA.md](UNKNOWN_DATA.md) for fields that remain intentionally unknown.

## Quick start

Assumes the hindcast conda env exists at `$HOME/inacawo-deps/miniforge3/envs/hindcast` and this repo is at `$HOME/inacawo-hindcast-progress`. `pytest` must be available in that environment or your user site.

```bash
# Prefer the hindcast conda environment
export PATH="$HOME/inacawo-deps/miniforge3/envs/hindcast/bin:$PATH"
cd "$HOME/inacawo-hindcast-progress"

python scripts/validate_data.py
python scripts/compute_progress.py
python dashboard/generate.py
# open dashboard/public/index.html

pytest -q
```

## Documentation map

| Document | Purpose |
|----------|---------|
| [DISCOVERY_REPORT.md](DISCOVERY_REPORT.md) | Phase 1 workspace/HPC/dataset findings |
| [ARCHITECTURE_PROPOSAL.md](ARCHITECTURE_PROPOSAL.md) | System design decisions |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Phased delivery plan |
| [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) | Owner decisions still required |
| [PROJECT_CHARTER.md](PROJECT_CHARTER.md) | Purpose, boundaries, rules |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to update tracking data |
| [docs/user_guide.md](docs/user_guide.md) | Day-to-day usage |
| [docs/progress_metrics.md](docs/progress_metrics.md) | How completion is calculated |
| [docs/operational_readiness.md](docs/operational_readiness.md) | Readiness checklist |

## Boundaries (mandatory)

- Modify **only** this repository for tracking work.
- Never launch, cancel, or alter HPC simulation jobs from here.
- Never commit credentials, tokens, NetCDF outputs, or sensitive full logs.
- Store **references** to scratch paths, not the datasets themselves.

## Remote

`origin` → `git@github.com:devmetmar/inacawo-hindcast-progress.git`

Do not push or change GitHub settings without explicit authorization.
