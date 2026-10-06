# Phase 6G.2 research results



PHASE6G2_NO_IMPROVEMENT



Primary comparison: identical common start and global intersection of successful forecast origins across all six models in BOTH sample regimes. Errors and bias are actual minus forecast; OOS R² is 1 − SSE_model/SSE_M0.



| Model | M2 transform | Economic lag | H1 RMSE | H2 RMSE | H3 RMSE | Pooled RMSE | OOS R² | 2026Q3 |

|---|---|---:|---:|---:|---:|---:|---:|---:|

| M0 | YoY log | 0 | 0.415646 | 0.411440 | 0.416489 | 0.414531 | 0.000000 | 8.315353 |

| M1 | YoY log | 1 | 0.429024 | 0.416992 | 0.414047 | 0.420071 | -0.026908 | 8.370595 |

| M2 | YoY log | 2 | 0.468407 | 0.439950 | 0.433727 | 0.447616 | -0.165996 | 8.413701 |

| Q0 | 3-month log | 0 | 0.642148 | 0.632873 | 1.345868 | 0.935279 | -4.090595 | 8.194775 |

| Q1 | 3-month log | 1 | 0.632771 | 0.624178 | 1.341484 | 0.929081 | -4.023351 | 8.194402 |

| Q2 | 3-month log | 2 | 0.635935 | 0.626584 | 1.338538 | 0.928925 | -4.021662 | 8.193876 |



## Implementation audit



M2 source: https://cbu.uz/sdmx/public/DCS_Uzbekistan_Online.xlsx. Monthly end-of-period stock, billion UZS, end of period. Code and 92 matched months verify 100 × ln(M2_t/M2_t−12); maximum reconstruction difference 0.

The publication assumption is 25 days; it is separate from economic lag. Order: transformation -> source release mask -> economic lag -> balanced start -> training-only standardization. Standardization uses the pre-target-quarter mean and sample standard deviation only. No filling, annualization or quarterly collapse occurs.

Accepted kernels are reused: eight predictors, one DynamicFactorMQ factor, AR(2), no idiosyncratic AR(1), EM maxiter 500/tolerance 1e−5, missing-data M step, likelihood-decrease revert, filtered factors, quarterly mean bridge with intercept and GDP(q−1). GDP publication/vintage gating and target actuals remain unchanged.



## A–C. Transformation, economic lag and samples



First raw M2 month: 2013-01-31 00:00:00; first YoY month: 2014-01-31 00:00:00; first 3-month month: 2013-04-30 00:00:00. The accepted specification keeps the January 2019 earliest start. Economic lags are applied after the release mask, including its initial boundary, exactly as Phase 6F. Natural balanced starts may therefore differ; common starts use the latest of all six starts per origin. Full starts and training counts are in sample_comparison.csv.

Natural best: M0; common best: M0. Primary common forecast count per model: 30. Best 3-month model: Q2; pooled improvement versus common M0: -0.514394 pp. Natural and common results are both reported, never blended.

Best YoY model is M0; best 3-month improvement versus best YoY: -0.514394 pp.



## D. Factor behavior



Q0: median factor correlation with M0 0.702496; current M2 loading 0.056579; current factor/M2 correlation 0.091839. Signs are aligned to M0 for comparisons; no forecast changes from alignment.

Q1: median factor correlation with M0 0.708201; current M2 loading 0.051074; current factor/M2 correlation 0.059852. Signs are aligned to M0 for comparisons; no forecast changes from alignment.

Q2: median factor correlation with M0 0.632875; current M2 loading 0.075143; current factor/M2 correlation 0.092878. Signs are aligned to M0 for comparisons; no forecast changes from alignment.



## E–G. FDI audit and bridge sensitivity



FDI_TRANSFORMATION_USED = FDI_million_USD / 1000 (nominal levels; linear scaling). Exact parser selects the CBU BOP Dataset row “Direct investment: liabilities”, quarterly net incurrence of liabilities, million USD. No ln, log1p, asinh or statistical standardization was used in Phase 6F. FDI only enters quarterly bridges.

B3 = M0 factor + GDP(q−1) + economic-L1 M2 quarter mean + latest release-gated FDI/1000. B4 adds one exact reference-quarter FDI lag. B5 = M1 factor + GDP(q−1) + latest gated FDI/1000, without separate M2. Evidence: scripts/phase6f/experiment.py:96–156 and 254–260. Full repository text evidence is preserved in fdi_repository_evidence.csv.

Q2 bridge challengers compare levels with asinh(FDI_million_USD), with no separate M2 bridge regressor. Both use identical factor histories and GDP gating. The inherited bridge helper’s /1000 scaling is cancelled for asinh inputs. Ordinary ln is optional and was not fitted; zero/negative counts are in fdi_transformation_audit.csv.

FDI sensitivities use assumed quarter-end +90/+120 days at the same H stage in training. They are revised-history diagnostics, NOT vintage-real-time. Source release dates remain unknown. The FDI snapshot was retrieved after the frozen current production cutoff, so Q2_FDI_ASINH current estimates are unavailable. No post-cutoff value is injected.

Q2_FDI_ASINH: N=42, RMSE=0.930502, MAE=0.677882, bias=0.538987.

Q2_FDI_ASINH_120D: N=42, RMSE=0.949457, MAE=0.721999, bias=0.555614.

Q2_FDI_LEVELS: N=42, RMSE=0.946476, MAE=0.695661, bias=0.483619.

Q2_FDI_LEVELS_120D: N=42, RMSE=0.970140, MAE=0.760888, bias=0.495155.



## H. Leave-one-quarter-out sensitivity



Q2 improves common M0 after every quarter exclusion: False. RMSE delta range 0.216443 to 0.574064. This removes a scoring quarter; it does not refit a cross-validation model. All model/exclusion results are in leave_one_quarter_out.csv.



## Explicit answers



1. Best 3-month versus YoY M0 improvement: -0.514394 pp; versus corresponding YoY: -0.481309 pp.

2. Identical common-sample best is M0; compare natural results in model_comparison.csv.

3. Best common M2 lag is 0 months (M0).

4. Factor correlations and loading differences above quantify the effect; loadings are descriptive associations, not causal contributions.

5. Horizon-specific differences versus M0: H1: 0.220289 pp; H2: 0.215144 pp; H3: 0.922049 pp.

6. FDI was not logarithmized; it used linearly scaled levels.

7–8. See identical-origin FDI metrics below; robustness across 90/120 days is required and revised-history results cannot establish vintage-real-time gains.

9. No challenger is promoted. Missing historical M2/FDI value vintages, retrospective specification testing and a small quarter sample preclude production-readiness.



## Volatility and current forecasts



m2_diagnostics.csv reports mean, sample standard deviation, extrema, calendar autocorrelations at 1/3/12, YoY/3-month correlation and >3 SD flags. No flagged observation is removed.

Unchanged production DFM 8.301152885%; U-MIDAS 8.060649796%; COMBO_50_50 8.180901341%. Research forecasts and differences versus production DFM are in current_nowcasts.csv.



Reproduce: `.venv/Scripts/python.exe -m scripts.phase6g2.run`; test: `.venv/Scripts/python.exe -m scripts.phase6g2.tests`. Only the new scripts/phase6g2 and results/phase6g2 areas are authored. Protected production, earlier research, processed/master data and dashboard bytes are verified before and after.

ASINH minus levels RMSE (90 days): -0.015973 pp; improvement: True.

ASINH minus levels RMSE (120 days): -0.020683 pp; improvement: True.

## Convergence and fair-origin exclusions


30 failed fits across sample regimes (including optional bridge failures). These are explicitly recorded in failures.csv; no failed fit is used as a forecast. All estimators keep the accepted convergence settings.

All six models and both regimes share 30 scored origins. Natural/common RMSE differences therefore reflect estimation history, rather than different realized forecast-origin selections.

The strict cross-regime intersection excludes all 2025Q3–2026Q2 holdout origins because natural Q0/Q1 do not converge. Consequently the headline metrics are retrospective development-period diagnostics, with ZERO complete recent holdout origins. No holdout performance claim is justified by that table.

Supplementary within_regime_horizon_metrics.csv uses a separate six-model intersection for each sample regime, preserving the additional successful COMMON-sample holdout fits; these supplemental scores cannot be used for a matched natural-versus-common comparison.

Supplementary COMMON origin count: 39; pooled RMSEs: {'M0': 0.5083526703903103, 'M1': 0.497054440012132, 'M2': 0.5130972203120556, 'Q0': 0.97807934754432, 'Q1': 0.986148027701558, 'Q2': 0.9727334053142404}

Supplementary NATURAL origin count: 30; pooled RMSEs: {'M0': 0.40257929877216325, 'M1': 0.41465911040398185, 'M2': 0.4476159319138699, 'Q0': 0.9238321936953794, 'Q1': 0.9323166556485305, 'Q2': 0.9289251943015971}

COMMON Q0: 3 failures.

COMMON Q1: 3 failures.

COMMON Q2: 2 failures.

NATURAL Q0: 12 failures.

NATURAL Q1: 8 failures.

NATURAL Q2: 2 failures.

Origins removed from BOTH regimes: [{'target_quarter': '2022Q3', 'horizon': 'H2'}, {'target_quarter': '2022Q3', 'horizon': 'H3'}, {'target_quarter': '2025Q3', 'horizon': 'H1'}, {'target_quarter': '2025Q3', 'horizon': 'H2'}, {'target_quarter': '2025Q3', 'horizon': 'H3'}, {'target_quarter': '2025Q4', 'horizon': 'H1'}, {'target_quarter': '2025Q4', 'horizon': 'H2'}, {'target_quarter': '2025Q4', 'horizon': 'H3'}, {'target_quarter': '2026Q1', 'horizon': 'H1'}, {'target_quarter': '2026Q1', 'horizon': 'H2'}, {'target_quarter': '2026Q1', 'horizon': 'H3'}, {'target_quarter': '2026Q2', 'horizon': 'H1'}, {'target_quarter': '2026Q2', 'horizon': 'H2'}, {'target_quarter': '2026Q2', 'horizon': 'H3'}]

On the exact 42 FDI challenger origins, Q2 without FDI has RMSE 0.954501.

Q2_FDI_ASINH: RMSE difference versus identical-origin Q2 without FDI -0.023998 pp. Improvement versus the base Q2 bridge: True.

Q2_FDI_ASINH_120D: RMSE difference versus identical-origin Q2 without FDI -0.005043 pp. Improvement versus the base Q2 bridge: True.

Q2_FDI_LEVELS: RMSE difference versus identical-origin Q2 without FDI -0.008025 pp. Improvement versus the base Q2 bridge: True.

Q2_FDI_LEVELS_120D: RMSE difference versus identical-origin Q2 without FDI 0.015639 pp. Improvement versus the base Q2 bridge: False.

Q2_FDI_ASINH: improvement versus Q2 survives every quarter exclusion: False.

Q2_FDI_ASINH_120D: improvement versus Q2 survives every quarter exclusion: False.

Q2_FDI_LEVELS: improvement versus Q2 survives every quarter exclusion: False.

Q2_FDI_LEVELS_120D: improvement versus Q2 survives every quarter exclusion: False.

Small FDI gains relative to the weak Q2 bridge do not rescue the three-month transformation relative to YoY M2. The longer release lag attenuates the gain, and revised-history FDI evidence remains insufficient for promotion.
