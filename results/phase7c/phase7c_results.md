# Phase 7C economic coverage research

Classification: **PHASE7C_NO_INCREMENTAL_IMPROVEMENT**. RESEARCH_ONLY. No promotion.

Production active predictors: industrial_production, ppi, usd_uzs, rub_uzs, gold_price, m2, fx_reserves_ex_gold, pos_turnover. All four candidates are AVAILABLE_IN_DATABASE_NOT_ACTIVE; experiments are additions. R1_REAL_APPROX is a transformation sensitivity. No duplicate active predictors were added.

Production remains M0=8.301152885464585, U0=8.060649795767965, C0=8.180901340616275%. Cutoff 2026-10-05 11:28:16.244132; no 2026Q3 outcome used.

Retrospective revised predictor histories, assumed registry reporting lags, strict preserved GDP vintages and approved matched origins. Forecast horizons repeat GDP quarters; uncertainty resamples target-quarter average loss differences, not independent origins. Pairwise samples and exact origins are in model_comparison.csv. Empty samples indicate insufficient 36-month balanced history, not zero forecast error. EM convergence and warnings are in estimation_diagnostics.csv; nonconverged fits require caution.

## Matched DFM and 50/50 comparisons

```text
      comparison            model  n_origins  n_quarters     rmse      mae     bias  r_squared  oos_r_squared_ar1 first_quarter last_quarter
              R1               M0         24           8 0.591581 0.524502 0.524502   0.409337           0.175423        2024Q1       2026Q1
              R1               R1         24           8 0.739609 0.623326 0.528695   0.076757          -0.288864        2024Q1       2026Q1
              R2               M0         18           6 0.633364 0.536965 0.536965   0.106902           0.249661        2025Q1       2026Q2
              R2               R2         18           6 1.106799 1.039932 1.039932  -1.727280          -1.291332        2025Q1       2026Q2
              R3               M0         18           6 0.633364 0.536965 0.536965   0.106902           0.249661        2025Q1       2026Q2
              R3               R3         18           6 1.117425 1.053000 1.053000  -1.779899          -1.335539        2025Q1       2026Q2
  R1_REAL_APPROX               M0         18           6 0.633364 0.536965 0.536965   0.106902           0.249661        2025Q1       2026Q2
  R1_REAL_APPROX   R1_REAL_APPROX         18           6 1.122879 1.058667 1.058667  -1.807105          -1.358397        2025Q1       2026Q2
            C_R1               C0         24           8 0.516991 0.431285 0.397845   0.548894           0.370248        2024Q1       2026Q1
            C_R1             C_R1         24           8 0.552043 0.431895 0.399942   0.485651           0.281959        2024Q1       2026Q1
            C_R2               C0         18           6 0.554264 0.443690 0.338006   0.316048           0.425376        2025Q1       2026Q2
            C_R2             C_R2         18           6 0.733683 0.601470 0.589490  -0.198422          -0.006857        2025Q1       2026Q2
            C_R3               C0         18           6 0.554264 0.443690 0.338006   0.316048           0.425376        2025Q1       2026Q2
            C_R3             C_R3         18           6 0.734750 0.604090 0.596024  -0.201908          -0.009786        2025Q1       2026Q2
C_R1_REAL_APPROX               C0         18           6 0.554264 0.443690 0.338006   0.316048           0.425376        2025Q1       2026Q2
C_R1_REAL_APPROX C_R1_REAL_APPROX         18           6 0.736999 0.606127 0.598857  -0.209277          -0.015977        2025Q1       2026Q2
```

## Horizon accuracy

```text
      comparison            model horizon  n_origins  n_quarters     rmse
              R1               M0      H1          8           8 0.600748
              R1               M0      H2          8           8 0.587055
              R1               M0      H3          8           8 0.586832
              R1               R1      H1          8           8 0.712619
              R1               R1      H2          8           8 0.740725
              R1               R1      H3          8           8 0.764568
              R2               M0      H1          6           6 0.643809
              R2               M0      H2          6           6 0.629045
              R2               M0      H3          6           6 0.627107
              R2               R2      H1          6           6 1.097975
              R2               R2      H2          6           6 1.107606
              R2               R2      H3          6           6 1.114751
              R3               M0      H1          6           6 0.643809
              R3               M0      H2          6           6 0.629045
              R3               M0      H3          6           6 0.627107
              R3               R3      H1          6           6 1.108076
              R3               R3      H2          6           6 1.117559
              R3               R3      H3          6           6 1.126562
  R1_REAL_APPROX               M0      H1          6           6 0.643809
  R1_REAL_APPROX               M0      H2          6           6 0.629045
  R1_REAL_APPROX               M0      H3          6           6 0.627107
  R1_REAL_APPROX   R1_REAL_APPROX      H1          6           6 1.115828
  R1_REAL_APPROX   R1_REAL_APPROX      H2          6           6 1.121750
  R1_REAL_APPROX   R1_REAL_APPROX      H3          6           6 1.131008
            C_R1               C0      H1          8           8 0.569317
            C_R1               C0      H2          8           8 0.593905
            C_R1               C0      H3          8           8 0.353546
            C_R1             C_R1      H1          8           8 0.603357
            C_R1             C_R1      H2          8           8 0.644426
            C_R1             C_R1      H3          8           8 0.367330
            C_R2               C0      H1          6           6 0.622295
            C_R2               C0      H2          6           6 0.640033
            C_R2               C0      H3          6           6 0.353175
            C_R2             C_R2      H1          6           6 0.816222
            C_R2             C_R2      H2          6           6 0.843445
            C_R2             C_R2      H3          6           6 0.487088
            C_R3               C0      H1          6           6 0.622295
            C_R3               C0      H2          6           6 0.640033
            C_R3               C0      H3          6           6 0.353175
            C_R3             C_R3      H1          6           6 0.816253
            C_R3             C_R3      H2          6           6 0.843988
            C_R3             C_R3      H3          6           6 0.490905
C_R1_REAL_APPROX               C0      H1          6           6 0.622295
C_R1_REAL_APPROX               C0      H2          6           6 0.640033
C_R1_REAL_APPROX               C0      H3          6           6 0.353175
C_R1_REAL_APPROX C_R1_REAL_APPROX      H1          6           6 0.819831
C_R1_REAL_APPROX C_R1_REAL_APPROX      H2          6           6 0.845538
C_R1_REAL_APPROX C_R1_REAL_APPROX      H3          6           6 0.492384
```

## Robustness and limitations

Retail trade turnover: On 24 origins / 8 GDP quarters (2024Q1–2026Q1), DFM RMSE gain is -0.1480 pp and fixed-combination RMSE gain is -0.0351 pp (positive means improvement). Quarter-level mean squared-error gain interval [-0.3946, -0.0231] pp². Sensitivities: LAG_PLUS_15D: -0.1486 pp; LAG_PLUS_30D: -0.1486 pp; TRAINING_ONLY_WINSOR_1_99: -0.1487 pp. On 22 converged identical-history-control origins, the DFM RMSE gain is -0.0101 pp; this separates history truncation from added information.
Construction works: On 18 origins / 6 GDP quarters (2025Q1–2026Q2), DFM RMSE gain is -0.4734 pp and fixed-combination RMSE gain is -0.1794 pp (positive means improvement). Quarter-level mean squared-error gain interval [-1.1191, -0.4814] pp². Sensitivities: LAG_PLUS_15D: -0.4690 pp; LAG_PLUS_30D: -0.4690 pp; TRAINING_ONLY_WINSOR_1_99: -0.4571 pp. On 18 converged identical-history-control origins, the DFM RMSE gain is +0.0116 pp; this separates history truncation from added information.
Total imports: On 18 origins / 6 GDP quarters (2025Q1–2026Q2), DFM RMSE gain is -0.4841 pp and fixed-combination RMSE gain is -0.1805 pp (positive means improvement). Quarter-level mean squared-error gain interval [-1.1399, -0.5066] pp². Sensitivities: LAG_PLUS_15D: -0.4839 pp; LAG_PLUS_30D: -0.4839 pp; TRAINING_ONLY_WINSOR_1_99: -0.4839 pp. On 18 converged identical-history-control origins, the DFM RMSE gain is +0.0010 pp; this separates history truncation from added information.
NON_GOLD_EXPORT_PROXY: Primary experiment excluded; empirical incremental value remains unknown.

Early/recent splits and leave-one-quarter-out scoring use identical matched quarters. Quarter-cluster bootstrap intervals describe uncertainty; multiple comparisons and retrospective specification selection preclude superiority claims. +15/+30 day lag sensitivities and training-only 1%/99% candidate clipping preserve baseline rules. Sample controls recompute M0 with each candidate's identical balanced start and preserve missing cells. These separate shorter estimation history from added information. CPI sensitivity begins later and must use its own matched sample. Construction lacks a validated price deflator. No missing observations interpolated.

Factor correlations use sign alignment; changes in common-factor paths and nowcasts are in factor_stability.csv. Loadings and standardized loading signals explicitly include M2. Loading redistribution cannot establish more representative real output or predictive superiority. Correlations are descriptive revised-data associations. No causal attribution.

Groupings deferred: Deferred: individual additions worsen matched accuracy; export proxy fails validation; no defensible best set selected. Proxy excluded because of a negative parent flow and unresolved measurement definition; do not infer official non-gold exports.

All reused raw checksums verified. January resets and annual/last-YTD reconciliation checked; raw YTD and monthly flows retained in data_audit.csv. No new download required. Source update timestamps and retrieval dates retained separately. Candidate raw coverage ends August 2026; exact last eligible current month by lag is in current_nowcasts.csv.

Protected files unchanged: True. Production recomputation errors: {'dfm': {'recomputed': 8.301152885464585, 'frozen': 8.301152885464585, 'error': 0.0}, 'umidas': {'recomputed': 8.060649795767965, 'frozen': 8.060649795767965, 'error': 0.0}, 'final': {'recomputed': 8.180901340616275, 'frozen': 8.180901340616275, 'error': 0.0}}. Full test and deterministic verification results are added to validation.json by the validation command.

## Decisions

{
  "retail_trade": "NO_INCREMENTAL_VALUE",
  "construction": "NO_INCREMENTAL_VALUE",
  "imports_total": "NO_INCREMENTAL_VALUE",
  "exports_non_gold": "DATA_NOT_VALIDATED"
}

## Research-only current predictions

```text
           model  prediction last_available_candidate_month                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  failure
              M0    8.301153                            NaN                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      NaN
              U0    8.060650                            NaN                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      NaN
              C0    8.180901                            NaN                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      NaN
              R1    7.613164            2026-08-31 00:00:00                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      NaN
            C_R1    7.836907            2026-08-31 00:00:00                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      NaN
              R2         NaN            2026-08-31 00:00:00 nonconvergence_or_unstable_transition:{"n_training_months": 54, "n_observed_cells": 468, "n_missing_cells": 18, "iterations": 500, "relative_likelihood_change": 1.5426684083857965e-05, "converged": false, "log_likelihood": -603.4183316151771, "n_states": 2, "warnings": "EM reached maximum number of iterations (500), without achieving convergence: llf=-603.43, convergence criterion=1.5427e-05 (while specified tolerance was 1e-05)", "estimator": "DynamicFactorMQ_EM_MLE", "factor_source": "FILTERED_ONE_SIDED", "estimation_start": "2022-01-31", "spectral_radius": 0.7535649864261742, "transition": "[[0.9499187251918227, -0.14796530248766449], [1.0, 0.0]]", "bic": 1290.605328208204, "aic": 1248.8366632303541}
            C_R2         NaN            2026-08-31 00:00:00 nonconvergence_or_unstable_transition:{"n_training_months": 54, "n_observed_cells": 468, "n_missing_cells": 18, "iterations": 500, "relative_likelihood_change": 1.5426684083857965e-05, "converged": false, "log_likelihood": -603.4183316151771, "n_states": 2, "warnings": "EM reached maximum number of iterations (500), without achieving convergence: llf=-603.43, convergence criterion=1.5427e-05 (while specified tolerance was 1e-05)", "estimator": "DynamicFactorMQ_EM_MLE", "factor_source": "FILTERED_ONE_SIDED", "estimation_start": "2022-01-31", "spectral_radius": 0.7535649864261742, "transition": "[[0.9499187251918227, -0.14796530248766449], [1.0, 0.0]]", "bic": 1290.605328208204, "aic": 1248.8366632303541}
              R3         NaN            2026-08-31 00:00:00   nonconvergence_or_unstable_transition:{"n_training_months": 54, "n_observed_cells": 468, "n_missing_cells": 18, "iterations": 500, "relative_likelihood_change": 1.5444559334478815e-05, "converged": false, "log_likelihood": -606.3026394002065, "n_states": 2, "warnings": "EM reached maximum number of iterations (500), without achieving convergence: llf=-606.31, convergence criterion=1.5445e-05 (while specified tolerance was 1e-05)", "estimator": "DynamicFactorMQ_EM_MLE", "factor_source": "FILTERED_ONE_SIDED", "estimation_start": "2022-01-31", "spectral_radius": 0.751729633691964, "transition": "[[0.951941995758473, -0.15050556559685974], [1.0, 0.0]]", "bic": 1296.3739437782629, "aic": 1254.605278800413}
            C_R3         NaN            2026-08-31 00:00:00   nonconvergence_or_unstable_transition:{"n_training_months": 54, "n_observed_cells": 468, "n_missing_cells": 18, "iterations": 500, "relative_likelihood_change": 1.5444559334478815e-05, "converged": false, "log_likelihood": -606.3026394002065, "n_states": 2, "warnings": "EM reached maximum number of iterations (500), without achieving convergence: llf=-606.31, convergence criterion=1.5445e-05 (while specified tolerance was 1e-05)", "estimator": "DynamicFactorMQ_EM_MLE", "factor_source": "FILTERED_ONE_SIDED", "estimation_start": "2022-01-31", "spectral_radius": 0.751729633691964, "transition": "[[0.951941995758473, -0.15050556559685974], [1.0, 0.0]]", "bic": 1296.3739437782629, "aic": 1254.605278800413}
  R1_REAL_APPROX         NaN            2026-08-31 00:00:00 nonconvergence_or_unstable_transition:{"n_training_months": 55, "n_observed_cells": 477, "n_missing_cells": 18, "iterations": 500, "relative_likelihood_change": 1.4618184528430745e-05, "converged": false, "log_likelihood": -616.3717872904336, "n_states": 2, "warnings": "EM reached maximum number of iterations (500), without achieving convergence: llf=-616.38, convergence criterion=1.4618e-05 (while specified tolerance was 1e-05)", "estimator": "DynamicFactorMQ_EM_MLE", "factor_source": "FILTERED_ONE_SIDED", "estimation_start": "2021-12-31", "spectral_radius": 0.7721392401676744, "transition": "[[0.925945536252306, -0.11875987659179177], [1.0, 0.0]]", "bic": 1316.8975714707492, "aic": 1274.7435745808673}
C_R1_REAL_APPROX         NaN            2026-08-31 00:00:00 nonconvergence_or_unstable_transition:{"n_training_months": 55, "n_observed_cells": 477, "n_missing_cells": 18, "iterations": 500, "relative_likelihood_change": 1.4618184528430745e-05, "converged": false, "log_likelihood": -616.3717872904336, "n_states": 2, "warnings": "EM reached maximum number of iterations (500), without achieving convergence: llf=-616.38, convergence criterion=1.4618e-05 (while specified tolerance was 1e-05)", "estimator": "DynamicFactorMQ_EM_MLE", "factor_source": "FILTERED_ONE_SIDED", "estimation_start": "2021-12-31", "spectral_radius": 0.7721392401676744, "transition": "[[0.925945536252306, -0.11875987659179177], [1.0, 0.0]]", "bic": 1316.8975714707492, "aic": 1274.7435745808673}
```

Run: `.venv/Scripts/python.exe -m scripts.phase7c.run`. Artifacts and offline dashboard: results/phase7c/. Earlier 0.582528 and Phase7B 0.415602 scores use different samples and are not directly compared here.

## Current M2 and factor interpretation

model  loading
   R1 0.212196
   M0 0.519784

The current retail addition redistributes M2 loading from about 0.520 to 0.212 and has an absolute sign-aligned factor correlation of about 0.242 with M0. Both added information and the shorter balanced history change the fitted factor. Reduced monetary loading does not establish greater real-output representation or forecasting accuracy; the matched backtest deteriorates. Current factor paths are in phase7c_current_factor_paths.csv. Signals are descriptive standardized values, not GDP percentage-point or causal contributions.

## Final validation

52 tests passed; independent deterministic refits reproduce retail forecasts and the same explicit non-estimability for other current fits. Protected files unchanged. All 15 dashboard tabs and candidate/horizon selectors rendered locally in Edge.

## Artifact index

- `results/phase7c/browser.log`
- `results/phase7c/browser_test.html`
- `results/phase7c/browser_validation.json`
- `results/phase7c/dashboard_preview.png`
- `results/phase7c/initial_tests.log`
- `results/phase7c/initial_tests.xml`
- `results/phase7c/phase7c_baseline_reproduction.csv`
- `results/phase7c/phase7c_candidate_history.csv`
- `results/phase7c/phase7c_correlations.csv`
- `results/phase7c/phase7c_current_factor_paths.csv`
- `results/phase7c/phase7c_current_nowcasts.csv`
- `results/phase7c/phase7c_data_audit.csv`
- `results/phase7c/phase7c_economic_coverage_dashboard.html`
- `results/phase7c/phase7c_estimation_diagnostics.csv`
- `results/phase7c/phase7c_factor_loadings.csv`
- `results/phase7c/phase7c_factor_signals.csv`
- `results/phase7c/phase7c_factor_stability.csv`
- `results/phase7c/phase7c_historical_predictions.csv`
- `results/phase7c/phase7c_horizon_metrics.csv`
- `results/phase7c/phase7c_indicator_passports.md`
- `results/phase7c/phase7c_management_summary.md`
- `results/phase7c/phase7c_model_comparison.csv`
- `results/phase7c/phase7c_predictor_inventory.csv`
- `results/phase7c/phase7c_results.md`
- `results/phase7c/phase7c_robustness.csv`
- `results/phase7c/phase7c_sample_control_metrics.csv`
- `results/phase7c/phase7c_sample_controls.csv`
- `results/phase7c/pipeline.log`
- `results/phase7c/run_manifest.json`
- `results/phase7c/tests.log`
- `results/phase7c/tests.xml`
- `results/phase7c/validation.json`