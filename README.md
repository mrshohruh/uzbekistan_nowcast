# Uzbekistan Nowcasting Database

## Current production state

- **Target:** 2026Q3, operational stage **H2**
- **Nowcast:** **7.6239786595896035%**
- **Model:** 0.5 × AR(2) + 0.5 × USD/UZS U-MIDAS(3)
- **Latest official GDP:** 2026Q2 = 8.5% YoY
- **Frozen through:** Phase 5B.1
- **Canonical current outputs:** [`results/production/`](results/production/) and [`dashboard/current/uzbekistan_nowcast.html`](dashboard/current/uzbekistan_nowcast.html)
- **Historical archives:** kept in place — `results/phase4*_*`, `results/phase5b/`, `results/phase5b1/`, `dashboard/phase5*_uzbekistan_nowcast.html` (see [`results/archive/README.md`](results/archive/README.md))

See [`PROJECT_STATE.md`](PROJECT_STATE.md) for the operator status page and [`docs/PROJECT_HISTORY.md`](docs/PROJECT_HISTORY.md) for the phase-by-phase history.

## Quick start

1. **Environment.** Python 3.11+; pinned on 3.12.10 (Windows).
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m pip install -e . --no-deps
   ```
2. **Tests.**
   ```powershell
   .\.venv\Scripts\python.exe -m pytest
   ```
3. **Ingestion (offline replay from cached raw payloads).**
   ```powershell
   .\.venv\Scripts\python.exe -m uznowcast.cli build --scope pilot8 --offline --fx-end 2026-09-29
   ```
   Use `--refresh` (mutually exclusive with `--offline`) to hit official sources and discover revisions.
4. **Operational nowcast (Phase 5A entry point; Phase 5B.1 module used for the frozen headline).**
   ```powershell
   .\.venv\Scripts\python.exe -m uznowcast.operational --as-of-date 2026-09-30
   ```
5. **Outputs.** Ingestion writes to `data/{raw,processed,master}/`. The current operational headline is at `results/production/current_nowcast.json` and the current dashboard is `dashboard/current/uzbekistan_nowcast.html`. Historical phase outputs remain under `results/phase4*_*`, `results/phase5b/`, `results/phase5b1/`.
6. **Status codes.** `SUCCESS` = every gate green; `SUCCESS_WITH_WARNINGS` = the run completed but at least one non-blocking warning was raised (data-quality AMBER, publication-readiness blocker, or model-monitoring flag). The Phase 5B.1 publication gate additionally blocks official publication when the git working tree is dirty.
7. **Frozen historical results.** Phase 4A → Phase 5B.1 evidence is immutable; the file list is in `results/phase5b2/protected_artifact_manifest_before.csv` and every hash was re-verified after Phase 5B.2 (see `results/phase5b2/protected_artifact_hash_comparison.csv`).

---

## Legacy Phase 2B documentation

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

## Phase 2C / 2C.1 / 3B

Phase 2C attempted all 29 V1 series, kept the panel ragged, and produced live
per-variable coverage in [`docs/phase2c_results.md`](docs/phase2c_results.md) and
recommendations in [`docs/phase2c_registry_recommendations.md`](docs/phase2c_registry_recommendations.md).
Phase 2C.1 diagnosed the Rosstat `russia_ipi` TLS failure and left it unresolved
under a documented `UZNOWCAST_USE_SYSTEM_TRUST=1` opt-in path
([`docs/phase2c1_results.md`](docs/phase2c1_results.md)).

Phase 3B applied the approved source-maintenance corrections into
[`registry/uzbekistan_nowcasting_v1.2_registry.xlsx`](registry/uzbekistan_nowcasting_v1.2_registry.xlsx)
(V1.0 and V1.1 are archived under `registry/archive/`), audited the sparse
banking/payment series, diagnosed the June-2026 negative `gold_exports_proxy`
flow, and defined model-readiness tiers. Highlights:

- [Phase 3B results](docs/phase3b_results.md)
- [Model-readiness tiers](docs/model_readiness_tiers.md)
- [Historical extension audit](docs/historical_extension_audit.md)
- [Sparse-series audit](docs/sparse_series_audit.md)
- [Gold-proxy diagnostic](docs/gold_proxy_diagnostic.md)
- [Registry changelog](registry/CHANGELOG.md)

### Prospective vintage collection

`python -m uznowcast.cli collect-vintage --root <checkout>` runs the standard
V1 build with `refresh=True`, preserving every earlier vintage, checksumming
each payload, and writing an immutable per-run summary to
`metadata/vintage_runs/{collector_run_id}.json` (plus a mirror at
`metadata/vintage_collection_latest.json`). The command never overwrites raw
files, never modifies the OS trust store, and never installs a scheduler.
See [`docs/phase3b_results.md`](docs/phase3b_results.md) §10 for the Windows
Task Scheduler instructions the operator runs manually.
