# Implementation Plan — INACAWO Hindcast Progress Tracking

**Repository:** `inacawo-hindcast-progress` only  
**Rule:** Do not modify model source, HPC working dirs, jobs, or scientific outputs.

---

## Phase 1 — Discovery (this document set)

**Deliverables:**

- [x] `DISCOVERY_REPORT.md`
- [x] `ARCHITECTURE_PROPOSAL.md`
- [x] `IMPLEMENTATION_PLAN.md`
- [x] `OPEN_QUESTIONS.md`
- [x] Initial `README.md` and `.gitignore`

**Exit criteria:** Architecture approved; open questions documented; no application code required yet.

---

## Phase 2 — Tracking foundation

**Deliverables:**

- Repository skeleton (`schemas/`, `data/`, `scripts/`, `docs/`, `.github/`)
- `PROJECT_CHARTER.md`, `CONTRIBUTING.md`
- JSON Schemas for all entities
- Provisional `data/project.yaml`, `team.yaml`, `workflow_stages.yaml`
- Period stubs for provisional remaining years (labeled provisional)
- Dataset inventory stubs for known CLS/internal evidence (facts only; no fabricated completion)
- Status transition and progress metric documentation
- CI workflow for schema/integrity validation

**Exit criteria:** `scripts/validate_data.py` passes on checked-in data.

---

## Phase 3 — Tracking interface

**Deliverables:**

- `dashboard/generate.py` → static `dashboard/public/index.html`
- Year grid, stage progress, blockers, workload, evidence links
- Provisional/unconfirmed banners
- Helper CLIs: `new_period.py`, `new_run.py`, `new_task.py`, `new_issue.py`, `log_activity.py`
- Optional `collect_slurm_readonly.py`

**Exit criteria:** Dashboard renders from data without inventing status; UNKNOWN/NOT_VERIFIED shown when absent.

---

## Phase 4 — Validation and QA

**Deliverables:**

- Pytest suite: schema, unique IDs, referential integrity, dates, transitions, progress math, retry/failure, stale HPC snapshots
- Dashboard consistency checks

**Exit criteria:** `pytest` green; validators fail intentionally broken fixtures.

---

## Phase 5 — Operational readiness

**Deliverables:**

- User guide, onboarding, update procedures
- Run registration, failure/recovery, validation procedures
- Backup/recovery and maintenance notes
- `docs/operational_readiness.md` checklist

**Exit criteria:** Checklist items for tooling pass; science thresholds and owner scope confirmation remain explicitly open until owners decide.

---

## Work rules (all phases)

1. Tracking only — never launch/modify hindcast jobs.
2. Never invent job IDs, validation outcomes, or completion.
3. Mark unknown information explicitly.
4. Distinguish reported / verified / accepted.
5. Keep remaining period configurable until confirmed.
6. No push/merge without authorization.
7. No paid external services.

---

## Suggested local commands

```bash
# Prefer the hindcast conda env when available
export PATH="$HOME/inacawo-deps/miniforge3/envs/hindcast/bin:$PATH"

cd $HOME/inacawo-hindcast-progress
python scripts/validate_data.py
python scripts/compute_progress.py
python dashboard/generate.py
pytest -q
```
