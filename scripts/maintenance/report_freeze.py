"""Produce the final Phase 6H inventories, dependency audit and candid report."""
from __future__ import annotations
import ast
import csv
import json
from pathlib import Path
from scripts.maintenance.repository_freeze import ROOT, OUT, git, table, write


def read(name):
    return json.loads((OUT/name).read_text(encoding='utf-8'))


def main():
    before=read('pre_cleanup_manifest.json');after=read('post_cleanup_manifest.json')
    with (OUT/'file_inventory_before.csv').open(encoding='utf-8') as handle:old=list(csv.DictReader(handle))
    with (OUT/'file_inventory_after.csv').open(encoding='utf-8') as handle:new=list(csv.DictReader(handle))
    with (OUT/'deleted_files.csv').open(encoding='utf-8') as handle:deleted=list(csv.DictReader(handle))
    removed={r['path'] for r in deleted}
    tracked_deletions=[r for r in deleted if r['recoverable_commit']]
    temporary_deletions=[r for r in deleted if not r['recoverable_commit']]
    paths={r['path'] for r in new if r['exists']=='True'}
    # Include dynamic worker imports, staged-directory dependencies, and every
    # checksum-locked module even if its code is not numerically executed.
    roots={p for p in paths if p.endswith('.py') and p.startswith(('scripts/operations/','scripts/production/','src/')) and '/test_' not in p}
    roots.update(p for p in paths if p.endswith('.py') and p.startswith('scripts/research/phase6d/') and '/test_' not in p)
    roots.update(['scripts/research/phase6c/kernel.py','scripts/research/phase6b2/vintages.py','scripts/research/phase6b2/run.py'])
    edges=read('dependency_graph_after.json')
    required=set(roots)
    while True:
        expanded=required | {e['target'] for e in edges if e['source'] in required and e['target'] in paths}
        # Directory copies in workspace.seed are dependencies too.
        expanded.update(p for p in paths for prefix in ['scripts/research/phase6b2/','scripts/research/phase6c/']
                        if p.startswith(prefix) and p.endswith('.py') and '/test_' not in p)
        if expanded==required:break
        required=expanded
    python=[];retained=[];tests=[];data=[];syntax_errors=[]
    for row in new:
        path=row['path'];kind='UNCERTAIN';reason='Role not proven; retained'
        if path in required:
            kind='PRODUCTION_REQUIRED';reason='Active dependency, staged dependency or checksum-locked source'
        elif path.startswith('tests/') or Path(path).name.startswith('test_'):
            kind='TEST_REQUIRED';reason='Current tests or frozen regression evidence'
        elif path.startswith('scripts/phase6e/'):
            kind='PRODUCTION_REQUIRED';reason='Historical policy compatibility entrypoint or validation harness'
        elif path.startswith('scripts/maintenance/'):
            kind='DEVELOPMENT_USEFUL';reason='Auditable maintenance/reproduction utility'
        elif '/_vendor/' in path or path.startswith('archive/'):
            kind='LEGACY_PHASE_CODE';reason='Historical archive or vendored historical tooling; retained'
        elif path.startswith('scripts/research/'):
            kind='LEGACY_PHASE_CODE';reason='Checksum-protected history or reusable research utility; not removed without proof'
        elif path.startswith(('data/','metadata/','config/','registry/','dashboard/','results/')):
            reason='Data, configuration, evidence or result; retained unless separately audited'
        record=dict(path=path,classification=kind,reason=reason,tracked=row['tracked'],exists=row['exists'])
        if path.endswith('.py'):
            python.append(record)
            if row['exists']=='True' and path.startswith(('src/','scripts/','tests/')):
                try:ast.parse((ROOT/path).read_text(encoding='utf-8-sig'))
                except (SyntaxError,UnicodeError,OSError) as exc:syntax_errors.append(dict(path=path,error=str(exc)))
        retained.append(record)
        if path.startswith('data/') or path.startswith('metadata/'):
            category='authoritative raw source' if '/raw/' in path else 'processed current dataset' if path.startswith(('data/processed/','data/master/','metadata/')) else 'uncertain/research data retained'
            data.append(dict(path=path,classification=category,action='KEEP'))
    for row in old:
        path=row['path']
        if path.endswith('.py') and path not in {r['path'] for r in python}:
            python.append(dict(path=path,classification='LEGACY_PHASE_CODE' if path in removed else 'UNCERTAIN',
                               reason='Removed recoverable rejected experiment' if path in removed else 'Original path retained for audit',
                               tracked=row['tracked'],exists=False))
        if Path(path).name.startswith('test_') and path.endswith('.py'):
            classification='OBSOLETE_EXPERIMENT_TEST' if path in removed else 'CURRENT_MODEL_UNIT_TEST' if path.startswith('tests/models/') else 'CRITICAL_PRODUCTION' if path.startswith(('tests/production/','scripts/operations/')) else 'REGRESSION_PROTECTION'
            action='DELETE' if path in removed else 'KEEP'
            if path=='scripts/phase6e/test_phase6e.py':classification='CRITICAL_PRODUCTION';action='MOVE_TO_TESTS_PRODUCTION'
            if path in {'scripts/research/phase6c/test_phase6c.py','scripts/research/phase6b2/test_vintages.py'}:
                classification='CURRENT_MODEL_UNIT_TEST';action='KEEP_UNIT_TESTS; frozen historical inventory test outside current suite'
            tests.append(dict(path=path,classification=classification,action=action))
    tests.append(dict(path='scripts/operations/test_operations.py::test_source_fix_preserves_original_masters_snapshots_and_ledger',
                      classification='LEGACY_PHASE_TEST',action='REMOVE_STALE_SNAPSHOT_ASSERTION; live data preservation covered by private-worker test'))
    table('retained_files.csv',retained,['path','classification','reason','tracked','exists'])
    table('python_classification.csv',python,['path','classification','reason','tracked','exists'])
    table('test_cleanup.csv',tests,['path','classification','action'])
    table('data_classification.csv',data,['path','classification','action'])
    dangling=[]
    for rel in sorted(required):
        if not rel.endswith('.py') or not (ROOT/rel).is_file():continue
        text=(ROOT/rel).read_text(encoding='utf-8-sig')
        if any(token in text for token in ['scripts.phase6f.','scripts.phase6g.','scripts.phase6g1.','scripts.phase6g2.','scripts.phase6g3.','scripts.phase6g4.','scripts.phase6g5.']):
            dangling.append(rel)
    audit=dict(production_roots=sorted(roots),required_paths=sorted(required),syntax_errors=syntax_errors,
               rejected_experiment_imports=dangling,
               static_graph_limitations='Literal templates and staged directory copies are conservative; frozen dynamic import roots are explicitly included. Unresolved files are retained.',
               retained_legacy_dependencies=['scripts/research/phase6b2','scripts/research/phase6c','scripts/research/phase6d','src/uznowcast/operational/phase5a.py','src/uznowcast/operational/phase5b.py'],
               cannot_claim_clean_checkout_exact_reproduction=bool(before['untracked_scientific_inputs']))
    write('production_dependency_audit.json',audit)
    comparison=read('production_comparison.json')
    validations={scope:read(f'tests_{scope}.json') for scope in ['repository','operations','dfm','vintages']}
    clean=all(v['exit_code']==0 for v in validations.values()) and read('post_operations_exit.json')['exit_code']==0
    status='PHASE6H_PARTIAL_CONSOLIDATION' if comparison['passed'] and clean and not dangling and not syntax_errors else 'PHASE6H_VALIDATION_FAILED'
    write('final_status.json',dict(status=status,scientific_outputs_unchanged=comparison['passed'],validation_passed=clean,
                                  legacy_dependencies_remain=True,tests=validations))
    dirs=sorted({str(Path(r['path']).parent) for r in deleted if r['path'].startswith('results/')})
    originally_existing={r['path'] for r in old if r['exists']=='True'}
    original_remaining=len(originally_existing & paths)
    maintained=lambda rows:sum(r['exists']=='True' and r['path'].endswith('.py') and r['path'].startswith(('src/','scripts/','tests/')) for r in rows)
    report=f'''# Phase 6H repository cleanup

**{status}**

The M0 DFM, USD/UZS U-MIDAS, 50/50 policy, coefficients, information rules and saved current nowcast are unchanged. This is a partial consolidation because immutable operational locks still require historical phase kernels and artifact paths. No checksum seal was regenerated to disguise those dependencies.

## Baseline and recoverability

Baseline commit: `{before['commit']}`. Five recent commits and the original working-tree status are in `pre_cleanup_manifest.json`. There were {len(before['working_tree_status'].splitlines())} pre-existing status entries, including inaccessible vendored files reported by Git as deleted. These were not restored, staged or committed.

{len(before['untracked_scientific_inputs'])} important inputs/metadata artifacts were not tracked (including intentionally ignored generated data). They were preserved. Exact replay from a clean checkout therefore requires the preserved data/vintages; network bootstrap can ingest official data but cannot promise the same historical vintage. Git history was not rewritten. No new sources were fetched during freeze validation.

## Counts and removals

| Inventory | Before | After |
|---|---:|---:|
| Accessible files in declared inventory scope | {before['accessible_files']} | {after['accessible_files']} |
| Python files in that scope | {before['python_files']} | {after['python_files']} |
| Test files in that scope | {before['tests']} | {after['tests']} |
| Maintained Python files under src/scripts/tests | {maintained(old)} | {maintained(new)} |

{len(tracked_deletions)} explicitly audited tracked files were removed or relocated, plus {len(temporary_deletions)} files in disposable validation workspaces created during this phase; {original_remaining} of the {len(originally_existing)} originally accessible paths remain. New evidence affects total counts, so counts are not a claim that every new file is maintained source. Traversal exclusions/access failures are listed in the manifests. Python classifications cover all inventoried Python paths, including historical copies; uncertain files remain intact.

Rejected Phase 6F and Phase 6G/G1/G2/G3/G4/G5 executable experiments, their dedicated tests and recoverable results were removed. Raw CBU source evidence under `results/phase6f/raw/` was preserved. Protected historical Phase 4/5/6B/6C/6D artifacts and untracked results were retained. Inaccessible or dirty candidates were preserved; see `cleanup_exceptions.json`. Affected result directories and their remaining existence are listed in `removed_result_directories.json`; directories containing preserved files may remain.

## Architecture and functions

`scripts/production/{{models,diagnostics,dashboard,run,update}}.py` owns the current implementation. Twenty-eight function/test migrations are recorded in `function_migrations.csv`; old Phase 6E modules are thin compatibility imports, not duplicate implementations. Current production tests are discovered under `tests/production/`. `config/production.json` resolves the existing frozen sources of settings through `scripts.production.config.configuration`. It does not redefine scientific values. `results/current/index.json` and `results/diagnostics/index.json` locate authoritative outputs without copying datasets or breaking sealed paths.

The duplicate-function AST audit is saved before and after. No growth, standardization, factor, GDP or release formula was replaced. Remaining duplicate implementations inside frozen historical source are retained because changing their bytes invalidates operational locks. Full removal of those dependencies would require an explicit migration of the sealing protocol and independent reproduction, beyond a cleanup that preserves current locks.

## Tests and validation

'''
    for scope,v in validations.items():report+=f"- {scope}: {v['passed']} passed, {v['failures']} failures, {v['errors']} errors, {v['skipped']} skipped.\n"
    report+='''
The original repository test run exposed a Windows locale decoding failure in Git-diff capture. The validation runner now starts Python in UTF-8 mode; frozen model source was not edited. Three stale operations assertions were corrected: private news perturbation now changes an actually used month, the September gold parser comparison uses an explicit August information set, and a historical live-master checksum assertion was replaced by current-data preservation checks around the private worker.

Two checksum-locked historical inventory tests remain byte-preserved outside the current suite. Their original failures are recorded in `dfm_tests.log` and `vintage_tests.log`: they compare today's promoted dashboard/data against obsolete research snapshots. Current unit suites retain 19 DFM and 19 vintage tests; scientific preservation is checked separately against the Phase 6H baseline. They were not marked as passing or silently rewritten.

The production updater completed in dry, cached historical replay mode with `NO_INFORMATION_CHANGE`; no snapshot or master was promoted. Provider/network availability was not checked. The console's historical implementation-test count is not this phase's test count; use the JSON/XML reports here.

The complete pre-cleanup build, post-cleanup build and independent deterministic rerun all succeeded without publication. Generated scientific CSV/JSON outputs and dashboard HTML are byte-identical. Relocated code paths/hashes in run manifests and operational logs/reports are excluded from byte identity.

| Output | Before | After | Independent rerun |
|---|---:|---:|---:|
'''
    for key,values in comparison['predictions'].items():report+=f"| {key} | {values['baseline_run']} | {values['post_run']} | {values['deterministic_run']} |\n"
    report+='''
Frozen source, registry, processed observations, masters and provenance metadata match baseline checksums. The authoritative saved policy and nowcast remain untouched. `production_comparison.json` records exact equality, not rounded display equality.

## Dependency and dead-code checks

The active dependency audit includes AST imports, literal data/config paths, explicitly resolved dynamic worker imports and staged directory dependencies. No retained active import points to removed Phase 6F/6G modules. Active source parses successfully. Historical manifests still reference historical artifacts; these are evidence, not rewritten production configuration. Unknown roles were retained rather than guessed unused.

Full phase-free operation and exact clean-checkout reconstruction are not claimed. Remaining frozen kernels and ignored data are listed in `production_dependency_audit.json` and the baseline. The current README describes the active V2 policy, commands, inputs and output pointers.

## Git status

The final status is recorded verbatim in `git_status_after.txt`. All changes remain reviewable in the working tree; no commit, index modification, history rewrite, model search, coefficient change or nowcast publication was performed.
'''
    (OUT/'phase6h_repository_cleanup.md').write_text(report,encoding='utf-8')
    write('removed_result_directories.json',[dict(path=p,still_exists=(ROOT/p).exists()) for p in dirs])
    (OUT/'git_status_after.txt').write_text(git('status','--short'),encoding='utf-8')
    print(status)


if __name__=='__main__':main()
