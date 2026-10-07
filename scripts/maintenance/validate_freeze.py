"""Validate the production freeze without publishing or refreshing observations."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
import uuid
import xml.etree.ElementTree as ET

from scripts.maintenance.repository_freeze import ROOT, OUT, checksum, write


def command(name, args):
    with (OUT/f'{name}.log').open('w',encoding='utf-8') as log:
        result=subprocess.run([sys.executable,*args],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                              env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
    write(f'{name}_exit.json',dict(exit_code=result.returncode,command=args))
    return result.returncode


def tests(scope):
    import pytest
    from _pytest.tmpdir import TempPathFactory
    scopes={'repository':['tests'], 'operations':['scripts/operations/test_operations.py'],
            'dfm':['scripts/research/phase6c/test_phase6c.py'],
            'vintages':['scripts/research/phase6b2/test_vintages.py']}
    temp=ROOT/'results/h6'/uuid.uuid4().hex[:8];temp.mkdir(parents=True)
    def base(self):self._basetemp=temp;return temp
    def mktemp(self,basename,numbered=True):
        path=temp/(basename[:8]+uuid.uuid4().hex[:6]);path.mkdir();return path
    if sys.platform=='win32':
        TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    xml=OUT/f'tests_{scope}.xml'
    historical_inventory_tests={
        'dfm':'scripts/research/phase6c/test_phase6c.py::test_protected_inventory_and_saved_metrics',
        'vintages':'scripts/research/phase6b2/test_vintages.py::test_protected_artifacts_unchanged'}
    selection=['--deselect',historical_inventory_tests[scope]] if scope in historical_inventory_tests else []
    code=int(pytest.main([*scopes[scope],*selection,'-p','no:cacheprovider','--junitxml',str(xml),'-q']))
    suites=list(ET.parse(xml).getroot().iter('testsuite'))
    totals={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
    write(f'tests_{scope}.json',dict(totals,exit_code=code,passed=totals['tests']-totals['failures']-totals['errors']-totals['skipped'],
          historical_test_outside_current_suite=historical_inventory_tests.get(scope)))
    if not temp.resolve().is_relative_to((ROOT/'results/h6').resolve()):
        raise ValueError('Unsafe test workspace cleanup')
    shutil.rmtree(temp)
    return code


def compare():
    baseline=json.loads((OUT/'pre_cleanup_manifest.json').read_text())
    runs={name:json.loads((OUT/name/'phase6e_current_nowcast.json').read_text()) for name in ['baseline_run','post_run','deterministic_run']}
    keys=['dfm_forecast','umidas_forecast','combo_50_50_forecast','final_forecast']
    predictions={key:{name:run[key] for name,run in runs.items()} for key in keys}
    exact=all(len(set(values.values()))==1 for values in predictions.values())
    fields={'dfm_forecast':'dfm_output','umidas_forecast':'umidas_output','combo_50_50_forecast':'combination_output','final_forecast':'final_nowcast'}
    saved_exact=all(runs['post_run'][k]==baseline[v] for k,v in fields.items())
    current_changed=[rel for rel,h in baseline['checksums'].items()
                     if rel.startswith(('src/','config/','registry/','data/master/','data/processed/','metadata/')) and
                     (not (ROOT/rel).is_file() or checksum(ROOT/rel)!=h)]
    output_differences=[]
    for path in (OUT/'baseline_run').glob('*'):
        if path.suffix not in {'.csv','.json','.html'} or path.name=='phase6e_run_manifest.json':continue
        for name in ['post_run','deterministic_run']:
            other=OUT/name/path.name
            if not other.is_file() or checksum(path)!=checksum(other):output_differences.append(f'{name}/{path.name}')
    pointer=baseline['production_pointer']
    authoritative=[pointer['nowcast'],pointer['policy'],pointer['dashboard'],'dashboard/current/uzbekistan_nowcast.html']
    # dashboard paths may be outside the broad baseline checksum inventory.
    frozen_changed=[p for p in authoritative if p in baseline['checksums'] and checksum(ROOT/p)!=baseline['checksums'][p]]
    result=dict(passed=exact and saved_exact and not current_changed and not frozen_changed and not output_differences,
                predictions=predictions,exact_rerun=exact,saved_production_exact=saved_exact,
                transformed_data_or_frozen_code_changes=current_changed,authoritative_output_changes=frozen_changed,
                scientific_and_dashboard_output_differences=output_differences,
                exclusions='Run manifests contain relocated code paths/hashes; reports/logs contain operational metadata')
    write('production_comparison.json',result)
    print(json.dumps(result,indent=2));return int(not result['passed'])


if __name__=='__main__':
    if os.name=='nt' and not sys.flags.utf8_mode:
        sys.exit(subprocess.call([sys.executable,'-X','utf8','-m','scripts.maintenance.validate_freeze',*sys.argv[1:]],cwd=ROOT))
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['post_run','deterministic_run','operations','tests','compare'])
    parser.add_argument('--scope',choices=['repository','operations','dfm','vintages'],default='repository')
    args=parser.parse_args()
    if args.mode=='tests':code=tests(args.scope)
    elif args.mode=='compare':code=compare()
    elif args.mode=='operations':
        code=command('post_operations',['-m','scripts.production.update','--run-nowcast','--dry-run','--no-network','--as-of','2026-10-05'])
    else:
        code=command(args.mode,['-m','scripts.production.run','--output-dir',str(OUT/args.mode),'--no-publish'])
    sys.exit(code)
