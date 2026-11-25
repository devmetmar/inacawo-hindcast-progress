# ft2 vs CLS identity check, 2015-01-01 through 2015-01-07

**Date:** 2026-11-25
**Audience:** `cawohdcst_ft2` operators
**Claim level:** reported
**Status:** Numeric comparison of seven chained warm-start days. Not catalog VERIFIED and not scientifically ACCEPTED. The chain is **not identical** to CLS. Only the first history hour of 2015-01-01 matches.

---

## Run

| Item | Evidence |
|------|----------|
| Hindcast jobs | `610471` (20150101), `610669` (20150102), `610704` (20150103), `610763` (20150104), `610804` (20150105), `610843` (20150106), `610851` (20150107). Partition HDCAST, account `HDCST-FT` |
| Mode | Continuing warm start. `NRREC = -1`. No `--day1`. Each later day reads the ft2 restart written by the previous day |
| Prior day | `20141231` triad copied from CLS into ft2 before 20150101 |
| Atmosphere IC | `wrfinput_d01` / `wrfbdy_d01` copied from the CLS run directory after metgrid failed on HDCAST |
| History | 24 hourly records per day under `$CAWO_OUTPUT` and `$SCRATCH_HISTORICAL` |
| Comparison jobs | `610859` ocean sample, then `610870` on DEV1 with 10 m wind added |
| Notebook | `notebooks/compare_ft2_cls_20150101.ipynb` |

A full scan of every WRF history field was cancelled (`610507`) because it was too expensive. This report uses the sampled ocean fields from job `610859`.

## Method

Hourly ROMS history from `his_00002` (13:00 UTC) through `his_00025` (12:00 UTC the next day), for hindcast days 20150101 through 20150107. Three-dimensional fields use the surface `s_rho` level. Land fill `1e37` is excluded. The wet-point count is 1,874,969 at every sampled hour.

The domain mean is an unweighted mean of finite points. Bias is `mean(ft2) − mean(CLS)`. RMSE is the pointwise gap. Correlation is Pearson on points that are finite in both files.

| Label | Variable | Slab |
|-------|----------|------|
| SWH | `Hwave` | significant wave height |
| arus u | `u_eastward` | surface |
| arus v | `v_northward` | surface |
| arus | speed | `hypot(u, v)` at the surface |
| salinity | `salt` | surface |
| sea temperature | `temp` | surface |
| angin u | `UX10` | 10 m wind, full WRF grid |
| angin v | `VX10` | 10 m wind, full WRF grid |
| angin | speed | `hypot(UX10, VX10)` |

The 10 m wind sample uses `wrfhtr_d01_*` at the same hours. Its grid count is 2,305,200. It is not limited to the ocean wet points.

Days after 20150101 are not restarted from CLS. The 13:00 hour of each later day already carries the gap left by the previous ft2 day.

## Start of 1 January

At 2015-01-01 13:00 UTC every sampled field, including 10 m wind, matches CLS exactly: bias, RMSE, and maximum absolute difference are 0, and correlation is 1. That is the evidence that the copied ROMS restart and the copied WRF history at that hour were read. No later sampled hour is identical.

## 13:00 UTC each day

| Day | Time (UTC) | Field | Bias | RMSE | Max abs | Corr |
|-----|------------|-------|------|------|---------|------|
| 20150101 | 2015-01-01 13:00:00 | SWH | 0 | 0 | 0 | 1.0000 |
| 20150101 | 2015-01-01 13:00:00 | arus u | 0 | 0 | 0 | 1.0000 |
| 20150101 | 2015-01-01 13:00:00 | arus v | 0 | 0 | 0 | 1.0000 |
| 20150101 | 2015-01-01 13:00:00 | arus speed | 0 | 0 | 0 | 1.0000 |
| 20150101 | 2015-01-01 13:00:00 | salinity | 0 | 0 | 0 | 1.0000 |
| 20150101 | 2015-01-01 13:00:00 | sea temperature | 0 | 0 | 0 | 1.0000 |
| 20150101 | 2015-01-01 13:00:00 | angin u | 0 | 0 | 0 | 1.0000 |
| 20150101 | 2015-01-01 13:00:00 | angin v | 0 | 0 | 0 | 1.0000 |
| 20150101 | 2015-01-01 13:00:00 | angin speed | 0 | 0 | 0 | 1.0000 |
| 20150102 | 2015-01-02 13:00:00 | SWH | -3.85e-4 | 0.0262 | 0.9462 | 0.9994 |
| 20150102 | 2015-01-02 13:00:00 | arus u | -7.70e-5 | 0.0106 | 0.3669 | 0.9994 |
| 20150102 | 2015-01-02 13:00:00 | arus v | 6.32e-5 | 0.0092 | 0.4030 | 0.9993 |
| 20150102 | 2015-01-02 13:00:00 | arus speed | -9.63e-6 | 0.0103 | 0.3641 | 0.9988 |
| 20150102 | 2015-01-02 13:00:00 | salinity | -9.61e-5 | 0.0605 | 9.9741 | 0.9957 |
| 20150102 | 2015-01-02 13:00:00 | sea temperature | 6.03e-5 | 0.0161 | 1.9464 | 0.9999 |
| 20150102 | 2015-01-02 13:00:00 | angin u | -0.0057 | 0.8339 | 22.826 | 0.9859 |
| 20150102 | 2015-01-02 13:00:00 | angin v | -4.52e-4 | 0.8412 | 25.395 | 0.9738 |
| 20150102 | 2015-01-02 13:00:00 | angin speed | -3.64e-4 | 0.7635 | 17.536 | 0.9725 |
| 20150103 | 2015-01-03 13:00:00 | SWH | -0.0020 | 0.0566 | 0.9924 | 0.9964 |
| 20150103 | 2015-01-03 13:00:00 | arus u | -3.56e-4 | 0.0215 | 0.4928 | 0.9975 |
| 20150103 | 2015-01-03 13:00:00 | arus v | 2.08e-4 | 0.0179 | 0.4202 | 0.9971 |
| 20150103 | 2015-01-03 13:00:00 | arus speed | -7.74e-5 | 0.0209 | 0.4294 | 0.9951 |
| 20150103 | 2015-01-03 13:00:00 | salinity | 4.77e-4 | 0.0746 | 13.312 | 0.9935 |
| 20150103 | 2015-01-03 13:00:00 | sea temperature | 9.02e-4 | 0.0378 | 3.2545 | 0.9995 |
| 20150103 | 2015-01-03 13:00:00 | angin u | -0.0113 | 1.2076 | 21.536 | 0.9733 |
| 20150103 | 2015-01-03 13:00:00 | angin v | -0.0058 | 1.2741 | 20.220 | 0.9255 |
| 20150103 | 2015-01-03 13:00:00 | angin speed | 0.0106 | 1.1180 | 21.597 | 0.9283 |
| 20150104 | 2015-01-04 13:00:00 | SWH | -0.0013 | 0.0605 | 1.0463 | 0.9947 |
| 20150104 | 2015-01-04 13:00:00 | arus u | -4.19e-4 | 0.0246 | 0.5000 | 0.9966 |
| 20150104 | 2015-01-04 13:00:00 | arus v | -0.0013 | 0.0217 | 0.4408 | 0.9956 |
| 20150104 | 2015-01-04 13:00:00 | arus speed | 3.88e-4 | 0.0240 | 0.4501 | 0.9936 |
| 20150104 | 2015-01-04 13:00:00 | salinity | 9.28e-4 | 0.0938 | 12.276 | 0.9897 |
| 20150104 | 2015-01-04 13:00:00 | sea temperature | 4.34e-4 | 0.0499 | 2.4471 | 0.9990 |
| 20150104 | 2015-01-04 13:00:00 | angin u | 0.0056 | 1.3304 | 26.052 | 0.9641 |
| 20150104 | 2015-01-04 13:00:00 | angin v | -0.0159 | 1.4155 | 20.999 | 0.8916 |
| 20150104 | 2015-01-04 13:00:00 | angin speed | 0.0089 | 1.2208 | 25.290 | 0.9032 |
| 20150105 | 2015-01-05 13:00:00 | SWH | -0.0033 | 0.0708 | 1.1050 | 0.9928 |
| 20150105 | 2015-01-05 13:00:00 | arus u | -6.16e-4 | 0.0300 | 0.5470 | 0.9951 |
| 20150105 | 2015-01-05 13:00:00 | arus v | 2.48e-4 | 0.0252 | 0.5600 | 0.9939 |
| 20150105 | 2015-01-05 13:00:00 | arus speed | 3.45e-5 | 0.0293 | 0.5365 | 0.9911 |
| 20150105 | 2015-01-05 13:00:00 | salinity | -1.04e-4 | 0.0931 | 14.494 | 0.9899 |
| 20150105 | 2015-01-05 13:00:00 | sea temperature | -0.0017 | 0.0617 | 2.8107 | 0.9984 |
| 20150105 | 2015-01-05 13:00:00 | angin u | -0.0203 | 1.4136 | 21.521 | 0.9527 |
| 20150105 | 2015-01-05 13:00:00 | angin v | -0.0023 | 1.4142 | 20.866 | 0.9086 |
| 20150105 | 2015-01-05 13:00:00 | angin speed | -0.0133 | 1.2848 | 17.686 | 0.8821 |
| 20150106 | 2015-01-06 13:00:00 | SWH | 1.85e-4 | 0.0840 | 1.1228 | 0.9894 |
| 20150106 | 2015-01-06 13:00:00 | arus u | -8.26e-4 | 0.0314 | 0.4583 | 0.9945 |
| 20150106 | 2015-01-06 13:00:00 | arus v | -8.16e-5 | 0.0271 | 0.3675 | 0.9931 |
| 20150106 | 2015-01-06 13:00:00 | arus speed | 2.11e-4 | 0.0297 | 0.4462 | 0.9905 |
| 20150106 | 2015-01-06 13:00:00 | salinity | -2.99e-4 | 0.0939 | 8.8640 | 0.9897 |
| 20150106 | 2015-01-06 13:00:00 | sea temperature | -4.33e-4 | 0.0651 | 3.4839 | 0.9981 |
| 20150106 | 2015-01-06 13:00:00 | angin u | -0.0469 | 1.4714 | 26.093 | 0.9505 |
| 20150106 | 2015-01-06 13:00:00 | angin v | -0.0356 | 1.4870 | 20.128 | 0.8948 |
| 20150106 | 2015-01-06 13:00:00 | angin speed | 0.0110 | 1.3236 | 21.015 | 0.8834 |
| 20150107 | 2015-01-07 13:00:00 | SWH | 0.0073 | 0.1031 | 1.5339 | 0.9850 |
| 20150107 | 2015-01-07 13:00:00 | arus u | -9.25e-4 | 0.0344 | 0.5021 | 0.9938 |
| 20150107 | 2015-01-07 13:00:00 | arus v | -0.0027 | 0.0307 | 0.4674 | 0.9915 |
| 20150107 | 2015-01-07 13:00:00 | arus speed | 3.62e-4 | 0.0337 | 0.4749 | 0.9885 |
| 20150107 | 2015-01-07 13:00:00 | salinity | -1.99e-4 | 0.1005 | 8.3621 | 0.9882 |
| 20150107 | 2015-01-07 13:00:00 | sea temperature | -5.75e-4 | 0.0706 | 2.1942 | 0.9978 |
| 20150107 | 2015-01-07 13:00:00 | angin u | -0.0054 | 1.5552 | 28.406 | 0.9560 |
| 20150107 | 2015-01-07 13:00:00 | angin v | -0.0312 | 1.5618 | 18.770 | 0.8839 |
| 20150107 | 2015-01-07 13:00:00 | angin speed | -6.32e-4 | 1.4323 | 19.542 | 0.8954 |

## 12:00 UTC the next day

| Day | Time (UTC) | Field | Bias | RMSE | Max abs | Corr |
|-----|------------|-------|------|------|---------|------|
| 20150101 | 2015-01-02 12:00:00 | SWH | -8.08e-5 | 0.0242 | 1.0504 | 0.9995 |
| 20150101 | 2015-01-02 12:00:00 | arus u | -2.31e-5 | 0.0096 | 0.3701 | 0.9995 |
| 20150101 | 2015-01-02 12:00:00 | arus v | 2.64e-5 | 0.0081 | 0.3594 | 0.9994 |
| 20150101 | 2015-01-02 12:00:00 | arus speed | 2.04e-5 | 0.0094 | 0.3165 | 0.9990 |
| 20150101 | 2015-01-02 12:00:00 | salinity | -1.92e-4 | 0.0518 | 7.1270 | 0.9969 |
| 20150101 | 2015-01-02 12:00:00 | sea temperature | 2.38e-5 | 0.0151 | 2.1018 | 0.9999 |
| 20150101 | 2015-01-02 12:00:00 | angin u | -0.0044 | 0.7703 | 27.965 | 0.9880 |
| 20150101 | 2015-01-02 12:00:00 | angin v | 0.0014 | 0.7785 | 20.414 | 0.9782 |
| 20150101 | 2015-01-02 12:00:00 | angin speed | -0.0091 | 0.7098 | 25.088 | 0.9760 |
| 20150102 | 2015-01-03 12:00:00 | SWH | -0.0014 | 0.0570 | 1.0191 | 0.9964 |
| 20150102 | 2015-01-03 12:00:00 | arus u | -3.86e-4 | 0.0215 | 0.4007 | 0.9976 |
| 20150102 | 2015-01-03 12:00:00 | arus v | 2.65e-4 | 0.0180 | 0.5678 | 0.9972 |
| 20150102 | 2015-01-03 12:00:00 | arus speed | -6.74e-5 | 0.0208 | 0.4846 | 0.9952 |
| 20150102 | 2015-01-03 12:00:00 | salinity | 4.93e-4 | 0.0723 | 20.763 | 0.9939 |
| 20150102 | 2015-01-03 12:00:00 | sea temperature | 8.93e-4 | 0.0400 | 3.1747 | 0.9994 |
| 20150102 | 2015-01-03 12:00:00 | angin u | -0.0157 | 1.1945 | 23.747 | 0.9741 |
| 20150102 | 2015-01-03 12:00:00 | angin v | -0.0045 | 1.2685 | 20.771 | 0.9285 |
| 20150102 | 2015-01-03 12:00:00 | angin speed | 0.0091 | 1.1144 | 18.874 | 0.9270 |
| 20150103 | 2015-01-04 12:00:00 | SWH | -0.0018 | 0.0615 | 1.2486 | 0.9946 |
| 20150103 | 2015-01-04 12:00:00 | arus u | -8.27e-4 | 0.0247 | 0.5241 | 0.9968 |
| 20150103 | 2015-01-04 12:00:00 | arus v | -0.0014 | 0.0221 | 0.4967 | 0.9955 |
| 20150103 | 2015-01-04 12:00:00 | arus speed | 3.46e-4 | 0.0241 | 0.5147 | 0.9937 |
| 20150103 | 2015-01-04 12:00:00 | salinity | 8.60e-4 | 0.0874 | 13.148 | 0.9911 |
| 20150103 | 2015-01-04 12:00:00 | sea temperature | 5.97e-5 | 0.0530 | 2.8513 | 0.9989 |
| 20150103 | 2015-01-04 12:00:00 | angin u | -7.58e-4 | 1.3160 | 26.999 | 0.9653 |
| 20150103 | 2015-01-04 12:00:00 | angin v | -0.0235 | 1.3997 | 19.753 | 0.8943 |
| 20150103 | 2015-01-04 12:00:00 | angin speed | 0.0115 | 1.2090 | 20.980 | 0.9027 |
| 20150104 | 2015-01-05 12:00:00 | SWH | -0.0041 | 0.0748 | 1.2124 | 0.9921 |
| 20150104 | 2015-01-05 12:00:00 | arus u | -5.50e-4 | 0.0301 | 0.6879 | 0.9953 |
| 20150104 | 2015-01-05 12:00:00 | arus v | 3.91e-4 | 0.0261 | 0.3899 | 0.9936 |
| 20150104 | 2015-01-05 12:00:00 | arus speed | 4.56e-5 | 0.0293 | 0.6276 | 0.9913 |
| 20150104 | 2015-01-05 12:00:00 | salinity | -2.80e-4 | 0.0937 | 12.980 | 0.9898 |
| 20150104 | 2015-01-05 12:00:00 | sea temperature | -0.0018 | 0.0665 | 2.7899 | 0.9981 |
| 20150104 | 2015-01-05 12:00:00 | angin u | -0.0259 | 1.3762 | 21.752 | 0.9555 |
| 20150104 | 2015-01-05 12:00:00 | angin v | 0.0080 | 1.4384 | 20.239 | 0.9066 |
| 20150104 | 2015-01-05 12:00:00 | angin speed | -0.0252 | 1.2716 | 20.318 | 0.8841 |
| 20150105 | 2015-01-06 12:00:00 | SWH | 9.33e-4 | 0.0859 | 1.2350 | 0.9891 |
| 20150105 | 2015-01-06 12:00:00 | arus u | -8.12e-4 | 0.0316 | 0.5008 | 0.9947 |
| 20150105 | 2015-01-06 12:00:00 | arus v | -1.61e-5 | 0.0277 | 0.4911 | 0.9928 |
| 20150105 | 2015-01-06 12:00:00 | arus speed | 1.77e-5 | 0.0299 | 0.4799 | 0.9906 |
| 20150105 | 2015-01-06 12:00:00 | salinity | -1.77e-4 | 0.0916 | 9.3454 | 0.9902 |
| 20150105 | 2015-01-06 12:00:00 | sea temperature | -4.94e-4 | 0.0706 | 3.2478 | 0.9978 |
| 20150105 | 2015-01-06 12:00:00 | angin u | -0.0395 | 1.4726 | 25.298 | 0.9500 |
| 20150105 | 2015-01-06 12:00:00 | angin v | -0.0264 | 1.4904 | 18.935 | 0.8975 |
| 20150105 | 2015-01-06 12:00:00 | angin speed | 0.0047 | 1.3330 | 19.680 | 0.8795 |
| 20150106 | 2015-01-07 12:00:00 | SWH | 0.0078 | 0.1046 | 1.2829 | 0.9846 |
| 20150106 | 2015-01-07 12:00:00 | arus u | -0.0012 | 0.0348 | 0.5354 | 0.9938 |
| 20150106 | 2015-01-07 12:00:00 | arus v | -0.0028 | 0.0314 | 0.4453 | 0.9909 |
| 20150106 | 2015-01-07 12:00:00 | arus speed | -8.09e-5 | 0.0338 | 0.4726 | 0.9886 |
| 20150106 | 2015-01-07 12:00:00 | salinity | 4.28e-5 | 0.0970 | 10.841 | 0.9890 |
| 20150106 | 2015-01-07 12:00:00 | sea temperature | -6.75e-4 | 0.0751 | 2.2371 | 0.9975 |
| 20150106 | 2015-01-07 12:00:00 | angin u | -0.0058 | 1.5502 | 33.671 | 0.9558 |
| 20150106 | 2015-01-07 12:00:00 | angin v | -0.0385 | 1.5847 | 21.973 | 0.8828 |
| 20150106 | 2015-01-07 12:00:00 | angin speed | 0.0062 | 1.4144 | 24.428 | 0.8948 |
| 20150107 | 2015-01-08 12:00:00 | SWH | -0.0103 | 0.1116 | 1.4651 | 0.9884 |
| 20150107 | 2015-01-08 12:00:00 | arus u | 1.64e-4 | 0.0336 | 0.6736 | 0.9949 |
| 20150107 | 2015-01-08 12:00:00 | arus v | 0.0024 | 0.0313 | 0.6182 | 0.9915 |
| 20150107 | 2015-01-08 12:00:00 | arus speed | -8.97e-5 | 0.0330 | 0.6022 | 0.9898 |
| 20150107 | 2015-01-08 12:00:00 | salinity | 0.0012 | 0.1123 | 12.400 | 0.9854 |
| 20150107 | 2015-01-08 12:00:00 | sea temperature | 0.0023 | 0.0700 | 2.1709 | 0.9979 |
| 20150107 | 2015-01-08 12:00:00 | angin u | 0.0097 | 1.5028 | 25.184 | 0.9658 |
| 20150107 | 2015-01-08 12:00:00 | angin v | -0.0135 | 1.5153 | 30.260 | 0.9158 |
| 20150107 | 2015-01-08 12:00:00 | angin speed | -0.0263 | 1.3542 | 22.351 | 0.9238 |

Exact 2015-01-02 12:00 UTC maximum absolute differences, carried forward from the first comparison, are SWH 1.050435 m, arus u 0.370110 m/s, arus v 0.359406 m/s, arus speed 0.316485 m/s, salinity 7.127007, and sea temperature 2.101772 °C.

By 2015-01-08 12:00 UTC the domain-mean bias is still near zero. Pointwise RMSE has grown to about 0.112 m for SWH, 0.033 m/s for surface current speed, 0.112 for salinity, and 0.070 °C for sea temperature. The largest salinity maximum absolute difference in these edge hours is 20.763, at 2015-01-03 12:00 UTC. Correlation at the sampled edges stays above 0.984.

## 10 m wind

`UX10` and `VX10` are the 10 m wind components in `wrfhtr`. At 2015-01-01 13:00 UTC both components and the speed match CLS. By 2015-01-02 12:00 UTC the speed RMSE is 0.710 m/s and the maximum absolute difference is 25.088 m/s. By 2015-01-08 12:00 UTC the speed RMSE is 1.354 m/s, the maximum absolute difference is 22.351 m/s, and the correlation is 0.924. Domain-mean bias stays near zero. The largest component maximum absolute difference at these edge hours is `UX10` 33.671 m/s, at 2015-01-07 12:00 UTC. Wind correlation at the edges falls to about 0.879, which is lower than the ocean sample. The 13:00 and next-day 12:00 tables above include these 10 m wind rows with the ocean fields.

## Time series and maps

The hourly series starts at a zero gap on 1 January. RMSE then grows through the chain, while the domain means of CLS and ft2 stay close. The horizontal axis is the calendar date, labeled 01 Jan through 08 Jan, for the 1–7 January chain. The last column is 10 m wind speed. Each map adds that wind speed under the ocean rows, at 12:00 UTC at the end of the hindcast day.

![Hourly domain mean, bias, RMSE, and correlation for SWH, surface current speed, salinity, sea temperature, and 10 m wind speed. The horizontal axis is the calendar date from 01 Jan through 08 Jan. CLS and ft2 means stay close while RMSE grows after the matching 13:00 UTC hour on 1 January.](reports/ft2_cls_20150101_timeseries.png?v=wind10m)

![Surface maps at 2015-01-02 12:00 UTC for SWH, surface current speed, salinity, sea temperature, and 10 m wind speed on hindcast day 20150101. Each row shows CLS, ft2, and ft2 minus CLS.](reports/ft2_cls_20150101_spatial.png?v=wind10m)
![Surface maps at 2015-01-03 12:00 UTC for SWH, surface current speed, salinity, sea temperature, and 10 m wind speed on hindcast day 20150102. Each row shows CLS, ft2, and ft2 minus CLS.](reports/ft2_cls_20150102_spatial.png?v=wind10m)
![Surface maps at 2015-01-04 12:00 UTC for SWH, surface current speed, salinity, sea temperature, and 10 m wind speed on hindcast day 20150103. Each row shows CLS, ft2, and ft2 minus CLS.](reports/ft2_cls_20150103_spatial.png?v=wind10m)
![Surface maps at 2015-01-05 12:00 UTC for SWH, surface current speed, salinity, sea temperature, and 10 m wind speed on hindcast day 20150104. Each row shows CLS, ft2, and ft2 minus CLS.](reports/ft2_cls_20150104_spatial.png?v=wind10m)
![Surface maps at 2015-01-06 12:00 UTC for SWH, surface current speed, salinity, sea temperature, and 10 m wind speed on hindcast day 20150105. Each row shows CLS, ft2, and ft2 minus CLS.](reports/ft2_cls_20150105_spatial.png?v=wind10m)
![Surface maps at 2015-01-07 12:00 UTC for SWH, surface current speed, salinity, sea temperature, and 10 m wind speed on hindcast day 20150106. Each row shows CLS, ft2, and ft2 minus CLS.](reports/ft2_cls_20150106_spatial.png?v=wind10m)
![Surface maps at 2015-01-08 12:00 UTC for SWH, surface current speed, salinity, sea temperature, and 10 m wind speed on hindcast day 20150107. Each row shows CLS, ft2, and ft2 minus CLS.](reports/ft2_cls_20150107_spatial.png?v=wind10m)

## What this does not claim

File-size differences in the history files are not this comparison. A matched first hour on 1 January, followed by a growing pointwise gap, means the warm start was read and the chain then diverged from CLS. It does not set any dataset to VERIFIED or ACCEPTED, and it does not authorize a 20150201 continuation by itself.
