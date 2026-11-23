# CLS baseline warm-start findings

**Date:** 2026-11-23  
**Audience:** `cawohdcst_ft2` operators continuing the hindcast after the CLS historical baseline  
**Status:** Hindcast job submission **deferred** until a warm-start ROMS restart is recovered  

---

## 1. Purpose

This report records investigation results for January 2015 on the CLS historical archive and defines how an **ft2** warm-start continuation should proceed **after ~20 years of CLS** production (approximately 1995–2014, with January 2015 inventory extending some post products).

Hindcast runs are **not** started in this tracking iteration. The dashboard day-coverage panel and this document are the deliverables until the restart blocker is cleared.

---

## 2. CLS ~20-year baseline

| Item | Evidence-based statement |
|------|--------------------------|
| Historical stream | Catalogued as `origin: cls_brazil` / `stream: historical_baseline` (~1995–2014) |
| Product coverage | Uneven (e.g. legacy `ocean2d` ends 2001-12-31; `ocean2d_with_tm01` / `ocean3d` / `wrf2d` / `wrf3d` extend through **2015-01-31**) |
| Acceptance | **Not** treated as scientifically ACCEPTED here — see `OPEN_QUESTIONS.md` Q2 / Q3 / Q6 |
| Scratch root | `$SCRATCH_HISTORICAL` → `/scratch/cawohdcst/data` (read-only for ft2 continuation work) |

January 2015 on CLS is **inventory extension evidence**, not ft2 internal delivery acceptance.

---

## 3. January 2015 inventory (CLS)

Under `/scratch/cawohdcst/data` (read-only checks, 2026-11-23):

| Layer | Result |
|-------|--------|
| `cawo_hindcast_run/f201501*` | **31/31** day directories |
| `cawo_hindcast_outputs/f201501*` | **31/31** |
| `postprocessed/ocean2d_with_tm01/f201501*` | **31/31** |
| `postprocessed/ocean3d`, `wrf2d`, `wrf3d` | **31/31** each |
| `postprocessed/ocean2d` (legacy tree) | **0** Jan 2015 dirs (delivery is under `ocean2d_with_tm01`) |
| Sample completion | `f20150101`, `f20150115`, `f20150131` logs include `ROMS/TOMS: DONE` and WRF SUCCESS through next-day 12Z |

**January 2025:** no `f202501*` run/output dirs on CLS — the finished month under discussion is **2015**.

Tracking note: `period_2015` remains remaining-internal / not year-complete; directory presence ≠ VERIFIED ≠ ACCEPTED.

---

## 4. Warm-start triad (from successful history)

Continuing (non–`--day1`) COAWST days in `inacawo-iht` require **all three** prior-day restarts:

| Component | Continuing template behaviour | Example from successful CLS day |
|-----------|-------------------------------|----------------------------------|
| **ROMS** | `NRREC == -1`, `ININAME` → prior `cawo_g2.8.0_rst_*_12.nc` under outputs | `f20150131` read `.../f20150130/cawo_g2.8.0_rst_20150130_12.nc` |
| **WRF** | `restart = .true.`, `RST_INNAME` → `../f<yesterday>/wrfrst_d01_<date>` | Log: `RESTART run: opening ../f20150130/wrfrst_...` |
| **SWAN** | `INITIAL HOTSTART MULTIPLE '../f<yesterday>/swan_rst.<today>.120000.dat'` | Present in Jan 2015 run dirs |

Same pattern on `f20150102` and `f20150115`.

**Skipping ROMS is not a warm start.** The only built-in path without that ROMS file is `--day1` (`NRREC == 0`, `ININAME` → `ocean_ini.nc`, WRF `restart = .false.`) — a **cold** ocean start, rejected for this continuation.

`copy_files_for_run.bash` does **not** stage restarts; they must already exist (or be copied into the ft2 tree).

---

## 5. Restart availability today (CLS-only)

| Component | January 2015 on `/scratch/cawohdcst` | Implication |
|-----------|--------------------------------------|-------------|
| SWAN hotstart | Present for **31/31** days | Handoff possible on wave side |
| WRF `wrfrst_*` | Present for **31/31** days (e.g. end of `f20150131` → `2015-02-01_12:00:00`) | Handoff possible on atmosphere side |
| ROMS `cawo_g2.8.0_rst_*.nc` | **0** files under CLS `cawo_hindcast_outputs` (and no `*rst*.nc` in that tree) | **No CLS warm-startable day** |

Logs for completed days show ROMS restart files were **written** historically (e.g. `f20150131` → `cawo_g2.8.0_rst_20150131_12.nc`). They are absent on disk now (consistent with `LcycleRST == T` / retention cleanup).

**CLS-only startable warm days: none** — including preferred **`20150201`**.

Shifting the start date within January 2015 does not help on CLS alone: every handoff still lacks ROMS rst.

*(ft2 early-1995 ROMS files under `/scratch/cawohdcst_ft2/data` are a different era and are out of scope for CLS-based continuation after the ~20y baseline.)*

---

## 6. ft2 execution boundary (when runs resume)

| Role | Path / rule |
|------|-------------|
| User | `cawohdcst_ft2` only |
| Workflow / model / deps | `$HOME/inacawo-iht`, `$HOME/inacawo-src`, `$HOME/inacawo-deps` |
| Writable base | `$CAWO_HINDCAST_BASE` → `/scratch/cawohdcst_ft2/inacawo-iht` (`cawo_hindcast_run`, `cawo_output`, `cawo_post`) |
| Shared static / offline | Read or symlink **in** per `inacawo-iht` preprocess design (`SHARED_DATA`, offline roots) — **do not edit** shared trees |
| CLS archive | **Read-only**; never `sbatch` into CLS run dirs; never overwrite CLS post/raw |

Tracking YAML may be updated under `$HOME/inacawo-hindcast-progress` without mutating scientific scratch.

---

## 7. How the hindcast should start after ~20 years of CLS

Intended handoff (once unblocked):

1. Treat CLS inventory through **2015-01-31** as the operational predecessor for remaining-internal work (subject to owner resolution of OPEN_QUESTIONS Q6 for catalog classification).
2. Recover a **2015-era ROMS** restart for the prior day `S-1` (preferred: `cawo_g2.8.0_rst_20150131_12.nc` for start **`S = 20150201`**).
3. Confirm WRF + SWAN restarts for that same prior day still exist on CLS (they do for all January 2015 days as of this report).
4. **Stage** the triad under ft2 only:
   - ROMS → `$CAWO_OUTPUT/f<S-1>/`
   - WRF + SWAN → `$CAWO_HINDCAST_RUN/f<S-1>/`
5. As `cawohdcst_ft2`, source `$HOME/inacawo-iht/setup_env.bash`, preprocess forcing for `S` (and ROMS day+1 as required), then:

```bash
./run_hindcast.bash --start S --end S    # NEVER pass --day1
./run_postprocess.bash --start S --end S
```

6. Register the run in the tracking catalog with `hpc_user: cawohdcst_ft2` and evidence refs; update day-presence inventory after outputs exist.

Until step 2 succeeds: **no submit**.

---

## 8. Open blockers / next actions

| Priority | Action |
|----------|--------|
| Blocker | Locate or recover `cawo_g2.8.0_rst_20150131_12.nc` (or another 2015 prior-day rst) without mutating CLS |
| Tracking | Keep day calendar / manifests updated (`data/manifests/day_presence_*.json`) |
| Policy | Resolve OPEN_QUESTIONS Q1–Q3 / Q6 before treating acceptance % as authoritative |
| Deferred | Warm-start stage → `20150201` (or chosen `S`) hindcast on ft2 → catalog run YAML |

---

## References

- Workflow: `$HOME/inacawo-iht/hindcast_run/README.md`, `in_templates/roms.in.template`, `namelist.input.template`, `swan.in.template`
- Inventory: `data/manifests/inventory_scan_20261123.json`, `data/manifests/day_presence_2015.json`
- Metrics / claim ladder: `docs/progress_metrics.md`, `OPEN_QUESTIONS.md`
- Dashboard: `dashboard/public/index.html` (Daily inventory coverage panel)
