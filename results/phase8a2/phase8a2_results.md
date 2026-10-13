# Phase 8A.2 — collection-only engine

Classification: **PHASE8A2_PARTIAL**. Implementation date: 2026-10-12, Asia/Tashkent.

The collection workflow is implemented and tested in isolation. Live verification remains unavailable, POS archive completeness/admission is degraded, and collection-version integration with sealed production readers is deliberately not enabled. No production data promotion, scheduler installation or GDP forecast execution occurred.

## What changed

- A supported `scripts.collection.run` entry point and `run_collection.bat` launcher collect the eight active predictors plus GDP, with no forecast-builder import or invocation. Dry/check modes stage candidates; an explicit commit publishes a collection version only.
- Existing approved SIAT, CBU and World Bank adapters and named transformations are reused. No inactive indicator or new provider is fetched. Approved real industry SIAT577 is distinct from the unchanged nominal SIAT590 canonical series.
- Validated daily USD/UZS and RUB/UZS changes are retained independently of completed-month admission. Existing activation-date arithmetic means, log changes and partial-month exclusions remain intact. Old values and revision provenance are retained.
- POS normalizes the exact evidenced `apreily`/`yanuary` spelling, parses the archived English XLSX attachment, checks reporting date/range, explicit million-sum unit, amount header, unique Total row and finite positive numeric amount. Page and attachment checksums/parents are distinct. The official March-2023 Total is 52,919,100.966056414 million UZS.
- Archive article failures, duplicate releases and missing periods reach run diagnostics and source status. Later POS candidates are retained as withheld run evidence outside committed data. Comparable POS recovery remains capped at December 2024, even if a candidate claims scope verification.
- Existing GDP documented-first-release admission rules are reused; no release dates are inferred from typical lags or SIAT update dates.
- Transport errors distinguish TLS, proxy/environment, temporary network, HTTP/authentication and format/schema failures. TLS/proxy failures are not retried; temporary errors have bounded retry/backoff. Every received payload is archived before interpretation with SHA-256 and timestamps.
- Collection snapshots publish one immutable directory and one atomic pointer. Hash-verifying readers retain a complete old version during interruptions. The shared legacy operational lock prevents overlapping writers; pending journals block subsequent runs. Explicit recovery never guesses a stale lock or automatically promotes abandoned candidates.
- Approved real-industry recovery observations/revisions have a separate ledger. A collection predictor view contains the eight production IDs and preserves POS scope; nominal industry never becomes real growth inside the canonical master.

## Commands and destinations

```powershell
.venv/Scripts/python.exe -B -X utf8 -m scripts.collection.run --dry-run
run_collection.bat --check-only --offline
```

Future collection-version publication, after operational review:

```powershell
run_collection.bat --commit
```

The commit command writes `data/collection/versions/<run_id>` and atomically advances `data/collection/current.json`. It does **not** replace production `data/master`, processed snapshots, metadata or forecasts. Use `scripts.collection.versions.current_snapshot` as the complete-version reader. `--store` and `--root` support separate evidence stores and isolated replicas. Historical cutoffs require offline replay. No live commit was executed here.

Run evidence includes collection.log, run_manifest.json, source_status.csv, source_receipts.csv, observation_decisions.csv, archive_audit.csv, validation_reports.json and a candidate manifest. New data retain observed source/reference/retrieval dates separately. Raw receipts live outside mutable processing stages and survive failure. Exit codes: 0 success/no change, 2 degraded, 3 aborted validation, 4 blocked configuration/lock/recovery.

## Archived and live outcomes

Archived dry-run evidence is `validation/archived_collection_result.json` and its companion CSVs. All nine source families reached parse success and processed validation with warnings. Industry, PPI, gold, M2, reserves and GDP retained their existing admissible observations. Both FX series produced **one new daily observation**, independently retained in the isolated stage while October's monthly change stayed withheld; latest completed monthly change remained September.

POS is not a clean archive success. The sampled official `apreily` page/attachment regression passes. The complete archived collection reports **44 failed articles and 14 missing periods**. Unsupported/changed layouts, missing files, unrecognized date spellings such as `avgust`, and nonmatching amount headers fail visibly. Two historical growth candidates, 2022-06 and 2023-01, hit the existing >50/extreme validation gate, so the entire POS candidate series was withheld and previous valid data retained. Nine post-2024 scope candidates were recorded as withheld. No threshold, transformation, scope or value was repaired to force admission. This is a remaining source/admission limitation, not a hidden parser success.

Genuine live verification passed for **zero sources**. Nine TLS-verified official initial requests on 2026-10-12 failed before provider contact at configured proxy 127.0.0.1:9, WinError10061. Every source is `LIVE_NOT_TESTED`, not declared down. No TLS/access-control/proxy bypass was used. `validation/live_checks.json` records exact URLs, timestamps and failure classes. These initial probes do not certify provider parsing or the unattended task account's network state.

## Seal and compatibility boundary

The audit-identified legacy orchestrator, acquisition adapter, HTTP downloader, POS parser and old launcher are included in the accepted production seal. They were not edited. No seal or acceptance record was regenerated. New files under scripts/collection, a new launcher, tests and official fixtures are additive; their code hashes are recorded in collection manifests, but they are outside the existing accepted runtime seal.

The new workflow fixes collection behavior without silently migrating production. The legacy production wrapper still has its old `--run-nowcast`/`--update-data` behavior; it must not be used for this collection-only runner. Existing production readers continue consuming their frozen masters. Connecting the new immutable version boundary to production requires an explicit reviewed integration/seal migration; no auto-acceptance is included. This compatibility boundary is a principal reason for PARTIAL classification.

## Tests and freeze evidence

See `phase8a2_test_results.md` for the final test count, twelve required scenarios, initial failures corrected and archived evidence. Testing uses short private Windows workspaces, with no model fitting or production forecast reconstruction.

Final freeze verification is recorded in `validation/freeze_verification.json`: original file hashes, accepted seal/current-version checks and the exact saved 2026Q3 nowcast. The reference remains **8.180901340616275%**, with DFM/U-MIDAS weights 0.5/0.5. Production models/policy/registry, original data, metadata, forecasts, dashboards and Phase8A.1 artifacts remain unchanged. No protected historical archive was changed.

## Remaining work and scheduling

The Windows launcher is prepared for exactly days **1, 11 and 21 in Asia/Tashkent**. No release-calendar/hybrid/event trigger or scheduled task was created. Installation is not yet operationally approved: verify the real task account's network/TLS and permissions, select a clock time and missed-slot policy, review POS archive/scope evidence, and agree the explicit production version-reader integration. A stale process lock still requires human inspection before removal; journal recovery alone does not bypass that protection.

The five requested deliverables are phase8a2_results.md, phase8a2_source_status.csv, phase8a2_test_results.md, phase8a2_automation_readiness.md and phase8a2_change_manifest.csv under results/phase8a2. Validation receipts, XML reports and freeze hashes are additional new evidence under its validation subdirectory. Temporary test replicas remain in ignored .tmp paths; no repository cleanup was performed.
