"""Read-only frozen imports and Phase 6D-only storage boundaries."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'results/phase6d'
sys.path.insert(0, str(ROOT / 'src'))
from uznowcast.shadow.storage import freeze, digest, file_hash, append_record, records

FIELDS = ('industrial_production', 'ppi', 'usd_uzs', 'rub_uzs', 'gold_price', 'm2', 'fx_reserves_ex_gold', 'pos_turnover')
MODELS = ('AR1', 'AR2', 'UMIDAS_USD', 'PRODUCTION_ENSEMBLE', 'PHASE6C_DFM', 'COMBO_50_50', 'COMBO_DEV_WEIGHT')
WEIGHT_DFM = 0.5438822544881572
WEIGHT_UMIDAS = 0.4561177455118428
LEDGER_COLUMNS = ['run_id','run_timestamp_utc','as_of_date','information_cutoff','target_quarter','horizon','model',
 'forecast','operational_stage','nominal_horizon_date','canonical_horizon_eligible','latest_available_gdp_quarter',
 'latest_available_gdp_value','latest_predictor_month','factor_count','factor_ar_order','bridge',
 'combination_weight_dfm','combination_weight_umidas','specification_hash','input_data_hash','code_hash',
 'forecast_status','failure_reason','prospective_eligible','realization_available','realization_first_release',
 'forecast_error','absolute_error','squared_error','snapshot_id']


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def kernel():
    return module('phase6d_frozen_phase6c_kernel', 'scripts/research/phase6c/kernel.py')


def vintage_kernel():
    return module('phase6d_frozen_vintages', 'scripts/research/phase6b2/vintages.py')


def benchmark_kernel():
    directory = str(ROOT / 'scripts/research/phase6b2')
    if directory not in sys.path:
        sys.path.append(directory)
    return module('phase6d_frozen_benchmarks', 'scripts/research/phase6b2/run.py')


def safe(value):
    if isinstance(value, dict):
        return {str(k): safe(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)):
        return [safe(v) for v in value]
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, pd.Period, Path)):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if value is pd.NA or value is pd.NaT:
        return None
    return value


def write_json(path, value):
    path.write_text(json.dumps(safe(value), indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8')


def save(name, frame, out=OUT):
    frame.to_csv(out / f'phase6d_{name}.csv', index=False, float_format='%.17g')


def protection(root=ROOT):
    """Protect earlier artifacts across runs; dynamic inputs are checked per run."""
    hashes = {}
    for directory in ['src','scripts','config','registry','results','dashboard','docs']:
        for path in (root / directory).rglob('*'):
            relative = path.relative_to(root).as_posix()
            if any(s in relative for s in ['/phase6d/', '__pycache__', '_pytest', 'test_tmp', '_vendor', '/t_', 'pytest_cache', 'test_workspace']):
                continue
            if relative == 'dashboard/phase6d_shadow_monitor.html':
                continue
            if path.is_file():
                hashes[relative] = file_hash(path)
    return hashes


def verify_hashes(root, hashes):
    changed = [p for p,h in hashes.items() if not (root/p).is_file() or file_hash(root/p)!=h]
    if changed:
        raise ValueError('Protected artifact changed: ' + ', '.join(changed))


def csv_bytes(rows):
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=LEDGER_COLUMNS, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode('utf-8')


def ledger_rows(out=OUT):
    batches = records(out / 'ledger_batches')
    batches.sort(key=lambda r:r['sequence'])
    rows = []
    for i,batch in enumerate(batches):
        if batch['sequence'] != i:
            raise ValueError('Ledger sequence missing')
        rows.extend(batch['rows'])
    path = out / 'phase6d_prospective_forecast_ledger.csv'
    if path.exists() and path.read_bytes()!=csv_bytes(rows):
        raise ValueError('Append-only CSV ledger was altered; refusing repair')
    return rows


def append_ledger(rows, out=OUT):
    previous = ledger_rows(out)
    path = out / 'phase6d_prospective_forecast_ledger.csv'
    if not path.exists():
        with path.open('xb') as handle:
            handle.write(csv_bytes([]))
    if not rows:
        return False
    snapshot_id = rows[0]['snapshot_id']
    old = [r for r in previous if r['snapshot_id']==snapshot_id]
    if old:
        if old!=rows:
            raise ValueError('Conflicting rows for immutable snapshot')
        return False
    if previous and rows[0]['run_timestamp_utc']<previous[-1]['run_timestamp_utc']:
        raise ValueError('Cannot backdate prospective ledger')
    batch = dict(sequence=len(records(out/'ledger_batches')), rows=rows)
    append_record(out / 'ledger_batches', digest(batch), batch)
    # Check existing bytes BEFORE opening in append mode; retain every old byte.
    encoded = csv_bytes(previous+rows)
    prefix = csv_bytes(previous)
    assert encoded.startswith(prefix)
    with path.open('ab') as handle:
        handle.write(encoded[len(prefix):])
    return True


def verify_snapshots(out=OUT):
    ledger=ledger_rows(out)
    for identity in {r['snapshot_id'] for r in ledger}:
        folder=out/'snapshots'/identity
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        info=json.loads((folder/'inputs.json').read_text(encoding='utf-8'))
        rows=[r for r in ledger if r['snapshot_id']==identity]
        if digest(info)!=rows[0]['input_data_hash']:
            raise ValueError('Snapshot inputs do not match sealed ledger')
        if json.loads((folder/'forecasts.json').read_text(encoding='utf-8'))!=rows:
            raise ValueError('Snapshot forecasts do not match sealed ledger')
        for name,h in manifest['artifacts'].items():
            if file_hash(folder/name)!=h:
                raise ValueError('Immutable snapshot altered: '+name)
        for h in manifest['code_hashes'].values():
            if file_hash(out/'code_archive'/h)!=h:
                raise ValueError('Archived snapshot code changed')
        # An exclusive immutable seal also protects the fit manifest itself.
        freeze(out/'snapshot_seals'/(identity+'.json'),dict(snapshot_id=identity,manifest_sha256=file_hash(folder/'manifest.json')))
