# Uzbekistan Nowcasting Database — Phase 2B

Registry-driven data infrastructure for quarterly GDP and seven monthly predictors:
industrial production, construction, headline CPI, exports, imports, USD/UZS and M2.
No forecasting models or remaining V1 variables are included. The workbook in `registry/`
remains unchanged and authoritative.

## Install and run

Python 3.11+ is required; the pinned environment was tested on Python 3.12.10 / Windows.
Run commands from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uznowcast.cli build --scope pilot8
```

On macOS/Linux use `.venv/bin/python` instead.

The default build uses checksum-verified cached payloads and downloads missing URLs.
The initial CBU history bootstrap is sequential and can take tens of minutes. It starts
in January 2013, as specified in the workbook, and walks backward from today's date
through official activation dates. Interrupted runs resume from the immutable cache.

```powershell
# Reproduce archived payloads without network access:
.\.venv\Scripts\python.exe -m uznowcast.cli build --scope pilot8 --offline --fx-end 2026-09-29

# Compare all eight output tables, vintage rows and raw-file hashes against a replay:
.\.venv\Scripts\python.exe -m scripts.verify_pilot_replay

# Download fresh vintages, including revisions at existing URLs:
.\.venv\Scripts\python.exe -m uznowcast.cli build --scope pilot8 --refresh

# Explicitly restrict FX history for a smoke build:
.\.venv\Scripts\python.exe -m uznowcast.cli build --scope pilot8 --fx-start 2026-06-01 --fx-end 2026-09-29
```

Use `--refresh` for source updates: cached reruns do not discover revisions at existing
URLs. Offline replay should specify the original FX end date, otherwise the default
advances with today's date. An uncached date fails visibly. Date overrides are recorded
in the run report. `--offline` and `--refresh` are mutually exclusive.

The CLI returns nonzero for any series/build failure. Inspect
`metadata/validation_summary.json` after every run. Successful processed series can
be saved during a partial failure, but masters are not promoted. Any existing master
belongs to the run in `data/master/build_manifest.json`.

## Outputs

| Location | Contents |
|---|---|
| `data/raw/{provider}/{variable}/` | Immutable payloads and JSON sidecars, including failed HTTP bodies |
| `data/processed/gdp_real_yoy.parquet` | Published quarterly index, index minus 100, provenance |
| `data/processed/industrial_production.parquet` | Original YTD, monthly flows, YoY log growth and flags |
| `data/processed/construction.parquet` | Original YTD, reconstructed monthly flows, YoY log growth and flags |
| `data/processed/cpi_headline.parquet` | Previous-month=100 source index and monthly log inflation |
| `data/processed/exports_total.parquet` | Original YTD USD values, monthly flows and YoY log growth |
| `data/processed/imports_total.parquet` | Original YTD USD values, monthly flows and YoY log growth |
| `data/processed/usd_uzs_daily.parquet` | Activation-date quotes, nominal and normalized rates |
| `data/processed/usd_uzs.parquet` | Monthly means, counts, log changes and input lineage |
| `data/processed/m2.parquet` | CBU DCS broad-money EOP level and YoY log growth |
| `data/master/pilot8_monthly.{parquet,xlsx}` | Seven clean predictors plus explicit FX completeness/quality fields |
| `data/master/gdp_quarterly.{parquet,xlsx}` | Separate target and vintage/release metadata |
| `metadata/observations_long.parquet` | Canonical observations preserving retrieval vintages |
| `metadata/vintages.parquet` | Retrieval-vintage/source-file catalogue |
| `metadata/revisions.parquet` | Created when changed values are observed; revision comparisons |
| `metadata/download_log.parquet` | Download/cache/parser events and errors |
| `metadata/schema_log.parquet` | Raw schema fingerprints |
| `metadata/release_calendar.parquet` | Observed update/retrieval dates, never lag estimates |
| `metadata/validation_summary.json` | Latest coverage, warnings, failures and reconciliation |
| `metadata/runs/` | Immutable run reports |
| `logs/pipeline.log` | Operational download/error records |

Generated data, metadata, logs and the environment are Git-ignored. Code, configuration,
the source workbook, documentation and small frozen fixtures are versioned.

## Data conventions

- Headers are read from row 4. All 29 registry rows are validated; only the eight Phase 2B
  series execute. Original labels are retained. Reviewed prose transformations are mapped in
  `config/registry_contracts.json`; changes fail until reviewed.
- Both SIAT descriptors and linked files are archived. Exact row codes/labels, indicator
  IDs, units, periods and frequency are checked against `config/siat_contracts.json`.
- GDP remains quarterly, using index minus 100 without interpolation or de-cumulation.
  The pipeline does not claim to reconstruct standalone-quarter growth.
- January industrial flow equals January YTD. Later months require the preceding
  calendar month in the same year. YoY compares monthly flows. Complete years reconcile
  to December YTD.
- Construction, exports and imports use the same within-year YTD de-cumulation before YoY
  growth. CPI applies `100*ln(index/100)` to the published previous-month=100 index.
- M2 resolves the current DCS workbook from the registry's official CBU page, preserves
  the exact `Broad money liabilities` EOP stock and applies 12-month log growth.
- CBU `Date` is activation, not release. Each distinct activation contributes once to
  the monthly mean. No synthetic calendar days are generated; conflicting duplicates fail.
- Incomplete FX months retain their means and flags but have null clean changes. A
  subsequent month cannot use an incomplete previous month as a full-period comparator.
- Missing values remain missing. Initial growth lags are unavailable by construction.
  Large growth and monthly-flow changes are warnings, not arbitrary adjustments.
- SIAT update dates are labelled as dataset updates, not historical first releases.
  CBU release dates are null. `available_asof` gates on retrieval as well as known
  releases; it cannot reconstruct unobserved first-release history.
- FX changes carry lineage from both monthly means. Multiple URLs/files/checksums are
  JSON lists inside the corresponding provenance fields.

## Implementation and checks

`registry.py` validates configuration; `io/` downloads; `parsers/` verifies source
schemas; `transforms/` contains calendar-aware functions; `master.py` separates targets
from predictors. `pipeline.py` orchestrates both pilot scopes. `vintages.py` preserves previous
observations and compares changed raw and clean values.

HTTP requests have bounded timeouts, three attempts for connection/timeouts/429/5xx,
a research User-Agent and a configurable pause. Other errors are not retried. Raw bytes
are saved before content validation. Cache reads verify checksums. Structural fingerprints
ignore added period columns and changed values; parser contracts reject unsupported schemas.

Tests explicitly block network calls. They cover registry errors, exact row selection,
nominal normalization, calendar alignment, de-cumulation, duplicate dates, immutability,
retry policy, revision gating, master isolation and deterministic full-build replay.
Synthetic numerical edge cases are test-only.

Run one build writer at a time. Output replacement is not a transaction across all files.
See [Phase 2B live results](docs/phase2b_results.md),
[registry recommendations](docs/phase2b_registry_recommendations.md), and the retained
[Phase 2A results](docs/phase2a_results.md).
