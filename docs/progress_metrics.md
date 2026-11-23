# Progress Metrics

## Principles

1. Do **not** compute project completion from task counts.
2. Never assume success when evidence is missing — use `UNKNOWN` / `NOT_VERIFIED`.
3. If `data/project.yaml` `scope.confirmed` is `null`, overall acceptance **percentage is suppressed**.

## Four independent metrics (remaining_internal stream)

| Metric | Numerator | Denominator |
|--------|-----------|-------------|
| Execution coverage | Periods with `execution_status=COMPLETED` | Remaining period count |
| Output coverage | Periods with at least one `related_dataset_ids` entry | Remaining period count |
| Validation coverage | Periods with `scientific_status` in `{VERIFIED, ACCEPTED}` | Remaining period count |
| Acceptance coverage | Periods with computed `fully_complete=YES` | Remaining period count |

While scope is unconfirmed, displays show counts and `NOT_CONFIRMED` instead of an authoritative %.

## Year fully complete

A year is fully complete only when project `completion_criteria` are satisfied:

- Execution verified (completed with related run evidence)
- Outputs verified (related datasets present and later integrity-checked)
- Validations verified
- Human acceptance (`scientific_status=ACCEPTED`)

Default implementation is conservative: missing evidence yields `NOT_VERIFIED` / `NO`, never silent `YES`.

## Historical baseline

Historical years (`stream: historical_baseline`) are inventoried separately and are **not** included in remaining acceptance percentage until the owner defines acceptance rules (OPEN_QUESTIONS Q2/Q3).
