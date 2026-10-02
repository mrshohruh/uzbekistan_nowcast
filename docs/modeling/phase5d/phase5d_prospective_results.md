# Phase 5D prospective results

Status: WAITING_FOR_FIRST_PROSPECTIVE_GDP_RELEASE. Prospective realized quarters: 0.
Production unchanged: `production_ensemble_ar2_usd`. Historical 2026Q3 H2: 7.6239786595896035%.
Frozen research challengers: combination_equal_weight, combination_inverse_past_rmse, combination_nonnegative_past_stack.
Four exact H2 forecasts inherited; H1/H3 unavailable. No models re-estimated on initialization.
No replacement is authorized. Best challenger is NOT_YET_EVALUABLE until prospective outcomes exist.

Warnings:
- Inherited 2026Q3 H1/H3 were not recorded; no forecasts synthesized.
- Phase 5C combination conservative-lag evidence is unavailable; eligibility remains blocked until tested prospectively.
- GDP source-release fields in existing target are dataset update timestamps, not reliable historical first releases.
- No newly verified GDP realization has been registered.
- Official SIAT payload verified through 2026Q2; 2026Q3 GDP is not present.

## Operations

`python -m uznowcast.shadow.phase5d initialize` checks freezes and rebuilds mirrors.
`python -m uznowcast.shadow.phase5d forecast --target 2026Q4` generates current-time
forecasts using the frozen cohort and actual retrieval-bounded observations;
target quarters have no configured end. Refresh ingestion separately before forecasting.
`python -m uznowcast.shadow.phase5d realize --record path.json` appends an official
realization: target_quarter, release_date (timezone), retrieval_timestamp (timezone),
value, source_url, raw_file (workspace relative), data_hash (SHA256),
release_date_evidence, parser_version. Archive official raw data before registration.
Unknown or retrospective release evidence is rejected; do not guess timestamps.
`python -m uznowcast.shadow.phase5d refresh` scores matched forecasts and regenerates
the standalone dashboard. Frozen JSON ledgers are authoritative and immutable.
CSV/Parquet are rebuildable mirrors. No operation writes to production.
