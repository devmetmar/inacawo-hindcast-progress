# Project Charter — INACAWO Hindcast Progress Tracking

## Purpose

Establish and maintain an evidence-based, Git-native progress tracking system for completing the remaining INACAWO hindcast simulation work on HPC user `cawohdcst_ft2`, while preserving an auditable inventory of the CLS Brazil historical archive.

## In scope

- Progress, task, run, dataset, validation, and issue tracking
- Documentation of reproducibility metadata (commits, builds, paths, job IDs)
- Static dashboard and automated validation of tracking data
- Optional read-only SLURM status snapshots

## Out of scope

- Executing, modifying, or cancelling hindcast simulations
- Changing model source, configs, dependencies, or scientific datasets
- Storing large scientific outputs or credentials in Git
- Inventing scientific acceptance thresholds

## Success criteria

1. Tracking data validates against schemas and integrity rules.
2. Dashboard reflects only recorded evidence (UNKNOWN when absent).
3. Reported / verified / accepted layers remain distinct.
4. Remaining period is configurable; unconfirmed scope is labeled provisional.
5. Four team members can update ownership and status without conflicting sources of truth.
6. System usable offline on the HPC host.

## Authority

- **Data authority:** YAML under `data/` in this repository.
- **Acceptance authority:** Designated project lead (`member_01` placeholder until named).
- **Scope confirmation:** Project owner decisions recorded in `OPEN_QUESTIONS.md` and `data/project.yaml`.

## Non-negotiable rules

See README “Boundaries” and `docs/security.md`. Tracking only; evidence required for verified/accepted states.
