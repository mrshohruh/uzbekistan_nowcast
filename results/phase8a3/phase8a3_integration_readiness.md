# Phase 8A.3 integration readiness

Status: NOT_READY_FOR_PRODUCTION_INTEGRATION. The additive collection contracts are available, but live end-to-end verification remains blocked. No integration was implemented.

The final dry-run candidate contains 23 manifest-hashed files; all exist and match their hashes. Its journal is DRY_RUN_COMPLETE. There is no committed collection pointer, and no collection version was published in this phase. A validated candidate here means structurally valid retained inputs, not successful live source validation: every source failed before download. See `validation/snapshot_verification.json`.

The committed reader validates the pointer's manifest digest, VALIDATED status, safe paths and every declared file hash. Regression tests exercise immutable publication, corruption rejection and recovery on isolated roots; existing production readers remain unchanged. Partial staged files are not a production input route.

The explicit predictor view maps the eight active keys: industrial_production, ppi, usd_uzs, rub_uzs, gold_price, m2, fx_reserves_ex_gold and pos_turnover. Approved real industrial activity is kept in recovery observations separately from the nominal canonical master. POS comparable recovery remains capped at 2024-12. GDP remains in a quarterly target table. These mappings require reviewed reader wiring and provenance checks in a subsequent authorized integration phase; no model definition or coefficient change is needed for the data contract itself.

Network failures retained all previous observations and produced a degraded status. Critical USD schema/format/validation errors prevent publication; other invalid sources retain previous observations with explicit status. A future collection commit may therefore contain stale series: integration must inspect source statuses, freshness and admission decisions rather than treat a complete snapshot as proof of complete fresh coverage.

POS archive parsing/admission limitations documented in Phase 8A.2 remain unresolved; there is no new live evidence to resolve its failed articles, missing periods or extreme-change flags. Thresholds and December 2024 scope were not relaxed. New GDP periods still require documented FIRST_RELEASE realization evidence; SIAT update timestamps are not first-release evidence. Daily FX persistence remains independent of completed monthly eligibility and passed synthetic regression coverage; it was not live verified here.

Before integration: verify all nine adapters with actual downloads in an authorized environment, resolve or explicitly govern POS degradation, confirm GDP first-release evidence, verify the unattended identity, then review an explicit production-reader migration without altering the scientific model or silently regenerating its seal.
