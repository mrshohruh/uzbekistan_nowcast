# Phase 8A.2 — isolated tests and validation

Final result: **108 tests passed, 0 failed, 0 skipped**. The final suite contains 35 collection tests and 73 maintained ingestion/configuration tests. The final report is `validation/tests_3064fda5.xml` (132.27 seconds). No production model fit or forecast reconstruction was run.

## Reproducible command

```powershell
.venv/Scripts/python.exe -B -X utf8 -m scripts.collection.test_runner tests/collection tests/test_registry.py tests/test_decumulate.py tests/test_siat_parser.py tests/test_cbu_fx_parser.py tests/test_cbu_m2_parser.py tests/test_prices.py tests/test_master.py tests/test_http.py tests/test_provenance.py tests/test_validate_series.py tests/production/test_configuration.py
```

The runner creates unique short private directories under ignored `.tmp/`, keeps managed Windows ACL inheritance, disables pytest cache/bytecode writes, and writes a new XML report. Each engine scenario has separate copied source configuration/data and its own collection store. Fake values/receipts are explicitly synthetic test inputs and never promoted to the repository's production database. Existing tests prohibit network. The official POS fixture bytes are frozen checksum-identical copies, not synthetic observations.

## Required scenarios

| Scenario | Tests/evidence | Outcome |
|---|---|---|
| 1. No new observations | test_no_new_observations_does_not_publish | No pointer/version publication; old production master unchanged |
| 2. New valid observation | test_new_valid_observation_commits_only_collection_version | Isolated collection version accepts the new period; original master unchanged |
| 3. Historical revision | test_historical_revision_retains_both_vintages; test_daily_revision_retains_original_and_reports_changed_date | Prior observation and new revision retained; original daily frame unchanged |
| 4. One source unavailable | test_unavailable_sources_retain_prior_values parameter | Previous source snapshot preserved; independent valid source can commit with exit2 |
| 5. Multiple unavailable | same test, three-source parameter | Degraded status and preserved old source bytes |
| 6. Changed/invalid format | test_invalid_source_data_never_enters_master parameters; POS unit/numeric/year regressions | Duplicate/unit/frequency/nonfinite inputs rejected; critical USD failure aborts publication |
| 7. FX daily without complete month | test_daily_fx_without_complete_month_is_retained, USD and RUB | Daily observation/vintage retained; October monthly change stays null |
| 8. Incomplete POS archive | test_incomplete_pos_archive_is_degraded_with_errors; duplicate/gap and failure/admission tests | Article errors, gaps and duplicates reported; old data retained on admission failure |
| 9. Identical repeat | test_identical_repeat_keeps_pointer_and_observation_identity | Committed pointer unchanged; append identities unique |
| 10. Interruption/recovery | test_interrupted_run_blocks_then_recovers_without_promotion; pointer-failure and published-journal tests | Pending journal blocks; unpublished stage abandoned; complete published version can finish its journal |
| 11. Concurrent run | test_concurrent_collection_is_excluded | Shared operational lock blocks second writer with exit4 |
| 12. GDP without first release | test_gdp_without_first_release_remains_withheld | New 2026Q3 candidate withheld; GDP remains quarterly through existing admitted period |

Additional tests verify post-2024 POS remains ineligible despite claimed scope, distinct real-industry recovery provenance, official POS date/unit/Total extraction, unique Total rejection, bounded HTTP/network retries, permanent TLS/proxy failure classification, immutable receipts for every HTTP attempt, corrupt-stage rejection and complete-version reader integrity. Maintained registry/parser/transformation tests verify named scientific transformations are unchanged.

## Official archived source exercise

`validation/archived_collection_result.json` records a full collection-only dry-run in a separate replica at observed cutoff 2026-10-05T18:59:59.999999Z. The registry, contracts and retained input files were copied; a checksum-verifying offline client read original immutable source bytes without modifying them. Configuration copies required by the existing FX adapter are included in the final staging implementation.

All nine source families reached parser success and series validation with warnings. The archived FX traversal produced one new daily activation per currency, while completed monthly admission remained unchanged. This exercises the audited persistence defect using actual archived official observations, in addition to synthetic unit scenarios.

POS passed the sampled `apreily` regression and full series parsing/validation-with-warnings, but its overall archived run is degraded: 44 article failures, 14 gaps, and two invalid admission candidates. The existing extreme gate withheld 2022-06 (small value difference above the existing threshold) and 2023-01 (growth about52.42). The prior POS series was retained, and nine post-2024 candidates were scope-withheld. No threshold or historical value was altered. See archived_archive_audit.csv and archived_observation_decisions.csv; parser success is not source completeness or production admission.

Frozen fixture provenance is in `tests/fixtures/collection/pos_receipts.json`. The page checksum differs from the attachment checksum. XLSX extraction verifies March2023 and Total52,919,100.966056414 million UZS with its exact English-sheet amount header. Tests explicitly reject wrong year, wrong unit, nonnumeric amount, duplicate Total and conflicting reporting-range date.

## Genuine live checks

Nine initial official requests attempted on 2026-10-12 failed at configured proxy 127.0.0.1:9 before provider contact. Genuine live source verification successes: **0**. All source statuses are LIVE_NOT_TESTED; proxy failures are classified NETWORK_ENVIRONMENT_ERROR without retry. TLS remains enabled and no access controls were bypassed. Initial-request checks do not claim successful provider parsing. The intended unattended Windows account still needs verification. Exact evidence is validation/live_checks.json.

## Development failures and verification limits

The first direct pytest invocation hit the managed Windows ACL issue on its restrictive temporary directory. The short-path runner corrects this without changing production. An early collection run exposed missing quality/vintage fields in copied recovery input, mixed ISO timestamp parsing, unrealistic synthetic RUB scaling and an overbroad synthetic POS perturbation. These were corrected; no production value was changed. Archived integration also exposed the existing FX adapter's unconditional source-contract read, now supplied in the isolated stage. Earlier XML reports remain as development evidence; the final XML is authoritative.

The initial failing suite had 8 failures/21 passes, followed by targeted debugging runs. A 102-test suite then passed, followed by 29 collection rechecks and four publication checks. The final expanded suite passes all108 tests. Counts are distinct final tests, not a sum of repeated executions.

No power-loss hardware test, real task-account launch, full live download, real production promotion or scheduler installation was performed. Actual process termination can leave a stale shared lock; recovery requires verifying no live writer holds it. Existing production readers have not been migrated to collection versions. Unsupported POS formats/spellings remain explicit failures rather than guessed observations.

## Production freeze

`validation/freeze_verification.json` checks SHA-256 for 1,961 original files, accepted runtime seal81 files and the recognized current data version. Existing production models, source contracts, registry, data/metadata, forecasts and dashboards remain unchanged. The stored 2026Q3 reference is exactly **8.180901340616275%**; arithmetic 0.5×DFM + 0.5×U-MIDAS verifies it without generating a new forecast. No seal or acceptance record was regenerated.
