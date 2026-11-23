# INACAWO Hindcast Progress Tracking — Discovery Report

**Phase:** 1 — Discovery and Assessment  
**Date:** 2026-11-23  
**Author:** Tracking system setup (automated discovery)  
**Scope of inspection:** Read-only. No scientific jobs were launched or modified.

**Legend:** **Verified** | **Observation** | **Assumption** | **Recommendation** | **Open question**

---

## 1. Workspace assessment

**Verified** — Multi-root Cursor workspace roots are accessible:

| Folder | Path (portable) | Role |
|--------|------------------|------|
| `inacawo-iht` | `$HOME/inacawo-iht` | Preprocess / hindcast / postprocess workflow |
| `inacawo-src` | `$HOME/inacawo-src` | COAWST build helpers and binaries |
| `inacawo-deps` | `$HOME/inacawo-deps` | Conda env, LiveOcean, COAWST library env |
| `apps` | `$HOME/apps` | Installed application dependencies |
| `scratch-inacawo-iht` | `$CAWO_HINDCAST_BASE` | Internal IHT working scratch (~81G) |
| previous hindcast | `$SCRATCH_HISTORICAL` | CLS Brazil historical archive |
| `inacawo-hindcast-progress` | `$HOME/inacawo-hindcast-progress` | Dedicated tracking repository |

**Verified** — Scientific workflow is day-based COAWST (WRF–ROMS–SWAN). Each integration day uses directory `fYYYYMMDD`. Stage entry points are CLI date-range driven (`--start` / `--end`); no hardcoded 30-year campaign definition exists in `inacawo-iht` configs.

---

## 2. Tracking repository assessment

**Verified** (as of discovery):

- Working tree contained only `.git` (no tracked content prior to Phase 1 docs).
- Branch intent: `main`; zero commits at discovery time.
- Remote: `git@github.com:devmetmar/inacawo-hindcast-progress.git`
- GitHub repository: public and empty.
- `gh` CLI was not installed on the HPC host.

**Recommendation:** Greenfield tracking repository. All tracking implementation remains inside this repo only.

---

## 3. Project metadata inventory

### 3.1 Source / dependency / workflow revisions (Verified)

| Component | Evidence |
|-----------|----------|
| `inacawo-iht` HEAD | `dfa52934654a1357e81470175bcd384526ee47d8` |
| `inacawo-src` HEAD | `a5cfc5eb3b310e6e6423222c30e8f4e126a9cfac` |
| `inacawo-deps` HEAD | `e3457cdd31c914be3310ab843c6965bce27d20ec` |
| COAWST source tarball sha256 | `617afa3addf449a4943a6c31771a7ea028969d688b38aee269b517bff8106f73` |
| `coawstM` ramp / no_ramp | Present under `inacawo-src/binaries/`; built 2026-10-20 (SLURM jobs 568717 / 568718) |

### 3.2 Internal scratch `$CAWO_HINDCAST_BASE` (Verified)

| Path | Approx. size | Notes |
|------|--------------|-------|
| `cawo_input/` | ~70G | Sparse sample days (1995, 2000, 2021 Seroja, late 2025 / early 2026) |
| `cawo_output/` | symlink only | Points to CLS `f20150113` |
| `cawo_post/` | ~8.5G | Only `f20150113` for ocean2d/3d and wrf2d/3d |
| `validation/` | ~2.0G | Argo/WOD/WRF–ERA5 windows around 1995-12 / 1996-01 |
| `deps_tarballs/`, `src_tarballs/` | ~0.7G | Shared install artifacts + SHA256SUMS |

**Observation:** Internal scratch appears to be staging/test material, not continuous 2015+ production.

### 3.3 Historical archive `$SCRATCH_HISTORICAL/data` (Verified, read-only)

| Product | `fYYYYMMDD` span | Distinct years |
|---------|------------------|----------------|
| `postprocessed/ocean2d` | 1995-01-01 … **2001-12-31** | 7 |
| `postprocessed/ocean2d_with_tm01` | **2002-01-01 … 2015-01-31** | 14 (re-inventory 2026-11-23) |
| `postprocessed/ocean3d` | 1995-01-01 … **2015-01-31** | 21 |
| `postprocessed/wrf2d` | 1995-01-01 … **2015-01-31** | 21 |
| `postprocessed/wrf3d` | 1995-01-01 … **2015-01-31** | 21 |
| `cawo_hindcast_outputs` | sparse 2000–2015 (47 day dirs) | 16 |
| `cawo_hindcast_run` | 1996-12-30 … **2024-12-31** (~8403 dirs) | 24 |
| `era5` | ~1995-01-01 … 2016-01-01 | forcing archive |

**Critical observation (updated 2026-11-23):** CLS `ocean2d` is split across two folders (`ocean2d` for 1995–2001 and `ocean2d_with_tm01` for 2002–2015-01). Combined day-folder coverage aligns with ocean3d/WRF spans, but **integrity remains NOT_VERIFIED** and human acceptance rules are still open. Presence of `cawo_hindcast_run` directories through 2024 does **not** imply verified scientific completion.

**Unknown:** Exact byte sizes of each `$SCRATCH_HISTORICAL/data/*` subtree (background `du` was aborted).

### 3.4 HPC scheduler (Verified)

- SLURM 24.11.5 available (`squeue`, `sacct`, `sinfo`, `scontrol`).
- Partitions observed: `DEV1*` (default), `HDCAST`, `ENS1`.
- No jobs queued/running for the internal tracking HPC user at discovery time.
- IHT templates prefer HDCAST when allowed, else DEV1.

### 3.5 Team (Verified absence)

No team member names were found in accessible READMEs. Only organizational signals (`devmetmar`, `pusmar.org`, HPC users `cawohdcst` / `cawohdcst_ft2`).

---

## 4. Period discrepancy (mandatory)

**Open question — owner decision required.**

Stated project language:

- “30-year hindcast”
- Existing: 1995–2014 (20 calendar years)
- Remaining: 2015–2025 described as “10 years”

**Arithmetic fact:** 2015–2025 inclusive = **11** calendar years → 1995–2025 inclusive = **31** years.

Until confirmed, tracking uses configurable provisional scope and does **not** hardcode total years or overall completion percentages based on an assumed denominator.

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

---

## 5. Workflow stages observed

**Verified** stages in `inacawo-iht`:

1. **Bootstrap** — `setup_env.bash` / conda `hindcast` / Intel COAWST env  
2. **Preprocess** — ERA5, GLORYS, WPS, SWAN BC, ROMS IC/BC  
3. **Hindcast execution** — per-day folders, namelists, copy, `sbatch`  
4. **Postprocess** — ocean2d/3d, wrf2d/3d to CAWO grid  
5. **Validation** — present under scratch `validation/` (methods/thresholds not formally accepted in tracking)

**Recommendation:** Model configurable stages A–F in tracking data (preparation → model prep → execution → output → validation → integration), aligned with but not hard-wired to these entry points.

---

## 6. Assumptions and non-actions

**Assumptions (explicit):**

- Tracking repository is the future operational source of truth for progress.
- Four internal team members will collaborate; names remain placeholders until supplied.
- Scientific acceptance thresholds will be supplied by owners; none are invented here.

**Non-actions during discovery (mandatory):**

- No job submission, cancellation, or modification.
- No changes to model source, configs, dependencies, or scientific outputs.
- No push to GitHub without authorization.
- No fabricated job IDs, validation results, or completion claims.

---

## 7. Discovery conclusions

1. Tracking repo was empty and ready for a Git-native system.  
2. Workflow and reproducibility metadata are available from companion repos and build_info.  
3. Historical coverage must be tracked **per product stream**, not as a single boolean “20 years done.”  
4. Remaining period end year is **unconfirmed**; architecture must remain configurable.  
5. SLURM read-only monitoring is feasible; tracking must not depend on a permanent HPC connection.

Next documents: [ARCHITECTURE_PROPOSAL.md](ARCHITECTURE_PROPOSAL.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
