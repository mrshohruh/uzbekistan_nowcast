# `results/` — Phase 4A and Phase 4A.1 output tables

Committed here:

- `phase4a_predictions.parquet`
- `phase4a_metrics.parquet`
- `phase4a_evaluation_windows.parquet`
- `phase4a_factor_loadings.parquet`
- `phase4a_model_specs.json`

These were produced by the fixture-based rehearsal
(`scripts/build_master_from_fixtures.py` + `python -m uznowcast.models
evaluate --phase 4a`). They exist so the Phase 4A framework is
inspectable without a live rebuild. See
`docs/modeling/phase4a_results.md` §10 for the caveats.

Not committed here (produced on the operator's own environment):

- `phase4a1_predictions.parquet`
- `phase4a1_predictions_small_sample.parquet`
- `phase4a1_metrics.parquet`
- `phase4a1_matched_metrics.parquet`
- `phase4a1_common_sample_metrics.parquet`
- `phase4a1_evaluation_windows.parquet`
- `phase4a1_horizon_deltas.parquet`
- `phase4a1_lag_mode_deltas.parquet`
- `phase4a1_factor_loadings.parquet`
- `phase4a1_model_specs.json`
- `phase4a1_resolved_tiers.json`
- `frozen_validation_definition.json`

The Phase 4A.1 CLI refuses `data/master_from_fixtures` by design and
only accepts the live V1.2 build. The cloud environment in which this
repository was authored has an egress policy that denies
`api.siat.stat.uz` and `cbu.uz`, so the live build cannot run here.
See `docs/modeling/phase4a1_real_v1_results.md` §0 for the exact
instructions the operator runs to produce the tables above.

None of the files in this directory are inputs to any other script;
they are pure outputs. Delete them freely and regenerate with the CLI.
