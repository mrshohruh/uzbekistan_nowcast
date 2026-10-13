# Phase 7D research

Run from the repository root:

```powershell
.venv\Scripts\python.exe -m scripts.phase7d.run
.venv\Scripts\python.exe -m scripts.phase7d.test_runner
.venv\Scripts\python.exe -m scripts.phase7d.browser_check
```

Optional arguments: `--workbook PATH`, `--cutoff YYYY-MM-DD`.
The default locates the supplied workbook and uses the frozen production
calendar cutoff. Re-running replaces generated Phase 7D reports only; immutable
input archives are content-addressed and never overwritten. All prior
scientific, raw/master, registry and production artifacts are hashed before
and verified after the experiment.

No model, weight, forecast, master or registry promotion occurs. Read the
generated methodology for all transformation, release-lag, estimation and
uncertainty assumptions. Uses existing pinned dependencies; no new dependency
or CDN is required. The dashboard opens directly as a local HTML file.
