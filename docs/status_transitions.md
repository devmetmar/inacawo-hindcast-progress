# Status Transition Rules

Execution and scientific statuses are independent axes.

## Execution

Allowed transitions:

| From | To |
|------|----|
| NOT_STARTED | READY, BLOCKED, CANCELLED |
| READY | RUNNING, BLOCKED, CANCELLED, NOT_STARTED |
| RUNNING | COMPLETED, FAILED, BLOCKED, CANCELLED |
| COMPLETED | FAILED (correction only; requires evidence/activity log) |
| BLOCKED | READY, RUNNING, CANCELLED, FAILED |
| FAILED | READY, RUNNING, CANCELLED |
| CANCELLED | READY, NOT_STARTED |
| UNKNOWN | any primary execution state (bootstrap only) |

A scheduler job completing does **not** automatically set scientific acceptance.

## Scientific

| From | To |
|------|----|
| NOT_VALIDATED | NEEDS_REVIEW, FAILED_VALIDATION |
| NEEDS_REVIEW | VERIFIED, FAILED_VALIDATION, NOT_VALIDATED |
| VERIFIED | ACCEPTED, FAILED_VALIDATION, NEEDS_REVIEW |
| ACCEPTED | *(terminal in normal workflow)* |
| FAILED_VALIDATION | NEEDS_REVIEW, NOT_VALIDATED |
| UNKNOWN | bootstrap into any scientific state |

`VERIFIED` requires technical evidence. `ACCEPTED` requires designated reviewer approval evidence.

## Enforcement

- Documented here for operators.
- `scripts/lib/tracking.py` exposes `validate_transition()` for tools/tests.
- CI validates schema/referential integrity of checked-in data.
