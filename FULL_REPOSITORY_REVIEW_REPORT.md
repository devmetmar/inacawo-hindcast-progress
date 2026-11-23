# FULL REPOSITORY REVIEW REPORT — INACAWO Hindcast Progress

**Review date:** 2026-11-23  
**Mode:** Audit-first; remediations applied in the working tree only (**not committed**, per instructions)  
**Repository:** `/home/cawohdcst_ft2/inacawo-hindcast-progress`

---

## A. Executive verdict

**CONDITIONAL PASS — OWNER DECISIONS REQUIRED**

### Why this verdict

1. **Claimed F-01–F-04 remediation commits did not exist** at review start. HEAD remained `e708bc9` (independent audit report only). No pre-remediation→post-remediation commit range was available.
2. This review **implemented and verified** F-01–F-04 remediations in the **working tree** (tests pass). They are **not** on `HEAD` until the owner authorizes commits.
3. **Owner-blocked** items remain: target end year (2024 vs 2025), historical acceptance, scientific thresholds, team identities, GitHub push/history-rewrite authorization.
4. **Git history still contains absolute `/home/...` and `/scratch/...` paths** even after current-tree sanitization. History rewrite was not performed (forbidden without authorization).

Until remediations are committed and owner decisions for scope/publication are recorded, do not treat the repository as fully operationally authoritative or push-safe.

---

## B. Repository and commit identity

| Item | Value |
|------|-------|
| Path | `/home/cawohdcst_ft2/inacawo-hindcast-progress` |
| Branch | `main` |
| **Committed HEAD** | `e708bc93a52bcc45d4ab65373c4e2362cc4a8059` — *Add independent implementation audit report.* |
| Working tree at review end | **Dirty** (remediation + this report uncommitted) |
| Remote | `git@github.com:devmetmar/inacawo-hindcast-progress.git` |
| Remote visibility (API) | **public** (`private=false`); remote `size=0` suggests local commits may not be pushed |
| README vs committed HEAD (pre-remediation) | Matched at audit start; README later edited in WT for placeholders |

### Commit history (no F-01–F-04 remediation commits)

```
e708bc9 Add independent implementation audit report.
4a45c84 Add GitHub Actions validation workflow and issue/PR templates.
1750c33 Add automated tests for validation, progress, and dashboard.
bc9b097 Add operational docs for metrics, procedures, and readiness.
edb2064 Add static dashboard generator and initial public HTML.
82ff8db Add validation, progress, helper, and read-only SLURM scripts.
1e83668 Add provisional project data, periods, datasets, tasks, and issues.
bc3999d Add JSON schemas for tracking entities and common definitions.
… (earlier Phase 1 docs / charter / requirements / gitignore)
068a368 Add gitignore for secrets, scientific outputs, and caches.
```

**Relevant remediation commits:** **NONE in Git history.**  
**Pre-remediation vs current committed diff for F-01–F-04:** N/A (no remediation revision).  
**Working-tree remediations** are present relative to `HEAD` (see section C evidence).

---

## C. Previous finding closure matrix

| Finding | Required behavior | Evidence inspected | Test result | Verdict |
|---------|-------------------|--------------------|-------------|---------|
| F-01 | Status transitions enforced by validator and CI | `scripts/lib/tracking.py` (`_validate_status_transitions`, activity-log ledger); `docs/status_transitions.md`; CI still runs `validate_data.py` | Negative tests in `tests/test_remediation_f01_f04.py` pass in WT | **PASS** (working tree); **FAIL** on committed `HEAD` until committed |
| F-02 | Output coverage evidence-based, not weak proxy | `period_output_assessment`, `compute_progress` output metric + `by_product`; `docs/progress_metrics.md` | Sparse-link and partial-product tests pass | **PASS** (working tree); **FAIL** on committed `HEAD` until committed |
| F-03 | HPC snapshots stale after TTL | `hpc_snapshot_ttl_hours=24`; `classify_hpc_snapshot`; collector no-write on failure; dashboard/CLI show state | Stale/missing/malformed/failed-selection tests pass | **PASS** (working tree); **FAIL** on committed `HEAD` until committed |
| F-04 | Public path/history review | Current WT sanitized; `git grep` history still has `/home/` `/scratch/`; remote public | Dashboard assert no `/home/` `/scratch/`; history exposure remains | **PARTIAL** — current tree cleaned; **history OWNER BLOCKED** |

---

## D. Full repository review

### D.1 README and documentation

| Check | Result |
|-------|--------|
| Markdown / relative links among core docs | OK |
| Quick-start commands | Verified executable with hindcast env on PATH; `pytest` via user site if needed (documented assumption) |
| Provisional scope clearly labeled | Yes |
| Docs describe implemented behavior after WT remediation | Updated `status_transitions.md`, `progress_metrics.md`, `hpc_monitoring.md`, `security.md` |
| Owner-blocked decisions | Still explicit in `OPEN_QUESTIONS.md` |

**Issue (medium):** README/docs in WT diverge from `HEAD` until committed.

### D.2 Data model and schemas

- 31 provisional years retained; `scope.confirmed: null`; no ACCEPTED / `fully_complete: YES`.
- Historical vs `remaining_internal` streams separated.
- Referential integrity enforced.
- `hpc_snapshot` schema now requires `collection_ok`.
- Placeholders used for work/dataset locations in WT.

### D.3 Progress computation

- Four metrics remain separate; overall % suppressed while unconfirmed.
- Output coverage now requires per-product `integrity_status=VERIFIED` + year coverage — sparse IDs alone do not count.
- Historical years excluded from remaining denominators.
- 30 vs 31 year discrepancy remains explicit and unresolved.

### D.4 Dashboard

- Regenerated from progress API; shows provisional banner; HPC state pill (`FRESH`/`STALE`/…).
- WT dashboard HTML contains no `/home/` or `/scratch/` strings (tested).

### D.5 CLI helpers

- `validate_data.py` uses `validate_store` (now includes transitions).
- Collector: read-only; failure does not write empty success snapshot.
- Helpers write only under repo `data/`.

### D.6 HPC collector

- Only `squeue` / `sacct`; no `sbatch`/`scancel`/`scontrol update`.
- Live job mutation: not performed in this review.

### D.7 CI

- `.github/workflows/validate.yml` runs `validate_data.py`, progress, dashboard, `pytest`.
- After F-01 wiring, CI-equivalent validation rejects illegal transitions **once remediations are committed**.

### D.8 Tests

- See Section E. Meaningful negative coverage added for F-01–F-04.

### D.9 Security and public exposure

| Layer | Status |
|-------|--------|
| Current working tree host-specific `/home/...` `/scratch/...` | Cleared (placeholders) |
| Secrets / keys / NetCDF | Not found |
| Git history | **Still contains absolute paths and HPC usernames** from earlier commits |
| Public remote | Confirmed public via API; push of history would publish those paths |

### D.10 Git history

- History rewrite **not** performed.
- Owner must decide whether to push as-is, scrub history before first push, or change visibility (**OPEN_QUESTIONS Q5**).

---

## E. Test results (executed)

Environment: hindcast conda `python` on `PATH` (plus user-site `pytest` as needed).

| Command | Exit code | Notes |
|---------|-----------|-------|
| `python scripts/validate_data.py` | **0** | 0 errors, 0 warnings (WT) |
| `python scripts/compute_progress.py` | **0** | Provisional; HPC status printed |
| `python dashboard/generate.py` | **0** | Regenerated `dashboard/public/index.html` |
| `pytest -q` | **0** | **27 passed** |
| `python scripts/collect_slurm_readonly.py --dry-run` | Not re-run in final pass | Previously verified read-only command print |

**Inspected but not live-executed against scheduler in final pass:** destructive/job-altering commands (none present).

---

## F. Owner-blocked decisions

1. **Target end year:** 2015–2024 (30-year total) vs 2015–2025 (31-year total) — keep provisional until confirmed.
2. **Historical baseline acceptance** despite uneven product coverage.
3. **Scientific validation thresholds** — must not be invented.
4. **Real team member identities / ownership mapping.**
5. **GitHub:** authorize push? scrub history before push? change visibility?
6. **Authorize commits** of the working-tree F-01–F-04 remediations + this report.

---

## G. Critical issues

1. **Committed `HEAD` does not contain F-01–F-04 remediations** — only the working tree does.
2. **Git history retains absolute path exposure** — separate owner-authorized handling required before treating a public push as safe.
3. **Scope still unconfirmed** — overall % correctly suppressed; delivery planning remains provisional.

---

## H. Non-blocking issues

1. `pytest` may live in user-site rather than conda env — documented assumption.
2. Output completeness still cannot prove day-level continuity without inventory manifests (by design; no invented thresholds).
3. Stage/task bootstrap rules are documented; advanced statuses require activity-log discipline.
4. Remote `size=0` suggests commits may not yet be on GitHub — confirm before assuming public history content.

---

## I. Remediation performed in this review (working tree only)

| ID | Change |
|----|--------|
| F-01 | `validate_store()` enforces transition tables + activity-log history for non-bootstrap statuses |
| F-02 | Evidence-based `period_output_assessment` / output metric with per-product VERIFIED+coverage rules |
| F-03 | Configurable TTL (24h), read-time classification, collector no-write on failure, dashboard/CLI labels |
| F-04 | Placeholder paths in data/docs/README; dashboard/tests assert no absolute home/scratch in generated HTML |
| Tests | `tests/test_remediation_f01_f04.py` (+ fixture updates) |
| Docs | status/progress/hpc/security updates |

**Not done (by rule):** commit, push, history rewrite, GitHub settings changes.

---

## J. Recommended owner actions

1. Review working-tree remediations.
2. Authorize a series of commits (or one remediation series) authored as required.
3. Decide history scrub vs visibility before any push to the public remote.
4. Resolve `OPEN_QUESTIONS.md` Q1 (and Q2/Q3) before authoritative completion percentages.
5. Re-run `validate_data.py` / `pytest` after commit.

---

## K. Demonstration notes (F-01 negative path)

Illegal direct edit simulation (working tree code):

- Set `period_2015.execution_status = COMPLETED` with no activity history → `validate_store` error: *non-bootstrap status … no activity-log transition history*.
- Activity `NOT_STARTED → COMPLETED` → error: *illegal or ambiguous status transition*.

CI equivalence: workflow step `python scripts/validate_data.py` invokes the same `validate_store()` path.
