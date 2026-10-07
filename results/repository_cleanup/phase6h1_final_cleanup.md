# Phase 6H.1 final repository minimization

**PHASE6H1_FULLY_CONSOLIDATED**

The current production system works from committed code and explicitly restored external data. All frozen scientific outputs match exactly. Historical phase implementations and compatibility namespaces are absent from the active runtime.

## Git protection and commits

- Safe Phase 6H checkpoint: `fe252655d79648c8af3132f3c1d635db3bdd2253`.
- Production seal and historical-runtime removal: `e6a9def417a0b9c44a388a1c4e174f36ce2ac2bf`.
- Obsolete pilot-launcher removal: `800f5e5a543a4744f0259fb2b1ac21cfb34841b5`.
- Final code revision tested in a fresh checkout: **`73f1f1a7ff374be5500a3f7f012a6ec641605982`**.
- The subsequent audit-only commit records this final validation; it changes no sealed runtime/configuration or scientific data.

Every commit used an explicit path list. No `git add -A`, `git clean -fd`, or `git reset --hard` was used. The checkpoint excluded 721 pre-existing dirty paths; those historical vendored dependencies and synthetic workspaces were later classified deliberately and removed under this task. No unrelated pre-existing source changes were staged. Final Git status is recorded in `phase6h1/final_git_status.json`; local run/cleanup outputs remain untracked where appropriate. The fresh checkout started with no tracked changes and ended with only its generated test XML changed.

## Counts and scope

| Measure | Before | After |
|---|---:|---:|
| Maintained Python files (`src/`, `scripts/`, `tests/`, checkpoint versus validated code) | 190 | 100 |
| Test files in those scopes (`test_*.py`) | 43 | 23 |
| Executed retained test cases | 378 | 202 |
| Total tracked files, checkpoint versus final audit commit | 3,391 | 805 |
| Physical files under `data/staging/` | 9,666 | 0 |
| Original raw archive files | 22,609 | 22,609 |

Counts use the Git checkpoint for a reproducible code baseline; the preceding Phase 6H physical audit reported 189 maintained Python files before the checkpoint helper was added. Total tracked counts include the final audit evidence and exclude intentionally ignored data. The independently validated code commit contains 788 tracked files. Removed-file evidence contains **34,663 unique paths**, with categories: {'F: research-only': 149, 'G: generated/staging': 32272, 'D: historical checksum/evidence-only': 2230, 'E: compatibility-only': 12}. Generated synthetic copies account for most physical removals. No arbitrary file-count target was used.

## Scientific equivalence

| Output | Exact value |
|---|---:|
| M0 DFM | 8.301152885464585 |
| USD/UZS U-MIDAS | 8.060649795767965 |
| 50/50 final | 8.180901340616275 |

The old seal was reproduced before migration. The new architecture, independent deterministic run, and two fresh-checkout builds reproduce **all 17 scientific artifacts byte for byte**: current nowcast JSON, DFM structure/loadings, U-MIDAS coefficients/contributions, historical reproduction, matched forecasts, metrics, news, freshness/drivers, and dashboard. Run manifests and policy operational code-location/checksum metadata are the only excluded comparisons. Specification hashes, coefficients, inputs, transformations, target definition, release masks, and 0.5/0.5 weights remain unchanged.

GDP remains quarterly and retains the published cumulative YTD real GDP YoY convention. No raw observation, release date, or retrieval timestamp was changed. Prospective validation remains pending; the original historical-vintage limitations remain documented.

## Current production seal

`config/production_seal.json` protects **81 runtime/setup/configuration files** and records **63 initial replay inputs**. It covers current production/operational modules, reusable library code, registry, model/transformation definitions, bootstrap manifest, pinned requirements, package setup and batch entrypoint. `config/production_seal_acceptance.json` explicitly accepts the tested candidate.

The seal enforces current code/configuration hashes and active policy/specification hashes. Version checks enforce master, processed, recovered-data and provenance checksums, permitting successors only through successful committed transactional manifests. Staged candidate calculations remain possible before promotion. Tests reject code tampering, unexplained provenance changes, altered bootstrap bytes, and path traversal.

Every candidate revision and earlier acceptance is retained in `phase6h1/candidate_revisions/`. Old seal evidence remains in `phase6h1/old_baseline.json` and Git. Revision 05 fixes an actual Windows bootstrap failure: equivalent `\\?\` path spellings are normalized after link resolution before containment checks. No containment or checksum check was disabled. The failed attempt and diagnostic are preserved. Text runtime hashes normalize CRLF to LF; `.gitattributes` preserves scientific artifacts and immutable records byte for byte.

## Removed implementations and migrated functions

Removed: `scripts/phase6e/`; research kernels under phase6a2, phase6b, phase6b1, phase6b2, phase6c and phase6d; phase4b/phase4c/phase5c model modules; phase5a/phase5b/phase5b1 implementations and old dashboards; historical shadow infrastructure; unused development evaluators; tests for removed implementations; duplicate pilot/fixture launchers; one-time registry builders; stale root state/start documents and generated logs.

Current reusable functions are:

- `uznowcast.models.dfm`: `mask`, `standardize`, `training_panel`, `estimate`, `quarterly`, `bridge`.
- `uznowcast.gdp_vintages`: `available_gdp_vintage_as_of`, `assert_boundary` and vintage validation.
- `uznowcast.transforms.vintage_flows`: `safe_flows`.
- `uznowcast.operational.forecast`: release-aware datasets, target/stage detection, and existing operational forecasts.
- `scripts.production.benchmarks`: GDP-gated benchmark calculations.
- `scripts.operations.prospective`: current monitoring, immutable ledger/snapshot governance and evaluation.
- `uznowcast.storage`: content-addressed immutable records.

Historical content-addressed code objects remain solely as required snapshot provenance. They are not imported as an active namespace. Registry-driven ingestion and official FX bootstrap utilities remain supported.

## Staging and generated workspace cleanup

The updater seeds only an explicit projection of sealed runtime/input files and necessary operational records. It removes its staged project after validation. No full historical research tree is copied into the active stage. Historical pytest roots, browser profiles, rerun copies and the migration's own failed test workspace were inventoried individually and removed. Staging now contains zero files.

Automatic approval review initially rejected broad directory deletion. The replacement was approved only after exact file inventories, saved test constructors, unchanged-file guards, exclusion of all required evidence paths, and 17 exact rerun-copy comparisons established the generated scope. No cleanup remains blocked.

## Raw data and provenance

All **22,609 original raw files / 2,367,280,664 bytes** remain. Fresh SHA256 hashing found **4,435 duplicate groups / 6,011 extra identical copies**. None were deleted. The audit is `phase6h1/raw_duplicates_verified.json`.

The explicit bootstrap lists **9,213 data/source-evidence files**, with checksums verified on restoration. It documents **669 already-missing historical raw references** as missing; no replacement, endpoint or release date was fabricated. Fourteen official source files remain under `results/research/phase6b2/evidence/` as a protected source-evidence exception, with no historical runtime code. Original immutable receipt paths are retained and resolved through `config/provenance_relocations.json`.

## Dependencies and tests

The actual reconstruction trace loaded 60 repository modules. The dependency/path scan found **zero active references to deleted phase directories or imported historical kernels**. `phase6h1_runtime_dependencies.csv` classifies current runtime, data, validation, old checksum-only, compatibility, research and generated dependencies. The dead-code scan records 40 unused-import candidates for context; these are minor import/re-export candidates, not retained historical implementations.

The final committed-checkout suite passes **202 tests, zero failures, errors or skips**. The taxonomy in `phase6h1_test_inventory.csv` covers CORE_DATA, TRANSFORMS, DFM, UMIDAS, COMBINATION, INFORMATION_BOUNDARY, RAGGED_EDGE, PROVENANCE, PARSERS, END_TO_END and DETERMINISM. GDP leakage, observed release/retrieval gating, missing values, transformations, current numerical models, 50/50 reconciliation, provenance, rollback and deterministic estimation remain tested. Historical implementation-snapshot tests and the obsolete determinism-file skip were removed.

## Fresh-checkout verification

A temporary clone of commit `73f1f1a7ff374be5500a3f7f012a6ec641605982` received a **new Python 3.12 virtual environment**. Pinned requirements were installed from downloaded official wheels, then the editable package was installed from that checkout. `pip check` passed. No existing virtual environment or working-tree source code was copied.

Only `scripts.operations.bootstrap` and `config/bootstrap_inputs.json` supplied the intentionally external data. Package origins and the accepted 81-file seal were verified inside the clone without `UZNOWCAST_SEAL_MIGRATION`. Two production runs matched the old baseline exactly; all 202 tests passed; the safe/dry updater returned `NO_INFORMATION_CHANGE`, appended no snapshot, and reported no unexpected protected changes. The temporary checkout was removed after all evidence was recorded, with exact target, temporary-parent, commit and origin checks.

Machine-readable proof: `phase6h1_clean_checkout_validation.json`. Logs, environment versions and final test XML are retained beside it. README documents installation, explicit data restoration, production execution and current tests. A new official download does not replace archived frozen vintages.

Required deliverables: `phase6h1_removed_files.csv`, `phase6h1_runtime_dependencies.csv`, `phase6h1_seal_migration.csv`, `phase6h1_test_inventory.csv`, and `phase6h1_clean_checkout_validation.json`.
