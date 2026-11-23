# Architecture Proposal — INACAWO Hindcast Progress Tracking

**Status:** Approved for implementation (Phase 2+)  
**Decision date:** 2026-11-23  
**Constraint:** All implementation remains inside `inacawo-hindcast-progress`.

---

## 1. Goals

Provide a reliable, auditable, collaborative, scientifically defensible source of truth for:

- Project and year-level progress
- Workflow stage tracking
- HPC run metadata and evidence
- Dataset inventory references
- Validation and acceptance status
- Issues/blockers and team accountability

without modifying model code, HPC jobs, or scientific datasets.

---

## 2. Chosen architecture

**Local-first Git + YAML + JSON Schema + Python validators + generated static HTML dashboard.**

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Persistence | Version-controlled YAML under `data/` | Human-readable, reviewable, offline |
| Integrity | JSON Schema + Python referential checks | CI-enforceable without a database |
| Presentation | Generated static HTML | Fast, no server, works offline |
| HPC | Manual updates + optional read-only SLURM snapshot | Safe; stale-aware; no always-on dependency |
| Collaboration | One entity per file + helper scripts + PRs | Reduces merge conflict surface |

**Rejected alternatives:**

- SQLite as primary store — harder multi-user Git collaboration; unnecessary for current scale
- External SaaS / always-on DB — conflicts with offline HPC and “no paid infra” constraint
- Embedding NetCDF/logs in Git — size and sensitivity risk

---

## 3. Single source of truth

**Authoritative:** files under `data/`.

**Derived (never independent status stores):**

- `dashboard/public/` HTML
- Narrative docs under `docs/`
- Progress summaries printed by `scripts/compute_progress.py`

---

## 4. Evidence layers

Status claims are layered and never conflated:

| Layer | Meaning | Required to advance |
|-------|---------|---------------------|
| `reported` | Human statement | Actor + timestamp |
| `verified` | Technical evidence checked | Evidence refs (job ID, path, checksum, commit, etc.) |
| `accepted` | Designated reviewer acceptance | Reviewer ID + date + criteria |

A simulation year is **fully complete** only when configured completion criteria all pass (execution verified, required outputs verified, required validations verified, human acceptance).

---

## 5. Data ownership model

| Entity | Owner of record | Typical updater |
|--------|-----------------|-----------------|
| `project.yaml` | Project lead | Lead via PR |
| `team.yaml` | Project lead | Lead |
| `workflow_stages.yaml` | Project lead | Lead |
| `periods/*` | Period assignee | Owner / lead |
| `runs/*` | Run owner (HPC ops) | HPC operator |
| `datasets/*` | Data steward | Postprocess / inventory owner |
| `tasks/*` | Task owner | Owner |
| `issues/*` | Issue owner | Reporter / owner |
| `validations/*` | Validation owner | QA reviewer |
| `activity_log/*` | System / actor | Append-only via helpers |
| `hpc_snapshots/*` | Optional collector | Explicit read-only script |

---

## 6. Status axes

Keep execution and scientific acceptance separate.

**Execution:**  
`NOT_STARTED` → `READY` → `RUNNING` → `COMPLETED`  
Also: `BLOCKED`, `FAILED`, `CANCELLED`

**Scientific:**  
`NOT_VALIDATED` → `NEEDS_REVIEW` → `VERIFIED` → `ACCEPTED`  
Also: `FAILED_VALIDATION`

Illegal transitions are rejected by validators (see `docs/status_transitions.md`).

---

## 7. Progress metrics

Do **not** use arbitrary task counts as project completion.

Independent metrics:

1. **Execution coverage**
2. **Output coverage**
3. **Validation coverage**
4. **Acceptance coverage**

Overall project percentage uses **acceptance coverage over confirmed-scope periods only**.  
If scope is unconfirmed: show counts and a **PROVISIONAL** banner; do not present a misleading overall %.

Methodology details: `docs/progress_metrics.md`.

---

## 8. Configurable scope

```yaml
scope:
  confirmed: null   # set only after owner decision
  provisional:
    historical_claimed: { start: "1995-01-01", end: "2014-12-31" }
    remaining_claimed:  { start: "2015-01-01", end: "2025-12-31" }
```

Period files may exist for provisional years but remain labeled provisional until `scope.confirmed` is set.

---

## 9. HPC integration

1. **Manual mode (default):** operators record job metadata into `data/runs/`.
2. **Optional collector:** `scripts/collect_slurm_readonly.py` — user-scoped, time-bounded `squeue`/`sacct` only; writes timestamped snapshots.

Never: `sbatch`, `scancel`, or job mutation from this repository.

---

## 10. Security

- Public GitHub: no credentials, tokens, private keys, or full sensitive logs.
- Store path references and checksum/manifest pointers only.
- `.gitignore` blocks NetCDF, large binaries, and credential patterns.
- Prefer member IDs over personal identifying data until policy is clarified.

Details: `docs/security.md`.

---

## 11. Collaboration model (four members)

Placeholders `member_01` … `member_04` until real names are supplied.  
Each Task/Period/Run/Issue has `owner` and optional `reviewer`.  
Shared changes go through branches/PRs; CI validates schemas and integrity.

---

## 12. Architecture decision record summary

| ID | Decision |
|----|----------|
| ADR-001 | Git + YAML as system of record |
| ADR-002 | JSON Schema + Python for validation |
| ADR-003 | Static generated dashboard |
| ADR-004 | Three-layer evidence model |
| ADR-005 | Separate execution vs scientific status |
| ADR-006 | Provisional scope until owner confirmation |
| ADR-007 | Read-only optional SLURM snapshots |
| ADR-008 | No scientific data files in Git |
