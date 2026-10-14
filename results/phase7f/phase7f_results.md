# Phase 7F — optimal DFM factor-number selection

Research diagnostics completed without changing production. **COMBO_50_50 remains 8.180901340616275% for 2026Q3.** All counts below select static covariance components on balanced subpanels; they are not automatically dynamic DFM shocks, state dimensions or economic block counts.

## Primary full-variable balanced panels

| model | declared_variables | n_variables | n_months | sample_start | sample_end | current_factors | k_max | ICp1 | ICp2 | ICp3 | ER | methods_disagree | hits_search_boundary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PRODUCTION_DFM | 8 | 8 | 72 | 2019-01-31 | 2024-12-31 | 1 | 4 | 4 | 4 | 4 | 4 | False | True |
| E1 | 53 | 53 | 24 | 2024-01-31 | 2026-06-30 | 4 | 10 | 10 | 9 | 10 | 2 | True | True |
| E2 | 91 | 91 | 24 | 2024-01-31 | 2026-06-30 | 5 | 10 | 10 | 6 | 10 | 2 | True | True |
| E3 | 91 | 91 | 24 | 2024-01-31 | 2026-06-30 | 5 | 10 | 10 | 6 | 10 | 2 | True | True |
| E4 | 91 | 91 | 24 | 2024-01-31 | 2026-06-30 | 5 | 10 | 10 | 6 | 10 | 2 | True | True |
| ECONOMIC_CORE | 17 | 17 | 28 | 2024-01-31 | 2026-06-30 | 5 | 8 | 8 | 6 | 8 | 6 | True | True |
| GROUP_F1 | 29 | 29 | 65 | 2020-01-31 | 2026-06-30 | 1 | 10 | 5 | 4 | 10 | 1 | True | True |
| CORE_F1 | 3 | 3 | 78 | 2020-01-31 | 2026-06-30 | 1 | 1 | 1 | 1 | 1 | 1 | False | True |
| GROUP_F2 | 14 | 14 | 30 | 2024-01-31 | 2026-06-30 | 1 | 7 | 7 | 7 | 7 | 1 | True | True |
| CORE_F2 | 4 | 4 | 30 | 2024-01-31 | 2026-06-30 | 1 | 2 | 2 | 2 | 2 | 2 | False | True |
| GROUP_F3 | 5 | 5 | 39 | 2023-01-31 | 2026-06-30 | 1 | 2 | 2 | 2 | 2 | 1 | True | True |
| CORE_F3 | 3 | 3 | 51 | 2022-01-31 | 2026-06-30 | 1 | 1 | 1 | 1 | 1 | 1 | False | True |
| GROUP_F4 | 5 | 5 | 54 | 2022-01-31 | 2026-06-30 | 1 | 2 | 2 | 2 | 2 | 1 | True | True |
| CORE_F4 | 3 | 3 | 54 | 2022-01-31 | 2026-06-30 | 1 | 1 | 1 | 1 | 1 | 1 | False | True |
| GROUP_F5 | 38 | 38 | 66 | 2021-01-31 | 2026-06-30 | 1 | 10 | 3 | 3 | 10 | 1 | True | True |
| CORE_F5 | 4 | 4 | 66 | 2021-01-31 | 2026-06-30 | 1 | 2 | 2 | 2 | 2 | 2 | False | True |
| E3_STAGE2 | 5 | 5 | 30 | 2024-01-31 | 2026-06-30 | 1 | 2 | 2 | 2 | 2 | 1 | True | True |
| E3_BRIDGE | 5 | 5 | 30 | 2024-01-31 | 2026-06-30 | 5 | 2 | 2 | 2 | 2 | 2 | False | True |

All main recommendations retain original variables, subject to an explicitly recorded constant-column exclusion where necessary. Rows lost to missingness are listed individually. Production has 72 jointly observed months (2019–2024), versus its 90-month missing-data estimator sample; full Phase 7E pools have only 24 jointly complete months, mostly 2024–2026. These different samples do not support a clean cross-model causal ranking.

## Common-calendar and longer-history sensitivity

| model | sample | n_variables | n_months | sample_start | sample_end | ICp1 | ICp2 | ICp3 | ER | status | failure |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PRODUCTION_DFM | COMMON_STRICT | 8 | 9 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | UNAVAILABLE | Insufficient balanced panel: T=9, N=8 (minimum T=12,N=2) |
| PRODUCTION_DFM | COMMON_CALENDAR_SUBSET | 8 | 12 | 2024-01-31 | 2024-12-31 | 4 | 4 | 4 | 2 | OK | unavailable |
| PRODUCTION_DFM | LONG_HISTORY_RECTANGLE | 7 | 90 | 2019-01-31 | 2026-06-30 | 3 | 3 | 3 | 2 | OK | unavailable |
| PRODUCTION_DFM | UNWEIGHTED_ORIGINAL | 8 | 72 | 2019-01-31 | 2024-12-31 | 4 | 4 | 4 | 4 | OK | unavailable |
| PRODUCTION_DFM | BALANCED_RESTANDARDIZED | 8 | 72 | 2019-01-31 | 2024-12-31 | 4 | 4 | 4 | 4 | OK | unavailable |
| E1 | COMMON_STRICT | 53 | 9 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | UNAVAILABLE | Insufficient balanced panel: T=9, N=53 (minimum T=12,N=2) |
| E1 | COMMON_CALENDAR_SUBSET | 50 | 12 | 2024-01-31 | 2024-12-31 | 6 | 6 | 6 | 1 | OK | unavailable |
| E1 | LONG_HISTORY_RECTANGLE | 24 | 78 | 2020-01-31 | 2026-06-30 | 10 | 5 | 10 | 1 | OK | unavailable |
| E1 | UNWEIGHTED_ORIGINAL | 53 | 24 | 2024-01-31 | 2026-06-30 | 10 | 7 | 10 | 1 | OK | unavailable |
| E1 | BALANCED_RESTANDARDIZED | 53 | 24 | 2024-01-31 | 2026-06-30 | 10 | 6 | 10 | 1 | OK | unavailable |
| E2 | COMMON_STRICT | 91 | 9 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | UNAVAILABLE | Insufficient balanced panel: T=9, N=91 (minimum T=12,N=2) |
| E2 | COMMON_CALENDAR_SUBSET | 88 | 12 | 2024-01-31 | 2024-12-31 | 6 | 6 | 6 | 1 | OK | unavailable |
| E2 | LONG_HISTORY_RECTANGLE | 63 | 66 | 2021-01-31 | 2026-06-30 | 6 | 4 | 10 | 2 | OK | unavailable |
| E2 | UNWEIGHTED_ORIGINAL | 91 | 24 | 2024-01-31 | 2026-06-30 | 10 | 6 | 10 | 1 | OK | unavailable |
| E2 | BALANCED_RESTANDARDIZED | 91 | 24 | 2024-01-31 | 2026-06-30 | 10 | 10 | 10 | 2 | OK | unavailable |
| E3 | COMMON_STRICT | 91 | 9 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | UNAVAILABLE | Insufficient balanced panel: T=9, N=91 (minimum T=12,N=2) |
| E3 | COMMON_CALENDAR_SUBSET | 88 | 12 | 2024-01-31 | 2024-12-31 | 6 | 6 | 6 | 1 | OK | unavailable |
| E3 | LONG_HISTORY_RECTANGLE | 63 | 66 | 2021-01-31 | 2026-06-30 | 6 | 4 | 10 | 2 | OK | unavailable |
| E3 | UNWEIGHTED_ORIGINAL | 91 | 24 | 2024-01-31 | 2026-06-30 | 10 | 6 | 10 | 1 | OK | unavailable |
| E3 | BALANCED_RESTANDARDIZED | 91 | 24 | 2024-01-31 | 2026-06-30 | 10 | 10 | 10 | 2 | OK | unavailable |
| E4 | COMMON_STRICT | 91 | 9 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | UNAVAILABLE | Insufficient balanced panel: T=9, N=91 (minimum T=12,N=2) |
| E4 | COMMON_CALENDAR_SUBSET | 88 | 12 | 2024-01-31 | 2024-12-31 | 6 | 6 | 6 | 1 | OK | unavailable |
| E4 | LONG_HISTORY_RECTANGLE | 63 | 66 | 2021-01-31 | 2026-06-30 | 6 | 4 | 10 | 2 | OK | unavailable |
| E4 | UNWEIGHTED_ORIGINAL | 91 | 24 | 2024-01-31 | 2026-06-30 | 10 | 6 | 10 | 1 | OK | unavailable |
| E4 | BALANCED_RESTANDARDIZED | 91 | 24 | 2024-01-31 | 2026-06-30 | 10 | 10 | 10 | 2 | OK | unavailable |
| ECONOMIC_CORE | COMMON_STRICT | 17 | 9 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | UNAVAILABLE | Insufficient balanced panel: T=9, N=17 (minimum T=12,N=2) |
| ECONOMIC_CORE | COMMON_CALENDAR_SUBSET | 16 | 12 | 2024-01-31 | 2024-12-31 | 6 | 6 | 6 | 6 | OK | unavailable |
| ECONOMIC_CORE | LONG_HISTORY_RECTANGLE | 12 | 54 | 2022-01-31 | 2026-06-30 | 6 | 6 | 6 | 6 | OK | unavailable |
| ECONOMIC_CORE | UNWEIGHTED_ORIGINAL | 17 | 28 | 2024-01-31 | 2026-06-30 | 8 | 0 | 8 | 6 | OK | unavailable |
| ECONOMIC_CORE | BALANCED_RESTANDARDIZED | 17 | 28 | 2024-01-31 | 2026-06-30 | 8 | 0 | 8 | 4 | OK | unavailable |

The strict common full-coverage sample has nine months and is unavailable under the fixed 12-month minimum. The 12-month common-calendar sensitivity excludes incomplete/constant columns explicitly. Long-history rectangles omit short-history indicators and are reduced specifications. Neither sensitivity is silently treated as the original model.

## Search-cap sensitivity on primary panels

| model | requested_cap | k_max | ICp1 | ICp2 | ICp3 | ER | hits_search_boundary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PRODUCTION_DFM | 5 | 5 | 5 | 5 | 5 | 4 | True |
| PRODUCTION_DFM | 10 | 6 | 6 | 6 | 6 | 4 | True |
| PRODUCTION_DFM | 15 | 6 | 6 | 6 | 6 | 4 | True |
| E1 | 5 | 5 | 5 | 5 | 5 | 2 | True |
| E1 | 10 | 10 | 10 | 9 | 10 | 2 | True |
| E1 | 15 | 15 | 15 | 15 | 15 | 2 | True |
| E2 | 5 | 5 | 5 | 5 | 5 | 2 | True |
| E2 | 10 | 10 | 10 | 6 | 10 | 2 | True |
| E2 | 15 | 15 | 15 | 15 | 15 | 2 | True |
| E3 | 5 | 5 | 5 | 5 | 5 | 2 | True |
| E3 | 10 | 10 | 10 | 6 | 10 | 2 | True |
| E3 | 15 | 15 | 15 | 15 | 15 | 2 | True |
| E4 | 5 | 5 | 5 | 5 | 5 | 2 | True |
| E4 | 10 | 10 | 10 | 6 | 10 | 2 | True |
| E4 | 15 | 15 | 15 | 15 | 15 | 2 | True |
| ECONOMIC_CORE | 5 | 5 | 5 | 2 | 5 | 2 | True |
| ECONOMIC_CORE | 10 | 10 | 10 | 10 | 10 | 6 | True |
| ECONOMIC_CORE | 15 | 15 | 15 | 15 | 15 | 6 | True |
| GROUP_F1 | 5 | 5 | 5 | 4 | 5 | 1 | True |
| GROUP_F1 | 10 | 10 | 5 | 4 | 10 | 1 | True |
| GROUP_F1 | 15 | 15 | 15 | 4 | 15 | 1 | True |
| CORE_F1 | 5 | 1 | 1 | 1 | 1 | 1 | True |
| CORE_F1 | 10 | 1 | 1 | 1 | 1 | 1 | True |
| CORE_F1 | 15 | 1 | 1 | 1 | 1 | 1 | True |
| GROUP_F2 | 5 | 5 | 5 | 5 | 5 | 1 | True |
| GROUP_F2 | 10 | 10 | 10 | 10 | 10 | 1 | True |
| GROUP_F2 | 15 | 12 | 12 | 12 | 12 | 1 | True |
| CORE_F2 | 5 | 2 | 2 | 2 | 2 | 2 | True |
| CORE_F2 | 10 | 2 | 2 | 2 | 2 | 2 | True |
| CORE_F2 | 15 | 2 | 2 | 2 | 2 | 2 | True |
| GROUP_F3 | 5 | 3 | 3 | 3 | 3 | 3 | True |
| GROUP_F3 | 10 | 3 | 3 | 3 | 3 | 3 | True |
| GROUP_F3 | 15 | 3 | 3 | 3 | 3 | 3 | True |
| CORE_F3 | 5 | 1 | 1 | 1 | 1 | 1 | True |
| CORE_F3 | 10 | 1 | 1 | 1 | 1 | 1 | True |
| CORE_F3 | 15 | 1 | 1 | 1 | 1 | 1 | True |
| GROUP_F4 | 5 | 3 | 3 | 3 | 3 | 1 | True |
| GROUP_F4 | 10 | 3 | 3 | 3 | 3 | 1 | True |
| GROUP_F4 | 15 | 3 | 3 | 3 | 3 | 1 | True |
| CORE_F4 | 5 | 1 | 1 | 1 | 1 | 1 | True |
| CORE_F4 | 10 | 1 | 1 | 1 | 1 | 1 | True |
| CORE_F4 | 15 | 1 | 1 | 1 | 1 | 1 | True |
| GROUP_F5 | 5 | 5 | 3 | 3 | 5 | 1 | True |
| GROUP_F5 | 10 | 10 | 3 | 3 | 10 | 1 | True |
| GROUP_F5 | 15 | 15 | 3 | 3 | 15 | 1 | True |
| CORE_F5 | 5 | 2 | 2 | 2 | 2 | 2 | True |
| CORE_F5 | 10 | 2 | 2 | 2 | 2 | 2 | True |
| CORE_F5 | 15 | 2 | 2 | 2 | 2 | 2 | True |
| E3_STAGE2 | 5 | 3 | 3 | 3 | 3 | 3 | True |
| E3_STAGE2 | 10 | 3 | 3 | 3 | 3 | 3 | True |
| E3_STAGE2 | 15 | 3 | 3 | 3 | 3 | 3 | True |
| E3_BRIDGE | 5 | 3 | 3 | 3 | 3 | 2 | True |
| E3_BRIDGE | 10 | 3 | 3 | 3 | 3 | 2 | True |
| E3_BRIDGE | 15 | 3 | 3 | 3 | 3 | 2 | True |

## Interpretation and future evaluation

1. **Production one-factor support:** in its original eight-variable balanced panel, ICp1/ICp2/ICp3/ER recommend 4/4/4/4 respectively. One static component is not selected on that sample. All reach the main ceiling 4, so the exact optimal count is unresolved; stress searches and reduced-variable samples must be read alongside it. N=8 is small, and static evidence does not establish a replacement dynamic architecture or better GDP forecasts.

2. **Five Phase 7E economic factors:** no consensus validates exactly five independent static factors. The full E2/E3/E4 monthly pools give IC recommendations 10/6/10 versus ER=2 on 24 complete months, with two criteria at the ceiling. E4 repeats E2 because quarterly bridge variables do not change the monthly measurement panel. E3 stage diagnostics separately examine its global and residual structure; generated-regressor results cannot prove a fully identified hierarchy.

3. **Groups needing further investigation:** industrial activity has ICp1/ICp2=5/4 while ER=1; prices/monetary conditions have ICp1/ICp2=3/3 while ER=1; services IC criteria reach seven while ER=1. Domestic demand and external conditions give IC=2 versus ER=1. These conflicts motivate multi-factor or sub-family sensitivities, not definitive claims that every group requires the largest count. ICp3 is especially ceiling-sensitive here.

4. **Possible redundancy:** low ER counts in pooled panels and in the five generated block signals suggest a small number of dominant shared directions. High IC counts simultaneously suggest remaining heterogeneous covariance or finite-sample over-selection. Economic blocks need not represent statistically independent common factors. Neither result justifies deleting channels or describing redundant causal shocks.

5. **Structures deserving future evaluation:** predeclare alternative static/dynamic dimensions rather than taking an RMSE winner: a two-direction pooled Phase 7E diagnostic motivated by ER, moderate within-industry and within-price sub-family structures motivated by ICp1/ICp2, and production multi-factor sensitivity informed by its full scree/cap results. Revisit short-history services after more observations and test E3 common/residual dependence. Compare interpretation, identification, genuine release availability and prospective forecasting performance in a separately authorized phase. Keep all disagreements and upper-bound hits visible.

6. **Core:** 17-variable core ICp1/ICp2/ICp3/ER=8/6/8/6 in 28 complete months. Narrower labels do not establish a uniquely five-factor static structure. Core block ER counts of one can be mechanical when only one positive candidate is admissible.

## Reproduction — Windows CMD

```cmd
cd /d C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter
.venv\Scripts\python.exe -B -m scripts.phase7f.run
.venv\Scripts\python.exe -B -m scripts.phase7f.validate
start "" "results\phase7f\phase7f_factor_selection_dashboard.html"
```

The methodology, candidate curves, eigenvalues/ratios, loadings, input panels, variable/month exclusion audits and cap sensitivity are stored alongside this report. Actual executed tests, browser checks, determinism and before/after file hashes are recorded in phase7f_validation.json.

## Executed validation

75 tests passed; 0 failures, 0 errors, 0 skips. Full diagnostic replay reproduced all 95 CSV files and the dashboard byte for byte. Offline browser: passed. 27,792 existing files verified unchanged against the resumed baseline.

Concurrent-workspace disclosure: Phase 7E models.py acquired an optional configuration interface between the earlier 2026-10-13 baseline and the repeated 2026-10-14 request. Phase 7F did not edit that file. Both audit baselines are retained; frozen production, data and Phase 7E forecast artifacts remain unchanged. See phase7f_resumption_audit.json.

Offline Edge exercised all 756 model/sample/tab combinations, all nine table sorts, three individual IC charts, four spectral charts, variable search and PC-count heatmap selectors. Zero JavaScript errors or external resource requests. Its raw-byte HTML fingerprint matches the tested dashboard.
