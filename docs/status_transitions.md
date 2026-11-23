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

## Bootstrap vs advanced status

Bootstrap statuses may exist without transition history:

- Execution: `NOT_STARTED`, `UNKNOWN`
- Scientific: `NOT_VALIDATED`, `UNKNOWN`
- Task: `NOT_STARTED`, `READY`
- Issue: `OPEN`
- Stage: `NOT_STARTED`, `UNKNOWN`, `READY`

Any other status **requires** activity-log entries (`previous_state` → `new_state`) that:

1. Are individually legal under the transition tables.
2. End at the entity’s current status.

## Enforcement

- `scripts/validate_data.py` → `validate_store()` enforces the rules above (F-01).
- CI runs `validate_data.py`, so illegal committed transitions fail CI.
- Direct YAML edits that jump to non-bootstrap statuses without history are rejected.
- `scripts/lib/tracking.py` also exposes `validate_transition()` for helpers/tests.

Use `scripts/log_activity.py` when advancing status.
