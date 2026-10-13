# Tests and evidence

No network requests were made. `validation/diagnose.py` replays only the named run's recorded URLs and verifies payload SHA256 before parsing; recorded non-200 responses fail explicitly. There is no fallback to live networking. Replay results are not claimed as new live verification.

Real reserves replay reproduces September INVALID and unchanged accepted history. Full POS replay restores two months, reduces article failures from 46 to 44, and reduces internal gaps from 14 to 12 while preserving failed admission.

Five focused regressions pass: both unchanged official Avgust workbooks and exact amounts, contradictory reporting range rejection, explicit truncated-row failure, and simultaneous reserves/POS failure retaining those series while an independent gold observation is accepted in an isolated dry-run stage. The latter does not publish any version or alter gold methodology.

The broader collection/HTTP/FX/production-configuration suite passed **60 tests, zero failures**, in 127.88 seconds; see validation/regression_tests.xml. The focused suite passed **5 tests, zero failures** in 7.38 seconds; see validation/focused_tests.xml. Four focused tests overlap the broader run, so there are **61 distinct passing tests**, not 65. The independent-acceptance test was added after broad collection began and passed in the focused run. Coverage includes outages, revisions, daily FX persistence, POS scope, GDP first releases, competing locks, interruption/recovery and version integrity. Existing tests that publish versions use synthetic isolated roots only; no repository collection or production commit was requested or executed.

Commands:

```powershell
.venv\Scripts\python.exe -B -X utf8 -m scripts.collection.test_runner tests/collection tests/test_http.py tests/test_cbu_fx_parser.py tests/production/test_configuration.py
.venv\Scripts\python.exe -B -X utf8 -m scripts.collection.test_runner tests/collection/test_phase8a3b.py
```

Production protection: all 1,961 original baseline files unchanged, 81 accepted runtime hashes PASS, current-version check PASS. Masters, processed inputs, vintage history, scientific definitions, coefficients, forecast and dashboards are unchanged. The additive POS collector is outside the accepted production runtime; no seal was regenerated.
