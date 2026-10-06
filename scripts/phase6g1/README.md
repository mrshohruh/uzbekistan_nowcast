# Phase 6G.1 research audit

Uses the existing pinned environment and archived official observations. All new outputs are isolated in `results/phase6g1/`; production and earlier phases are hash protected. Historical predictor value vintages remain unverified.

Run from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.venv/Scripts/python.exe -m scripts.phase6g1.verify
.venv/Scripts/python.exe -m scripts.phase6g1.tests existing
.venv/Scripts/python.exe -m scripts.phase6g1.tests new
.venv/Scripts/python.exe -m scripts.phase6g1.finalize
```

`verify` executes the complete reproduction gate and challenger audit twice and compares every numerical CSV byte for byte. Tests use no network. `finalize` validates test results, output hashes, and protected files, then records validation in the report and manifest. Failed challenger fits stay missing and are excluded only through explicitly named common samples; they are never replaced by benchmark forecasts.
