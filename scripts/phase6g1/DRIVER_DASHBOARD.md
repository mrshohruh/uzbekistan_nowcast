# M2-L2 research driver dashboard

Reconstruct the frozen current D0 and D2 fits and generate the standalone dashboard and two CSVs:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.venv/Scripts/python.exe -m scripts.phase6g1.driver_dashboard
.venv/Scripts/python.exe -m pytest scripts/phase6g1/test_driver_dashboard.py -q -p no:cacheprovider
```

The renderer copies the Phase 6E dashboard's exact stylesheet and driver bar geometry. Each fit supplies its own training mean, sample SD and sign-aligned loadings. Signals are descriptive standardized units, not GDP contributions. The latest value is the transformed source observation. D2 M2's July 2026 observation occupies the September 2026 factor cell; its Q3 signal averages the three available lagged factor cells. POS remains null and is excluded from the available-signal denominator. The U-MIDAS channel is copied from the unchanged Phase 6E output.

Outputs: `dashboard/phase6g1_m2_lag_driver_dashboard.html`, `results/phase6g1/phase6g1_d2_current_drivers.csv`, and `results/phase6g1/phase6g1_d0_vs_d2_driver_comparison.csv`. Validation and test evidence use separate `phase6g1_driver_dashboard_*` files. The earlier audit report, manifest, CSVs, and production artifacts are protected and remain unchanged.
