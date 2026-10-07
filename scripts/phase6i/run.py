"""Offline reproducible Phase 6I research. Run: python -m scripts.phase6i.run."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import sys
import json
import hashlib
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0,str(ROOT/'src'))
from scripts.phase6i.models import KEYS, SPECS, estimate, gated, common_sample, metrics
from scripts.production.models import sw, frames, umidas
from scripts.operations.state import sha
from scripts.operations.prospective.inputs import eligible
from uznowcast.models.data import load_dataset, build_information_set

LOG = logging.getLogger('phase6i')


def protection(root=ROOT):
    """Hash all existing scientific, production, registry and raw inputs."""
    paths = []
    for directory in ['src','scripts','config','registry','data','metadata','dashboard','results','docs']:
        paths.extend(p for p in (root/directory).rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and not p.suffix == '.pyc'
            and not p.relative_to(root).as_posix().startswith(('results/phase6i/','scripts/phase6i/')))
    hashes={}
    def checksum(p):return p.relative_to(root).as_posix(),sha(p)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i,(name,value) in enumerate(pool.map(checksum,sorted(paths))):
            if i % 1000 == 0:LOG.info('Protection: hashing file %d/%d: %s',i,len(paths),name)
            hashes[name]=value
    return hashes


def current_inputs(dataset):
    current = json.loads((ROOT/'results/current/current_nowcast.json').read_text())
    ledger = pd.read_csv(ROOT/'results/operations/prospective/prospective_forecast_ledger.csv',float_precision='round_trip')
    withdrawn = pd.read_csv(ROOT/'results/operations/prospective/withdrawal_registry.csv')
    rows = ledger.loc[ledger.model.eq('UMIDAS_USD') & ledger.target_quarter.eq('2026Q3') &
        ~ledger.snapshot_id.isin(withdrawn.snapshot_id)]
    rows = rows.loc[np.isclose(rows.forecast,current['umidas_forecast'],rtol=0,atol=1e-10)]
    row = rows.sort_values('run_timestamp_utc').iloc[-1]
    info = json.loads((ROOT/'results/operations/prospective/snapshots'/row.snapshot_id/'inputs.json').read_text())
    cutoff = pd.Timestamp(row.information_cutoff)
    origin = cutoff.tz_convert('Asia/Tashkent').tz_localize(None)
    _, benchmark, available = frames(info, ROOT, origin)
    # Added predictors use canonical registry transforms, retrieval AND release gated.
    obs = eligible(pd.read_parquet(ROOT/'metadata/observations_long.parquet'),cutoff)
    obs = obs.loc[obs.frequency.astype(str).isin(['M','monthly'])].copy()
    obs['retrieval'] = pd.to_datetime(obs.retrieved_at,utc=True)
    monthly = benchmark.monthly.reindex(dataset.monthly.index.union(benchmark.monthly.index))
    for key in KEYS[1:]:
        source = obs.loc[obs.variable_key.eq(key)].sort_values('retrieval').drop_duplicates('reference_period',keep='last')
        series = pd.Series(pd.to_numeric(source.clean_value,errors='coerce').to_numpy(),
            index=pd.PeriodIndex(source.reference_period.astype(str),freq='M').to_timestamp('M'))
        monthly[dataset.clean_field_by_key[key]] = series.reindex(monthly.index)
    return replace(benchmark,monthly=monthly),available,info,origin,current,row.snapshot_id


def evaluate(dataset, origins, current_data):
    events = pd.read_csv(ROOT/'data/current/gdp_vintages.csv')
    forecasts, coefficients, diagnostics, reconstruction = [], [], [], []
    jobs = [(r,False) for r in origins.to_dict('records')]
    cd, ca, info, co, _, _ = current_data
    jobs.append((dict(target_quarter=info['target'],horizon=info['horizon'],
        forecast_origin_date=str(co),actual=np.nan,evaluation_group='CURRENT'),True))
    for row,is_current in jobs:
        target,horizon,origin = row['target_quarter'],row['horizon'],pd.Timestamp(row['forecast_origin_date'])
        available = ca if is_current else sw.common.vintage_kernel().available_gdp_vintage_as_of(events,origin,target=target,timing_rule='STRICT')
        ds = cd if is_current else gated(dataset,available)
        for model,keys in SPECS.items():
            prediction,diag = estimate(ds,available,keys,target,horizon)
            record = dict(model=model,origin=str(origin),target_quarter=target,horizon=horizon,
                actual=row['actual'],evaluation_group=row['evaluation_group'],prediction=prediction,
                **{k:v for k,v in diag.items() if k not in ['coefficients','standard_errors','columns','regressor_values']})
            forecasts.append(record); diagnostics.append(record)
            if 'coefficients' in diag:
                for term,b,se,x in zip(diag['columns'],diag['coefficients'],diag['standard_errors'],diag['regressor_values']):
                    variable,position = term.split(':') if ':' in term else (term,'')
                    coefficients.append(dict(model=model,origin=str(origin),target_quarter=target,horizon=horizon,
                        evaluation_group=row['evaluation_group'],variable=variable,monthly_position=position,
                        coefficient=b,standard_error=se,sign=int(np.sign(b)),regressor_value=x,
                        contribution_pp=b*x,n_train=diag['n_train'],condition_number=diag['condition_number']))
            if model == 'U0':
                expected,_,_ = umidas(ds,available,target,horizon,origin)
                frozen = current_data[4]['umidas_forecast'] if is_current else row['prediction']
                reconstruction.append(dict(origin=str(origin),target_quarter=target,horizon=horizon,
                    research=prediction,production_recomputed=expected,frozen=frozen,error=prediction-frozen))
                if not np.isclose(prediction,expected,rtol=0,atol=1e-12) or not np.isclose(prediction,frozen,rtol=0,atol=1e-7):
                    raise ValueError(f'U0 reproduction failed: {target} {horizon}')
    return pd.DataFrame(forecasts),pd.DataFrame(coefficients),pd.DataFrame(reconstruction)


def comparisons(f):
    rows, samples = [], []
    groups = {'strict_common':list(SPECS), 'sequence_common':['U0','U1','U4','U6']}
    groups.update({f'U0_vs_{m}':['U0',m] for m in list(SPECS)[1:]})
    groups.update({'IP_increment':['U0','U1'],'M2_increment':['U1','U4'],'Retail_increment':['U4','U6']})
    for evaluation in ['HOLDOUT','DEVELOPMENT','ALL']:
        block = f if evaluation == 'ALL' else f.loc[f.evaluation_group.eq(evaluation)]
        for sample,models in {'maximum_available':list(SPECS),**groups}.items():
            common = common_sample(block,models)
            selected = block if sample == 'maximum_available' else block.merge(common[['origin','target_quarter','horizon']],on=['origin','target_quarter','horizon'],validate='many_to_one')
            selected = selected.loc[selected.model.isin(models) & selected.prediction.notna()]
            for h in ['H1','H2','H3','POOLED']:
                part = selected if h == 'POOLED' else selected.loc[selected.horizon.eq(h)]
                local=[]
                for model in models:
                    g=part.loc[part.model.eq(model)]
                    local.append(dict(sample=sample,evaluation_group=evaluation,horizon=h,model=model,**metrics(g)))
                benchmark=next((x for x in local if x['model']=='U0'),local[0])
                for r in local:
                    r.update(delta_rmse=r['rmse']-benchmark['rmse'],delta_mae=r['mae']-benchmark['mae'])
                rows.extend(local)
            samples.append(dict(sample=sample,evaluation_group=evaluation,models=' + '.join(models),
                n_common=len(common),first_origin=common.origin.min() if len(common) else None,
                last_origin=common.origin.max() if len(common) else None))
    return pd.DataFrame(rows),pd.DataFrame(samples)


def save(out,name,frame):
    frame.to_csv(out/f'phase6i_{name}.csv',index=False,float_format='%.17g')


def run(out=None, baseline_manifest=None):
    out=Path(out or ROOT/'results/phase6i');out.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(out/'phase6i_pipeline.log',mode='w',encoding='utf8')])
    if baseline_manifest:
        audited=json.loads(Path(baseline_manifest).read_text(encoding='utf8'))
        if not audited.get('protected_artifacts_verified') or audited['protected_hashes_before']!=audited['protected_hashes_after']:
            raise ValueError('Cannot reuse an unverified protection baseline')
        before=audited['protected_hashes_after']
        LOG.info('Reusing previously fully verified baseline; every file will be rehashed after this run')
    else:
        before=protection()
    dataset=load_dataset(ROOT)
    expected={'usd_uzs':'usd_uzs_mom_dlog','industrial_production':'ind_prod_yoy_log','m2':'m2_yoy_log','retail_trade':'retail_yoy_log'}
    if any(dataset.clean_field_by_key[k]!=v for k,v in expected.items()):raise ValueError('Registry field changed')
    source=pd.read_csv(ROOT/'results/diagnostics/historical_forecasts.csv',float_precision='round_trip')
    origins=source.loc[source.model.eq('UMIDAS_USD') & source.lag_mode.eq('standard') & source.timing_rule.eq('STRICT') & source.prediction.notna()]
    current=current_inputs(dataset)
    LOG.info('Evaluating %d frozen origins; canonical registry predictor transforms',len(origins))
    allf,coef,repro=evaluate(dataset,origins,current)
    historical=allf.loc[allf.evaluation_group.ne('CURRENT')].copy()
    scores,samples=comparisons(historical)
    common=common_sample(historical,list(SPECS))
    currentf=allf.loc[allf.evaluation_group.eq('CURRENT')].copy()
    u0=float(currentf.loc[currentf.model.eq('U0'),'prediction'].iloc[0])
    latest={key:str(build_information_set(current[0],current[2]['target'],current[2]['horizon'],[expected[key]])[expected[key]].last_valid_index()) for key in KEYS}
    currentf['current_nowcast']=currentf.prediction
    currentf['difference_from_U0']=currentf.prediction-u0
    currentf['latest_usable_month_by_predictor']=currentf.model.map(lambda m:json.dumps({k:latest[k] for k in SPECS[m]},sort_keys=True))
    for key in KEYS:currentf[f'{key}_included']=currentf.model.map(lambda m:key in SPECS[m])
    primary=scores.loc[scores['sample'].eq('strict_common') & scores.evaluation_group.eq('HOLDOUT')]
    pooled=primary.loc[primary.horizon.eq('POOLED')].sort_values(['rmse','mae','model'])
    best=pooled.iloc[0].model
    challenger=pooled.loc[pooled.model.ne('U0')].iloc[0].model
    # Four holdout quarters cannot robustly support selecting 8–14 parameter models.
    classification=('PHASE6I_KEEP_U0' if best=='U0' else
        'PHASE6I_SAMPLE_TOO_SMALL' if common.loc[common.evaluation_group.eq('HOLDOUT'),'target_quarter'].nunique()<8
        else 'PHASE6I_MIXED_RESULTS')
    summary=[]
    for model,keys in SPECS.items():
        p=primary.loc[primary.model.eq(model)].set_index('horizon')
        r=dict(model=model,predictors=' + '.join(keys),n_parameters=2+3*len(keys),
            n_origins=int(p.loc['POOLED','n_origins']),pooled_rmse=p.loc['POOLED','rmse'],
            pooled_mae=p.loc['POOLED','mae'],bias=p.loc['POOLED','bias'],
            current_nowcast=float(currentf.loc[currentf.model.eq(model),'prediction'].iloc[0]))
        for h in ['H1','H2','H3']:
            for metric in ['rmse','mae']:r[f'{h.lower()}_{metric}']=p.loc[h,metric]
        summary.append(r)
    incremental=[]
    for a,b,sample in [('U0','U1','IP_increment'),('U1','U4','M2_increment'),('U4','U6','Retail_increment'),('U0','U2','U0_vs_U2'),('U0','U3','U0_vs_U3')]:
        for h in ['H1','H2','H3','POOLED']:
            p=scores.loc[scores['sample'].eq(sample)&scores.evaluation_group.eq('HOLDOUT')&scores.horizon.eq(h)].set_index('model')
            matched=common_sample(historical.loc[historical.evaluation_group.eq('HOLDOUT')],[a,b])
            if h!='POOLED':matched=matched.loc[matched.horizon.eq(h)]
            gain=(matched.actual-matched[a])**2-(matched.actual-matched[b])**2
            byq=pd.DataFrame({'q':matched.target_quarter,'gain':gain}).groupby('q').gain.sum().sort_values(ascending=False)
            incremental.append(dict(baseline=a,challenger=b,horizon=h,n_origins=len(matched),
                delta_rmse=p.loc[b,'rmse']-p.loc[a,'rmse'],delta_mae=p.loc[b,'mae']-p.loc[a,'mae'],
                largest_quarter_sse_gain=float(byq.iloc[0]) if len(byq) else np.nan,
                top_two_quarter_sse_gain=float(byq.head(2).sum()),total_sse_gain=float(gain.sum()),
                improved_origins=int((gain>0).sum())))
    correlation=dataset.monthly[list(expected.values())].corr(min_periods=12)
    corrrows=[]
    for a in correlation:
        for b in correlation:
            corrrows.append(dict(variable_a=a,variable_b=b,correlation=correlation.loc[a,b],
                n_months=len(dataset.monthly[[a,b]].dropna()) if a!=b else dataset.monthly[a].count()))
    stability=coef.loc[coef.evaluation_group.ne('CURRENT')].groupby(['model','horizon','variable','monthly_position']).coefficient.agg(['count','mean','std','min','max']).reset_index()
    signs=coef.loc[coef.evaluation_group.ne('CURRENT')].groupby(['model','horizon','variable','monthly_position']).sign.agg(lambda s:s.nunique()).reset_index(name='distinct_signs')
    stability=stability.merge(signs)
    outputs={'model_comparison':pd.DataFrame(summary),'horizon_metrics':scores,'common_sample_forecasts':common,
        'current_nowcasts':currentf,'coefficients':coef,'predictor_correlations':pd.DataFrame(corrrows),
        'sample_comparison':samples,'incremental_value':pd.DataFrame(incremental),'all_forecasts':allf,
        'u0_reproduction':repro,'coefficient_stability':stability}
    for name,frame in outputs.items():save(out,name,frame)
    from scripts.phase6i.report import report
    report(out,outputs,classification,challenger,dataset,current,latest)
    after=protection()
    if before!=after:raise ValueError('Protected files changed: '+str([p for p in before if before[p]!=after.get(p)]))
    artifact_hashes={p.name:sha(p) for p in sorted(out.glob('*')) if p.suffix in ['.csv','.html','.md']}
    manifest=dict(classification=classification,production_changed=False,production_nowcast=current[4]['final_forecast'],
        protected_artifacts_verified=True,protected_file_count=len(before),protected_hashes_before=before,
        protected_hashes_after=after,output_sha256=artifact_hashes,
        current_snapshot=current[5],current_origin=str(current[3]),
        specification={m:list(k) for m,k in SPECS.items()},
        registry_fields=expected,lag_days={k:dataset.release_lag_days[k] for k in KEYS},
        scientific_basis='Registry V1.2 canonical transformed monthly master; NOT recovered real IP used by DFM',
        source_code_sha256={p.name:sha(p) for p in sorted((ROOT/'scripts/phase6i').glob('*.py'))},
        historical_vintages='Latest revised predictors with registry lag masks; verified strict GDP release vintages',
        primary_evaluation='STRICT COMMON HOLDOUT; development and combined samples supplementary',
        protection_baseline='Previously fully verified manifest; full after-run rehash' if baseline_manifest else 'Full before/after rehash')
    (out/'phase6i_run_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf8')
    LOG.info('%s; protected %d files unchanged',classification,len(before))
    print(classification)
    for r in summary:print(f"{r['model']} {r['predictors']}: pooled RMSE {r['pooled_rmse']:.6f}")
    print(f'Best common-sample model: {best}')
    for h in ['H1','H2','H3']:print(h+' winner: '+primary.loc[primary.horizon.eq(h)].sort_values('rmse').iloc[0].model)
    print(f"2026Q3 challenger nowcast ({challenger}): {float(currentf.loc[currentf.model.eq(challenger),'prediction'].iloc[0]):.12f}%")
    print(f"Production remains unchanged at {current[4]['final_forecast']}%. Protected artifacts: verified.")
    return manifest


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-manifest',type=Path,help='Reuse an already verified baseline; still fully rehash every protected file after execution')
    run(baseline_manifest=parser.parse_args().baseline_manifest)
