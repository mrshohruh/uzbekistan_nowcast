# Phase 2B implementation and live-run results

Completed on 29 September 2026 using the supplied, unchanged registry. The eight-series
pilot is implemented; no remaining V1 variables and no forecasting/nowcasting models were
added.

## Result

- Full eight-series build: **passed with documented warnings**; no final source, download,
  parser or schema failures.
- Offline tests: **62 passed** in 24.68 seconds. Tests prohibit network calls and use frozen
  official-source fixtures.
- Dependency check: **no broken requirements**.
- Offline artifact replay: **passed**. All 13 processed/master artifacts matched exactly,
  all **3,691 raw files/sidecars** were unchanged, and all **2,678 observation-vintage rows**
  remained unchanged.
- Successful source build: `49e0fc513ccc446e83615114cdfadf9e`.
- Verified replay: `a0d03da0382548e3a47ae104cc3380d6`, completed at
  `2026-09-29T06:33:57.592750+00:00`.
- The replay created no duplicate vintages and no revision records. Raw archives remain
  immutable.

Machine-readable evidence is in `metadata/validation_summary.json`,
`metadata/replay_verification.json`, `metadata/industrial_production_outliers.parquet` and
the immutable reports under `metadata/runs/`.

## Actual parsed coverage

This is downloaded/parsed coverage, not copied registry coverage.

| Variable | First observation | Last observation | Frequency | Missing source periods | Warnings |
|---|---|---|---|---:|---|
| `gdp_real_yoy` | 2018 Q1 | 2026 Q2 | Quarterly | 0 | Quarterly published index minus 100; no interpolation; first-release history unavailable. |
| `industrial_production` | 2019-01 | 2026-07 | Monthly YTD/flow | 0 | First 12 growth values unavailable; 2 extreme log-growth warnings; 0 non-positive flows. |
| `construction` | 2021-01 | 2026-08 | Monthly YTD/flow | 0 | First 12 growth values unavailable; 7 extreme growth and 5 extreme increment flags (overlapping); 0 non-positive flows; source marks data preliminary. |
| `cpi_headline` | 2021-01 | 2026-08 | Monthly index | 0 | No transformation flags; official formula/method break in 2026 retained. |
| `exports_total` | 2021-01 | 2026-08 | Monthly YTD/flow | 0 | First 12 growth values unavailable; 17 extreme growth warnings consistent with lumpy nominal exports; 0 non-positive flows. |
| `imports_total` | 2021-01 | 2026-08 | Monthly YTD/flow | 0 | First 12 growth values unavailable; 1 extreme growth warning; 0 non-positive flows. |
| `usd_uzs` | 2013-01 | 2026-09 | Daily inputs / monthly output | 0 monthly | Initial monthly change unavailable; September 2017 structural-break warning; September 2026 partial month retained with null clean change. |
| `m2` | 2013-01 | 2026-08 | Monthly EOP stock | 0 | First 12 YoY growth values unavailable; no non-positive stock or growth-input flags. |

All complete YTD calendar years reconcile exactly: the sum of reconstructed monthly flows
equals December YTD. January is never differenced against the preceding December. Missing
values and initial transformation lags remain explicit.

## Transformation verification

### Construction and trade

The exact official Uzbekistan row is code `1700`. Within each year, the published values
rise cumulatively and reset in January. The pipeline preserves `raw_value` as the published
YTD value, calculates `monthly_flow` only against the preceding month of the same year, and
then calculates `100 * ln(flow_t / flow_t-12)` where both flows are positive. No construction,
export or import flow is non-positive in this vintage.

### CPI

The source is explicitly a previous-month comparison, not a year-on-year CPI series. The
official code `1` row is preserved as the raw index and transformed as
`100 * ln(index / 100)`. The source note says COICOP-2018 applies from January 2021, the
modified Laspeyres/Lowe formula applied before 2026, and a modified arithmetic Young formula
applies from 2026. That methodological break is documented and not adjusted.

### M2

The current official DCS workbook's exact `Broad money liabilities` row is parsed in
`billion sum, end of period`. The clean field is `100 * ln(level_t / level_t-12)`. The
workbook has 164 contiguous monthly observations and 152 usable growth observations. The
official page update timestamp, `2026-09-25T09:40:00+05:00`, is captured; it is not treated
as each historical observation's original release date.

## Industrial-production outlier diagnostics

The current processed source contains **two** industrial growth values beyond the configured
absolute 50-point threshold. The request's “three” corresponds to the two industrial warnings
plus the separate September 2017 FX warning; there is no third flagged industrial month in
the retained Phase 2A/2B source.

| Month | Raw YTD | Previous-month raw YTD | Reconstructed flow | t−12 raw YTD | t−13 raw YTD | t−12 flow | Growth |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2024-09 | 629,171.5 | 505,790.5 | 123,381.0 | 459,919.7 | 400,618.4 | 59,301.3 | 73.264590 |
| 2026-07 | 795,447.4 | 637,205.9 | 158,241.5 | 575,601.4 | 488,532.3 | 87,069.1 | 59.742029 |

Both observations are genuine published source-flow spikes. Their t−12 flows are consistent
with adjacent months, so the warnings are not denominator base effects. Inputs are positive,
the row selector and calendar subtraction are exact, complete years reconcile, and adjacent
months do not show a sustained break. No retained raw-vintage change supports a source-revision
explanation. The values remain unchanged—no capping, smoothing, replacement or deletion.

## Monthly master and cross-series alignment

`data/master/pilot8_monthly` has **165 unique monthly rows × 10 columns**:

```text
date
ind_prod_yoy_log
construction_yoy_log
cpi_headline_mom_log
exports_total_yoy_log
imports_total_yoy_log
usd_uzs_mom_dlog
m2_yoy_log
usd_uzs_is_complete
usd_uzs_quality_flag
```

GDP is absent and remains in a separate 34-row quarterly table.

- Earliest month with all seven clean predictors: **January 2022**.
- Latest complete month with all seven predictors: **July 2026**.
- Complete monthly rows: **55**.
- Missing clean values over the 165-month union: industrial production 86; construction 109;
  CPI 97; exports 109; imports 109; USD/UZS 2; M2 13.
- August 2026 lacks industrial production but has the other six predictors.
- September 2026 contains only an incomplete USD/UZS monthly mean; its clean change and all
  other predictor values are null.
- Construction, CPI and trade have substantially shorter histories (levels begin 2021) than
  FX/M2 (2013) and industrial production (2019). No imputation was applied.

## Registry/source findings

The registry workbook was not changed. Three recommendations are documented in
[Phase 2B registry recommendations](phase2b_registry_recommendations.md): construction's
live coverage/update date, CPI's exact machine row label, and the stale M2 JSON machine URL
versus the current official page-linked DCS XLSX.

SIAT release fields remain dataset update timestamps, not reconstructed historical release
dates. CBU FX activation dates are not called releases. Unknown release dates remain null.

## Delivered outputs

All eight requested processed Parquet files, `pilot8_monthly` and `gdp_quarterly` Parquet/XLSX
pairs, immutable raw payloads, checksums, schema fingerprints, release/download/vintage logs,
outlier diagnostics and validation summaries exist. Re-run with one writer at a time. Use
`--refresh` to collect changed current-source vintages; use `--offline --fx-end 2026-09-29`
to reproduce this exact information set.

Phase 2B stops here. The remaining V1 variables and all modelling are intentionally out of
scope pending review.
