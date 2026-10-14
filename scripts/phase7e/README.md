# Phase 7E — isolated economic factor research

Reads the SHA256-selected immutable Phase 7D input archive and existing GDP vintages. All outputs go to `results/phase7e`; implementation and tests are confined to this namespace. No downloads, forecasting promotion or production writes occur.

Windows CMD:

```cmd
cd /d C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter
.venv\Scripts\python.exe -B -m scripts.phase7e.run
.venv\Scripts\python.exe -B -m scripts.phase7e.validate
start "" "results\phase7e\phase7e_economic_dfm_dashboard.html"
```

Use the repository's pinned `requirements.txt` and `requirements-models.txt` environment. Validation re-executes the complete research pipeline, compares every generated CSV and the HTML bytes, runs the entire existing pytest suite plus new scientific tests, exercises all offline dashboard controls in installed Edge, and verifies protected-file hashes. Temporary test/browser artifacts remain inside the Phase 7E results directory.

Fixed identification rules, sign anchors, weighting, ridge penalties, reduced-history bridge and the E3 two-stage hierarchical approximation are documented in the generated methodology. Predictor vintages remain unverified and historical research must not be described as authentic real time. The economics core is 17 monthly indicators. Production stays `COMBO_50_50 = 8.180901340616275%`.
