# Phase 6B.1 — GDP information-boundary repair

**PHASE6B_RESULT_WEAKENED — research only.** Complementary DFM information survives on H2/H3, but the original all-horizon claim loses H1 coverage. No model was promoted; all historical Phase 6B evidence remains intact.

## Bug reproduction completed before repair

The immutable Phase 6B `bridge()` was imported and executed for **2024Q2 H1 standard**, origin **2024-04-30**. Registry timing puts 2024Q1 GDP availability at **2024-05-01**. Changing that unavailable GDP to 999999 changes the forecast; see the deterministic leak reproduction CSV/JSON. This is **LEAK_CONFIRMED under repository timing**, not proof of an observed actual historical publication date. The defect is unconditional chronological GDP selection in `run.py` and unconditional target-lag access in `bridge()`. Bridge A's dependent-variable training also has the same missing release gate.

## GDP source and availability audit

Existing target: `data/master/gdp_quarterly.parquet:gdp_real_yoy_pct`, SIAT dataset **3698**, native ID **1.01.01.0059**, Uzbekistan national selector **1700**. Quarterly published growth convention is unchanged; GDP is never interpolated.

Master, processed GDP, release calendar, release-availability analysis, observations, vintages, download log, raw descriptor/payload/provenance files and frozen Phase 4/5 code were inspected. **Zero of 34 quarters has a verified per-quarter historical release date.** Master dates refer to the dataset update on 2026-07-31. Raw metadata also has dataset-first-publication 2024-07-09: that is not a release calendar for every historical GDP observation. Neither date was assigned to individual quarterly first releases.

The explicit hierarchy accepts quarter-specific verified/publication metadata first, documented historical dates second, a justified conservative repository rule third, otherwise unavailable. No current stored evidence qualifies for the first two tiers. The fallback is **quarter end + 46 days**, derived from the existing registry's **31-day GDP lag** and the existing `effective_release_day(..., 'conservative')` **15-day cushion**, already used by Phase 5A `detect_target_quarter`. The same conservative GDP fallback applies to both monthly standard/conservative experiments; **monthly masks and lag definitions are unchanged**. The 31-day rule is shown only in the timing-sensitivity audit, not selected by forecast accuracy.

Actual `release_date` remains null. The separate `available_date` is explicitly an assumed rule cutoff, quality **APPROXIMATE_FALLBACK**, verified=false. All 34 quarterly availability decisions use this fallback; actual publication remains unknown for all 34. `available_for_H1/H2/H3` in the GDP audit refers to the following quarter's horizons. Thus this is defensible **calendar pseudo-real-time research under a documented conservative rule**, not a verified vintage backtest. Frozen benchmark availability is policy-auditable; actual historical timing is UNVERIFIABLE.

## Repair and preserved DFM

`available_gdp_as_of` gates GDP by explicit availability date before excluding the target/later quarters. The repaired bridge accepts only an `AvailableGDP` object carrying its origin and dated observations. Defensive assertions reject wrong origins, target GDP, later GDP or unreleased rows. Bridge A intersects available GDP with complete historical factor quarters. Bridge B also requires every training lag to be available and returns **PRIOR_QUARTER_GDP_NOT_AVAILABLE** when target-minus-one GDP is absent. No previous available quarter or model forecast is substituted.

The Phase 6B DynamicFactor implementation is imported unchanged: one factor, AR(1), diagonal white-noise idiosyncratic errors, identical training-only scaling and monthly masking, filtered factors and latent-state prediction through quarter end. All **60** primary factor-origin paths were re-estimated and checked against stored Phase 6B states; maximum discrepancy **4.99e-12**, tolerance 1e-8. No imports/services/POS/two-factor model was rerun. Training audits give each dependent and lagged GDP cutoff.

## Origins and frozen benchmark audit

The unchanged monthly sample is **2021-01–2026-08**. Unchanged target quarters are **2024Q1–2026Q2**: six development and four historical post-development quarters. There are 30 calendar origins per monthly lag mode, not 30 independent GDP outcomes.

**20 Bridge B origin records** lose prior GDP availability: {'H1': 20}. This means **10 H1 forecasts per lag mode**; H2/H3 are unaffected. All ten target quarters' H1 origins are affected. Bridge A also excludes the prior GDP from H1 dependent-variable training. At 2024Q1 H1 this leaves only 11 aligned training GDP quarters, so Bridge A is unavailable; remaining H1 Bridge A origins can be estimated. Bridge B and its combinations remain unavailable at every H1.

Frozen Phase 4B `_benchmark_rows/_midas_rows`, Phase 4C `_forecast_rows`, `benchmarks.py` and `midas.py` use all chronological prior GDP. AR(1), AR(2), U-MIDAS and the ensemble therefore have the same GDP boundary defect under the conservative rule. Across all 22 frozen target quarters, **176 model-origin records** are affected; **160** had an issued finite forecast. Within the ten-quarter DFM window, **80** model-origin records are affected. Counts include both lag modes and each benchmark model separately, not distinct GDP outcomes.

| benchmark_model | horizon | leakage_status | model_origin_count |
| --- | --- | --- | --- |
| ar1 | H1 | LEAK_CONFIRMED | 44 |
| ar1 | H2 | CLEAN | 44 |
| ar1 | H3 | CLEAN | 44 |
| ar2 | H1 | LEAK_CONFIRMED | 44 |
| ar2 | H2 | CLEAN | 44 |
| ar2 | H3 | CLEAN | 44 |
| ensemble_ar2_umidas_usd | H1 | LEAK_CONFIRMED | 44 |
| ensemble_ar2_umidas_usd | H2 | CLEAN | 44 |
| ensemble_ar2_umidas_usd | H3 | CLEAN | 44 |
| umidas_usd_uzs_mom_dlog | H1 | LEAK_CONFIRMED | 44 |
| umidas_usd_uzs_mom_dlog | H2 | CLEAN | 44 |
| umidas_usd_uzs_mom_dlog | H3 | CLEAN | 44 |

Clean research-only AR(1)/AR(2)/U-MIDAS/production-ensemble reruns retain the frozen OLS specifications and U-MIDAS minimum 15 effective rows. Missing target-minus-one GDP makes these exact one-step specifications unavailable; using the last available quarter would forecast the wrong quarter. No new recursive multi-step benchmark was introduced. On all eligible finite frozen origins, clean reruns reproduce the original forecasts within 1e-9. Production operational Phase 5A's availability-aware code was not changed; this audit concerns the frozen historical validation generator, not a claim that the current live production code shares its omission.

## Pooled standard-monthly-lag metrics

Bias = actual minus forecast. Zero-count horizons are explicit. These all-available rows may have different coverage; use the matched comparison below for accuracy claims.

| model | horizon | n_forecasts | n_target_quarters | rmse | mae | bias |
| --- | --- | --- | --- | --- | --- | --- |
| AR1_CLEAN_GDP_BOUNDARY | H1 | 0 | 0 | unavailable | unavailable | unavailable |
| AR1_CLEAN_GDP_BOUNDARY | H2 | 10 | 10 | 0.6062 | 0.5095 | 0.5095 |
| AR1_CLEAN_GDP_BOUNDARY | H3 | 10 | 10 | 0.6062 | 0.5095 | 0.5095 |
| AR1_CLEAN_GDP_BOUNDARY | ALL | 20 | 10 | 0.6062 | 0.5095 | 0.5095 |
| AR2_CLEAN_GDP_BOUNDARY | H1 | 0 | 0 | unavailable | unavailable | unavailable |
| AR2_CLEAN_GDP_BOUNDARY | H2 | 10 | 10 | 0.7619 | 0.6491 | 0.6491 |
| AR2_CLEAN_GDP_BOUNDARY | H3 | 10 | 10 | 0.7619 | 0.6491 | 0.6491 |
| AR2_CLEAN_GDP_BOUNDARY | ALL | 20 | 10 | 0.7619 | 0.6491 | 0.6491 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_A_CLEAN | H1 | 0 | 0 | unavailable | unavailable | unavailable |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_A_CLEAN | H2 | 10 | 10 | 0.6475 | 0.4840 | 0.4040 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_A_CLEAN | H3 | 10 | 10 | 0.4321 | 0.3235 | 0.1171 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_A_CLEAN | ALL | 20 | 10 | 0.5504 | 0.4038 | 0.2606 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN | H1 | 0 | 0 | unavailable | unavailable | unavailable |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN | H2 | 10 | 10 | 0.5692 | 0.4310 | 0.3343 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN | H3 | 10 | 10 | 0.3579 | 0.2757 | 0.0646 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN | ALL | 20 | 10 | 0.4754 | 0.3533 | 0.1995 |
| DFM_DOMESTIC_3__BRIDGE_A_CLEAN | H1 | 9 | 9 | 0.9630 | 0.7387 | 0.6849 |
| DFM_DOMESTIC_3__BRIDGE_A_CLEAN | H2 | 10 | 10 | 0.8242 | 0.6107 | 0.4621 |
| DFM_DOMESTIC_3__BRIDGE_A_CLEAN | H3 | 10 | 10 | 0.8705 | 0.6898 | 0.3954 |
| DFM_DOMESTIC_3__BRIDGE_A_CLEAN | ALL | 29 | 10 | 0.8851 | 0.6777 | 0.5082 |
| DFM_DOMESTIC_3__BRIDGE_B_CLEAN | H1 | 0 | 0 | unavailable | unavailable | unavailable |
| DFM_DOMESTIC_3__BRIDGE_B_CLEAN | H2 | 10 | 10 | 0.6151 | 0.4386 | 0.3226 |
| DFM_DOMESTIC_3__BRIDGE_B_CLEAN | H3 | 10 | 10 | 0.6444 | 0.4892 | 0.2904 |
| DFM_DOMESTIC_3__BRIDGE_B_CLEAN | ALL | 20 | 10 | 0.6299 | 0.4639 | 0.3065 |
| PRODUCTION_ENSEMBLE_CLEAN_GDP_BOUNDARY | H1 | 0 | 0 | unavailable | unavailable | unavailable |
| PRODUCTION_ENSEMBLE_CLEAN_GDP_BOUNDARY | H2 | 10 | 10 | 0.6689 | 0.5401 | 0.4975 |
| PRODUCTION_ENSEMBLE_CLEAN_GDP_BOUNDARY | H3 | 10 | 10 | 0.4130 | 0.3148 | 0.2440 |
| PRODUCTION_ENSEMBLE_CLEAN_GDP_BOUNDARY | ALL | 20 | 10 | 0.5559 | 0.4274 | 0.3708 |
| UMIDAS_USD_CLEAN_GDP_BOUNDARY | H1 | 0 | 0 | unavailable | unavailable | unavailable |
| UMIDAS_USD_CLEAN_GDP_BOUNDARY | H2 | 10 | 10 | 0.6898 | 0.5753 | 0.3459 |
| UMIDAS_USD_CLEAN_GDP_BOUNDARY | H3 | 10 | 10 | 0.5311 | 0.3995 | -0.1611 |
| UMIDAS_USD_CLEAN_GDP_BOUNDARY | ALL | 20 | 10 | 0.6156 | 0.4874 | 0.0924 |

## Exactly matched comparison against clean U-MIDAS

Both models in each row use the same origin set and denominator. Development, post-development and pooled results are separate. Bridge A H1 gains cannot be compared with an unavailable U-MIDAS H1 forecast.

| model | evaluation_group | n_forecasts | n_target_quarters | rmse | mae | benchmark_rmse | benchmark_mae |
| --- | --- | --- | --- | --- | --- | --- | --- |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_A_CLEAN | DEVELOPMENT_PSEUDO_OOS | 12 | 6 | 0.3142 | 0.2651 | 0.4949 | 0.3914 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_A_CLEAN | HISTORICAL_POST_DEVELOPMENT_TEST | 8 | 4 | 0.7806 | 0.6118 | 0.7615 | 0.6314 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_A_CLEAN | POOLED_RESEARCH_ONLY | 20 | 10 | 0.5504 | 0.4038 | 0.6156 | 0.4874 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN | DEVELOPMENT_PSEUDO_OOS | 12 | 6 | 0.2657 | 0.2307 | 0.4949 | 0.3914 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN | HISTORICAL_POST_DEVELOPMENT_TEST | 8 | 4 | 0.6776 | 0.5372 | 0.7615 | 0.6314 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN | POOLED_RESEARCH_ONLY | 20 | 10 | 0.4754 | 0.3533 | 0.6156 | 0.4874 |
| DFM_DOMESTIC_3__BRIDGE_A_CLEAN | DEVELOPMENT_PSEUDO_OOS | 12 | 6 | 0.4996 | 0.3203 | 0.4949 | 0.3914 |
| DFM_DOMESTIC_3__BRIDGE_A_CLEAN | HISTORICAL_POST_DEVELOPMENT_TEST | 8 | 4 | 1.1924 | 1.1451 | 0.7615 | 0.6314 |
| DFM_DOMESTIC_3__BRIDGE_A_CLEAN | POOLED_RESEARCH_ONLY | 20 | 10 | 0.8476 | 0.6503 | 0.6156 | 0.4874 |
| DFM_DOMESTIC_3__BRIDGE_B_CLEAN | DEVELOPMENT_PSEUDO_OOS | 12 | 6 | 0.3347 | 0.2186 | 0.4949 | 0.3914 |
| DFM_DOMESTIC_3__BRIDGE_B_CLEAN | HISTORICAL_POST_DEVELOPMENT_TEST | 8 | 4 | 0.9077 | 0.8318 | 0.7615 | 0.6314 |
| DFM_DOMESTIC_3__BRIDGE_B_CLEAN | POOLED_RESEARCH_ONLY | 20 | 10 | 0.6299 | 0.4639 | 0.6156 | 0.4874 |

## Before/after on identical surviving origins

| model | evaluation_group | n_forecasts | n_target_quarters | old_rmse | rmse | old_mae | mae | rmse_change |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DFM_DOMESTIC_3__BRIDGE_B_CLEAN | DEVELOPMENT_PSEUDO_OOS | 12 | 6 | 0.3347 | 0.3347 | 0.2186 | 0.2186 | 0.0000 |
| DFM_DOMESTIC_3__BRIDGE_B_CLEAN | HISTORICAL_POST_DEVELOPMENT_TEST | 8 | 4 | 0.9077 | 0.9077 | 0.8318 | 0.8318 | -0.0000 |
| DFM_DOMESTIC_3__BRIDGE_B_CLEAN | POOLED_RESEARCH_ONLY | 20 | 10 | 0.6299 | 0.6299 | 0.4639 | 0.4639 | -0.0000 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN | DEVELOPMENT_PSEUDO_OOS | 12 | 6 | 0.2657 | 0.2657 | 0.2307 | 0.2307 | 0.0000 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN | HISTORICAL_POST_DEVELOPMENT_TEST | 8 | 4 | 0.6776 | 0.6776 | 0.5372 | 0.5372 | -0.0000 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN | POOLED_RESEARCH_ONLY | 20 | 10 | 0.4754 | 0.4754 | 0.3533 | 0.3533 | 0.0000 |
| DFM_DOMESTIC_3__BRIDGE_A_CLEAN | DEVELOPMENT_PSEUDO_OOS | 17 | 6 | 0.4508 | 0.4563 | 0.2878 | 0.3015 | 0.0055 |
| DFM_DOMESTIC_3__BRIDGE_A_CLEAN | HISTORICAL_POST_DEVELOPMENT_TEST | 12 | 4 | 1.2347 | 1.2641 | 1.1827 | 1.2107 | 0.0294 |
| DFM_DOMESTIC_3__BRIDGE_A_CLEAN | POOLED_RESEARCH_ONLY | 29 | 10 | 0.8660 | 0.8851 | 0.6581 | 0.6777 | 0.0190 |

For transparency, the original and corrected headline denominators are shown below. These **different-sample headlines cannot establish an accuracy gain**:

| model | old_n | old_rmse | old_mae | clean_n | clean_rmse | clean_mae | sample_note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DFM_DOMESTIC_3__BRIDGE_A_CLEAN | 30 | 0.8519 | 0.6412 | 29 | 0.8851 | 0.6777 | DIFFERENT_SAMPLES: see matched table; no direct gain claim |
| DFM_DOMESTIC_3__BRIDGE_B_CLEAN | 30 | 0.6251 | 0.4538 | 20 | 0.6299 | 0.4639 | DIFFERENT_SAMPLES: see matched table; no direct gain claim |
| UMIDAS_USD_CLEAN_GDP_BOUNDARY | 30 | 0.6368 | 0.5116 | 20 | 0.6156 | 0.4874 | DIFFERENT_SAMPLES: see matched table; no direct gain claim |
| PRODUCTION_ENSEMBLE_CLEAN_GDP_BOUNDARY | 30 | 0.5857 | 0.4627 | 20 | 0.5559 | 0.4274 | DIFFERENT_SAMPLES: see matched table; no direct gain claim |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN | 30 | 0.5054 | 0.3746 | 20 | 0.4754 | 0.3533 | DIFFERENT_SAMPLES: see matched table; no direct gain claim |

Bridge A's direct information-boundary effect on the same 29 standard origins is RMSE **0.866009 to 0.885054**, MAE **0.658079 to 0.677697**. Standalone Bridge B on the surviving 20 origins has RMSE **0.629909**, worse than clean U-MIDAS **0.615566**. Thus the old pooled standalone improvement also fails to survive on the clean comparison sample.

The original **0.7319** post-development combination RMSE covered **12 standard origins**. Its corrected headline covers **8 H2/H3 origins**, RMSE **0.677638**, MAE **0.537209**. The old combination on those **same eight origins** has RMSE **0.677638**. Consequently the smaller headline is a coverage change, not an accuracy improvement caused by the repair. The original all-horizon 0.7319 result **does not survive as a valid clean-information headline**; surviving H2/H3 forecasts and complementary information do survive unchanged.

## Required diagnostic answers

1. Old Bridge B used unavailable prior GDP at **20 origin records**, all H1 (10 standard, 10 conservative), **under the explicit 46-day policy**. Actual first-release counts cannot be verified.
2. Affected targets: every quarter 2024Q1–2026Q2 at H1. The 31-day sensitivity alone also excludes the Q2 H1 origins for 2024/2025/2026; these are assumptions, not recovered actual dates.
3. Bridge A's H1 dependent-variable training used the same unavailable prior GDP; repaired rows are removed and minimum-training failures are retained.
4. AR(1): same historical-generator boundary defect, now release-gated.
5. AR(2): same defect, now release-gated.
6. U-MIDAS: its GDP targets and target lag were not release-gated; clean reruns gate both while preserving its monthly kernel.
7. Frozen ensemble: inherits unavailable components. No change to the current production ensemble or operational code.
8. Bridge B RMSE is unchanged on identical surviving H2/H3 origins; old all-horizon comparisons must be withdrawn.
9. Combination RMSE likewise is unchanged on matched surviving origins; a denominator change must not be called a gain.
10. The 0.7319 all-horizon headline is withdrawn; the corrected eight-origin value is 0.677638.
11. DFM retains complementary information on H2/H3 relative to clean U-MIDAS and its combination has lower RMSE than the clean production ensemble. Later-partition combination MAE is slightly higher than the production ensemble, so dominance on every metric is not claimed. Standalone Bridge B no longer beats U-MIDAS on pooled matched RMSE. Evidence is limited to ten GDP targets overall and four later quarters. No H1 combination claim remains. Classification: **PHASE6B_RESULT_WEAKENED** because useful matched combination evidence persists with materially reduced coverage and weaker standalone support.

## Governance and reproduction

All **538 protected files**, including Phase 6B outputs/code/report/dashboard and earlier artifacts, are SHA256-identical before and after. Stored raw GDP archives also have inspection hashes checked during finalization. Registries, canonical datasets, production, Phase 5D, forecast history and dashboards were not modified. New writes are confined to the three Phase 6B.1 directories. Tests and finalization append their evidence below.

Run the commands in `scripts/research/phase6b1/README.md`. No network access or data collection occurs. Stop after Phase 6B.1; no Phase 6C action is started.


Final verification: **23 tests passed**, zero failures/errors/skips. **7 core numeric outputs are byte-identical across reruns**. **538 protected artifacts are byte-identical**, including every inventoried Phase 6B artifact. Stored GDP source inspection checksums also match. No promotion or dashboard replacement.
