"""Immutable run evidence, model locks and recoverable file promotion."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str, allow_nan=False)+'\n', encoding='utf-8')


def model_lock(root):
    bundle = read(root/'results/phase6d/phase6d_frozen_challengers.json')
    paths = {**bundle['code_hashes'], **bundle['source_artifact_hashes'], **bundle['static_specification_hashes']}
    paths['results/phase6d/phase6d_frozen_challengers.json'] = sha(root/'results/phase6d/phase6d_frozen_challengers.json')
    inventory = pd.read_csv(root/'results/phase5b1/phase5b1_code_hash_inventory.csv')
    for row in inventory.to_dict('records'):
        if row['file_path'].startswith(('src/', 'config/')):
            paths[row['file_path']] = row['sha256']
    for rel, expected in paths.items():
        if sha(root/rel) != expected:
            raise ValueError('Frozen code/specification mismatch: '+rel)
    return paths, bundle


def protected(root):
    paths, _ = model_lock(root)
    for directory in ['results/production', 'results/phase5b1', 'results/phase6c', 'results/phase6d']:
        for parent, dirs, files in os.walk(root/directory):
            dirs[:] = [d for d in dirs if not d.startswith(('t_', 'test_', '_pytest', '__pycache__', '.pytest'))]
            for name in files:
                p = Path(parent)/name
                if not p.is_symlink(): paths[p.relative_to(root).as_posix()] = sha(p)
    return paths


def verify(root, expected, allowed=()):
    changed = [p for p,h in expected.items() if p not in allowed and (not (root/p).is_file() or sha(root/p)!=h)]
    if changed: raise ValueError('Protected artifacts changed: '+', '.join(changed))


def preflight(root):
    frozen, bundle = model_lock(root)
    paths=['registry/uzbekistan_nowcasting_v1.2_registry.xlsx','data/master/v1_monthly.parquet','data/master/gdp_quarterly.parquet',
           'results/phase6d/phase6d_prospective_forecast_ledger.csv','results/phase6d/phase6d_realization_registry.csv',
           'results/phase6d/phase6d_withdrawal_registry.csv']
    current={p.relative_to(root).as_posix():sha(p) for directory in ['data/master','data/processed','metadata','data/operations']
             for p in (root/directory).glob('*') if p.is_file() and p.suffix in {'.parquet','.xlsx'}}
    return dict(timestamp=datetime.now(timezone.utc).isoformat(),current_data_hashes=current,
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        git_status=subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True,encoding='utf-8'),
        input_hashes={p:sha(root/p) if (root/p).exists() else None for p in paths},
        frozen_hashes=frozen,specification_hashes=bundle['specification_hashes'],protected_hashes=protected(root))


@contextmanager
def operational_lock(root):
    path=root/'data/staging/operations.lock';path.parent.mkdir(parents=True,exist_ok=True)
    try:
        with path.open('x',encoding='utf-8') as f:f.write(str(os.getpid()))
    except FileExistsError as exc:
        raise RuntimeError('Another operation or interrupted transaction holds data/staging/operations.lock; inspect its journal before recovery.') from exc
    try:yield
    finally:path.unlink()


def promote(root, staged, paths, run_id, before, *, replace=os.replace,validate=None):
    """Atomic per-file replacement with a journal, durable originals and rollback.

    Readers should use this workflow's lock/committed manifest. A filesystem cannot
    atomically replace multiple Parquet files together; the journal identifies an
    interrupted transaction and prevents the next run from continuing blindly.
    """
    backup=root/'data/versions'/run_id;backup.mkdir(parents=True,exist_ok=False)
    paths=list(dict.fromkeys(paths));journal=backup/'transaction.json'
    for rel in paths:
        destination=(root/rel).resolve()
        if not destination.is_relative_to(root.resolve()) or not (staged/rel).is_file():raise ValueError('Unsafe/missing transaction path: '+rel)
        actual=sha(destination) if destination.exists() else None
        if actual!=before.get(rel):raise RuntimeError('Concurrent modification: '+rel)
        if destination.exists():
            saved=backup/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(destination,saved)
    write(journal,dict(status='PREPARED',paths=paths,before=before,completed=[]))
    completed=[]
    try:
        for rel in paths:
            target=root/rel;target.parent.mkdir(parents=True,exist_ok=True)
            temp=target.with_name(target.name+'.operations-'+uuid.uuid4().hex)
            shutil.copyfile(staged/rel,temp)
            try:replace(temp,target)
            finally:
                if temp.exists():temp.unlink()
            completed.append(rel)
            write(journal,dict(status='COMMITTING',paths=paths,before=before,completed=completed))
        if validate is not None:validate()
        write(journal,dict(status='COMMITTED',paths=paths,before=before,completed=completed))
    except BaseException:
        for rel in reversed(completed):
            saved=backup/rel;target=root/rel
            if saved.exists():
                temp=target.with_name(target.name+'.rollback');shutil.copyfile(saved,temp);os.replace(temp,target)
            elif target.exists():target.unlink()
        write(journal,dict(status='ROLLED_BACK',paths=paths,before=before,completed=completed))
        raise
    return {rel:sha(root/rel) for rel in paths}


def rollback_completed(root,run_id,promoted):
    """Rollback this still-locked operation if final reporting/validation fails."""
    backup=root/'data/versions'/run_id;journal=read(backup/'transaction.json')
    for rel,h in promoted.items():
        if not (root/rel).is_file() or sha(root/rel)!=h:raise RuntimeError('Concurrent edit prevents rollback: '+rel)
    for rel in reversed(journal['completed']):
        target=(root/rel).resolve();saved=backup/rel
        if not target.is_relative_to(root.resolve()):raise ValueError('Unsafe rollback target')
        if saved.exists():
            temp=target.with_name(target.name+'.rollback');shutil.copyfile(saved,temp);os.replace(temp,target)
        elif target.exists():target.unlink()
    write(backup/'transaction.json',dict(journal,status='ROLLED_BACK'))


def pending_transactions(root):
    return [p for p in (root/'data/versions').glob('*/transaction.json') if read(p)['status'] not in {'COMMITTED','ROLLED_BACK'}]


def validate_current_manifest(state, specifications):
    if state.get('scope')!='CURRENT_OPERATIONAL_STATE' or state.get('does_not_replace_historical_release') is not True or state.get('historical_release_reproduction') is not False:
        raise ValueError('Current-state identity cannot replace historical evidence')
    if state.get('candidate_only') and state.get('promoted'):raise ValueError('Candidate-only state cannot claim promotion')
    if state.get('model_specification_hashes')!=specifications:raise ValueError('Current manifest changed model specifications')
    if set(state.get('master_hashes',{}))!={'monthly','quarterly'}:raise ValueError('Both master hashes are required')
    for h in [*state['master_hashes'].values(),state.get('registry_hash','')]:
        if not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):raise ValueError('Invalid current input SHA256')
    if pd.Timestamp(state['timestamp_utc']).tzinfo is None:raise ValueError('Actual manifest timestamp must include its timezone')


def verify_current_version(root):
    """Permit recorded operational successors, never silently accept unexplained masters."""
    candidates=[]
    for p in (root/'results/operations').glob('update_*/current_state_manifest.json'):
        state=read(p)
        if state.get('promoted') and not state.get('candidate_only') and (p.parent/'run_manifest.json').exists():
            if read(p.parent/'run_manifest.json').get('status')!='UPDATE_ABORTED':candidates.append(state)
    if candidates:
        state=max(candidates,key=lambda s:s['timestamp_utc']);expected=state['master_hashes']
    else:
        previous=read(root/'results/reconciliation/current_production_state_manifest.json')
        expected=dict(monthly=previous['input_hashes']['monthly_master_hash'],quarterly=previous['input_hashes']['quarterly_master_hash'])
    for kind,name in [('monthly','v1_monthly'),('quarterly','gdp_quarterly')]:
        if sha(root/f'data/master/{name}.parquet')!=expected[kind]:raise ValueError('Unrecognized current master version: '+kind+'; reconcile before operations')
