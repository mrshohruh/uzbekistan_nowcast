"""Auditable minimization after explicit scientific-equivalence acceptance."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/repository_cleanup'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def rows(path,values):
    if not values:return
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)

def inputs():
    """Discover source references rather than copying an unbounded repository."""
    paths=set()
    def visit(v):
        if isinstance(v,dict):
            for k,x in v.items():
                if k in {'raw_file_path','raw_file'} and isinstance(x,str):paths.add(x.replace('\\','/'))
                else:visit(x)
        elif isinstance(v,list):
            for x in v:visit(x)
    import pandas as pd
    for p in [ROOT/'metadata/observations_long.parquet']:
        frame=pd.read_parquet(p)
        for col in ['raw_file_path','raw_file']:
            if col in frame:paths.update(str(x).replace('\\','/') for x in frame[col].dropna())
    for p in [ROOT/'data/current/predictor_provenance.csv',ROOT/'tests/fixtures/industry_receipts.json']:
        if p.suffix=='.csv':
            for r in csv.DictReader(p.open(encoding='utf-8')):visit(r)
        else:visit(json.loads(p.read_text(encoding='utf-8')))
    for directory in ['results/operations/prospective/source_checks','results/operations/prospective/snapshots']:
        for p in (ROOT/directory).rglob('*.json'):visit(json.loads(p.read_text(encoding='utf-8')))
    # Frozen official workbook parser regression fixture.
    for p in (ROOT/'results/operations').glob('update_*/source_receipts.csv'):
        for r in csv.DictReader(p.open(encoding='utf-8')):visit(r)
    reloc=json.loads((ROOT/'config/provenance_relocations.json').read_text())
    paths={reloc.get(p,p) for p in paths}
    seal=json.loads((ROOT/'config/production_seal.json').read_text())
    paths.update(p for p in seal['initial_input_hashes'] if p.startswith(('data/','metadata/')) and not p.startswith('data/current/'))
    archived={}
    for p in (ROOT/'metadata').glob('*.parquet'):
        frame=pd.read_parquet(p)
        if 'raw_file_path' in frame and 'checksum' in frame:
            for r,h in zip(frame.raw_file_path,frame.checksum):
                if isinstance(r,str) and isinstance(h,str):archived[r.replace('\\','/')]=h
    valid=[p for p in sorted(paths) if (ROOT/p).is_file() and (ROOT/p).resolve().is_relative_to(ROOT.resolve())]
    def entry(p):return p,archived.get(p) or sha(ROOT/p)
    with ThreadPoolExecutor(max_workers=24) as pool:existing=dict(pool.map(entry,valid))
    missing=[p for p in sorted(paths) if not (ROOT/p).is_file()]
    write(ROOT/'config/bootstrap_inputs.json',dict(protocol='EXPLICIT_EXTERNAL_DATA_V1',files=existing,
        original_missing_source_references=missing,checksum_basis='Existing immutable download checksums for archived payloads; freshly computed for other inputs; bootstrap verifies every copied byte',note='Missing historical references are preserved as missing; never fabricated or silently downloaded.'))
    return existing

def plan():
    external=json.loads((ROOT/'config/bootstrap_inputs.json').read_text())['files'] if (ROOT/'config/bootstrap_inputs.json').exists() else inputs()
    tracked=set(subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines())
    seal=json.loads((ROOT/'config/production_seal.json').read_text())
    keep=set(seal['runtime_hashes'])|set(seal['initial_input_hashes'])|set(external)
    files=[]
    legacy_src={'bridge.py','cli.py','__main__.py','evaluate.py','evaluate_v11.py','matched.py','metrics.py','preprocess.py','production.py','splits.py','phase4b.py','phase4c.py','phase5c.py'}
    legacy_tests={'conftest.py','__init__.py','test_data.py','test_benchmarks.py','test_midas.py'}
    historical_results=('results/phase','results/research/','results/shadow/','results/challengers/','results/production/','results/reconciliation/','results/op_tests/','results/cleanup/','results/archive/')
    old_scripts={'scripts/create_registry_v1_1.py','scripts/create_registry_v1_2.py','scripts/phase5b2_cleanup.py','scripts/phase5b2_finalize.py','scripts/operations/test_operations.py','scripts/operations/run_tests.py','ACTIVE_CORE.md','PROJECT_STATE.md','CODEX_START_PROMPT.md','results_phase6c_run.log'}
    candidates=set(tracked)
    for directory in ['scripts/research','scripts/phase6e','src/uznowcast/shadow','tests/shadow','tests/operational','data/staging','data/t','results/current','results/operations/prospective','scripts/maintenance']:
        for parent,dirs,names in os.walk(ROOT/directory):
            dirs[:]=[d for d in dirs if d!='__pycache__']
            candidates.update((Path(parent)/n).relative_to(ROOT).as_posix() for n in names)
    for rel in sorted(candidates):
        if rel in keep:continue
        reason=None;category='F: research-only'
        if rel.startswith('scripts/phase6e/'):reason='Superseded compatibility namespace';category='E: compatibility-only'
        elif rel.startswith('scripts/research/'):reason='Historical kernel; reusable numerical functions extracted'
        elif rel.startswith('src/uznowcast/models/') and Path(rel).name in legacy_src:reason='Unused development evaluator/model implementation'
        elif rel.startswith('src/uznowcast/operational/') and Path(rel).name not in {'forecast.py','__init__.py'}:reason='Current release-aware functions extracted'
        elif rel.startswith('src/uznowcast/shadow/'):reason='Old challenger infrastructure; immutable storage extracted'
        elif rel.startswith(('tests/shadow/','tests/operational/')):reason='Tests for removed historical infrastructure'
        elif rel.startswith('tests/models/') and Path(rel).name not in legacy_tests:reason='Tests for removed model searches/evaluation variants'
        elif rel.startswith('scripts/maintenance/') and Path(rel).name not in {'finalize_repository.py','validate_current.py','compare_migration.py'}:reason='Completed historical migration/cleanup tool'
        elif rel in old_scripts:reason='Historical one-time script or duplicate test entrypoint'
        elif rel.startswith(('data/staging/','data/t/')):reason='Reproducible isolated validation workspace';category='G: generated/staging'
        elif '/_vendor/' in rel:reason='Accidentally tracked historical downloaded dependencies';category='G: generated/staging'
        elif rel.startswith('results/current/') and Path(rel).name in {'pre_change_state.json','test_results.json','validation_evidence.json','determinism.json','dashboard_preview.png','legacy_current_dashboard.html','console_summary.txt'}:reason='Superseded historical validation artifact'
        elif rel.startswith('results/operations/prospective/') and (Path(rel).suffix in {'.log','.xml'} or Path(rel).name in {'frozen_challengers.json','protected_start.json','new_test_results.json','phase6c_test_results.json','repository_test_results.json','research_challenger_registry.csv','research_experiment_registry.csv'}):reason='Unused historical seal/test/development inventory'
        elif rel.startswith(historical_results):reason='Historical results recoverable from checkpoint';category='D: historical checksum/evidence-only'
        elif rel.startswith('dashboard/') and Path(rel).name not in {'uzbekistan_nowcast_v2.html','uzbekistan_nowcast.html','README.md'}:reason='Superseded dashboard'
        if reason:
            p=ROOT/rel
            if rel not in tracked and not rel.startswith(('data/staging/','data/t/','results/current/','results/operations/prospective/','scripts/maintenance/')):continue
            try:h=('GENERATED_REPRODUCIBLE' if rel.startswith(('data/staging/','data/t/')) else sha(p)) if p.is_file() else ''
            except OSError:h='UNREADABLE_PREEXISTING'
            files.append(dict(path=rel,category=category,reason=reason,sha256=h,tracked=rel in tracked,recoverable_commit='fe252655d79648c8af3132f3c1d635db3bdd2253' if rel in tracked else 'generated; original raw archives retained'))
    rows(OUT/'phase6h1_removed_files.csv',files)
    write(OUT/'phase6h1/removal_plan.json',files)
    print(json.dumps(dict(planned_removals=len(files),external_inputs=len(external))))

def remove():
    seal=json.loads((ROOT/'config/production_seal.json').read_text())
    if seal['status']!='ACCEPTED':raise ValueError('Accept proven current seal before deletion')
    files=json.loads((OUT/'phase6h1/removal_plan.json').read_text())
    blocked=[]
    for r in files:
        p=(ROOT/r['path']).resolve()
        if not p.is_relative_to(ROOT.resolve()):raise ValueError('Unsafe removal')
        try:
            if p.is_file():p.unlink()
        except OSError as e:blocked.append(dict(path=r['path'],error=str(e)))
    # Remove empty generated directories only; never touch raw archives.
    for directory in ['data/staging','data/t','scripts/research','scripts/phase6e','tests/shadow','tests/operational','src/uznowcast/shadow']:
        for parent,dirs,names in os.walk(ROOT/directory,topdown=False):
            p=Path(parent)
            if p.name=='__pycache__':shutil.rmtree(p)
            try:p.rmdir()
            except OSError:pass
    write(OUT/'phase6h1/removal_results.json',dict(planned=len(files),blocked=blocked))
    print(json.dumps(dict(planned=len(files),blocked=len(blocked))))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['plan','remove']);args=parser.parse_args()
    plan() if args.mode=='plan' else remove()
