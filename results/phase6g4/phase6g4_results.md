# Phase 6G.4 — real M2 and inflation decomposition



| model | forecast_n | common_sample_rmse | common_sample_mae | bias | post_dev_rmse | current_2026q3_nowcast |
| --- | --- | --- | --- | --- | --- | --- |
| M0_CURRENT_M2 | 18 | 1.118430 | 1.053906 | 1.053906 | 1.132615 | 8.301153 |
| M1_CPI_ONLY | 18 | 0.923321 | 0.867418 | 0.867418 | 0.952786 | 8.215914 |
| M2_NOMINAL_M2_PLUS_CPI | 18 | 0.953824 | 0.900741 | 0.900741 | 0.973573 | 8.212569 |
| M3_REAL_M2_PLUS_CPI | 18 | 0.960822 | 0.879681 | 0.879681 | 0.992191 | 8.218520 |
| M4_REAL_M2_ONLY | 18 | 1.090065 | 1.017761 | 1.017761 | 1.073884 | 8.166406 |



Primary metrics use re-estimated identical monthly training spans and the global intersection of successful origins across all five COMMON fits. Native metrics use each model’s legitimate history and successful origins; they are not a fair ranking across different samples. Bias is actual minus forecast.



Native-sample results:



| model | native_forecast_n | native_sample_rmse | native_sample_mae |
| --- | --- | --- | --- |
| M0_CURRENT_M2 | 44 | 0.487529 | 0.410833 |
| M1_CPI_ONLY | 18 | 0.923321 | 0.867418 |
| M2_NOMINAL_M2_PLUS_CPI | 18 | 0.953824 | 0.900741 |
| M3_REAL_M2_PLUS_CPI | 18 | 0.960822 | 0.879681 |
| M4_REAL_M2_ONLY | 18 | 1.090065 | 1.017761 |



A crucial distinction: the unchanged native M0 evaluated on the SAME 18 common scoring origins has RMSE 0.633364, better than every challenger. Restricting M0’s estimation history to January 2022 raises its RMSE to 1.118430. Thus the improvement over common-span M0 does not establish an improvement over the current full-history benchmark. All common origins span 2025Q1–2026Q2: only six scored quarters, not 18 independent quarters.



## Benchmark and information contract



M0 is the exact Phase 6E DFM, not the production ensemble. Predictors in order: industrial_production, ppi, usd_uzs, rub_uzs, gold_price, m2, fx_reserves_ex_gold, pos_turnover. CPI is absent directly; PPI is already present and remains unchanged. Nominal M2 uses YoY log growth, no economic lag. Native M0 reproduces every accepted historical benchmark and the current saved DFM within 1e-7 (see reproduction.csv). COMMON M0 is separately refitted on the shorter challenger history and is explicitly not the saved native benchmark.



All models reuse one DynamicFactorMQ factor, AR(2), no idiosyncratic AR(1), EM MLE maxiter=500/tolerance=1e-5, missing M-step, likelihood-decrease revert, training-only mean/sample-SD scaling, one-sided filtered factors, quarterly mean bridge B with intercept and released GDP(q−1). Earliest permitted start is January 2019; balanced starts and at least 36 training months are inherited. The GDP bridge also requires at least 12 eligible quarters. No factor selection or retuning occurs.



The target remains gdp_real_yoy_pct: existing SIAT real YTD YoY volume index minus 100. Target actuals are copied from the accepted Phase 6G scored forecasts; training/prior-quarter GDP uses unchanged STRICT verified vintage availability. Post-development quarters are 2025Q3–2026Q2. H1/H2/H3 are the existing target-quarter month-end stages. Exact forecast origins, training dates, exclusions and counts are saved in origin_forecasts, common_forecasts and sample_comparison.



Current archived information cutoff: 2026-10-05 16:54:48.927036; the inherited H3 monthly stage cutoff remains September 30, 2026. Registry lags: {"construction": 27, "corporate_credit": 25, "corporate_deposits": 25, "cpi_food": 5, "cpi_headline": 5, "cpi_services": 5, "electricity_gas": 33, "exports_non_gold": 26, "exports_total": 26, "fx_reserves_ex_gold": 7, "gdp_real_yoy": 31, "gold_exports_proxy": 26, "gold_price": 7, "household_credit": 25, "household_deposits": 25, "imports_total": 26, "industrial_production": 33, "instant_payments": 18, "interbank_payments": 18, "m2": 25, "manufacturing": 33, "mining": 33, "pos_turnover": 18, "ppi": 15, "retail_trade": 24, "rub_uzs": 0, "russia_ipi": 23, "usd_uzs": 0, "wholesale_trade": 24}. Real M2 is gated by the maximum M2/CPI lag. The new CPI snapshot predates the archived current cutoff. Historical predictor value vintages remain unverified, as in the benchmark: this is availability-aware pseudo-real-time, not a claim of fully revision-free historical data. Unknown releases are not fabricated.



## Levels, units and source audit



M2: https://cbu.uz/sdmx/public/DCS_Uzbekistan_Online.xlsx (end-of-month stock, billion UZS). CPI: https://api.siat.stat.uz/media/uploads/sdmx/sdmx_data_1286.json (official previous-month=100 price index). The price level is chained multiplicatively from January 2021 with an arbitrary normalization; no external index or percentage subtraction approximation is used. REAL_M2=M2/chained_CPI; its unit is billion UZS per normalized price-index unit. Scaling the base does not change growth. The chained history stops at a missing or nonpositive index; nothing is filled. Real-money and CPI YoY signals first become available in January 2022. Source notes: Since January 2021, the CPI is calculated according to the Classification of Individual Consumption According to Purposes-2018. Before 2026, the CPI was calculated using the modified Laspeyres (Lowe) index formula. Since 2026, the modified arithmetic Young index formula has been used.



CPI separately enters as exact YoY log inflation, matching the nominal-money horizon. Nominal M2 remains exactly the frozen panel series; raw levels reconstruct it on every overlapping month. Real levels and growth are retained in signals.csv. Signal diagnostics record missingness, actual first/last usable months and distributions. Source hashes and input paths are pinned in run_manifest.json.



## Results and direct answers



1. Descriptive monthly nominal-M2/CPI YoY correlation is 0.041058; real-M2/CPI is -0.196248. These quantify overlap, not the proportion of predictive power explained. Quarterly correlations with the unchanged GDP target include pairwise dates and N; GDP is never interpolated.

2. CPI alone: common RMSE 0.923321, versus common M0 1.118430.

3. Adding nominal M2 to CPI changes common RMSE from 0.923321 to 0.953824; this is a controlled predictive comparison, not a causal effect.

4. Real M2 alone: common RMSE 1.090065; with CPI: 0.960822. Limited origins prevent a reliable general claim about retained predictive information.

5. Main challenger versus common M0 RMSE difference: -0.157608 pp. Both are refitted on identical training dates.

6. Horizon metrics below show whether the change is broad-based; the small common scoring sample limits robustness.



| model | sample | horizon | n | rmse | mae | bias |
| --- | --- | --- | --- | --- | --- | --- |
| M0_CURRENT_M2 | COMMON | H1 | 6 | 1.108932 | 1.040764 | 1.040764 |
| M0_CURRENT_M2 | COMMON | H2 | 6 | 1.118711 | 1.055215 | 1.055215 |
| M0_CURRENT_M2 | COMMON | H3 | 6 | 1.127570 | 1.065739 | 1.065739 |
| M0_CURRENT_M2 | COMMON | POOLED | 18 | 1.118430 | 1.053906 | 1.053906 |
| M1_CPI_ONLY | COMMON | H1 | 6 | 0.975059 | 0.931897 | 0.931897 |
| M1_CPI_ONLY | COMMON | H2 | 6 | 0.934722 | 0.890760 | 0.890760 |
| M1_CPI_ONLY | COMMON | H3 | 6 | 0.856225 | 0.779598 | 0.779598 |
| M1_CPI_ONLY | COMMON | POOLED | 18 | 0.923321 | 0.867418 | 0.867418 |
| M2_NOMINAL_M2_PLUS_CPI | COMMON | H1 | 6 | 0.997505 | 0.957164 | 0.957164 |
| M2_NOMINAL_M2_PLUS_CPI | COMMON | H2 | 6 | 0.962727 | 0.920346 | 0.920346 |
| M2_NOMINAL_M2_PLUS_CPI | COMMON | H3 | 6 | 0.898601 | 0.824712 | 0.824712 |
| M2_NOMINAL_M2_PLUS_CPI | COMMON | POOLED | 18 | 0.953824 | 0.900741 | 0.900741 |
| M3_REAL_M2_PLUS_CPI | COMMON | H1 | 6 | 0.983812 | 0.899798 | 0.899798 |
| M3_REAL_M2_PLUS_CPI | COMMON | H2 | 6 | 0.964187 | 0.885504 | 0.885504 |
| M3_REAL_M2_PLUS_CPI | COMMON | H3 | 6 | 0.933807 | 0.853742 | 0.853742 |
| M3_REAL_M2_PLUS_CPI | COMMON | POOLED | 18 | 0.960822 | 0.879681 | 0.879681 |
| M4_REAL_M2_ONLY | COMMON | H1 | 6 | 1.078804 | 1.004802 | 1.004802 |
| M4_REAL_M2_ONLY | COMMON | H2 | 6 | 1.088328 | 1.018711 | 1.018711 |
| M4_REAL_M2_ONLY | COMMON | H3 | 6 | 1.102929 | 1.029769 | 1.029769 |
| M4_REAL_M2_ONLY | COMMON | POOLED | 18 | 1.090065 | 1.017761 | 1.017761 |



7. Decomposition clarifies the distinction between purchasing-power money growth and inflation. Loading signs/magnitudes/ranks are descriptive; not causal importance. Signs are aligned to M0 within each origin/regime when M0 fits successfully; absent M0 leaves the kernel’s deterministic sign and a null correlation. Current native loadings for M0/M2/M3 are shown below; full historical origin loadings remain in factor_loadings.csv.



| model | variable | loading | abs_loading | rank |
| --- | --- | --- | --- | --- |
| M0_CURRENT_M2 | industrial_production | 0.077893 | 0.077893 | 4 |
| M0_CURRENT_M2 | ppi | -0.041512 | 0.041512 | 6 |
| M0_CURRENT_M2 | usd_uzs | -0.165815 | 0.165815 | 3 |
| M0_CURRENT_M2 | rub_uzs | 0.036923 | 0.036923 | 7 |
| M0_CURRENT_M2 | gold_price | 0.016334 | 0.016334 | 8 |
| M0_CURRENT_M2 | m2 | 0.519784 | 0.519784 | 1 |
| M0_CURRENT_M2 | fx_reserves_ex_gold | 0.057998 | 0.057998 | 5 |
| M0_CURRENT_M2 | pos_turnover | 0.335507 | 0.335507 | 2 |
| M2_NOMINAL_M2_PLUS_CPI | industrial_production | -0.289567 | 0.289567 | 3 |
| M2_NOMINAL_M2_PLUS_CPI | ppi | 0.021802 | 0.021802 | 7 |
| M2_NOMINAL_M2_PLUS_CPI | usd_uzs | 0.082325 | 0.082325 | 4 |
| M2_NOMINAL_M2_PLUS_CPI | rub_uzs | -0.018346 | 0.018346 | 9 |
| M2_NOMINAL_M2_PLUS_CPI | gold_price | -0.039579 | 0.039579 | 6 |
| M2_NOMINAL_M2_PLUS_CPI | m2 | 0.069471 | 0.069471 | 5 |
| M2_NOMINAL_M2_PLUS_CPI | fx_reserves_ex_gold | -0.019730 | 0.019730 | 8 |
| M2_NOMINAL_M2_PLUS_CPI | pos_turnover | 0.374673 | 0.374673 | 2 |
| M2_NOMINAL_M2_PLUS_CPI | cpi | 0.605403 | 0.605403 | 1 |
| M3_REAL_M2_PLUS_CPI | industrial_production | -0.266198 | 0.266198 | 3 |
| M3_REAL_M2_PLUS_CPI | ppi | 0.020481 | 0.020481 | 7 |
| M3_REAL_M2_PLUS_CPI | usd_uzs | 0.076926 | 0.076926 | 4 |
| M3_REAL_M2_PLUS_CPI | rub_uzs | -0.017366 | 0.017366 | 9 |
| M3_REAL_M2_PLUS_CPI | gold_price | -0.036444 | 0.036444 | 6 |
| M3_REAL_M2_PLUS_CPI | real_m2 | -0.067340 | 0.067340 | 5 |
| M3_REAL_M2_PLUS_CPI | fx_reserves_ex_gold | -0.019516 | 0.019516 | 8 |
| M3_REAL_M2_PLUS_CPI | pos_turnover | 0.345673 | 0.345673 | 2 |
| M3_REAL_M2_PLUS_CPI | cpi | 0.558147 | 0.558147 | 1 |



| sample | model | fits | median_factor_correlation | max_spectral_radius | max_EM_iterations |
| --- | --- | --- | --- | --- | --- |
| COMMON | M0_CURRENT_M2 | 18 | 1.000000 | 0.973290 | 106 |
| COMMON | M1_CPI_ONLY | 19 | 0.595704 | 0.909108 | 48 |
| COMMON | M2_NOMINAL_M2_PLUS_CPI | 19 | 0.637330 | 0.907463 | 44 |
| COMMON | M3_REAL_M2_PLUS_CPI | 19 | 0.853978 | 0.972277 | 83 |
| COMMON | M4_REAL_M2_ONLY | 19 | 0.982158 | 0.986892 | 106 |
| NATIVE | M0_CURRENT_M2 | 45 | 1.000000 | 0.982962 | 165 |
| NATIVE | M1_CPI_ONLY | 19 | 0.574878 | 0.909108 | 48 |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 19 | 0.611549 | 0.907463 | 44 |
| NATIVE | M3_REAL_M2_PLUS_CPI | 19 | 0.866744 | 0.972277 | 83 |
| NATIVE | M4_REAL_M2_ONLY | 19 | 0.971807 | 0.986892 | 106 |



8. M3 increases mean absolute within-quarter revisions from 0.022908 pp to 0.048372 pp on the common sample; its maximum rises from 0.077632 to 0.143748 pp. This is worse forecast stability despite lower error. Stability is assessed through within-quarter H1→H2→H3 forecast revisions, spectral radius, convergence, factor correlation and leave-one-scoring-quarter-out RMSE. Recent-observation sensitivity perturbs each latest released current-quarter M2/CPI cell by ±one training SD with unchanged training parameters (an input sensitivity, not a data revision or forecast interval). These diagnostics do not establish structural stability from a small sample. Current driver signals are loading×quarter-mean standardized observations, not additive GDP contributions.



| model | sample | n_horizon_revisions | mean_abs_horizon_revision | max_abs_horizon_revision | prediction_std |
| --- | --- | --- | --- | --- | --- |
| M0_CURRENT_M2 | NATIVE | 30 | 0.027690 | 0.304804 | 0.879980 |
| M0_CURRENT_M2 | COMMON | 12 | 0.022908 | 0.077632 | 0.774262 |
| M1_CPI_ONLY | NATIVE | 12 | 0.095398 | 0.417938 | 0.675373 |
| M1_CPI_ONLY | COMMON | 12 | 0.095398 | 0.417938 | 0.675373 |
| M2_NOMINAL_M2_PLUS_CPI | NATIVE | 12 | 0.088580 | 0.411116 | 0.689503 |
| M2_NOMINAL_M2_PLUS_CPI | COMMON | 12 | 0.088580 | 0.411116 | 0.689503 |
| M3_REAL_M2_PLUS_CPI | NATIVE | 12 | 0.048372 | 0.143748 | 0.724627 |
| M3_REAL_M2_PLUS_CPI | COMMON | 12 | 0.048372 | 0.143748 | 0.724627 |
| M4_REAL_M2_ONLY | NATIVE | 12 | 0.029670 | 0.088012 | 0.825432 |
| M4_REAL_M2_ONLY | COMMON | 12 | 0.029670 | 0.088012 | 0.825432 |



| sample | model | target_quarter | horizon | forecast_origin | variable | reference_period | shock_training_sd | nowcast | change_pp | training_parameters_unchanged |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | -1 | 8.188870 | -0.112283 | True |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | 1 | 8.413436 | 0.112283 | True |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2026-08 | -1 | 8.649138 | 0.433224 | True |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2026-08 | 1 | 7.782689 | -0.433224 | True |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | -1 | 8.213630 | 0.001061 | True |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | 1 | 8.211508 | -0.001061 | True |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2026-08 | -1 | 8.642485 | 0.429916 | True |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2026-08 | 1 | 7.782653 | -0.429916 | True |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | -1 | 8.217406 | -0.001113 | True |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | 1 | 8.219633 | 0.001113 | True |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2026-08 | -1 | 8.651840 | 0.433320 | True |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2026-08 | 1 | 7.785199 | -0.433320 | True |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | -1 | 8.017481 | -0.148925 | True |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | 1 | 8.315331 | 0.148925 | True |
| COMMON | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2026-08 | -1 | 8.649138 | 0.433224 | True |
| COMMON | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2026-08 | 1 | 7.782689 | -0.433224 | True |
| COMMON | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | -1 | 8.213630 | 0.001061 | True |
| COMMON | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | 1 | 8.211508 | -0.001061 | True |
| COMMON | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2026-08 | -1 | 8.642485 | 0.429916 | True |
| COMMON | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2026-08 | 1 | 7.782653 | -0.429916 | True |
| COMMON | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | -1 | 8.217406 | -0.001113 | True |
| COMMON | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | 1 | 8.219633 | 0.001113 | True |
| COMMON | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2026-08 | -1 | 8.651840 | 0.433320 | True |
| COMMON | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2026-08 | 1 | 7.785199 | -0.433320 | True |
| COMMON | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | -1 | 8.017481 | -0.148925 | True |
| COMMON | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2026-08 | 1 | 8.315331 | 0.148925 | True |



9. Post-development common RMSE is 1.132615 for M0 and 0.992191 for M3. This is the inherited evaluation period, already inspected in earlier research; it is not a new untouched holdout.

10. Native research 2026Q3 estimates: M0 8.301153%, M3 8.218520%. COMMON current M0 fails the unchanged 500-iteration convergence gate; its estimate is unavailable and common-current differences versus it stay null. Both regimes and model-specific latest observation dates are reported in current_nowcasts.csv; production stays unchanged.



## Limits and preservation



The short CPI history forces later starts and excludes early forecast origins. Neither interpolation nor relaxed minimum-training rules were used to increase N. CPI-only wins against the short-span refitted benchmark, but all challengers lose against unchanged native M0 on the identical scoring origins. Combined with worse revision stability and the failed common-current M0 fit, this prevents a reliable conclusion that inflation dominates money’s predictive content or that M3 offers a robust improvement. The optional orthogonalization exercise was not implemented.



Protected artifact checks cover 905 files and pass. All experiment outputs reside under results/phase6g4/. Production models, policy, operational outputs, dashboards and preceding phase results are unchanged. No automatic promotion.



PHASE6G4_INCONCLUSIVE
