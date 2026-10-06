# Phase 6F research experiment

Run from repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.venv/Scripts/python.exe -m scripts.phase6f.experiment
.venv/Scripts/python.exe -m pytest scripts/phase6f/test_phase6f.py scripts/phase6e/test_phase6e.py tests/models
```

Research dependencies are pinned in `requirements-research.txt`. Run `python -m pip install -r scripts/phase6f/requirements-research.txt` in a Python 3.11+ environment. For independent numerical rerun evidence, run `python -m scripts.phase6f.verify`. The completed validation evidence records 123 existing model/Phase 6E tests passing and 11 Phase 6F tests passing after correction of a mixed-timestamp test parser.

Uses the frozen Phase 6E origins and current input snapshot, and the archived official CBU BOP workbook in `results/phase6f/raw/`. No network refresh, production promotion or dashboard writes occur. Outputs stay under `results/phase6f/`.

M0 reconstructs Phase 6E; M1/M2 apply economic lags to publication-masked transformed M2. B1/B2 add lagged M2 to the original factor + GDP AR bridge. B3/B4 add quarterly FDI and extra-quarter FDI respectively. B5 uses M1 factor extraction with FDI only in the bridge. FDI sensitivities use 90/120-day assumed publication delays. Revised FDI historical values are explicitly diagnostic and not certified real-time forecasts. Current FDI is withheld because this snapshot was retrieved after the production cutoff.

Historical release-vintage recovery is required before a genuine real-time FDI promotion assessment. The experiment cannot manufacture this evidence by assigning assumed release dates to today's revised values.
