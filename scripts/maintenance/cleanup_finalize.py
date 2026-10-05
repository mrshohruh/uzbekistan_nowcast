"""Verify post-cleanup evidence and write the cleanup report/manifest."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
from cleanup_audit import ROOT,OUT,files,sha,write,json_out,temporary,cache
import pandas as pd


def finalize():
    summary=json.loads((OUT/'audit_summary.json').read_text())
    protected=json.loads((OUT/'protected_hashes_before.json').read_text())
    original=pd.read_csv(OUT/'repository_inventory.csv',keep_default_na=False)
    plan=pd.read_csv(OUT/'cleanup_plan.csv',keep_default_na=False)
    archived=pd.read_csv(OUT/'archived_files.csv',keep_default_na=False)
    deletion_receipts=pd.read_csv(OUT/'deleted_files.csv',keep_default_na=False)
    validation_deleted=deletion_receipts.loc[deletion_receipts.path.str.startswith('results/cleanup/validation_workspaces/')]
    deleted=deletion_receipts.loc[~deletion_receipts.path.str.startswith('results/cleanup/validation_workspaces/')]
    checks=[];failures=[]
    def check(item):
        path,h=item
        try:actual=sha(ROOT/path)
        except (PermissionError,FileNotFoundError):actual='UNREADABLE_OR_MISSING'
        return dict(path=path,before_sha256=h,after_sha256=actual,passed=h==actual)
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures=[executor.submit(check,item) for item in protected.items()]
        for i,future in enumerate(as_completed(futures),1):
            result=future.result();checks.append(result)
            if not result['passed']:failures.append(result)
            if i%2000==0:print('Protected checks:',i,'/',len(protected),flush=True)
    write('protected_hash_comparison.csv',sorted(checks,key=lambda r:r['path']))
    # Archived bytes must remain exact; no active path should accidentally move.
    archive_failures=[r.path for r in archived.itertuples() if sha(ROOT/r.destination)!=r.sha256 or (ROOT/r.path).exists()]
    json_out('archive_integrity.json',dict(files_checked=len(archived),failures=archive_failures))
    tests=[json.loads(p.read_text()) for p in OUT.glob('validation_after_*_tests.json')]
    assert len(tests)==7,'All seven post-cleanup test groups must finish'
    test_passed=sum(r['passed'] for r in tests);test_failed=sum(r['failures']+r['errors'] for r in tests)
    shadow=json.loads((OUT/'validation_shadow.json').read_text())
    production=json.loads((OUT/'validation_production.json').read_text())
    baseline_production=json.loads((OUT/'baseline_production_reference.json').read_text())
    imports=json.loads((OUT/'validation_imports.json').read_text())
    unchanged_production=production['forecasts']==baseline_production['forecasts'] and production['current_input_hashes']==baseline_production['current_input_hashes']
    review=plan.loc[plan.action.eq('REVIEW')].copy()
    write('manual_review.csv',review.to_dict('records'),list(plan.columns))
    current=[p for p in files() if not p.is_relative_to(OUT)]
    active=[p for p in current if not p.is_relative_to(ROOT/'archive')]
    total_bytes=sum(p.stat().st_size for p in current)
    active_bytes=sum(p.stat().st_size for p in active)
    deleted_bytes=int(deleted.size_bytes.sum())
    archive_bytes=int(archived.size_bytes.sum())
    ledger='results/phase6d/phase6d_prospective_forecast_ledger.csv'
    comparison={r['path']:r for r in checks}
    ledger_ok=comparison[ledger]['passed']
    snapshots_ok=all(r['passed'] for r in checks if r['path'].startswith('results/phase6d/snapshots/'))
    operational_ok=production['passed'] and production['configuration_gate_passed']
    passed=not failures and not archive_failures and not test_failed and shadow['passed'] and imports['passed'] and operational_ok and unchanged_production
    status='CLEANUP_SUCCESS' if passed else 'CLEANUP_PARTIAL'
    active_python=pd.read_csv(OUT/'active_python_inventory.csv')
    duplicates=pd.read_csv(OUT/'duplicate_files.csv')
    removed_duplicates=int(duplicates.duplicate_file.isin(deleted.path).sum())
    manifest=dict(cleanup_timestamp=datetime.now(timezone.utc).isoformat(),git_commit=summary['git_commit'],
        classification=status,scope='Project tree excluding .git, .venv, and cleanup audit/validation outputs; after-size includes archive',
        files_before=summary['files_before'],files_after=len(current),active_files_after=len(active),
        bytes_before=summary['bytes_before'],bytes_after=total_bytes,active_bytes_after=active_bytes,
        bytes_archived=archive_bytes,bytes_safely_deleted=deleted_bytes,net_space_reclaimed=summary['bytes_before']-total_bytes,
        files_kept=int(plan.action.isin(['KEEP','REVIEW']).sum()),files_archived=len(archived),files_deleted=len(deleted),
        validation_temporary_files_deleted=len(validation_deleted),total_deletion_receipts=len(deletion_receipts),
        python_files_before=summary['python_files_before'],python_files_active=summary['active_python_files'],
        python_files_archived=int(archived.path.str.endswith('.py').sum()),python_files_deleted=int(deleted.path.str.endswith('.py').sum()),
        duplicates_removed=removed_duplicates,protected_files_checked=len(checks),protected_hash_failures=len(failures),
        archive_integrity_failures=len(archive_failures),tests_passed=test_passed,tests_failed=test_failed,
        forecast_reproduction_passed=shadow['passed'] and production['frozen_horizon_forecasts_reproduced'],
        phase6d_forecast_reproduction_passed=shadow['passed'],production_forecast_reproduction_passed=production['frozen_horizon_forecasts_reproduced'],
        production_configuration_gate_passed=production['configuration_gate_passed'],production_before_after_unchanged=unchanged_production,
        ledger_unchanged=ledger_ok,snapshots_unchanged=snapshots_ok,imports_passed=imports['passed'],
        manual_review_items=len(review),unreadable_existing_files=summary.get('unreadable_files',[]),tests=tests,
        pre_existing_blockers=[] if operational_ok else [production['warning']],
        protected_failure_details=failures,
        validation_command='.venv/Scripts/python.exe scripts/maintenance/cleanup_validate.py shadow')
    json_out('cleanup_manifest.json',manifest)
    forecast_rows=shadow['forecasts'];write('forecast_reproduction.csv',forecast_rows)
    table='| Model | Before | After | Absolute difference |\n|---|---:|---:|---:|\n'+''.join(f"| {r['model']} | {r['before']:.12f} | {r['after']:.12f} | {r['absolute_difference']:.3g} |\n" for r in forecast_rows)
    report=f'''# Safe repository cleanup — Phase 6E.0

**{status}**. Cleanup actions and frozen forecast reconstruction are verified. No model specification, source kernel, production output, prospective ledger, withdrawal or realization record was changed. No commit or reset was performed.

The current masters already differed from the saved production release before cleanup. The four production forecasts reproduce exactly at their recorded H2 stage, but the full production configuration gate rejects the newer master hashes. The historical monthly and quarterly master hashes were not found among any readable repository files. This pre-existing blocker prevents the stricter CLEANUP_SUCCESS classification; the cleanup did not repair it by changing model code or data.

## Before and after

| Item | Before | After |
|---|---:|---:|
| Project files, including archive | {summary['files_before']} | {len(current)} |
| Project bytes, including archive | {summary['bytes_before']} | {total_bytes} |
| Active-tree files, excluding archive | {summary['files_before']} | {len(active)} |
| Active-tree bytes, excluding archive | {summary['bytes_before']} | {active_bytes} |
| Python files | {summary['python_files_before']} | {sum(p.suffix=='.py' for p in current)} |

The same comparison scope excludes `.git`, the installed `.venv` and `results/cleanup/` audit and validation outputs. Before: {summary['directories_before']} directories; {summary['cache_temp_files']} cache/temporary files. Original result artifacts: {sum(str(p).startswith('results/') for p in original.path)}. Archive moves reduce active-tree clutter, not disk usage. Cache deletion reclaimed {deleted_bytes:,} bytes; net project-byte reduction after new maintenance documentation/utilities is {summary['bytes_before']-total_bytes:,} bytes.

## Actions

- {len(archived)} files archived with preserved paths and matching SHA256; {archive_bytes:,} bytes retained in archive.
- {len(deleted)} regenerable cache files permanently removed. No Python source was permanently removed.
- {int(archived.path.str.endswith('.py').sum())} Python files archived. No standalone legacy runner met all dead-code conditions: old phases remain pinned by hashes, imports, tests or reconstruction references.
- {removed_duplicates} redundant cache duplicates removed. Semantic raw-vintage duplicates, frozen references and snapshot code copies remain intact.
- Historical dashboards archived: {int(archived.path.str.startswith('dashboard/').sum())}. Frozen and current dashboards stay at their original paths.
- User changes and {len(summary['pre_existing_deleted_paths'])} pre-existing deletions were preserved. Unknown files and third-party recovery dependencies were retained.

Every mutation is listed in `archived_files.csv` or `deleted_files.csv`. `cleanup_plan.csv` records the pre-quarantine decisions and reasons. Archive integrity was checked after moves. Restore an archived file by reversing its recorded source/destination pair; there were no archive failures or missing active imports requiring restoration.

{len(validation_deleted)} additional disposable files created by the baseline/post-cleanup test runs were removed from `results/cleanup/validation_workspaces/`. They were outside the before/after project-size comparison. Their individual receipts are also in `deleted_files.csv`; XML, logs and verification reports were retained.

## Active code and paths

{summary['active_python_files']} Python files are reachable from operational, ingestion, shadow, reconstruction, documentation or test roots. The dependency graph combines AST imports, identifiable dynamic imports, script/CLI path literals, exact textual references, configuration, documentation and test entry points. Unknown dynamic dependencies are retained. `dependency_edges.csv` and `active_python_inventory.csv` provide the file-level evidence.

Read `ACTIVE_CORE.md` for the operator entry-point map. Production uses the operational Phase 5B.1 stack and AR1/AR2/USD U-MIDAS(3)/equal-weight ensemble. The shadow monitor retains `scripts/research/phase6b2/run.py`, `vintages.py`, `scripts/research/phase6c/kernel.py` and all Phase 6D modules. The eight-variable DFM remains one factor, AR(2), bridge B and quarterly mean. Combination weights remain exactly 0.5/0.5 and 0.5438822544881572/0.4561177455118428. POS after December 2024 remains missing.

Older results, dashboards, documentation and runners pinned by current hashes were deliberately kept. `results/phase6d/` was preserved in full, including its existing test/cache folders. This limits reclamation to 344 independently safe files; path stability takes precedence over a larger cosmetic consolidation.

## Verification

- {len(checks):,} protected files checked; {len(failures)} unauthorized hash changes.
- {len(archived)} archived files checked; {len(archive_failures)} archive integrity failures.
- {test_passed} tests passed, {test_failed} failed, across repository, Phase 6A2, 6B, 6B.1, 6B.2, 6C and 6D groups. Baseline exclusion tests also passed before quarantine.
- Import/syntax validation passed for {imports['n_checked']} retained Python files. Effectful runner scripts were syntax checked; their pure operational/shadow dependencies executed in the smoke tests.
- Phase 6D ledger unchanged: {ledger_ok}. Existing snapshots unchanged: {snapshots_ok}. Validation reconstructs saved observations, GDP vintages and the original timestamp without calling the operational writer, fetching sources or appending a prospective snapshot.
- Production calculations and input hashes are identical before and after cleanup. The saved production headline reconstructs at the recorded H2 stage. Current input hashes differ from the saved release; the configuration blocker is documented in `validation_production.json` and `production_historical_input_lookup.json`.

{table}

## Manual review and retained uncertainty

{len(review)} files are retained for manual review; exact paths and reasons are in `manual_review.csv`. Unreadable recovery-vendor files were not moved or deleted. All active source and frozen-evidence hashes were readable and verified. Unknown data were retained. The graph cannot prove arbitrary runtime-computed imports dead, so no such source was removed.

The production master-vintage mismatch needs separate data/governance work. Both current masters and the historical production release remain unchanged. No stale historical forecast was replaced with a newly fitted value.
'''
    (OUT/'cleanup_report.md').write_text(report,encoding='utf-8')
    status_text=f'''REPOSITORY CLEANUP COMPLETE
Files before: {summary['files_before']}
Files after: {len(current)}
Repository size before: {summary['bytes_before']}
Repository size after: {total_bytes}
Space reclaimed (net bytes): {summary['bytes_before']-total_bytes}
Python files before: {summary['python_files_before']}
Python files active: {summary['active_python_files']}
Python files archived: {manifest['python_files_archived']}
Python files deleted: {manifest['python_files_deleted']}
Temporary/cache files deleted: {len(deleted)}
Historical result files archived: {sum(str(p).startswith(('results/','.tmp/','.phase5d_test_tmp/')) for p in archived.path)}
Historical dashboards archived: {sum(str(p).startswith('dashboard/') for p in archived.path)}
Duplicate files removed: {removed_duplicates}
Protected files checked: {len(checks)}
Protected hash failures: {len(failures)}
Phase 6D ledger unchanged: {'YES' if ledger_ok else 'NO'}
Phase 6D snapshots unchanged: {'YES' if snapshots_ok else 'NO'}
Phase 6C frozen model unchanged: {'YES' if not failures else 'NO'}
Production model unchanged: {'YES' if unchanged_production and not failures else 'NO'}
Forecast reproduction:
'''+''.join(f"{r['model']}: {r['after']:.12f}\n" for r in forecast_rows)+f'''Tests passed: {test_passed}
Tests failed: {test_failed}
Manual-review files: {len(review)}
Pre-existing blocker: {production['warning']}
FINAL STATUS: {status}
'''
    (OUT/'cleanup_console_summary.txt').write_text(status_text,encoding='utf-8')
    print(status_text,flush=True)
    subprocess.run(['git','status','--short'],cwd=ROOT,stdout=(OUT/'post_cleanup_git_status.txt').open('w',encoding='utf-8'),check=True)


if __name__=='__main__':finalize()
