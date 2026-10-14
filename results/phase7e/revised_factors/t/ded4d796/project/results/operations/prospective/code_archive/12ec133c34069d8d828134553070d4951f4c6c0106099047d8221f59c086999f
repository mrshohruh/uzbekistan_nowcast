"""Research-only GDP vintage re-evaluation with immutable monthly/model kernels."""
from dataclasses import replace
from datetime import datetime,timezone
import json
import hashlib
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from evidence import reconstruct,ROOT,OUT
from vintages import available_gdp_vintage_as_of,assert_boundary
from factors import frozen_module
sys.path.insert(0,str(ROOT/'src'))
from uznowcast.models.data import load_dataset,horizon_month_end
from uznowcast.models.benchmarks import ar_forecast
from uznowcast.models.midas import MidasSpec,midas_forecast

KEYS=['target_quarter','horizon','lag_mode','timing_rule']
MODELS=['AR1','AR2','UMIDAS_USD','PRODUCTION_ENSEMBLE','DFM_A','DFM_B','COMBO_A','COMBO_B']
RULES=['STRICT','PERMISSIVE_END_OF_DAY']
EVALS=['DEVELOPMENT_PSEUDO_OOS','HISTORICAL_POST_DEVELOPMENT_TEST','POOLED_RESEARCH_ONLY']
TARGETS=['FIRST_RELEASE','LATEST_REVISED']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def protect():
    before=json.loads((OUT/'phase6b2_protected_before.json').read_text())
    changed=[p for p,h in before.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    if changed:
        raise RuntimeError('Protected artifact modification: '+str(changed))
    return len(before)

def write(name,frame):
    frame.to_csv(OUT/f'phase6b2_{name}.csv',index=False,float_format='%.17g')
    return frame

def benchmarks(dataset,available,target,horizon,mode,*,diagnostic=False):
    if not diagnostic:
        assert_boundary(available,target)
    gd=available.frame.value
    prior=str(pd.Period(target,freq='Q')-1)
    if prior not in gd.index:
        return {m:(np.nan,'PRIOR_QUARTER_GDP_NOT_AVAILABLE') for m in MODELS[:4]}
    sequence=pd.period_range(gd.index[0],gd.index[-1],freq='Q').astype(str)
    if not gd.index.equals(pd.Index(sequence,name=gd.index.name)):
        return {m:(np.nan,'NONCONSECUTIVE_DOCUMENTED_GDP') for m in MODELS[:4]}
    result={}
    for p,name in [(1,'AR1'),(2,'AR2')]:
        prediction,diag=ar_forecast(gd,p)
        result[name]=(prediction,diag.get('failure',''))
    original_train=dataset.gdp.loc[dataset.gdp.quarter.lt(target),'quarter'].tolist()
    gated=replace(dataset,gdp=pd.DataFrame({'quarter':gd.index,dataset.target_field:gd.to_numpy()}))
    spec=MidasSpec('umidas_usd_uzs_mom_dlog','usd_uzs_mom_dlog',3,True,None)
    prediction,diag=midas_forecast(gated,spec,original_train,target,horizon=horizon,mode=mode)
    if np.isfinite(prediction) and diag.get('n_train',0)<15:
        prediction=np.nan;diag['failure']='insufficient_effective_training'
    result['UMIDAS_USD']=(prediction,diag.get('failure',''))
    pred=.5*result['AR2'][0]+.5*prediction
    result['PRODUCTION_ENSEMBLE']=(pred,'' if np.isfinite(pred) else 'COMPONENT_UNAVAILABLE')
    return result

def predictions(dataset,available,target,horizon,mode,states,boundary,*,diagnostic=False):
    values=benchmarks(dataset,available,target,horizon,mode,diagnostic=diagnostic)
    adapted=available.frame.copy()
    adapted['release_date']=pd.to_datetime(adapted.publication_date)
    adapted['release_date_quality']='APPROXIMATE_FALLBACK' if diagnostic else 'ARCHIVED_PUBLICATION_DATE'
    typed=boundary.AvailableGDP(adapted,available.origin)
    index=pd.to_datetime(states.month)
    factors=states.value.to_numpy()[:,None]
    for letter in ['A','B']:
        try:
            value,_=boundary.bridge(factors,pd.DatetimeIndex(index),typed,target,'BRIDGE_'+letter,available.origin)
            values['DFM_'+letter]=(value,'')
        except ValueError as exc:
            values['DFM_'+letter]=(np.nan,str(exc))
        value=.5*values['DFM_'+letter][0]+.5*values['UMIDAS_USD'][0]
        values['COMBO_'+letter]=(value,'' if np.isfinite(value) else 'COMPONENT_UNAVAILABLE')
    return values

def matched(frame):
    if frame.duplicated(KEYS+['model']).any():
        raise ValueError('Duplicate model origin')
    wide=frame.pivot(index=KEYS,columns='model',values='prediction').reindex(columns=MODELS)
    valid=wide.dropna().reset_index()[KEYS]
    result=frame.merge(valid,on=KEYS,validate='many_to_one')
    assert result.groupby(KEYS).model.nunique().eq(len(MODELS)).all()
    return result

def metrics(frame,sample):
    rows=[]
    for (model,mode,rule),block in frame.groupby(['model','lag_mode','timing_rule']):
        for definition in TARGETS:
            for group in EVALS:
                f=block if group=='POOLED_RESEARCH_ONLY' else block.loc[block.evaluation_group.eq(group)]
                for horizon in ['H1','H2','H3','ALL','H2_H3']:
                    s=f if horizon=='ALL' else f.loc[f.horizon.isin(['H2','H3'])] if horizon=='H2_H3' else f.loc[f.horizon.eq(horizon)]
                    target_column='actual_first_release' if definition=='FIRST_RELEASE' else 'actual_latest_revised'
                    v=s.dropna(subset=['prediction',target_column])
                    error=v[target_column]-v.prediction
                    rows.append(dict(model=model,lag_mode=mode,timing_rule=rule,target_definition=definition,
                        evaluation_group=group,horizon=horizon,sample=sample,n_forecasts=len(v),n_target_quarters=v.target_quarter.nunique(),
                        rmse=float(np.sqrt((error**2).mean())) if len(v) else np.nan,
                        mae=float(error.abs().mean()) if len(v) else np.nan,bias=float(error.mean()) if len(v) else np.nan,
                        information_class='VERIFIED_DOCUMENTED_VINTAGES_PARTIAL_RELEASE_HISTORY'))
    return pd.DataFrame(rows)

def historical_forecasts(registry):
    mapping={'AR1_CLEAN_GDP_BOUNDARY':'AR1','AR2_CLEAN_GDP_BOUNDARY':'AR2',
        'UMIDAS_USD_CLEAN_GDP_BOUNDARY':'UMIDAS_USD','PRODUCTION_ENSEMBLE_CLEAN_GDP_BOUNDARY':'PRODUCTION_ENSEMBLE',
        'DFM_DOMESTIC_3__BRIDGE_A_CLEAN':'DFM_A','DFM_DOMESTIC_3__BRIDGE_B_CLEAN':'DFM_B',
        'COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_A_CLEAN':'COMBO_A','COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN':'COMBO_B'}
    one=pd.read_csv(ROOT/'results/research/phase6b1/phase6b1_forecasts.csv')
    one['model']=one.model.map(mapping);one['phase']='PHASE6B1'
    old=pd.read_csv(ROOT/'results/research/phase6b/phase6b_forecasts.csv')
    old=old.loc[old.model.isin(['DFM_DOMESTIC_3__BRIDGE_A','DFM_DOMESTIC_3__BRIDGE_B'])].copy()
    old['model']=old.model.map({'DFM_DOMESTIC_3__BRIDGE_A':'DFM_A','DFM_DOMESTIC_3__BRIDGE_B':'DFM_B'})
    combos=pd.read_csv(ROOT/'results/research/phase6b/phase6b_combination_forecasts.csv')
    combos=combos.loc[combos.model.isin(['COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_A','COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B'])].copy()
    combos['model']=combos.model.map({'COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_A':'COMBO_A','COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B':'COMBO_B'})
    frozen=pd.concat([pd.read_csv(ROOT/'results/phase4b_predictions.csv'),pd.read_csv(ROOT/'results/phase4c_holdout_predictions.csv')])
    names={'ar1':'AR1','ar2':'AR2','umidas_usd_uzs_mom_dlog':'UMIDAS_USD','ensemble_ar2_umidas_usd':'PRODUCTION_ENSEMBLE'}
    frozen=frozen.loc[frozen.model.isin(names)&frozen.target_quarter.isin(one.target_quarter.unique())].copy()
    frozen['model']=frozen.model.map(names)
    original=pd.concat([old,combos,frozen],ignore_index=True)
    original['phase']='PHASE6B'
    result=pd.concat([original,one],ignore_index=True)
    first=registry.set_index('quarter').first_release_value
    latest=registry.set_index('quarter').current_master_value
    result['actual_first_release']=result.target_quarter.map(first)
    result['actual_latest_revised']=result.target_quarter.map(latest)
    result['evaluation_group']=np.where(result.target_quarter.ge('2025Q3'),'HISTORICAL_POST_DEVELOPMENT_TEST','DEVELOPMENT_PSEUDO_OOS')
    return result

def evaluate(forecasts,registry,counterfactuals):
    common=write('matched_forecasts',matched(forecasts))
    write('horizon_metrics',pd.concat([metrics(forecasts,'ALL_AVAILABLE'),metrics(common,'COMMON_ALL_EIGHT_MODELS')],ignore_index=True))
    errors=[]
    for definition in TARGETS:
        f=common.copy()
        f['target_definition']=definition
        f['actual']=f.actual_first_release if definition=='FIRST_RELEASE' else f.actual_latest_revised
        f['error']=f.actual-f.prediction
        f['squared_error']=f.error**2
        errors.append(f)
    errors=pd.concat(errors,ignore_index=True)
    write('quarter_level_errors',errors)
    summary=errors.groupby(['target_quarter','model','lag_mode','timing_rule','target_definition'],as_index=False).agg(
        mean_error=('error','mean'),rmse=('squared_error',lambda s:float(np.sqrt(s.mean()))),mae=('error',lambda s:float(s.abs().mean())),n=('error','size'))
    write('quarter_error_summary',summary)
    leave=[]
    for q in sorted(common.target_quarter.unique()):
        m=metrics(common.loc[common.target_quarter.ne(q)&common.model.isin(['COMBO_B','UMIDAS_USD','PRODUCTION_ENSEMBLE','DFM_B'])],'LEAVE_ONE_QUARTER_OUT')
        group='HISTORICAL_POST_DEVELOPMENT_TEST' if q>='2025Q3' else 'DEVELOPMENT_PSEUDO_OOS'
        m=m.loc[m.evaluation_group.isin(['POOLED_RESEARCH_ONLY',group])].copy()
        m['omitted_target_quarter']=q
        leave.append(m)
    write('leave_one_quarter_out',pd.concat(leave,ignore_index=True))
    correlations=[]
    for (rule,mode,definition),f in errors.groupby(['timing_rule','lag_mode','target_definition']):
        for group in EVALS:
            s=f if group=='POOLED_RESEARCH_ONLY' else f.loc[f.evaluation_group.eq(group)]
            for horizon in ['H1','H2','H3','ALL','H2_H3']:
                h=s if horizon=='ALL' else s.loc[s.horizon.isin(['H2','H3'])] if horizon=='H2_H3' else s.loc[s.horizon.eq(horizon)]
                wide=h.pivot(index=['target_quarter','horizon'],columns='model',values='error')
                correlations.append(dict(timing_rule=rule,lag_mode=mode,target_definition=definition,evaluation_group=group,horizon=horizon,
                    n=len(wide),dfm_b_umidas_error_correlation=wide.DFM_B.corr(wide.UMIDAS_USD) if len(wide)>1 else np.nan))
    write('error_correlations',pd.DataFrame(correlations))
    historical=historical_forecasts(registry)
    comparisons=[]
    origins=['target_quarter','horizon','lag_mode','model']
    for rule in RULES:
        new=forecasts.loc[forecasts.timing_rule.eq(rule)]
        combined=new[origins+['prediction']].rename(columns={'prediction':'PHASE6B2'})
        for phase in ['PHASE6B','PHASE6B1']:
            old=historical.loc[historical.phase.eq(phase)]
            combined=combined.merge(old[origins+['prediction']].rename(columns={'prediction':phase}),on=origins,validate='one_to_one')
        combined['timing_rule']=rule
        combined=combined.merge(counterfactuals,on=KEYS+['model'],validate='one_to_one')
        combined['release_timing_effect']=combined.calendar_only_master_prediction-combined.PHASE6B1
        combined['archive_support_effect']=combined.master_on_documented_support_prediction-combined.calendar_only_master_prediction
        combined['GDP_value_vintage_effect']=combined.PHASE6B2-combined.master_on_documented_support_prediction
        combined['H1_restored']=combined.horizon.eq('H1')&combined.PHASE6B1.isna()&combined.PHASE6B2.notna()
        combined['counterfactual_information_class']='INVALID_REVISED_VALUES_DIAGNOSTIC_ONLY; calendar-only retains explicitly labelled 46-day fallback for unresolved early releases'
        comparisons.append(combined)
    comparison=write('phase6b1_comparison',pd.concat(comparisons,ignore_index=True))
    phase_metrics=[]
    # Every numerical three-phase comparison uses the identical three-way matched origins.
    for rule in RULES:
        keys=comparison.loc[comparison.timing_rule.eq(rule)].dropna(subset=['PHASE6B','PHASE6B1','PHASE6B2'])[origins]
        for phase in ['PHASE6B','PHASE6B1','PHASE6B2']:
            f=forecasts.loc[forecasts.timing_rule.eq(rule)] if phase=='PHASE6B2' else historical.loc[historical.phase.eq(phase)].assign(timing_rule=rule)
            f=f.merge(keys,on=origins,validate='one_to_one')
            m=metrics(f,'THREE_PHASE_EXACT_MATCHED_ORIGINS')
            m['phase']=phase
            if phase!='PHASE6B2':
                m['information_class']='FROZEN_HISTORICAL_REFERENCE_NOT_VERIFIED_VINTAGE_RESULT'
            phase_metrics.append(m)
    write('phase_comparison_metrics',pd.concat(phase_metrics,ignore_index=True))
    return common

def main():
    count=protect()
    registry,events=reconstruct()
    dataset=load_dataset(ROOT)
    boundary=frozen_module('phase6b2_frozen_boundary','scripts/research/phase6b1/boundary.py')
    states=pd.read_csv(OUT/'phase6b2_factor_series.csv')
    master=registry.set_index('quarter').current_master_value
    first=registry.set_index('quarter').first_release_value
    rindex=registry.set_index('quarter')
    forecasts,audit,usage,counterfactuals=[],[],[],[]
    from vintages import VintageGDP
    for (target,horizon,mode),factors in states.groupby(['target_quarter','horizon','lag_mode']):
        origin=horizon_month_end(target,horizon)
        for rule in RULES:
            available=available_gdp_vintage_as_of(events,origin,target=target,timing_rule=rule)
            prior=str(pd.Period(target,freq='Q')-1)
            date=rindex.loc[prior,'first_release_date']
            same=pd.notna(date) and pd.Timestamp(date).date()==origin.date()
            missing=[q for q in master.index if q<target and q not in available.frame.index]
            audit.append(dict(target_quarter=target,horizon=horizon,lag_mode=mode,timing_rule=rule,
                forecast_origin_date=str(origin.date()),operational_cutoff='00:00:00 Asia/Tashkent (frozen origin convention)',
                prior_quarter=prior,prior_first_release_date=date,prior_GDP_available=prior in available.frame.index,
                same_day_status='SAME_DAY_TIME_UNKNOWN' if same else 'NOT_SAME_DAY',
                first_release_date_verified=bool(rindex.loc[prior,'release_date_verified']),
                prior_GDP_vintage_value=available.frame.loc[prior,'value'] if prior in available.frame.index else np.nan,
                prior_GDP_current_value=float(master.loc[prior]),prior_GDP_first_release_value=first.loc[prior],
                excluded_GDP_quarters=json.dumps(missing),available_GDP_quarters=json.dumps(available.frame.index.tolist()),
                n_documented_GDP_quarters=len(available.frame),revision_history_complete=False,
                H1_restored_relative_46_day=horizon=='H1' and prior in available.frame.index))
            for q,row in available.frame.iterrows():
                usage.append(dict(target_quarter=target,horizon=horizon,lag_mode=mode,timing_rule=rule,
                    forecast_origin_date=str(origin.date()),GDP_quarter=q,**row.to_dict(),current_master_value=float(master.loc[q]),
                    GDP_vintage_differs_from_master=not np.isclose(row.value,master.loc[q],rtol=0,atol=1e-9)))
            values=predictions(dataset,available,target,horizon,mode,factors,boundary)
            # Explicit invalid-value diagnostics, never primary forecasts or accessor inputs.
            support=available.frame.copy();support['value']=master.reindex(support.index)
            support['value_verified']=False
            on_support=predictions(dataset,VintageGDP(support,origin,rule),target,horizon,mode,factors,boundary,diagnostic=True)
            calendar=[]
            for q in master.index:
                if q>=target:
                    continue
                d=rindex.loc[q,'first_release_date']
                d=pd.Timestamp(d) if pd.notna(d) else pd.Period(q,freq='Q').end_time.normalize()+pd.Timedelta(days=46)
                if d<origin or (d==origin and rule=='PERMISSIVE_END_OF_DAY'):
                    calendar.append(dict(quarter=q,value=master[q],publication_date=str(d.date()),available_date=d,
                        value_verified=False,date_verified=bool(rindex.loc[q,'release_date_verified']),source_url=None,sha256=None))
            cf=pd.DataFrame(calendar).set_index('quarter')
            calendar_values=predictions(dataset,VintageGDP(cf,origin,rule),target,horizon,mode,factors,boundary,diagnostic=True)
            for model,(value,failure) in values.items():
                forecasts.append(dict(model=model,target_quarter=target,horizon=horizon,lag_mode=mode,timing_rule=rule,
                    forecast_origin_date=str(origin.date()),prediction=value,failure=failure,
                    actual_first_release=first[target],actual_latest_revised=master[target],
                    evaluation_group='HISTORICAL_POST_DEVELOPMENT_TEST' if target>='2025Q3' else 'DEVELOPMENT_PSEUDO_OOS',
                    information_class='VERIFIED_DOCUMENTED_VINTAGES_PARTIAL_RELEASE_HISTORY',revision_history_complete=False))
                counterfactuals.append(dict(model=model,target_quarter=target,horizon=horizon,lag_mode=mode,timing_rule=rule,
                    calendar_only_master_prediction=calendar_values[model][0],master_on_documented_support_prediction=on_support[model][0]))
        print('GDP vintages evaluated',target,horizon,mode,flush=True)
    f=write('forecasts',pd.DataFrame(forecasts))
    write('clean_benchmark_forecasts',f.loc[f.model.isin(MODELS[:4])])
    write('dfm_forecasts',f.loc[f.model.isin(['DFM_A','DFM_B'])])
    write('combination_forecasts',f.loc[f.model.isin(['COMBO_A','COMBO_B'])])
    write('origin_information_audit',pd.DataFrame(audit))
    write('GDP_training_vintage_usage',pd.DataFrame(usage))
    common=evaluate(f,registry,pd.DataFrame(counterfactuals))
    protect()
    manifest=dict(phase='6B.2',status='RESEARCH_COMPLETED_WITH_INCOMPLETE_RELEASE_HISTORY',
        classification='PHASE6B2_RELEASE_HISTORY_INCOMPLETE',research_only=True,model_promotion=False,
        created_at=datetime.now(timezone.utc).isoformat(),verified_first_release_dates=int(registry.release_date_verified.sum()),
        verified_first_release_values=int(registry.first_release_value_verified.sum()),GDP_quarters=len(registry),
        unresolved_first_release_quarters=registry.loc[~registry.release_date_verified,'quarter'].tolist(),
        revision_history_complete=False,documented_vintage_events=len(events),
        known_first_to_master_revised_quarters=int(registry.revision_from_first_release.fillna(0).abs().gt(1e-9).sum()),
        same_day_unknown_origins=int(pd.DataFrame(audit).query("timing_rule == 'STRICT'").same_day_status.eq('SAME_DAY_TIME_UNKNOWN').sum()),
        H1_restored_per_timing_rule=int(pd.DataFrame(audit).query("timing_rule == 'STRICT'").H1_restored_relative_46_day.sum()),
        matched_origins_per_timing_rule=int(len(common.query("timing_rule == 'STRICT'"))/8),
        factor_identity_checks=len(pd.read_csv(OUT/'phase6b2_factor_core_identity_checks.csv')),
        maximum_factor_difference=float(pd.read_csv(OUT/'phase6b2_factor_core_identity_checks.csv').maximum_factor_difference.max()),
        protected_files=count,protected_status='UNCHANGED',
        inputs_sha256={p:sha(ROOT/p) for p in ['data/master/gdp_quarterly.parquet','data/master/v1_monthly.parquet',
            'data/research/phase6a2/cbu_midas_monthly_panel.csv','scripts/research/phase6b/experiment.py','scripts/research/phase6b1/boundary.py']},
        code_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in Path(__file__).parent.glob('*.py')},
        tests='PENDING',deterministic_rerun='PENDING',
        limitations=['Ten early first-release dates/values unresolved; undated files not backdated.',
            'Accessor selects latest DOCUMENTED vintage, not a certified exhaustive revision history.',
            'Two suspect historical chart labels retained in ledger and excluded from model accessor.',
            'FIRST_RELEASE is primary diagnostic; LATEST_REVISED is secondary; no model selection or tuning.'])
    (OUT/'phase6b2_run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':
    main()
