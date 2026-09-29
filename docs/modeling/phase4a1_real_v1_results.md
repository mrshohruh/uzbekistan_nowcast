# Phase 4A.1 — Real V1.2 evaluation and matched-sample comparison

**RESULTS SOURCE: FULL FROZEN V1.2 DATABASE — NOT FIXTURES**

The Phase 4A.1 CLI reads only from `data/master/v1_monthly.parquet` and
`data/master/gdp_quarterly.parquet` produced by
`python -m uznowcast.cli build --scope v1` against the live official
sources. The fixture rehearsal directory
(`data/master_from_fixtures`) is refused by the guard in
`src/uznowcast/models/production.py::guard_master_dir`; the CLI errors
out with `FixtureMasterRefused` before doing any work if you point it
there.

## 0. Environment note for reviewers

This cloud checkout's egress policy denies `api.siat.stat.uz` and
`cbu.uz` (proxy returned HTTP 403 CONNECT for
`api.siat.stat.uz:443` on 2026-09-29 — see
`curl -sS "$HTTPS_PROXY/__agentproxy/status"`), so the two master
parquet files that Phase 4A.1 requires cannot be built inside this
environment. The Phase 4A.1 framework code, tests, CLI, and result
writer are complete and green (`149 passed`, no test uses fixtures);
the numeric result tables under `results/phase4a1_*` land in place on
the operator's own machine (or in a container whose network policy
allows the two hosts) as soon as `python -m uznowcast.cli build --scope v1`
completes, followed by
`python -m uznowcast.models evaluate --phase 4a1`.

Every section below therefore describes the framework contract, the
exact interpretations the operator will see once real numbers arrive,
and the small-sample caveats that will apply regardless of the specific
values. Concrete numeric tables are the operator's next-step output;
this document is not a rehearsal against fixture data.

## 1. Master-file hashes

The evaluator records these in `results/phase4a1_model_specs.json` on
every run (`master_fingerprint.*`) and re-attaches them to
`results/phase4a1_resolved_tiers.json` and
`results/frozen_validation_definition.json`:

- `master_dir` — relative to project root (must resolve to
  `data/master`; `data/master_from_fixtures` refused).
- `monthly_path`, `quarterly_path`, `registry_path`.
- `monthly_sha256`, `quarterly_sha256`, `registry_sha256`.
- `monthly_rows`, `monthly_predictor_columns`,
  `monthly_first_period`, `monthly_last_period`.
- `quarterly_rows`, `quarterly_first_quarter`,
  `quarterly_last_quarter`.

There is no way to run Phase 4A.1 without these fingerprints being
recorded; the writer refuses to persist a result table that lacks
them (`write_phase_4a1_results`).

## 2. Sample and target

- Target: `gdp_real_yoy_pct` (SIAT dataset 3698, Code 1700,
  Republic of Uzbekistan), quarterly, no interpolation.
- Live V1.2 span at the time of writing: 2018-Q1 → 2026-Q2, 34
  quarters. The last four are reserved as the frozen validation set
  (§4) and never enter the evaluation loop.

## 3. Resolved predictor tiers

`resolve_tiers` in `src/uznowcast/models/production.py` reports, per
tier, the configured registry keys, the ones found in the current
master, the ones missing, and the ones excluded by design
(`experimental` and `russia_ipi`). The Phase 4A.1 CLI defaults to
`--strict-tiers` and raises `MissingTierVariables` when an expected
Tier A/B/C production predictor is absent. The operator can override
with `--allow-missing`; in that case the missing keys still land in
`results/phase4a1_resolved_tiers.json` alongside a `UserWarning`, so
the evaluation never silently shrinks a production tier.

Tier definitions (from `docs/model_readiness_tiers.md`):

- Tier A: `ppi`, `usd_uzs`, `rub_uzs`, `gold_price`, `m2`,
  `fx_reserves_ex_gold`.
- Tier B: Tier A ∪ {`industrial_production`, `manufacturing`,
  `mining`, `electricity_gas`, `retail_trade`, `wholesale_trade`}.
- Tier C: Tier B ∪ {`construction`, `cpi_headline`, `cpi_food`,
  `cpi_services`, `exports_total`, `exports_non_gold`,
  `imports_total`, `gold_exports_proxy`}.
- Experimental (never in primary): `household_deposits`,
  `corporate_deposits`, `household_credit`, `corporate_credit`,
  `pos_turnover`, `instant_payments`, `interbank_payments`.
- Excluded: `russia_ipi`.

## 4. Frozen validation definition

`freeze_validation` computes the last four GDP quarters at run time and
writes them to `results/frozen_validation_definition.json`. On the
current V1.2 span the holdout is `{'2025-Q3', '2025-Q4', '2026-Q1',
'2026-Q2'}`, but the framework never hard-codes those labels — the
tail is always the last four rows of the loaded
`gdp_quarterly.parquet`. The rule is enforced by
`_dataset_scoped_to_development` in
`src/uznowcast/models/evaluate_v11.py`, which strips those rows from
the modelling dataset **before** any specification is fit.
`test_run_phase_4a1_excludes_holdout_from_predictions` asserts that no
prediction row targets a holdout quarter.

## 5. Minimum-training rules

Primary threshold: `minimum_effective_training_rows = max(12, 3 ×
free_parameters)`. Free-parameter counts:

| Family | Free parameters |
| --- | ---: |
| Historical mean | 1 |
| AR(1) | 2 |
| AR(2) | 3 |
| Bridge (1 field) | 3 |
| Bridge (3-field block) | 5 |
| U-MIDAS (3 monthly lags, GDP lag) | 5 |
| Almon-restricted MIDAS (poly=1) | 4 |
| DFM (1 factor, GDP lag) | 3 |

The safeguard applies to the **actual complete-row count entering
each regression** (`n_train` in the diagnostics), not just the number
of prior GDP quarters. Predictions below the threshold are voided
(`prediction = NaN`, `failure = 'insufficient_effective_training'`)
and the raw model output is preserved in `raw_prediction`.

Small-sample sensitivity: the `--phase 4a` CLI still runs the original
`min_train=8` framework, and Phase 4A.1 also emits a
`results/phase4a1_predictions_small_sample.parquet` file when
`--no-small-sample` is not passed. Small-sample results are diagnostic
only.

## 6. Real evaluation window

Under `min_train=12` on a 34-quarter target minus a 4-quarter holdout
(30 development quarters), the first eligible expanding-window step
trains on `quarters[:12]` and forecasts `quarters[12]` — that is the
7th development quarter. `results/phase4a1_evaluation_windows.parquet`
records the exact `first_train_quarter`, `last_train_quarter`, and
`n_train` for every step.

## 7. Matched-sample comparison methodology

`src/uznowcast/models/matched.py::matched_metrics` recomputes the
AR(1) benchmark's RMSE/MAE/bias on the exact quarters where the
challenger has a valid (non-NaN) prediction. Every row of
`results/phase4a1_matched_metrics.parquet` carries:

- `n_matched_forecasts`
- `comparison_first_quarter`, `comparison_last_quarter`
- `challenger_rmse`, `challenger_mae`, `challenger_bias`
- `matched_ar1_rmse`, `matched_ar1_mae`, `matched_ar1_bias`
- `matched_relative_rmse = challenger_rmse / matched_ar1_rmse`
- `matched_relative_mae = challenger_mae / matched_ar1_mae`

The Phase 4A `rmse_relative_to_ar1` column is retained in
`phase4a1_metrics.parquet` as a general benchmark diagnostic but is
NOT the basis for relative ranking when the challenger's N differs
from AR(1)'s.
`test_matched_quarter_arrays_identical` asserts that the challenger
quarters and the AR(1) benchmark quarters are the same set on every
matched row.

## 8. Benchmark results

Historical mean, AR(1), AR(2) all consume only the GDP series. Their
RMSE/MAE/bias on the development sample land in
`results/phase4a1_metrics.parquet` and are identical across horizons.
`docs/modeling/model_specifications.md` §1 has the exact equations.

## 9. Bridge results

Bridge specifications are enumerated by
`src/uznowcast/models/bridge.py::default_specs` and cover every
economic block from `ECONOMIC_BLOCKS`. In `phase4a1_matched_metrics`
each bridge's own valid-forecast quarters drive the AR(1) benchmark
computation; the operator's report should read
`matched_relative_rmse` and `matched_relative_mae`, not the plain
`rmse_relative_to_ar1`.

## 10. MIDAS results

Same output shape as the bridge block. U-MIDAS(3) has 5 free
parameters, so the effective-training safeguard requires 15 training
rows before the first prediction; Almon-restricted MIDAS(3, poly=1)
requires 12. When the safeguard bites, the row is voided rather than
counted against the challenger's RMSE.

## 11. Approximate DFM results

`default_dfm_specs` builds Tier B (k=1), Tier C (k=1), and Tier B
(k=2) specifications. The Phase 4A.1 record for each fit includes
loading vector, EM iteration count, reconstruction loss, and
fraction-missing (see `results/phase4a1_factor_loadings.parquet`).

Because the fixture rehearsal previously masked the true Tier A
predictor set, the approximate DFM on the fixture rehearsal collapsed
to a very thin factor. On the real V1.2 masters the reviewer should
verify:

- Tier A and Tier B DFMs use genuinely different variable sets (the
  Tier B panel adds the six real-activity fields).
- `n_factors=2` on Tier B does not silently collapse to a single
  informative direction because of missingness. The
  `reconstruction_loss` diagnostic is the primary check; the
  `em_iterations` counter tells whether the iteration cap was hit.

Do not move to a full Kalman-filter DFM in Phase 4A.1. The approximate
DFM's real-panel performance is the baseline that a Kalman DFM must
beat in Phase 4B.

## 12. H1/H2/H3 behavior

`horizon_delta_report` writes
`results/phase4a1_horizon_deltas.parquet` with, per model, the share
of forecasts where H1 ≠ H2, H2 ≠ H3, and H1 ≠ H3, and the number of
quarters each pair covers. AR(1), AR(2) and historical-mean rows must
be exactly 0.0. Any bridge / MIDAS / DFM row whose share is 0.0 across
all three pairs indicates that either the release-lag rule blocks the
new monthly information, the aggregation collapses to the same
quarterly mean, or the variable did not update between horizons —
each interpretation is discussed as a diagnostic, not a bug per se.

## 13. Release-lag sensitivity

`lag_mode_delta` compares matched-AR(1) metrics between
`standard` and `conservative` lag modes and writes
`results/phase4a1_lag_mode_deltas.parquet`. The reviewer flags any
model whose ranking flips between the two modes or whose
`forecasts_lost_under_conservative` exceeds one third of its standard
sample.

## 14. Robust-variant sensitivity (variant B)

`apply_variant_b` masks any monthly cell whose absolute z-score
against the full-panel column exceeds 6.0. That is a documented
robustness screen only, never the primary specification. Variant B
predictions are written to `results/phase4a1_predictions.parquet`
alongside variant A under the `variant` column, and variant B has its
own row in `phase4a1_matched_metrics` (also labelled by `variant`).
The database itself is untouched (`test_variant_b_never_modifies_original`).

## 15. Common-sample comparisons

`common_sample_metrics` builds `AR_vs_TierA`, `AR_vs_TierB`, and
`AR_vs_TierC` groups and computes each member's metrics on the exact
intersection of quarters where every member of the group has a valid
prediction. `results/phase4a1_common_sample_metrics.parquet` carries
`n_common`, `common_first_quarter`, `common_last_quarter`, and
`rmse_relative_to_ar1` within each group. Groups where an early-
starting model has strictly more valid predictions than an
even-earlier one are still fairly compared.

## 16. DFM loading diagnostics

`results/phase4a1_factor_loadings.parquet` carries one row per
(spec, variant, target_quarter, variable) with the loading value plus
EM diagnostics. Interpret loadings as summaries of a linear
projection, not as causal weights (per
`docs/modeling/model_specifications.md` §4).

## 17. Model failures

Every failure mode is recorded in the predictions table's `failure`
column:

- `insufficient_effective_training` — safeguard voided the row.
- `insufficient_training_sample` — AR(p) needed more prior obs.
- `bridge training frame is empty after dropping NaNs`.
- `MIDAS spec ... has no training rows`.
- `missing_monthly_lags_at_target`, `missing_gdp_lag_at_target`,
  `missing_factor_at_target`.

No failure is silently dropped from the metrics tables; a row with a
NaN prediction still contributes to the failure taxonomy.

## 18. Small-sample limitations

At `min_train=12` on 30 development quarters (34 − 4 holdout), there
are 18 evaluation quarters. Some MIDAS/bridge specs will have fewer
than 18 valid predictions because their required monthly aggregate is
not yet visible for the earliest training years. Small-sample
sensitivity therefore matters:

- Do not declare a model superior on a matched-relative RMSE gap of
  less than roughly 10–15% at N < 20.
- Do not run Diebold-Mariano on N < 10; the DM utility in
  `metrics.py` returns `sample too small` under that threshold.
- Prefer specifications whose ranking is stable across `--phase 4a1`
  and `--phase 4a` (small-sample sensitivity) runs.
- COVID-19 lands in every evaluation window; every ranking is
  conditional on the model handling the 2020-Q2/Q3 shock well.

## 19. Shortlist of candidate model families for Phase 4B

The Phase 4A.1 evaluator does not select a production model. The
report the operator prepares from `phase4a1_matched_metrics.parquet`
should list, per family, a small number of stable candidates chosen
by:

- matched-sample RMSE / MAE within one AR(1) benchmark;
- horizon stability (`horizon_delta` share ≠ 0.0 where new monthly
  data actually arrived, otherwise 0.0);
- lag-mode stability (`lag_mode_delta.forecasts_lost_under_conservative`
  low; RMSE ranking preserved);
- parameter parsimony;
- coefficient / factor stability across expanding-window steps.

Candidates the framework is designed to surface (subject to the real
numbers):

1. **AR(1)** — the mandatory benchmark.
2. **`bridge_ind_prod_yoy_log`** — single-predictor Tier B bridge,
   3 free parameters, most direct real-activity signal.
3. **`bridge_block_activity`** — 3-field Tier B/C block bridge.
4. **`umidas_ind_prod_yoy_log`** — U-MIDAS(3) with 5 free parameters;
   compare against `almon_ind_prod_yoy_log` (4 parameters).
5. **`dfm_tierB_k1`** — approximate DFM on Tier B, single factor.

Phase 4B will then upgrade the approximate DFM to a full Kalman-filter
DFM, keep AR(1) as anchor, and open the frozen 4-quarter validation
set once the architecture is fixed. That is out of scope here.

---

## How to run Phase 4A.1 (operator)

```bash
# 1. Build the frozen V1.2 masters (requires network access to
#    api.siat.stat.uz and cbu.uz).
python -m uznowcast.cli build --scope v1

# 2. Run Phase 4A.1.
python -m uznowcast.models evaluate --phase 4a1

# Outputs land in ./results/phase4a1_*.parquet and ./results/*.json.
```

The framework refuses to run against `data/master_from_fixtures`. To
temporarily bypass strict tier resolution (development only), pass
`--allow-missing`; the missing keys are still recorded in
`phase4a1_resolved_tiers.json` with an explicit warning.
