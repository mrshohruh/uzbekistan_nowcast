# Source findings — 29 September 2026

The workbook was inspected before implementation and has not been amended.
SHA-256: `efe0f1c577afacfca47b5294437434038e4be5172e059c5f6a4046d4b2f78b73`.

## Registry names

The clean fields are `gdp_real_yoy_pct`, `ind_prod_yoy_log`, `usd_uzs_mom_dlog`.
Project-document examples differ; the implementation follows the workbook.

## SIAT topology and semantics

The registry's [GDP endpoint](https://api.siat.stat.uz/sdmx/3698/table/download/?download_format=json)
and [industrial endpoint](https://api.siat.stat.uz/sdmx/590/table/download/?download_format=json)
return descriptors containing `file`, `file_2`, `updated_at`, not observation tables.
The pipeline follows the observed `file` URL on the same official host, archiving both
responses. It does not guess file paths or silently switch to `file_2`.

Linked JSON is a one-element list containing `metadata` and `data`. English metadata
verify indicator ID, unit and frequency. Rows contain `Code`, multilingual `Klassifikator`
labels and wide period columns.

| Series | Observed exact selector | Periods | Dataset update |
|---|---|---|---|
| GDP | `Code=1700`; label `Republic of Uzbekistan` | `2018-Q1`–`2026-Q2` | `2026-07-31T10:54:09.201997+05:00` |
| Industrial | `Code=B, C, D, E`; label `Industrial production` | `2019-M01`–`2026-M07` | `2026-09-02T14:12:47.106082+05:00` |

GDP metadata describe quarterly frequency and a percentage of the corresponding period
of the previous year. The pipeline follows the registry's index-minus-100 convention.
This wording alone does not independently settle standalone-quarter versus cumulative
year-to-date growth semantics. Confirm that distinction from provider methodology before
modelling; do not reconstruct a different target from an inferred interpretation.

Industrial units are billion soums and notes specify current prices. The total rises
within complete years and resets in January, consistent with the registry's YTD rule.
The pipeline retains YTD and monthly flows and reconciles complete-year monthly sums
with December YTD. This is nominal activity, not a physical production-volume index.

Notes mention preliminary years but do not establish reliable per-observation revision
status across the full current span. Notes are retained; unspecified flags remain null.
Dataset updates are not reconstructed historical first releases. Initial inspection
archives remain immutable; the production reader computes current structural fingerprints
for those exploratory payloads without rewriting their sidecars.

## CBU dated snapshots

[CBU documentation](https://cbu.uz/en/arkhiv-kursov-valyut/veb-masteram/) defines `Date`
as activation date and `Nominal` as the quoted currency units. The registry URL template
is used exactly with USD and a calendar date.

Each observed dated response contains one quote, sometimes activated before the requested
date. Backward traversal next requests the day before that observed activation, avoiding
redundant snapshots while retaining every rate episode. Future activations, multiple USD
dates, empty responses and unsupported schemas fail visibly. Every response is archived.

Monthly means equally weight unique official activation-date observations, as the
workbook's Transform Rules require. Historical weekly updates and weekend/holiday gaps
do not create forward-filled observations. Activation does not establish release time;
CBU `source_release_date` remains null.

## Recommended clarifications — not applied to the workbook

1. Add machine-readable SIAT code/label selectors; the GDP selector is currently prose.
2. Document SIAT descriptor-to-`file` routing and distinguish dataset update timestamps
   from individual periods' original release dates.
3. Confirm standalone-quarter versus YTD GDP growth semantics before modelling. Retain
   the current published series until deliberately resolved.
4. Clarify unique-activation-date FX averaging, including historical weekly rates and
   incomplete-month treatment. The pilot retains incomplete means but nulls clean changes.
5. Align project-document example field names with the workbook.

No alternative source, indicator, release lag or historical observation was substituted.
