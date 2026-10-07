"""Isolated adapter: invoke unchanged Phase 6D calculations and its supported writer."""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'src'))
from scripts.operations.prospective import common, inputs as input_module, monitor
from uznowcast.models.data import information_cutoff_for_variable
from scripts.operations.state import read, write, sha


def adapted_inputs(asof):
    panel,dataset,provenance=input_module.inputs(asof)
    path=ROOT/'data/operations/shadow_observations.parquet'
    if path.exists():
        overlay=input_module.eligible(pd.read_parquet(path),asof)
        overlay=overlay.sort_values('retrieved_at').drop_duplicates(['variable_key','reference_period'],keep='last')
        for row in overlay.to_dict('records'):
            key=row['variable_key'];month=pd.Period(row['reference_period'],'M').to_timestamp('M')
            if key not in {'industrial_production','pos_turnover'}:raise ValueError('Unapproved shadow overlay variable')
            if key=='pos_turnover' and not row.get('scope_verified',False):continue
            if month not in panel.index or pd.isna(row['clean_value']):continue
            panel.loc[month,key]=float(row['clean_value'])
            provenance=[r for r in provenance if not (r['variable']==key and r['reference_period']==row['reference_period'])]
            provenance.append(common.safe(dict(variable=key,reference_period=row['reference_period'],value=float(row['clean_value']),
                retrieved_at=row['retrieved_at'],source_release_date=row['source_release_date'],raw_file_path=row['raw_file_path'],
                checksum=row['checksum'],source_url=row['source_url'])))
    return panel,dataset,provenance


def fingerprint(info,bundle,stage):
    """Economic information identity ignores retrieval/report clock changes."""
    def observations(records):
        result=[]
        for row in records:
            date_key=next(k for k in ['month','date','index'] if k in row)
            period=str(pd.Timestamp(row[date_key]).date())
            result.append(dict(period=period,values={k:common.safe(v) for k,v in row.items() if k!=date_key}))
        return result
    gdp=[dict(quarter=r['quarter'],value=float(r.get('value',r.get('published_value'))),
        publication_date=str(pd.Timestamp(r['publication_date']).date()) if r.get('publication_date') else None) for r in info['GDP']]
    return common.digest(dict(panel=observations(info['panel']),benchmark=observations(info['benchmark_monthly']),
        GDP=gdp,target=info['target'],horizon=info['horizon'],stage=stage,specifications=bundle['specification_hashes']))


def prepare(now,check,calculate=True):
    bundle=read(ROOT/'config/model_definitions.json')
    target=monitor.select_target(check['latest_quarter'],now)
    horizon,nominal,stage,on_time=monitor.context(target,now)
    origin=now.tz_convert('Asia/Tashkent').tz_localize(None)
    panel,dataset,provenance=adapted_inputs(now)
    cutoff=information_cutoff_for_variable(nominal,'usd_uzs',dataset.release_lag_days,'standard')
    dataset.monthly.loc[dataset.monthly.index>cutoff,'usd_uzs_mom_dlog']=np.nan
    events=pd.read_csv(ROOT/'data/current/gdp_vintages.csv')
    events=events.loc[pd.to_datetime(events.retrieved_at,utc=True).le(now)]
    for r in common.records(common.OUT/'realization_records'):
        if pd.Timestamp(r['ingested_timestamp'])>now:continue
        events=pd.concat([events,pd.DataFrame([dict(quarter=r['target_quarter'],
            publication_date=r.get('revision_release_date',r['first_release_date']),value=float(r['value']),
            source_url=r['source_url'].replace('https://www.stat.uz/','https://stat.uz/'),sha256=r['checksum'],
            value_verified=True,date_verified=True,time_verified=False,publication_time=None)])],ignore_index=True)
    available=common.vintage_kernel().available_gdp_vintage_as_of(events,origin,target=target,timing_rule='STRICT')
    dataset=replace(dataset,gdp=pd.DataFrame({'quarter':available.frame.index,dataset.target_field:available.frame.value.to_numpy()}))
    k=common.kernel();spec=k.Spec('DFM-4_R1_P2',common.FIELDS,1,2,'2019-01-31',True,False)
    masked,_=k.mask(panel,spec,target,horizon,dataset.release_lag_days,'standard')
    info=common.safe(dict(panel=masked.reset_index().rename(columns={'index':'month'}).to_dict('records'),
        benchmark_monthly=dataset.monthly[['usd_uzs_mom_dlog']].dropna(how='all').reset_index().to_dict('records'),
        GDP=available.frame.reset_index().to_dict('records'),target=target,horizon=horizon))
    identity=fingerprint(info,bundle,stage)
    withdrawn={r['snapshot_id'] for r in common.records(common.OUT/'withdrawal_records')}
    duplicate=None
    for row in reversed(common.ledger_rows()):
        if row['snapshot_id'] in withdrawn:continue
        stored=read(common.OUT/'snapshots'/row['snapshot_id']/'inputs.json')
        if 'benchmark_monthly' in stored and fingerprint(stored,bundle,row['operational_stage'])==identity:
            duplicate=row['snapshot_id'];break
    if calculate:values,details=monitor.calculate(masked,dataset,available,target,horizon,origin)
    else:
        cached=[r for r in common.ledger_rows() if r['snapshot_id']==duplicate]
        values={m:(next((r['forecast'] for r in cached if r['model']==m),None),'') for m in common.MODELS}
    return dict(target=target,horizon=horizon,stage=stage,nominal_horizon_date=str(nominal.date()),information_fingerprint=identity,
        duplicate_snapshot=duplicate,forecasts={key:common.safe(value[0]) for key,value in values.items()},
        failures={key:value[1] for key,value in values.items() if value[1]},info=info,
        data_status=common.safe(input_module.status(masked,dataset.release_lag_days,origin).to_dict('records')))


def main():
    mode,request_path=sys.argv[1:3];request_path=Path(request_path);request=read(request_path)
    now=pd.Timestamp(request['cutoff_utc']);check=request['check']
    preview=prepare(now,check,calculate=request.get('calculate',True))
    if mode=='append':
        if request.get('expected_fingerprint')!=preview['information_fingerprint']:raise ValueError('Information changed between staging and shadow commit')
        if preview['duplicate_snapshot']:raise ValueError('DUPLICATE_INFORMATION_SET: refusing writer')
        if request.get('historical'):raise ValueError('Historical reproduction cannot append')
        monitor.inputs=adapted_inputs
        # The original supported writer controls timestamps, seals, ledger batches,
        # scoring, governance and dashboard generation inside the isolated project.
        monitor.run(check)
        preview['appended_snapshot']=common.ledger_rows()[-1]['snapshot_id']
        adapter_hashes={p.name:sha(p) for p in (ROOT/'scripts/operations').glob('*.py')}
        for name,h in adapter_hashes.items():
            archived=common.OUT/'code_archive'/h
            if not archived.exists():
                with archived.open('xb') as handle:handle.write((ROOT/'scripts/operations'/name).read_bytes())
            if sha(archived)!=h:raise ValueError('Operations adapter archive changed')
        common.freeze(common.OUT/'operations_contexts'/(preview['appended_snapshot']+'.json'),dict(
            snapshot_id=preview['appended_snapshot'],information_fingerprint=preview['information_fingerprint'],
            adapter_hashes=adapter_hashes,model_specifications_unchanged=True,
            overlay_sha256=sha(ROOT/'data/operations/shadow_observations.parquet') if (ROOT/'data/operations/shadow_observations.parquet').exists() else None))
    write(request_path.with_name('shadow_preview.json'),common.safe(preview))


if __name__=='__main__':main()
