# Phase 6F — research only



Production remains COMBO_50_50. No model is promoted. Exact Phase 6E DFM and U-MIDAS reconstruction is required before writing the report.



## Audit and design



M2 is CBU broad money liabilities, end-of-period billion UZS, transformed to 100 ln(M2_t/M2_t-12). It enters the factor contemporaneously in economic time, with a 25-day registry publication mask. M1/M2 shift the transformed, release-gated series by one/two calendar months. Publication lag and economic lag are separate.

Historical M2 values are revised snapshots, not verified historical releases. The page update attached to the whole workbook is not an observation-level first release. Timing masks prevent future reference-period use under assumptions, but revision leakage cannot be excluded. No forecast here is certified vintage-real-time.

The eight predictors are industrial production, PPI, USD/UZS, RUB/UZS, gold price, M2, FX reserves excluding gold, and scope-limited POS turnover. Factor extraction is one filtered EM-MLE DynamicFactorMQ factor, AR(2), no idiosyncratic AR(1), training-only scaling and balanced start. GDP bridge is intercept + quarterly mean factor + GDP(q-1); GDP vintages are strictly publication-gated. The GDP target is published cumulative YTD YoY, not standalone-quarter growth.

B1/B2 retain the existing factor and GDP AR term and add quarter-mean transformed M2 with economic L1/L2. Training covariates use the same H1/H2/H3 calendar stage of each training quarter. B3/B4 add latest assumed-available quarterly FDI / an extra quarter; B5 uses M1 factors and only FDI as the additional bridge term. FDI never enters a monthly panel.



## FDI evidence



[Official CBU source](https://cbu.uz/en/statistics/e-gdds/data/127982/) and its exact analytical BOP workbook were discovered after repository search found no existing FDI ingestion or named FDI data file. Exact row: Direct investment: liabilities. Quarterly net incurrence of direct-investment liabilities, nominal million USD; this is a financial-account flow, not FDI stock, not gross inflows, and not the assets-minus-liabilities balance. The workbook unit is million USD; the page’s generic end-of-period label should not turn BOP transactions into a stock.

Coverage 2005Q1–2026Q2; missing cells 0. This is a revised 2026 snapshot without recovered historical value vintages. A 90-day and a 120-day quarter-end lag are conservative research assumptions, not observed release dates. Assumed dates are stored separately; source_release_date stays null.

FDI B3/B4/B5 estimates are explicitly revised-history timing sensitivities, not valid real-time forecasts. Their numbers must not be used for promotion. The newly retrieved FDI workbook postdates the frozen 2026-10-05 production cutoff, so no valid current FDI challenger nowcast is published. Historical archive-vintage recovery remains necessary.



## Evaluation



The exact twelve Phase 6E holdout origins (four quarters, H1/H2/H3) are reused. Every metric pairs challenger and benchmark on identical origins and actual vintages. Full available counts equal the common counts when no model failed. POST_DEVELOPMENT equals the existing holdout; there is no new prospective realization evidence. Bias is actual minus forecast. OOS R² = 1 − SSE_model/SSE_M0; negative values mean worse performance.



| Model | N | H1 RMSE | H2 RMSE | H3 RMSE | Pooled RMSE | Δ RMSE | OOS R² |

|---|---:|---:|---:|---:|---:|---:|---:|

| B1 | 12 | 0.597425 | 0.701518 | 0.647785 | 0.650300 | -0.028143 | 0.081242 |

| B2 | 12 | 0.584529 | 0.641900 | 0.646960 | 0.625105 | -0.053338 | 0.151055 |

| B3 | 12 | 0.643926 | 0.670635 | 0.447085 | 0.595616 | -0.082826 | 0.229262 |

| B3_120D | 12 | 0.643926 | 0.670635 | 0.646376 | 0.653757 | -0.024686 | 0.071448 |

| B4 | 12 | 1.023449 | 1.092733 | 0.646376 | 0.941508 | 0.263066 | -0.925849 |

| B4_120D | 12 | 1.023449 | 1.092733 | 1.051185 | 1.056173 | 0.377730 | -1.423504 |

| B5 | 12 | 0.655279 | 0.638593 | 0.331314 | 0.561831 | -0.116612 | 0.314220 |

| B5_120D | 12 | 0.655279 | 0.638593 | 0.639460 | 0.644490 | -0.033953 | 0.097586 |

| M0 | 12 | 0.690729 | 0.673486 | 0.670942 | 0.678442 | 0.000000 | 0.000000 |

| M1 | 12 | 0.634968 | 0.614855 | 0.612832 | 0.620965 | -0.057477 | 0.162261 |

| M2 | 12 | 0.633445 | 0.608262 | 0.597139 | 0.613137 | -0.065306 | 0.183251 |



M1/M2 improvement is assessed from the reported common-sample deltas, never in-sample R². Improvements of 0.03/0.05 pp are highlighted thresholds only; revised-history diagnostics and four quarters cannot justify promotion. Horizon metrics show the strongest/weakest horizon without asserting statistical significance.

Bridge coefficient files contain signs, OLS standard errors, VIF, condition number, Durbin–Watson, leverage and Cook’s distance by origin. Standard errors are descriptive with a small sample. DFM files contain loadings, EM convergence and factor correlations. Squared observed-series/factor correlation is labelled an association measure, not a likelihood variance decomposition. M2 inclusion in factor and bridge is a deliberately diagnosed redundancy experiment.

FDI bridge performance and combined M2/FDI deltas can be examined in the diagnostic table, including 120-day sensitivity and an extra quarterly lag. Whether FDI genuinely improves either bridge or factor remains unestablished; no monthly FDI factor model was fitted. No valid real-time FDI common sample exists, so apparent diagnostic improvements do not answer the promotion question.



## Current quarter



Unchanged 2026Q3 Phase 6E DFM 8.301152885%; U-MIDAS 8.060649796%; COMBO_50_50 8.180901341%.

M1: 8.371307849% (research challenger).

M2: 8.413700639% (research challenger).

B1: 8.355731413% (research challenger).

B2: 8.378356810% (research challenger).

FDI current estimates unavailable at the frozen cutoff. Exact additive bridge contributions are coefficient × design value in the coefficient output; historical FDI contributions are diagnostics only.



Reproduce: `.venv/Scripts/python.exe -m scripts.phase6f.experiment`. The archived workbook is reused; no refresh or production/dashboard writer is invoked. Protected artifacts are hashed before and after. Tests and deterministic rerun evidence are recorded separately.



Next required evidence: recover dated official BOP and M2 historical releases, attach observation-level value vintages, and repeat the same controlled comparisons before Phase 6G review.




## Explicit empirical answers


M1: common-sample pooled RMSE 0.620965; improvement 0.057477 pp; strongest relative horizon H2. At least 0.05 pp economically relevant diagnostic improvement.

M2: common-sample pooled RMSE 0.613137; improvement 0.065306 pp; strongest relative horizon H3. At least 0.05 pp economically relevant diagnostic improvement.

B1: common-sample pooled RMSE 0.650300; improvement 0.028143 pp; strongest relative horizon H1. Below 0.03 pp or worse than benchmark.

B2: common-sample pooled RMSE 0.625105; improvement 0.053338 pp; strongest relative horizon H1. At least 0.05 pp economically relevant diagnostic improvement.

B3: common-sample pooled RMSE 0.595616; improvement 0.082826 pp; strongest relative horizon H3. At least 0.05 pp economically relevant diagnostic improvement.

B3_120D: common-sample pooled RMSE 0.653757; improvement 0.024686 pp; strongest relative horizon H1. Below 0.03 pp or worse than benchmark.

B4: common-sample pooled RMSE 0.941508; improvement -0.263066 pp; strongest relative horizon H3. Below 0.03 pp or worse than benchmark.

B5: common-sample pooled RMSE 0.561831; improvement 0.116612 pp; strongest relative horizon H3. At least 0.05 pp economically relevant diagnostic improvement.

B5_120D: common-sample pooled RMSE 0.644490; improvement 0.033953 pp; strongest relative horizon H1. At least 0.03 pp potentially meaningful diagnostic improvement.

M1 leave-one-quarter-out RMSE deltas range -0.067042 to -0.044351; improvement survives every exclusion: True.

M2 leave-one-quarter-out RMSE deltas range -0.080290 to -0.045984; improvement survives every exclusion: True.

Both lagged M2 factor specifications improve this revised-history holdout comparison, but no genuine historical value-vintage improvement is established. B1/B2 assess redundancy separately; VIF and coefficient stability are in diagnostic files.

FDI gains do not survive as equally strong gains under the longer 120-day assumption. The additional-quarter specification worsens performance. This sensitivity and missing historical value vintages make FDI evidence inconclusive. Full diagnostic samples and common diagnostic samples each contain 12 forecasts; the valid vintage-real-time FDI sample contains zero forecasts.

No promotion is recommended. The production dashboard and 50/50 configuration remain unchanged.

## Completed validation and diagnostic interpretation

M0 also serves as B0, the unchanged benchmark bridge. Current B1 VIF 41.74 versus M0 1.15: explicitly adding M2 while retaining M2 in factor extraction creates substantial redundancy. Current B2 VIF 7.83. Do not automatically retain the duplicate M2 channel. M1 and M2 factors correlate 0.9642 and 0.9068 with M0; current M2 loadings are 0.5198, 0.5281, 0.5407. Factor/GDP-AR slopes remain positive in M0/M1/M2. Explicit bridge M2 makes the factor slope change sign, consistent with the VIF warning. Historical B5 has much lower collinearity than B3, but its FDI improvement still lacks verified historical value vintages.

The complete requested relevant suite executed 134 tests. Its one Phase 6F test initially failed because pandas inferred a timestamp format without fractional seconds. That parser was corrected; all 11 Phase 6F tests then passed without skips. Unresolved failures: 0. Windows sandbox temporary-directory errors were resolved by running the offline suite outside the sandbox. Independent reruns matched all 16 numerical CSV checksums exactly. All 609 protected artifact hashes remain unchanged. XML and JSON evidence are in this folder.

PHASE6F_INCONCLUSIVE

KEEP_PHASE6E_PRODUCTION
