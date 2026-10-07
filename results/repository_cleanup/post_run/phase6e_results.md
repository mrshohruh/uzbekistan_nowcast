# Phase 6E — production promotion and interpretation

Status: PHASE6E_PROMOTED. Primary: COMBO_50_50. 2026Q3 nowcast: 8.180901340616%.
DFM: 8.301152885465%; U-MIDAS: 8.060649795768%; weights 0.50 / 0.50.
Reconstruction error: 0.0. As-of: 2026-10-05T11:54:48.927036+00:00; H3 / POST_H3_LATE_INITIALIZATION.

Promotion basis: matched historical holdout superiority. Prospective validation pending; 0 realized quarters.
All candidates use the same 12 origins / four quarters, first-release GDP targets, standard predictor lag convention and STRICT documented GDP boundary.
Historical predictor vintages are incomplete: this is release-lag pseudo-real-time evidence, not complete historical real-time releases.
The expected ranking is recalculated from frozen matched forecasts, with DFM and U-MIDAS independently rerun on all holdout origins.
Development weights remain frozen; no holdout weight optimization. Equal and development-weight combinations perform nearly identically.

## Model comparison

               model  n        r2  r2_os_vs_ar1     rmse      mae     bias production_status  weight_dfm  weight_umidas  H1_rmse  H2_rmse  H3_rmse  current_2026Q3_forecast                                                                                                     notes
         COMBO_50_50 12 -0.463455      0.467631 0.582528 0.421518 0.329872           PRIMARY    0.500000       0.500000 0.671930 0.677106 0.328716                 8.180901 Strict documented GDP boundary; lag-based historical predictor availability; actual-minus-prediction bias
    COMBO_DEV_WEIGHT 12 -0.465657      0.466830 0.582966 0.416443 0.348348            SHADOW    0.543882       0.456118 0.666577 0.671408 0.352752                 8.191455 Strict documented GDP boundary; lag-based historical predictor availability; actual-minus-prediction bias
         PHASE6C_DFM 12 -0.985053      0.277886 0.678442 0.540381 0.540381            SHADOW         NaN            NaN 0.690729 0.673486 0.670942                 8.301153 Strict documented GDP boundary; lag-based historical predictor availability; actual-minus-prediction bias
             U_MIDAS 12 -1.030406      0.261387 0.686149 0.558501 0.119364         BENCHMARK         NaN            NaN 0.813032 0.802850 0.326822                 8.060650 Strict documented GDP boundary; lag-based historical predictor availability; actual-minus-prediction bias
LEGACY_PRODUCTION_V1 12 -1.116736      0.229983 0.700584 0.490827 0.435685            LEGACY         NaN            NaN 0.783570 0.802889 0.462430                 7.758977 Strict documented GDP boundary; lag-based historical predictor availability; actual-minus-prediction bias
                 AR1 12 -1.748946      0.000000 0.798381 0.684034 0.684034         BENCHMARK         NaN            NaN 0.798381 0.798381 0.798381                 8.114253 Strict documented GDP boundary; lag-based historical predictor availability; actual-minus-prediction bias
                 AR2 12 -2.879134     -0.411135 0.948406 0.752007 0.752007         BENCHMARK         NaN            NaN 0.948406 0.948406 0.948406                 7.457305 Strict documented GDP boundary; lag-based historical predictor availability; actual-minus-prediction bias

## Current drivers

            indicator source_model                   metric_type direction  contribution_or_signal  normalized_share_pct latest_period  latest_value                                                                                                                                              transformation                                                interpretation  observed_quarter_months               decomposition_type
                   m2  PHASE6C_DFM descriptive DFM factor signal  positive                0.726074             67.407878       2026-08     29.973970                                                                                                Use EOP level; model transform = 100*ln(level_t/level_t-12).                                      Supporting factor signal                      2.0        loading-based descriptive
              usd_uzs      U_MIDAS   exact forecast contribution  negative               -0.254877              2.665076       2026-09     -0.659799                 Normalize Rate/Nominal; aggregate daily observations to monthly mean; model transform = 100*Δln(monthly_mean). Positive = UZS depreciation. Combined three FX lag terms; model association, not causality                      NaN exact design-vector contribution
              usd_uzs  PHASE6C_DFM descriptive DFM factor signal  positive                0.151426             14.058265       2026-09     -0.659799                 Normalize Rate/Nominal; aggregate daily observations to monthly mean; model transform = 100*Δln(monthly_mean). Positive = UZS depreciation.                                      Supporting factor signal                      3.0        loading-based descriptive
  fx_reserves_ex_gold  PHASE6C_DFM descriptive DFM factor signal  negative               -0.079747              7.403588       2026-08    -35.327058                                                                        Use EOP stock; model transform = 100*ln(level_t/level_t-12). Preserve raw USD level.                                       Weakening factor signal                      2.0        loading-based descriptive
industrial_production  PHASE6C_DFM descriptive DFM factor signal  positive                0.050184              4.659028       2026-07      7.900000 Published real activity growth percent (index minus 100); same convention as frozen Phase6B; research-only deviation from nominal-flow registry clean field                                      Supporting factor signal                      1.0        loading-based descriptive
              rub_uzs  PHASE6C_DFM descriptive DFM factor signal  negative               -0.035020              3.251183       2026-09     -2.955007                                                                              Normalize Rate/Nominal; monthly mean; model transform = 100*Δln(monthly_mean).                                       Weakening factor signal                      3.0        loading-based descriptive
                  ppi  PHASE6C_DFM descriptive DFM factor signal  positive                0.031179              2.894604       2026-08      0.299551                                                                                                       Monthly producer-price inflation = 100*ln(index/100).                                      Supporting factor signal                      2.0        loading-based descriptive
           gold_price  PHASE6C_DFM descriptive DFM factor signal  positive                0.003506              0.325454       2026-08      7.972159                                                 Use published monthly price; model transform = 100*Δln(price). Optionally use YoY log change in robustness.                                      Supporting factor signal                      2.0        loading-based descriptive
         pos_turnover  PHASE6C_DFM descriptive DFM factor signal   neutral                     NaN                   NaN       2024-12     13.791768                                                         Use Total row. De-cumulate YTD within calendar year; then 100*ln(monthly_flow_t/monthly_flow_t-12).                        No released target-quarter measurement                      0.0        loading-based descriptive

DFM driver signals use the mean of released standardized target-quarter observations multiplied by the sign-normalized loading.
No target-quarter POS measurement exists: its current-quarter signal is unavailable, rather than carried from 2024.
The loadings file separately preserves the latest historical measurement signal and reports its actual period.
DFM loading shares sum to 100%; they are factor loadings, not causal GDP coefficients or shares of GDP growth.
U-MIDAS contributions use the actual design vector multiplied by the fitted coefficient vector, including GDP persistence and intercept.
Every current and successful standard/STRICT development and holdout U-MIDAS origin is exported.

## Nowcast news

            old_as_of_date             new_as_of_date target_quarter          indicator source_model  old_forecast  new_forecast  news_impact_pp  total_revision_pp  reconstruction_error            decomposition_type updated_indicator_groups
2026-10-05 11:24:03.030858 2026-10-05 11:28:16.244132         2026Q3 NO_NEW_INFORMATION  PHASE6C_DFM      8.301153      8.301153             0.0                0.0                   0.0 exact fixed-parameter Shapley                         
2026-10-05 11:24:03.030858 2026-10-05 11:28:16.244132         2026Q3 NO_NEW_INFORMATION      U_MIDAS      8.060650      8.060650             0.0                0.0                   0.0 exact fixed-parameter Shapley                         
2026-10-05 11:24:03.030858 2026-10-05 11:28:16.244132         2026Q3 NO_NEW_INFORMATION  COMBO_50_50      8.180901      8.180901             0.0                0.0                   0.0 exact fixed-parameter Shapley                         
2026-10-05 11:28:16.244132 2026-10-05 16:54:48.927036         2026Q3 NO_NEW_INFORMATION  PHASE6C_DFM      8.301153      8.301153             0.0                0.0                   0.0 exact fixed-parameter Shapley                         
2026-10-05 11:28:16.244132 2026-10-05 16:54:48.927036         2026Q3 NO_NEW_INFORMATION      U_MIDAS      8.060650      8.060650             0.0                0.0                   0.0 exact fixed-parameter Shapley                         
2026-10-05 11:28:16.244132 2026-10-05 16:54:48.927036         2026Q3 NO_NEW_INFORMATION  COMBO_50_50      8.180901      8.180901             0.0                0.0                   0.0 exact fixed-parameter Shapley                         

News uses exact all-subset Shapley reruns with old scaling, state parameters, bridge and U-MIDAS coefficients fixed.
Observation groups include revisions to previously observed cells as well as new releases. Parameter re-estimation is reported separately.
DFM and U-MIDAS channels combine at 50/50, with USD/UZS grouped once in the ensemble view.
GDP releases/revisions form a separate news group and must satisfy the new strict GDP cutoff; future target GDP remains excluded.
Different target/horizon contexts are not mislabelled as predictor news. Notes: [].

## Robustness and uncertainty

Per-quarter errors and leave-one-quarter-out metrics are exported. Four holdout quarters provide limited evidence.
Historical RMSE: 0.582528 pp. Indicative ±1 RMSE: [np.float64(7.598373617675209), np.float64(8.763429063557341)].
This is a historical-error reference range, not a formal confidence interval. Bias convention: actual minus prediction.
R² and R²_OS versus AR(1) use exactly matched origins at H1/H2/H3 and pooled; negative scores are retained.

## Operations and rollback

Run `python -m scripts.phase6e.run` to reproduce the latest committed information set without network calls.
Run `python -m scripts.phase6e.update` to refresh official sources using the existing transactional pipeline, then rebuild V2.
Legacy model, policy, entry point and dashboards remain available. Rollback pointer: results/phase5b/phase5b_production_policy.json.
The legacy recipe comparison uses the common STRICT documented GDP information set. Its current forecast is therefore distinct from the original
operational master-based legacy result (7.65689761757519); that original result and its pipeline remain preserved.
The default current dashboard is V2 after successful promotion. A byte-preserved legacy current dashboard is stored alongside these results.
The append-only revision ledger suppresses repeated fingerprints and identical nowcasts.

Frozen artifacts modified: NO; 1184 protected paths checked. Existing dirty repository state is preserved in phase6e_pre_change_state.json.
Tests and second-run verification are recorded in phase6e_test_results.json and phase6e_determinism.json after validation.
Tests: 451 passed; 7 failed; 0 skipped. The remaining legacy failures and pre-Phase-6E evidence are documented in validation_evidence.json.
The dashboard was also rendered from its local file in headless Chrome; dashboard_preview.png records the visual check.
