# Git State & Public Exposure Assessment

**Date:** 2026-11-23  
**Repository:** `inacawo-hindcast-progress` (absolute root omitted; local clone under the operator home directory)  
**Mode:** Read-only follow-up. No fetch, pull, push, history rewrite, file edits (except this report), or HPC access.

---

## Executive verdict

**LOCAL REMEDIATIONS UNCOMMITTED; COMMITTED HISTORY STILL CONTAINS ABSOLUTE HOME/SCRATCH PATHS; LIVE PUBLIC REMOTE TIP NOT VERIFIED.**

- Working tree holds F-01–F-04 remediations (unstaged + untracked); **none are in HEAD**.
- **15 of 17** local commits on `main` contain absolute `/home/...` and/or `/scratch/...` path strings.
- Local remote-tracking ref `refs/remotes/origin/main` **equals** HEAD (`e708bc9…`), which is **suggestive** that this tip was once associated with `origin`, but **live GitHub content was not verified** (no network/`ls-remote`/fetch per restrictions).
- Safe next step: commit remediations locally after owner approval; decide history scrub **before** any intentional public publish; do not assume the public remote is clean or empty without verification.

---

## A. Git state

| Item | Value |
|------|--------|
| Repository root | Local `inacawo-hindcast-progress` clone (path redacted in this report) |
| Current branch | `main` |
| HEAD | `e708bc93a52bcc45d4ab65373c4e2362cc4a8059` |
| HEAD subject | Add independent implementation audit report. |
| HEAD author | tyorus \<tyorus@users.noreply.github.com\> |
| Upstream branch | **None configured** (`git rev-parse @{u}` fails) |
| Tags | **None** |
| Local branches | `main` only |
| Remote-tracking | `refs/remotes/origin/main` → **same hash as HEAD** |
| Staged changes | **None** (`git diff --cached` empty) |
| Unstaged modified | 27 files |
| Untracked | 3 paths (see below) |

### `git status --short` (summary)

- **Modified (unstaged):** 27 files (docs, data, schemas, scripts, dashboard, tests, README, discovery/audit/open-questions).
- **Untracked:**
  - `FULL_REPOSITORY_REVIEW_REPORT.md`
  - `data/activity_log/act_20261123_stage_a_running.yaml`
  - `tests/test_remediation_f01_f04.py`
  - *(plus this report once written)* `GIT_STATE_AND_PUBLIC_EXPOSURE_REPORT.md`

### Diff statistics (unstaged vs HEAD)

- `git diff --stat`: **27 files changed, 644 insertions(+), 97 deletions(-)**
- `git diff --cached --stat`: empty

### Recent commit history (`main`)

```
e708bc9 Add independent implementation audit report.
4a45c84 Add GitHub Actions validation workflow and issue/PR templates.
1750c33 Add automated tests for validation, progress, and dashboard.
bc9b097 Add operational docs for metrics, procedures, and readiness.
edb2064 Add static dashboard generator and initial public HTML.
82ff8db Add validation, progress, helper, and read-only SLURM scripts.
1e83668 Add provisional project data, periods, datasets, tasks, and issues.
bc3999d Add JSON schemas for tracking entities and common definitions.
c15b381 Add repository README with boundaries and quick start.
bb1ac2d Add contributing guide for evidence-based tracking updates.
aa25ecb Add project charter defining scope and non-negotiable rules.
3996307 Add open owner questions including the period discrepancy.
7a87420 Add phased implementation plan for the tracking repository.
6ff2108 Add tracking system architecture proposal.
38f5a4c Add Phase 1 discovery report from workspace and HPC inspection.
57394f3 Add Python dependency pins for validators and tests.
068a368 Add gitignore for secrets, scientific outputs, and caches.
```

### Remote configuration (credentials redacted)

```
origin  git@github.com:devmetmar/inacawo-hindcast-progress.git (fetch)
origin  git@github.com:devmetmar/inacawo-hindcast-progress.git (push)
fetch   +refs/heads/*:refs/remotes/origin/*
```

No passwords/tokens observed in `remote.origin.*` config.

---

## B. Remediation mapping (F-01 – F-04)

**All remediation work is in the working tree only. Present in HEAD? No.**

| Finding | Changed / new files (WT) | Staged | Unstaged | Untracked | In HEAD? | Relevant tests |
|---------|--------------------------|--------|----------|-----------|----------|----------------|
| **F-01** Status transitions | `scripts/lib/tracking.py`, `scripts/lib/__init__.py`, `docs/status_transitions.md`, `data/activity_log/act_20261123_stage_a_running.yaml` | No | Yes (except new activity) | activity YAML | **No** | `tests/test_remediation_f01_f04.py` (untracked); existing transition unit tests in HEAD lack validator wiring |
| **F-02** Output coverage | `scripts/lib/tracking.py`, `docs/progress_metrics.md`, `dashboard/generate.py`, `dashboard/public/index.html`, `scripts/compute_progress.py` | No | Yes | — | **No** | `test_remediation_f01_f04.py` F-02 cases |
| **F-03** HPC TTL / stale | `scripts/lib/tracking.py`, `data/project.yaml`, `schemas/project.schema.json`, `schemas/hpc_snapshot.schema.json`, `data/hpc_snapshots/hpc_*.yaml`, `scripts/collect_slurm_readonly.py`, `docs/hpc_monitoring.md`, dashboard/CLI | No | Yes | — | **No** | F-03 cases in `test_remediation_f01_f04.py`; `test_runs_and_dashboard.py` fixture updated |
| **F-04** Path sanitization (current tree) | README, DISCOVERY/OPEN_QUESTIONS/INDEPENDENT_AUDIT (partial), `data/project.yaml`, datasets, issue evidence refs, docs/security | No | Yes | — | **No** (HEAD still has absolute paths) | Dashboard no-`/home/`/`/scratch/` assert in remediation tests |

### Match to previous audit claims

| Claim from full review | Local evidence now |
|------------------------|--------------------|
| Remediations implemented in WT, not committed | **Confirmed** |
| HEAD = audit report commit without F-01–F-04 code | **Confirmed** (`e708bc9`) |
| Tests added for remediations | **Confirmed as untracked** `tests/test_remediation_f01_f04.py` |
| Current-tree path placeholders | **Confirmed** in modified tracked files; HEAD still absolute |

---

## C. Git history exposure

### Commits containing absolute `/home/` and/or `/scratch/` strings

Reachable from local `main` (and thus from current HEAD):

| Commit | Notes (sanitized) |
|--------|-------------------|
| `38f5a4c` | Introduces discovery doc with home/scratch absolute paths |
| `3996307` | Open questions references scratch archive root |
| `1e83668` | Project/dataset YAML absolute scratch locations |
| `6ff2108` … `4a45c84` | Intermediate commits still **contain** those blobs (history continuity) |
| `e708bc9` | Independent audit report adds further home-path strings |

**Commits without those patterns (on `main`):**

- `068a368` — gitignore only  
- `57394f3` — requirements only  

**Total:** 15 / 17 commits on `main` have matching path strings in their trees.

### Categories of exposed content (sanitized)

- Operator **home** directory prefixes under `/home/<user>/…`
- HPC **scratch** prefixes under `/scratch/<space>/…` for internal and historical roots
- Dataset `location:` fields and discovery/audit narrative paths
- Mentions of HPC account identifiers in committed docs at HEAD

No credential/token/private-key values were sought beyond path/identifier patterns; none reported here.

### Reachability

- All listed commits are on local branch `main`.
- No tags.
- `refs/remotes/origin/main` points to `e708bc9` (same as HEAD), so **all 15 path-containing commits are ancestors of the local remote-tracking tip**.

### Remote exposure evidence and limitations

| Question | Finding |
|----------|---------|
| Do remote-tracking refs exist locally? | **Yes:** `origin/main` = `e708bc9` |
| Does local evidence prove those commits were pushed? | **Not proven.** Equality of `origin/main` and HEAD is **circumstantial** (could reflect a past push/fetch or a locally updated remote-tracking ref). Branch has **no upstream** configured. |
| Live GitHub tip / object presence | **`NOT VERIFIED`** — no fetch, no `ls-remote`, no API contact in this assessment |
| Can we claim commits are public? | **No.** Local clone + public *repo name* ≠ verified published objects |

**Do not treat “public GitHub repository” + local `origin/main` as proof of current public history content without an authorized live verification.**

---

## D. Safe next-step recommendations

### 1. Local remediation commit (recommended when authorized)

- Commit **only** remediation + review reports after owner approval.
- Prefer a clear series (e.g. F-01 / F-02 / F-03 / F-04 / tests / reports) or one well-described remediation series.
- Run `python scripts/validate_data.py` and `pytest -q` before commit.
- Do **not** push until history/publication decision is made.
- Note: untracked `FULL_REPOSITORY_REVIEW_REPORT.md` still contains some absolute path strings; sanitize or omit before committing if publishing.

### 2. History sanitization (if publishing a clean public history)

Because **15 commits** already embed absolute paths, a **new commit that only fixes the tip does not remove history exposure**.

Options (owner-authorized only; not performed here):

- **Filter-repo / BFG** rewrite to replace absolute prefixes with placeholders, then force-push with explicit approval; or  
- **Orphan/squash** rebuild from a sanitized tree as a new root (loses granular history); or  
- **Leave history**, keep remote **private**, or never push the contaminated commits.

Coordinate with anyone who may already have cloned `e708bc9`.

### 3. Publishing to GitHub

- First: authorized **live** check of remote tip (`ls-remote` / API) when allowed.
- If remote is still empty: consider pushing only after sanitization **or** accept that first push publishes the 15 contaminated commits.
- If remote already has `e708bc9`: tip cleanup commit is insufficient for history; sanitization or private visibility required for a clean public story.
- Do not force-push without explicit owner authorization.

### 4. Private vs public

| Choice | Implication |
|--------|-------------|
| **Keep/make private** | Reduces world-readable exposure; history still sensitive to collaborators with access |
| **Remain public** | Assume any pushed objects (including historical absolute paths) are world-readable |
| **Public + sanitized history** | Best if public collaboration is required without leaking home/scratch prefixes |

Owner should decide visibility (**OPEN_QUESTIONS Q5**) before push.

---

## E. Recommended next action (ordered)

1. Owner reviews uncommitted remediation diff.  
2. Sanitize or exclude any report files that still embed absolute paths.  
3. Authorize **local commits** of remediations (no push yet).  
4. Authorize **live remote verification**.  
5. Choose: private remote, sanitized history then public push, or accept public history with absolute paths.  
6. Only then push (and force-push only if explicitly approved after rewrite).

---

## Confirmation of non-modification (this assessment)

- No repository source/data files were modified for this assessment except **creation of this report**.
- No commits created.
- No push, pull, or fetch.
- No history rewrite.
- No GitHub settings or visibility changes.
- No HPC jobs, scientific datasets, or other repositories accessed or changed.

---

## Appendix — Unstaged file list (name-status)

```
M  DISCOVERY_REPORT.md
M  INDEPENDENT_AUDIT_REPORT.md
M  OPEN_QUESTIONS.md
M  README.md
M  dashboard/generate.py
M  dashboard/public/index.html
M  data/datasets/dataset_cls_hindcast_run.yaml
M  data/datasets/dataset_cls_post_ocean2d.yaml
M  data/datasets/dataset_cls_post_ocean3d.yaml
M  data/datasets/dataset_cls_post_wrf2d.yaml
M  data/datasets/dataset_cls_post_wrf3d.yaml
M  data/datasets/dataset_internal_input_scratch.yaml
M  data/datasets/dataset_internal_post_sample_20150113.yaml
M  data/hpc_snapshots/hpc_20261123T083639.yaml
M  data/issues/issue_uneven_historical_products.yaml
M  data/project.yaml
M  docs/hpc_monitoring.md
M  docs/progress_metrics.md
M  docs/security.md
M  docs/status_transitions.md
M  schemas/hpc_snapshot.schema.json
M  schemas/project.schema.json
M  scripts/collect_slurm_readonly.py
M  scripts/compute_progress.py
M  scripts/lib/__init__.py
M  scripts/lib/tracking.py
M  tests/test_runs_and_dashboard.py
?? FULL_REPOSITORY_REVIEW_REPORT.md
?? data/activity_log/act_20261123_stage_a_running.yaml
?? tests/test_remediation_f01_f04.py
?? GIT_STATE_AND_PUBLIC_EXPOSURE_REPORT.md
```
