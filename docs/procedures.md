# Operational Procedures

## Update procedure

1. Branch from `main`.
2. Modify the minimum set of `data/` files (prefer one entity).
3. Add/update evidence fields.
4. Append activity log for significant transitions.
5. `python scripts/validate_data.py`
6. `python dashboard/generate.py`
7. PR + review.

## Run registration

```bash
python scripts/new_run.py --id run_YYYY_aNN --period-id period_YYYY \
  --start YYYY-MM-DD --end YYYY-MM-DD --owner member_02 --job-id JOBID
```

Then edit the YAML to add partition, times, source revisions, log paths, and evidence.

**Important:** A COMPLETED job is not an ACCEPTED scientific year.

## Failure / recovery

1. Set run `execution_status: FAILED` with `exit_code` and `failure_info`.
2. Open or update an issue linked to the run/period.
3. Create a retry run with `attempt_number` incremented and `retry_of` set.
4. Log activity for failure and retry creation.

## Validation procedure

1. Record method and **owner-supplied** `threshold_definition` (do not invent thresholds).
2. Attach evidence (report path, plots location, reviewer).
3. Set `pass_fail_status` to PASS/FAIL/NOT_VERIFIED accordingly.
4. Only then advance period `scientific_status`.

## Backup / recovery

- Primary backup: Git history on the configured remote (after authorized push).
- Local recovery: `git status` / `git log` / restore from remote clone.
- Do not back up scientific NetCDF into this repository.

## Maintenance

- Re-run validators in CI on every PR.
- Refresh HPC snapshots intentionally, not in tight loops.
- Revisit `OPEN_QUESTIONS.md` until Resolutions are filled.
