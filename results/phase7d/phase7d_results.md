# Phase 7D results — KEEP_PRODUCTION

Audited **91 monthly + 5 quarterly = 96 predictors** and one separate quarterly
GDP target. D1/D2/D3/D4 retain all 96 declared predictors. All 96 are estimable
at the current origin; short histories are explicitly unidentifiable at earlier
origins, then enter without truncating older series. GDP never enters the
monthly predictor panel. See origin_availability for each column at each origin.

All 30 GDP values exactly match the repository's official cumulative YTD
target after index minus 100. Source column definitions are otherwise partly
inferred from labels and patterns. Zero PPI indices are raw preserved / clean
null; reserve swings and genuine structural gaps remain visible.

## Exact matched latest-revised-target evaluation

| model | rmse | bias | mae | r2 | r2_os_ar1 | n_forecasts | n_quarters | evaluation_start | evaluation_end |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 0.762615 | 0.609396 | 0.652147 | 0.193442 | 0.053054 | 45 | 15 | 2022Q3 | 2026Q2 |
| U0 | 0.726298 | 0.328667 | 0.619280 | 0.268434 | 0.141098 | 45 | 15 | 2022Q3 | 2026Q2 |
| COMBO_50_50 | 0.696453 | 0.469032 | 0.587243 | 0.327321 | 0.210236 | 45 | 15 | 2022Q3 | 2026Q2 |
| AR1 | 0.783687 | 0.670882 | 0.670882 | 0.148254 | 0.000000 | 45 | 15 | 2022Q3 | 2026Q2 |
| AR2 | 0.896667 | 0.761539 | 0.761539 | -0.115032 | -0.309112 | 45 | 15 | 2022Q3 | 2026Q2 |
| DFM_ALL_1F | 0.966441 | 0.651210 | 0.767284 | -0.295316 | -0.520777 | 45 | 15 | 2022Q3 | 2026Q2 |
| DFM_ALL_2F | 0.949901 | 0.618024 | 0.748623 | -0.251358 | -0.469167 | 45 | 15 | 2022Q3 | 2026Q2 |
| DFM_ALL_3F | 0.932952 | 0.644906 | 0.755193 | -0.207100 | -0.417206 | 45 | 15 | 2022Q3 | 2026Q2 |
| DFM_ALL_GROUPED | 0.905061 | 0.616814 | 0.724809 | -0.136005 | -0.333737 | 45 | 15 | 2022Q3 | 2026Q2 |

These metrics are newly recalculated on common origins and latest-revised GDP,
not the frozen production metrics. All legacy kernels were rerun read-only.
Forecast counts include overlapping H1/H2/H3; distinct quarters are shown.
Failures and all generated forecasts remain in the CSVs.

## Final holdout, excluded from model selection

| model | rmse | bias | mae | r2 | r2_os_ar1 | n_forecasts | n_quarters | evaluation_start | evaluation_end |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 0.678442 | 0.540381 | 0.540381 | -0.985053 | 0.277886 | 12 | 4 | 2025Q3 | 2026Q2 |
| U0 | 0.686149 | 0.119364 | 0.558501 | -1.030406 | 0.261387 | 12 | 4 | 2025Q3 | 2026Q2 |
| COMBO_50_50 | 0.582528 | 0.329872 | 0.421518 | -0.463455 | 0.467631 | 12 | 4 | 2025Q3 | 2026Q2 |
| AR1 | 0.798381 | 0.684034 | 0.684034 | -1.748946 | 0.000000 | 12 | 4 | 2025Q3 | 2026Q2 |
| AR2 | 0.948406 | 0.752007 | 0.752007 | -2.879134 | -0.411135 | 12 | 4 | 2025Q3 | 2026Q2 |
| DFM_ALL_1F | 0.925400 | 0.815220 | 0.815220 | -2.693218 | -0.343503 | 12 | 4 | 2025Q3 | 2026Q2 |
| DFM_ALL_2F | 0.892517 | 0.769248 | 0.769248 | -2.435412 | -0.249720 | 12 | 4 | 2025Q3 | 2026Q2 |
| DFM_ALL_3F | 0.832804 | 0.732590 | 0.732590 | -1.991108 | -0.088093 | 12 | 4 | 2025Q3 | 2026Q2 |
| DFM_ALL_GROUPED | 0.903164 | 0.768769 | 0.768769 | -2.517864 | -0.279714 | 12 | 4 | 2025Q3 | 2026Q2 |

Selected experiment: **DFM_ALL_GROUPED**, 2 common factors,
chosen using development RMSE through 2025Q2. Holdout RMSE change versus matched
production is -55.042% improvement (a negative value means worse).
This short retrospective sample cannot establish genuine statistical superiority.
Decision: **KEEP_PRODUCTION**, no automatic promotion.

## Experimental current target

2026Q3 experimental cumulative real YTD GDP YoY: **7.88568870%**.
Calendar cutoff: **2026-10-05**, H3 after quarter-end.
Source missing September predictors: 70;
missing after release assumptions / transforms:
73.
Current release/vintage class: **PSEUDO_REAL_TIME_NOT_VINTAGE_VERIFIED**.
Cutoff matches the production calendar date but lacks workbook release and
retrieval evidence; it does not reproduce the sealed legacy information set.
Indicative historical-error reference band:
6.1155% to
9.6559% — not a calibrated interval.

Frozen production remains **COMBO_50_50 = 8.180901340616275%**.
Original frozen metrics are in phase7d_frozen_production_metrics.csv and the
dashboard's separate historical-reference section. Their original holdout
RMSE is 0.5825277229410664 pp; it must not be confused with re-scored values.

## Audit and limitations

Raw workbook SHA256: 8d41008ac0650ff4f15825179c95d02a102521ef086952005bf0891514fc4a36.
Immutable workbook archive: input/8d41008ac0650ff4f15825179c95d02a102521ef086952005bf0891514fc4a36.xlsx.
Pipeline hashes 26533 prior files and verifies
unchanged bytes at completion; the manifest records the actual verification.
No production scientific output or forecast is overwritten.

The uploaded workbook lacks individual source URLs, release calendars and
retrieval dates. CPI label discrepancy and enterprise-count semantics require
source-owner clarification. Real GDP is compared with nominal activity and
income predictors; seasonal structure, correlated idiosyncratic errors, short
quarterly histories and revisions remain limitations. The estimator is a
two-step missing-data PCA / AR(2) Kalman DFM, not full dynamic MLE.
Fixed ridge penalties and minimum-history thresholds are documented.

The dashboard embeds generated data and SVG interactions with no server or CDN.
Horizon metrics, quarter-cluster uncertainty, group ablations, outlier / lag /
pandemic sensitivities, group factor energies and prequential band coverage
are auditable in accompanying CSVs. Tests and browser checks are reported
in phase7d_validation.json and phase7d_browser_validation.json after execution.

Reproduce: `.venv\Scripts\python.exe -m scripts.phase7d.run`.
Run tests: `.venv\Scripts\python.exe -m scripts.phase7d.test_runner`.

## Completed validation

307 distinct tests passed: 288 existing tests and 19 final Phase 7D tests. Zero failures, errors or remaining skips. The final generated-output tests resolved the three checks deferred during the first suite run.

Headless Edge verified all nine model selectors, eight tabs, sample/horizon controls, sorting, searches, the full 96-predictor inventory and 8,613 transformation-audit rows, with no JavaScript errors. Final-source historical/current reruns reproduced eight saved model forecasts within 1e-12. All 26,533 protected prior files remained byte-identical.
