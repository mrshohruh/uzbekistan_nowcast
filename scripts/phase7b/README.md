# Phase 7B satellite research

Run offline from the repository root:

```
.venv/Scripts/python.exe -m scripts.phase7b.run
.venv/Scripts/python.exe -m scripts.phase7b.test_runner
```

The colleague's semicolon-separated CSV must exist at
`data/research/satellite/input/uzbekistan_nightlights_monthly.csv`.
The pipeline archives exact bytes by SHA256, validates the expected monthly
coverage, and leaves source and production files untouched. Results are written
under `results/phase7b/`; transformations and the raw archive remain under
`data/research/satellite/`.

The adapter reuses production mask, standardization, EM estimator and GDP bridge
functions. GDP vintage boundary violations stop the run. Scientific estimation
failures are recorded as null predictions with reasons. Baselines are independently
recomputed and checked against frozen forecasts. Satellite availability at month
end plus 0/1/2/3 calendar months is an explicit hypothetical assumption.

Exploratory results use revised satellite measurements, not verified real-time
vintages. No experimental model is promoted. Leave-quarter-out robustness removes
quarters from scoring, not from training. The offline HTML embeds all chart data
and JavaScript. Existing artifacts are hashed before and verified after execution;
test temporary directories are excluded from scientific protection.

The test runner excludes the legacy whole-repository historical hash test
`test_protected_artifacts_unchanged`, which predates these authorized research
files. Existing production seal tests and this run's independent protection audit
cover integrity instead.
