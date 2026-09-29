# AGENTS.md — Uzbekistan Nowcasting Database

## 1. Mission

Build a reproducible, auditable, updateable Uzbekistan macroeconomic nowcasting database.

The immediate goal is **not** to build a forecasting model. The immediate goal is to build the data infrastructure that a real-time GDP nowcasting model can safely use.

The authoritative variable registry is:

`registry/uzbekistan_nowcasting_v1_registry.xlsx`

Treat that workbook as the configuration/specification layer for V1.

V1 contains:
- 1 quarterly GDP target;
- 28 monthly/daily predictors;
- official SIAT and Central Bank of Uzbekistan sources where available;
- explicitly documented external/proxy/derived series where needed.

Do not silently override the registry.

---

## 2. Core principles

1. **Official-source first.**
   - Uzbekistan Statistics Agency / SIAT.
   - Central Bank of Uzbekistan / CBU.
   - External series only where the registry explicitly specifies them, e.g. World Bank or Rosstat.
   - Never substitute an unofficial source because it is easier to scrape.

2. **Never fabricate identifiers, endpoints, dates, units, or release lags.**
   - If an endpoint is unavailable or its schema changes, fail visibly.
   - Record the failure in logs.
   - Do not guess a replacement indicator.

3. **Raw data are immutable.**
   - Every downloaded payload/file must be archived before any transformation.
   - Never overwrite an earlier raw vintage.

4. **Preserve provenance.**
   Every raw download must store, at minimum:
   - `variable_key`
   - provider
   - source URL
   - retrieval timestamp
   - source update/release date if observable
   - HTTP status where applicable
   - checksum
   - schema fingerprint / parser version

5. **Prevent look-ahead bias.**
   - Reference period and release/retrieval date are different concepts.
   - Preserve both whenever possible.
   - Never use a value in a historical pseudo-real-time dataset before its observed release date.

6. **GDP remains quarterly.**
   - Never interpolate GDP to monthly frequency.
   - Never forward-fill GDP as if it were observed monthly.
   - Quarterly GDP is the target, not another monthly predictor.

7. **De-cumulate before growth calculations.**
   - YTD cumulative SIAT/CBU flow series must first be converted to monthly flows.
   - Never calculate YoY growth directly from a YTD level when the registry says `DECUM_YTD`.

8. **Do not model yet.**
   - No MIDAS, DFM, bridge equations, ML, or GDP forecasts until the data pipeline has passed validation.

---

## 3. Registry contract

### Workbook

`registry/uzbekistan_nowcasting_v1_registry.xlsx`

Relevant sheets:
- `V1 Registry`
- `Transform Rules`
- `Source Families`
- `Pipeline Contract`
- `README`

### Important workbook detail

In `V1 Registry`, the actual column headers are on **row 4**, not row 1.

Required registry fields include:
- `V1 order`
- `Variable key`
- `Block`
- `Display name`
- `Provider`
- `Native indicator / dataset ID`
- `Dataset/page ID`
- `Row / field selector`
- `Human source URL`
- `Machine/download URL`
- `Native frequency`
- `Verified start`
- `Verified end`
- `Raw unit`
- `Flow / stock type`
- `Cumulative flag`
- `Typical publication lag (days)`
- `Lag basis / release convention`
- `Required transformation`
- `Clean model field`
- `Revision characteristics`
- `Structural breaks / caveats`
- `Model role`
- `Automation status`

### Registry behavior

At runtime:
1. load the registry;
2. normalize column names internally but preserve original labels;
3. validate uniqueness of `Variable key`;
4. validate required fields;
5. validate `Automation status`;
6. route each series to the correct downloader/parser;
7. route transformation logic from the registry / transformation rules.

Do not hard-code all 29 series in one large script.

---

## 4. Project architecture

Use this structure unless a clearly better implementation is required:

```text
uzbekistan-nowcast/
├── AGENTS.md
├── PROJECT_SPEC.md
├── README.md
├── requirements.txt
├── .gitignore
│
├── registry/
│   └── uzbekistan_nowcasting_v1_registry.xlsx
│
├── config/
│   └── settings.yaml
│
├── data/
│   ├── raw/
│   │   ├── siat/
│   │   ├── cbu/
│   │   ├── world_bank/
│   │   └── rosstat/
│   ├── processed/
│   └── master/
│
├── metadata/
│   ├── observations_long.parquet
│   ├── release_calendar.parquet
│   ├── vintages.parquet
│   ├── download_log.parquet
│   └── schema_log.parquet
│
├── logs/
│
├── src/
│   └── uznowcast/
│       ├── __init__.py
│       ├── registry.py
│       ├── provenance.py
│       ├── io/
│       │   ├── __init__.py
│       │   ├── siat.py
│       │   ├── cbu.py
│       │   ├── world_bank.py
│       │   └── rosstat.py
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── siat.py
│       │   └── cbu.py
│       ├── transforms/
│       │   ├── __init__.py
│       │   ├── decumulate.py
│       │   ├── prices.py
│       │   ├── frequency.py
│       │   └── growth.py
│       ├── validation/
│       │   ├── __init__.py
│       │   ├── registry.py
│       │   ├── observations.py
│       │   └── schema.py
│       └── master.py
│
├── tests/
│   ├── test_registry.py
│   ├── test_decumulate.py
│   ├── test_siat_parser.py
│   ├── test_cbu_fx_parser.py
│   ├── test_master.py
│   └── fixtures/
│
└── scripts/
    ├── download_pilot.py
    ├── build_pilot.py
    └── build_v1.py
```

Keep modules small and testable.

---

## 5. Canonical data model

### 5.1 Long observation table

All processed observations should be representable in a canonical long table with fields similar to:

```text
variable_key
reference_period
reference_date
frequency
raw_value
clean_value
unit
transformation
provider
source_id
source_url
source_release_date
retrieved_at
vintage_date
is_preliminary
revision_status
raw_file_path
checksum
parser_version
quality_flag
```

Not every provider exposes every field. Use null where the information genuinely does not exist.

Never invent release dates.

### 5.2 Monthly master table

The modelling-ready V1 monthly table should eventually have:

```text
date
industrial_production_yoy
manufacturing_yoy
mining_yoy
...
usd_uzs_mom
m2_yoy
...
```

Rules:
- one row per calendar month;
- unique month index;
- no duplicate clean variable columns;
- preserve missing values;
- do not fill missing observations unless an explicit rule authorizes it.

### 5.3 Quarterly target table

Keep GDP separately:

```text
quarter
gdp_real_yoy_pct
source_release_date
retrieved_at
vintage_date
revision_status
```

A later modelling layer may align monthly predictors with quarterly GDP, but the ingestion layer must not convert quarterly GDP into fake monthly observations.

---

## 6. Transformation rules

Read `Transform Rules` in the registry and implement named, testable functions.

### DECUM_YTD

For YTD cumulative flows:

```text
January:
monthly_flow_t = YTD_t

February–December:
monthly_flow_t = YTD_t - YTD_(t-1)
```

Critical rule:
- never subtract December of one year from January of the next;
- de-cumulation occurs before YoY growth;
- preserve the original YTD value.

Validation:
- January reset;
- unexpected negative monthly increment;
- extreme month-to-month increments;
- missing previous month;
- duplicate months.

### YoY log growth

Where the registry specifies:

```text
100 * ln(x_t / x_(t-12))
```

Requirements:
- `x_t > 0`
- `x_(t-12) > 0`
- otherwise output null and a quality flag.

### Monthly index inflation

For published previous-month=100 price indices:

```text
monthly_pct = 100 * ln(index / 100)
```

Preserve the raw index.

### Daily FX to monthly

For USD/UZS and RUB/UZS:
1. normalize `Rate / Nominal`;
2. retain daily observations;
3. aggregate to monthly mean;
4. compute:
   `100 * Δln(monthly_mean)`

Positive change means UZS depreciation.

Do not silently use end-of-month if the registry says monthly mean.

---

## 7. Pilot implementation: Phase 2A

Do not implement all V1 variables first.

Prove the architecture using three series that represent different data problems.

### Pilot A — GDP target

Registry key:

`gdp_real_yoy`

Provider:
SIAT

Requirements:
- download from official SIAT endpoint specified in registry;
- parse only the exact Uzbekistan GDP row/dimensions specified;
- keep frequency quarterly;
- published index/growth convention must follow registry;
- output clean field:
  `gdp_real_yoy_pct`
- never monthly-interpolate.

### Pilot B — Industrial production

Registry key:

`industrial_production`

Provider:
SIAT

Requirements:
- download official SIAT payload;
- parse correct national row;
- confirm YTD cumulative structure;
- de-cumulate within calendar year;
- preserve YTD and monthly flow;
- compute registry-specified YoY log growth;
- flag negative/non-positive flows.

### Pilot C — USD/UZS

Registry key:

`usd_uzs`

Provider:
CBU

Requirements:
- use official CBU endpoint specified in registry;
- preserve daily raw exchange-rate data;
- normalize quoted value by nominal;
- calculate monthly mean;
- calculate monthly log change;
- preserve exact retrieval timestamp and source URL.

---

## 8. Pilot outputs

A successful Phase 2A must produce at least:

```text
data/raw/...
data/processed/gdp_real_yoy.parquet
data/processed/industrial_production.parquet
data/processed/usd_uzs.parquet

data/master/pilot_monthly.parquet
data/master/pilot_monthly.xlsx
data/master/gdp_quarterly.parquet
data/master/gdp_quarterly.xlsx

metadata/download_log.parquet
metadata/vintages.parquet
logs/pipeline.log
```

The monthly pilot table should contain industrial production and USD/UZS only.

GDP stays in the quarterly target table.

---

## 9. Phase 2B pilot expansion

Only after Phase 2A passes tests, expand to the eight-series pilot:

1. `gdp_real_yoy`
2. `industrial_production`
3. `construction`
4. `cpi_headline`
5. `exports_total`
6. `imports_total`
7. `usd_uzs`
8. `m2`

This set should test:
- quarterly target;
- monthly YTD real activity;
- price index;
- YTD trade values;
- daily-to-monthly FX;
- monthly monetary stock.

After the eight-series pilot passes, expand systematically to the remaining V1 registry.

---

## 10. Automation-status routing

Respect the registry's `Automation status`.

Expected statuses include:

### `READY_API`
Use a stable official machine endpoint.

### `READY_PAGE`
Use the stable official page/table parser when a complete API is not available.

### `ARCHIVE_SPIDER`
Historical data require iteration over date-stamped official archive pages/files.

Rules:
- archive every source file;
- do not assume the latest snapshot contains history;
- store archive date / as-of date;
- detect duplicate releases;
- never overwrite previous vintage.

### `DERIVED`
Do not download directly.
Compute from already ingested parent series.

Example:
`exports_non_gold`

### `PROXY`
Preserve the proxy label in metadata.
Never rename it to imply it is a conceptually exact measure.

Example:
`gold_exports_proxy`

### `EXTERNAL`
Use only the external provider explicitly specified by the registry.

---

## 11. Revision and vintage policy

Revisions are a feature of macroeconomic data, not an error.

Whenever the same:
- `variable_key`
- `reference_period`

is retrieved again with a changed value:

1. do not overwrite the old observation;
2. store the new value as a new vintage;
3. calculate and record the revision;
4. preserve both retrieval dates;
5. mark whether this was a normal revision or a suspected schema/parser problem.

Create a revision comparison utility.

Future pseudo-real-time datasets must be constructed using the latest vintage actually available by a requested historical date.

---

## 12. Release-date policy

Three dates must not be conflated:

- `reference_period` — the month/quarter the statistic describes;
- `source_release_date` — when the provider says it was released/updated, if known;
- `retrieved_at` — when our pipeline actually downloaded it.

If release date is unknown:
- store null;
- preserve retrieval timestamp;
- never back-fill a made-up release date from the registry's typical lag.

The registry's `Typical publication lag (days)` is planning metadata, not a substitute for an observed release date.

---

## 13. Validation rules

Every run must validate:

### Registry
- unique `Variable key`;
- expected headers;
- valid frequency;
- non-empty provider;
- source path/URL available when required;
- recognized automation status;
- recognized transformation.

### Raw download
- HTTP success;
- non-empty payload;
- content type plausible;
- checksum computed;
- raw file saved;
- schema fingerprint recorded.

### Parsed observation
- valid date/period;
- numeric values where expected;
- no unexplained duplicates;
- national aggregate selected correctly;
- units consistent with registry.

### Time series
- sorted periods;
- duplicate period detection;
- missing-period report;
- negative-value checks where economically impossible;
- structural-break warning;
- extreme-change warning;
- start/end coverage report.

### Transformations
- YTD reset validation;
- no Dec→Jan de-cumulation;
- log-growth positivity checks;
- daily FX monthly aggregation checks.

### Master dataset
- unique monthly index;
- no duplicate columns;
- deterministic column order;
- variable names equal registry clean fields;
- GDP absent from monthly table;
- data types stable.

A validation warning may allow completion when appropriate.
A source/schema failure must not be silently swallowed.

---

## 14. Logging

Use structured logs.

Each download should record:

```text
run_id
variable_key
provider
source_url
retrieved_at
status
http_status
raw_file
checksum
rows_raw
rows_parsed
schema_fingerprint
warning_count
error_message
```

Make logs useful for monthly operations.

Do not use `print()` as the main logging system.

---

## 15. Error handling

Retry only errors that are plausibly temporary:
- timeout;
- connection reset;
- HTTP 429;
- HTTP 5xx.

Use bounded retries with backoff.

Do not retry forever.

For:
- HTTP 404;
- missing expected table;
- changed schema;
- unknown dimensions;
- unit mismatch;

fail that series clearly and preserve the error context.

A partial pipeline run may save successful series, but the final V1 build must state which series failed.

---

## 16. Networking etiquette

- identify the client with a sensible User-Agent;
- use reasonable timeouts;
- rate-limit archive spiders;
- cache raw downloads;
- do not repeatedly request the same file during one run;
- respect official provider infrastructure.

---

## 17. Testing requirements

Use `pytest`.

Minimum tests for Phase 2A:

### Registry
- loads row-4 headers correctly;
- `Variable key` unique;
- pilot keys exist;
- transformations/statuses recognized.

### De-cumulation
Test:
- normal Jan→Mar;
- Dec→Jan reset;
- missing previous month;
- negative increment;
- duplicate month.

### SIAT parser
Use a frozen fixture.
Test exact row/dimension filtering.

### CBU FX parser
Use a frozen fixture.
Test:
- nominal normalization;
- date parsing;
- monthly mean;
- duplicate daily values.

### Master builder
Test:
- unique monthly date;
- GDP not merged as fake monthly data;
- expected pilot column names;
- deterministic result.

No network calls in unit tests.

---

## 18. Reproducibility

Pin dependencies after the first successful environment build.

Provide a single command for pilot execution, e.g.:

```bash
python -m scripts.download_pilot
python -m scripts.build_pilot
```

or preferably one CLI entry point:

```bash
python -m uznowcast.cli build --scope pilot
```

A new machine should be able to clone the repository, install dependencies, and reproduce the processed outputs from official sources.

Do not depend on notebook state.

Notebooks may be used for exploration, not as the production pipeline.

---

## 19. Git policy

Commit:
- source code;
- registry;
- tests;
- small fixtures;
- documentation.

Do not normally commit:
- large raw downloads;
- generated processed datasets;
- credentials;
- local environment files;
- logs.

Recommended `.gitignore` entries include:

```text
.venv/
__pycache__/
.pytest_cache/
*.pyc
.env
data/raw/
data/processed/
data/master/
logs/
```

If reproducibility requires selected raw fixtures, store small sanitized/frozen copies under `tests/fixtures/`.

---

## 20. Credentials and secrets

The current V1 official sources should not require private credentials.

If credentials are later required:
- use environment variables;
- never commit secrets;
- never put credentials in the registry;
- never print secrets to logs.

---

## 21. Coding style

Target Python 3.11+.

Prefer:
- `pathlib`
- type hints
- small pure transformation functions
- `pandas` for tabular processing
- `requests` or `httpx` for HTTP
- `openpyxl` only where Excel-specific handling is needed
- `pyarrow`/Parquet for machine datasets
- `pytest` for tests

Functions should have clear inputs/outputs and docstrings where logic is non-obvious.

Avoid giant monolithic scripts.

---

## 22. Documentation rule

When implementation reveals a source characteristic not already captured in the registry:
1. document the finding;
2. do not silently change the conceptual series;
3. propose the registry correction;
4. make the code robust to the confirmed behavior.

The registry remains the authoritative specification until deliberately amended.

---

## 23. Definition of done — Phase 2A

Phase 2A is complete only when all of the following are true:

- registry loader works;
- official source downloaders work for the 3 pilot series;
- raw payloads are archived;
- checksums/provenance are stored;
- GDP parses correctly as quarterly;
- industrial production is de-cumulated correctly;
- USD/UZS daily data aggregate correctly to monthly;
- clean Parquet files are produced;
- `pilot_monthly.xlsx` and `.parquet` are produced;
- `gdp_quarterly.xlsx` and `.parquet` are produced;
- validation report is produced;
- unit tests pass;
- re-running the pipeline is deterministic except for new source vintages;
- no GDP interpolation occurs;
- no source IDs or release dates are guessed.

---

## 24. Definition of done — Phase 2B

Phase 2B is complete when the 8-series pilot:
- downloads from official sources;
- cleans successfully;
- implements all relevant transformation classes;
- passes validation;
- produces a coherent monthly master;
- preserves GDP quarterly;
- captures release/retrieval metadata;
- supports a clean re-run from scratch.

Only after this should implementation expand to all V1 variables.

---

## 25. Current priority

Start with Phase 2A only.

Do **not** expand to all 29 variables during the first implementation pass.

Recommended sequence:

1. inspect registry programmatically;
2. create project skeleton;
3. implement registry loader + validation;
4. implement provenance/raw storage utilities;
5. implement SIAT generic downloader;
6. implement CBU FX downloader;
7. implement GDP parser;
8. implement industrial-production parser;
9. implement YTD de-cumulation;
10. implement daily-FX monthly aggregation;
11. build pilot outputs;
12. add tests;
13. run full pilot;
14. report failures, warnings, coverage and next steps.

Do not begin forecasting-model code.
