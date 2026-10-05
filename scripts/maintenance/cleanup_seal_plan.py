"""Final conservative audit checks before any filesystem mutation."""
import json
from collections import defaultdict
from cleanup_audit import ROOT,OUT,write,json_out,temporary,cache,sha
import pandas as pd

plan=pd.read_csv(OUT/'cleanup_plan.csv',keep_default_na=False).to_dict('records')
inventory=pd.read_csv(OUT/'repository_inventory.csv',keep_default_na=False).to_dict('records')
python=pd.read_csv(OUT/'active_python_inventory.csv',keep_default_na=False).to_dict('records')
protected=json.loads((OUT/'protected_hashes_before.json').read_text())
original=json.loads((ROOT/'results/phase6d/phase6d_protected_start.json').read_text())
summary=json.loads((OUT/'audit_summary.json').read_text())
baseline=[json.loads(p.read_text()) for p in OUT.glob('validation_baseline_*_tests.json')]
assert len(baseline)==7 and all(r['exit_code']==0 for r in baseline),'Baseline exclusion tests must pass'
by_hash=defaultdict(list)
for row in inventory:
    if row['sha256']!='UNREADABLE':by_hash[row['sha256']].append(row['path'])
for row in plan:
    path=row['path']
    if path.startswith('scripts/maintenance/') or path=='ACTIVE_CORE.md':
        row.update(action='KEEP',destination='',protected=True,category='CURRENT_ACTIVE',hash=sha(ROOT/path),reason='New cleanup-only administrative utility/documentation; no existing model code changed')
        protected[path]=row['hash']
    if path=='.tmp_cleanup_audit.log':
        row.update(action='ARCHIVE',destination='archive/historical_results/'+path,category='TEMPORARY',reason='Task-generated interrupted audit log; retain under archive, not at project root')
    if path.startswith(('results/phase6d/','scripts/research/phase6d/')):
        row.update(action='KEEP',destination='',protected=True,category='CURRENT_ACTIVE',reason='Phase 6D preserved in FULL, including all existing cache/test artifacts')
        protected[path]=row['hash']
    elif '/_vendor/' in path:
        row.update(action='REVIEW',destination='',reason='Third-party recovery dependency or unreadable existing file; no relocation without evidence')
    elif cache(path) and path not in original and path not in summary['user_modified_existing']:
        row.update(action='DELETE_SAFE',destination='',protected=False,category='TEMPORARY',reason='Regenerable bytecode/cache not pinned by frozen inventory or user changes')
        protected.pop(path,None)
    if row['action']=='ARCHIVE' and path.endswith('.py'):
        canonical=[p for p in by_hash[row['hash']] if p.endswith('.py') and not temporary(p) and p!=path]
        if canonical:
            row.update(destination='archive/legacy_code/'+path,reason='Exact disposable source copy; canonical '+canonical[0]+' retained; all baseline tests pass with imports from old temporary trees denied')
        else:
            row.update(action='REVIEW',destination='',reason='Unknown temporary Python source; not proven redundant; keep in place')
    if row['action'] in ['ARCHIVE','DELETE_SAFE']:
        assert not row['protected'] and row['category']!='CURRENT_ACTIVE'
plan_by_path={r['path']:r for r in plan}
for row in inventory:
    planned=plan_by_path[row['path']]
    row['protected']=bool(planned['protected']);row['category']=planned['category']
for row in python:
    planned=plan_by_path[row['path']];row['candidate_action']=planned['action'];row['reason']=planned['reason']
    if planned['action']=='ARCHIVE':row['classification']='DEAD_CANDIDATE'
write('cleanup_plan.csv',plan);write('repository_inventory.csv',inventory);write('active_python_inventory.csv',python)
for name in ['result_artifact_inventory.csv','duplicate_files.csv']:
    rows=pd.read_csv(OUT/name,keep_default_na=False).to_dict('records')
    for row in rows:
        path=row.get('path',row.get('duplicate_file'))
        row['action']=plan_by_path[path]['action']
    write(name,rows)
json_out('protected_hashes_before.json',protected)
summary.update(protected_files=len(protected),actions={a:sum(p['action']==a for p in plan) for a in ['KEEP','ARCHIVE','DELETE_SAFE','REVIEW']},
    baseline_tests_passed=sum(r['passed'] for r in baseline),stage_A_safety_check='PASS; no CURRENT_ACTIVE mutation; Python copies proven redundant and exclusion-tested')
json_out('audit_summary.json',summary)
print(json.dumps(summary['actions'],indent=2))
# Find preserved inputs for the historical production release, if present.
prod=json.loads((ROOT/'results/production/run_manifest.json').read_text())['input_data_fingerprints']
json_out('production_historical_input_lookup.json',{k:by_hash.get(v,[]) for k,v in prod.items()})
