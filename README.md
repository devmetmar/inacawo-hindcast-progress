# INACAWO Hindcast Progress Tracking

Operational source of truth for the internal INACAWO hindcast completion effort (HPC user `cawohdcst_ft2`).

This repository tracks **progress, evidence, issues, and readiness**. It does **not** contain model source, dependencies, or scientific output files.

## Status

- Scope end year: **PROVISIONAL / NOT CONFIRMED** (see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) Q1).
- Do not treat overall completion percentage as authoritative until scope is confirmed.
- Unknown items are shown as `UNKNOWN` or `NOT_VERIFIED` — never assumed complete.

## Quick start

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
