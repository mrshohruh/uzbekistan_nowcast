"""Offline Phase 7E execution. Never writes outside its own namespace."""
from pathlib import Path
import argparse
import json
import logging
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'src'))
from scripts.phase7d.data import read_workbook, INFORMATION_CLASS, release_gate
from scripts.phase7d.run import information_gdp, original_models
from scripts.phase7d.evaluation import tables, metrics, matched, clustered_gain, KEYS
from scripts.phase7e.grouping import inventory, BLOCKS, RATIONALE
from scripts.phase7e.models import estimate, block_factor, SPECS
from scripts.phase7e.protection import snapshot, verify, sha
from scripts.operations.prospective.common import safe
from uznowcast.models.data import horizon_month_end, load_dataset

OUT=ROOT/'results/phase7e'
LOG=logging.getLogger('phase7e')
LEGACY=['DFM_ALL_GROUPED','M0','U0','COMBO_50_50','AR1','AR2']
ALL_MODELS=[*SPECS,*LEGACY]


def write_json(name,value):
    (OUT/f'phase7e_{name}.json').write_text(json.dumps(safe(value),indent=2,allow_nan=False)+'\n',encoding='utf8')


def save(name,frame):
    frame.to_csv(OUT/f'phase7e_{name}.csv',index=False,float_format='%.17g')


def add_meta(frame,meta):
    return frame.assign(**meta).to_dict('records')


def run(numerical_replay=False):
    OUT.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(OUT/'pipeline.log',mode='w',encoding='utf8')])
    before=json.loads((OUT/'phase7e_protection_baseline.json').read_text()) if numerical_replay else snapshot()
    write_json('protection_baseline',before)
    LOG.info('Protected prior files: %d',len(before))
    manifest=json.loads((ROOT/'results/phase7d/phase7d_run_manifest.json').read_text())
    digest=manifest['workbook_sha256']
    workbook=ROOT/'results/phase7d/input'/f'{digest}.xlsx'
    if sha(workbook)!=digest: raise ValueError('Phase 7D input archive checksum differs')
    inputs=read_workbook(workbook,ROOT/'data/master/gdp_quarterly.parquet')
    frozen=json.loads((ROOT/'results/current/current_nowcast.json').read_text())
    if frozen['final_forecast']!=8.180901340616275 or frozen['dfm_weight']!=.5 or frozen['umidas_weight']!=.5:
        raise ValueError('Production scientific result differs from required baseline')
    cutoff=frozen['as_of_date'];grouping=inventory(inputs,cutoff)
    save('variable_grouping',grouping);save('transformations',inputs.transformations)
    grouping.to_csv(OUT/'variable_grouping.csv',index=False,float_format='%.17g')
    write_json('data_audit',dict(inputs.audit,workbook_sha256=digest,source_archive=str(workbook)))
    events=pd.read_csv(ROOT/'data/current/gdp_vintages.csv')
    legacy=pd.read_csv(ROOT/'results/phase7d/phase7d_forecasts.csv',float_precision='round_trip')
    legacy=legacy.loc[legacy.model.isin(LEGACY)].copy()
    legacy['origin']=pd.to_datetime(legacy.origin).dt.strftime('%Y-%m-%d')
    legacy['legacy_procedure']='READ_ONLY_PHASE7D_ARCHIVE_SAME_INPUT_HASH_SAME_ORIGIN'
    # Re-run all six legacy procedures at one representative matching origin.
    from scripts.phase7d.models import estimate as old_estimate
    from uznowcast.models.benchmarks import ar_forecast
    dataset=load_dataset(ROOT)
    panel=pd.read_csv(ROOT/'data/current/historical_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip')
    check=legacy.loc[legacy.target_quarter.eq('2026Q2') & legacy.horizon.eq('H3')]
    origin=check.origin.iloc[0];av,gdp=information_gdp(events,'2026Q2',origin)
    old,errors=original_models(dataset,panel,av,'2026Q2','H3',pd.Timestamp(origin))
    old['DFM_ALL_GROUPED']=old_estimate(inputs,'DFM_ALL_GROUPED','2026Q2','H3',origin,gdp)[0]
    for p,m in [(1,'AR1'),(2,'AR2')]: old[m]=ar_forecast(av.frame.value,p)[0]
    reproduction=[]
    for r in check.itertuples():
        delta=old[r.model]-r.prediction
        if abs(delta)>1e-10: raise ValueError(f'Legacy kernel reproduction failed: {r.model} {delta}')
        reproduction.append(dict(model=r.model,target_quarter=r.target_quarter,horizon=r.horizon,origin=origin,archived=r.prediction,recomputed=old[r.model],difference=delta))
    save('legacy_reproduction',pd.DataFrame(reproduction))
    legacy['actual']=[float(inputs.gdp.loc[pd.Period(q,'Q')]) for q in legacy.target_quarter]
    forecasts=legacy.to_dict('records');factors=[];loads=[];availability=[];diagnostics=[];decomp=[];bridges=[];block_failures=[];hierarchy=[]
    cache={};robust=[];origin_history=[]
    original_origins=set(tuple(r) for r in legacy[KEYS].drop_duplicates().to_numpy())
    for q in pd.period_range(inputs.gdp.index.min()+1,'2026Q2',freq='Q'):
        for h in ['H1','H2','H3']:
            origin=horizon_month_end(str(q),h).strftime('%Y-%m-%d')
            origin_history.append(dict(target_quarter=str(q),horizon=h,origin=origin,
                legacy_schedule=(origin,str(q),h) in original_origins))
    origin_history.append(dict(target_quarter='2026Q3',horizon='H3',origin=cutoff,legacy_schedule=True))
    for row in origin_history:
        target,h,origin=row['target_quarter'],row['horizon'],row['origin']
        current=target=='2026Q3'
        _,gdp=information_gdp(events,target,origin)
        meta=dict(origin=origin,target_quarter=target,horizon=h,
            evaluation_group='CURRENT' if current else 'HOLDOUT' if target>='2025Q3' else 'DEVELOPMENT',
            actual=np.nan if current else float(inputs.gdp.loc[pd.Period(target,'Q')]),
            actual_definition='WORKBOOK_LATEST_REVISED_CUMULATIVE_REAL_YTD_YOY',information_class=INFORMATION_CLASS,
            legacy_schedule=row['legacy_schedule'])
        LOG.info('Origin %s %s %s',target,h,origin)
        # Inventory all variables at every origin, including failed models.
        for frame in [inputs.monthly,inputs.quarterly]:
            visible=release_gate(frame,inputs.inventory,origin)
            train_end=pd.Period(target,'Q').start_time
            for c in frame:
                observed=visible[c].dropna()
                availability.append(dict(meta,model='INVENTORY',original_label=c,frequency='M' if frame is inputs.monthly else 'Q',
                    economic_group=grouping.set_index('original_label').at[c,'economic_group'],
                    status='RELEASE_GATE_VISIBLE' if len(observed) else 'NO_RELEASED_HISTORY',
                    latest_available_period=str(observed.index[-1]) if len(observed) else None,
                    available_history=int(visible.loc[visible.index.start_time<train_end,c].count()),
                    actual_source_release_date=None,availability_basis='ASSUMED_LAG_NOT_OBSERVED_RELEASE',
                    requested_period=target))
        # Report each block's technical availability even when a model fails earlier.
        for core in [False,True]:
            for block in BLOCKS:
                key=(target,origin,block,core,0,False)
                try:
                    part=block_factor(inputs,grouping,block,target,origin,core)
                    cache[key]=part
                    diagnostics.append(dict(meta,model='CORE_BLOCKS' if core else 'FULL_BLOCKS',**part.diagnostics))
                except (ValueError,np.linalg.LinAlgError) as exc:
                    cache[key]=str(exc)
                    block_failures.append(dict(meta,model='CORE_BLOCKS' if core else 'FULL_BLOCKS',economic_group=block,failure=str(exc)))
        for model in SPECS:
            try:
                result=estimate(inputs,grouping,model,target,h,origin,gdp,events,cache)
                forecasts.append(dict(meta,model=model,prediction=result.prediction,failure=None,
                    n_factors=len(result.factors.columns),n_declared=int(result.diagnostics.n_declared.sum())+(5 if model=='E4' else 0),
                    n_gdp_training=result.bridge['n_gdp_training']))
                availability.extend(add_meta(result.availability,dict(meta,model=model)))
                loads.extend(add_meta(result.loadings,dict(meta,model=model)))
                for date,values in result.factors.iterrows():
                    for f,value in values.items():
                        factors.append(dict(meta,model=model,date=str(date.date()),factor=f,value=value,
                            units='training-standardized one-sided latent factor',is_target_quarter=date.to_period('Q')==pd.Period(target,'Q')))
                decomp.extend(add_meta(result.contributions,dict(meta,model=model,prediction=result.prediction)))
                bridges.append(dict(meta,model=model,**result.bridge))
                hierarchy.extend([dict(meta,model=model,**x) for x in result.bridge['hierarchical_projection']])
            except (ValueError,np.linalg.LinAlgError) as exc:
                forecasts.append(dict(meta,model=model,prediction=np.nan,failure=str(exc)))
        # Fixed lag and outlier sensitivities, all baseline origins >=2025Q1.
        if target>='2025Q1':
            for variant,options in [('LAG_PLUS_15D',dict(extra_days=15)),('TRAINING_WINSOR_1_99',dict(winsor=True))]:
                try:
                    r=estimate(inputs,grouping,'E2',target,h,origin,gdp,events,cache,**options)
                    robust.append(dict(meta,model='E2',variant=variant,prediction=r.prediction,failure=None))
                except (ValueError,np.linalg.LinAlgError) as exc:
                    robust.append(dict(meta,model='E2',variant=variant,prediction=np.nan,failure=str(exc)))
        # Checkpoint permits a visible failure trail on interruption.
        save('forecasts',pd.DataFrame(forecasts))
    hist=pd.DataFrame(forecasts)
    evaluated=hist.loc[hist.evaluation_group.ne('CURRENT')]
    scores,horizon_scores,common=tables(evaluated,ALL_MODELS)
    # Each contestant's own-success sample is explicitly separated from main matched comparison.
    extension=[]
    for model,part in evaluated.groupby('model'):
        for sample,subset in [('OWN_SUCCESS_ALL',part),('OWN_SUCCESS_DEVELOPMENT',part.loc[part.target_quarter<'2025Q3']),('OWN_SUCCESS_HOLDOUT',part.loc[part.target_quarter>='2025Q3'])]:
            extension.append(dict(model=model,sample=sample,**metrics(subset,evaluated.loc[evaluated.model.eq('AR1')])) )
    save('extended_metrics',pd.DataFrame(extension));save('model_comparison',scores);save('horizon_metrics',horizon_scores)
    save('factor_timeseries',pd.DataFrame(factors));save('factor_loadings',pd.DataFrame(loads))
    save('origin_availability',pd.DataFrame(availability));save('gdp_contributions',pd.DataFrame(decomp))
    save('estimation_diagnostics',pd.DataFrame(diagnostics));save('block_failures',pd.DataFrame(block_failures))
    save('bridge_diagnostics',pd.DataFrame(bridges));save('hierarchical_projection',pd.DataFrame(hierarchy))
    save('robustness_forecasts',pd.DataFrame(robust))
    uncertainty=[]
    for m in SPECS:
        for name,part in [('ALL',common),('HOLDOUT',common.loc[common.target_quarter>='2025Q3'])]:
            uncertainty.append(clustered_gain(part,m,subset=name))
    for variant,part in pd.DataFrame(robust).query("evaluation_group != 'CURRENT'").groupby('variant'):
        base=evaluated.loc[evaluated.model.eq('E2')]
        paired=part.merge(base[KEYS+['prediction']],on=KEYS,suffixes=('','_base')).dropna(subset=['prediction','prediction_base'])
        uncertainty.append(dict(model='E2',variant=variant,subset='PAIRED_SUCCESSFUL_ORIGINS',**metrics(paired),
            n_failed=int(part.prediction.isna().sum()),baseline_rmse=float(np.sqrt(((paired.actual-paired.prediction_base)**2).mean())),
            mean_absolute_forecast_change=float((paired.prediction-paired.prediction_base).abs().mean())))
    for model,part in common.groupby('model'):
        pivot=part.pivot(index='target_quarter',columns='horizon',values='prediction')
        changes=pivot.diff(axis=1).iloc[:,1:]
        uncertainty.append(dict(model=model,variant='HORIZON_FORECAST_REVISION_STABILITY',subset='MATCHED_ALL',
            n_quarters=len(pivot),mean_absolute_forecast_change=float(changes.abs().stack().mean()),
            max_absolute_forecast_change=float(changes.abs().stack().max())))
    save('robustness',pd.DataFrame(uncertainty))
    earliest=[]
    dfdiag=pd.DataFrame(diagnostics)
    for block in BLOCKS:
        d=dfdiag.loc[dfdiag.model.eq('FULL_BLOCKS') & dfdiag.economic_group.eq(block)]
        earliest.append(dict(kind='BLOCK',name=block,earliest_technical_origin=d.origin.min() if len(d) else None,
            reason='12 co-observed months, >=two indicators each with >=12 released training observations'))
    for model in SPECS:
        d=evaluated.loc[evaluated.model.eq(model)&evaluated.prediction.notna()]
        earliest.append(dict(kind='GDP_BRIDGE',name=model,earliest_technical_origin=d.origin.min() if len(d) else None,
            earliest_target=d.target_quarter.min() if len(d) else None,reason='All required blocks identifiable, four real quarterly factor signals per block, 12 released GDP training rows'))
    save('earliest_availability',pd.DataFrame(earliest))
    current=hist.loc[hist.evaluation_group.eq('CURRENT')]
    nowcast=dict(target_quarter='2026Q3',cutoff=cutoff,horizon='H3',models=current.to_dict('records'),
        production_model='COMBO_50_50',production_forecast=frozen['final_forecast'],
        economically_preferred_research_model='E2_CONDITIONAL_ON_PRICE_FACTOR_COHERENCE',
        operational_production_model='COMBO_50_50',promotion_allowed=False,
        selection_rule='E2 predeclared primary full-coverage economic research candidate; no holdout-driven selection',
        information_class=INFORMATION_CLASS,legacy_information_set_reproduced=False,
        caveat='Workbook release dates and historical predictor vintages are unverified; cutoff matches production calendar only.')
    write_json('current_nowcast',nowcast)
    preserved=len(before) if numerical_replay else verify(before)
    write_json('run_manifest',dict(protected_file_count=preserved,protected_artifacts_verified=not numerical_replay,
        workbook_sha256=digest,monthly_predictors=91,quarterly_predictors=5,
        origin_count=len(origin_history),production_forecast=frozen['final_forecast'],run_timestamp_utc=datetime.now(timezone.utc).isoformat(),
        code_sha256={p.name:sha(p) for p in (ROOT/'scripts/phase7e').glob('*') if p.is_file()},
        artifact_sha256={p.name:sha(p) for p in OUT.glob('*.csv')},decision='KEEP_PRODUCTION'))
    # Use the same round-trip artifact renderer for builds and reporting replay.
    # This avoids memory-versus-CSV dtype differences in embedded JSON.
    from scripts.phase7e.refresh import refresh
    refresh()
    run_manifest=json.loads((OUT/'phase7e_run_manifest.json').read_text())
    run_manifest['artifact_sha256']={p.name:sha(p) for p in OUT.glob('*.csv')}
    run_manifest['dashboard_sha256']=sha(OUT/'phase7e_economic_dfm_dashboard.html')
    write_json('run_manifest',run_manifest)
    if not numerical_replay: verify(before)
    write_json('validation',dict(production_preservation=not numerical_replay,protected_file_count=preserved,
        grouping_monthly_count=91,grouping_quarterly_count=5,monthly_groups=grouping.loc[grouping.frequency.eq('M')].economic_group.value_counts().to_dict(),
        exact_decomposition_max_error=float(pd.DataFrame(bridges).decomposition_error.abs().max()),
        numerical_nonconverged_count=int((~dfdiag.pca_converged).sum()),
        tests_status='PENDING_EXECUTION',browser_status='PENDING_EXECUTION'))
    LOG.info('Completed research, preserved %d scientific files',preserved)
    print(current[['model','prediction','failure']].to_string(index=False))
    print(scores.loc[scores['sample'].eq('MATCHED_HOLDOUT'),['model','rmse','mae','bias','n_quarters']].to_string(index=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--numerical-replay',action='store_true',help='Internal validation replay: final protection verification is performed by the owning validate command')
    args=parser.parse_args()
    run(args.numerical_replay)
