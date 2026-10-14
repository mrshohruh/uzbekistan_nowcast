# Phase 7E results — research only

OPERATIONAL_PRODUCTION_MODEL = COMBO_50_50; frozen forecast **8.180901340616275%** unchanged. ECONOMICALLY_PREFERRED_RESEARCH_MODEL = **E1 for the clearer four-channel economic explanation**. E2 remains the predeclared full-coverage research candidate. The estimated full F5 is M2-dominated with heterogeneous price/rate loadings; this economic interpretation review is not holdout-RMSE selection or permission to promote a forecast.

Implemented E1, E2, E3 two-stage hierarchical approximation, E4 and the 17-variable economic core. All 91 monthly variables are assigned exactly once (F1=29, F2=14, F3=5, F4=5, F5=38), plus five separately inventoried quarterly predictors. Five base factors are successfully estimated at the current cutoff.

## Current 2026Q3 cumulative real YTD GDP YoY

| model | prediction | failure |
| --- | --- | --- |
| E1 | 8.860393 | unavailable |
| E2 | 8.849506 | unavailable |
| E3 | 8.656072 | unavailable |
| E4 | 8.546187 | unavailable |
| ECONOMIC_CORE | 8.913026 | unavailable |

Research cutoff: 2026-10-05. September source observations are heavily incomplete. Factors extrapolate unavailable months with stable dynamics. Input release vintages are unverified; this is not a sealed production information-set reproduction.

## Identical-origin performance

| sample | model | rmse | mae | bias | median_absolute_error | max_absolute_error | r2 | r2_os_ar1 | n_forecasts | n_quarters |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MATCHED_ALL | E1 | 0.864003 | 0.762951 | 0.762951 | 0.594782 | 1.571726 | -0.661968 | -0.396307 | 18 | 6 |
| MATCHED_ALL | E2 | 0.948251 | 0.860952 | 0.860952 | 0.699004 | 1.595935 | -1.001885 | -0.681889 | 18 | 6 |
| MATCHED_ALL | E3 | 1.004778 | 0.902274 | 0.902274 | 0.737027 | 1.764971 | -1.247671 | -0.888387 | 18 | 6 |
| MATCHED_ALL | E4 | 0.786225 | 0.698949 | 0.698949 | 0.595300 | 1.352110 | -0.376216 | -0.156232 | 18 | 6 |
| MATCHED_ALL | ECONOMIC_CORE | 0.910017 | 0.810373 | 0.810373 | 0.591886 | 1.589783 | -0.843706 | -0.548994 | 18 | 6 |
| MATCHED_ALL | DFM_ALL_GROUPED | 0.804638 | 0.685702 | 0.685702 | 0.560219 | 1.797209 | -0.441432 | -0.211023 | 18 | 6 |
| MATCHED_ALL | M0 | 0.633364 | 0.536965 | 0.536965 | 0.527766 | 1.181675 | 0.106902 | 0.249661 | 18 | 6 |
| MATCHED_ALL | U0 | 0.698175 | 0.584007 | 0.139047 | 0.480326 | 1.369816 | -0.085229 | 0.088242 | 18 | 6 |
| MATCHED_ALL | COMBO_50_50 | 0.554264 | 0.443690 | 0.338006 | 0.441433 | 1.242122 | 0.316048 | 0.425376 | 18 | 6 |
| MATCHED_ALL | AR1 | 0.731181 | 0.645568 | 0.645568 | 0.568636 | 1.340150 | -0.190260 | 0.000000 | 18 | 6 |
| MATCHED_ALL | AR2 | 0.880810 | 0.743212 | 0.743212 | 0.705060 | 1.661983 | -0.727257 | -0.451160 | 18 | 6 |
| MATCHED_DEVELOPMENT | E1 | 0.446272 | 0.423946 | 0.423946 | 0.454869 | 0.582158 | -3.978978 | 0.394748 | 6 | 2 |
| MATCHED_DEVELOPMENT | E2 | 0.570769 | 0.557961 | 0.557961 | 0.558974 | 0.701782 | -7.144440 | 0.009950 | 6 | 2 |
| MATCHED_DEVELOPMENT | E3 | 0.586639 | 0.571814 | 0.571814 | 0.576820 | 0.714761 | -7.603633 | -0.045871 | 6 | 2 |
| MATCHED_DEVELOPMENT | E4 | 0.465004 | 0.448459 | 0.448459 | 0.444190 | 0.607774 | -4.405718 | 0.342873 | 6 | 2 |
| MATCHED_DEVELOPMENT | ECONOMIC_CORE | 0.484942 | 0.472069 | 0.472069 | 0.481743 | 0.613304 | -4.879207 | 0.285315 | 6 | 2 |
| MATCHED_DEVELOPMENT | DFM_ALL_GROUPED | 0.557602 | 0.519567 | 0.519567 | 0.471315 | 0.820901 | -6.772991 | 0.055103 | 6 | 2 |
| MATCHED_DEVELOPMENT | M0 | 0.531866 | 0.530134 | 0.530134 | 0.527766 | 0.583181 | -6.072039 | 0.140312 | 6 | 2 |
| MATCHED_DEVELOPMENT | U0 | 0.721627 | 0.635019 | 0.178414 | 0.524987 | 1.369816 | -12.018632 | -0.582565 | 6 | 2 |
| MATCHED_DEVELOPMENT | COMBO_50_50 | 0.492898 | 0.488034 | 0.354274 | 0.508011 | 0.565966 | -5.073705 | 0.261671 | 6 | 2 |
| MATCHED_DEVELOPMENT | AR1 | 0.573630 | 0.568636 | 0.568636 | 0.568636 | 0.644168 | -7.226288 | 0.000000 | 6 | 2 |
| MATCHED_DEVELOPMENT | AR2 | 0.727001 | 0.725624 | 0.725624 | 0.725624 | 0.770360 | -12.213276 | -0.606226 | 6 | 2 |
| MATCHED_HOLDOUT | E1 | 1.010035 | 0.932454 | 0.932454 | 0.995944 | 1.571726 | -3.399661 | -0.600490 | 12 | 4 |
| MATCHED_HOLDOUT | E2 | 1.088982 | 1.012447 | 1.012447 | 1.114767 | 1.595935 | -4.114312 | -0.860463 | 12 | 4 |
| MATCHED_HOLDOUT | E3 | 1.158575 | 1.067504 | 1.067504 | 1.190461 | 1.764971 | -4.788878 | -1.105854 | 12 | 4 |
| MATCHED_HOLDOUT | E4 | 0.905048 | 0.824194 | 0.824194 | 0.824889 | 1.352110 | -2.532556 | -0.285058 | 12 | 4 |
| MATCHED_HOLDOUT | ECONOMIC_CORE | 1.060477 | 0.979525 | 0.979525 | 1.039152 | 1.589783 | -3.850081 | -0.764342 | 12 | 4 |
| MATCHED_HOLDOUT | DFM_ALL_GROUPED | 0.903164 | 0.768769 | 0.768769 | 0.657789 | 1.797209 | -2.517864 | -0.279714 | 12 | 4 |
| MATCHED_HOLDOUT | M0 | 0.678442 | 0.540381 | 0.540381 | 0.489913 | 1.181675 | -0.985053 | 0.277886 | 12 | 4 |
| MATCHED_HOLDOUT | U0 | 0.686149 | 0.558501 | 0.119364 | 0.439722 | 1.345907 | -1.030406 | 0.261387 | 12 | 4 |
| MATCHED_HOLDOUT | COMBO_50_50 | 0.582528 | 0.421518 | 0.329872 | 0.257397 | 1.242122 | -0.463455 | 0.467631 | 12 | 4 |
| MATCHED_HOLDOUT | AR1 | 0.798381 | 0.684034 | 0.684034 | 0.574924 | 1.340150 | -1.748946 | 0.000000 | 12 | 4 |
| MATCHED_HOLDOUT | AR2 | 0.948406 | 0.752007 | 0.752007 | 0.638035 | 1.661983 | -2.879134 | -0.411135 | 12 | 4 |

Bias is actual minus prediction. All main models use common successful origins. Latest-revised GDP scoring differs from the frozen first-release production evaluation; frozen original production holdout RMSE remains 0.5825277229410664 pp. No superiority claim is justified by four holdout quarters.

The common development sample has only 2 distinct quarters and 6 horizon forecasts per model. The services-start restriction sharply reduces comparison history; development scores are diagnostic and do not support tuning or definitive model ranking.

## Historical availability

Earliest workbook GDP: 2019Q1.

| kind | name | earliest_technical_origin | reason | earliest_target |
| --- | --- | --- | --- | --- |
| BLOCK | F1 | 2021-01-31 | 12 co-observed months, >=two indicators each with >=12 released training observations | unavailable |
| BLOCK | F2 | 2025-01-31 | 12 co-observed months, >=two indicators each with >=12 released training observations | unavailable |
| BLOCK | F3 | 2022-01-31 | 12 co-observed months, >=two indicators each with >=12 released training observations | unavailable |
| BLOCK | F4 | 2020-04-30 | 12 co-observed months, >=two indicators each with >=12 released training observations | unavailable |
| BLOCK | F5 | 2020-01-31 | 12 co-observed months, >=two indicators each with >=12 released training observations | unavailable |
| GDP_BRIDGE | E1 | 2025-01-31 | All required blocks identifiable, four real quarterly factor signals per block, 12 released GDP training rows | 2025Q1 |
| GDP_BRIDGE | E2 | 2025-01-31 | All required blocks identifiable, four real quarterly factor signals per block, 12 released GDP training rows | 2025Q1 |
| GDP_BRIDGE | E3 | 2025-01-31 | All required blocks identifiable, four real quarterly factor signals per block, 12 released GDP training rows | 2025Q1 |
| GDP_BRIDGE | E4 | 2025-01-31 | All required blocks identifiable, four real quarterly factor signals per block, 12 released GDP training rows | 2025Q1 |
| GDP_BRIDGE | ECONOMIC_CORE | 2025-01-31 | All required blocks identifiable, four real quarterly factor signals per block, 12 released GDP training rows | 2025Q1 |

Earlier failures, including nonidentifiable services before 2024/2025, remain in forecast/block-failure files. The extended schedule investigates 2019Q2 onward, but does not create valid 2019 forecasts. Earlier bridge regressors retain null short-history factors with missing indicators; this reduced-history bridge is explicitly labeled.

## Economic and operational assessment

| model | economic_coherence | development_rmse | holdout_rmse | holdout_quarters | implementation_reliability | assessment |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | Four activity/external channels; financing intentionally excluded | 0.446272 | 1.010035 | 4 | Converged current factors; unverified source/release vintage; services short-history restriction | ECONOMICALLY_CLEARER_RESEARCH_EXPLANATION; no promotion |
| E2 | Five predeclared channels, all 91 monthly variables; price/finance interpretation conditional | 0.570769 | 1.088982 | 4 | Converged current factors; unverified source/release vintage; services short-history restriction | FULL_COVERAGE_RESEARCH_CANDIDATE; mixed F5 interpretation; no promotion |
| E3 | Global plus four orthogonal block residuals; F5 reference, two-stage approximation | 0.586639 | 1.158575 | 4 | Converged current factors; unverified source/release vintage; services short-history restriction | RESEARCH_ONLY_NO_PROMOTION; prospective vintage validation required |
| E4 | Five channels plus five separate quarterly covariates | 0.465004 | 0.905048 | 4 | Converged current factors; unverified source/release vintage; services short-history restriction | RESEARCH_ONLY_NO_PROMOTION; prospective vintage validation required |
| ECONOMIC_CORE | 17 exact economic-core indicators; clearer labels, smaller coverage | 0.484942 | 1.060477 | 4 | Converged current factors; unverified source/release vintage; services short-history restriction | RESEARCH_ONLY_NO_PROMOTION; prospective vintage validation required |

| factor | coherence_assessment |
| --- | --- |
| F1 | Broad nominal activity co-movement; cannot infer real output or sector GDP shares. Largest loading-energy family: manufacturing_details (63.5%); positive loading share 100.0%. |
| F2 | Short 2024-onward services history limits stability and development evaluation. Largest loading-energy family: other_services (66.4%); positive loading share 85.7%. |
| F3 | Demand proxies combine construction/trade with provisional enterprise definitions. Largest loading-energy family: activity (74.7%); positive loading share 60.0%. |
| F4 | External/valuation signal combines trade flows and reserve stocks; not real net exports. Largest loading-energy family: gold_price (54.0%); positive loading share 80.0%. |
| F5 | Mixed liquidity/price/rate co-movement; not a coherent unified inflation or monetary-conditions factor. Largest loading-energy family: money (52.0%); positive loading share 36.8%. |

No challenger merits operational promotion now. E2/E4 merit future research review after verified releases, more services history and prospective validation; this is not permission to replace production. Core selection improves label transparency, not established forecast superiority. The full contribution arithmetic, factor stability, missingness and quarter-cluster evidence are in the accompanying CSVs.

## Reproduction (Windows CMD)

```cmd
cd /d C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter
.venv\Scripts\python.exe -B -m scripts.phase7e.run
.venv\Scripts\python.exe -B -m scripts.phase7e.validate
start "" "results\phase7e\phase7e_economic_dfm_dashboard.html"
```

Validation status and actual executed test/browser/reproducibility results are recorded by the validate command in phase7e_validation.json.

## Executed validation

329 tests passed; 0 failures, 0 errors, 0 skips. Offline Edge passed all 52 model/tab/sample/horizon combinations, all 11 table sorts, searches, factor selectors, distribution toggle and charts, with zero JavaScript errors or external resource requests. Full numerical replay reproduced all 22 CSVs; current-version HTML reporting replay was byte-identical. All 26,645 prior protected files remained unchanged. Detailed evidence is in phase7e_validation.json.
