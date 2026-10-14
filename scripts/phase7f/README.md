# Phase 7F — static factor-number diagnostics

Read-only research implementation. Uses the exact production columns and transformed panel, the immutable Phase 7D workbook used by Phase 7E, and saved E3 block/hierarchical signals. No data download or forecast/model update occurs.

```cmd
cd /d C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter
.venv\Scripts\python.exe -B -m scripts.phase7f.run
.venv\Scripts\python.exe -B -m scripts.phase7f.validate
start "" "results\phase7f\phase7f_factor_selection_dashboard.html"
```

Uses existing pinned requirements and model requirements. Validation executes formula, balancing, information-boundary, loading and reproduction tests, relevant existing production/Phase 7D/Phase 7E regressions, full numerical/HTML replay and all-panel offline Edge interaction checks. Browser launching inside a restrictive Codex Windows sandbox may need the native approval for installed Edge; an actual successful fingerprinted check can be reused against byte-identical HTML.

See the generated methodology for origin normalization, weighting, complete-case gaps, common-calendar exclusions, long-history rectangles and upper-bound sensitivity. Recommendations concern static covariance components, never automatically dynamic shocks, production coefficients, economic sector shares or forecast-optimal counts.
