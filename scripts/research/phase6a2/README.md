# Phase 6A.2 isolated research recovery

These scripts read the existing registry/master/provenance files without modifying them. They never import or estimate forecasting models. Source archives and latest-vintage research outputs are separate from production.

Install PDF/XLS readers in an isolated directory, using the repository environment for its existing pinned pandas/requests/openpyxl/pyarrow dependencies:

```powershell
.venv/Scripts/python.exe -m pip install --target data/research/phase6a2/_vendor -r scripts/research/phase6a2/requirements-research.txt
```

Cached official-source collection:

```powershell
.venv/Scripts/python.exe scripts/research/phase6a2/collect_sources.py stat
.venv/Scripts/python.exe scripts/research/phase6a2/collect_sources.py pos
.venv/Scripts/python.exe scripts/research/phase6a2/collect_sources.py siat
.venv/Scripts/python.exe scripts/research/phase6a2/extend_trade.py
```

The source inventory lists the original paper, bulletin annexes, receipts evidence and individually researched supplementary sources. Those raw files and collector manifests must be retained for offline reproduction. All original downloads remain immutable; links returning 404 and unreadable PDFs remain visible in the fetch/parse failure logs. Existing official raw downloads are reused with checksum validation.

Reproduce extraction and audit outputs from archived sources:

```powershell
.venv/Scripts/python.exe scripts/research/phase6a2/extract.py
.venv/Scripts/python.exe scripts/research/phase6a2/build.py
.venv/Scripts/python.exe -m pytest -q -o addopts='' scripts/research/phase6a2/test_recovery.py
```

`build.py` verifies the preserved run-manifest baseline before and after work and stops on any changed protected file. Do not replace that baseline to bypass a failure. Raw observation CSV and provenance include source URLs, hashes, retrieval times, exact selectors and known publication/update dates. Historical first-release dates remain unknown. POS bulletins are selected by year to prefer consistent retrospective vintages; adjacent YTD snapshots with different raw vintages are withheld from monthly-flow calculations. Growth indices are never de-cumulated.

`repair_metadata.py` addresses an early collector logging race using exact URL hashes and the immutable filename timestamp. Original unavailable HTTP headers remain null. New collectors write separate process logs. The repair must leave zero raw files without mapped source URLs.

Main panel keys use published growth percentage points for real activity, nominal YTD levels for imports/POS/no-gold exports, and nominal monthly levels for the two receipts observations. `_raw_level` preserves the source number. `_monthly_flow`, `_monthly_log_yoy` and `_monthly_pct_yoy` are separate and may remain missing when vintage, positivity or definition checks fail. Historical scope candidates and registry proxies have distinct keys. Consult the recovery report and definition-break table before interpreting any common-sample count.
