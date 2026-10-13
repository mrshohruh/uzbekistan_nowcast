# Phase 8A.1 — fixed-schedule collection design

Audit date: 2026-10-12, Asia/Tashkent. This is a future implementation design. No scheduler, updater, model, transformation or production dataset was changed.

## Existing behavior

`config/production.json` resolves registry v1.2, the current policy and frozen models. `config/settings.yaml` defaults to v1.1 and is not the active production specification. The eight DFM fields agree with the acquisition and prospective input lists. U-MIDAS consumes USD/UZS log changes and lagged GDP; the headline combination is 50/50. The older AR2/USD ensemble remains shadow-only.

`scripts.operations.run_update` provides a reusable staged collection core. Acquisition executes when neither `--no-network` nor `--run-nowcast` is present. Its `--update-data` mode collects and validates data with model calculation disabled. Conversely, the documented `scripts.production.update --run-nowcast` skips collection. The production wrapper invokes the forecast builder even when passed `--update-data`. Neither command was executed in this audit.

## Recommended single entry point for Phase 8A.2

Provide one explicitly collection-only supported entry point reusing `python -m scripts.operations.run_update --update-data`. Define and test its contract before installing a task. Do not schedule `scripts.production.update --update-data`, which also rebuilds forecasts. Do not replace this core with the broad V1 bootstrap CLI: initial build and collect-vintage write other outputs and lack the production orchestration boundary.

Preserve existing series definitions, transformations, GDP target, admission gates and recovery exceptions. Publication and forecast execution should be an explicitly separate, serialized handoff after a committed data version. The current two-subprocess wrapper does not hold one lock across collection and publication.

## Fixed Windows schedule

Use exactly the **1st, 11th and 21st of every month in Asia/Tashkent**. No publication-calendar, hybrid or event-triggered checks. The user has not specified a clock time; select and document one during implementation. For example, 09:00 Tashkent could be an agreed choice, not an installed setting. On a Tashkent-configured host use local monthly triggers; otherwise verify the equivalent host/UTC triggers, with Tashkent at UTC+05:00. No scheduled task was created or inspected.

Use the absolute `.venv/Scripts/python.exe`, repository-root working directory, `PYTHONUTF8=1` and `PYTHONDONTWRITEBYTECODE=1`. The existing batch launcher sets these, but delegates to the forecast wrapper and is not yet a collection-specific launcher. Retain pinned requirements; no upgrades are needed for this audit. Confirm the historical inputs listed in `config/bootstrap_inputs.json` are installed and checksum-valid: fresh current downloads cannot recreate frozen historical vintages.

Verify the intended unattended account can read registry, sealed code and raw evidence and write raw/current_updates, staging, versions, metadata, processed/master files and operation reports. Test its proxy, network and certificate store separately. The audit's local proxy failure does not establish provider downtime or the task account's network state. No source credentials are required by the active adapters. Optional `UZNOWCAST_USE_SYSTEM_TRUST=1` requires truststore and valid OS roots; never disable TLS validation or bypass authentication, CAPTCHA or access controls. Do not log secrets or proxy credentials.

Configure one running instance. Preserve the existing lock and inspect transaction journals before recovering an interrupted run; do not automatically delete a stale lock. Establish bounded runtime for FX traversal and the POS archive. Current HTTP requests have (15,45)-second timeouts and three attempts with backoff; permanent schema/unit/auth/TLS failures should not be retried as temporary failures. Archive enumeration uses host `date.today()`; test date boundaries against the explicit Tashkent observation cutoff. Agree a missed-run policy without adding unscheduled source checks.

## Idempotency and vintage preservation

Current observation key: variable/period/frequency. Retained vintage identity additionally includes retrieval time, checksum and parser version. Existing append utilities deduplicate these identities. Comparison retains unchanged values and old provenance, and missing source rows never delete history. Repeated fetches may create additional immutable receipts intentionally. Economic-information fingerprints should remain stable when only the retrieval clock changes.

Archive bytes and sidecars before parsing: exact URL, retrieval time, observed update/release date, HTTP status, SHA-256, parser version and schema fingerprint. Unknown release dates remain null. Typical registry lags and SIAT dataset-update timestamps are not historical first-release dates.

Persist validated FX daily candidates and their vintages independently of whether a completed-month change is accepted. Current orchestration nests daily persistence inside the accepted monthly-period branch. Retain the distinct activation-date arithmetic mean and partial-month exclusion; do not introduce calendar-day filling or end-month substitution. The existing overlap window does not cover all possible old corrections; define a documented revision policy without silently widening scheduled crawls.

Version approved real-industry and reviewed POS overlay parents explicitly. Keep real SIAT 577 growth distinct from nominal registry SIAT 590. Real overlay changes currently bypass the canonical observation-vintage append list; transaction backups are useful but not a unified observation ledger. Link later forecasts to immutable input snapshots, overlay parent versions, GDP release records, specification hashes and committed source receipts.

## Staging and validation

Use immutable run-specific source archives and isolated candidate processing. Track reachability, HTTP/file success, parsing, validation and admission separately. Validate dates, frequency, national selectors, units, numeric values, unique sorted periods, missing periods, positivity, transformation lineage and coverage. Empty or changed-format downloads are failures.

De-cumulate nominal YTD flows within year before YoY calculations. Never de-cumulate published real-growth indices or quarterly GDP growth. Preserve GDP quarterly and keep the existing YTD target convention. Partial FX month changes, including comparisons involving partial lagged means, remain null. POS scope exclusions and documented GDP first-release admission remain explicit gates.

Propagate archive per-article errors and overlaps into source status. The current adapter discards this audit list; the audited POS article also fails its current parser with `KeyError: 'apreily'`. Correct and test parsing of the observed official month spelling without fabricating a period or relaxing conceptual scope. Page-parsed values should identify the actual page parent as well as retained attachment receipts.

Validate complete candidate outputs and provenance before promotion. Retain concurrency hashes, backups, journal and rollback. `os.replace` is atomic per file, not across the entire database. Readers must honor the lock/committed manifest, or a future version pointer published only after every required file passes validation. Test interruption, concurrency and rollback in an isolated workspace before allowing unattended promotion.

## No new data, repeated runs and source failure

- No new values: report `NO_INFORMATION_CHANGE`, retain current snapshots and forecast, and avoid unnecessary master rewrites.
- Repeated run: preserve unchanged canonical values/provenance, allow immutable retrieval receipts, reject ambiguous duplicate periods and retain the same economic fingerprint.
- Individual temporary failure: retain the prior valid series, collect independent sources, and name the stale/retained series in a degraded-run manifest.
- Critical USD schema/unit validation failure: abort promotion. Empty payloads, changed schema and unknown dimensions must never become valid empty observations.
- Partial archive success: propagate failed articles and coverage gaps; do not label the entire source clean because one article parsed.
- POS/GDP admission pending: retain prior production information and describe the evidence requirement. Do not invent release dates, replace the provider or fill unavailable values.

Define machine-readable success/degraded/aborted statuses and matching task exit codes. Separate accepted collection success from readiness to issue a new forecast. No automatic external messaging is proposed.

## Logs and implementation acceptance

Each run needs the scheduled local slot, actual UTC/local timestamps, run ID, source-stage statuses, URL/checksum/raw path, parser/fingerprint, rows and coverage, changes/revisions, withheld periods, committed hashes and exit status. Record environment/account identifiers without secrets. Preserve structured logs and source failure context.

Phase 8A.2 should address collection flag semantics, FX daily persistence, archive failure visibility, POS parsing and scope evidence, recovery overlay vintages, and collection/publication boundaries. Verify exact official sources under the unattended account and test unchanged/revised/partial/crash/rerun cases. Scheduling installation, new forecasts and scientific changes are outside this audit.
