# Open Questions — Owner Decisions Required

**Status:** Unresolved as of 2026-11-23  
**Rule:** Do not treat progress percentages as authoritative until Q1 and Q3 are answered and recorded under Resolutions.

---

## Q1 — Final simulation period (30 vs 31 calendar years)

**Context:** Project is described as a 30-year hindcast with existing 1995–2014 (20 years) and remaining 2015–2025 described as 10 years. Inclusive 2015–2025 is **11** calendar years (total **31** if historical is 1995–2014).

**Decision needed:**

- Remaining target **2015–2024** (10 years → total 30), or
- Remaining target **2015–2025** (11 years → total 31), or
- Other exact start/end dates?

**Until resolved:** `data/project.yaml` keeps `scope.confirmed: null` and provisional remaining end `2025-12-31`.

---

## Q2 — Historical baseline acceptance

**Context:** On-disk CLS products are uneven:

- `ocean2d` postprocessed ends **2001-12-31**
- `ocean3d` / `wrf2d` / `wrf3d` postprocessed extend through **2015-01-31**
- Raw outputs are sparse; run directories extend to 2024 without verified completion semantics

**Decision needed:** Is 1995–2014 accepted as delivered baseline despite incomplete/uneven product coverage? Per-product acceptance rules?

---

## Q3 — Definition of a “complete year”

**Decision needed:**

- Required products (ocean2d, ocean3d, wrf2d, wrf3d, restarts, other)?
- Required validations and thresholds (owner-supplied; not invented here)?
- Who holds acceptance authority?

---

## Q4 — Team roster

**Decision needed:** Real display names / IDs for four members and role mapping to `member_01`…`member_04`.

---

## Q5 — GitHub repository policy

**Decision needed:**

- Keep repository public?
- Enable branch protection / required reviews?
- Authorize first push when ready?

---

## Q6 — CLS scratch content beyond 2014

**Context:** January 2015 postprocessed days and `cawo_hindcast_run` through 2024 exist under `$SCRATCH_HISTORICAL` (historical archive root).

**Decision needed:** Treat as CLS legacy, internal WIP, or out of scope for this tracker?

---

## Resolutions

| ID | Resolution | Date | Decided by |
|----|------------|------|------------|
| Q1 | *Unresolved* | | |
| Q2 | *Unresolved* | | |
| Q3 | *Unresolved* | | |
| Q4 | *Unresolved* | | |
| Q5 | *Unresolved* | | |
| Q6 | *Unresolved* | | |

When resolved, update this table **and** set `data/project.yaml` `scope.confirmed` (for Q1) plus related period/dataset statuses as appropriate. Record an activity-log entry.
