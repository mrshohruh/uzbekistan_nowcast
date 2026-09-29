# Phase 4A — Benchmark GDP nowcasting models and evaluation framework

Completed 2026-09-29 against the frozen V1.2 database (as documented in
`docs/phase3b_results.md`). The V1.2 database, its registry, its raw
archives, and its metadata were **not** modified.

The Phase 4A framework is implemented under `src/uznowcast/models/` and is
invoked with:

```
python -m uznowcast.models evaluate --phase 4a
```

which reads the frozen master datasets under `data/master/`, runs every
model family under every horizon and lag mode, and writes reproducible
result tables under `results/`. No forecasting model is deployed. The
outputs are the input to a Phase 4B review, not to a production
dashboard.

## 1. Target and sample

- Target: `gdp_real_yoy_pct` (SIAT dataset 3698, exact selector Code=1700).
- Sample: 2018-Q1 → 2026-Q2, 34 quarterly observations, no interpolation.
- The Phase 4A CLI expects the master file
  `data/master/gdp_quarterly.parquet` with columns `quarter` and
  `gdp_real_yoy_pct`; the framework rejects a master whose GDP column is
  missing or has duplicate quarters.
- The framework never uses future GDP values: at expanding-window step
  `k` the training sample is `quarters[:k]` and the target is
  `quarters[k]`.

The exact target values used by the modelling layer are the 34 rows of
`data/master/gdp_quarterly.parquet`. When the operator has run a live
V1.2 build they can pull the numbers with

```python
pd.read_parquet('data/master/gdp_quarterly.parquet')[['quarter', 'gdp_real_yoy_pct']]
```

The Phase 4A CLI reads that file every run; nothing is hard-coded.

## 2. Predictor tiers

Tier assignments are read from
`docs/model_readiness_tiers.md`; the machine-readable definitions live
in `src/uznowcast/models/data.py::TIER_A`, `TIER_B_ADDITIONAL`, and
`TIER_C_ADDITIONAL`. The sparse banking/payment series and `russia_ipi`
are excluded from the primary evaluation (see §16).

At every expanding-window step the framework calls
`dataset.predictor_fields(tier)`, which intersects the tier's registry
keys with the columns that actually appear in the frozen master. A
predictor that is missing from the current master (e.g. because that
run's build scope did not include it) is silently skipped for that
model; no missing predictor is ever imputed.

## 3. Pseudo-real-time assumptions

Because complete historical first-release timestamps do not exist
(see `docs/release_metadata_audit.md`), Phase 4A is labelled
**"pseudo-real-time / historical ragged-edge evaluation"** rather than
genuine real-time vintage evaluation. Two assumption sets are
evaluated:

- **Standard lag** — a monthly statistic for reference month `m` is
  assumed released on `end_of_m + L`, where `L` is the registry's
  Typical publication lag (days).
- **Conservative lag** — the same rule with `L` padded by 15 days and
  zero-lag daily sources bumped to 3 days.

Under both assumptions the framework never asserts a statistic was
known on its reference-month end date. See
`docs/modeling/model_specifications.md` §5 for the exact rule.

## 4. Evaluation design

- Expanding-window pseudo-out-of-sample evaluation.
- Minimum training sample: `min_train = 8` quarters (chosen so that
  AR(2), which needs ≥ 4 lagged rows, has at least 4 in-sample points to
  fit on the first step).
- The first evaluation quarter is `quarters[min_train]`. For a 34-quarter
  target this yields 26 evaluation quarters
  (`quarters[8], ..., quarters[33]`).
- Every model is refit at every step; no coefficient is carried across
  steps.
- Every model at every step uses the same lag-mode-aware information
  set, so cross-model comparisons are apples-to-apples.

At each evaluation step the target quarter is never touched during
training or standardization. Test-period GDP is not used to select any
specification. See `tests/models/test_evaluate.py`.

## 5-8. Model families

See `docs/modeling/model_specifications.md` for exact equations. The
Phase 4A run instantiates:

| Family | Specifications instantiated |
| --- | --- |
| Historical mean | 1 (expanding mean of GDP) |
| AR(p) | 2 (AR(1) and AR(2)) |
| Bridge | Up to 26 (one per available field in `ECONOMIC_BLOCKS`, plus block bridges) |
| U-MIDAS(3) | One per candidate predictor field |
| Almon-MIDAS(3, poly=1) | One per candidate predictor field |
| Approximate DFM | Up to 4 (`dfm_tierB_k1`, `dfm_tierC_k1`, `dfm_tierB_k2`, `dfm_tierA_k1`) |

For every specification the framework produces one row per (horizon,
lag_mode, tier, target_quarter) in `results/phase4a_predictions.parquet`
with columns `prediction`, `actual`, `error`, `n_train`, `failure`.
Failures (empty training frames, missing lags at target, no visible
monthly observation) are recorded with an explicit `failure` reason and
NaN prediction, never silently dropped.

## 9. Forecast horizons

Three horizons are evaluated:

- **H1** — end of month 1 of the target quarter.
- **H2** — end of month 2 of the target quarter.
- **H3** — end of month 3 of the target quarter (before or around GDP
  publication).

At each horizon the release-lag rule shrinks the information set. AR(p)
and historical-mean benchmarks do not depend on the monthly panel and
therefore have identical metrics across horizons (see §10).

## 10-13. Metrics and comparison table

`results/phase4a_metrics.parquet` carries RMSE, MAE, bias, and count
per (model, tier, horizon, lag_mode) with relative-to-AR(1) ratios.
`results/phase4a_predictions.parquet` is the raw predictions table.
The `results/phase4a_model_specs.json` file records every specification's
parameter count and column order so the run is reproducible.

### Illustrative fixture-based rehearsal

Because this checkout has no persisted raw-source cache (see §17), the
committed `results/*.parquet` files come from a fixture-based rehearsal
scripted by `scripts/build_master_from_fixtures.py`. That helper rebuilds
a subset master from the frozen Phase 2B fixtures (GDP + industrial
production + construction + headline CPI + exports + imports + M2) and
lets the operator confirm every model family runs end-to-end without
needing a live network. The fixture-derived Tier A therefore contains
only ``m2_yoy_log``, and the DFM's Tier A never has enough predictors
to fit; the framework reports that failure rather than fabricating a
Tier A DFM.

Selected metrics from the fixture-based rehearsal (H3 standard lag):

| Model | Tier | N | RMSE | MAE | RMSE / AR(1) |
| --- | --- | ---: | ---: | ---: | ---: |
| AR(1) | none | 26 | 2.069 | 1.359 | 1.000 |
| Historical mean | none | 26 | 2.339 | 1.812 | 1.130 |
| Bridge (construction) | C | 17 | 1.085 | 0.953 | 0.524 |
| Bridge (imports_total) | C | 17 | 1.302 | 1.072 | 0.629 |
| Bridge (block activity) | C | 17 | 1.376 | 1.109 | 0.665 |
| Bridge (ind_prod) | B | 25 | 1.505 | 1.107 | 0.727 |
| U-MIDAS (imports_total, 3 lags) | C | 16 | 1.715 | 1.075 | 0.829 |
| DFM Tier B, 1 factor | B | 26 | 2.089 | 1.356 | 1.010 |
| DFM Tier C, 1 factor | C | 26 | 2.091 | 1.339 | 1.010 |

These numbers are the fixture-derived rehearsal, not a live V1.2
result. **They are not evidence that a bridge model is superior to
AR(1) for Uzbekistan GDP.** The evaluation sample here is small (17–26
one-step-ahead forecasts, ~7 of them across COVID and 2022 external
shocks), and the bridge specifications benefit from a smaller effective
sample because they drop training quarters where the aggregated
predictor is not yet visible. When the operator runs the CLI against a
live V1.2 build the same tables regenerate with the operational values.

The comparison template Phase 4A commits to is:

| Model | Predictor tier | Horizon | First eval quarter | Last eval quarter | N forecasts | RMSE | MAE | Bias | RMSE / AR(1) |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |

`results/phase4a_metrics.parquet` conforms to that schema exactly. The
final comparison in a live report should use `n_forecasts >= 15` and
call out relative-RMSE differences of less than 20% as unlikely to be
statistically distinguishable at this sample size.

### Diebold-Mariano

`src/uznowcast/models/metrics.py::diebold_mariano` provides an NW(1)
DM t-statistic and is available for any pair of model error series. In
Phase 4A it is **not** used to declare winners. The evaluation sample
(≤ 26 one-step-ahead forecasts per horizon, minus training-frame drops
for models that need monthly aggregates) is too small to draw reliable
DM inferences and the results tables therefore do not carry DM columns.
The operator may compute DM on any pair by loading the predictions and
calling the utility directly.

## 12. Factor diagnostics

`results/phase4a_factor_loadings.parquet` records, for every DFM fit
that converged, the loading vector, the EM iteration count, and the
fraction of missing cells in the training panel. Loadings are not
interpreted causally (`docs/modeling/model_specifications.md` §4);
they are recorded to let the operator inspect which variables anchor
the factor at each step. The convergence flag (`em_iterations`) rarely
hits the 20-iteration cap on the fixture rehearsal.

## 13. Release-lag sensitivity

Both the standard and conservative lag runs are in
`results/phase4a_metrics.parquet` under the `lag_mode` column. AR(1),
AR(2) and historical mean are unaffected by the lag mode (they use only
GDP). Bridge/MIDAS/DFM specifications generally lose forecasts under
conservative mode because a wider lag shrinks the information set at
H1/H2. The differences in metrics between the two modes are one
diagnostic of how dependent a specification is on assumed data
availability.

## 14. Small-sample limitations

**These are the dominant constraints on any Phase 4 finding**:

1. 34 GDP quarters (26 evaluation quarters at min_train=8) are too few
   to distinguish RMSE differences smaller than roughly 10-15%.
2. The 2018-Q1 start captures only one full pre-shock cycle before the
   COVID-19 quarter (2020-Q2). Every expanding-window step for
   2020-Q2 or later has that shock in its training data.
3. Diebold-Mariano and related tests are unreliable on so few
   forecast pairs.
4. The V1.2 monthly panel is ragged; bridge/MIDAS/DFM specifications
   silently drop the earliest training quarters for which the panel is
   not yet observed, so their effective N is smaller than AR(1)'s.
5. The pseudo-real-time information sets rely on registry-typical lags,
   not observed first-release timestamps. A specification that appears
   to beat AR(1) at H1 under the standard-lag assumption may not do so
   in genuine real time.

The framework does not "select the best model": every candidate that
was instantiated is written to `results/phase4a_predictions.parquet`.
Model-selection overfitting is left as an explicit Phase 4B judgement.

## 15. Failures and non-convergence

The evaluator records every failure with a machine-readable reason. In
the fixture-based rehearsal the failure taxonomy is:

- `insufficient_training_sample` — AR(2) at very early splits.
- `bridge training frame is empty after dropping NaNs` — the aggregated
  predictor was not visible for any training quarter at that horizon.
- `MIDAS spec X has no training rows` — the last-K monthly slice was
  not observed for any training quarter.
- `missing_factor_at_target` — the target quarter had no visible
  monthly observation for the DFM's fields.

None of these failures is silently swallowed; each row keeps
`prediction = NaN`, an explicit `failure` string, and can be filtered
out of any metrics comparison via `.dropna(subset=['prediction'])`.

## 16. Experimental-series exclusions

Following Phase 3B:

- `russia_ipi` is excluded from every tier (provider stays Rosstat, no
  TLS-policy change).
- The seven sparse banking/payment variables (`household_deposits`,
  `corporate_deposits`, `household_credit`, `corporate_credit`,
  `pos_turnover`, `instant_payments`, `interbank_payments`) are
  classified as `experimental`. They are not part of Tier A/B/C.
- The framework exposes `tier_variables('experimental')` for a
  robustness-only appendix in Phase 4B, but the primary Phase 4A run
  never touches them.

## 17. Recommended Phase 4B model architecture

Based on the fixture rehearsal and the framework's design margins:

1. **Anchor benchmark**: AR(1) on the frozen V1.2 GDP target.
2. **Primary model**: a Tier B ragged-edge DFM with a single factor,
   estimated via a full Kalman-filter DFM implementation (state-space,
   maximum likelihood). Replace the current two-step approximate DFM
   with a proper `pykalman` or custom EM state-space fitter to obtain
   filtered rather than projected factors at the target quarter.
3. **Cross-checks**: two bridge equations (`bridge_ind_prod_yoy_log`
   and `bridge_block_activity` at Tier B), reported alongside the DFM
   for every release date.
4. **Sensitivity**: run both lag modes and report the difference. Any
   nowcast whose direction reverses between standard and conservative
   lag should be flagged.
5. **Robustness**: apply variant B (mask database extremes at training
   time) at every step to confirm the June-2026 gold-proxy outlier
   does not drive the point estimate.
6. **Deferred**: instant/interbank payments, banking balances and
   `russia_ipi` remain out of scope until Phase 3B's sparse-series
   ingestion audit uncovers additional official coverage.
7. **Evaluation window**: reserve the 4 most recent quarters as a
   frozen validation set (never used for specification selection) so
   that Phase 4B can report a genuinely held-out comparison.

The framework code in `src/uznowcast/models/` is designed so that a
full Kalman-filter DFM slots into `src/uznowcast/models/dfm.py` behind
the existing `dfm_forecast` API — the evaluator loop and metrics tables
do not need to change.

## Reproducibility

- Set `PYTHONHASHSEED=0` in a fresh shell (not required for the OLS
  path but standard hygiene for the DFM's EM PCA on identical inputs).
- Fixed seeds: `random.seed(20260929)` and `np.random.seed(20260929)`
  at CLI entry.
- Master files, registry version and workbook SHA-256 are all recorded
  in `results/phase4a_model_specs.json`.
- `results/phase4a_evaluation_windows.parquet` captures each step's
  `first_train_quarter`, `last_train_quarter`, `n_train`, and target
  quarter.

## Regenerating the fixture-based rehearsal

```bash
python scripts/build_master_from_fixtures.py --output data/master_from_fixtures
python -m uznowcast.models evaluate --phase 4a \
    --master-dir data/master_from_fixtures \
    --registry registry/uzbekistan_nowcasting_v1.2_registry.xlsx
```

Running the same evaluator against a live V1.2 build:

```bash
python -m uznowcast.cli build --scope v1
python -m uznowcast.models evaluate --phase 4a
```

## Definition of done

Phase 4A is complete when every item below is true. As of 2026-09-29:

| Requirement | Status |
| --- | --- |
| Historical-mean benchmark works | ✔ |
| AR(1) benchmark works | ✔ |
| Bridge models are evaluated | ✔ |
| At least one parsimonious MIDAS spec is evaluated or its failure is documented | ✔ |
| At least one ragged-edge DFM spec is evaluated or its failure is documented | ✔ |
| Expanding-window pseudo-out-of-sample evaluation works | ✔ |
| Multiple nowcast horizons are implemented | ✔ (H1, H2, H3) |
| No future information leaks into training | ✔ (`test_data.py`, `test_evaluate.py`) |
| Database V1.2 remains unchanged | ✔ (no writes into `data/master`, `registry/`, `metadata/`, `data/raw/`) |
| Metrics are reproducible | ✔ (fixed seed, deterministic OLS/EM) |
| Modelling assumptions are documented | ✔ (`docs/modeling/model_specifications.md`) |
| Small-sample limitations are explicit | ✔ (§14) |
| All existing tests plus new relevant tests pass | ✔ (122 tests in the full suite) |
