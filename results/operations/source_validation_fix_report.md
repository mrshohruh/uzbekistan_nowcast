# Phase 6D.1A source validation fix

The approved real industrial source is SIAT table **577**, with internal indicator
code **1.02.01.0004**. Phase 6D.1 passed the table ID to the strict SIAT parser as
though it were the indicator metadata code. The source was valid; the acquisition
contract was wrong. The canonical nominal industrial series remains SIAT 590 and
has not been substituted into the frozen real-activity DFM.

The corrected adapter independently validates the HTTPS descriptor path
`/sdmx/577/table/download/?download_format=json` and its exact resolved payload
`https://api.siat.stat.uz/media/uploads/sdmx/sdmx_data_577.json`. The unchanged strict
parser validates indicator code, Percent unit, Monthly periodicity, national
`Code=1700` / `Klassifikator_en=Republic of Uzbekistan`, dimensions, numeric values
and duplicate periods. The adapter also validates the published indicator name,
`Index of the physical volume of industrial production (monthly)`.

The evidence predates this fix: the Phase 6A2 archived descriptor
`data/raw/research/phase6a2/siat_577/20261002T070310584604Z_25e1a1659bf0.json`,
payload `20261002T070312139096Z_c50ca4e3894a.json`,
`results/research/phase6a2/phase6a2_fetch_log.json`, and the industrial rows of
`results/research/phase6a2/phase6a2_provenance.csv`. The prior accepted extraction
in `scripts/research/phase6a2/extract.py` independently selected table 577 and the
exact national row. Archived metadata explicitly gives code `1.02.01.0004`,
physical-volume indicator name, Monthly frequency and Percent unit. The descriptor
response's own database `id` is not used as the table or indicator identifier.

The final live retrieval reproduces all 92 published national indices over
January 2019?August 2026. Latest August index is 108.0, or 8.0 percentage points
under the frozen published-index-minus-100 convention. This convention is retained
without nominal-flow de-cumulation. The overlap is recorded in
`source_validation_fix_industry_overlap.csv`; live URLs, receipt paths, checksums,
metadata identities and gold details are in `source_validation_fix_evidence.json`.

CSV serialization explains a handful of transformed-value differences around
2e-15 even when the raw published indices are identical. The adapter reads the
approved CSV with round-trip precision and treats only identical raw indices whose
old clean value agrees with the unchanged formula within two raw-index ULPs as
unchanged. It preserves the old value and provenance. Changed raw indices still
produce revision candidates. No model inputs are rounded or recomputed to conceal
an economic revision.

October USD/UZS and RUB/UZS candidates are `PARTIAL_CURRENT_MONTH` with
`accepted=False`. Daily payloads remain archived. Incomplete monthly means and
missing growth values neither count as historical revisions nor replace completed
September observations. If no observations are accepted, comparison returns the
old table exactly, including its column structure and provenance. Frozen daily
normalization, monthly-mean and monthly-log-change functions are unchanged.

September gold comes from the official World Bank Pink Sheet workbook, with its
exact Gold column and USD/troy-ounce unit validated by the existing strict parser.
September is complete, there are no duplicate monthly periods, and
`100 * ln(price_September / price_August) = -2.1077527144239383`. It is a valid
`NEW_OBSERVATION` candidate; **nothing is promoted in CHECK_ONLY**. The unchanged
2026Q3/H3 information mask has gold cutoff August 31, so this September candidate
is currently excluded from model inputs.

Final live command:

```powershell
.venv/Scripts/python.exe scripts/operations/run_update.py --check-only --verbose
```

Run **update_20261005_113447_78929bb8**, cutoff **2026-10-05T11:40:02.750033+00:00**, checked all nine source families.
Industrial production is `UNCHANGED`, independently `SOURCE_VERIFIED` in the
evidence audit. Both October FX candidates are `PARTIAL_CURRENT_MONTH`. Gold is
`UPDATED`: one accepted new September candidate, zero historical revisions and
zero rejected observations. No source family failed. Individual obsolete POS links
return archived 404 responses; valid retained POS data stay unchanged and the
post-2024 scope restriction remains visible. Operational status is
`UPDATE_SUCCESS_WITH_WARNINGS` because candidates were not promoted and POS remains
scope limited. Source-validation fix status is **SOURCE_VALIDATION_FIXED**.

Eligible fingerprint `4682b245f25db4ae87b43e80444f62b85e29533b53a3a8038ffb7c90191386e0` matches existing snapshot
`d1a9e5c4426f706b2007d26299921f2b5c788ac67bea615d577627d737664614`. A private staged worker actually recalculated all
seven frozen shadow forecasts from current live-staged eligible inputs. Every
difference from the immutable snapshot's JSON forecast values is **exactly zero**.
September gold remains null in the masked panel. CHECK_ONLY deliberately skips
production fitting; a separate private staged reproduction recalculated the four
production models, which also exactly match the prior offline operational run.
No forecast files, model definitions or historical snapshots were overwritten.

The final hash audit verified **293 original files unchanged**, including
current masters, processed/metadata tables, protected historical production
artifacts, Phase 6D ledger and snapshots, and frozen code/specifications. Existing
historical release identity and current-state reconciliation remain intact. The
candidate monthly master includes validated gold in staging only; there is no
master promotion, snapshot append, GDP realization registration or scoring.

Tests: **436 passed, 0 failed** in the aggregate. This fix reran all **57 operations
tests** (43 existing plus 14 new parameterized cases). The 379 earlier repository
and research regression results remain passing; protected code and inputs were
rechecked. New cases cover separate SIAT identities, approved-source acceptance,
rejection of wrong table resolution/code/name/unit/frequency, partial USD/RUB with
and without an October placeholder, exact September retention, valid September
gold and the actual frozen kernel mask, and unchanged masters/ledger/snapshots.
Existing tests reproduce frozen forecasts and assert immutable specifications and
combination weights.

Evidence: [final run report](update_20261005_113447_78929bb8/update_report.md),
[source receipts](update_20261005_113447_78929bb8/source_receipts.csv),
[candidate changes](update_20261005_113447_78929bb8/data_changes.csv),
[shadow recalculation](source_validation_fix_forecast_reproduction.json),
[production recalculation](source_validation_fix_production_reproduction.json),
and [final validation](source_validation_fix_validation.json).

Intermediate attempts are retained as actual evidence. Run
`update_20261005_112609_b129b94f` encountered the sandbox's blocked proxy and promoted
nothing. Approved network retry `update_20261005_112835_80cecfb9` exposed four
serialization-only revision candidates and also promoted nothing. The final
tested run above records zero such revisions.

