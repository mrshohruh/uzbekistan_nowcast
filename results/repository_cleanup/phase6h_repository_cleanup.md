# Phase 6H repository cleanup

**PHASE6H_PARTIAL_CONSOLIDATION**

The M0 DFM, USD/UZS U-MIDAS, 50/50 policy, coefficients, information rules and saved current nowcast are unchanged. This is a partial consolidation because immutable operational locks still require historical phase kernels and artifact paths. No checksum seal was regenerated to disguise those dependencies.

## Baseline and recoverability

Baseline commit: `f2f34d482b30c6e04fe258b5878243848601571c`. Five recent commits and the original working-tree status are in `pre_cleanup_manifest.json`. There were 722 pre-existing status entries, including inaccessible vendored files reported by Git as deleted. These were not restored, staged or committed.

85 important inputs/metadata artifacts were not tracked (including intentionally ignored generated data). They were preserved. Exact replay from a clean checkout therefore requires the preserved data/vintages; network bootstrap can ingest official data but cannot promise the same historical vintage. Git history was not rewritten. No new sources were fetched during freeze validation.

## Counts and removals

| Inventory | Before | After |
|---|---:|---:|
| Accessible files in declared inventory scope | 35473 | 35175 |
| Python files in that scope | 1390 | 1344 |
| Test files in that scope | 141 | 133 |
| Maintained Python files under src/scripts/tests | 235 | 189 |

463 explicitly audited tracked files were removed or relocated, plus 7226 files in disposable validation workspaces created during this phase; 35010 of the 35473 originally accessible paths remain. New evidence affects total counts, so counts are not a claim that every new file is maintained source. Traversal exclusions/access failures are listed in the manifests. Python classifications cover all inventoried Python paths, including historical copies; uncertain files remain intact.

Rejected Phase 6F and Phase 6G/G1/G2/G3/G4/G5 executable experiments, their dedicated tests and recoverable results were removed. Raw CBU source evidence under `results/phase6f/raw/` was preserved. Protected historical Phase 4/5/6B/6C/6D artifacts and untracked results were retained. Inaccessible or dirty candidates were preserved; see `cleanup_exceptions.json`. Affected result directories and their remaining existence are listed in `removed_result_directories.json`; directories containing preserved files may remain.

## Architecture and functions

`scripts/production/{models,diagnostics,dashboard,run,update}.py` owns the current implementation. Twenty-eight function/test migrations are recorded in `function_migrations.csv`; old Phase 6E modules are thin compatibility imports, not duplicate implementations. Current production tests are discovered under `tests/production/`. `config/production.json` resolves the existing frozen sources of settings through `scripts.production.config.configuration`. It does not redefine scientific values. `results/current/index.json` and `results/diagnostics/index.json` locate authoritative outputs without copying datasets or breaking sealed paths.

The duplicate-function AST audit is saved before and after. No growth, standardization, factor, GDP or release formula was replaced. Remaining duplicate implementations inside frozen historical source are retained because changing their bytes invalidates operational locks. Full removal of those dependencies would require an explicit migration of the sealing protocol and independent reproduction, beyond a cleanup that preserves current locks.

## Tests and validation

- repository: 284 passed, 0 failures, 0 errors, 0 skipped.
- operations: 56 passed, 0 failures, 0 errors, 0 skipped.
- dfm: 19 passed, 0 failures, 0 errors, 0 skipped.
- vintages: 19 passed, 0 failures, 0 errors, 0 skipped.

The original repository test run exposed a Windows locale decoding failure in Git-diff capture. The validation runner now starts Python in UTF-8 mode; frozen model source was not edited. Three stale operations assertions were corrected: private news perturbation now changes an actually used month, the September gold parser comparison uses an explicit August information set, and a historical live-master checksum assertion was replaced by current-data preservation checks around the private worker.

Two checksum-locked historical inventory tests remain byte-preserved outside the current suite. Their original failures are recorded in `dfm_tests.log` and `vintage_tests.log`: they compare today's promoted dashboard/data against obsolete research snapshots. Current unit suites retain 19 DFM and 19 vintage tests; scientific preservation is checked separately against the Phase 6H baseline. They were not marked as passing or silently rewritten.

The production updater completed in dry, cached historical replay mode with `NO_INFORMATION_CHANGE`; no snapshot or master was promoted. Provider/network availability was not checked. The console's historical implementation-test count is not this phase's test count; use the JSON/XML reports here.

The complete pre-cleanup build, post-cleanup build and independent deterministic rerun all succeeded without publication. Generated scientific CSV/JSON outputs and dashboard HTML are byte-identical. Relocated code paths/hashes in run manifests and operational logs/reports are excluded from byte identity.

| Output | Before | After | Independent rerun |
|---|---:|---:|---:|
| dfm_forecast | 8.301152885464585 | 8.301152885464585 | 8.301152885464585 |
| umidas_forecast | 8.060649795767965 | 8.060649795767965 | 8.060649795767965 |
| combo_50_50_forecast | 8.180901340616275 | 8.180901340616275 | 8.180901340616275 |
| final_forecast | 8.180901340616275 | 8.180901340616275 | 8.180901340616275 |

Frozen source, registry, processed observations, masters and provenance metadata match baseline checksums. The authoritative saved policy and nowcast remain untouched. `production_comparison.json` records exact equality, not rounded display equality.

## Dependency and dead-code checks

The active dependency audit includes AST imports, literal data/config paths, explicitly resolved dynamic worker imports and staged directory dependencies. No retained active import points to removed Phase 6F/6G modules. Active source parses successfully. Historical manifests still reference historical artifacts; these are evidence, not rewritten production configuration. Unknown roles were retained rather than guessed unused.

Full phase-free operation and exact clean-checkout reconstruction are not claimed. Remaining frozen kernels and ignored data are listed in `production_dependency_audit.json` and the baseline. The current README describes the active V2 policy, commands, inputs and output pointers.

## Git status

The final status is recorded verbatim in `git_status_after.txt`. All changes remain reviewable in the working tree; no commit, index modification, history rewrite, model search, coefficient change or nowcast publication was performed.
