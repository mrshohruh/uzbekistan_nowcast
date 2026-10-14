# Revised Phase 7E factor experiment

Run from the repository root with the existing pinned environment:

```powershell
.venv/Scripts/python.exe -B -m scripts.phase7e.revised_factors.run
.venv/Scripts/python.exe -B -m scripts.phase7e.revised_factors.validate
```

Outputs are confined to `results/phase7e/revised_factors/`. The runner uses the same immutable SHA256-selected Phase 7D input workbook, exact Phase 7E origins, GDP publication vintages and evaluation actuals. It reproduces every successful original model/origin fit before comparing exclusions. Original Phase 7E entry points keep their default factor configuration.

Exact exclusions: aggregate industrial production from F1; headline CPI and composite PPI from F5. The full monthly set becomes 88 and the original economic core becomes 15. Retained M2 replaces the removed F5 **sign anchor only**; it is already a measurement in both sets. No measurement is replaced or transferred. The original weighting formula is reapplied to retained families, with all penalties and estimation rules unchanged.

Predictor source release dates and historical vintages are not present in the original research input. Historical estimates retain the original assumed-lag gates and are labeled **PSEUDO_REAL_TIME_NOT_VINTAGE_VERIFIED**. Strict GDP vintage boundaries, causal training transformations and origin-by-origin refits are preserved, but authentic predictor real-time availability cannot be certified. No release dates are invented. Core F5 retains only money and lending rates, so it no longer directly measures inflation.

Production COMBO_50_50 remains **8.180901340616275%**. No production promotion occurs. The dashboard is an offline HTML artifact with embedded data, model/sample/horizon/version controls, searchable factor membership, sortable tables and SVG charts.

The validator uses short private fixture directories to keep staged snapshot filenames below legacy Windows path limits. In a restricted execution environment, Edge may require an approved unrestricted process launch for Windows IPC. `python -B -m scripts.phase7e.revised_factors.finish` resumes failed checks and offline browser validation without repeating completed model estimation. Initial failures and targeted retries remain in the validation JSON, XML and report.

Executed experiment: 351 distinct tests passed after resolving two staged-copy path-length failures; 82 browser state checks passed. Complete numerical replay preserved every CSV byte. After correcting case-insensitive dashboard search, two reporting replays produced identical HTML while numerical CSV hashes stayed unchanged. Original successful forecasts reproduced exactly at all 95 model/origin combinations.
