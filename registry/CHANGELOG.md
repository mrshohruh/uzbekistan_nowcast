# Registry change log

## V1.2 — 2026-09-29

V1.0 and V1.1 are preserved byte-for-byte. V1.0 lives at
`registry/archive/uzbekistan_nowcasting_v1_registry_v1.0.xlsx`
(SHA-256 `efe0f1c577afacfca47b5294437434038e4be5172e059c5f6a4046d4b2f78b73`).
V1.1 lives at
`registry/archive/uzbekistan_nowcasting_v1.1_registry.xlsx`
(SHA-256 `e719e8970b20b4a25acf04c7dc822ecab1ba91af6acf2145990cb67d94986f8d`).

The active V1.2 workbook is `registry/uzbekistan_nowcasting_v1.2_registry.xlsx`.
Its SHA-256 is `0659713cea0fea42c3823a3be26dd116ba15f2b292f269ba5f7e1c7b99abbb33`.

The Phase 3B task lists the corrections that were applied; the `russia_ipi`
recommendation from `docs/phase2c_registry_recommendations.md` is intentionally
excluded (provider stays Rosstat and no TLS policy is changed here). The
verified-no-op entries were checked against the workbook and the current
`row_field_selector` cell already matches the live SIAT label, so no cell
edit was required.

Approved changes:

- `manufacturing` — `Row / field selector`: `Manufacturing` →
  `Code=C; Klassifikator_en=Manufacturing industry`.
- `electricity_gas` — `Row / field selector`:
  `Electricity, gas, steam and air conditioning supply` →
  `Code=D; Klassifikator_en=Electricity, gas, steam and air conditioning`.
- `retail_trade` — `Raw unit`: `billion UZS` →
  `billion UZS (source: million sums; standardization scale 0.001)`.
- `wholesale_trade` — `Raw unit`: `billion UZS` →
  `billion UZS (source: million sums; standardization scale 0.001)`.
- `gold_exports_proxy` — `Row / field selector`:
  `Other goods (gold-dominated residual category)` →
  `Code=9; Klassifikator_en=Other goods (gold-dominated residual category)`.
- `fx_reserves_ex_gold` — `Machine/download URL`:
  `https://cbu.uz/upload/open_data/0017/4-009-0017_eng.json` →
  `https://cbu.uz/en/statistics/e-gdds/data/111574/` (the same page that the
  reserves resolver already reads to find the current
  `IR_Uzbekistan_MCD_STA.xlsx`).
- `interbank_payments` — `Raw unit`: `UZS (transaction amount)` →
  `billion UZS (source: thousand UZS; standardization scale 1e-6)` (the
  archive parser already scales thousand UZS by `1e-6` and the raw table
  publishes total amount in thousand sum).
- `ppi` — `Structural breaks / caveats`:
  `Monitor producer-price methodology/rebasing notices.` →
  the verbatim SIAT reporting-entity break wording followed by an explicit
  note that period labels mix Cyrillic `М` (U+041C) for 2016-M01..2020-M12
  with Latin `M` elsewhere (parser normalizes to Latin without rewriting
  the raw payload).

Verified no-op (Phase 2C recommendation already satisfied in V1.1):

- `retail_trade` — `Row / field selector` is already
  `Republic of Uzbekistan / retail trade turnover`.
- `wholesale_trade` — `Row / field selector` is already
  `Republic of Uzbekistan / wholesale trade turnover`.

Deliberately not applied:

- `russia_ipi` — provider stays Rosstat and no TLS policy, root store, or
  provider substitution is changed here. The variable remains
  `automation_status = EXTERNAL` and `russia_ipi = unresolved` per Phase 3B
  guidance.

No conceptual series, transformation, cumulative flag, provider, dataset ID,
frequency, verified span, publication lag or model role changed. The README
version label moved from V1.1 to V1.2. Machine-readable cell-level evidence
and all workbook hashes are stored in
`registry/uzbekistan_nowcasting_v1.2_changes.json`.

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
