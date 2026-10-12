# Phase 7C economic coverage research

Run from the repository root:

```powershell
.venv\Scripts\python.exe -B -m scripts.phase7c.run
.venv\Scripts\python.exe -B -m scripts.phase7c.validate
.venv\Scripts\python.exe -B -m scripts.phase7c.browser_check
.venv\Scripts\python.exe -B -m scripts.phase7c.finalize
```

Only `results/phase7c/` is written. Archived official observations are reused;
production inputs/configuration and prior research results are protected by hashes.
The frozen current snapshot is reproduced before challenger fitting.

R1/R2/R3 add retail/construction/imports to the unchanged one-factor AR(2) DFM.
R1_REAL_APPROX replaces nominal retail growth with approximate CPI-adjusted growth
inside the addition experiment. R4 is excluded when parent-flow validation fails.
No predictor is promoted. All historical predictor histories are retrospective
revised vintages with separately labeled assumed reporting delays. GDP uses the
existing strict publication-vintage accessor. Current predictions use archived
inputs available by 2026-10-05, never the subsequent 2026Q3 GDP outcome.

Non-estimable origins retain explicit failure reasons. Comparisons use pairwise
matched origins; uncertainty resamples target quarters. Sample controls recompute
M0 on each candidate's identical balanced estimation start. A 36-month minimum
comes from the unchanged production kernel, not phase-specific tuning.

The browser check uses installed Microsoft Edge in headless mode; restricted
Windows execution may require allowing its local process communication.
Finalization adds current M0/R1 factor paths and baseline loading signals, embeds
validation status, refreshes reports and updates artifact checksums.
