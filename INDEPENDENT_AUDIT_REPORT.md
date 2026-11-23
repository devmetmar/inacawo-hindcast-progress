# INDEPENDENT AUDIT REPORT — INACAWO Hindcast Progress Tracking

**Audit date:** 2026-11-23  
**Auditor role:** Independent implementation review (audit-only)  
**Repository audited:** `/home/cawohdcst_ft2/inacawo-hindcast-progress`  
**Remote:** `git@github.com:devmetmar/inacawo-hindcast-progress.git` (public)  
**Commit/push performed during audit:** None  

---

## 1. Overall verdict

**PASS WITH NON-BLOCKING NOTES**

Evidence supports that:

- Tracking implementation is confined to `inacawo-hindcast-progress` as source of truth.
- Provisional scope is preserved; no fabricated scientific acceptance.
- HPC collector is read-only and does not submit/cancel jobs.
- Independent re-runs of validators and tests succeeded.
- No secrets or scientific binary/NetCDF artifacts were found in the tracking tree.

Non-blocking gaps remain (transition enforcement not wired into CI validators; public exposure of internal absolute paths; test-coverage depth limits). None of these constitute a fail for commit readiness of the current tree, provided the owner accepts the notes below.

---

## 2. Repository boundary verification

### Verified — tracking repo

| Check | Result |
|-------|--------|
| All intended tracking files under `inacawo-hindcast-progress` | Yes |
| Git history in tracking repo | No commits yet; all content untracked |
| Remote configured | `origin` → `devmetmar/inacawo-hindcast-progress.git` |
| Scientific NetCDF / `coawstM` / large binaries in tracking tree | None found |
| `__pycache__` / `.pytest_cache` ignored by `.gitignore` | Yes (`git check-ignore` confirmed) |

### Companion repositories

| Repo | Git porcelain | Assessment |
|------|---------------|------------|
| `inacawo-src` | Clean | No modifications attributed to tracking work |
| `inacawo-deps` | Clean (tracked tree) | `miniforge3/` is gitignored; no tracked file changes |
| `inacawo-iht` | Dirty notebook + untracked cache/checkpoints | **Not attributed to tracking implementation** (notebook mtime 2026-10-20; 1-line diff in tutorial notebook). Unrelated pre-existing local state. |

### HPC / scientific filesystem

| Check | Result |
|-------|--------|
| Scratch `cawo_post` / `cawo_output` mtimes | Still dated **2026-10-21** (pre-tracking) |
| Active SLURM jobs for `cawohdcst_ft2` at audit | None |
| Tracking scripts containing `sbatch` / `scancel` / `scontrol update` | **None** (mentions only in documentation forbidding them) |

### Side effects outside the tracking repo (non-source)

During earlier implementation/testing, `pytest` was installed into the user site:

- `/home/cawohdcst_ft2/.local/lib/python3.13/site-packages/pytest`
- `/home/cawohdcst_ft2/.local/bin/pytest`

This is **outside** `inacawo-hindcast-progress` but is a local Python tooling install, not a model/HPC/dataset modification. Running this audit also refreshed `__pycache__` under the gitignored hindcast conda tree when importing packages.

**Boundary conclusion:** No unauthorized edits to model source, configs, dependencies git content, scientific datasets, or SLURM jobs. Local pytest user-site install is a side effect to note, not a tracking-repo boundary breach.

### Audit re-execution note

This audit re-ran `dashboard/generate.py`, which rewrote `dashboard/public/index.html` inside the tracking repo (same generator path used for validation). No other repositories were modified for the audit deliverable except creation of this report file.

---

## 3. Authorization compliance

### Original assignment gates

The original task required Phase 1 discovery first and **explicit owner approval before Phase 2**.

### Subsequent owner instruction

The owner then directed: implement the attached plan and **complete all to-dos** (phase1-docs through phase5-ops).

### What was implemented

| Phase | Content present | Relative to original phased gates |
|-------|-----------------|-----------------------------------|
| Phase 1 | Discovery docs, open questions, architecture | Required; completed |
| Phase 2 | Schemas, data model, charter, CI, provisional data | Implemented in same session after “implement the plan” |
| Phase 3 | Dashboard + helpers + optional SLURM collector | Implemented same session |
| Phase 4 | Pytest suite + validation scripts | Implemented same session |
| Phase 5 | User/ops/readiness docs | Implemented same session |

### Scope deviation statement

- **Deviation from the original sequential approval gates:** Phases 2–5 were implemented without separate per-phase owner approvals after Phase 1 docs alone.
- **Alignment with the later explicit instruction:** Completing Phases 2–5 matches the owner’s “implement the plan / complete all to-dos” authorization.
- **Per audit instructions:** Completed ahead-of-schedule work was **not** deleted.

Owner decisions in `OPEN_QUESTIONS.md` (Q1–Q6) remain unresolved; the system correctly keeps scope provisional.

---

## 4. Data integrity findings

### Independent validation (re-run)

```text
python scripts/validate_data.py
→ 0 error(s), 0 warning(s)
→ periods=31 runs=0 datasets=7 tasks=3 issues=2 validations=0
```

### 31 provisional calendar-year records

| Stream | Years | Count | `scope_basis` | `execution_status` | `scientific_status` | `fully_complete` |
|--------|-------|-------|---------------|--------------------|---------------------|------------------|
| `historical_baseline` | 1995–2014 | 20 | `provisional` | `UNKNOWN` | `UNKNOWN` | `NOT_VERIFIED` |
| `remaining_internal` | 2015–2025 | 11 | `provisional` | `NOT_STARTED` | `NOT_VALIDATED` | `NO` |

**Verified:**

- Unique period IDs; dates fall within declared calendar years.
- `data/project.yaml` has `scope.confirmed: null`.
- No period has `scientific_status: ACCEPTED`.
- No period has `fully_complete: YES`.
- Progress overall percent is `null`; metric displays are `NOT_CONFIRMED`.
- Historical vs internal datasets separated by `origin: cls_brazil` vs `internal`.
- Referential integrity checks detect broken foreign keys (spot-checked by injecting `run_nope`).

### Gap — status transition enforcement

`validate_transition()` exists and is unit-tested, but **`validate_store()` / `validate_data.py` do not enforce transitions** on checked-in YAML (no prior-state ledger). Hand-edited illegal jumps (e.g. `NOT_STARTED` → `COMPLETED`) would currently pass schema/referential CI until additional controls are added.

This does **not** invent success today (current data is conservative), but it is a control gap.

### Progress calculation

- Four metrics implemented; acceptance % suppressed while unconfirmed.
- `output_coverage` currently counts presence of `related_dataset_ids` (weak proxy); `is_year_fully_complete` remains conservative and does not auto-YES.
- Historical years excluded from remaining acceptance denominator.

---

## 5. Scientific tracking findings

| Requirement | Assessment |
|-------------|------------|
| Job completion ≠ scientific acceptance | **Pass** — separate execution vs scientific axes; completed-alone period computes `fully_complete=NO` |
| Failed attempts traceable | **Pass by design** — run records + `failure_info`; no production failed-run YAML yet (empty `data/runs/`) |
| Retries do not overwrite history | **Pass by design** — new run IDs + `retry_of`; helper refuses overwrite; unit coverage for linkage |
| Output verification separate from execution | **Pass** — distinct metrics/criteria; products listed in `completion_criteria` |
| Validation thresholds not invented | **Pass** — thresholds null/owner-required; docs forbid invention; warning path if PASS without threshold |
| Human acceptance not bypassable | **Pass** — `require_human_acceptance: true`; no ACCEPTED periods present |
| Unknown never silent success | **Pass** — UNKNOWN/NOT_VERIFIED/NO used; dashboard provisional banner |

---

## 6. HPC safety findings

### Collector inspection (`scripts/collect_slurm_readonly.py`)

| Check | Result |
|-------|--------|
| Commands used | `squeue -u <user> …`, `sacct -u <user> -S <today> …` only |
| `sbatch` / `scancel` / `scontrol update` | Absent |
| User-scoped | Yes (`-u`) |
| Accounting bounded | Yes (`-S` today) |
| Writes | Only under `data/hpc_snapshots/` in tracking repo |
| Dashboard/validate auto-trigger collector | **No** |

### Dry-run during audit

```text
python scripts/collect_slurm_readonly.py --dry-run
→ prints the two read-only commands; exit 0
```

No live collector write was performed during this audit (an earlier implementation run created `data/hpc_snapshots/hpc_20261123T083639.yaml` with 0 queue jobs).

### Stale snapshot handling

Snapshots store `collected_at`. Dashboard displays timestamp and warns to treat old data as stale, but **does not auto-label STALE via a configured TTL**. Non-blocking.

### Residual risk

`--user` can be pointed at another account (still read-only). Acceptable; document operator discipline.

---

## 7. Security findings

**Repository visibility:** public GitHub remote.

| Class | Finding |
|-------|---------|
| Credentials / tokens / private keys | **None found** in tracking content (search covered password/secret/token/private key/cdsapirc/vault patterns; hits were documentation warnings only) |
| NetCDF / large scientific files | **None** in tree; `.gitignore` blocks common types |
| Raw HPC logs | **None** committed |
| Environment secret files | **None** |
| Internal absolute paths | **Present** in docs/data (`/scratch/...`, `/home/cawohdcst_ft2/...`, HPC usernames) |
| Companion git SHAs / tarball checksum | Present in `data/project.yaml` metadata (reproducibility, not secrets) |
| Generated dashboard | No secret patterns; shows provisional status and issue IDs |

**Public-repo note:** Absolute HPC paths and usernames are operational metadata. Not credentials, but may be undesirable on a public remote depending on institutional policy (OPEN_QUESTIONS Q5). **Do not change GitHub visibility in this audit.**

---

## 8. Test results (independent re-run)

| Command | Exit code | Result |
|---------|-----------|--------|
| `python scripts/validate_data.py` | 0 | 0 errors, 0 warnings |
| `python scripts/compute_progress.py` | 0 | Provisional; overall % suppressed |
| `python dashboard/generate.py` | 0 | Wrote `dashboard/public/index.html` |
| `pytest -q` | 0 | **14 passed** |
| `collect_slurm_readonly.py --dry-run` | 0 | Read-only commands printed |

### Coverage assessment

| Concern | Covered? | Notes |
|---------|----------|-------|
| Failed runs | Partial | Logic tested via synthetic period mutation; no checked-in failed run fixture |
| Retry handling | Partial | `retry_of` referential test; no full YAML retry pair in `data/runs/` |
| Missing outputs | Partial | fully_complete conservative; output metric is weak proxy |
| Invalid references | Yes | Task/run foreign-key tests |
| Unconfirmed scope | Yes | overall % / NOT_CONFIRMED assertions |
| Stale HPC snapshots | Partial | Latest snapshot selection tested; no TTL classification test |
| Progress calculation | Yes | Bucket counts and metric suppression |
| Concurrent collaboration risks | **No** | No merge-conflict/lock tests (process mitigated by one-file-per-entity convention only) |
| Status transitions in CI path | **No** | Unit-tested function not invoked by `validate_data.py` |

---

## 9. Critical issues

**None identified** that would require blocking an initial local commit of the current tracking tree.

(Unresolved owner questions Q1–Q6 are **project** blockers for authoritative delivery metrics, not implementation defects.)

---

## 10. Non-blocking issues

1. **Status transitions not enforced by `validate_data.py`/CI** — illegal hand-edits could pass schema checks.
2. **`output_coverage` metric is a weak proxy** (link presence, not integrity/product completeness).
3. **No automatic STALE TTL** for HPC snapshots in dashboard logic.
4. **Public exposure of internal absolute paths / HPC usernames**.
5. **Empty `data/runs/` and `data/validations/`** — designs are sound, but operational examples are sparse.
6. **Concurrent-edit risks** rely on process, not automated detection.
7. **Local pytest install in `~/.local`** as implementation side effect.
8. **Phases 2–5 compressed** relative to original per-phase approval cadence (authorized later by “implement the plan”).
9. **Unrelated dirty state in `inacawo-iht`** (tutorial notebook/cache) — do not include in tracking commit; not caused by this work.

---

## 11. Recommended remediation

Prioritized for a follow-up change set (not applied in this audit):

1. Wire transition checks into validation (e.g. require activity-log evidence for non-trivial status jumps, or store previous status hashes).
2. Strengthen output completeness checks against `completion_criteria.required_products` and dataset integrity status.
3. Add dashboard/CI stale threshold for HPC snapshots (configurable hours/days).
4. Add fixture YAML for failed run + retry pair and missing-output scenarios.
5. Owner decision on whether absolute scratch/home paths should remain in the public repo (redact or keep).
6. Resolve `OPEN_QUESTIONS.md` Q1–Q6 before treating percentages as authoritative.
7. Keep companion repos untouched; ignore unrelated `inacawo-iht` local dirt when committing tracking.

---

## 12. Commit readiness recommendation

**Ready for an initial local Git commit of `inacawo-hindcast-progress` after owner review of this audit**, with these constraints:

1. Commit **only** files under `inacawo-hindcast-progress` (including this audit report if desired).
2. Do **not** push until explicitly authorized (OPEN_QUESTIONS Q5).
3. Do **not** treat the tracker as authority for final delivery % until scope confirmation (Q1) and completion rules (Q3) are resolved.
4. Do **not** commit unrelated `inacawo-iht` local changes.

**Push readiness:** Not authorized by this audit. Await explicit owner instruction.

---

## Appendix A — Evidence commands (audit)

- `git -C …/inacawo-hindcast-progress status|remote|branch`
- `git -C …/{inacawo-iht,inacawo-src,inacawo-deps} status --porcelain`
- `rg` for `sbatch|scancel|scontrol update` and secret-like patterns
- `find` for `*.nc` / large files in tracking tree
- Independent: `validate_data.py`, `compute_progress.py`, `dashboard/generate.py`, `pytest -q`, collector `--dry-run`
- Programmatic period/stream/scope integrity probe via `TrackingStore`

## Appendix B — Audit constraints honored

- No feature implementation or refactor of existing tracking code (except generating this report).
- No commit / push / GitHub settings changes.
- No job submission/cancellation; collector exercised only with `--dry-run` during audit.
- Completed ahead-of-schedule phases retained.
