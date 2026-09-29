# Registry change log

## V1.1 — 2026-09-29

V1.0 is preserved byte-for-byte at `registry/archive/uzbekistan_nowcasting_v1_registry_v1.0.xlsx`.
Its SHA-256 is `efe0f1c577afacfca47b5294437434038e4be5172e059c5f6a4046d4b2f78b73`.

The active V1.1 workbook is `registry/uzbekistan_nowcasting_v1.1_registry.xlsx`.
Its SHA-256 is `e719e8970b20b4a25acf04c7dc822ecab1ba91af6acf2145990cb67d94986f8d`.

Only the approved changes were applied:

- `construction`: verified end changed from `2026-M07` to `2026-M08`; release evidence changed from the July 2026 update dated 2026-08-27 to the August 2026 update dated 2026-09-28.
- `cpi_headline`: row selector changed from `Composite index` to `Code=1; Klassifikator_en=Cumulative index`.
- `m2`: machine URL changed from the stale JSON snapshot to the current official CBU DCS workbook, `https://cbu.uz/sdmx/public/DCS_Uzbekistan_Online.xlsx`.
- README version label changed from V1.0 to V1.1. No conceptual series, units, cumulative flags, transformations, source IDs, automation classes, or other registry fields changed.

Machine-readable cell-level evidence and both workbook hashes are stored in `registry/uzbekistan_nowcasting_v1.1_changes.json`.
