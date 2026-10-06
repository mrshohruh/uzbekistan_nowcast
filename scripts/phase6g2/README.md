# Phase 6G.2 research only

Run from the repository root:

```powershell
.venv/Scripts/python.exe -m scripts.phase6g2.run
.venv/Scripts/python.exe -m scripts.phase6g2.tests
```

Outputs are confined to `results/phase6g2`. Existing accepted estimation kernels are imported without modification. No source refresh, model promotion, production forecast or dashboard writer is invoked.

M0/M1/M2 retain YoY M2 with economic lags 0/1/2; Q0/Q1/Q2 use monthly rolling three-month log changes with the same lags. Natural and common starts are both estimated on the frozen Phase 6G eligible origins. The primary common sample intersects successful forecasts globally across all six specifications. Raw M2 must reproduce the accepted historical YoY panel before estimation proceeds.

FDI levels and asinh are tested only in the Q2 quarterly bridge with assumed 90/120-day timing. The archived FDI snapshot postdates the frozen current cutoff; current FDI challenger forecasts stay unavailable. Historical results are revised-history diagnostics, not vintage-real-time forecasts.

The before/after SHA-256 inventory includes production, earlier research outputs, dashboards and processed/master data. Tests write temporary files and reports only inside this phase's output directory.
