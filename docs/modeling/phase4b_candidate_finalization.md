# Phase 4B — Candidate model finalization before holdout

Phase 4B was run against the frozen V1.2 masters and stops at the candidate
freeze. The development endpoint is **2025Q2**. The reserved quarters remain
2025Q3, 2025Q4, 2026Q1, and 2026Q2.

> **FROZEN VALIDATION OUTCOMES HAVE NOT BEEN USED**

The Phase 4B loader first reads only the quarterly labels, validates them
against `results/frozen_validation_definition.json`, and then reads
`gdp_real_yoy_pct` with an explicit Parquet filter containing only the 30
development quarters. No frozen-quarter target value is materialized by the
candidate-finalization process.

## 1. Phase 4A.1 findings

Phase 4A.1 provided 18 expanding-window development targets from 2021Q1
through 2025Q2. It established three findings that determine Phase 4B:

- AR(2) materially outperformed AR(1) on the complete 18-quarter development
  sample.
- `umidas_usd_uzs_mom_dlog` was the strongest sufficiently sized monthly
  candidate at H3 under the standard release assumption, with 14 matched
  forecasts after the 15-row effective-training safeguard.
- The approximate DFM result was not decision-ready. Its factor panel inherited
  the 1960 union-panel start, reported 82%–96% missing cells, silently omitted
  configured fields, and almost always stopped at the old 20-iteration cap.

Recent construction, CPI, trade, and gold-export bridge/MIDAS results with only
about six forecasts remain appendix diagnostics. Phase 4B requires at least 12
matched development forecasts for primary candidacy and did not promote any of
them.

## 2. AR(2) is a primary benchmark

On all 18 development forecasts, invariant across horizons and lag modes:

| Model | N | RMSE | MAE | Bias | RMSE / AR(1) |
| --- | ---: | ---: | ---: | ---: | ---: |
| AR(1) | 18 | 1.4042 | 0.9199 | 0.5273 | 1.0000 |
| AR(2) | 18 | 0.8908 | 0.7224 | 0.3377 | 0.6343 |

AR(2) reduces RMSE by 36.6% relative to AR(1). Every Phase 4B challenger is
therefore compared on identical valid quarters against both AR(1) and AR(2).

## 3. Frozen USD/UZS MIDAS candidate

The primary monthly candidate is frozen as
`umidas_usd_uzs_mom_dlog`: three monthly lags, one quarterly GDP lag,
unrestricted monthly coefficients, H1/H2/H3, and both standard and
conservative release-lag assumptions. No lag length or polynomial restriction
was selected using validation data.

| Horizon | Lag mode | N | RMSE | MAE | Bias | RMSE / matched AR(2) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| H1 | standard | 14 | 1.2542 | 0.7524 | -0.1676 | 1.4538 |
| H2 | standard | 14 | 0.9755 | 0.6606 | 0.0290 | 1.1307 |
| H3 | standard | 14 | 0.6764 | 0.4808 | -0.0946 | 0.7841 |
| H1 | conservative | 14 | 0.8663 | 0.6059 | 0.1734 | 1.0042 |
| H2 | conservative | 14 | 1.2542 | 0.7524 | -0.1676 | 1.4538 |
| H3 | conservative | 14 | 0.9755 | 0.6606 | 0.0290 | 1.1307 |

Predictions change at every H1→H2 and H2→H3 comparison. The Almon version is
retained only as `secondary_robustness`; its H3 RMSE is 1.2611 standard and
1.2032 conservative on 17 forecasts.

## 4. DFM input-window diagnosis and repair

The prior `training_slice` admitted every month before the last training
quarter. Because the union monthly master begins with gold prices in 1960, EM
received decades with nearly all domestic series missing even though GDP begins
in 2018.

The corrected rule is exact: each fit begins at the first month of its earliest
GDP training quarter and ends at the final month of its latest GDP training
quarter. Every Phase 4B fit starts at **2018-01-31**. Window length expands from
36 to 87 months across origins; no 1960 observation enters factor estimation.

After repair, maximum missing-cell fractions are 0.5% for Tier A, 29.9% for
Tier B, and 42.3% for Tier C, versus as much as 95.9% before repair. Each fit
records first/last month, month count, variable count, total/observed/missing
cells, and missing fraction in `phase4b_dfm_diagnostics`.

## 5. DFM field-resolution diagnosis

The omissions were naming bugs in the old hard-coded DFM field list:

- `gold_price_yoy_log` was requested, but the registry/master field is
  `gold_price_mom_dlog`;
- `electricity_gas_yoy_log`, `retail_trade_yoy_log`, and
  `wholesale_trade_yoy_log` were requested, while the registry fields are
  `utilities_yoy_log`, `retail_yoy_log`, and `wholesale_yoy_log`.

Consequently, old Tier A omitted gold; Tier B used 8 rather than 12 configured
variables; Tier C used 16 rather than 20. Phase 4B constructs each tier from
the registry-resolved fields instead of a second hard-coded naming layer.

Every configured field now receives one of `included`, `unavailable`, or
`excluded`, with an explicit reason. A field needs at least 12 observed months
inside the current GDP window and non-zero variance. Early-start fits therefore
exclude later-starting activity/trade variables as
`insufficient_in_window_coverage`; they enter automatically after reaching 12
observations. No field is silently dropped. The 4,104-row report is
`results/phase4b_dfm_field_resolution.parquet` (and CSV).

## 6. EM-PCA convergence

EM now reports `converged`, iteration count, maximum iterations, full
reconstruction-loss path, final loss, relative loss change, and tolerance.
Reaching the iteration cap is explicitly `converged = False`.

A development-only sensitivity check crossed tolerances 1e-4, 1e-5, and 1e-6
with all tiers, horizons, lag modes, and the first/middle/last origins. The
representative Tier B/C fits converged 18/18 at 1e-4. Tighter settings frequently
hit 100 iterations while producing essentially unchanged median reconstruction
loss. Phase 4B therefore freezes:

- maximum iterations: 100;
- relative-loss tolerance: **1e-4**;
- iteration cap is not convergence.

Across all 108 fits per tier, convergence rates are 100.0% (A), 99.1% (B), and
85.2% (C). Median successive-loading cosine stability is 0.999, 0.994, and
0.982 respectively. Remaining non-convergence is visible, not reclassified.

## 7. Corrected approximate DFM performance

Only one-factor Tier A/B/C specifications were rerun. The unstable two-factor
model is not a production candidate.

| Model | H3 lag mode | N | RMSE | RMSE / matched AR(1) | RMSE / matched AR(2) |
| --- | --- | ---: | ---: | ---: | ---: |
| Tier A, 1 factor | standard | 17 | 1.3482 | 1.1058 | 1.4803 |
| Tier A, 1 factor | conservative | 17 | 1.2713 | 1.0426 | 1.3958 |
| Tier B, 1 factor | standard | 17 | 1.2147 | 0.9962 | 1.3337 |
| Tier B, 1 factor | conservative | 17 | 1.2155 | 0.9969 | 1.3345 |
| Tier C, 1 factor | standard | 17 | 1.2340 | 1.0121 | 1.3549 |
| Tier C, 1 factor | conservative | 17 | 1.2942 | 1.0614 | 1.4209 |

The factors update between horizons and loadings are stable, but even the best
Tier B result is roughly 33% worse than matched AR(2) at H3. No corrected DFM
passes the pre-specified accuracy gate (H3 relative RMSE to AR(2) no greater
than 1.05 under both lag modes).

## 8. Kalman/state-space DFM decision

A full Kalman DFM is deferred. The corrected approximate factors now have a
valid window, explicit variables, good loading stability, and mostly reasonable
convergence. Their development forecast accuracy nevertheless remains clearly
inferior to AR(2), and Tier B/C still contain some iteration-cap fits. Added
state-space complexity is not justified before the holdout.

## 9. Fixed 50/50 ensemble

`ensemble_ar2_umidas_usd` is exactly 0.5 × AR(2) + 0.5 × USD U-MIDAS wherever
the MIDAS prediction exists. The function exposes no tunable weight argument.

| Horizon | Lag mode | N | RMSE | MAE | Bias | Component-error correlation |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| H1 | standard | 14 | 0.7629 | 0.5184 | 0.1552 | 0.0960 |
| H2 | standard | 14 | 0.7533 | 0.5841 | 0.2536 | 0.3903 |
| H3 | standard | 14 | 0.5828 | 0.4674 | 0.1918 | 0.2569 |
| H1 | conservative | 14 | 0.7622 | 0.6365 | 0.3258 | 0.5441 |
| H2 | conservative | 14 | 0.7629 | 0.5184 | 0.1552 | 0.0960 |
| H3 | conservative | 14 | 0.7533 | 0.5841 | 0.2536 | 0.3903 |

At H3 the ensemble RMSE is 0.6755 of matched AR(2) under standard lags and
0.8732 under conservative lags. Quarter-level component and ensemble
predictions are in `phase4b_ensemble_diagnostics`; these results did not alter
the 50/50 weight.

## 10. Final frozen candidate set

The architectures entering final validation are:

1. `ar1`;
2. `ar2`;
3. `umidas_usd_uzs_mom_dlog` with three monthly lags and one GDP lag;
4. `ensemble_ar2_umidas_usd` with fixed weights 0.5/0.5.

Historical mean remains a benchmark. `almon_usd_uzs_mom_dlog` remains a
secondary robustness comparison. Tier A/B/C one-factor DFMs remain diagnostics
and no two-factor or Kalman DFM enters the frozen set. No model may be added or
respecified after validation outcomes are opened.

The authoritative freeze is `results/phase4b_candidate_freeze.json`; it records
equations, predictors, lags, weights, DFM settings, release assumptions,
preprocessing, master hashes, development endpoint, and holdout labels.

## 11. Outputs and holdout status

Machine-readable Phase 4B outputs include:

- `results/phase4b_development_metrics.csv` and `.parquet`;
- `results/phase4b_predictions.csv` and `.parquet`;
- `results/phase4b_horizon_updates.csv` and `.parquet`;
- `results/phase4b_ensemble_diagnostics.csv` and `.parquet`;
- `results/phase4b_dfm_diagnostics.csv` and `.parquet`;
- `results/phase4b_dfm_field_resolution.csv` and `.parquet`;
- `results/phase4b_dfm_factor_loadings.csv` and `.parquet`;
- `results/phase4b_dfm_tolerance_sensitivity.csv` and `.parquet`;
- `results/phase4b_dfm_decision.json`;
- `results/phase4b_candidate_freeze.json`.

The maximum target quarter in Phase 4B predictions is 2025Q2. There are no
prediction or metric rows for 2025Q3, 2025Q4, 2026Q1, or 2026Q2.

> **FROZEN VALIDATION OUTCOMES HAVE NOT BEEN USED**

