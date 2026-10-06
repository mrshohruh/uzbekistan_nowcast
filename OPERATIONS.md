# Automated data refresh and nowcast operations

Run commands from the repository root. The established Windows environment is
`.venv`; `run_nowcast.bat` uses it and forwards command-line arguments.

```powershell
# Normal update: check approved sources, stage validated changes, run frozen models.
.venv/Scripts/python.exe scripts/operations/run_update.py

# Check sources and candidate data without promoting data or fitting models.
.venv/Scripts/python.exe scripts/operations/run_update.py --check-only

# Retrieve and validate candidates; reproduce forecasts; write no current data/ledger/dashboard.
.venv/Scripts/python.exe scripts/operations/run_update.py --dry-run

# Reproduce stored information without checking provider availability.
.venv/Scripts/python.exe scripts/operations/run_update.py --no-network

# Safest first run, entirely offline.
.venv/Scripts/python.exe scripts/operations/run_update.py --dry-run --no-network
```

Python must have the repository requirements installed. The entry point adds the
repository and `src` to its import path; it does not require notebook state.
No task scheduler or background service is installed by this phase.

Each call creates a distinct `results/operations/update_.../` directory. Find the
operator summary in `update_report.md`, console output in `console_summary.txt`,
pre-run Git/input/frozen hashes in `pre_run_state.json`, and completion status in
`run_manifest.json`. `source_status_before.csv` and `source_status_after.csv`
describe coverage and stale/missing variables. Release lags are planning metadata;
unknown observed release dates remain null. The freshness calendar reuses
`information_cutoff_for_variable`, including month-end publication-lag timing.

`source_receipts.csv` lists immutable raw responses, checksums, HTTP status and
actual retrieval times. Successful and failed HTTP responses are archived using
the existing acquisition code, with per-run copies under
`data/raw/current_updates/<run_id>/<variable>/`. Failed retrievals never erase
stored data. Offline receipts explicitly say that no new retrieval took place.
Read `operations.log` and `update_failure.json` for failures.

The approved real industrial adapter validates SIAT table `577` through its
descriptor URL and resolved payload URL, and separately validates internal
indicator code `1.02.01.0004`, name, Percent unit, monthly frequency and the exact
national selector. It retains the frozen published index-minus-100 convention.
Identical raw indices with CSV serialization differences within two raw-index
ULPs retain the approved old transformed values; a changed raw index remains a
revision candidate. Evidence is in `results/operations/source_validation_fix_report.md`.

Current-month USD/UZS and RUB/UZS candidates are `PARTIAL_CURRENT_MONTH`, with
`accepted=False`. Their daily payloads are archived, but incomplete monthly
means and missing transformed changes do not count as historical revisions or
replace completed-month data. Frozen FX transformations and availability masks
still apply. Candidate acceptance in check-only reports never means promotion.

`data_changes.csv` distinguishes unchanged observations, new periods, revisions,
source omissions, schema failures and invalid data. `revisions.csv` records
accepted historical changes. Source omissions retain the old observations and
provenance. Suspicious candidate values are withheld, and critical USD validation
failure aborts the transaction. Data-source failure can still permit calculations
on the retained usable information set. No substitute predictor is selected.

Candidate processed files, metadata, masters and shadow outputs are built in
`data/staging/<run_id>/project/`. Exact model/specification hashes are checked
beforehand. The monthly master retains the registry's column order and missing
values; GDP remains separate and quarterly. All validations and forecast
reproduction precede promotion. Unchanged master contents retain their original
bytes, rather than being re-exported solely because a source was checked again.

Promotion atomically replaces individual files under a single operations lock.
Old files are copied to `data/versions/<run_id>/` with a transaction journal;
in-process promotion failure restores them. Multiple files cannot be replaced as
one filesystem operation. An interrupted journal/lock blocks subsequent runs.
Inspect `transaction.json`, compare its before/after hashes and recover from its
backups before removing an interrupted lock; do not blindly delete the lock or
publish from an incomplete transaction. Only a committed manifest identifies a
completed update. Immutable snapshot assets/batches are installed before the
append-only ledger mirror. External readers should wait for the operation to
finish or honor the same lock.

`current_state_manifest.json` records current/candidate master, registry, code,
source and model hashes, forecasts and a semantic information fingerprint. Dry
and check manifests say `candidate_only: true` and `promoted: false`. They are not
publication approvals. Current-state evidence succeeds the Phase 6E.1 manifest;
the September 30 historical production release and its missing-input hash gate
are preserved. Historical manifests are never rewritten.

Production reproduction is in `production_forecasts.csv`. The seven frozen shadow
models are in `shadow_forecasts.csv`. Production retains its existing current-GDP
vintage/registry-lag policy; the shadow retains strict documented GDP vintages, so
their benchmark forecasts can differ. `forecast_revisions.csv` compares the prior
same-target shadow snapshot, and `changed_model_inputs.csv` describes changed
observations. It does not claim an exact causal decomposition.

The existing Phase 6D target selection, H1/H2/H3 calendar, release masks,
calculations, snapshot writer, scoring and dashboard generation execute unchanged
inside the isolated project. A small input adapter supplies newly approved real
industrial-production observations from SIAT 577; the canonical ingestion
industrial-production variable retains its separate nominal-flow definition.
The already archived SIAT 577 descriptor is the authority for its endpoint.
No source identifiers or alternate variables are guessed.

Information-set fingerprints include masked active values, full U-MIDAS USD
history, eligible GDP values/publication dates, target, horizon/stage and frozen
specifications. They omit incidental run/retrieval timestamps and provenance
formatting. A match to an existing non-withdrawn snapshot is
`DUPLICATE_INFORMATION_SET`: the writer is skipped, preserving snapshots and all
ledger bytes. Thus a routine date advance by itself does not create artificial
prospective history. A changed horizon, release mask or eligible observation can
create a legitimate new snapshot. Dry runs never append.

The current dashboard is `dashboard/phase6d_shadow_monitor.html`, labelled
**RESEARCH SHADOW — NOT PRODUCTION**. It is updated through the original Phase 6D
writer only when a valid new information set is recorded. Other historical
dashboards are preserved.

GDP API changes are reported as `GDP_VALUE_DETECTED_UNVERIFIED` and are withheld
from automatic quarterly-master promotion and realization registration. A dataset
update time is not first-publication evidence. Use the existing Phase 6D official
document archival/review and `--realization` interface to register an actual
verified first release. The updater then uses the existing strict scorer on
already recorded forecasts; it does not re-estimate specifications or weights.
The scorer writes separate views and never fills forecast errors into the ledger.
Governance remains INITIALIZED / EARLY_EVIDENCE / INSUFFICIENT_EVIDENCE /
PRELIMINARY_REVIEW / GOVERNANCE_REVIEW_ELIGIBLE at 0 / 1 / 2 / 3 / 4+ realized
quarters. No model is promoted automatically.

POS is actively checked through the existing public CBU payment archive. The
POS/E-POS definition break prevents automatic admission after December 2024;
such candidates are reported as `SCOPE_VERIFICATION_REQUIRED` and remain missing
in the shadow input panel. There is no interpolation, extrapolation or alternate
payments-variable substitution. A genuinely reviewed coverage extension can be
supplied in `config/operations_pos_scope_review.json` with `approved_assets`.
Each asset must contain `receipt_file` (an archived official HTTP-success CBU
receipt), matching `checksum`, `unit: "million UZS"`, `reviewer`,
`definition_evidence`, `scope_verified: true`, `values_verified: true`, and
`observations` with `period`, `raw_ytd`, `value_verified: true` and an actual
`extracted_excerpt`. This review file is never generated automatically. Reviewed
monthly YTD extracts are processed by the original Phase 6A2 `safe_flows`
function: consecutive months, same within-year vintage, January reset, positive
flows and exact 12-month log growth. Missing predecessors remain missing. The
adapter admits only reviewed feasible transformed values, without altering the
frozen model or old snapshots.

Additional switches:

- `--update-data`: validate/promote data only; skip model fitting and snapshot append.
- `--run-nowcast`: use stored data and skip acquisition; a new snapshot still needs
  an intact official GDP source check satisfying Phase 6D's existing 24-hour rule.
- `--as-of YYYY-MM-DD --no-network`: historical reproduction, automatically read
  only; future dates are rejected. Missing historical checks/vintages cause a
  visible failure, never fabricated historical knowledge.
- `--force-source VARIABLE`: explicitly request a fresh check for that variable;
  normal network updates already refresh every active source.
- `--verbose`: increase structured acquisition logging.

All source checks are bounded by the existing timeout/retry and official-host
policies. A new snapshot cannot be committed with an expired/unverified GDP check
or unusable critical inputs. Source failures, stale POS and missing release dates
stay visible in the report. A failed run is `UPDATE_ABORTED`; nothing is silently
repaired.

Offline checks are run in isolated groups with
`scripts/operations/run_tests.py`; Windows temporary paths inherit workspace ACLs
and stay short enough for snapshot filenames. Test evidence is under
`results/operations/implementation_tests/`, and aggregate results are in
`implementation_test_results.json`.
