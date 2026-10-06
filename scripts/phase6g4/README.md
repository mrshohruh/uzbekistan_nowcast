# Phase 6G.4

Run from the repository root:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
.venv/Scripts/python.exe -m scripts.phase6g4.run
.venv/Scripts/python.exe -m pytest scripts/phase6g4/test_phase6g4.py -q -p no:cacheprovider
```

This experiment reuses frozen estimation and vintage kernels and archived inputs.
It writes only `results/phase6g4/`. Native M0 must reproduce existing forecasts.
Common M0 is explicitly refitted with the same shorter training span as all four
challengers. CPI inflation is exact YoY log growth of a level chained from the
official previous-month=100 indices. No models are promoted.
