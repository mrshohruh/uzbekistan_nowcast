# Phase 6B: small-scale DFM research

**CALENDAR_PSEUDO_REAL_TIME_RESEARCH. RESEARCH ONLY. No promotion, registry amendment or production replacement.**

## Sources and frozen definitions

Monthly panel: `data/research/phase6a2/cbu_midas_monthly_panel.csv`, January 2021–August 2026, **68 consecutive months**, no predictor interpolation or historical splice. GDP: `data/master/gdp_quarterly.parquet`, field `gdp_real_yoy_pct`, the existing published cumulative quarterly growth convention, unchanged. This is not a reconstructed standalone-quarter GDP growth target. Current GDP retrieval metadata differs from the original freeze; every GDP value was checked against saved frozen outcomes and agrees to 1e-10.

H1/H2/H3 are the first/second/third target-quarter month ends, exactly from `uznowcast.models.data.horizon_month_end`. Release masks call the frozen `information_cutoff_for_variable`: month end plus registry lag, standard or conservative (+15 days, minimum 3). Industrial production lag 33 days, construction 27, retail 24, imports 26. Services is not a V1.2 registry series: the inherited function's **30-day fallback** is explicit research timing metadata, not an observed release date. No registry was amended. POS uses its existing 18-day lag.

Quarter origins: **2024Q1–2026Q2**, ten distinct quarters. Frozen development subset: **2024Q1–2025Q2** (six); historical post-development subset: **2025Q3–2026Q2** (four). Both partitions are reported; none is claimed to be a pristine unseen holdout. Each full-coverage model/bridge has up to **10 H1, 10 H2, 10 H3 forecasts per lag mode**. Origin counts and failures are explicit CSV rows, not manufactured extra tests. Optional POS ends December 2024 and has only four calendar target quarters.

Saved AR/U-MIDAS predictions come from Phase 4B development and Phase 4C holdout artifacts underlying the Phase 5A frozen architecture. The saved Phase 5C USD U-MIDAS(3) challenger predictions were verified numerically identical on all matched non-missing origins (identity audit CSV). Production remains 0.5 AR(2) + 0.5 USD U-MIDAS(3). Phase 5C saved DFM metrics but **did not persist its origin-level predictions**. Those aggregate metrics are available at `results/challengers/phase5c/phase5c_dfm_metrics.csv`; they cannot support an exact Phase 6B matched-origin comparison and are not substituted or rerun.

## Estimation and leakage controls

State-space equation: standardized indicators = loadings × factors + diagonal white-noise measurement errors; factor dynamics are stationary AR(1), identity innovation variance. One factor for primary/robustness models; two-factor imports uses unrestricted VAR(1), rejected if covariance condition exceeds 1e12. L-BFGS is followed by BFGS only on nonconvergence; each capped at 400 iterations. Nonconverged/near-unit-root origins are unavailable rather than silently accepted.

At each origin, masks apply first. Services adjustment regresses its observed training values on an intercept and regime indicator; only the dummy coefficient is subtracted from post-break observations. With no training post-break observations, adjustment is zero and marked unidentified. Training means/stds use masked months strictly before the target quarter. DFM parameters are estimated on those same training months, then held fixed while filtering through the masked origin. Missing future target-quarter measurements remain null; latent states are model-predicted through quarter end. No observed predictor is filled. Bridges A/B use full-quarter means of **filtered/predicted states**, with at least 12 GDP quarters before the target. B adds prior-quarter GDP; A omits it. Full-sample smoothed states appear only in rows explicitly labelled descriptive and forecast-ineligible.

Sign normalization makes industrial loading positive. Two-factor signs do not remove rotational ambiguity. Predictor/factor correlations, expanding loading changes, training means/stds, services raw/adjusted values, regime adjustments and optimizer diagnostics are saved per origin. Descriptive full-sample loadings below are not forecast-origin parameters.

## Recomputed factor structure

| predictor_set | variance_pct | pc1_loadings |
| --- | --- | --- |
| DOMESTIC_3 | 77.7080 | {"industrial_production": 0.5814739300388297, "construction": 0.5952713002224457, "retail_trade": 0.5545630242061559} |
| DOMESTIC_3_PLUS_IMPORTS | 58.3941 | {"industrial_production": 0.5797937283122161, "construction": 0.5965073111631138, "retail_trade": 0.5519321440658232, "imports_total_monthly_log_yoy": -0.058216567106578666} |
| DOMESTIC_3_PLUS_SERVICES | 68.1798 | {"industrial_production": 0.5413792420165208, "construction": 0.49835798179913804, "retail_trade": 0.5195939892226823, "services_output": 0.43424638703663077} |
| DOMESTIC_3_PLUS_IMPORTS_PLUS_SERVICES | 54.5446 | {"industrial_production": 0.5414091118215743, "construction": 0.4986356802016093, "retail_trade": 0.5195510580393448, "imports_total_monthly_log_yoy": -0.00475619037951428, "services_output": 0.43391555492943895} |

Stored-panel results are checked against the requested approximate PC1 shares with a one-percentage-point tolerance; imports loading must have absolute magnitude <=0.12. Eigenvalues, all component shares and correlation matrices are saved.

| specification | variable | loading | idiosyncratic_variance |
| --- | --- | --- | --- |
| DFM_DOMESTIC_3 | industrial_production | 0.6018 | 0.3112 |
| DFM_DOMESTIC_3 | construction | 0.6256 | 0.2570 |
| DFM_DOMESTIC_3 | retail_trade | 0.5640 | 0.3932 |
| DFM_DOMESTIC_3_SERVICES | industrial_production | 0.3745 | 0.6290 |
| DFM_DOMESTIC_3_SERVICES | construction | 0.4066 | 0.5653 |
| DFM_DOMESTIC_3_SERVICES | retail_trade | 0.6229 | 0.0000 |
| DFM_DOMESTIC_3_SERVICES | services_output | 0.3502 | 0.6739 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK | industrial_production | 0.3746 | 0.6290 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK | construction | 0.4067 | 0.5654 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK | retail_trade | 0.6229 | 0.0000 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK | services_output | 0.3537 | 0.6676 |
| DFM_DOMESTIC_3_IMPORTS | industrial_production | 0.3745 | 0.6290 |
| DFM_DOMESTIC_3_IMPORTS | construction | 0.4066 | 0.5654 |
| DFM_DOMESTIC_3_IMPORTS | retail_trade | 0.6229 | 0.0000 |
| DFM_DOMESTIC_3_IMPORTS | imports_total_monthly_log_yoy | 0.0086 | 0.9851 |
| DFM_TWO_FACTOR_IMPORTS | industrial_production | 0.5040 | 0.0000 |
| DFM_TWO_FACTOR_IMPORTS | construction | 0.4654 | 0.3789 |
| DFM_TWO_FACTOR_IMPORTS | retail_trade | 0.5817 | 0.0234 |
| DFM_TWO_FACTOR_IMPORTS | imports_total_monthly_log_yoy | 0.0026 | 0.9839 |
| DFM_POS_HISTORICAL_ROBUSTNESS_ONLY | industrial_production | 0.7883 | 0.0000 |
| DFM_POS_HISTORICAL_ROBUSTNESS_ONLY | construction | 0.6495 | 0.3143 |
| DFM_POS_HISTORICAL_ROBUSTNESS_ONLY | retail_trade | 0.5978 | 0.4160 |
| DFM_POS_HISTORICAL_ROBUSTNESS_ONLY | pos_turnover_monthly_log_yoy | -0.1719 | 0.9326 |

## Exactly common standard-lag origins

Intersection across successful primary one-factor variants/bridges and frozen benchmarks. POS and two-factor models do not reduce the main comparison intersection. Pairwise matched samples include these optional models separately. RMSE/MAE are percentage points; bias = actual minus forecast.

| model | horizon | n | quarters | rmse | mae | bias |
| --- | --- | --- | --- | --- | --- | --- |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_A | H1 | 10 | 10 | 0.8599 | 0.6233 | 0.5875 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_A | H2 | 10 | 10 | 0.8235 | 0.6098 | 0.4632 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_A | H3 | 10 | 10 | 0.8699 | 0.6891 | 0.3956 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_A | ALL | 30 | 10 | 0.8514 | 0.6408 | 0.4821 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_B | H1 | 10 | 10 | 0.6152 | 0.4338 | 0.3785 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_B | H2 | 10 | 10 | 0.6147 | 0.4381 | 0.3232 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_B | H3 | 10 | 10 | 0.6441 | 0.4888 | 0.2905 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_B | ALL | 30 | 10 | 0.6248 | 0.4536 | 0.3308 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_A | H1 | 10 | 10 | 0.8686 | 0.6312 | 0.6040 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_A | H2 | 10 | 10 | 0.8241 | 0.6172 | 0.4747 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_A | H3 | 10 | 10 | 0.8712 | 0.6929 | 0.4137 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_A | ALL | 30 | 10 | 0.8549 | 0.6471 | 0.4974 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_B | H1 | 10 | 10 | 0.6177 | 0.4347 | 0.3854 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_B | H2 | 10 | 10 | 0.6150 | 0.4409 | 0.3278 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_B | H3 | 10 | 10 | 0.6430 | 0.4889 | 0.2977 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_B | ALL | 30 | 10 | 0.6253 | 0.4548 | 0.3370 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_A | H1 | 10 | 10 | 0.8597 | 0.6228 | 0.5956 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_A | H2 | 10 | 10 | 0.8114 | 0.6059 | 0.4634 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_A | H3 | 10 | 10 | 0.8508 | 0.6747 | 0.3955 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_A | ALL | 30 | 10 | 0.8409 | 0.6345 | 0.4848 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_B | H1 | 10 | 10 | 0.6143 | 0.4310 | 0.3818 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_B | H2 | 10 | 10 | 0.6155 | 0.4393 | 0.3262 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_B | H3 | 10 | 10 | 0.6439 | 0.4866 | 0.2953 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_B | ALL | 30 | 10 | 0.6247 | 0.4523 | 0.3344 |
| DFM_DOMESTIC_3__BRIDGE_A | H1 | 10 | 10 | 0.8604 | 0.6231 | 0.5891 |
| DFM_DOMESTIC_3__BRIDGE_A | H2 | 10 | 10 | 0.8242 | 0.6107 | 0.4621 |
| DFM_DOMESTIC_3__BRIDGE_A | H3 | 10 | 10 | 0.8705 | 0.6898 | 0.3954 |
| DFM_DOMESTIC_3__BRIDGE_A | ALL | 30 | 10 | 0.8519 | 0.6412 | 0.4822 |
| DFM_DOMESTIC_3__BRIDGE_B | H1 | 10 | 10 | 0.6152 | 0.4337 | 0.3793 |
| DFM_DOMESTIC_3__BRIDGE_B | H2 | 10 | 10 | 0.6151 | 0.4386 | 0.3226 |
| DFM_DOMESTIC_3__BRIDGE_B | H3 | 10 | 10 | 0.6444 | 0.4892 | 0.2904 |
| DFM_DOMESTIC_3__BRIDGE_B | ALL | 30 | 10 | 0.6251 | 0.4538 | 0.3308 |
| ar1 | H1 | 10 | 10 | 0.6062 | 0.5095 | 0.5095 |
| ar1 | H2 | 10 | 10 | 0.6062 | 0.5095 | 0.5095 |
| ar1 | H3 | 10 | 10 | 0.6062 | 0.5095 | 0.5095 |
| ar1 | ALL | 30 | 10 | 0.6062 | 0.5095 | 0.5095 |
| ar2 | H1 | 10 | 10 | 0.7619 | 0.6491 | 0.6491 |
| ar2 | H2 | 10 | 10 | 0.7619 | 0.6491 | 0.6491 |
| ar2 | H3 | 10 | 10 | 0.7619 | 0.6491 | 0.6491 |
| ar2 | ALL | 30 | 10 | 0.7619 | 0.6491 | 0.6491 |
| ensemble_ar2_umidas_usd | H1 | 10 | 10 | 0.6413 | 0.5332 | 0.4700 |
| ensemble_ar2_umidas_usd | H2 | 10 | 10 | 0.6689 | 0.5401 | 0.4975 |
| ensemble_ar2_umidas_usd | H3 | 10 | 10 | 0.4130 | 0.3148 | 0.2440 |
| ensemble_ar2_umidas_usd | ALL | 30 | 10 | 0.5857 | 0.4627 | 0.4038 |
| umidas_usd_uzs_mom_dlog | H1 | 10 | 10 | 0.6773 | 0.5600 | 0.2908 |
| umidas_usd_uzs_mom_dlog | H2 | 10 | 10 | 0.6898 | 0.5753 | 0.3459 |
| umidas_usd_uzs_mom_dlog | H3 | 10 | 10 | 0.5311 | 0.3995 | -0.1611 |
| umidas_usd_uzs_mom_dlog | ALL | 30 | 10 | 0.6368 | 0.5116 | 0.1585 |

## Frozen post-development partition versus U-MIDAS

| model | horizon | n | rmse | mae | bias | benchmark_rmse | rmse_difference |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_A | H1 | 4 | 1.3146 | 1.2569 | 1.2569 | 0.9670 | 0.3476 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_A | H2 | 4 | 1.2212 | 1.1670 | 1.1670 | 0.9302 | 0.2910 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_A | H3 | 4 | 1.1643 | 1.1246 | 1.1246 | 0.5428 | 0.6215 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_A | ALL | 12 | 1.2349 | 1.1828 | 1.1828 | 0.8356 | 0.3993 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_B | H1 | 4 | 0.9374 | 0.8611 | 0.8611 | 0.9670 | -0.0296 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_B | H2 | 4 | 0.9143 | 0.8366 | 0.8366 | 0.9302 | -0.0159 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_B | H3 | 4 | 0.9015 | 0.8276 | 0.8276 | 0.5428 | 0.3587 |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_B | ALL | 12 | 0.9178 | 0.8418 | 0.8418 | 0.8356 | 0.0822 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_A | H1 | 4 | 1.3259 | 1.2700 | 1.2700 | 0.9670 | 0.3589 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_A | H2 | 4 | 1.2160 | 1.1690 | 1.1690 | 0.9302 | 0.2858 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_A | H3 | 4 | 1.1699 | 1.1348 | 1.1348 | 0.5428 | 0.6271 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_A | ALL | 12 | 1.2390 | 1.1913 | 1.1913 | 0.8356 | 0.4034 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_B | H1 | 4 | 0.9410 | 0.8653 | 0.8653 | 0.9670 | -0.0259 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_B | H2 | 4 | 0.9125 | 0.8359 | 0.8359 | 0.9302 | -0.0177 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_B | H3 | 4 | 0.9016 | 0.8289 | 0.8289 | 0.5428 | 0.3588 |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_B | ALL | 12 | 0.9185 | 0.8434 | 0.8434 | 0.8356 | 0.0829 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_A | H1 | 4 | 1.3131 | 1.2553 | 1.2553 | 0.9670 | 0.3462 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_A | H2 | 4 | 1.1966 | 1.1482 | 1.1482 | 0.9302 | 0.2664 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_A | H3 | 4 | 1.1351 | 1.0993 | 1.0993 | 0.5428 | 0.5923 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_A | ALL | 12 | 1.2172 | 1.1676 | 1.1676 | 0.8356 | 0.3815 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_B | H1 | 4 | 0.9362 | 0.8592 | 0.8592 | 0.9670 | -0.0307 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_B | H2 | 4 | 0.9139 | 0.8349 | 0.8349 | 0.9302 | -0.0163 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_B | H3 | 4 | 0.9041 | 0.8271 | 0.8271 | 0.5428 | 0.3613 |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_B | ALL | 12 | 0.9182 | 0.8404 | 0.8404 | 0.8356 | 0.0826 |
| DFM_DOMESTIC_3__BRIDGE_A | H1 | 4 | 1.3153 | 1.2577 | 1.2577 | 0.9670 | 0.3483 |
| DFM_DOMESTIC_3__BRIDGE_A | H2 | 4 | 1.2206 | 1.1664 | 1.1664 | 0.9302 | 0.2904 |
| DFM_DOMESTIC_3__BRIDGE_A | H3 | 4 | 1.1636 | 1.1239 | 1.1239 | 0.5428 | 0.6208 |
| DFM_DOMESTIC_3__BRIDGE_A | ALL | 12 | 1.2347 | 1.1827 | 1.1827 | 0.8356 | 0.3991 |
| DFM_DOMESTIC_3__BRIDGE_B | H1 | 4 | 0.9375 | 0.8614 | 0.8614 | 0.9670 | -0.0294 |
| DFM_DOMESTIC_3__BRIDGE_B | H2 | 4 | 0.9141 | 0.8364 | 0.8364 | 0.9302 | -0.0161 |
| DFM_DOMESTIC_3__BRIDGE_B | H3 | 4 | 0.9012 | 0.8273 | 0.8273 | 0.5428 | 0.3584 |
| DFM_DOMESTIC_3__BRIDGE_B | ALL | 12 | 0.9177 | 0.8417 | 0.8417 | 0.8356 | 0.0821 |

## Equal-weight combinations

Separate combinations for every DFM/bridge avoid ex-post best-model selection. No error-based adaptive weights were fitted. Each row uses identical origins for the combination and U-MIDAS; development and post-development remain separate.

| model | evaluation_group | n | rmse | mae | benchmark_rmse | rmse_difference |
| --- | --- | --- | --- | --- | --- | --- |
| COMBO_EQUAL__DFM_DOMESTIC_3_IMPORTS__BRIDGE_A | DEVELOPMENT_PSEUDO_OOS | 18 | 0.3056 | 0.2519 | 0.4587 | -0.1531 |
| COMBO_EQUAL__DFM_DOMESTIC_3_IMPORTS__BRIDGE_A | HISTORICAL_POST_DEVELOPMENT_TEST | 12 | 0.8523 | 0.6893 | 0.8356 | 0.0167 |
| COMBO_EQUAL__DFM_DOMESTIC_3_IMPORTS__BRIDGE_B | DEVELOPMENT_PSEUDO_OOS | 18 | 0.2615 | 0.2208 | 0.4587 | -0.1971 |
| COMBO_EQUAL__DFM_DOMESTIC_3_IMPORTS__BRIDGE_B | HISTORICAL_POST_DEVELOPMENT_TEST | 12 | 0.7319 | 0.6045 | 0.8356 | -0.1037 |
| COMBO_EQUAL__DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_A | DEVELOPMENT_PSEUDO_OOS | 18 | 0.3101 | 0.2564 | 0.4587 | -0.1486 |
| COMBO_EQUAL__DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_A | HISTORICAL_POST_DEVELOPMENT_TEST | 12 | 0.8526 | 0.6915 | 0.8356 | 0.0169 |
| COMBO_EQUAL__DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_B | DEVELOPMENT_PSEUDO_OOS | 18 | 0.2634 | 0.2229 | 0.4587 | -0.1953 |
| COMBO_EQUAL__DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_B | HISTORICAL_POST_DEVELOPMENT_TEST | 12 | 0.7317 | 0.6039 | 0.8356 | -0.1039 |
| COMBO_EQUAL__DFM_DOMESTIC_3_SERVICES__BRIDGE_A | DEVELOPMENT_PSEUDO_OOS | 18 | 0.3083 | 0.2548 | 0.4587 | -0.1503 |
| COMBO_EQUAL__DFM_DOMESTIC_3_SERVICES__BRIDGE_A | HISTORICAL_POST_DEVELOPMENT_TEST | 12 | 0.8436 | 0.6814 | 0.8356 | 0.0080 |
| COMBO_EQUAL__DFM_DOMESTIC_3_SERVICES__BRIDGE_B | DEVELOPMENT_PSEUDO_OOS | 18 | 0.2627 | 0.2222 | 0.4587 | -0.1960 |
| COMBO_EQUAL__DFM_DOMESTIC_3_SERVICES__BRIDGE_B | HISTORICAL_POST_DEVELOPMENT_TEST | 12 | 0.7317 | 0.6024 | 0.8356 | -0.1040 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_A | DEVELOPMENT_PSEUDO_OOS | 18 | 0.3064 | 0.2528 | 0.4587 | -0.1523 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_A | HISTORICAL_POST_DEVELOPMENT_TEST | 12 | 0.8522 | 0.6893 | 0.8356 | 0.0166 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B | DEVELOPMENT_PSEUDO_OOS | 18 | 0.2618 | 0.2214 | 0.4587 | -0.1968 |
| COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B | HISTORICAL_POST_DEVELOPMENT_TEST | 12 | 0.7319 | 0.6044 | 0.8356 | -0.1038 |
| COMBO_EQUAL__DFM_POS_HISTORICAL_ROBUSTNESS_ONLY__BRIDGE_A | DEVELOPMENT_PSEUDO_OOS | 12 | 0.2581 | 0.2015 | 0.3492 | -0.0912 |
| COMBO_EQUAL__DFM_POS_HISTORICAL_ROBUSTNESS_ONLY__BRIDGE_B | DEVELOPMENT_PSEUDO_OOS | 12 | 0.2035 | 0.1704 | 0.3492 | -0.1458 |

## Convergence, stability and research decisions

Nonconverged actual fit records: **0**. Failed-origin records (including identification and bridge failures): **60**. Successful research forecasts across models, bridges and lag modes: **528**. Two-factor fits attempted, including descriptive: **2**. Its first expanding-origin fit failed identification and remaining origins were explicitly skipped; this is **NOT_ESTIMABLE_WITH_CURRENT_SAMPLE**, not 60 optimizer failures. All optimizer warnings and covariance conditions are retained. Services dummy identification changes recursively after the break; its adjustment must not be interpreted as causal or a verified methodological correction.

| model | classification | failure_rate | successful_origins | quarters | rationale |
| --- | --- | --- | --- | --- | --- |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_A | NO_INCREMENTAL_VALUE | 0.0000 | 30 | 10 | does not meet prespecified standalone gain criteria; combinations reported separately |
| DFM_DOMESTIC_3_IMPORTS__BRIDGE_B | PROMISING_RESEARCH_CHALLENGER | 0.0000 | 30 | 10 | pooled matched RMSE/MAE gains with gains in at least two horizons; only exploratory evidence |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_A | NO_INCREMENTAL_VALUE | 0.0000 | 30 | 10 | does not meet prespecified standalone gain criteria; combinations reported separately |
| DFM_DOMESTIC_3_SERVICES_RAW_BREAK__BRIDGE_B | PROMISING_RESEARCH_CHALLENGER | 0.0000 | 30 | 10 | pooled matched RMSE/MAE gains with gains in at least two horizons; only exploratory evidence |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_A | NO_INCREMENTAL_VALUE | 0.0000 | 30 | 10 | does not meet prespecified standalone gain criteria; combinations reported separately |
| DFM_DOMESTIC_3_SERVICES__BRIDGE_B | PROMISING_RESEARCH_CHALLENGER | 0.0000 | 30 | 10 | pooled matched RMSE/MAE gains with gains in at least two horizons; only exploratory evidence |
| DFM_DOMESTIC_3__BRIDGE_A | NO_INCREMENTAL_VALUE | 0.0000 | 30 | 10 | does not meet prespecified standalone gain criteria; combinations reported separately |
| DFM_DOMESTIC_3__BRIDGE_B | PROMISING_RESEARCH_CHALLENGER | 0.0000 | 30 | 10 | pooled matched RMSE/MAE gains with gains in at least two horizons; only exploratory evidence |
| DFM_POS_HISTORICAL_ROBUSTNESS_ONLY__BRIDGE_A | INSUFFICIENT_EVIDENCE | 0.0000 | 12 | 4 | fewer than eight distinct evaluation quarters |
| DFM_POS_HISTORICAL_ROBUSTNESS_ONLY__BRIDGE_B | INSUFFICIENT_EVIDENCE | 0.0000 | 12 | 4 | fewer than eight distinct evaluation quarters |
| DFM_TWO_FACTOR_IMPORTS__BRIDGE_A | UNSTABLE | 1.0000 | 0 | 0 | 100% origin failure rate |
| DFM_TWO_FACTOR_IMPORTS__BRIDGE_B | UNSTABLE | 1.0000 | 0 | 0 | 100% origin failure rate |

The prespecified classification rule is recorded in the specifications JSON. Pooled gains are exploratory; the post-development sample is only four quarters. No significance claim is made, and repeated H1/H2/H3 errors are not 30 independent GDP outcomes.

## Required questions

1. **Domestic factor:** yes. Domestic PC1 explains 77.71% over 68 months. This is descriptive coherence, not GDP predictive validation.
2. **Variables loading:** industrial production, construction and retail form the coherent block. Signed PCA eigenvectors and standardized state-space loadings are both saved; their scales differ.
3. **Imports:** its PCA loading is weak and adding it lowers PC1 share. One-factor GDP bridge B versus domestic bridge B: RMSE 0.6248 versus 0.6251 (-0.0002). Two-factor identification is separately diagnosed; no interpretation of unidentified rotated factors.
4. **Services:** training-only adjusted services bridge B versus domestic bridge B: RMSE 0.6247 versus 0.6251 (-0.0004). Raw-break robustness is separate. A level dummy cannot prove the expanded reporting universe is economically comparable.
5. **Standalone GDP forecasts:** primary domestic bridge B versus frozen U-MIDAS: RMSE 0.6251 versus 0.6368 (-0.0118). Bridge A versus B: RMSE 0.8519 versus 0.6251 (+0.2269). AR(1) and the production ensemble have lower pooled RMSE than standalone DFM. On the four post-development quarters, domestic bridge B pooled RMSE is 0.9177 versus U-MIDAS 0.8356, so the standalone advantage does not persist in the later partition.
6. **Combination:** equal-weight domestic bridge B plus U-MIDAS: RMSE 0.5054 versus 0.6368 (-0.1315). On the post-development partition: 0.7319 versus U-MIDAS 0.8356. Each specification/bridge has its own combination; none was selected using its test errors.
7. **Retain as active challenger:** the prespecified primary domestic model plus lagged GDP is promising chiefly as an equal-weight combination research candidate. Standalone evidence is mixed and does not support replacement. The pooled-rule labels below are provisional; only four later quarters are available. This run does not activate or promote any model.
8. **Limits:** 68 monthly observations, only 12 initial GDP training quarters and 10 evaluation quarters, revised rather than first-release inputs, published cumulative real-activity growth versus nominal monthly import growth, an unresolved services universe change, and release-lag assumptions. Bridge sensitivity and convergence failures quantify additional limitations. A strong domestic factor alone does not establish incremental GDP information.

## Reproduction and governance

Run `.venv/Scripts/python.exe scripts/research/phase6b/run.py`; tests: `.venv/Scripts/python.exe -m pytest -q -o addopts='' scripts/research/phase6b/test_experiment.py`. Research dependency pins are local to this directory. Seeds and input/code hashes are in the manifest. Numeric tables are deterministic conditional on pinned libraries and stored inputs; timestamps/log durations change.

**457 protected artifacts were SHA256-identical before and after execution.** The persistent baseline includes production code, registries, canonical masters/metadata, Phase 5 artifacts, Phase 5D monitoring, Phase 6A data/reports and current dashboard. Pre-existing inaccessible vendored reader/test-cache directories are outside the model/artifact inventory; their state was not repaired. Protected start/end inventories are separate artifacts; the runner refuses to overwrite the baseline. No forecast history was rewritten. Stop after Phase 6B; no collection phase starts automatically.


Final verification: **17 tests passed**, no failures/skips. **7 core numeric tables byte-identical across reruns**. **457 protected artifacts unchanged**. Test XML and determinism hashes are saved beside the manifest.
