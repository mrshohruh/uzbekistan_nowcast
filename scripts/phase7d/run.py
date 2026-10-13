"""Run: .venv\\Scripts\\python.exe -m scripts.phase7d.run (offline)."""
from pathlib import Path
from dataclasses import replace
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'src'))
from scripts.phase7d.data import read_workbook, INFORMATION_CLASS, release_gate
from scripts.phase7d.models import MODELS, SPECS, estimate
from scripts.phase7d.evaluation import metrics, tables, clustered_gain, prequential_intervals
from uznowcast.models.data import load_dataset, horizon_month_end
from uznowcast.models.benchmarks import ar_forecast
from scripts.operations.prospective.common import safe

LOG=logging.getLogger('phase7d')
OUT=ROOT/'results/phase7d'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protection():
    """Byte checks protect all prior scientific artifacts, not only current forecast."""
    paths=[]
    for folder in ['src','scripts','config','registry','data','metadata','dashboard','results','docs']:
        for directory,dirs,files in os.walk(ROOT/folder):
            dirs[:]=[d for d in dirs if d!='__pycache__' and not d.startswith(('pytest_tmp','tmp','.'))]
            for name in files:
                path=Path(directory)/name;rel=path.relative_to(ROOT).as_posix()
                if path.suffix!='.pyc' and not rel.startswith(('scripts/phase7d/','results/phase7d/')):
                    paths.append((rel,path))
    def digest(item):return item[0],sha(item[1])
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(pool.map(digest,paths))


def verify(hashes):
    def changed(item):
        name,digest=item
        return name if not (ROOT/name).is_file() or sha(ROOT/name)!=digest else None
    with ThreadPoolExecutor(max_workers=8) as pool:
        errors=[p for p in pool.map(changed,hashes.items()) if p]
    if errors:raise ValueError('Protected artifacts changed: '+str(errors))


def save(name,frame):
    frame.to_csv(OUT/f'phase7d_{name}.csv',index=False,float_format='%.17g')


def write_json(name,value):
    (OUT/f'phase7d_{name}.json').write_text(json.dumps(safe(value),indent=2,allow_nan=False)+'\n',encoding='utf8')


def locate(path=None):
    if path:return Path(path).resolve()
    candidates=[p for p in (ROOT/'data').rglob('uzbekistan_macro_monthly_quarterly*.xlsx') if 'phase7d' not in p.parts]
    preferred=[p for p in candidates if p.name=='uzbekistan_macro_monthly_quarterly(2).xlsx']
    if preferred:return preferred[0]
    if len(candidates)!=1:raise ValueError('Specify --workbook; candidates: '+str(candidates))
    return candidates[0]


def information_gdp(events,target,origin,start='2019Q1'):
    from uznowcast.gdp_vintages import available_gdp_vintage_as_of, assert_boundary
    available=available_gdp_vintage_as_of(events,pd.Timestamp(origin),target=target,timing_rule='STRICT')
    assert_boundary(available,target)
    gdp=available.frame.value.loc[available.frame.index>=start]
    return available,gdp


def original_models(dataset,panel,available,target,horizon,origin):
    """Rerun unchanged frozen model kernels; final GDP scoring is separate."""
    from scripts.production.models import dfm,umidas
    gated=replace(dataset,gdp=pd.DataFrame({'quarter':available.frame.index,dataset.target_field:available.frame.value.to_numpy()}))
    predictions={};failures={}
    for name,fn in [('M0',lambda:dfm(panel,gated,available,target,horizon,origin)[0]),
                    ('U0',lambda:umidas(gated,available,target,horizon,origin)[0])]:
        try:predictions[name]=fn()
        except ValueError as error:predictions[name]=np.nan;failures[name]=str(error)
    predictions['COMBO_50_50']=.5*(predictions['M0']+predictions['U0'])
    if pd.isna(predictions['COMBO_50_50']):failures['COMBO_50_50']='COMPONENT_UNAVAILABLE'
    return predictions,failures


def build(args):
    OUT.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(OUT/'pipeline.log',mode='w',encoding='utf8')])
    LOG.info('Capturing immutable production and scientific inputs')
    baseline=OUT/'phase7d_protection_baseline.json'
    before=json.loads(baseline.read_text(encoding='utf8')) if args.resume and baseline.is_file() else protection()
    write_json('protection_baseline',before)
    workbook=locate(args.workbook);digest=sha(workbook)
    archive=OUT/'input'/f'{digest}.xlsx';archive.parent.mkdir(exist_ok=True)
    if not archive.exists():
        with archive.open('xb') as handle:handle.write(workbook.read_bytes())
    if sha(archive)!=digest:raise ValueError('Raw workbook archive checksum mismatch')
    inputs=read_workbook(archive,ROOT/'data/master/gdp_quarterly.parquet')
    inputs.inventory['workbook_sha256']=digest
    save('predictor_inventory',inputs.inventory);save('transformations',inputs.transformations)
    write_json('data_audit',dict(inputs.audit,source_workbook=str(workbook),raw_archive=str(archive),source_sha256=digest))
    save('raw_monthly',inputs.monthly_raw.reset_index(names='reference_period'))
    save('raw_quarterly',inputs.quarterly_raw.reset_index(names='reference_period'))
    save('monthly_inputs',inputs.monthly.reset_index(names='reference_period'))
    save('quarterly_inputs',inputs.quarterly.reset_index(names='reference_period'))
    save('missingness',inputs.inventory[['original_label','frequency','group','first_observation','last_observation','raw_observations','usable_observations','missing_raw','missing_transformed','late_start','status']])
    dataset=load_dataset(ROOT)
    panel=pd.read_csv(ROOT/'data/current/historical_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip')
    events=pd.read_csv(ROOT/'data/current/gdp_vintages.csv')
    source=pd.read_csv(ROOT/'results/diagnostics/historical_forecasts.csv',float_precision='round_trip')
    existing=source.loc[source.lag_mode.eq('standard')&source.timing_rule.eq('STRICT')]
    origins=existing.loc[existing.model.eq('UMIDAS_USD')&existing.prediction.notna(),['target_quarter','horizon','forecast_origin_date']].copy()
    origins['origin']=pd.to_datetime(origins.forecast_origin_date,format='mixed').dt.strftime('%Y-%m-%d')
    origins=origins.drop(columns='forecast_origin_date').sort_values(['target_quarter','horizon'])
    origins=origins.loc[origins.target_quarter.isin(inputs.gdp.index.astype(str))]
    if origins.duplicated(['target_quarter','horizon']).any():raise ValueError('Duplicate legacy origins')
    for r in origins.itertuples():
        if pd.Timestamp(r.origin)!=horizon_month_end(r.target_quarter,r.horizon):raise ValueError('Legacy horizon mismatch')
    forecasts=[];signals=[];loads=[];availability=[];diagnostics=[];reproduction=[];cache={}
    failures=[];robust_forecasts=[]
    robustness_variants=[('WINSOR_TRAINING_1_99',dict(winsor=True)),
        ('EXCLUDE_SERVICES',dict(exclude=('services',))),('EXCLUDE_PANDEMIC_TRAINING',dict(exclude_pandemic=True)),
        ('LAG_PLUS_15D',dict(extra_days=15))]
    robustness_variants += [('ABLATION_'+g.upper(),dict(exclude=(g,))) for g in sorted(inputs.inventory.group.unique()) if g!='services']
    # Every variant uses all historical origins, not selected favorable quarters.
    for row in origins.to_dict('records'):
        target,horizon,origin=row['target_quarter'],row['horizon'],pd.Timestamp(row['origin'])
        LOG.info('Starting origin %s %s',target,horizon)
        available,gdp=information_gdp(events,target,origin)
        meta=dict(origin=row['origin'],target_quarter=target,horizon=horizon,
            actual=float(inputs.gdp.loc[pd.Period(target,'Q')]),information_class=INFORMATION_CLASS,
            actual_definition='WORKBOOK_LATEST_REVISED_CUMULATIVE_REAL_YTD_YOY',
            evaluation_group='HOLDOUT' if target>='2025Q3' else 'DEVELOPMENT')
        original,errors=original_models(dataset,panel,available,target,horizon,origin)
        for model,prediction in original.items():
            refname={'M0':'DFM-4_R1_P2__BRIDGE_B_mean','U0':'UMIDAS_USD','COMBO_50_50':'COMBO_50_50'}[model]
            archived=existing.loc[existing.model.eq(refname)&existing.target_quarter.eq(target)&existing.horizon.eq(horizon)]
            reproduction.append(dict(model=model,origin=row['origin'],target_quarter=target,horizon=horizon,
                recalculated=prediction,archived_prediction=archived.prediction.iloc[0] if len(archived) else np.nan,
                difference=prediction-archived.prediction.iloc[0] if len(archived) else np.nan,
                legacy_actual=archived.actual.iloc[0] if len(archived) else np.nan,matched_actual=meta['actual']))
            forecasts.append(dict(meta,model=model,prediction=prediction,failure=errors.get(model),n_declared=8 if model=='M0' else 1 if model=='U0' else 9))
        for p,model in [(1,'AR1'),(2,'AR2')]:
            # Same origin's released GDP, including any missing latest quarter.
            sequence=available.frame.value.copy()
            last=pd.Period(sequence.index[-1],'Q');qtarget=pd.Period(target,'Q')
            prediction=None
            for _ in range(qtarget.ordinal-last.ordinal):
                prediction,_=ar_forecast(sequence,p)
                last+=1;sequence.loc[str(last)]=prediction
            forecasts.append(dict(meta,model=model,prediction=prediction,n_declared=0,failure=None))
        forecasts.append(dict(meta,model='HISTORICAL_MEAN',prediction=float(gdp.mean()),n_declared=0,failure=None))
        for model in SPECS:
            try:
                prediction,factor,loading,z,av,diag=estimate(inputs,model,target,horizon,origin,gdp,cache=cache)
                for key,value in meta.items():av[key]=value;loading[key]=value
                av['model']=model;loading['model']=model
                availability.extend(av.to_dict('records'));loads.extend(loading.to_dict('records'))
                diagnostics.append(dict(meta,model=model,**diag))
                for date,values in factor.iterrows():
                    for f,value in values.items():signals.append(dict(meta,model=model,date=str(date.date()),factor=f,value=float(value),units='training-standardized one-sided latent factor'))
                forecasts.append(dict(meta,model=model,prediction=prediction,failure=None,**diag))
            except (ValueError,np.linalg.LinAlgError) as error:
                failures.append(dict(meta,model=model,failure=str(error)))
                forecasts.append(dict(meta,model=model,prediction=np.nan,failure=str(error)))
        for variant,kw in robustness_variants:
            for model in ['DFM_ALL_1F','DFM_ALL_GROUPED']:
                try:
                    prediction,_,_,_,_,diag=estimate(inputs,model,target,horizon,origin,gdp,cache=cache,**kw)
                    robust_forecasts.append(dict(meta,model=model,variant=variant,prediction=prediction,failure=None,n_declared=diag['n_declared']))
                except (ValueError,np.linalg.LinAlgError) as error:
                    robust_forecasts.append(dict(meta,model=model,variant=variant,prediction=np.nan,failure=str(error)))
        LOG.info('Completed origin %s %s; cached fits %d',target,horizon,len(cache))
        save('forecasts',pd.DataFrame(forecasts));save('robustness_forecasts',pd.DataFrame(robust_forecasts))
    hist=prequential_intervals(pd.DataFrame(forecasts))
    model_metrics,horizon_metrics,common=tables(hist,MODELS)
    # Formal selection only on development; holdout excluded from selection.
    dev=model_metrics.loc[model_metrics['sample'].eq('MATCHED_DEVELOPMENT')&model_metrics.model.isin(SPECS)&model_metrics.rmse.notna()].sort_values(['rmse','model'])
    if dev.empty:raise ValueError('No matched development forecasts: cannot select an experimental DFM')
    selected=dev.iloc[0].model
    robust=[]
    for model in SPECS:
        robust.append(clustered_gain(common,model))
        robust.append(clustered_gain(common.loc[common.target_quarter.ge('2025Q3')],model,subset='HOLDOUT'))
    for (model,variant),b in pd.DataFrame(robust_forecasts).groupby(['model','variant']):
        base=common.loc[common.model.eq(model)]
        paired=b.merge(base[['origin','target_quarter','horizon','prediction']],on=['origin','target_quarter','horizon'],suffixes=('','_base')).dropna(subset=['prediction','prediction_base'])
        robust.append(dict(model=model,variant=variant,subset='IDENTICAL_VARIANT_ORIGINS',**metrics(paired),
            baseline_rmse=float(np.sqrt(((paired.actual-paired.prediction_base)**2).mean())),
            failed_origins=int(b.prediction.isna().sum()),min_predictor_count=float(b.n_declared.min()) if 'n_declared' in b else np.nan))
    for model,b in common.groupby('model'):
        qs=sorted(b.target_quarter.unique());half=len(qs)//2
        for name,periods in [('EARLY',qs[:half]),('RECENT',qs[half:])]+[('LEAVE_OUT_'+q,[x for x in qs if x!=q]) for q in qs]:
            robust.append(dict(model=model,variant='ERROR_STABILITY_'+name,subset=name,**metrics(b.loc[b.target_quarter.isin(periods)])))
    save('robustness',pd.DataFrame(robust))
    save('model_metrics',model_metrics);save('horizon_metrics',horizon_metrics);save('forecasts',hist)
    save('legacy_reproduction',pd.DataFrame(reproduction));save('failures',pd.DataFrame(failures,columns=[*meta,'model','failure']))
    save('estimation_diagnostics',pd.DataFrame(diagnostics))
    # Current cutoff agrees in calendar date with production, but the workbook
    # has no retrieval or actual release dates; equality of vintage is unverified.
    frozen=json.loads((ROOT/'results/current/current_nowcast.json').read_text())
    if frozen['final_forecast']!=8.180901340616275:raise ValueError('Frozen production forecast unexpectedly different')
    cutoff=pd.Timestamp(args.cutoff or frozen['as_of_date'])
    target='2026Q3';available,gdp=information_gdp(events,target,cutoff)
    current=[];contributions=[]
    for model in SPECS:
        prediction,factor,loading,z,av,diag=estimate(inputs,model,target,'H3',cutoff,gdp,cache=cache)
        current.append(dict(model=model,prediction=prediction,**diag))
        for key,value in dict(model=model,origin=str(cutoff.date()),target_quarter=target,horizon='H3',evaluation_group='CURRENT').items():
            loading[key]=value;av[key]=value
        loads.extend(loading.to_dict('records'));availability.extend(av.to_dict('records'))
        for date,values in factor.iterrows():
            for f,value in values.items():signals.append(dict(model=model,origin=str(cutoff.date()),target_quarter=target,horizon='H3',date=str(date.date()),factor=f,value=float(value),evaluation_group='CURRENT',units='training-standardized one-sided latent factor'))
        for item in loading.loc[loading.factor.ne('QUARTERLY_BRIDGE')].to_dict('records'):
            for date,value in z[item['original_label']].items():
                contributions.append(dict(model=model,date=str(date.date()),original_label=item['original_label'],group=item['group'],factor=item['factor'],
                    standardized_input=value,loading=item['loading'],loading_signal=value*item['loading'],
                    units='standardized measurement reconstruction signal; not additive GDP pp'))
    latest=next(v for v in current if v['model']==selected)
    hold=model_metrics.loc[model_metrics['sample'].eq('MATCHED_HOLDOUT')&model_metrics.model.eq(selected)].iloc[0]
    historical_rmse=float(hold.rmse)
    width=1.96*historical_rmse if np.isfinite(historical_rmse) else None
    missing_september=inputs.monthly_raw.loc[pd.Period('2026-09','M')].index[inputs.monthly_raw.loc[pd.Period('2026-09','M')].isna()].tolist()
    visible=release_gate(inputs.monthly,inputs.inventory,cutoff)
    gated_september=visible.loc[pd.Period('2026-09','M')].index[visible.loc[pd.Period('2026-09','M')].isna()].tolist()
    nowcast=dict(target_quarter=target,cutoff=str(cutoff.date()),horizon='H3',stage='POST_H3_WORKBOOK_RESEARCH',
        model=selected,factor_count=SPECS[selected][0],prediction=latest['prediction'],all_models=current,
        selection='Lowest matched development RMSE; final holdout not used to choose model/factor count',
        information_class=INFORMATION_CLASS,release_availability='Assumed lags only; workbook vintage/retrieval at cutoff unverified',
        cutoff_matches_production_calendar_date=str(cutoff.date())==frozen['as_of_date'],
        legacy_information_set_reproduced=False,legacy_difference='Workbook has no vintage/retrieval evidence and omits legacy FX/POS predictors; exact frozen information set cannot be reproduced.',
        missing_september_source_count=len(missing_september),missing_september_source_predictors=missing_september,
        missing_september_after_release_and_transform_count=len(gated_september),missing_september_after_release_and_transform=gated_september,
        historical_error_reference_lower=latest['prediction']-width if width is not None else None,
        historical_error_reference_upper=latest['prediction']+width if width is not None else None,
        uncertainty='Indicative +/-1.96 matched holdout RMSE; NOT a calibrated 95% prediction interval; four dependent-quarter clusters.',
        decision='KEEP_PRODUCTION',production_model='COMBO_50_50',production_forecast=frozen['final_forecast'],
        promotion_allowed=False,workbook_sha256=digest)
    write_json('current_nowcast',nowcast)
    save('factor_signals',pd.DataFrame(signals));save('factor_loadings',pd.DataFrame(loads))
    save('signal_contributions',pd.DataFrame(contributions));save('origin_availability',pd.DataFrame(availability))
    group_energy=pd.DataFrame(loads).loc[lambda f:f.evaluation_group.eq('CURRENT')&f.factor.ne('QUARTERLY_BRIDGE')].groupby(['model','factor','group']).loading_energy_share.sum().reset_index()
    group_energy['dominance_flag']=group_energy.loading_energy_share>.5
    save('factor_group_dominance',group_energy)
    interval_summary=[]
    for model,b in hist.groupby('model'):
        measured=b.dropna(subset=['interval_covered'])
        interval_summary.append(dict(model=model,n_interval_forecasts=len(measured),n_quarters=int(measured.target_quarter.nunique()),empirical_coverage=float(measured.interval_covered.mean()),interpretation='Illustrative prequential past-error bands; finite sample, overlap and revisions prevent calibrated nominal claims'))
    save('interval_diagnostics',pd.DataFrame(interval_summary))
    frozen_metrics=pd.read_csv(ROOT/'results/current/model_comparison.csv')
    save('frozen_production_metrics',frozen_metrics)
    manifest=dict(source_workbook=str(workbook),workbook_sha256=digest,predictor_count=96,
        production_forecast=frozen['final_forecast'],selected_model=selected,selected_factor_count=SPECS[selected][0],
        protected_file_count=len(before),protected_artifacts_verified=False,
        historical_origin_count=len(origins),matched_forecast_count=int(model_metrics.iloc[0].n_forecasts),
        information_class=INFORMATION_CLASS,run_timestamp_utc=datetime.now(timezone.utc).isoformat(),decision='KEEP_PRODUCTION')
    from scripts.phase7d.report import report
    LOG.info('Verifying %d protected files',len(before));verify(before)
    manifest['protected_artifacts_verified']=True
    report(inputs,model_metrics,horizon_metrics,hist,pd.DataFrame(signals),pd.DataFrame(loads),pd.DataFrame(contributions),pd.DataFrame(availability),pd.DataFrame(robust),nowcast,manifest,frozen_metrics,OUT)
    manifest['output_sha256']={p.name:sha(p) for p in OUT.glob('phase7d_*') if p.is_file() and p.suffix!='.log' and p.name!='phase7d_run_manifest.json'}
    write_json('run_manifest',manifest)
    LOG.info('Finished; experimental %s = %.10f; production kept',selected,latest['prediction'])
    print(model_metrics.loc[model_metrics['sample'].eq('MATCHED_ALL'),['model','rmse','bias','mae','r2','r2_os_ar1','n_forecasts','n_quarters']].to_string(index=False))
    print(json.dumps(safe(dict(selected_model=selected,current_nowcast=latest['prediction'],decision='KEEP_PRODUCTION')),indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbook');parser.add_argument('--cutoff')
    parser.add_argument('--resume',action='store_true',help='Reuse an existing protection baseline after an interrupted run; verify all its hashes at completion')
    args=parser.parse_args();build(args)


if __name__=='__main__':main()
