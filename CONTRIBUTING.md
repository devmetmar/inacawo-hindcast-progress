# Contributing to INACAWO Hindcast Progress Tracking

## Principles

1. **One source of truth:** update `data/` YAML; regenerate dashboard; do not hand-edit HTML as status.
2. **Evidence over assertion:** do not mark `verified` or `accepted` without evidence references.
3. **No inventions:** unknown → `UNKNOWN` / `NOT_VERIFIED` / leave fields null.
4. **No secrets or NetCDF** in commits.
5. **Small PRs:** prefer one entity type or one logical change per PR.

## Workflow

1. Create a branch from `main`.
2. Prefer helper scripts under `scripts/` (`new_run.py`, `new_task.py`, …) over multi-file hand edits.
3. Run locally:

```bash
export PATH="$HOME/inacawo-deps/miniforge3/envs/hindcast/bin:$PATH"
python scripts/validate_data.py
python scripts/compute_progress.py
python dashboard/generate.py
pytest -q
```

4. Open a pull request. CI must pass.
5. Request review from the entity’s `reviewer` or project lead when changing status beyond `RUNNING` / into scientific acceptance.

## Status changes

See `docs/status_transitions.md`. Illegal transitions will fail validation.

## Activity log

Use `scripts/log_activity.py` for significant state changes (especially anything past `RUNNING` or into `VERIFIED`/`ACCEPTED`).

## What not to do

- Do not push secrets.
- Do not run `sbatch` / `scancel` from this repo’s tooling.
- Do not copy HPC datasets into the repository.
- Do not hardcode a confirmed total year count until `OPEN_QUESTIONS.md` Q1 is resolved.
