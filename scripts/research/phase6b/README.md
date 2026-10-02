# Phase 6B isolated state-space research

Install `requirements-research.txt` in the repository virtual environment. Run:

```powershell
.venv/Scripts/python.exe scripts/research/phase6b/run.py
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider -o addopts='' scripts/research/phase6b/test_experiment.py --junitxml=results/research/phase6b/phase6b_test_results.xml
.venv/Scripts/python.exe scripts/research/phase6b/finalize.py
```

The persistent `results/research/phase6b/phase6b_protected_before.json` baseline
must exist and must never be replaced to bypass a failure. The runner checks
every listed artifact before and after its work. Outputs are confined to the
new Phase 6B research/report paths and a separate research dashboard.

Frozen Phase 5C calendar cutoffs and V1.2 release lags are reused. Services uses
the existing cutoff function's explicit 30-day fallback because no services
registry entry exists; this is an assumed calendar mask, never a release date.
The latest panel contains revised observations rather than historical vintages.
All forecasts are CALENDAR_PSEUDO_REAL_TIME_RESEARCH.

Parameters, standardization and services adjustment are estimated strictly
before the target quarter. State-space filtering uses only masked observations;
future missing states are forecasts, not interpolated predictor measurements.
Smoothed factors are descriptive only. Separate equal-weight combinations
avoid selecting a best DFM on its reported test performance.

Phase 5C origin-level DFM predictions were not saved by its runner. Its aggregate
metrics cannot be compared on exact Phase 6B origins. Frozen AR and U-MIDAS
predictions are reused from the saved Phase 4B/4C validation artifacts.

The finalizer verifies the required outputs, tests, core numeric rerun hashes
and protected baseline. It adds verification evidence and output checksums to
the manifest without altering forecast tables. The determinism reference was
captured from the first completed experiment and remains persistent.
