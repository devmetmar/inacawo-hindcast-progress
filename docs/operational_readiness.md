# Operational Readiness Assessment

**Date:** 2026-11-23  
**Repository:** `inacawo-hindcast-progress`

## Tooling checklist

| Item | Status |
|------|--------|
| Discovery docs present | PASS |
| Architecture + charter documented | PASS |
| Schemas for core entities | PASS |
| Provisional project/team/stages/periods data | PASS |
| `validate_data.py` | PASS (must be green locally/CI) |
| `compute_progress.py` | PASS |
| Dashboard generator | PASS |
| Helper CLIs | PASS |
| Optional SLURM readonly collector | PASS |
| Automated tests | PASS (must be green) |
| CI workflow | PASS (present; runs on GitHub when pushed) |
| Security guidance + gitignore | PASS |
| User/onboarding/procedures docs | PASS |

## Explicitly NOT ready (owner-dependent)

| Item | Status |
|------|--------|
| Confirmed simulation end year (Q1) | OPEN |
| Historical baseline acceptance rules (Q2/Q6) | OPEN |
| Complete-year scientific thresholds (Q3) | OPEN |
| Real team roster (Q4) | OPEN |
| GitHub push / branch protection authorization (Q5) | OPEN |

## Readiness verdict

**Tracking system tooling: READY for team use in provisional mode.**

**Operational authority for delivery percentages: NOT READY** until Q1 and Q3 are resolved and recorded.

Do not declare the hindcast project complete based on this tracker until acceptance criteria and confirmed scope are set by owners.
