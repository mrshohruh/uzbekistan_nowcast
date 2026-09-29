# Historical extension audit — Phase 3B

Scope: audit whether an official, methodologically comparable **quarterly
real GDP growth** series can be extended before 2018-Q1, and whether the
core monthly activity/price/trade series can be pushed back beyond their
current Phase 2C Verified start. No incompatible series is spliced. No
value is imputed. Where an official older series is documented but is
non-comparable, it is described but not merged.

The Verified spans below all come from `registry/uzbekistan_nowcasting_v1.2_registry.xlsx`
and match the coverage documented in `docs/phase2c_results.md` section 3.

---

## 1. Quarterly real GDP (target)

### Current state

- Series: `gdp_real_yoy` (SIAT dataset 3698, exact selector Code=1700,
  Republic of Uzbekistan).
- Verified span: **2018-Q1 → 2026-Q2** (34 quarters).
- Native unit: percentage of the corresponding period of the previous year,
  minus 100.
- Frequency: quarterly, no interpolation.
- Revision behaviour: SIAT re-publishes recent quarters; the dataset update
  timestamp is retained but is not treated as a first-release date.

### Official pre-2018 sources examined

Only official SIAT / State Committee on Statistics / Ministry of Economic
Development and Trade (MoED) publications were considered. External /
mirror sources (IMF WEO, World Bank WDI, ADB Asian Statistical Yearbook,
CEIC) were explicitly excluded from the "extend the target" question,
because the task requires official SIAT quarterly real GDP growth.

| Historical source examined | Frequency and definition | Comparability with the current 2018-Q1+ series |
| --- | --- | --- |
| SIAT current dashboard dataset **3698** ("Gross Domestic Product") | Quarterly YoY, current SNA-based estimation | This is the current target and its verified span starts 2018-Q1. Older quarters are not published behind the same dataset ID. |
| SIAT historical statistical yearbook chapter "National Accounts" (annual editions) | **Annual only** real growth in constant prices, base-year revisions per edition (2015→2020 rebasing documented in the yearbook methodology note) | Not comparable at quarterly frequency. Cannot be used to extend a quarterly target. |
| MoED historical quarterly national-accounts summary tables (mirror of SIAT quarterly bulletin) | Quarterly headline growth, published from 2010 onward in some editions | Discontinuous methodology: base-year rebasings in 2015 and 2020 that were **not** back-cast for the entire quarterly history. Sector weight reclassifications on the 2015 SNA transition also affect earlier quarters. |
| State Committee "Uzbekistan in figures" mid-1990s to early 2010s | Annual real growth; some quarterly summaries in narrative form | Different SNA vintage; construction of a quarterly volume index would require redoing the deflator/rebase. Not published as a machine-readable series. |
| IMF Article-IV Staff Reports 2013-2019 (Table 1 macroeconomic framework) | Annual + calendar-year components; no quarterly series | Not official SIAT; annual only; excluded per rule 6. |

### Conclusion for GDP extension

There is **no consistent official SIAT quarterly real GDP growth series
before 2018-Q1**. The pre-2018 SIAT publications either:

1. publish national accounts only at annual frequency and only in printed
   yearbook tables; or
2. publish quarterly narrative summaries whose methodology (base year,
   sector weights, SNA vintage) differs materially from the current dataset
   3698, and which were not back-cast when the 2015→2020 base-year revision
   was applied.

Splicing these onto the 2018-Q1+ series would create an artificial break
at 2018-Q1 and violate AGENTS.md §6 ("GDP remains quarterly") and §22
(document the finding, do not silently change the conceptual series).

**Recommendation for Phase 4+:**

- Leave the target `gdp_real_yoy` unchanged at 2018-Q1 → present.
- Keep annual pre-2018 growth (SIAT annual national accounts, official
  yearbook editions) as an **informational** covariate only, never as a
  quarterly interpolation. Store it under a new experimental key
  (`gdp_real_annual_pre2018`) with an explicit `is_experimental = true`
  flag when and if a modelling need arises.
- Do not attempt an in-house quarterly reconstruction (e.g. Chow-Lin,
  Denton disaggregation of the annual series) without an explicit
  Phase-4 governance approval and a signed methodology note. The Phase 3B
  audit finds none of the raw material required for a defensible
  disaggregation (no quarterly deflator series across the full pre-2018
  span, no consistent quarterly sector breakdown).

The Phase 2C `usable_transformed_start` of 2018-Q1 stands.

---

## 2. Core monthly predictors — extension audit

For each series below the audit answers: does an official SIAT (or CBU,
where relevant) publication carry the same concept at monthly frequency
before the current Verified start, and does that older publication use a
methodology that would splice cleanly into the current series?

The audit distinguishes the two documented Verified starts already in the
registry:

- **2019-01** — SIAT dataset 590 industrial-activity subaggregates.
- **2020-01** — SIAT retail/wholesale trade (datasets 2699/964).
- **2021-01** — SIAT construction/CPI/trade totals.

### 2.1 Industrial production, manufacturing, mining, electricity/gas

- Registry span: 2019-01 → 2026-07 (usable YoY from 2020-01).
- Dataset 590 is the current SIAT publication and does not host earlier
  months.
- Older State Committee industrial monthly bulletins (2010-2018) exist in
  the SIAT archive as **PDF releases**, not machine-readable tables. They
  use current-price soum values in the same way as dataset 590, but with:
  1. a different sector classification (ISIC Rev.3 vs. Rev.4);
  2. different underlying reporting-enterprise universe (the 2018 industrial
     survey redesign expanded coverage).
- Splicing pre-2019 monthly totals from PDFs would silently break the
  YTD-cumulative behaviour that the current parser relies on and would
  introduce a coverage discontinuity in January 2019.

**Recommendation:** do not extend. Keep 2019-01 as the industrial-block
Verified start. If a specific model requires pre-2019 industrial growth,
consult the SIAT industrial statistics methodology note first and record
an explicit break flag.

### 2.2 Retail trade, wholesale trade

- Registry span: 2020-01 → 2026-08 (usable YoY from 2021-01).
- SIAT dataset 2699 / 964 do not carry pre-2020 months.
- The Ministry of Economic Development and Trade published monthly retail
  turnover as far back as 2015 (paper bulletin only), but at a **different
  base** (retail trade includes catering in some editions, excludes it in
  others).

**Recommendation:** do not extend. The Phase 2C V1.2 selector correction
already ensures the exact SIAT label; the pre-2020 material is not
machine-readable and definitionally inconsistent.

### 2.3 CPI (headline, food, services)

- Registry span: 2021-01 → 2026-08.
- Both source Notes (recorded in `docs/phase2c_results.md`) and the V1.2
  PPI break statement confirm that COICOP-2018 applies from January 2021.
- Pre-2021 CPI was published under a different classification and the
  official statement is that a full back-cast has not been released.
- CPI subcomponent food/services indexes had a different weight structure
  before COICOP-2018.

**Recommendation:** do not extend. This is a genuine methodological break
and splicing would understate 2020-2021 inflation.

### 2.4 Construction

- Registry span: 2021-01 → 2026-08.
- Earlier construction monthly totals exist in SIAT PDF bulletins but the
  definition of "construction works" (whether it includes on-site erection
  vs. installation vs. major repair) was changed in the 2021 SIAT dataset
  redesign.

**Recommendation:** do not extend without an explicit methodology memo.

### 2.5 Exports / imports totals and gold-export proxy

- Registry span: 2021-01 → 2026-08.
- Uzbekistan customs began publishing complete monthly trade with an "Other
  goods" residual (which the gold-export proxy relies on) only from 2021.
- Pre-2021 external trade totals are available in annual customs bulletins
  and IMF DOTS mirrors, but neither preserves the SIAT "Other goods"
  residual line that defines `gold_exports_proxy`.

**Recommendation:** do not extend. The proxy identity used in
`transforms/derived.py::exports_non_gold` is defined only from 2021 onward.

---

## 3. Long-history predictors already in the panel

The following predictors already extend well before the GDP target's
2018-Q1 start and require no extension work; they simply cannot be used to
extend the target itself.

| Variable | Verified start | Notes |
| --- | --- | --- |
| `usd_uzs` | 2013-01 | 2017 FX liberalization documented in registry Structural breaks. |
| `rub_uzs` | 2013-01 | Same 2017 break window. |
| `ppi` | 2013-01 | April-2024 reporting-entity expansion documented in V1.2. |
| `m2` | 2013-01 | Same CBU DCS workbook back to 2013. |
| `fx_reserves_ex_gold` | 2013-01 | Same CBU IR workbook back to 2013. |
| `gold_price` | 1960-01 | External (World Bank Pink Sheet); the earliest series in the panel. |

These are the six Tier A variables in `docs/model_readiness_tiers.md`. They
already anchor the Phase 4 benchmark AR/MIDAS runs.

---

## 4. Summary

| Question | Answer |
| --- | --- |
| Is there an official SIAT quarterly real GDP growth series before 2018-Q1 with a methodology comparable to dataset 3698? | **No.** Annual only, or quarterly with base-year/SNA breaks that were not back-cast. |
| Can any core monthly activity/price/trade series be extended backwards without splicing incompatible definitions? | **No** for industrial, retail/wholesale, CPI, construction, external trade. |
| Which V1 variables already provide long history? | `ppi`, `usd_uzs`, `rub_uzs`, `m2`, `fx_reserves_ex_gold` (2013+), `gold_price` (1960+). |
| Was the current 2018-Q1 GDP start modified? | **No.** It remains authoritative for Phase 4. |
| Was any pre-2018 GDP value silently spliced into the target? | **No.** |
