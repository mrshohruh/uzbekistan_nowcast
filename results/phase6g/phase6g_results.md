# Phase 6G — M2-L2 DFM ensemble promotion test



Phase 6E production is unchanged. The primary challenger is G2 = 50% M2-L2 DFM + 50% unchanged U-MIDAS; no FDI is read or fitted.

The evaluation is **availability-aware pseudo-real-time**, not fully vintage-real-time. Reference-period/publication timing is masked and tested. Historical predictor revision-value leakage remains unresolved because M2 and other predictor value vintages are incomplete. All numerical conclusions below carry that limitation.

## Reproduction and historical extension



The first stage refits Phase 6E DFM, U-MIDAS and COMBO_50_50 and Phase 6F M2-L1/L2 at each of the twelve frozen holdout origins and at the archived current cutoff. All 65 required reconstruction checks must pass absolute tolerance 1e-7 before extension or promotion conclusions are permitted. Reproduction failures stop the experiment.

The extended strict-common sample contains 44 origins across 15 realized quarters, beginning 2022Q3 and ending 2026Q2. The unchanged original holdout contains 12 origins across four quarters. 46 candidate origins were excluded; their exact missing-history, convergence or GDP-evidence reasons are in phase6g_origin_eligibility.csv.

Earlier origins were attempted using the existing verified first-release GDP registry, publication-vintage accessor and frozen minimum-history rules. No earlier target is scored with revised GDP as a substitute for an unresolved first release. DFM needs at least 36 training months, the GDP bridge needs its frozen minimum quarters and released GDP(q−1), and U-MIDAS needs at least 15 usable training rows. Nonconverged or unstable DFM fits remain unavailable. All seven models must succeed at an origin for the main common comparison.

The earlier extension overlaps the repository’s model development period. It is retrospective robustness evidence for an already chosen specification, not an independent holdout or a new prospective validation sample. Original holdout and earlier-development metrics are reported separately. Full-available scores are also reported; benchmark-relative metrics always pair identical origins. No unequal-sample RMSE difference is used for promotion.

## Fixed model design



S0/S1/S2 retain the eight Phase 6E predictors: industrial production, PPI, USD/UZS, RUB/UZS, world gold, M2, reserves excluding gold and scope-limited POS. M2 transformation remains 100 ln(level_t/level_t−12). The 25-day registry publication gate is applied to the source series before assigning its transformed value to a month one/two months later. Thus an economic L2 means the factor cell at month t contains the observed transformed M2 value from t−2. This exactly reproduces Phase 6F rather than reversing the shift.

One EM-MLE DynamicFactorMQ factor, AR(2), filtered states, no idiosyncratic AR(1), training-only standardization, balanced start and the original intercept + mean-quarter factor + GDP(q−1) bridge remain unchanged. Future within-quarter latent factor states are forecasts, not future observed monthly data. Factor dimensionality and monthly parameter count do not increase; lagging M2 can shorten the balanced training window and is explicitly documented in the convergence table.

## Ensemble performance



| Sample | Model | N | H1 RMSE | H2 RMSE | H3 RMSE | Pooled RMSE | MAE | Bias |

|---|---|---:|---:|---:|---:|---:|---:|---:|

| ORIGINAL_HOLDOUT_COMMON | P0 | 12 | 0.671930 | 0.677106 | 0.328716 | 0.582528 | 0.421518 | 0.329872 |

| ORIGINAL_HOLDOUT_COMMON | G1 | 12 | 0.645408 | 0.651980 | 0.303865 | 0.557961 | 0.394812 | 0.292926 |

| ORIGINAL_HOLDOUT_COMMON | G2 | 12 | 0.646056 | 0.652769 | 0.302546 | 0.558280 | 0.388609 | 0.277012 |

| ORIGINAL_HOLDOUT_COMMON | S0 | 12 | 0.690729 | 0.673486 | 0.670942 | 0.678442 | 0.540381 | 0.540381 |

| ORIGINAL_HOLDOUT_COMMON | S1 | 12 | 0.634968 | 0.614855 | 0.612832 | 0.620965 | 0.498301 | 0.466489 |

| ORIGINAL_HOLDOUT_COMMON | S2 | 12 | 0.633445 | 0.608262 | 0.597139 | 0.613137 | 0.492978 | 0.434660 |

| ORIGINAL_HOLDOUT_COMMON | U0 | 12 | 0.813032 | 0.802850 | 0.326822 | 0.686149 | 0.558501 | 0.119364 |

| EXTENDED_COMMON | P0 | 44 | 0.482015 | 0.460713 | 0.298027 | 0.420197 | 0.333252 | 0.242446 |

| EXTENDED_COMMON | G1 | 44 | 0.475299 | 0.453230 | 0.298830 | 0.415153 | 0.331520 | 0.228910 |

| EXTENDED_COMMON | G2 | 44 | 0.485639 | 0.488267 | 0.338725 | 0.442075 | 0.366020 | 0.189276 |

| EXTENDED_COMMON | S0 | 44 | 0.504859 | 0.482322 | 0.476113 | 0.487529 | 0.410833 | 0.377577 |

| EXTENDED_COMMON | S1 | 44 | 0.492419 | 0.463332 | 0.460859 | 0.471957 | 0.402893 | 0.350504 |

| EXTENDED_COMMON | S2 | 44 | 0.520924 | 0.559129 | 0.504724 | 0.528928 | 0.454438 | 0.271236 |

| EXTENDED_COMMON | U0 | 44 | 0.541399 | 0.515852 | 0.444575 | 0.501358 | 0.383518 | 0.107315 |

| EARLIER_DEVELOPMENT_COMMON | P0 | 32 | 0.380366 | 0.350319 | 0.286052 | 0.339891 | 0.300152 | 0.209662 |

| EARLIER_DEVELOPMENT_COMMON | G1 | 32 | 0.386848 | 0.354318 | 0.296978 | 0.346754 | 0.307786 | 0.204903 |

| EARLIER_DEVELOPMENT_COMMON | G2 | 32 | 0.404014 | 0.412492 | 0.350958 | 0.389663 | 0.357549 | 0.156375 |

| EARLIER_DEVELOPMENT_COMMON | S0 | 32 | 0.407422 | 0.390243 | 0.381337 | 0.392695 | 0.362252 | 0.316526 |

| EARLIER_DEVELOPMENT_COMMON | S1 | 32 | 0.422130 | 0.394043 | 0.391224 | 0.402085 | 0.367115 | 0.307010 |

| EARLIER_DEVELOPMENT_COMMON | S2 | 32 | 0.468407 | 0.540155 | 0.466603 | 0.493660 | 0.439986 | 0.209952 |

| EARLIER_DEVELOPMENT_COMMON | U0 | 32 | 0.382033 | 0.358441 | 0.480289 | 0.411181 | 0.317899 | 0.102797 |



Bias is actual minus forecast. Positive OOS R² = improvement, negative = worse: 1 − SSE_challenger/SSE_benchmark. G1/G2 use P0; standalone S1/S2 use S0. Correlation with actual GDP, median and maximum absolute errors, SSE and mean absolute revision appear in the horizon metrics. GDP remains the published cumulative YTD real YoY convention; it is not monthly interpolated.



Original holdout: G2 pooled RMSE improvement 0.024247 pp (4.162%). Below the 0.03 pp practical threshold, or worse than P0.

Original holdout H1: P0 0.671930; G2 0.646056; ΔRMSE G2−P0 -0.025873 pp (improves).

Original holdout H2: P0 0.677106; G2 0.652769; ΔRMSE G2−P0 -0.024337 pp (improves).

Original holdout H3: P0 0.328716; G2 0.302546; ΔRMSE G2−P0 -0.026170 pp (improves).

Original holdout origin-level G2 wins: 9/12 (75.00%); ties 0; worse 3. Leave-one-quarter-out improvement survives every exclusion: True; ΔRMSE range -0.031891 to -0.017388.

Original holdout revisions: P0 mean absolute 0.193951, maximum 0.594044; G2 mean absolute 0.200173, maximum 0.607738. G2 is less stable by mean absolute revision. Directional consistency: P0 50.0%, G2 50.0%.

Extended common sample: G2 pooled RMSE improvement -0.021878 pp (-5.206%). Below the 0.03 pp practical threshold, or worse than P0.

Extended common sample H1: P0 0.482015; G2 0.485639; ΔRMSE G2−P0 0.003623 pp (worsens).

Extended common sample H2: P0 0.460713; G2 0.488267; ΔRMSE G2−P0 0.027554 pp (worsens).

Extended common sample H3: P0 0.298027; G2 0.338725; ΔRMSE G2−P0 0.040698 pp (worsens).

Extended common sample origin-level G2 wins: 19/44 (43.18%); ties 0; worse 25. Leave-one-quarter-out improvement survives every exclusion: False; ΔRMSE range 0.004615 to 0.036276.

Extended common sample revisions: P0 mean absolute 0.132765, maximum 0.967245; G2 mean absolute 0.131676, maximum 0.970504. G2 is more stable by mean absolute revision. Directional consistency: P0 42.9%, G2 35.7%.



Revision chronology in this repository is **H1 → H2 → H3** (first to third month). The requested H3 → H2 → H1 view is also provided with reversed signs; it is a reverse traversal of the saved forecasts, not the calendar order. Absolute revision statistics are invariant to that reversal.

## Error diversification and ensemble revision identity



ORIGINAL_HOLDOUT_COMMON pooled error correlations with U0: S0 0.536244, S1 0.501054, S2 0.506860. M2-L2 reduces error correlation, increasing correlation-based diversification. Exact ensemble-MSE change splits into -0.02108689 from one-quarter of the DFM mean-squared-error change and -0.00657481 from half the change in mean DFM×U-MIDAS error product. Their sum is -0.02766170. The U-MIDAS MSE term is unchanged. This decomposition includes bias, which correlation alone does not capture.

EXTENDED_COMMON pooled error correlations with U0: S0 0.450797, S1 0.452488, S2 0.432542. M2-L2 reduces error correlation, increasing correlation-based diversification. Exact ensemble-MSE change splits into 0.01052000 from one-quarter of the DFM mean-squared-error change and 0.00834438 from half the change in mean DFM×U-MIDAS error product. Their sum is 0.01886438. The U-MIDAS MSE term is unchanged. This decomposition includes bias, which correlation alone does not capture.

At every eligible origin G2−P0 = 0.5(S2−S0), checked to 1e-12. Extended common-sample ensemble revision: mean 0.053171, minimum -0.079914, maximum 0.697706 pp. H1/H2/H3 diversification correlations are provided separately.



## Fixed-weight robustness and statistical uncertainty



ORIGINAL_HOLDOUT_COMMON, DFM/U-MIDAS 25%/75%: M2-L2 ensemble RMSE 0.602757; Δ versus unchanged M2 at the same weights -0.008405; Δ versus production 50/50 0.020229.

ORIGINAL_HOLDOUT_COMMON, DFM/U-MIDAS 50%/50%: M2-L2 ensemble RMSE 0.558280; Δ versus unchanged M2 at the same weights -0.024247; Δ versus production 50/50 -0.024247.

ORIGINAL_HOLDOUT_COMMON, DFM/U-MIDAS 75%/25%: M2-L2 ensemble RMSE 0.562035; Δ versus unchanged M2 at the same weights -0.044809; Δ versus production 50/50 -0.020492.

EXTENDED_COMMON, DFM/U-MIDAS 25%/75%: M2-L2 ensemble RMSE 0.453720; Δ versus unchanged M2 at the same weights 0.009903; Δ versus production 50/50 0.033523.

EXTENDED_COMMON, DFM/U-MIDAS 50%/50%: M2-L2 ensemble RMSE 0.442075; Δ versus unchanged M2 at the same weights 0.021878; Δ versus production 50/50 0.021878.

EXTENDED_COMMON, DFM/U-MIDAS 75%/25%: M2-L2 ensemble RMSE 0.469110; Δ versus unchanged M2 at the same weights 0.033064; Δ versus production 50/50 0.048913.

Only 25/75, 50/50 and 75/25 fixed weights were assessed. G2 remains 50/50. Comparing the changed and unchanged DFM at identical weights isolates M2 timing; comparing with P0 also changes weights. These diagnostics cannot justify weight promotion from the same sample.

EXTENDED_COMMON: exploratory 95% paired quarter-cluster bootstrap interval for RMSE(G2)−RMSE(P0): [-0.014873, 0.081889] pp from 15 quarter clusters. Mean paired squared-loss difference 0.01886438.

ORIGINAL_HOLDOUT_COMMON: exploratory 95% paired quarter-cluster bootstrap interval for RMSE(G2)−RMSE(P0): [-0.048142, 0.004180] pp from 4 quarter clusters. Mean paired squared-loss difference -0.02766170.

EARLIER_DEVELOPMENT_COMMON: exploratory 95% paired quarter-cluster bootstrap interval for RMSE(G2)−RMSE(P0): [-0.002089, 0.121633] pp from 11 quarter clusters. Mean paired squared-loss difference 0.03631166.

Horizons within a quarter are dependent. Four original holdout clusters are too few for strong significance claims; extended development results are not independent confirmation. Bootstrap intervals are descriptive and do not resolve revision-value leakage. No unsupported Diebold–Mariano p-value is asserted.



## Convergence, complexity and factors



S0: 51 successful DFM fits; EM iterations median 68.0, max 165; training months 36–87; monthly parameters 18, factor AR order 2. Rejected fits remain excluded in the eligibility table.

S1: 48 successful DFM fits; EM iterations median 63.0, max 152; training months 38–86; monthly parameters 18, factor AR order 2. Rejected fits remain excluded in the eligibility table.

S2: 44 successful DFM fits; EM iterations median 97.0, max 145; training months 40–85; monthly parameters 18, factor AR order 2. Rejected fits remain excluded in the eligibility table.

Current S0: factor correlation with S0 1.000000, sign alignment 1, factor SD 1.871131, lag-1 persistence 0.962035; factor AR coefficients (1.354396, -0.399762); M2 loading 0.519784; converged True.

Current S1: factor correlation with S0 0.964240, sign alignment 1, factor SD 1.839839, lag-1 persistence 0.961234; factor AR coefficients (1.356768, -0.401885); M2 loading 0.528105; converged True.

Current S2: factor correlation with S0 0.906796, sign alignment 1, factor SD 1.791046, lag-1 persistence 0.962303; factor AR coefficients (1.405649, -0.450348); M2 loading 0.540672; converged True.

Factors are sign-aligned diagnostically before comparison. Predictions retain the untouched fitted factor/bridge pairing, so alignment cannot manufacture forecast changes. M2-L2 is not merely a sign flip. Loadings are measurement associations, not causal contributions. Every loading and its absolute share and change versus S0 is in phase6g_factor_loadings.csv; loading-share changes do not decompose GDP effects.

S2 industrial_production: loading 0.041766, Δ vs S0 -0.036128, absolute loading share 3.63%.

S2 ppi: loading -0.011731, Δ vs S0 0.029781, absolute loading share 1.02%.

S2 usd_uzs: loading -0.166182, Δ vs S0 -0.000367, absolute loading share 14.45%.

S2 rub_uzs: loading -0.008817, Δ vs S0 -0.045740, absolute loading share 0.77%.

S2 gold_price: loading 0.011017, Δ vs S0 -0.005317, absolute loading share 0.96%.

S2 fx_reserves_ex_gold: loading 0.015793, Δ vs S0 -0.042205, absolute loading share 1.37%.

S2 pos_turnover: loading 0.353908, Δ vs S0 0.018401, absolute loading share 30.78%.



## Current quarter and governance



| Model | Frozen-cutoff 2026Q3 nowcast (%) | Δ vs P0 (pp) |

|---|---:|---:|

| P0 | 8.180901341 | 0.000000000 |

| G1 | 8.215978822 | 0.035077482 |

| G2 | 8.237175217 | 0.056273877 |

| S0 | 8.301152885 | 0.120251545 |

| S1 | 8.371307849 | 0.190406509 |

| S2 | 8.413700639 | 0.232799298 |

| U0 | 8.060649796 | -0.120251545 |



G2 is 8.237175217%, 0.056273877 pp above the unchanged 8.180901341% production estimate. These are rebuilt from the exact archived Phase 6E economic inputs at its 2026-10-05 cutoff, not hard-coded or refreshed to the execution date.

The serious-candidate screen considers both original-holdout and extended common samples: at least 0.03 pp pooled improvement, no horizon deterioration, improvement after every quarter exclusion, at least 50% origin win rate, and no more than 25% mean-absolute-revision deterioration. The revision screen is a declared research governance tolerance, not an estimated model parameter. All successful fits must pass the unchanged convergence and information-boundary gates. The 0.05 pp threshold is highlighted as economically relevant, not automatic promotion.

Classification: PHASE6G_INCONCLUSIVE. Recommendation: KEEP_PHASE6E_PRODUCTION. The combined evidence does not justify advancing M2-L2 to shadow production under this screen.

Historical M2 value-vintage evidence remains unresolved even if a publication mask passes. No release dates are invented: assumed availability and verified GDP publication dates are distinguished. Predictor revision-value leakage cannot be ruled out. Phase 6E production, its COMBO_50_50 configuration and dashboards remain unchanged.

Reproduce with `.venv/Scripts/python.exe -m scripts.phase6g.run`. Independent refit-rerun verification and completed test counts are attached in phase6g_validation_evidence.json and phase6g_determinism.json. Protected artifacts are hashed before and after; a changed protected file fails the run. No network request or production writer is invoked.

## Completed validation

157 tests: 157 passed, 0 failures, 0 errors, 0 skips. The existing Phase 6E/6F and model suite passed 134 tests; the new Phase 6G suite passed 23. Two independent complete refits produced identical checksums for all 16 numerical CSV outputs. All 643 protected artifact checksums remain unchanged. Completed XML, scope counts and JSON validation evidence are stored in this folder. These tests establish the stated availability rules and deterministic computation; they do not recover missing historical predictor value vintages.

PHASE6G_INCONCLUSIVE

KEEP_PHASE6E_PRODUCTION
