# Production V2 / Phase 6E

Reproduce the latest committed operational information set:

```powershell
.venv/Scripts/python.exe -m scripts.phase6e.run
```

Refresh official sources through the existing transactional updater, then rebuild V2:

```powershell
.venv/Scripts/python.exe -m scripts.phase6e.update --update-data
```

The existing `scripts.operations.run_update` remains the legacy reproduction entry
point. V2's policy and default dashboard are selected through
`results/operations/current_production.json` and
`dashboard/current/uzbekistan_nowcast.html`. Legacy source code, policies,
research files and versioned dashboards remain intact.
The normal Windows launcher `run_nowcast.bat` routes to the V2 updater when the
active production pointer exists; its legacy fallback remains available.

Run offline tests in isolated processes:

```powershell
.venv/Scripts/python.exe -m scripts.phase6e.tests all
```

Run an independent build for byte-level reproducibility checks:

```powershell
.venv/Scripts/python.exe -m scripts.phase6e.verify
```

Promotion requires complete identical holdout origins and the lowest pooled RMSE.
Historical predictor availability retains the frozen lag-based pseudo-real-time
protocol; complete historical observed release vintages are unavailable. Current
inputs are gated by observed retrieval/release dates and the frozen horizon mask.
GDP uses documented publication vintages and remains quarterly; the target is
the published cumulative YTD real GDP growth convention.

News uses exact all-subset Shapley counterfactual reruns with old parameters fixed.
The actual protocol refits, so parameter re-estimation is reported as a distinct
channel. Current-quarter DFM loading signals are descriptive and remain unavailable
when that indicator has no released observation in the target quarter. They must
not be summed with U-MIDAS percentage-point contributions.

To roll back the default view, copy the preserved
`results/phase6e/legacy_current_dashboard.html` to
`dashboard/current/uzbekistan_nowcast.html` and set `current_production.json` to
the legacy policy `results/phase5b/phase5b_production_policy.json`. The legacy
operations entry point remains runnable without changing frozen code.
