# M0 / M1 / M2 driver comparison

Generate all five new artifacts with two independent complete refits, then test and print the validation record:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.venv/Scripts/python.exe -m scripts.phase6g1.m1_dashboard
.venv/Scripts/python.exe -m pytest scripts/phase6g1/test_m1_dashboard.py scripts/phase6g1/test_driver_dashboard.py scripts/phase6g1/test_phase6g1.py -q -p no:cacheprovider --junitxml=results/phase6g1/phase6g1_m1_driver_tests.xml
.venv/Scripts/python.exe -m scripts.phase6g1.finish_m1_dashboard
```

The original Phase 6F common holdout contains 12 identical origins (2025Q3–2026Q2, H1/H2/H3), with revised historical predictor values. Its metrics are copied without replacing them with Phase 6G extended-history scores. This is a revised-history diagnostic, not fully vintage-real-time validation or a promotion decision.

Each current DFM is refitted from the exact archived Phase 6E information identity used by Phase 6F/6G.1. Publication gating occurs before the economic lag. Each fit supplies its own training sample, mean, sample SD and loadings. Latest M1 M2 is August 2026 in the September cell; latest M2 M2 is July 2026 in the September cell. No newer source observation is implied. POS has no current-quarter observation: both current value and signal remain null while its historical fitted loading is retained. U-MIDAS predictions and its FX contribution are copied unchanged.

The three comparison panels share a single absolute signal scale; the standalone M1 panel follows the original geometry. Missing signals receive zero-width visual bars labeled Unavailable, never numeric zero. Shares and signals are descriptive factor statistics, not GDP contributions.

All earlier audit and production outputs, including the existing M2 dashboard, are protected against modification. New output hashes, publication checks, fit-specific scaling, and the exact archived cutoff are available in the validation JSON and embedded dashboard payloads.
