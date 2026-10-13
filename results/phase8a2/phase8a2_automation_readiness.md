# Phase 8A.2 — Windows automation readiness

Status: **runner prepared; installation pending operational verification**. No scheduled task is installed or activated.

## Supported launcher

`run_collection.bat` sets repository-root cwd, uses the existing `.venv/Scripts/python.exe`, enables UTF-8 and disables bytecode writes. It invokes only `scripts.collection.run` and propagates its exit code. It does not use `run_nowcast.bat` or the production wrapper.

Use `run_collection.bat --dry-run` for isolated downloaded-candidate validation and `run_collection.bat --check-only --offline` for archived validation. Use the explicit future `run_collection.bat --commit` only when publication to the collection-version store is intended. Collection commit never changes production masters or calculates forecasts. The default is dry-run.

## Fixed scheduling contract

Exactly **1st, 11th and 21st of every month**, Asia/Tashkent. There is no release-calendar dependency and no hybrid/event-triggered check. Run manifests record these days, UTC and Tashkent timestamps, cutoff, unique run ID and mode. Observation eligibility uses Asia/Tashkent; historical replay requires --offline.

No clock time was specified or installed. Choose one during scheduler installation; verify the host's timezone and UTC+05 conversion. Configure one running instance and decide how to report a missed slot without adding unrequested event triggers. Task Scheduler configuration remains outside this phase.

## Dependencies and permissions

- Existing pinned Python environment and requirements.txt/requirements-models.txt; no upgrade or replacement environment was installed.
- Read access to sealed runtime/config/registry, existing processed/master/current data, vintage metadata and archived raw files.
- Write access to the selected collection store and the shared data/staging operations-lock directory. Normal collection commits only modify the collection store; legacy production paths remain protected.
- Task-account HTTPS access to official SIAT/CBU/World Bank hosts. TLS stays verified. Optional system trust must have the existing truststore package and valid installed roots; never disable verification or bypass access controls.
- Sufficient storage for immutable receipts, complete versions and retained run evidence. Future retention policy must preserve source and observation vintages rather than blindly delete them.

Live verification currently fails at the environment proxy before provider contact. The intended task account has not been tested; do not assume interactive proxy/CA settings apply to it. No active source adapter requires private credentials. Do not put secrets in the registry, launcher or logs.

## Status and recovery

Exit 0: validated, committed or no information change. Exit 2: degraded sources/partial archive, with retained prior values and optionally committed independent valid series. Exit 3: validation abort, no version publication. Exit 4: blocked lock/config/seal/interruption. The run_manifest is the authoritative detail; Task Scheduler success alone does not imply every source succeeded.

Inspect source_status, source_receipts, validation reports, decisions and archive errors. TLS/proxy failures are permanent for the run; temporary timeouts/connections/429/5xx use bounded retries. Per-request timeouts are (15,45) seconds. Overall archive runtime still depends on the number of official pages/files; establish a tested task wall-time policy under real network conditions.

The shared legacy lock excludes duplicate scheduled/legacy writers. Pending legacy transactions and new collection journals block the next run. After inspecting the interrupted run and ensuring no live writer holds the lock, use `run_collection.bat --recover-run <run_id>` to reconcile the journal. It finishes an already fully published snapshot or abandons unpublished candidates without data promotion. It never guesses/removes stale process locks. Preserve the failed receipts/stage for diagnosis.

## Reader and production compatibility

Use `scripts.collection.versions.current_snapshot(store)` for hash-verified, complete immutable inputs. Versions publish through a directory rename followed by one atomic pointer replacement. Old versions stay readable and canonical production files are untouched. The collection snapshot includes canonical monthly/quarterly data plus a separate approved production-predictor view: real industry and POS recovery remain distinct from nominal canonical inputs.

The accepted production seal remains unchanged and valid. New collection modules are additive and outside that seal; manifests record their code hashes. Existing production readers are not redirected. A reviewed version-reader/production integration and explicit seal policy are needed before claiming unattended end-to-end production updates.

POS eligibility stays <=December2024. The observed `apreily` attachment parses correctly, but full archive gaps, unsupported formats/headers and extreme historical growth admissions remain visible blockers. New GDP admission still needs documented first-release evidence. These gates must remain enabled on scheduled runs.

Installation checklist remaining: working task-account live access; account/path permissions; agreed clock/missed-slot behavior; tested wall-time/exit monitoring; stale-lock recovery procedure; POS review; explicit production integration. No schedule, production promotion or forecast was executed.
