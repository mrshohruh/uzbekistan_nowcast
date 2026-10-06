# Phase 6G.3 — GDP target audit

```powershell
.venv/Scripts/python.exe -m scripts.phase6g3.run
.venv/Scripts/python.exe -m scripts.phase6g3.tests
```

All outputs are in `results/phase6g3`. Official nominal SIAT descriptors/payloads are archived there and reused with checksum validation. No production, registry, dashboard or prior research writer is invoked by the experiment.

The real audit covers every quarter from 2018Q1 and reconciles archived SIAT indices, processed index-minus-100 values and current quarterly master values. Current snapshot dates are distinct from evidenced first-release dates. The existing verified GDP vintage accessor controls historical real training and actuals.

Nominal GDP is SIAT production-method current-price dataset 3695 / indicator 1.01.01.0056, billion UZS. Quarterly cumulative levels are de-cumulated within year. Annual totals are independently validated against SIAT dataset 544 / indicator 1.01.01.0001.

Historical nominal levels come from a reviewed extraction ledger tied to checksummed dated official PDFs and one rounded official article. Every nominal growth regressor records all cumulative parent values, dates and source hashes. The latest revised SIAT snapshot is used for validation/descriptive diagnostics, never backdated into historical model training.

Both controlled bridges use identical GDP training quarters within the accepted estimation window and identical accepted filtered factor paths. A separate accepted full-history real bridge is reproduced for reference. Origin failures from insufficient nominal history remain explicit.

The requested comparison changes cumulative real growth to standalone nominal growth, as well as ordinary to log growth. It does not isolate price-basis effects alone. Supplementary cumulative nominal / log-real / implicit-price diagnostics document that limitation. No automatic promotion occurs.
