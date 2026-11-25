# ft2 vs CLS identity check, 2015-01-01

**Date:** 2026-11-25
**Audience:** `cawohdcst_ft2` operators
**Claim level:** reported
**Status:** Numeric comparison of one warm-start day. Not catalog VERIFIED and not scientifically ACCEPTED. The day is **not identical** to CLS by 2015-01-02 12:00 UTC.

---

## Run

| Item | Evidence |
|------|----------|
| Hindcast job | `610471`, partition HDCAST, account `HDCST-FT` |
| Mode | Continuing warm start. `NRREC = -1`. No `--day1` |
| Prior day | `20141231` triad copied from CLS into ft2 |
| Atmosphere IC | `wrfinput_d01` / `wrfbdy_d01` copied from the CLS run directory after metgrid failed on HDCAST |
| Comparison job | `610520` on partition DEV1 (sampled fields only) |
| Notebook | `notebooks/compare_ft2_cls_20150101.ipynb` |

A full scan of every WRF history field was cancelled (`610507`) because it was too expensive. This report uses the sampled ocean fields from job `610520`.

## Method

Hourly ROMS history from `his_00002` (2015-01-01 13:00 UTC) through `his_00025` (2015-01-02 12:00 UTC). Three-dimensional fields use the surface `s_rho` level. Land fill `1e37` is excluded. The wet-point count is 1,874,969.

The domain mean is an unweighted mean of finite points. Bias is `mean(ft2) − mean(CLS)`. RMSE is the pointwise gap. Correlation is Pearson on points that are finite in both files.

| Label | Variable | Slab |
|-------|----------|------|
| SWH | `Hwave` | significant wave height |
| arus u | `u_eastward` | surface |
| arus v | `v_northward` | surface |
| arus | speed | `hypot(u, v)` at the surface |
| salinity | `salt` | surface |
| sea temperature | `temp` | surface |

## Start of the compared window

At 2015-01-01 13:00 UTC every sampled field matches CLS exactly: bias, RMSE, and maximum absolute difference are 0, and correlation is 1. That is the evidence that the copied ROMS restart was read.

## End of the day

At 2015-01-02 12:00 UTC the domain-mean bias is still near zero, while the pointwise gap has grown.

| Field | Bias | RMSE | Max absolute difference | Correlation |
|-------|------|------|-------------------------|-------------|
| SWH | −8.1e-5 m | 0.024 m | 1.05 m | 0.9995 |
| arus u | −2.3e-5 m/s | 0.0096 m/s | 0.37 m/s | 0.9995 |
| arus v | +2.6e-5 m/s | 0.0081 m/s | 0.36 m/s | 0.9994 |
| arus speed | +2.0e-5 m/s | 0.0094 m/s | 0.32 m/s | 0.9990 |
| salinity | −1.9e-4 | 0.052 | 7.127 | 0.9969 |
| sea temperature | +2.4e-5 °C | 0.015 °C | 2.102 °C | 0.9999 |

Exact end-of-day maximum absolute differences from the notebook are SWH 1.050435 m, arus u 0.370110 m/s, arus v 0.359406 m/s, arus speed 0.316485 m/s, salinity 7.127007, and sea temperature 2.101772 °C.

## Time series and maps

The hourly series starts at a zero gap and the RMSE grows through the day. Correlation stays above 0.996. The maps are the surface fields at 2015-01-02 12:00 UTC.

![Hourly domain mean, bias, RMSE, and correlation for SWH, surface current speed, salinity, and sea temperature. CLS and ft2 means stay close while RMSE grows from zero after 13:00 UTC on 1 January.](reports/ft2_cls_20150101_timeseries.png)

![Surface maps at 2015-01-02 12:00 UTC for SWH, surface current speed, salinity, and sea temperature. Each row shows CLS, ft2, and ft2 minus CLS.](reports/ft2_cls_20150101_spatial.png)

## What this does not claim

File-size differences in the history files are not this comparison. A matched start plus a non-zero end-of-day gap means the warm start was read and the day then diverged. It does not set any dataset to VERIFIED or ACCEPTED, and it does not authorize a 20150201 continuation by itself.
