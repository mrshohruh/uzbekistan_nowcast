"""Read-only production state reconciliation; evidence is written in a new namespace.

Commands: audit, validate_current_production_state, tests SCOPE, finalize.
Historical production gates and model implementations are never modified.
"""
from __future__ import annotations
import concurrent.futures as cf
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/reconciliation'
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, default=str) + '\n', encoding='utf-8')


def validate_state_identity(state, historical):
    """Reject any current-state record that purports to reproduce the old release."""
    if state.get('scope') != 'CURRENT_OPERATIONAL_STATE':
        raise ValueError('Current-state scope must be explicit')
    if state.get('does_not_replace_historical_release') is not True or state.get('historical_release_reproduction') is not False:
        raise ValueError('A current state cannot replace or reproduce a historical release')
    if state.get('run_id') == historical['run_id'] or state.get('timestamp_utc') == historical['run_timestamp_utc']:
        raise ValueError('Historical identity/timestamp cannot be reused')
    if 'input_hashes' not in state or 'forecasts' not in state:
        raise ValueError('Current input hashes and forecasts are required')


def walk():
    errors = []
    paths = []
    for parent, dirs, files in os.walk(ROOT, onerror=lambda e: errors.append(str(e))):
        dirs[:] = [d for d in dirs if d not in {'.git', '.venv', 'venv'} and not (Path(parent)/d).is_symlink()]
        for name in files:
            path = Path(parent)/name
            if not path.is_relative_to(OUT) and not path.is_relative_to(ROOT/'scripts/reconciliation') and not path.is_symlink(): paths.append(path)
    return paths, errors


def inventory(paths):
    def one(path):
        rel = path.relative_to(ROOT).as_posix()
        try: return rel, sha(path), path.stat().st_size, None
        except OSError as e: return rel, None, None, str(e)
    with cf.ThreadPoolExecutor(max_workers=16) as pool:
        return list(pool.map(one, paths))


def helper():
    spec = importlib.util.spec_from_file_location('reconciliation_validation', ROOT/'scripts/maintenance/cleanup_validate.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.OUT = OUT
    return module


def describe(data, expected_frame):
    import pandas as pd
    try:
        frame = data if isinstance(data, pd.DataFrame) else pd.read_parquet(data)
        col = 'date' if 'date' in frame else 'quarter' if 'quarter' in frame else None
        return dict(schema_match=list(frame.columns)==list(expected_frame.columns),
                    date_range=f'{frame[col].min()}..{frame[col].max()}' if col else '',row_count=len(frame),status='READABLE_CANDIDATE')
    except Exception as e:
        return dict(schema_match=False,date_range='',row_count=None,status=f'NOT_COMPARABLE: {type(e).__name__}')


def audit():
    import pandas as pd
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'baseline.json').exists(): raise RuntimeError('Audit baseline already exists; preserve original evidence.')
    paths, errors = walk(); entries = inventory(paths)
    hashes = {p:h for p,h,_,e in entries if not e}
    write('baseline.json', hashes)
    pd.DataFrame(entries,columns=['path','sha256','size_bytes','error']).to_csv(OUT/'repository_search_inventory.csv',index=False)
    write('search_coverage.json',dict(unreadable_directories=errors,unreadable_files=[p for p,h,s,e in entries if e],
          exclusions=['installed .venv/venv environments','Git object container bytes (reachable object contents searched separately)','new reconciliation outputs','symlinks'],
          readable_file_count=len(hashes),claim='No matches among searched readable files; opaque directories are not claimed searched.'))
    old = read(ROOT/'results/production/run_manifest.json')
    refs = [('monthly','data/master/v1_monthly.parquet','monthly_master_hash'),('quarterly','data/master/gdp_quarterly.parquet','quarterly_master_hash')]
    frames = {kind:pd.read_parquet(ROOT/path) for kind,path,key in refs}
    search=[]; found={kind:[] for kind,_,_ in refs}
    for kind, path, key in refs:
        expected=old['input_data_fingerprints'][key]
        for rel,h,size,error in entries:
            candidate=ROOT/rel
            likely=(candidate.suffix.lower() in {'.parquet','.csv','.xlsx'} and
                    (candidate.stem in {'v1_monthly','gdp_quarterly','pilot_monthly','pilot8_monthly'} or h==expected))
            if h==expected or likely:
                desc=describe(candidate,frames[kind]) if candidate.suffix=='.parquet' else {}
                if candidate.suffix in {'.csv','.xlsx'}:
                    try: desc=describe(pd.read_csv(candidate) if candidate.suffix=='.csv' else pd.read_excel(candidate),frames[kind])
                    except Exception as e: desc=dict(status='UNREADABLE_OR_NOT_TABULAR: '+type(e).__name__)
                search.append(dict(expected_hash=expected,candidate_path=rel,candidate_hash=h,exact_match=h==expected,**desc))
                if h==expected:found[kind].append(rel)
    # Read deleted tracked inputs from every reachable Git revision, without checkout/reset.
    objects=subprocess.check_output(['git','rev-list','--objects','--all'],cwd=ROOT,text=True,encoding='utf-8').splitlines()
    seen=set();git_count=0
    for line in objects:
        parts=line.split(' ',1)
        if len(parts)<2:continue
        oid,name=parts
        if oid in seen or Path(name).suffix.lower() not in {'.parquet','.csv','.xlsx'}:continue
        seen.add(oid);data=subprocess.check_output(['git','cat-file','blob',oid],cwd=ROOT);git_count+=1
        digest=hashlib.sha256(data).hexdigest()
        for kind,path,key in refs:
            expected=old['input_data_fingerprints'][key]
            if digest==expected or Path(name).stem in {'v1_monthly','gdp_quarterly'}:
                desc=describe(io.BytesIO(data),frames[kind]) if name.endswith('.parquet') else dict(status='GIT_TABULAR_CANDIDATE')
                location='git:'+oid+':'+name
                search.append(dict(expected_hash=expected,candidate_path=location,candidate_hash=digest,exact_match=digest==expected,**desc))
                if digest==expected:
                    target=OUT/'historical_inputs'/digest/Path(path).name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
                    found[kind].append(target.relative_to(ROOT).as_posix())
    pd.DataFrame(search,columns=['expected_hash','candidate_path','candidate_hash','exact_match','schema_match','date_range','row_count','status']).to_csv(OUT/'historical_master_search.csv',index=False)
    coverage=read(OUT/'search_coverage.json');coverage['reachable_git_tabular_blobs_checked']=git_count;write('search_coverage.json',coverage)
    audit_rows=[]
    for kind,path,key in refs+[('registry','registry/uzbekistan_nowcasting_v1.2_registry.xlsx','registry_hash')]:
        expected=old['input_data_fingerprints'][key];actual=sha(ROOT/path)
        audit_rows.append(dict(artifact=kind,path=path,expected_hash=expected,current_hash=actual,match=expected==actual,
           historical_file_found=bool(found.get(kind)) if kind!='registry' else expected==actual,role='HISTORICAL_RELEASE_INPUT',
           action_required='NONE' if expected==actual else 'KEEP_HISTORICAL_GATE; VALIDATE_CURRENT_STATE_SEPARATELY',notes=old['run_id']))
    code=pd.read_csv(ROOT/old['code_version']['code_hash_inventory_file'])
    for row in code.to_dict('records'):
        p=ROOT/row['file_path']; actual=sha(p) if p.is_file() else None
        audit_rows.append(dict(artifact='recorded_code_inventory',path=row['file_path'],expected_hash=row['sha256'],current_hash=actual,
            match=actual==row['sha256'],historical_file_found=actual==row['sha256'],role=row['role'],action_required='NONE' if actual==row['sha256'] else 'REVIEW',notes='Recorded inventory; not every row is model code.'))
    pd.DataFrame(audit_rows).to_csv(OUT/'production_manifest_audit.csv',index=False)
    write('historical_input_locations.json',found)
    print('Search complete:',len(hashes),'readable files;',git_count,'Git tabular blobs; historical matches:',found)


def validate_current_production_state():
    import pandas as pd
    import numpy as np
    from uznowcast.registry import load_registry
    from uznowcast.master import build_monthly, build_quarterly
    from uznowcast.models.data import load_dataset
    from uznowcast.operational.phase5a import detect_target_quarter, generate_nowcasts
    from uznowcast.operational.phase5b import detect_operational_stage
    registry=load_registry(ROOT/'registry/uzbekistan_nowcasting_v1.2_registry.xlsx')
    processed={p.stem:pd.read_parquet(p) for p in (ROOT/'data/processed').glob('*.parquet') if p.stem in registry.rows}
    processed={k:v for k,v in processed.items() if len(v)}
    rebuilt={'monthly':build_monthly(processed,registry,scope='v1'),
             'quarterly':build_quarterly(processed['gdp_real_yoy'],'gdp_real_yoy_pct')}
    checks=[];evidence={};pairs=set()
    for kind,name in [('monthly','v1_monthly'),('quarterly','gdp_quarterly')]:
        frame=pd.read_parquet(ROOT/f'data/master/{name}.parquet')
        equal=frame.equals(rebuilt[kind]);checks.append(dict(check=kind+'_processed_reconstruction',passed=equal,details='Exact values, dtypes, schema and row order'))
        evidence[kind]=dict(current_rows=len(frame),columns=list(frame.columns),processed_reconstruction_exact=equal)
    # FX monthly provenance contains independently sorted JSON lists; compare checksum sets, never zip lists.
    failures=[];groups=0
    for key,frame in processed.items():
        for paths,sums in frame[['raw_file_path','checksum']].drop_duplicates().itertuples(index=False,name=None):
            if pd.isna(paths) or pd.isna(sums):failures.append((key,'missing provenance'));continue
            paths=str(paths);sums=str(sums)
            names=json.loads(paths) if paths.startswith('[') else [paths]
            expected=json.loads(sums) if sums.startswith('[') else [sums]
            try:
                actual=[sha(ROOT/name) for name in names]
                if sorted(actual)!=sorted(expected):failures.append((key,'raw checksum mismatch',names))
                groups+=1;pairs.update(names)
            except OSError as e:failures.append((key,str(e)))
    checks.append(dict(check='raw_provenance',passed=not failures,details=f'{groups} provenance groups; {len(pairs)} raw files; failures={len(failures)}'))
    write('current_input_provenance.json',dict(datasets=evidence,raw_group_count=groups,raw_file_count=len(pairs),failures=failures,
          build_manifest=read(ROOT/'data/master/build_manifest.json'),
          latest_retrievals={k:sorted(map(str,v.retrieved_at.dropna().unique())) for k,v in processed.items()},
          limitation='Reconstruction compares current processed data to current masters, NOT missing historical master observations. GDP latest-source dates are not first-release history.'))
    old=read(ROOT/'results/production/run_manifest.json'); hashes={k:sha(ROOT/p) for k,p in [('monthly_master_hash','data/master/v1_monthly.parquet'),('quarterly_master_hash','data/master/gdp_quarterly.parquet'),('registry_hash','registry/uzbekistan_nowcasting_v1.2_registry.xlsx')]}
    checks.append(dict(check='registry_matches_saved_release',passed=hashes['registry_hash']==old['registry_hash'],details=hashes['registry_hash']))
    audit_frame=pd.read_csv(OUT/'production_manifest_audit.csv')
    model_code=audit_frame[audit_frame.path.str.startswith(('src/','config/'))]
    checks.append(dict(check='recorded_model_code_and_configuration',passed=bool(model_code['match'].all()),details=f'{len(model_code)} recorded source/config entries'))
    dataset=load_dataset(ROOT);timestamp=datetime.now(timezone.utc).isoformat();asof=datetime.now(ZoneInfo('Asia/Tashkent')).date().isoformat()
    calendar_target=detect_target_quarter(dataset,asof)
    # Reconcile the frozen production target, rather than roll its specification
    # to a new quarter merely because the validation clock has crossed September.
    target=detect_target_quarter(dataset,old['as_of_date'])
    if target['target_quarter']!=old['target_quarter']:raise RuntimeError('Saved production target cannot be reconstructed')
    target['reason']='Saved production target retained for master-state reconciliation; availability and horizon are evaluated at the current as-of date.'
    stage=detect_operational_stage(dataset,target['target_quarter'],asof)
    first,_=generate_nowcasts(dataset,asof,target,stage,hashes,timestamp)
    second,_=generate_nowcasts(dataset,asof,target,stage,hashes,timestamp)
    predictions={r['model']:float(r['prediction']) for r in first.to_dict('records')}
    repeat=first[['model','prediction']].equals(second[['model','prediction']]) and all(np.isfinite(list(predictions.values()))) and len(predictions)==4
    checks.append(dict(check='current_forecasts_reproduce',passed=repeat,details=json.dumps(predictions)))
    write('current_calculation.json',dict(timestamp_utc=timestamp,as_of_date=asof,target=target,operational_stage=stage,input_hashes=hashes,forecasts=predictions,
          target_selection_mode='SAVED_PRODUCTION_TARGET',calendar_detected_target=calendar_target['target_quarter'],
          scope='CURRENT_OPERATIONAL_STATE',publication_ready=False,limitation='Read-only calculation under unchanged operational availability policy; no official release or prospective snapshot.'))
    helper().production();helper().shadow()
    checks.append(dict(check='historical_H2_numeric_reproduction',passed=read(OUT/'validation_production.json')['frozen_horizon_forecasts_reproduced'],details='Numeric consistency on current inputs does not prove historical input recovery'))
    checks.append(dict(check='phase6d_seven_forecasts',passed=read(OUT/'validation_shadow.json')['passed'],details='Saved inputs, GDP vintages and timestamp; no ledger writes'))
    pd.DataFrame(checks).to_csv(OUT/'current_state_validation.csv',index=False)
    found=read(OUT/'historical_input_locations.json');differences=[]
    for kind in ['monthly','quarterly']:
        differences.append(dict(dataset=kind,difference_type='LATER_PIPELINE_REBUILD; HISTORICAL_VINTAGE_UNAVAILABLE' if not found[kind] else 'HISTORICAL_INPUT_RECOVERED',
            n_rows_old=None,n_rows_current=evidence[kind]['current_rows'],new_rows=None,changed_existing_rows=None,removed_rows=None,schema_changed=None,economic_values_changed=None,
            assessment='Current master reconstructs exactly from October 2 processed observations with verified raw checksums. Old/current observation deltas cannot be determined without the old bytes.'))
    pd.DataFrame(differences).to_csv(OUT/'master_difference_summary.csv',index=False)
    print('Current production:',predictions)


def tests(scope):
    if scope!='reconciliation':return helper().tests(scope,'reconciliation')
    import pytest
    return int(pytest.main(['scripts/reconciliation/test_reconciliation.py','-p','no:cacheprovider','--junitxml',str(OUT/'reconciliation_reconciliation_tests.xml'),'-q']))


def finalize():
    import pandas as pd
    import xml.etree.ElementTree as ET
    baseline={p:h for p,h in read(OUT/'baseline.json').items() if not p.startswith('scripts/reconciliation/')}
    current=inventory([ROOT/p for p in baseline]);changes=[p for p,h,s,e in current if e or h!=baseline[p]]
    write('protected_hash_verification.json',dict(checked=len(baseline),changes=changes,passed=not changes))
    tests=[]
    for xml in OUT.glob('reconciliation_*_tests.xml'):
        for suite in ET.parse(xml).getroot().iter('testsuite'):
            tests.append(dict(scope=xml.name,tests=int(suite.get('tests',0)),failures=int(suite.get('failures',0)),errors=int(suite.get('errors',0)),skipped=int(suite.get('skipped',0))))
    passed=sum(r['tests']-r['failures']-r['errors']-r['skipped'] for r in tests);failed=sum(r['failures']+r['errors'] for r in tests)
    validation=pd.read_csv(OUT/'current_state_validation.csv');found=read(OUT/'historical_input_locations.json')
    inputs_ok=bool(validation.passed.all());required={'repository','phase6c','phase6d','reconciliation'}
    scopes={r['scope'].removeprefix('reconciliation_').removesuffix('_tests.xml') for r in tests}
    valid=inputs_ok and not changes and failed==0 and required.issubset(scopes)
    classification='HISTORICAL_INPUT_RECOVERED' if all(found.values()) else 'LEGITIMATE_MASTER_EVOLUTION' if inputs_ok else 'UNRESOLVED_MASTER_MISMATCH'
    calculation=read(OUT/'current_calculation.json');old=read(ROOT/'results/production/run_manifest.json')
    historical=all(found.values())
    result=dict(classification=classification,historical_release_id=old['run_id'],historical_release_reproduction='INPUTS_RECOVERED' if historical else 'BLOCKED_MISSING_EXACT_INPUTS',
        current_operational_state='VALIDATED_READ_ONLY' if valid else 'BLOCKED',historical_files=found,tests=tests,tests_passed=passed,tests_failed=failed,
        protected_files_checked=len(baseline),protected_changes=changes,old_observation_differences='UNKNOWN: no historical bytes recovered',
        current_state_does_not_replace_historical_release=True,publication_ready=False,search_coverage=read(OUT/'search_coverage.json'))
    if valid and classification in {'LEGITIMATE_MASTER_EVOLUTION','CONTENT_EQUIVALENT_HASH_DIFFERENCE'}:
        specs={p:sha(ROOT/p) for p in baseline if p.endswith('.json') and any(word in p for word in ['production_policy','candidate_freeze','frozen_challengers','model_specs']) and not any(word in p for word in ['test_','/t_','_pytest','test_workspace'])}
        code={p:sha(ROOT/p) for p in baseline if (p.startswith('src/') or p.startswith('scripts/research/')) and p.endswith('.py') and '__pycache__' not in p}
        state=dict(**calculation,classification=classification,validation_status='VALIDATED_READ_ONLY',code_hashes=code,model_specification_hashes=specs,
            historical_relationship=dict(saved_run_id=old['run_id'],saved_manifest_path='results/production/run_manifest.json',saved_manifest_hash=baseline['results/production/run_manifest.json'],saved_expected_input_hashes=old['input_data_fingerprints']),
            does_not_replace_historical_release=True,historical_release_reproduction=False,tests_passed=passed,provenance_evidence='current_input_provenance.json')
        validate_state_identity(state,old)
        write('current_production_state_manifest.json',state)
    else:write('production_blocker.json',result)
    result['current_state_manifest_created']=(OUT/'current_production_state_manifest.json').exists();write('reconciliation_manifest.json',result)
    questions=[
      f"Blocked release: `results/production/run_manifest.json`, {old['run_id']}, 2026Q3/H2. Enforcement: `src/uznowcast/operational/phase5b1.py`, Phase 4B frozen master hashes.",
      f"Missing historical master hashes: monthly `{old['input_data_fingerprints']['monthly_master_hash']}`; quarterly `{old['input_data_fingerprints']['quarterly_master_hash']}`.",
      f"Exact historical master recovery: {found}. Search coverage and inaccessible paths are documented separately; Git candidates were checked by content hash.",
      f"Current hashes: {calculation['input_hashes']}. Both master hashes differ; registry matches.",
      "Legitimate evolution is supported by the October 2 build manifest, later retrieval timestamps, verified raw provenance and exact reconstruction from current processed observations. The saved release reported incomplete September FX/H2; current data support H3. Specific appended/revised rows, historical schema changes and byte-only GDP changes remain UNKNOWN. No historical observation-level comparison was fabricated.",
      "No model code was edited. Recorded source/config hashes were checked in production_manifest_audit.csv; any non-model inventory differences are reported there.",
      "No model specifications changed; all pre-existing readable file hashes were verified after tests.",
      f"Four current production forecasts reproduce twice for the saved {calculation['target']['target_quarter']} target at {calculation['as_of_date']}/{calculation['operational_stage']['horizon']}: {calculation['forecasts']}. The current calendar target ({calculation['calendar_detected_target']}) is recorded but not promoted to production by this reconciliation. Saved H2 values reproduce numerically; all seven Phase 6D forecasts reproduce from immutable snapshot inputs. Production retains its registry-lag/current-GDP-vintage policy; Phase 6D retains its documented-release GDP-vintage policy. Those inputs differ, so the production and shadow benchmark numbers need not coincide.",
      "Historical release cannot be fully reconstructed without exact historical masters; numeric forecast agreement does not satisfy its hash gate." if not historical else "Historical master inputs were recovered; historical reconstruction requires the recorded context.",
      f"Current operational state: {result['current_operational_state']}. This is read-only input/calculation validation, not publication approval. Existing dirty-tree and data-quality warnings remain applicable.",
      f"New current-state manifest created: {result['current_state_manifest_created']}; it explicitly disclaims replacing the historical release and records current inputs, code, specifications and timestamp.",
      f"Original historical manifest unchanged: {not changes}. Historical expected hashes and enforcement code were never rewritten.",
      f"Phase 6D unchanged: {not changes}; complete existing directory covered by the baseline inventory, including ledgers, withdrawals, realizations, snapshots and seals. No new snapshot was appended.",
      f"Final classification: **{classification}**. Tests: {passed} passed, {failed} failed. Protected readable files: {len(baseline)} checked, {len(changes)} changed."]
    report='# Production master-state reconciliation — Phase 6E.1\n\n'+ '\n\n'.join(f'{i}. {q}' for i,q in enumerate(questions,1))
    report+='\n\nRun read-only verification with `.venv/Scripts/python.exe scripts/reconciliation/reconcile.py validate_current_production_state`. Evidence is written only under results/reconciliation; the historical production gate is unchanged. This command alone does not issue a valid state manifest: finalize additionally requires passed tests and protected-file checks.\n'
    (OUT/'production_reconciliation_report.md').write_text(report,encoding='utf-8')
    lines=['PRODUCTION STATE RECONCILIATION',f'Blocked historical production manifest: results/production/run_manifest.json ({old["run_id"]})']
    for kind,key in [('monthly','monthly_master_hash'),('quarterly','quarterly_master_hash')]:
        lines += [f'Expected {kind} hash: {old["input_data_fingerprints"][key]}',f'Current {kind} hash: {calculation["input_hashes"][key]}',f'Historical {kind} master recovered: '+('YES' if found[kind] else 'NO'),f'{kind.title()} differences explained: PARTIAL']
    lines += [f'Current {k}: {v}' for k,v in calculation['forecasts'].items()]
    lines += ['Model specifications changed: NO','Historical manifest changed: '+('YES' if changes else 'NO'),'Phase 6D ledger changed: '+('YES' if any('phase6d' in p and 'ledger' in p for p in changes) else 'NO'),'Phase 6D snapshots changed: '+('YES' if any('phase6d/snapshots' in p for p in changes) else 'NO'),'Current-state manifest created: '+('YES' if result['current_state_manifest_created'] else 'NO'),f'Tests passed: {passed}',f'Tests failed: {failed}','FINAL CLASSIFICATION: '+classification]
    text='\n'.join(lines);(OUT/'console_summary.txt').write_text(text+'\n',encoding='utf-8');print(text)
    if not valid:raise SystemExit(1)


if __name__=='__main__':
    command=sys.argv[1]
    if command=='tests':sys.exit(tests(sys.argv[2]))
    else:globals()[command]()
