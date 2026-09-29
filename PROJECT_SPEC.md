# PROJECT_SPEC.md — Uzbekistan Nowcasting Database V1

## 1. Objective

Create a production-style macroeconomic data pipeline for GDP nowcasting in Uzbekistan.

The system will automatically:
1. read the V1 variable registry;
2. retrieve source data;
3. archive raw vintages;
4. parse and standardize observations;
5. apply registry-defined transformations;
6. validate data quality;
7. preserve release/retrieval metadata;
8. construct a master monthly predictor panel;
9. keep quarterly GDP as a separate target dataset.

This document describes **Phase 2: database construction**.

Forecasting/nowcasting models belong to a later phase.

---

## 2. Authoritative registry

File:

`registry/uzbekistan_nowcasting_v1_registry.xlsx`

Version in supplied workbook:

`V1.0 — verified 2026-09-29`

Scope:
- 29 total variables;
- 1 quarterly GDP target;
- 28 monthly/daily predictors.

The workbook contains five sheets:
- `V1 Registry`
- `Transform Rules`
- `Source Families`
- `Pipeline Contract`
- `README`

The registry is the source of truth for series IDs, URLs, transformations, frequency, units, cumulative status, model role and automation strategy.

---

## 3. V1 variable catalogue

### Target

1. `gdp_real_yoy`

### Real activity

2. `industrial_production`
3. `manufacturing`
4. `mining`
5. `electricity_gas`
6. `construction`
7. `retail_trade`
8. `wholesale_trade`

### Prices

9. `cpi_headline`
10. `cpi_food`
11. `cpi_services`
12. `ppi`

### External trade

13. `exports_total`
14. `exports_non_gold`
15. `imports_total`
16. `gold_exports_proxy`

### FX / external drivers

17. `usd_uzs`
18. `rub_uzs`
19. `gold_price`
20. `russia_ipi`

### Money / banking

21. `m2`
22. `household_deposits`
23. `corporate_deposits`
24. `household_credit`
25. `corporate_credit`
26. `fx_reserves_ex_gold`

### Payments

27. `pos_turnover`
28. `instant_payments`
29. `interbank_payments`

---

## 4. Source strategy

### SIAT

Primary use:
- GDP;
- activity;
- prices;
- trade.

Where the registry marks `READY_API`, use the official machine endpoint.

Raw SIAT payloads must be archived.

Important SIAT issue:
many activity/trade series are YTD cumulative even though they are released monthly.

Therefore:

**download → parse YTD → de-cumulate → calculate monthly growth**

Never:

**download YTD → calculate monthly growth directly**

---

### Central Bank of Uzbekistan

Primary use:
- exchange rates;
- monetary aggregates;
- reserves;
- banking balances;
- payment-system indicators.

Source classes may include:
- stable API;
- stable official data page;
- official monthly archive files.

For `ARCHIVE_SPIDER` variables, build historical retrieval from official date-stamped pages/files rather than treating a current snapshot as a historical API.

---

### External sources

Only two external families are currently part of V1:
- World Bank Pink Sheet for gold price;
- Rosstat for Russian industrial production.

They are not part of Phase 2A.

---

## 5. Data layers

### Layer 0 — registry

Static configuration/specification.

### Layer 1 — raw

Exact downloaded data.

Example:

```text
data/raw/siat/industrial_production/2026-09-29T101501Z.json
data/raw/cbu/usd_uzs/2026-09-29T101606Z.json
```

Raw files are immutable.

### Layer 2 — standardized observations

Provider-specific payloads converted to the canonical observation schema.

No modelling transformation should destroy the raw value.

### Layer 3 — transformed series

Examples:
- YTD → monthly flow;
- daily FX → monthly mean;
- level → YoY log growth;
- price index → monthly inflation.

### Layer 4 — master datasets

`master_monthly`
- monthly predictors only.

`gdp_quarterly`
- quarterly target only.

### Layer 5 — future real-time vintages

A future phase will reconstruct the information set available on any historical date.

The Phase 2 pipeline must preserve enough metadata to make this possible.

---

## 6. Core schemas

### Raw download metadata

```text
run_id
variable_key
provider
source_id
source_url
retrieved_at
source_release_date
http_status
content_type
raw_file_path
checksum_sha256
schema_fingerprint
parser_version
```

### Canonical observation

```text
variable_key
reference_period
reference_date
frequency
raw_value
raw_unit
clean_value
clean_unit
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
checksum_sha256
quality_flag
```

### Revision table

```text
variable_key
reference_period
old_value
new_value
old_vintage_date
new_vintage_date
absolute_revision
relative_revision
revision_type
```

---

## 7. Phase 2A — three-series architecture pilot

### Why three series

These three cover the principal engineering problems before expanding:

| Series | Frequency | Source | Main challenge |
|---|---|---|---|
| `gdp_real_yoy` | Quarterly | SIAT | quarterly target / revisions |
| `industrial_production` | Monthly | SIAT | YTD de-cumulation |
| `usd_uzs` | Daily | CBU | daily-to-monthly aggregation |

If these run end-to-end, the architecture is sufficiently tested to add the next five pilot variables.

---

## 8. Phase 2A transformations

### GDP

Registry instruction:

- keep quarterly;
- convert the published index convention to growth rate according to registry;
- do not interpolate.

Expected clean field:

`gdp_real_yoy_pct`

### Industrial production

Registry instruction:

1. preserve YTD raw series;
2. de-cumulate within each calendar year;
3. compute:
   `100 * ln(monthly_flow_t / monthly_flow_t-12)`;
4. flag non-positive flows.

### USD/UZS

Registry instruction:

1. download daily official rates;
2. normalize `Rate / Nominal`;
3. aggregate to monthly mean;
4. calculate:
   `100 * Δln(monthly_mean)`;
5. positive = UZS depreciation.

---

## 9. Phase 2A expected output

### `pilot_monthly`

Minimum columns:

```text
date
industrial_production_yoy
usd_uzs_mom
```

Depending on implementation, additional diagnostic raw/level columns may exist in processed files, but the master should contain the registry-defined clean model fields.

### `gdp_quarterly`

```text
quarter
gdp_real_yoy_pct
```

Plus available vintage/release metadata.

---

## 10. Phase 2B — eight-series pilot

After Phase 2A passes:

1. `gdp_real_yoy`
2. `industrial_production`
3. `construction`
4. `cpi_headline`
5. `exports_total`
6. `imports_total`
7. `usd_uzs`
8. `m2`

This validates all major transformation families needed for most of V1.

---

## 11. Final V1 build

Once the eight-series pilot is stable, implement the remaining registry entries by automation class.

Recommended order:

### Group 1 — additional SIAT API
- manufacturing
- mining
- electricity/gas
- retail
- wholesale
- CPI subcomponents
- PPI
- trade/proxy components

### Group 2 — stable CBU API/page
- RUB/UZS
- reserves
- other stable monetary pages

### Group 3 — CBU archive spiders
- household deposits
- corporate deposits
- household credit
- corporate credit
- POS turnover
- instant payments
- interbank payments

### Group 4 — external
- gold price
- Russia IPI

### Group 5 — derived
- non-gold exports

---

## 12. Quality-control philosophy

The pipeline should prefer a visible missing value to a plausible but invented value.

Do not:
- interpolate missing macro data silently;
- substitute a similar indicator;
- change units without documentation;
- repair a structural break using an arbitrary coefficient;
- ignore a changed provider schema;
- overwrite revised historical data.

Do:
- preserve raw observations;
- create flags;
- log exceptions;
- expose coverage gaps;
- retain old vintages.

---

## 13. Look-ahead-bias requirements

A nowcasting database is not just a historical matrix.

For each observation, distinguish:
- when the economic activity occurred;
- when the statistic was released;
- when the pipeline retrieved it.

This matters because a model evaluated using final revised history can appear much better than it would have been in real time.

The pipeline should be built so that a later function can answer:

> “What values would have been available to a forecaster on date X?”

Phase 2 does not yet need to implement the full pseudo-real-time engine, but its metadata must make this possible.

---

## 14. Technology

Recommended:
- Python 3.11+
- pandas
- pyarrow
- requests or httpx
- openpyxl
- beautifulsoup4/lxml where official HTML parsing is needed
- tenacity or equivalent bounded retry utility
- pytest
- pydantic optional for configuration/schema validation

Primary machine format:
- Parquet.

Human review/export format:
- XLSX.

Do not use XLSX as the only persisted database format.

---

## 15. First Codex implementation task

Codex should:

1. read `AGENTS.md`;
2. inspect the registry programmatically;
3. create the package/project skeleton;
4. implement a registry loader;
5. validate the registry;
6. implement raw-file/provenance storage;
7. implement SIAT downloader support needed for:
   - `gdp_real_yoy`
   - `industrial_production`
8. implement CBU support for:
   - `usd_uzs`
9. add transformation utilities;
10. add unit tests with frozen fixtures;
11. run the Phase 2A pilot;
12. produce:
   - processed series;
   - monthly pilot master;
   - quarterly GDP target;
   - validation report;
   - download/vintage metadata;
13. report any source/schema discrepancy instead of guessing.

---

## 16. Acceptance criteria

Phase 2A passes only if:

- [ ] registry loads correctly from row 4;
- [ ] variable keys are unique;
- [ ] raw downloads are retained;
- [ ] source URLs are logged;
- [ ] checksums are calculated;
- [ ] SIAT GDP parses correctly;
- [ ] GDP stays quarterly;
- [ ] industrial YTD values de-cumulate correctly;
- [ ] industrial YoY growth uses monthly flow;
- [ ] daily CBU FX rates normalize correctly;
- [ ] FX monthly mean is reproducible;
- [ ] FX log change is reproducible;
- [ ] master monthly date is unique;
- [ ] quarterly GDP table date is unique;
- [ ] revisions do not overwrite old vintages;
- [ ] unit tests pass;
- [ ] no network access occurs in unit tests;
- [ ] failed schemas produce explicit errors;
- [ ] no fabricated metadata exists.

---

## 17. What comes after Phase 2

Once all V1 data are stable:

### Phase 3 — exploratory/release analysis
- coverage;
- missingness;
- correlations;
- lag structure;
- revision behavior;
- release calendar;
- ragged edge.

### Phase 4 — benchmark nowcasting models
- naive / autoregressive GDP benchmarks;
- bridge equations;
- MIDAS;
- dynamic factor model.

### Phase 5 — pseudo-real-time evaluation
- historical information sets;
- nowcast horizons;
- RMSFE/MAE;
- revision-aware evaluation.

### Phase 6 — dashboard/panel
- current-quarter nowcast;
- contributions/drivers;
- latest releases;
- surprises;
- historical nowcast path;
- uncertainty bands;
- database freshness/status.

The database comes first.
