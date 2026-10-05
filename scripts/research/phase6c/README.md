# Phase 6C isolated research

From the repository root:

```powershell
.venv/Scripts/python.exe -X utf8 scripts/research/phase6c/run.py
.venv/Scripts/python.exe -m pytest scripts/research/phase6c/test_phase6c.py
```

On the Windows sandbox, pytest's `mkdir(mode=0700)` can remove inherited
sandbox access. Run the unchanged assertions through the isolated temporary
folder adapter when needed:

```powershell
.venv/Scripts/python.exe -X utf8 scripts/research/phase6c/test_runner.py all
```

To repeat the selected development fit and verify numerical reproducibility:

```powershell
.venv/Scripts/python.exe -X utf8 scripts/research/phase6c/verify.py
```

`finalize.py` reconstructs metadata/reports and adds controlled development
diagnostics without changing the selection freeze or forecasting the holdout.
`preliminary_master_only` preserves the initial interrupted master-only
experiment; it was stopped before any holdout forecast.

Dependencies are pinned by the existing Phase 6B research environment in
`scripts/research/phase6b/requirements-research.txt`.

Only `results/phase6c` is written by the runner. Existing model kernels,
registry, master datasets, forecasts, dashboards and earlier phase outputs
remain read-only and are checked against a SHA-256 inventory.

The runner audits registry master fields, estimates EM state-space factors,
selects blocks/information structure/factor count/AR order/bridge in that
order on development-only exact common origins, persists a selection freeze,
runs development-only robustness, and evaluates the selected holdout once.
Re-running reproduces the deterministic experiment, not a new opportunity
to tune against holdout results.

Approved Phase 6A.2 industrial/retail/construction published-growth recoveries
are explicitly labelled research transformation deviations from registry
nominal-flow clean fields; POS is scope-gated through December 2024. The
registry and canonical data are unchanged. An identical three-variable
domestic-panel 2019 sample-length experiment is unavailable.
Latest stored predictor values are release-lag masked; historical predictor
revision vintages are not known. The holdout was evaluated in previous
phases, so this phase provides a selection quarantine, not a previously
unseen research-programme holdout.

The estimator is statsmodels DynamicFactorMQ EM maximum likelihood with
missing measurements, independent AR factor blocks and diagonal white-noise
idiosyncratic errors. Missing observations are never filled in stored data.
H1/H2 future monthly factors are Kalman state predictions. See the
[official estimator documentation](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.dynamic_factor_mq.DynamicFactorMQ.html).
