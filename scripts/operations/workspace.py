"""Build an isolated project for unchanged Phase 6D code and staged datasets."""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pandas as pd
from scripts.operations.state import read, write, sha


def copy_file(root,staged,rel):
    source=root/rel;target=staged/rel
    if not source.is_file():raise ValueError('Required operational input missing: '+rel)
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)


def seed(root,staged):
    staged.mkdir(parents=True,exist_ok=False)
    frozen=read(root/'results/phase6d/phase6d_protected_start.json')
    for rel,expected in frozen.items():
        if rel=='dashboard/current/uzbekistan_nowcast.html' and sha(root/rel)!=expected:
            # Phase 6E deliberately promotes the operational dashboard pointer.
            # Frozen workers still receive the original, hash-verified V1 file.
            legacy=root/'results/phase6e/legacy_current_dashboard.html'
            policy=root/'results/phase6e/phase6e_production_policy.json'
            manifest=root/'results/phase6e/phase6e_run_manifest.json'
            if (not legacy.exists() or sha(legacy)!=expected or not policy.exists() or not manifest.exists()
                    or read(policy).get('status')!='PHASE6E_PROMOTED'
                    or read(manifest).get('dashboard_sha256')!=sha(root/rel)):
                raise ValueError('Unverified production V2 dashboard pointer')
            target=staged/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(legacy,target)
            continue
        if sha(root/rel)!=expected:raise ValueError('Pre-existing protected-artifact mismatch: '+rel)
        copy_file(root,staged,rel)
    for directory in ['src','scripts/operations','scripts/research/phase6b2','scripts/research/phase6c','scripts/research/phase6d','config','registry']:
        for parent,dirs,files in os.walk(root/directory):
            dirs[:]=[d for d in dirs if not d.startswith(('__pycache__','t_','test_','_vendor'))]
            for name in files:
                path=Path(parent)/name
                if path.suffix in {'.py','.json','.yaml','.xlsx'}:copy_file(root,staged,path.relative_to(root).as_posix())
    for directory in ['data/master','data/processed','metadata']:
        for path in (root/directory).glob('*.parquet'):copy_file(root,staged,path.relative_to(root).as_posix())
    for rel in ['data/research/phase6a2/cbu_midas_monthly_panel.csv','results/research/phase6a2/phase6a2_provenance.csv',
                'results/research/phase6b2/phase6b2_gdp_revision_history.csv']:
        copy_file(root,staged,rel)
    overlay=root/'data/operations/shadow_observations.parquet'
    if overlay.exists():copy_file(root,staged,overlay.relative_to(root).as_posix())
    for parent,dirs,files in os.walk(root/'results/phase6d'):
        dirs[:]=[d for d in dirs if not d.startswith(('__pycache__','t_','test_','_pytest'))]
        for name in files:
            path=Path(parent)/name;copy_file(root,staged,path.relative_to(root).as_posix())
    (staged/'dashboard').mkdir(exist_ok=True)
    for rel in ['dashboard/phase6d_shadow_monitor.html']:
        if (root/rel).exists():copy_file(root,staged,rel)


def worker(staged,request,mode='preview'):
    path=staged/'operations_request.json';write(path,request)
    env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run([sys.executable,str(staged/'scripts/operations/shadow_worker.py'),mode,str(path)],
                          cwd=staged,env=env,capture_output=True,text=True,encoding='utf-8')
    (staged/'shadow_worker.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError('Frozen shadow worker failed: '+(result.stderr or result.stdout)[-3000:])
    return read(staged/'shadow_preview.json')


def current_check(root,staged,frame=None,client=None,asof=None):
    """An unverified GDP API value is never registered as a realization."""
    # Real GDP acquisition uses the original SIAT downloader and exact parser.
    if frame is not None and client is not None:
        frame=frame.loc[frame.clean_value.notna()]
        events=[e for e in client.events if e.get('variable_key')=='gdp_real_yoy' and e.get('http_status')==200]
        descriptors=[e for e in events if '/table/download/' in e['source_url']]
        payloads=[e for e in events if '/table/download/' not in e['source_url']]
        if not descriptors or not payloads:raise ValueError('GDP descriptor/payload receipts missing')
        receipts={}
        for kind,event in [('descriptor',descriptors[-1]),('payload',payloads[-1])]:
            source=root/event['raw_file_path'];folder=staged/'results/phase6d/source_checks';folder.mkdir(exist_ok=True)
            target=folder/(event['checksum']+'.payload');shutil.copyfile(source,target)
            receipts[kind]=dict(source_url=event['source_url'],retrieved_at=event['retrieved_at'],http_status=200,
                checksum=event['checksum'],raw_file_path=target.relative_to(staged).as_posix(),content_type=event.get('content_type'))
        descriptor=read(root/descriptors[-1]['raw_file_path'])
        check=dict(checked_at_utc=receipts['payload']['retrieved_at'],descriptor=receipts['descriptor'],payload=receipts['payload'],
            latest_quarter=frame.reference_period.max(),available_quarters=frame.reference_period.tolist(),
            values=dict(zip(frame.reference_period,frame.clean_value)),source_verified=True,observed_dataset_update=descriptor.get('updated_at'),
            first_release_dates_verified=False,note='Official current series only; no first-release inference or automatic scoring')
        import hashlib,json
        # Use the existing storage digest byte convention.
        sys.path.insert(0,str(root/'src'))
        from uznowcast.shadow.storage import digest
        write(staged/'results/phase6d/source_checks'/(digest(check)+'_check.json'),check)
        return check
    checks=[read(p) for p in (root/'results/phase6d/source_checks').glob('*_check.json')]
    if asof is not None:checks=[c for c in checks if pd.Timestamp(c['checked_at_utc'])<=asof]
    if not checks:raise ValueError('No archived official GDP check available')
    return max(checks,key=lambda c:c['checked_at_utc'])
