# Phase 6C research results

**Recommendation: RESEARCH_ONLY. Production and frozen artifacts are unchanged.**

This sequential experiment freezes block composition, factor count/AR order, bridge and combination weight using development origins only. The four final quarters are selection-quarantined here, but were evaluated in earlier phases; they are not a newly unseen research-programme holdout. Predictors use registry release-lag masking of latest stored values; their historical revision vintages are not verified. GDP uses the strict Phase 6B.2 documented-vintage accessor. Unknown historical GDP values are excluded rather than inferred from a release-delay assumption. These limitations preclude operational promotion from this experiment alone.

## Coverage and identification limits

Long core starts January 2019 with 7 variables: industrial_production, ppi, usd_uzs, rub_uzs, gold_price, m2, fx_reserves_ex_gold. Approved recovered published industrial growth begins in 2019, retail in 2020 and construction in 2021. Extending the identical old three-variable domestic panel to 2019 is blocked by construction coverage, so DFM-0 versus DFM-1 cannot isolate sample length. The registry master industrial growth is nominal de-cumulated-flow log growth; Phase6C uses explicitly labelled published growth from the approved research panel consistently with DFM-0. POS is available only through its verified December 2024 scope boundary, and remains missing afterward. No registry or canonical data change is made.

Recovered source integrity: 11 of 11 archived official source files match their recorded checksums.

Prespecified combined ragged panel: industrial_production, construction, retail_trade, cpi_headline, ppi, exports_total, imports_total, usd_uzs, rub_uzs, gold_price, m2, fx_reserves_ex_gold, pos_turnover.

Selected factor fields: industrial_production, ppi, usd_uzs, rub_uzs, gold_price, m2, fx_reserves_ex_gold, pos_turnover. Factors: **1**; AR order: **2**; bridge: **B**, quarterly aggregation: **mean**.

Exclusions:

| model | sample |
| --- | --- |
| manufacturing | predeclared_aggregate_industrial_representative; avoid_four_series_production_dominance |
| mining | predeclared_aggregate_industrial_representative; avoid_four_series_production_dominance |
| electricity_gas | predeclared_aggregate_industrial_representative; avoid_four_series_production_dominance |
| wholesale_trade | predeclared_retail_representative_for_trade_demand_block |
| cpi_food | redundant_CPI_subcomponents; retain_headline_and_PPI |
| cpi_services | redundant_CPI_subcomponents; retain_headline_and_PPI |
| exports_non_gold | redundant_or_proxy_trade_measure; use_total_exports_only |
| gold_exports_proxy | redundant_or_proxy_trade_measure; use_total_exports_only |
| russia_ipi | no_validated_stored_Rosstat_observations; approved acquisition previously failed TLS |
| household_deposits | fewer_than_24_pre_holdout_months |
| corporate_deposits | fewer_than_24_pre_holdout_months |
| household_credit | fewer_than_24_pre_holdout_months |
| corporate_credit | fewer_than_24_pre_holdout_months |
| instant_payments | fewer_than_24_pre_holdout_months |
| interbank_payments | fewer_than_24_pre_holdout_months |

## Development evidence

| model | horizon | sample | n | rmse | mae | bias | median_absolute_error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DFM-0 | ALL | FULL_AVAILABLE | 18 | 0.4402 | 0.3243 | 0.1485 | 0.2533 |
| DFM-1 | ALL | FULL_AVAILABLE | 24 | 1.0798 | 1.0413 | 1.0413 | 1.0397 |
| DFM-1_SHORT_HISTORY_CONTROL | ALL | FULL_AVAILABLE | 0 | nan | nan | nan | nan |
| DFM-2_COMBINED | ALL | FULL_AVAILABLE | 0 | nan | nan | nan | nan |
| DFM-2_CORE | ALL | FULL_AVAILABLE | 24 | 1.0798 | 1.0413 | 1.0413 | 1.0397 |
| DFM-2_PLUS_DOMESTIC_DEMAND | ALL | FULL_AVAILABLE | 0 | nan | nan | nan | nan |
| DFM-2_PLUS_EXTERNAL | ALL | FULL_AVAILABLE | 0 | nan | nan | nan | nan |
| DFM-2_PLUS_PAYMENTS | ALL | FULL_AVAILABLE | 30 | 0.9115 | 0.8618 | 0.7385 | 0.9555 |
| DFM-2_PLUS_PRICES | ALL | FULL_AVAILABLE | 0 | nan | nan | nan | nan |
| DFM-3 | ALL | FULL_AVAILABLE | 30 | 0.9115 | 0.8618 | 0.7385 | 0.9555 |
| DFM-3_COMBINED | ALL | FULL_AVAILABLE | 30 | 1.3415 | 0.9214 | 0.5978 | 0.6046 |
| DFM-4_R1_P1 | ALL | FULL_AVAILABLE | 30 | 0.9115 | 0.8618 | 0.7385 | 0.9555 |
| DFM-4_R1_P2 | ALL | FULL_AVAILABLE | 39 | 0.9764 | 0.8821 | 0.5017 | 0.9355 |
| DFM-4_R1_P2__BRIDGE_A_end | ALL | FULL_AVAILABLE | 39 | 0.9866 | 0.8787 | 0.6165 | 0.9576 |
| DFM-4_R1_P2__BRIDGE_A_mean | ALL | FULL_AVAILABLE | 39 | 0.9764 | 0.8821 | 0.5017 | 0.9355 |
| DFM-4_R1_P2__BRIDGE_B_end | ALL | FULL_AVAILABLE | 39 | 0.5750 | 0.4658 | 0.1538 | 0.4472 |
| DFM-4_R1_P2__BRIDGE_B_mean | ALL | FULL_AVAILABLE | 39 | 0.5736 | 0.4620 | 0.1108 | 0.4009 |
| DFM-4_R1_P2__BRIDGE_C_end | ALL | FULL_AVAILABLE | 36 | 0.4942 | 0.4319 | 0.2845 | 0.4344 |
| DFM-4_R1_P2__BRIDGE_C_mean | ALL | FULL_AVAILABLE | 36 | 0.4896 | 0.4443 | 0.3707 | 0.4367 |
| DFM-4_R2_P1 | ALL | FULL_AVAILABLE | 18 | 1.8815 | 1.4493 | 1.3131 | 0.9243 |
| DFM-4_R2_P2 | ALL | FULL_AVAILABLE | 32 | 1.6522 | 1.2613 | 0.8335 | 0.9082 |
| DFM-4_R3_P1 | ALL | FULL_AVAILABLE | 0 | nan | nan | nan | nan |
| DFM-4_R3_P2 | ALL | FULL_AVAILABLE | 4 | 0.9201 | 0.6444 | -0.5785 | 0.3452 |

These full-available scores do not establish superiority on unequal samples. The sequential selection file contains exact common development origins at every decision. The minimum is nine common forecasts; numerical failures are saved explicitly and ineligible candidates do not get an advantage from missing origins. Block design retains one industrial aggregate, headline CPI plus PPI, total exports/imports and at most the adequately observed payment/banking fields. Pairwise correlations are diagnostic only, through June 2025; no unrestricted variable search is performed.

Matched development findings:

Old DFM versus recovered long core (composition also changes): matched RMSE 0.3845 → 1.1573, 15 common origins; did not improve.

Longer history with identical core fields: blocked by insufficient mutually estimable development forecasts.

Economically balanced block selection: matched RMSE 1.0798 → 0.9265, 24 common origins; improved.

Ragged history versus identical balanced fields: matched RMSE 0.9115 → 0.9115, 30 common origins; did not improve.

## Final horizon-specific performance

| model | horizon | sample | n | rmse | mae | bias | median_absolute_error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DFM-4_R1_P2__BRIDGE_B_mean | H1 | FULL_AVAILABLE | 13 | 0.5869 | 0.4563 | 0.1385 | 0.3866 |
| DFM-4_R1_P2__BRIDGE_B_mean | H2 | FULL_AVAILABLE | 13 | 0.6000 | 0.4790 | 0.1026 | 0.4405 |
| DFM-4_R1_P2__BRIDGE_B_mean | H3 | FULL_AVAILABLE | 13 | 0.5317 | 0.4507 | 0.0913 | 0.4009 |
| DFM-4_R1_P2__BRIDGE_B_mean | ALL | FULL_AVAILABLE | 39 | 0.5736 | 0.4620 | 0.1108 | 0.4009 |
| DFM-4_R1_P2__BRIDGE_B_mean | H1 | FULL_AVAILABLE | 4 | 0.6907 | 0.5471 | 0.5471 | 0.4899 |
| DFM-4_R1_P2__BRIDGE_B_mean | H2 | FULL_AVAILABLE | 4 | 0.6735 | 0.5420 | 0.5420 | 0.4911 |
| DFM-4_R1_P2__BRIDGE_B_mean | H3 | FULL_AVAILABLE | 4 | 0.6709 | 0.5321 | 0.5321 | 0.4775 |
| DFM-4_R1_P2__BRIDGE_B_mean | ALL | FULL_AVAILABLE | 12 | 0.6784 | 0.5404 | 0.5404 | 0.4899 |

## Final holdout: every model on its own available sample

| model | horizon | sample | n | rmse | mae | bias | median_absolute_error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AR1 | ALL | FULL_AVAILABLE | 12 | 0.7984 | 0.6840 | 0.6840 | 0.5749 |
| AR2 | ALL | FULL_AVAILABLE | 12 | 0.9484 | 0.7520 | 0.7520 | 0.6380 |
| DFM-0 | ALL | FULL_AVAILABLE | 12 | 1.2464 | 1.1981 | 1.1981 | 1.0337 |
| DFM-4_R1_P2__BRIDGE_B_mean | ALL | FULL_AVAILABLE | 12 | 0.6784 | 0.5404 | 0.5404 | 0.4899 |
| PHASE6B2_COMBO_B | ALL | FULL_AVAILABLE | 12 | 0.6846 | 0.5327 | 0.4851 | 0.4390 |
| PHASE6B2_DFM_B | ALL | FULL_AVAILABLE | 12 | 0.9241 | 0.8509 | 0.8509 | 0.6725 |
| PRODUCTION_ENSEMBLE | ALL | FULL_AVAILABLE | 12 | 0.7006 | 0.4908 | 0.4357 | 0.2105 |
| UMIDAS_USD | ALL | FULL_AVAILABLE | 12 | 0.6861 | 0.5585 | 0.1194 | 0.4397 |

## Pairwise matched holdout comparisons

| model | horizon | sample | n | rmse | mae | bias | median_absolute_error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DFM-4_R1_P2__BRIDGE_B_mean | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.6784 | 0.5404 | 0.5404 | 0.4899 |
| AR1 | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.7984 | 0.6840 | 0.6840 | 0.5749 |
| DFM-4_R1_P2__BRIDGE_B_mean | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.6784 | 0.5404 | 0.5404 | 0.4899 |
| AR2 | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.9484 | 0.7520 | 0.7520 | 0.6380 |
| DFM-4_R1_P2__BRIDGE_B_mean | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.6784 | 0.5404 | 0.5404 | 0.4899 |
| DFM-4_R1_P2__BRIDGE_B_mean | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.6784 | 0.5404 | 0.5404 | 0.4899 |
| UMIDAS_USD | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.6861 | 0.5585 | 0.1194 | 0.4397 |
| DFM-4_R1_P2__BRIDGE_B_mean | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.6784 | 0.5404 | 0.5404 | 0.4899 |
| PRODUCTION_ENSEMBLE | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.7006 | 0.4908 | 0.4357 | 0.2105 |
| DFM-0 | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 1.2464 | 1.1981 | 1.1981 | 1.0337 |
| DFM-4_R1_P2__BRIDGE_B_mean | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.6784 | 0.5404 | 0.5404 | 0.4899 |
| DFM-4_R1_P2__BRIDGE_B_mean | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.6784 | 0.5404 | 0.5404 | 0.4899 |
| PHASE6B2_DFM_B | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.9241 | 0.8509 | 0.8509 | 0.6725 |
| DFM-4_R1_P2__BRIDGE_B_mean | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.6784 | 0.5404 | 0.5404 | 0.4899 |
| PHASE6B2_COMBO_B | ALL | PAIRWISE_COMMON_WITH_FINAL | 12 | 0.6846 | 0.5327 | 0.4851 | 0.4390 |
On identical holdout origins, final DFM RMSE is 0.6784 versus U-MIDAS 0.6861: the DFM is more accurate on this matched sample.


## Complementarity

| model | horizon | sample | n | rmse | mae | bias | median_absolute_error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DEVELOPMENT_WEIGHT_DFM | ALL | FULL_AVAILABLE | 12 | 0.5830 | 0.4164 | 0.3483 | 0.2089 |
| FIXED_25_DFM | ALL | FULL_AVAILABLE | 12 | 0.6112 | 0.4839 | 0.2246 | 0.4129 |
| FIXED_50_DFM | ALL | FULL_AVAILABLE | 12 | 0.5825 | 0.4215 | 0.3299 | 0.2574 |
| FIXED_75_DFM | ALL | FULL_AVAILABLE | 12 | 0.6068 | 0.4351 | 0.4351 | 0.2482 |
Estimated DFM combination weight: 0.543882, fitted on standard-mode development origins and frozen before holdout. Fixed-weight and estimated-weight combinations preserve the production ensemble. Error and revision correlations are in their CSV files. Leave-one-quarter-out scores disclose whether an apparent gain depends on one quarter; those holdout diagnostics never retune the frozen model.

The final DFM has lower quarter-level mean squared error than DFM-0 in 4 of four holdout quarters. The frozen development-weight combination improves on U-MIDAS in 3 of four quarters; the final DFM largest quarterly error is in 2026Q1. This is broad improvement relative to the old DFM, but not uniform superiority over U-MIDAS.

Matched holdout DFM/U-MIDAS error correlation: 0.5362.

## Factor interpretation and numerical reliability

Top ten absolute signed loadings, squared-loading economic block shares, factor covariances and recursive matched-loading/subspace cosines are saved in tidy files. Empirical factors are left numbered: financial/price/external dominance of a long core must not be labelled domestic real activity without supporting loadings. Multi-factor rotation and sign indeterminacy are handled in stability diagnostics by maximum absolute cosine matching and subspace angles. Likelihood BIC/AIC provide a finite-state alternative diagnostic to Bai–Ng, whose large-panel assumptions are weak here. Scree shares describe the complete overlapping development subsample only, never the ragged estimator. Factor common-component variances are not falsely reported as additive explained shares when factors correlate.

Factor-count selection on identical development origins:

| model | horizon | sample | n | rmse | mae | bias | median_absolute_error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DFM-4_R1_P1 | ALL | SELECTION_COMMON_DEVELOPMENT | 16 | 1.0533 | 1.0457 | 1.0457 | 1.0479 |
| DFM-4_R1_P2 | ALL | SELECTION_COMMON_DEVELOPMENT | 16 | 1.0331 | 1.0046 | 1.0046 | 1.0161 |
| DFM-4_R2_P1 | ALL | SELECTION_COMMON_DEVELOPMENT | 16 | 1.9072 | 1.4765 | 1.3233 | 0.9243 |
| DFM-4_R2_P2 | ALL | SELECTION_COMMON_DEVELOPMENT | 16 | 1.9721 | 1.5725 | 1.5725 | 1.1167 |
Two-factor candidates were worse on the common development sample. Three-factor candidates could not supply enough converged, bridge-estimable origins to enter selection; this is a numerical/data limitation, not evidence that three economic factors cannot exist. The factor-only Bridge A remains weak relative to DFM-0. Much of the final accuracy gain arrives when released lagged GDP enters Bridge B; it must not be interpreted as proof that longer history or additional factors repaired factor extraction. The financial loading concentration and failure of the identical-core short-history control to produce a matched estimable sample limit the scientific attribution of gains.

Factor 1 has its largest squared-loading contribution in FINANCIAL (70.0%); this describes loadings rather than imposing a causal economic label.

Successful factor fits: 924; failed origin/specification records: 906. Training months range 36–87; selected development/holdout sample lengths are in factor_diagnostics.csv. The selected model uses 36–87 monthly training rows and 287–681 observed predictor cells across successful recursive fits. EM convergence and transition stability are mandatory; rejected fits produce null forecasts and retain their error context. There is no observation backfill, interpolation, listwise deletion in ragged mode, or full-sample scaling. The balanced comparator trims to the latest first-valid month but preserves internal gaps; DFM-3 keeps the identical fields and all earlier months. H1/H2 future within-quarter states are model predictions under missing measurements, not future observed factors. Monthly factors are quarterly means or quarter-end latent states; bridges use only released GDP and require at least max(12, three times regressor count) quarters.

## Robustness and operational decision

Development-only start-date, winsorization and available block/individual exclusions are saved without changing the freeze. Russia IPI is unavailable in validated stored data, so all estimable models exclude it; a with-Russia experiment is blocked rather than fabricated. Excluded sparse instant/interbank payments and banking have fewer than 24 development observations. Recovered POS is evaluated explicitly as an incremental block but has no validated measurements after December 2024. Winsorization at training-only 1/99 percentiles is an explicit research sensitivity, not a claimed existing production convention. A challenger must show stable matched gains/complementarity across horizons and quarters, complete release-vintage evidence and reliable recursive estimation before shadow promotion. The documented vintage/coverage constraints and short independent evaluation do not establish that standard. Protected artifacts changed: **NO** (882 files checked).
Automated tests: 341 passed, 0 failed, 0 errors, 0 skipped. Repository and prior research suites use separate processes to avoid their shared `run` module names colliding.
