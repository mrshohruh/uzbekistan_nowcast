# Model-readiness tiers — Phase 3B

Actual clean-data coverage is taken from `docs/phase2c_results.md` section 3,
which was itself derived from the Phase 2C build's
`data/master/v1_observations_long.parquet`. No imputation is used. No new
data is invented for a variable to promote it to a higher tier.

The purpose of these tiers is to plan benchmark regressions and MIDAS
robustness runs, and to document which variables carry the ragged edge. The
Dynamic Factor Model does not require a balanced panel and can use every
tier's variables together; the tier boundaries are a modelling-convenience
grouping, not a data-quality classification.

## Tier definitions

### Tier A — core long-history predictors (6 variables)

Variables with coverage back to at least 2013 that pass Phase 2C validation
with no unresolved warnings on their first-usable transformed observation.

| Variable | First usable transformed observation | Last observation | Frequency | Notes |
| --- | --- | --- | --- | --- |
| `ppi` | 2013-01 | 2026-08 | Monthly | Cyrillic/Latin period-label anomaly normalized in parser; April-2024 reporting-entity expansion documented in V1.2. |
| `usd_uzs` | 2013-02 | 2026-09 | Monthly (from daily) | September-2017 FX liberalization is a documented structural break. |
| `rub_uzs` | 2013-02 | 2026-09 | Monthly (from daily) | Same 2017 break window as USD/UZS. |
| `gold_price` | 1960-02 | 2026-08 | Monthly | External-source (World Bank Pink Sheet). |
| `m2` | 2014-01 | 2026-08 | Monthly | CBU DCS workbook resolver. |
| `fx_reserves_ex_gold` | 2014-01 | 2026-08 | Monthly | CBU IR workbook resolver (V1.2 page-resolver update). |

- First common usable month: **2014-01**.
- Last common usable month: **2026-08**.
- Monthly observations in the common window: **152**.
- Corresponding GDP quarters observed (2018-Q1..2026-Q2): **34**.

### Tier B — activity-enhanced (Tier A plus real-activity indicators; 12 variables)

Adds the reliable monthly real-activity indicators whose first usable
transformed observation is 2020-01 or 2021-01.

Additional variables:

| Variable | First usable transformed observation | Last observation |
| --- | --- | --- |
| `industrial_production` | 2020-01 | 2026-07 |
| `manufacturing` | 2020-01 | 2026-07 |
| `mining` | 2020-01 | 2026-07 |
| `electricity_gas` | 2020-01 | 2026-07 |
| `retail_trade` | 2021-01 | 2026-08 |
| `wholesale_trade` | 2021-01 | 2026-08 |

- First common usable month with Tier A ∪ Tier B: **2021-01**.
- Last common usable month: **2026-07** (SIAT industrial dataset trails
  construction/trade/CPI by one month in the current vintage).
- Monthly observations in the common window: **67**.
- Corresponding GDP quarters observed: **22**.

### Tier C — full modern panel (Tier A ∪ Tier B plus construction/trade/prices; 20 variables)

Adds construction, CPI, trade and the gold-export proxy.

Additional variables:

| Variable | First usable transformed observation | Last observation |
| --- | --- | --- |
| `construction` | 2022-01 | 2026-08 |
| `cpi_headline` | 2021-01 | 2026-08 |
| `cpi_food` | 2021-01 | 2026-08 |
| `cpi_services` | 2021-01 | 2026-08 |
| `exports_total` | 2022-01 | 2026-08 |
| `exports_non_gold` | 2022-01 | 2026-08 |
| `imports_total` | 2022-01 | 2026-08 |
| `gold_exports_proxy` | 2021-01 | 2026-08 |

- First common usable month with Tier A ∪ Tier B ∪ Tier C: **2022-01**.
- Last common usable month: **2026-08**.
- Monthly observations in the common window: **56**.
- Corresponding GDP quarters observed: **18**.

### Experimental / ragged-only (7 variables)

Coverage is too short and/or too gapped for the balanced-panel tiers. Only
use them in ragged-edge estimators that tolerate arbitrary missingness
patterns, and only after the sparse-series audit's remedial ingestion (see
`docs/sparse_series_audit.md`) has run.

| Variable | First usable transformed observation | Last observation | Documented missing periods within span |
| --- | --- | --- | --- |
| `household_deposits` | 2023-07 | 2026-06 | 20 |
| `corporate_deposits` | 2023-07 | 2026-06 | 20 |
| `household_credit` | 2023-07 | 2026-06 | 20 |
| `corporate_credit` | 2023-07 | 2026-06 | 20 |
| `pos_turnover` | 2020-01 | 2026-06 | 33 |
| `instant_payments` | 2022-01 | 2026-06 | 27 |
| `interbank_payments` | 2019-12 | 2025-11 | 53 |

For the balanced-panel joint window (Tier A ∪ B ∪ C ∪ experimental) the
common start is **2023-07** and the common end is **2025-11**, i.e.
**29 months** and **9 GDP quarters** — the interbank_payments end and the
2023-07 banking start together dominate the ragged edge.

### Excluded (Phase 3B policy)

- `russia_ipi` — kept outside every model-candidate tier per Phase 3B rule 2
  (no TLS-policy change, no provider substitution, no unofficial mirror).

## Recommended modelling use

- **Benchmark AR/quarterly-GDP models** — Tier A only, using the 2014-01 to
  2026-Q2 window (34 GDP quarters, no ragged edge).
- **MIDAS with real-activity block** — Tier A + Tier B, 2021-01 start.
- **Bridge equations and DFM sanity checks with full modern panel** —
  Tier A + Tier B + Tier C, 2022-01 start; drop the four Tier C prices
  variables (`cpi_headline/food/services`) if a specification wants only
  volume-side signals.
- **DFM** — all Tier A/B/C variables plus experimental where useful. The DFM
  does not require balance; the tiering here is only for balanced-panel
  robustness runs.

## Regeneration

The Phase 3B run summary and the missingness diagnostics in
`docs/phase3b_results.md` are computed from the same coverage table used
above. If a future `collect-vintage` pass changes the coverage, regenerate
this file with the same helper in `docs/phase3b_results.md` §3.
