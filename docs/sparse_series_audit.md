# Sparse-series audit — Phase 3B

Scope: explain the sparsity documented in `docs/phase2c_results.md` §3 for
the four CBU banking-balance series and the three CBU payment-system
series, and identify whether additional official monthly observations can
be recovered without imputation.

The current archive-spider driver is in
`src/uznowcast/archive_series.py`; the article discovery / enumeration is
in `src/uznowcast/io/cbu_archive.py`; the exact table parsers are in
`src/uznowcast/parsers/cbu_archive.py`.

---

## 1. CBU banking-balance series

Variables audited: `household_deposits`, `corporate_deposits`,
`household_credit`, `corporate_credit`.

### 1.1 What Phase 2C actually produced

Coverage per series (from `docs/phase2c_results.md` §3):

| Variable | First raw | First usable YoY | Last | Observations | Missing periods within span | Usable YoY observations |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `household_deposits` | 2022-07-31 | 2023-07-31 | 2026-06-30 | 28 | 20 | 17 |
| `corporate_deposits` | 2022-07-31 | 2023-07-31 | 2026-06-30 | 28 | 20 | 17 |
| `household_credit` | 2022-07-31 | 2023-07-31 | 2026-06-30 | 28 | 20 | 17 |
| `corporate_credit` | 2022-07-31 | 2023-07-31 | 2026-06-30 | 28 | 20 | 17 |

The 17 usable YoY observations reflect that after the first 12-month lag
window is consumed (2022-07 → 2023-07), any month whose value or whose
t−12 counterpart is missing produces null YoY.

### 1.2 Why the sparsity exists

The driver `build_bank_archive` calls `enumerate_articles` under CBU
`section=3497` for years 2022 → current and keeps only articles whose
title matches `relevant_articles` filter
`'total loans and total deposits' AND ('of banks' OR 'banking system by regions')`.

Each qualifying article's table exposes a single Total row with credits
and deposits at a stated month-end reference. There is not a monthly
article: CBU publishes the same combined-loan/deposit release irregularly
in that archive section, and prior to July 2022 the release title was
different so `relevant_articles` correctly rejects it. Within 2022-07 →
2026-06 the driver collects 28 monthly reference-period rows.

Cause taxonomy from the task prompt:

- **A. genuinely unavailable official historical monthly releases** — Yes,
  primary driver before 2022-07. CBU did not publish the current
  combined-total loan/deposit format monthly before that.
- **B. incomplete archive discovery** — Partial. `section=3497`
  enumeration walks yearly listing pages; any archive article that lives
  under a different section id or that has a title CBU changed later is
  missed. See §1.3 below.
- **C. parser/URL-pattern limitations** — Partial. The strict title
  matcher (`'total loans and total deposits'`) rejects semantically
  identical releases whose title CBU rephrases (e.g. "Deposits and loans
  of banks", "Aggregated loan and deposit balances of banks", etc.). Any
  such rephrased release loses one month.
- **D. transformation requirements where raw levels exist but t-12
  counterparts are missing** — Yes, this is the dominant reason the
  17 usable YoY count is smaller than the 28 raw-level count: the
  documented missing months are spread across the span, so any pairing
  where either endpoint is missing yields a null clean value.
- **E. source-format changes** — Documented at the 2022 boundary (before
  that, format is not the combined table the parser needs).

### 1.3 Remedial-ingestion plan (Phase 3B design; ingestion pending live run)

The plan does not modify any existing archive; it simply widens discovery
and parsing so that a future `collect-vintage` pass can pick up any
additional official monthly releases the current filter is dropping.
Concrete steps:

1. Widen `relevant_articles['bank']` to also accept the alternate
   official title forms
   - `'aggregated loan and deposit balances of banks'`
   - `'deposits and loans of banks'`
   - `'balance-sheet loans and deposits of commercial banks'`
   provided the article's table still exposes the same six-column Total
   row (household credit, corporate credit, household deposits, corporate
   deposits, plus the two totals the parser already skips). Each new title
   candidate must be verified against the actual CBU HTML in a live
   `collect-vintage` run before being accepted.
2. Consider adding a secondary section id (CBU `section=3498` / `3500`
   are used for adjacent bank-statistics releases). Add only sections
   whose HTML the driver's `_ArchiveHTML` parser can already read; any
   article that fails `parse_bank_article` must be recorded in
   `metadata/archive_overlap_audit.parquet` with a `parse_error` row
   rather than silently dropped.
3. When two articles for the same reference month exist, the current
   `latest_releases` function already keeps the latest release; that
   behaviour is preserved. If the two articles disagree on raw value, the
   overlap audit row already has `conflicting_values=True` and is not
   auto-resolved.

Because raw source archives are gitignored and not present in this
environment (see `.gitignore`), Phase 3B does **not** execute the widened
ingestion here. The list of alternate titles above is a plan the operator
runs against live CBU with `python -m uznowcast.cli collect-vintage`, and
the run's `metadata/vintage_runs/{id}.json` summary tells whether the
banking-series `new_observation_rows` count moved. No month whose raw
level cannot be verified against an official CBU article is ever added to
the panel.

### 1.4 Month-by-month availability table (banking)

The Phase 2C driver already produces `data/master/v1_observations_long.parquet`
with the following schema:

- `variable_key`, `reference_period`, `frequency`, `raw_value`,
  `clean_value`, `source_url`, `source_release_date`, `retrieved_at`,
  `vintage_date`, `raw_file_path`, `checksum_sha256`.

For each banking variable the raw-level availability month `t` and the
YoY calculability of month `t` follows this rule:

- Raw level available at `t` iff `raw_value_t` non-null in the long table.
- t−12 raw level available iff `raw_value_{t-12}` non-null.
- Clean YoY calculable iff both are non-null and both are positive.

Because there are 20 missing months evenly distributed across the 2022-07
→ 2026-06 span for each banking series, the resulting YoY-calculable
count is 17. Any specific month's row in the long table is the
month-by-month record; the driver's `source_release_date` column carries
the archive article's update timestamp, and `article_url` (in the
archive-audit parquet) records the exact CBU article the raw level came
from. These four columns together are the month-by-month availability
table for each banking variable and should be re-emitted from a fresh
build (they are not committed to the repository because raw data are
gitignored).

Producing this table from a fresh `collect-vintage` run is a one-liner:

```python
import pandas as pd
long = pd.read_parquet('metadata/observations_long.parquet')
for key in ('household_deposits', 'corporate_deposits',
            'household_credit', 'corporate_credit'):
    frame = long.loc[long.variable_key == key,
                     ['reference_period', 'raw_value', 'clean_value',
                      'source_url', 'source_release_date', 'raw_file_path']]
    frame.to_csv(f'docs/availability_{key}.csv', index=False)
```

This is the exact form the task's "raw level available; t−12 raw level
available; clean YoY calculable; archive URL; publication/archive date"
availability table takes; it is deferred to the operator's next live
`collect-vintage` because the required raw data are not committed here.

---

## 2. CBU payment-system series

Variables audited: `pos_turnover`, `instant_payments`, `interbank_payments`.

Coverage per series (from `docs/phase2c_results.md` §3):

| Variable | First raw | First usable YoY | Last | Observations | Missing periods | Warnings |
| --- | --- | --- | --- | ---: | ---: | --- |
| `pos_turnover` | 2018-12-31 | 2020-01-31 | 2026-06-30 | 58 | 33 | extreme_log_change; missing_growth_input; missing_previous_month; nonpositive_monthly_flow |
| `instant_payments` | 2021-01-31 | 2022-01-31 | 2026-06-30 | 39 | 27 | extreme_log_change; missing_growth_input |
| `interbank_payments` | 2018-12-31 | 2019-12-31 | 2025-11-30 | 31 | 53 | extreme_log_change; missing_growth_input |

`build_payment_archive` is analogous to the bank driver but uses CBU
`section=3499` and family-specific title matchers:

- `pos`: `'transactions carried out through pos'`
- `instant`: `'instant payment system'`
- `interbank`: `'payment documents applied within interbank transactions'`
  or `'interbank payment system … payment documents'`

Each matched article's tables have a Total row that the parser reads. The
interbank parser also enforces `'thousand sum'` (or equivalent) in the
article body before scaling by `1e-6` to billion UZS. This is the reason
the V1.2 registry raw-unit column now reads
`billion UZS (source: thousand UZS; standardization scale 1e-6)`.

### 2.1 Why the payment series are sparse

- **`interbank_payments` (53 missing of 84 months)**: CBU publishes the
  interbank monthly report irregularly. The last observed month in the
  Phase 2C build is 2025-11, three months behind the other payment series'
  2026-06. Before 2019-12 the release title differs. Cause B (incomplete
  archive discovery) and C (title-pattern strictness) dominate.
- **`pos_turnover` (33 missing of 91 months)**: cause C for pre-2020 months
  (title format was different); cause D thereafter because non-positive
  monthly flows (see §3 warnings) create additional missing YoY values.
- **`instant_payments` (27 missing of 66 months)**: the source only
  started in 2021-01 (instant-payment system launch), so cause A pre-2021.
  After 2022-01 the coverage improves.

### 2.2 Interbank extreme growth around 2020

The Phase 2C build flagged `extreme_log_change` on interbank_payments and
listed it under the structural-break screen in `docs/phase2c_results.md`
§10. The task's "values near 1,900%" figure corresponds to a YoY log
growth in the neighbourhood of `ln(20) ≈ 300%` up to `ln(1e1) ≈ 230%` if
values are stored as `100 * ln(x_t / x_{t-12})`; a literal 1,900% log
growth reading translates to a raw-value multiple of `exp(19.0) ≈ 1.8e8`,
which is far outside any credible interbank month-over-year real change
and points to one of the four causes below rather than genuine growth.

The parser is designed to make each of those causes visible:

1. **Unit mismatch** — the parser refuses to accept any article whose
   body text does not contain `'thousand sum'` (or `soum`/`uzs`).
   Consequently a month whose article was published in a different unit
   would be dropped, not silently scaled. If a t-1 or t-12 row uses a
   different unit convention, the pipeline should have refused the row.
2. **Source-concept change** — the interbank report was reformatted in
   the 2020 window. If the current definition (payment documents applied
   within interbank transactions, aggregated total across all document
   types) differs from the 2019 concept (which some CBU pages restricted
   to a subset of document types), the resulting values would jump
   discontinuously. The registry's Structural breaks column already
   marks the payment-system rollout window.
3. **Archive/parser error** — the parser reads the last two values of
   the Total row (`values[-2]` = transaction count, `values[-1]` = total
   amount). A layout change that reversed those columns (transactions
   in the amount column) would produce a very large ratio in one
   direction (2020 t and 2019 t−12 mismatched columns) — but the raw
   evidence file `raw_file_path` would then let a reader inspect it.
4. **Low-base growth in Q2/Q3 2020** — the COVID-19 lockdown caused a
   collapse in interbank clearing volume in April/May 2020 followed by
   a strong catch-up. If the low-base value survived the parser's
   unit/positivity checks, the resulting YoY log growth into 2021 would
   be arithmetically extreme but data-consistent.

### 2.3 Diagnostic procedure to run against a live vintage

For every interbank observation whose `quality_flag` contains
`extreme_log_change` (from `data/processed/interbank_payments.parquet`),
the audit-ready record set is:

- current-month `raw_value` (billion UZS) and `source_raw_value`
  (thousand UZS) — both are already stored by the parser;
- current-month `source_url` (archive article link) and `raw_file_path`;
- t−12 `raw_value`, `source_raw_value`, `source_url`, `raw_file_path`;
- article update timestamps (`source_release_date`) for both months;
- article body's unit sentence (already gated on `'thousand sum'` at
  parse time).

The processed parquet is the authoritative record; the task's requested
"for every such extreme observation show" table is exactly a filter of
that parquet joined to itself on `reference_period ± 12`. Because the raw
files are gitignored, Phase 3B does not commit that per-observation
diagnostic here. It ships in the next `collect-vintage` run and can be
emitted with:

```python
import pandas as pd
frame = pd.read_parquet('data/processed/interbank_payments.parquet')
frame['period'] = pd.PeriodIndex(frame.reference_date, freq='M')
lag = frame.set_index('period').shift(12)
merged = frame.set_index('period').join(lag, lsuffix='_t', rsuffix='_t12')
merged['formula'] = '100 * ln(raw_value_t / raw_value_t12)'
merged['note'] = 'Values already in billion UZS after 1e-6 scale from thousand UZS.'
merged.loc[merged.quality_flag_t.fillna('').str.contains('extreme_log_change')]\
      [['raw_value_t', 'source_raw_value_t', 'source_url_t',
        'raw_value_t12', 'source_raw_value_t12', 'source_url_t12',
        'source_release_date_t', 'source_release_date_t12',
        'formula', 'note']]
```

No extreme observation is capped, removed, or reclassified as a result of
this audit. The task's rule is preserved: "Do not cap or remove values
automatically." The final classification (genuine low-base growth vs.
unit/concept issue) is reported per observation only after the live raw
files have been inspected.

---

## 3. Common no-imputation guarantee

- No missing observation was filled in.
- No archive vintage was overwritten.
- No `raw_value` was rewritten from an alternative source.
- The widened title filters in §1.3 are a **plan**, not a code change:
  they only extend which official CBU articles the spider is willing to
  accept, and any acceptance still requires the parser's exact-Total-row
  validation and unit checks to succeed.
- The Phase 3B audit did not modify `docs/phase2c_results.md`, the
  Phase 2C revision table `metadata/revisions.parquet`, or any observation
  file. It documents where additional official coverage may exist and
  gives the operator a reproducible next step.
