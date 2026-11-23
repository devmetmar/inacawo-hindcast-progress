# Pre-Commit Diff Review — F-01–F-04 Remediation

**Date:** 2026-11-23  
**Repository:** `inacawo-hindcast-progress`  
**Mode:** Read-only review of the working tree. No stage/commit/push/fetch/history rewrite/HPC access.

---

## 1. Executive verdict

**READY FOR A LOCAL REMEDIATION COMMIT SET after excluding or sanitizing one sensitive audit report.**

- HEAD remains `e708bc9` (no remediations committed).
- Working tree holds a coherent F-01–F-04 implementation with supporting docs/tests/dashboard.
- **Include** core code, schemas, data placeholders, docs, generated dashboard, remediation tests, activity-log bootstrap entry, and sanitized audit/state reports (after checks).
- **Exclude or sanitize before commit:** `FULL_REPOSITORY_REVIEW_REPORT.md` (embeds absolute home-path strings).
- Remediations do **not** invent scientific thresholds or confirm scope; provisional scope preserved.
- History sanitization / push / visibility remain **separate owner decisions** (out of scope for this commit plan).

---

## 2. Git state at review time

| Item | Value |
|------|--------|
| Branch | `main` |
| HEAD | `e708bc93a52bcc45d4ab65373c4e2362cc4a8059` |
| Staged | **None** |
| Modified tracked | **27** |
| Untracked (before this report) | **4** (`FULL_REPOSITORY_REVIEW_REPORT.md`, `GIT_STATE_AND_PUBLIC_EXPOSURE_REPORT.md`, `data/activity_log/act_20261123_stage_a_running.yaml`, `tests/test_remediation_f01_f04.py`) |
| Diff vs HEAD | 27 files, +644 / −97 |
| Renames/deletes | None |
| Mode changes | Scripts remain executable where previously set |
| CI workflow file | Unchanged (still runs `validate_data.py` → `validate_store`) |

`validate_data.py` itself is unchanged; F-01 is enforced because it already calls `validate_store()`, which now includes `_validate_status_transitions()`.

---

## 3. Complete file classification table

Exactly one label per path. Multi-finding files use the **primary** label; other findings noted in the reason.

| Path | Class | Reason |
|------|-------|--------|
| `scripts/lib/tracking.py` | `F01_REMEDIATION` | Primary: wires transition enforcement into `validate_store`. Also implements F-02 (`period_output_assessment`) and F-03 (`classify_hpc_snapshot` / TTL). |
| `scripts/lib/__init__.py` | `F01_REMEDIATION` | Exports validator/progress helpers used by remediations. |
| `data/activity_log/act_20261123_stage_a_running.yaml` | `F01_REMEDIATION` | Required history so stage `RUNNING` passes new transition rules. |
| `docs/status_transitions.md` | `REQUIRED_DOCUMENTATION` | Documents bootstrap vs advanced rules and CI enforcement. |
| `docs/progress_metrics.md` | `F02_REMEDIATION` | Documents evidence-based per-product output coverage. |
| `dashboard/generate.py` | `F02_REMEDIATION` | Surfaces output completeness detail + F-03 HPC state pills (primary F-02 UI). |
| `dashboard/public/index.html` | `F02_REMEDIATION` | Regenerated artifact from updated generator (must match code). |
| `scripts/compute_progress.py` | `F03_REMEDIATION` | Prints TTL/HPC classification; consumes new progress fields. |
| `scripts/collect_slurm_readonly.py` | `F03_REMEDIATION` | No-write on `squeue` failure; sets `collection_ok`. |
| `data/project.yaml` | `F03_REMEDIATION` | Adds `hpc_snapshot_ttl_hours: 24` and F-04 path/user placeholders. |
| `schemas/project.schema.json` | `F03_REMEDIATION` | Schema for TTL field. |
| `schemas/hpc_snapshot.schema.json` | `F03_REMEDIATION` | Requires `collection_ok`. |
| `data/hpc_snapshots/hpc_20261123T083639.yaml` | `F03_REMEDIATION` | Adds `collection_ok`; removes real HPC username from committed snapshot. |
| `docs/hpc_monitoring.md` | `REQUIRED_DOCUMENTATION` | TTL states and failure behavior. |
| `README.md` | `F04_REMEDIATION` | Removes HPC username; documents placeholders / env assumptions. |
| `DISCOVERY_REPORT.md` | `F04_REMEDIATION` | Absolute paths → `$HOME` / `$CAWO_HINDCAST_BASE` / `$SCRATCH_HISTORICAL`. |
| `OPEN_QUESTIONS.md` | `F04_REMEDIATION` | Scratch path → placeholder. |
| `INDEPENDENT_AUDIT_REPORT.md` | `F04_REMEDIATION` | Absolute path strings reduced to `$HOME`-style placeholders. |
| `data/datasets/dataset_*.yaml` (7 files) | `F04_REMEDIATION` | `location:` absolute scratch → placeholders. |
| `data/issues/issue_uneven_historical_products.yaml` | `F04_REMEDIATION` | Evidence reference path sanitized. |
| `docs/security.md` | `REQUIRED_DOCUMENTATION` | Placeholder guidance + history note. |
| `tests/test_remediation_f01_f04.py` | `REQUIRED_TEST` | Negative/positive tests for F-01–F-04 against real `validate_store` / metrics. |
| `tests/test_runs_and_dashboard.py` | `REQUIRED_TEST` | Snapshot fixture updated for `collection_ok` + placeholder user. |
| `FULL_REPOSITORY_REVIEW_REPORT.md` | `POTENTIALLY_SENSITIVE` | Untracked audit report still embeds absolute `/home/<user>/...` strings. |
| `GIT_STATE_AND_PUBLIC_EXPOSURE_REPORT.md` | `AUDIT_REPORT` | Git/exposure assessment; uses sanitized descriptions (safe if included). |
| `PRE_COMMIT_REVIEW_REPORT.md` | `AUDIT_REPORT` | This report (created as deliverable). |

No `UNRELATED` changes found. No renames/deletes.

---

## 4. F-01 through F-04 implementation review

### F-01 — Status transitions

| Check | Result |
|-------|--------|
| Authoritative path | `validate_data.py` → `validate_store()` → `_validate_status_transitions()` |
| CI | Unchanged workflow still runs `validate_data.py` → will enforce once committed |
| Direct YAML jump | Non-bootstrap status without activity history → error |
| Illegal activity step | e.g. `NOT_STARTED`→`COMPLETED` → illegal/ambiguous error |
| Bootstrap rules | Documented; does not silently rewrite historical records |
| Weakening? | **No** — tighter than HEAD |

### F-02 — Output coverage

| Check | Result |
|-------|--------|
| Definition | All `required_products` need related dataset with `integrity_status=VERIFIED` and year coverage |
| Sparse links | Do **not** count as complete |
| Streams | Remaining-only denominator; historical not mixed in |
| Invented thresholds | **None** (uses integrity/coverage evidence only) |
| Scope | Still provisional; % still `NOT_CONFIRMED` |

### F-03 — HPC TTL

| Check | Result |
|-------|--------|
| Config | `hpc_snapshot_ttl_hours: 24` in project data + schema |
| Classification | `FRESH` / `STALE` / `MISSING` / `MALFORMED` / `FAILED` at read time |
| Collector failure | Exits without writing success snapshot |
| MISSING ≠ zero jobs | Documented in CLI/dashboard |
| Dashboard | Shows state pill + TTL |

### F-04 — Path sanitization (current tree)

| Check | Result |
|-------|--------|
| Tracked WT tip content | Absolute host-specific scratch/home dataset paths replaced with placeholders |
| Generated dashboard | No `/home/` or `/scratch/` host paths expected from generator |
| HPC username in snapshot/README | Replaced with placeholders / removed |
| Git history | **Unchanged** — still contains absolute paths (not solved by this commit) |

---

## 5. Security review

| Class | Working-tree finding |
|-------|----------------------|
| Secrets / tokens / private keys | **None** found |
| Absolute host home/scratch in **recommended remediation files** | Cleared to placeholders |
| Absolute paths in **`FULL_REPOSITORY_REVIEW_REPORT.md`** | **Present** — treat as sensitive for public commit |
| `docs/security.md` | Mentions `/home/` `/scratch/` only as patterns to avoid (OK) |
| HPC usernames in WT remediations | Replaced with `PLACEHOLDER_*` in project/snapshot |
| Collector future runs | May write real `$USER` into new snapshots if re-run — operational caution, not in current staged set |

**Before any public push:** history scrub or private visibility remains required (prior assessment). This pre-commit plan only addresses the tip.

---

## 6. Test quality assessment

### `tests/test_remediation_f01_f04.py` (untracked)

| Test focus | Quality |
|------------|---------|
| Illegal period jump → `validate_store` errors | **Strong** — mutates store, calls real validator |
| Illegal activity transition | **Strong** — real validator path |
| “CI equivalent” | **Adequate but thin** — calls `validate_store` (same function CI uses) but does **not** subprocess `validate_data.py` |
| Sparse output IDs | **Strong** — uses `period_output_assessment` + `compute_progress` |
| Partial verified products | **Strong** — synthetic fixtures exercise completeness logic |
| HPC stale/missing/malformed/failed selection | **Strong** — real classifiers; fixed `now` where needed |
| Dashboard path assert | **Strong** — renders HTML from real generator |

### `tests/test_runs_and_dashboard.py`

- Fixture update necessary for schema/`collection_ok`; not a bypass.

**Gap (non-blocking):** No subprocess test of `python scripts/validate_data.py` exit code; acceptable because CI invokes that script and it only wraps `validate_store`.

---

## 7. Proposed commit contents

### Recommended include set

**Commit series A — F-01 (transitions)**  
`scripts/lib/tracking.py`, `scripts/lib/__init__.py`, `data/activity_log/act_20261123_stage_a_running.yaml`, `docs/status_transitions.md`

*Note: `tracking.py` also contains F-02/F-03; if splitting commits, either (1) one combined “remediation core” commit for `tracking.py`, or (2) accept F-02/F-03 land with F-01 in the same file commit.*

**Safer practical plan: 4 logical commits**

1. **Core library + schemas + project TTL/placeholders + activity**  
   - `scripts/lib/tracking.py`, `scripts/lib/__init__.py`  
   - `schemas/project.schema.json`, `schemas/hpc_snapshot.schema.json`  
   - `data/project.yaml`, `data/activity_log/act_20261123_stage_a_running.yaml`  
   - `data/hpc_snapshots/hpc_20261123T083639.yaml`

2. **Collectors/CLI/dashboard**  
   - `scripts/collect_slurm_readonly.py`, `scripts/compute_progress.py`  
   - `dashboard/generate.py`, `dashboard/public/index.html`

3. **F-04 path sanitization of data/docs**  
   - `README.md`, `DISCOVERY_REPORT.md`, `OPEN_QUESTIONS.md`, `INDEPENDENT_AUDIT_REPORT.md`  
   - all 7 `data/datasets/*.yaml`, `data/issues/issue_uneven_historical_products.yaml`  
   - `docs/hpc_monitoring.md`, `docs/progress_metrics.md`, `docs/security.md`, `docs/status_transitions.md`

4. **Tests + audit reports (sanitized)**  
   - `tests/test_remediation_f01_f04.py`, `tests/test_runs_and_dashboard.py`  
   - `GIT_STATE_AND_PUBLIC_EXPOSURE_REPORT.md`  
   - `PRE_COMMIT_REVIEW_REPORT.md`  
   - `FULL_REPOSITORY_REVIEW_REPORT.md` **only if sanitized first**

### Suggested messages

```
fix(tracking): enforce status transitions and evidence-based metrics

Wire activity-log transition checks into validate_store, strengthen
output coverage per required product, and classify HPC snapshots by TTL.
```

```
fix(security): replace absolute scratch/home paths with placeholders

Keep operational meaning via $CAWO_HINDCAST_BASE / $SCRATCH_HISTORICAL
without embedding host-specific absolute paths in the tip tree.
```

```
test: add F-01–F-04 remediation regression coverage
```

---

## 8. Excluded files and reasons

| Path | Action | Reason |
|------|--------|--------|
| `FULL_REPOSITORY_REVIEW_REPORT.md` | **Exclude until sanitized** | Contains absolute `/home/<user>/...` strings (`POTENTIALLY_SENSITIVE`) |
| Anything outside this repo | N/A | Out of scope |
| Live re-collected HPC snapshots with real usernames | Do not add | Would reintroduce identifiers |

If the owner wants the full review report in Git: sanitize path strings to `$HOME/...` first, then include as `AUDIT_REPORT`.

---

## 9. Remaining owner decisions

1. Authorize local commits (and author identity).  
2. Sanitize or permanently exclude `FULL_REPOSITORY_REVIEW_REPORT.md`.  
3. History scrub vs private vs accept public path history (unchanged by tip commit).  
4. Live GitHub tip verification before push.  
5. Scope Q1 (2024 vs 2025) and related open questions — **not** part of remediation commit.

---

## 10. Confirmation

- No files were modified for this review except **creation of this report**.
- Nothing was staged or committed.
- No push, pull, fetch, or history rewrite.
- No GitHub settings/visibility changes.
- No HPC job or scientific dataset access.
- No network remote verification performed.

---

## Appendix — Modified tracked files (name-status)

```
M DISCOVERY_REPORT.md
M INDEPENDENT_AUDIT_REPORT.md
M OPEN_QUESTIONS.md
M README.md
M dashboard/generate.py
M dashboard/public/index.html
M data/datasets/dataset_cls_hindcast_run.yaml
M data/datasets/dataset_cls_post_ocean2d.yaml
M data/datasets/dataset_cls_post_ocean3d.yaml
M data/datasets/dataset_cls_post_wrf2d.yaml
M data/datasets/dataset_cls_post_wrf3d.yaml
M data/datasets/dataset_internal_input_scratch.yaml
M data/datasets/dataset_internal_post_sample_20150113.yaml
M data/hpc_snapshots/hpc_20261123T083639.yaml
M data/issues/issue_uneven_historical_products.yaml
M data/project.yaml
M docs/hpc_monitoring.md
M docs/progress_metrics.md
M docs/security.md
M docs/status_transitions.md
M schemas/hpc_snapshot.schema.json
M schemas/project.schema.json
M scripts/collect_slurm_readonly.py
M scripts/compute_progress.py
M scripts/lib/__init__.py
M scripts/lib/tracking.py
M tests/test_runs_and_dashboard.py
```
