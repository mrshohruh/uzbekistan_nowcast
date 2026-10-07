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
    """Project only sealed runtime files and necessary inputs into isolation."""
    staged.mkdir(parents=True,exist_ok=False)
    seal=read(root/'config/production_seal.json')
    paths=set(seal['runtime_hashes']) | set(seal['initial_input_hashes'])
    paths.update(['config/production_seal.json'])
    if (root/'config/production_seal_acceptance.json').exists():paths.add('config/production_seal_acceptance.json')
    # Prospective records are operational state, rather than copied research trees.
    for path in (root/'results/operations/prospective').rglob('*'):
        if path.is_file() and not any(part.startswith(('__pycache__','t_','test_')) for part in path.parts):
            paths.add(path.relative_to(root).as_posix())
    for rel in sorted(paths):copy_file(root,staged,rel)
    (staged/'dashboard').mkdir(exist_ok=True)



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
            source=root/event['raw_file_path'];folder=staged/'results/operations/prospective/source_checks';folder.mkdir(exist_ok=True)
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
        from uznowcast.storage import digest
        write(staged/'results/operations/prospective/source_checks'/(digest(check)+'_check.json'),check)
        return check
    checks=[read(p) for p in (root/'results/operations/prospective/source_checks').glob('*_check.json')]
    if asof is not None:checks=[c for c in checks if pd.Timestamp(c['checked_at_utc'])<=asof]
    if not checks:raise ValueError('No archived official GDP check available')
    return max(checks,key=lambda c:c['checked_at_utc'])
