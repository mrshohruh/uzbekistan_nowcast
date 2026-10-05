"""Read-only production/shadow reproduction; tests write only cleanup workspaces.

Use `... cleanup_validate.py shadow` for Phase 6D validation without appending
snapshots, changing its manifests, fetching sources, or advancing its clock.
"""
from __future__ import annotations
import ast
from dataclasses import replace
import importlib
import json
import os
from pathlib import Path
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/cleanup'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
sys.dont_write_bytecode=True


def output(scope,value):
    (OUT/f'validation_{scope}.json').write_text(json.dumps(value,indent=2,default=str)+'\n',encoding='utf-8')


def shadow():
    sys.path.insert(0,str(ROOT/'scripts/research/phase6d'))
    import common
    from monitor import calculate
    import numpy as np
    import pandas as pd
    from uznowcast.models.data import load_dataset
    ledger=common.ledger_rows()
    rows=ledger[-7:];identity=rows[0]['snapshot_id']
    folder=common.OUT/'snapshots'/identity
    info=json.loads((folder/'inputs.json').read_text(encoding='utf-8'))
    panel=pd.DataFrame(info['panel']).set_index('month');panel.index=pd.to_datetime(panel.index)
    dataset=load_dataset(ROOT)
    usd=pd.DataFrame(info['benchmark_monthly'])
    usd=usd.set_index(usd.columns[0]);usd.index=pd.to_datetime(usd.index)
    monthly=pd.DataFrame(index=usd.index,columns=['usd_uzs_mom_dlog'],data=usd.to_numpy())
    events=pd.DataFrame(info['GDP']).drop(columns=['available_date','published_value','same_day_status'],errors='ignore')
    origin=pd.Timestamp(rows[0]['run_timestamp_utc']).tz_convert('Asia/Tashkent').tz_localize(None)
    available=common.vintage_kernel().available_gdp_vintage_as_of(events,origin,target=rows[0]['target_quarter'])
    dataset=replace(dataset,monthly=monthly,gdp=pd.DataFrame({'quarter':available.frame.index,dataset.target_field:available.frame.value.to_numpy()}))
    before=common.file_hash(common.OUT/'phase6d_prospective_forecast_ledger.csv')
    # Existing manifests are verified read-only; do not call helpers that can create missing seals.
    for snap in (common.OUT/'snapshots').iterdir():
        manifest=json.loads((snap/'manifest.json').read_text())
        for name,h in manifest['artifacts'].items():
            assert common.file_hash(snap/name)==h
    predictions,details=calculate(panel,dataset,available,rows[0]['target_quarter'],rows[0]['horizon'],origin)
    result=[]
    for row in rows:
        value,failure=predictions[row['model']]
        delta=abs(value-row['forecast'])
        assert not failure and np.isfinite(value) and delta<1e-8,(row['model'],value,row['forecast'],failure)
        result.append(dict(model=row['model'],before=row['forecast'],after=value,absolute_difference=delta))
    assert before==common.file_hash(common.OUT/'phase6d_prospective_forecast_ledger.csv')
    output('shadow',dict(passed=True,snapshot_id=identity,forecasts=result,ledger_unchanged=True,mode='VALIDATION_ONLY_NO_WRITES_TO_PHASE6D',tolerance=1e-8))
    print(json.dumps(result,indent=2))


def production():
    from uznowcast.models.data import load_dataset
    from uznowcast.operational.phase5a import detect_target_quarter,generate_nowcasts,file_sha256
    from uznowcast.operational.phase5b import detect_operational_stage
    reference=json.loads((ROOT/'results/production/current_nowcast.json').read_text(encoding='utf-8'))
    dataset=load_dataset(ROOT)
    target=detect_target_quarter(dataset,reference['as_of_date'])
    observed_stage=detect_operational_stage(dataset,target['target_quarter'],reference['information_cutoff'])
    stage=reference['operational_stage']
    hashes={name:file_sha256(ROOT/path) for name,path in [('monthly_master_hash','data/master/v1_monthly.parquet'),
        ('quarterly_master_hash','data/master/gdp_quarterly.parquet'),('registry_hash','registry/uzbekistan_nowcasting_v1.2_registry.xlsx')]}
    forecasts,_=generate_nowcasts(dataset,reference['as_of_date'],target,stage,hashes,reference['run_timestamp_utc'])
    results=[]
    for r in reference['predictions']:
        actual=forecasts.loc[forecasts.model.eq(r['model']),'prediction'].iloc[0]
        results.append(dict(model=r['model'],before=r['prediction'],after=actual,absolute_difference=abs(actual-r['prediction'])))
    reproduced=all(r['absolute_difference']<1e-8 for r in results)
    manifest=json.loads((ROOT/'results/production/run_manifest.json').read_text())
    config_ok=all(hashes[k]==v for k,v in manifest['input_data_fingerprints'].items())
    output('production',dict(passed=reproduced and config_ok,functional_smoke_passed=True,frozen_horizon_forecasts_reproduced=reproduced,
        configuration_gate_passed=config_ok,recorded_horizon=stage['horizon'],current_data_horizon=observed_stage['horizon'],
        forecasts=results,mode='FROZEN_CORE_SMOKE_NO_OUTPUT_WRITES',
        current_input_hashes=hashes,recorded_input_hashes=manifest['input_data_fingerprints'],
        warning=None if config_ok else 'Pre-existing master hash drift: current inputs differ from saved production release; full frozen production CLI would reject its configuration. Do not retune or overwrite production evidence.'))
    print(json.dumps(results,indent=2))


def imports():
    import pandas as pd
    inv=pd.read_csv(OUT/'active_python_inventory.csv')
    rows=[]
    for r in inv.to_dict('records'):
        path=ROOT/r['path']
        if not path.exists() or r['candidate_action']=='ARCHIVE':continue
        if r['classification']=='UNKNOWN':
            rows.append(dict(path=r['path'],status='UNKNOWN_RETAINED_NOT_EXECUTED'));continue
        ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
        status='SYNTAX_CHECKED_ENTRYPOINT_NOT_IMPORTED'
        if r['path'].startswith('src/') and path.name!='__main__.py':
            module=r['path'][4:-3].replace('/','.').removesuffix('.__init__')
            importlib.import_module(module);status='IMPORTED'
        rows.append(dict(path=r['path'],status=status))
    output('imports',dict(passed=True,n_checked=len(rows),import_errors=[],checks=rows,
        note='Script entrypoints with top-level effects are syntax checked; production and Phase 6D callable dependencies execute in isolated smoke checks.'))
    print('Import/syntax checks passed:',len(rows))


def tests(scope,label):
    import pytest
    from _pytest.tmpdir import TempPathFactory
    temp=OUT/'validation_workspaces'/('t_'+uuid.uuid4().hex[:8]);temp.mkdir(parents=True)
    def base(self):self._basetemp=temp;return temp
    def mktemp(self,basename,numbered=True):
        path=temp/(basename[:12]+uuid.uuid4().hex[:8]);path.mkdir();return path
    if sys.platform=='win32':TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    # Before quarantine, deny imports from all candidate archive paths. This proves
    # test execution does not rely on old disposable source copies still on disk.
    if label=='baseline':
        from cleanup_audit import temporary
        class ExcludeArchivedImports:
            def find_spec(self,fullname,path=None,target=None):
                from importlib.machinery import PathFinder
                found=PathFinder.find_spec(fullname,path)
                if found and found.origin:
                    origin=Path(found.origin).resolve()
                    if origin.is_relative_to(ROOT):
                        relative=origin.relative_to(ROOT).as_posix()
                        if temporary(relative) and not relative.startswith(('.venv/','venv/','results/cleanup/','results/phase6d/')):
                            raise ImportError('Quarantine exclusion: '+found.origin)
                return None
        sys.meta_path.insert(0,ExcludeArchivedImports())
    paths={'repository':['tests'],'phase6c':['scripts/research/phase6c/test_phase6c.py'],
           'phase6d':['scripts/research/phase6d/test_phase6d.py'],
           'phase6b':['scripts/research/phase6b/test_experiment.py'],
           'phase6b1':['scripts/research/phase6b1/test_boundary.py','scripts/research/phase6b1/test_reproduction.py'],
           'phase6b2':['scripts/research/phase6b2/test_vintages.py'],
           'phase6a2':['scripts/research/phase6a2/test_recovery.py']}[scope]
    xml=OUT/f'{label}_{scope}_tests.xml'
    code=pytest.main([*paths,'-p','no:cacheprovider','--junitxml',str(xml),'-q'])
    suites=list(ET.parse(xml).getroot().iter('testsuite'))
    result={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','errors','failures','skipped']}
    result.update(passed=result['tests']-result['errors']-result['failures']-result['skipped'],exit_code=int(code),label=label,scope=scope)
    output(f'{label}_{scope}_tests',result)
    return int(code)


if __name__=='__main__':
    scope=sys.argv[1];label=sys.argv[2] if len(sys.argv)>2 else 'after'
    if scope in ['shadow','production','imports']:
        {'shadow':shadow,'production':production,'imports':imports}[scope]()
    else:sys.exit(tests(scope,label))
