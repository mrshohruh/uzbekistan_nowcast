# Phase 2B registry recommendations

The authoritative workbook was not edited. These recommendations record live official-source
behavior observed on 29 September 2026 and should be reviewed before a deliberate registry
revision.

| Variable | Registry field | Current registry value | Observed live behavior and evidence | Recommended amendment |
|---|---|---|---|---|
| `construction` | `Verified end`; lag/release convention | `2026-M07`; “Jul-2026 source updated 2026-08-27” | Official SIAT dataset `1.04.02.0002`, page `2403`, contains contiguous values through `2026-M08`; descriptor update timestamp is `2026-09-28T16:51:34.606838+05:00`. The archived national row is code `1700`. | After provider review, advance verified end to `2026-M08` and update the release-convention evidence. Keep the conceptual series, unit, cumulative flag and transformation unchanged. |
| `cpi_headline` | `Row / field selector` | `Composite index` | The official SIAT payload for dataset `1.11.01.0002`, page `1286`, labels code `1` as `Cumulative index`. Metadata identifies the dataset as CPI “compared to last month,” and the values use previous month = 100. | Make the selector machine-readable, for example `Code=1; Klassifikator_en=Cumulative index`, while retaining “headline/composite CPI” as the conceptual display label. |
| `m2` | `Machine/download URL` | `https://cbu.uz/upload/open_data/0020/4-009-0020_eng.json` | The URL returned only 37 months, `2022-01`–`2025-01`, when retrieved. The registry's official page `111578` showed the current table for `2013-01`–`2026-08`, update timestamp `25 Sep 2026, 09:40`, and linked `https://cbu.uz/sdmx/public/DCS_Uzbekistan_Online.xlsx`. The XLSX contains the exact `Broad money liabilities` row and unit `billion sum, end of period`. | Replace the stale JSON machine URL with the official DCS XLSX, or explicitly configure the human page as the resolver for that XLSX. Preserve `READY_PAGE`, source ID `4-009-0020 (DCS); alternate 4-009-0021`, exact row selector, unit and transformation. |

No discrepancy was observed for construction's unit/frequency/YTD behavior; exports/imports
IDs, national row, unit, frequency and YTD behavior; CPI frequency/unit/index convention; or
the M2 concept/unit/frequency in the current official workbook.

The SIAT descriptor update timestamps are dataset-edition timestamps, not per-period first
release dates. The CBU page timestamp is stored as an observed page update for the linked
workbook. Neither is backfilled into unavailable historical release dates.
