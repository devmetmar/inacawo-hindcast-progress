# Progress Metrics

## Principles

1. Do **not** compute project completion from task counts.
2. Never assume success when evidence is missing — use `UNKNOWN` / `NOT_VERIFIED`.
3. If `data/project.yaml` `scope.confirmed` is `null`, overall acceptance **percentage is suppressed**.

## Four independent metrics (remaining_internal stream)

| Metric | Numerator | Denominator |
|--------|-----------|-------------|
| Execution coverage | Periods with `execution_status=COMPLETED` | Remaining period count |
| Output coverage | Periods with **all** configured `required_products` evidenced as VERIFIED for that year | Remaining period count |
| Validation coverage | Periods with `scientific_status` in `{VERIFIED, ACCEPTED}` | Remaining period count |
| Acceptance coverage | Periods with computed `fully_complete=YES` | Remaining period count |

While scope is unconfirmed, displays show counts and `NOT_CONFIRMED` instead of an authoritative %.

## Output coverage (evidence-based)

A period is output-**COMPLETE** only when, for every product in `completion_criteria.required_products`:

1. A related dataset ID is listed on the period.
2. That dataset’s `product` matches.
3. `integrity_status` is `VERIFIED`.
4. `period_coverage` includes the period’s calendar year (`basis` may still be directory_names / verified / etc.).

Otherwise the product is `MISSING` or `NOT_VERIFIED`. Periods may be:

- `COMPLETE` — all required products verified
- `PARTIAL` — some verified, others not
- `NOT_VERIFIED` — links/candidates exist but integrity/coverage not verified
- `MISSING` — no qualifying related datasets

Sparse run directories or unverified dataset links **do not** count as complete output.

## Year fully complete

A year is fully complete only when project `completion_criteria` are satisfied:

- Execution verified (completed with related run evidence)
- Outputs complete per the rules above
- Validations verified
- Human acceptance (`scientific_status=ACCEPTED`)

## Historical baseline

Historical years (`stream: historical_baseline`) are inventoried separately and are **not** included in remaining acceptance percentage until the owner defines acceptance rules (OPEN_QUESTIONS Q2/Q3).
