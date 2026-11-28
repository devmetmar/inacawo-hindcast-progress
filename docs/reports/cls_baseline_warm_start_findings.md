# CLS baseline warm-start findings

**Date:** 2026-11-23  
**Audience:** `cawohdcst_ft2` operators continuing the hindcast after the CLS historical baseline  
**Status:** ROMS restarts located under CLS `postprocessed/roms_rst` (2026-11-23 re-search). On 2026-11-25 an ft2 warm start of **20150101** was run and compared with CLS. The day is **not identical**. Days `20150102` through `20150107` were then chained from that ft2 restart and are in the same report. See `ft2_cls_20150101_identity.md`. On 2026-11-26 ft2 submitted a warm-start chain **20150201–20150228** from the CLS `20150131` triad (not from the diverged January ft2 restarts). Unified log: `$WORK_BASE/logs/hindcast/feb2015_cls_chain_*.log`. Claim level reported only. No CLS February history exists for identity comparison. On 2026-11-27 ft2 submitted a warm-start continuation **20150301–20150630** from the ft2 `20150228` triad (CLS forcing copy; no Mercator). Unified log: `$WORK_BASE/logs/hindcast/mar_jun2015_chain_*.log`. Cap is 30 Jun 2015. Claim level reported only. <!-- MAR_JUN2015_CHAIN_NOTE -->  

---

## 1. Purpose

This report records investigation results for January 2015 on the CLS historical archive and defines how an **ft2** warm-start continuation should proceed **after ~20 years of CLS** production (approximately 1995–2014, with January 2015 inventory extending some post products).

Hindcast **submit** remains operator-deferred. The dashboard day-coverage panel, CLS `roms_rst` catalog record, and this document capture inventory and the warm-start handoff procedure now that ROMS restarts are located.

---

## 2. CLS ~20-year baseline

| Item | Evidence-based statement |
|------|--------------------------|
| Historical stream | Catalogued as `origin: cls_brazil` / `stream: historical_baseline` (~1995–2014) |
| Product coverage | Uneven (e.g. legacy `ocean2d` ends 2001-12-31; `ocean2d_with_tm01` / `ocean3d` / `wrf2d` / `wrf3d` extend through **2015-01-31**) |
| Acceptance | **Not** treated as scientifically ACCEPTED here — see `OPEN_QUESTIONS.md` Q2 / Q3 / Q6 |
| Scratch root | `$SCRATCH_HISTORICAL` (read-only for ft2 continuation work) |

January 2015 on CLS is **inventory extension evidence**, not ft2 internal delivery acceptance.

---

## 3. January 2015 inventory (CLS)

Under `$SCRATCH_HISTORICAL` (read-only checks, 2026-11-23):

| Layer | Result |
|-------|--------|
| `cawo_hindcast_run/f201501*` | **31/31** day directories |
| `cawo_hindcast_outputs/f201501*` | **31/31** |
| `postprocessed/ocean2d_with_tm01/f201501*` | **31/31** |
| `postprocessed/ocean3d`, `wrf2d`, `wrf3d` | **31/31** each |
| `postprocessed/ocean2d` (legacy tree) | **0** Jan 2015 dirs (delivery is under `ocean2d_with_tm01`) |
| `postprocessed/roms_rst/f201501*` | **31/31** (`cawo_g2.8.0_rst_*_12.nc`, ~14 GiB each) |
| Sample completion | `f20150101`, `f20150115`, `f20150131` logs include `ROMS/TOMS: DONE` and WRF SUCCESS through next-day 12Z |

**January 2025:** no `f202501*` run/output dirs on CLS — the finished month under discussion is **2015**.

Tracking note: the 2015 period record remains remaining-internal / not year-complete; directory presence ≠ VERIFIED ≠ ACCEPTED.

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

### Where ROMS restarts actually live

An earlier check that only looked under `cawo_hindcast_outputs/` reported **zero** ROMS rst files. That was **incomplete**.

A broader search found the archived ROMS restarts here:

| Path | Contents |
|------|----------|
| `$SCRATCH_HISTORICAL/data/postprocessed/roms_rst/` | **7336** day dirs `fYYYYMMDD` |
| Span | `f19950101` … `f20150131` |
| Naming | `cawo_g2.8.0_rst_<YYYYMMDD>_12.nc` (~14 GiB each) |
| January 2015 | **31/31** days present |

Example (preferred prior day for Feb start):

`$SCRATCH_HISTORICAL/postprocessed/roms_rst/f20150131/cawo_g2.8.0_rst_20150131_12.nc`

They are **not** retained next to history files under `cawo_hindcast_outputs/` (run-time `RSTNAME` path); they are **postprocessed/archived** under `roms_rst/`.

Other spots checked: `cawo_hindcast_run` (no ROMS nc rst), `mercator` (0), ft2/ft early trees (only sparse 1995 samples on ft2 — not needed for 2015 handoff).

### Triad for preferred start `20150201` (prior day `20150131`)

| Component | Location | Status |
|-----------|----------|--------|
| **ROMS** | `postprocessed/roms_rst/f20150131/cawo_g2.8.0_rst_20150131_12.nc` | **PRESENT** (14 G) |
| **WRF** | `cawo_hindcast_run/f20150131/wrfrst_d01_2015-02-01_12:00:00_*` | **PRESENT** (5952 shards) |
| **SWAN** | `cawo_hindcast_run/f20150131/swan_rst.20150201.120000.dat-*` | **PRESENT** (672 shards) |

**CLS warm-startable day (evidence):** **`20150201`** (and any other Jan 2015+1 day whose prior `roms_rst` + WRF/SWAN exist — all Jan 2015 priors appear populated).

---

## 6. ft2 execution boundary (when runs resume)

| Role | Path / rule |
|------|-------------|
| User | `cawohdcst_ft2` only |
| Workflow / model / deps | `$HOME/inacawo-iht`, `$HOME/inacawo-src`, `$HOME/inacawo-deps` |
| Writable base | `$CAWO_HINDCAST_BASE` (`cawo_hindcast_run`, `cawo_output`, `cawo_post`) |
| Shared static / offline | Read or symlink **in** per `inacawo-iht` preprocess design (`SHARED_DATA`, offline roots) — **do not edit** shared trees |
| CLS archive | **Read-only**; never `sbatch` into CLS run dirs; never overwrite CLS post/raw |

Tracking YAML may be updated under `$HOME/inacawo-hindcast-progress` without mutating scientific scratch.

---

## 7. How the hindcast should start after ~20 years of CLS

Intended handoff (once unblocked):

1. Treat CLS inventory through **2015-01-31** as the operational predecessor for remaining-internal work (subject to owner resolution of OPEN_QUESTIONS Q6 for catalog classification).
2. **ROMS rst is available** at `postprocessed/roms_rst/f20150131/…` (not under `cawo_hindcast_outputs`). Preferred start **`S = 20150201`**.
3. Confirm WRF + SWAN for `f20150131` (confirmed present as of this report).
4. **Stage** the triad under ft2 only (read from CLS, write to ft2 — do not modify CLS):
   - ROMS → `$CAWO_OUTPUT/f20150131/` (copy or symlink from `postprocessed/roms_rst/f20150131/`)
   - Or point `ININAME` at the CLS `roms_rst` path if site policy allows read-only use without copy
   - WRF + SWAN → `$CAWO_HINDCAST_RUN/f20150131/` (copy/symlink from CLS run dir)
5. As `cawohdcst_ft2`, source `$HOME/inacawo-iht/setup_env.bash`, preprocess forcing for `20150201` (and ROMS day+1 as required), then:

```bash
./run_hindcast.bash --start 20150201 --end 20150201    # NEVER pass --day1
./run_postprocess.bash --start 20150201 --end 20150201
```

6. Register the run in the tracking catalog with `hpc_user: cawohdcst_ft2` and evidence refs; update day-presence inventory after outputs exist.

---

## 8. Open blockers / next actions

| Priority | Action |
|----------|--------|
| Cleared | ROMS rst archive found: `$SCRATCH_HISTORICAL/data/postprocessed/roms_rst/` |
| Next | Operator decision on postprocess / inventory for February 2015 outputs |
| Tracking | Keep day calendar / manifests updated; catalog `roms_rst` as a dataset when ready |
| Policy | Resolve OPEN_QUESTIONS Q1–Q3 / Q6 before treating acceptance % as authoritative |
| Done (reported) | ft2 warm start `20150101` through `20150107` compared with CLS; not identical. See `ft2_cls_20150101_identity.md` |
| Done (reported) | ft2 warm start `20150201`–`20150228` from CLS `20150131`; see unified hindcast log |
| Done (reported) | ft2 warm start `20150301`–`20150630` from ft2 `20150228`; see unified hindcast log |

---

## References

- Workflow: `$HOME/inacawo-iht/hindcast_run/README.md`, `in_templates/roms.in.template`, `namelist.input.template`, `swan.in.template`
- Inventory: `data/manifests/inventory_scan_20261123.json`, `data/manifests/day_presence_2015.json`
- Metrics / claim ladder: `docs/progress_metrics.md`, `OPEN_QUESTIONS.md`
- Dashboard: `dashboard/public/index.html` (Daily inventory coverage panel)
