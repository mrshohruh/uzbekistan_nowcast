# Safe repository cleanup — Phase 6E.0

**CLEANUP_PARTIAL**. Cleanup actions and frozen forecast reconstruction are verified. No model specification, source kernel, production output, prospective ledger, withdrawal or realization record was changed. No commit or reset was performed.

The current masters already differed from the saved production release before cleanup. The four production forecasts reproduce exactly at their recorded H2 stage, but the full production configuration gate rejects the newer master hashes. The historical monthly and quarterly master hashes were not found among any readable repository files. This pre-existing blocker prevents the stricter CLEANUP_SUCCESS classification; the cleanup did not repair it by changing model code or data.

## Before and after

| Item | Before | After |
|---|---:|---:|
| Project files, including archive | 20012 | 19894 |
| Project bytes, including archive | 2419259155 | 2417261610 |
| Active-tree files, excluding archive | 20012 | 19669 |
| Active-tree bytes, excluding archive | 2419259155 | 2413515976 |
| Python files | 158 | 159 |

The same comparison scope excludes `.git`, the installed `.venv` and `results/cleanup/` audit and validation outputs. Before: 535 nonempty file-parent directories recorded (empty/opaque directories excluded); 1052 cache/temporary files. Original result artifacts: 1881. Archive moves reduce active-tree clutter, not disk usage. Cache deletion reclaimed 2,013,051 bytes; net project-byte reduction after new maintenance documentation/utilities is 1,997,545 bytes.

## Actions

- 225 files archived with preserved paths and matching SHA256; 3,745,634 bytes retained in archive.
- 119 regenerable cache files permanently removed. No Python source was permanently removed.
- 0 Python files archived. No standalone legacy runner met all dead-code conditions: old phases remain pinned by hashes, imports, tests or reconstruction references.
- 0 redundant cache duplicates removed. Semantic raw-vintage duplicates, frozen references and snapshot code copies remain intact.
- Historical dashboards archived: 0. Frozen and current dashboards stay at their original paths.
- User changes and 695 pre-existing deletions were preserved. Unknown files and third-party recovery dependencies were retained.

Every mutation is listed in `archived_files.csv` or `deleted_files.csv`. `cleanup_plan.csv` records the pre-quarantine decisions and reasons. Archive integrity was checked after moves. Restore an archived file by reversing its recorded source/destination pair; there were no archive failures or missing active imports requiring restoration.

## Active code and paths

140 Python files are reachable from operational, ingestion, shadow, reconstruction, documentation or test roots. The dependency graph combines AST imports, identifiable dynamic imports, script/CLI path literals, exact textual references, configuration, documentation and test entry points. Unknown dynamic dependencies are retained. `dependency_edges.csv` and `active_python_inventory.csv` provide the file-level evidence.

Read `ACTIVE_CORE.md` for the operator entry-point map. Production uses the operational Phase 5B.1 stack and AR1/AR2/USD U-MIDAS(3)/equal-weight ensemble. The shadow monitor retains `scripts/research/phase6b2/run.py`, `vintages.py`, `scripts/research/phase6c/kernel.py` and all Phase 6D modules. The eight-variable DFM remains one factor, AR(2), bridge B and quarterly mean. Combination weights remain exactly 0.5/0.5 and 0.5438822544881572/0.4561177455118428. POS after December 2024 remains missing.

Older results, dashboards, documentation and runners pinned by current hashes were deliberately kept. `results/phase6d/` was preserved in full, including its existing test/cache folders. This limits reclamation to 344 independently safe files; path stability takes precedence over a larger cosmetic consolidation.

## Verification

- 19,521 protected files checked; 0 unauthorized hash changes.
- 225 archived files checked; 0 archive integrity failures.
- 379 tests passed, 0 failed, across repository, Phase 6A2, 6B, 6B.1, 6B.2, 6C and 6D groups. Baseline exclusion tests also passed before quarantine.
- Import/syntax validation passed for 158 retained Python files. Effectful runner scripts were syntax checked; their pure operational/shadow dependencies executed in the smoke tests.
- Phase 6D ledger unchanged: True. Existing snapshots unchanged: True. Validation reconstructs saved observations, GDP vintages and the original timestamp without calling the operational writer, fetching sources or appending a prospective snapshot.
- Production calculations and input hashes are identical before and after cleanup. The saved production headline reconstructs at the recorded H2 stage. Current input hashes differ from the saved release; the configuration blocker is documented in `validation_production.json` and `production_historical_input_lookup.json`.

| Model | Before | After | Absolute difference |
|---|---:|---:|---:|
| AR1 | 8.114253474802 | 8.114253474802 | 0 |
| AR2 | 7.457305185501 | 7.457305185501 | 0 |
| UMIDAS_USD | 8.060649795768 | 8.060649795768 | 0 |
| PRODUCTION_ENSEMBLE | 7.758977490634 | 7.758977490634 | 0 |
| PHASE6C_DFM | 8.301152885465 | 8.301152885465 | 0 |
| COMBO_50_50 | 8.180901340616 | 8.180901340616 | 0 |
| COMBO_DEV_WEIGHT | 8.191455158404 | 8.191455158404 | 0 |


## Manual review and retained uncertainty

147 files are retained for manual review; exact paths and reasons are in `manual_review.csv`. Unreadable recovery-vendor files were not moved or deleted. All active source and frozen-evidence hashes were readable and verified. Unknown data were retained. The graph cannot prove arbitrary runtime-computed imports dead, so no such source was removed.

The production master-vintage mismatch needs separate data/governance work. Both current masters and the historical production release remain unchanged. No stale historical forecast was replaced with a newly fitted value.

562 task-generated validation files were also removed from the excluded cleanup workspace; every receipt is included in deleted_files.csv. Test XML/logs were retained.

46 pre-existing directories could not be enumerated under current permissions. They were retained without modification; unreadable_directories.csv lists the omitted paths. File counts and checksum inventories cover readable project entries, not hidden contents of these opaque directories.
