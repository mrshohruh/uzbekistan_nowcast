"""Research-only GDP-boundary repair; immutable Phase 6B DFM core import."""
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import logging
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(Path(__file__).parent))
import numpy as np
import pandas as pd
from reproduce import old_core, demonstrate
from boundary import release_metadata,available_gdp_as_of,bridge,assert_boundary
from uznowcast.models.data import load_dataset,horizon_month_end,quarter_start,quarter_end
from uznowcast.models.benchmarks import ar_forecast
from uznowcast.models.midas import MidasSpec,midas_forecast

OUT=ROOT/'results/research/phase6b1'
DOC=ROOT/'docs/modeling/phase6b1'
KEYS=['target_quarter','horizon','lag_mode']
BENCH_NAMES={'ar1':'AR1_CLEAN_GDP_BOUNDARY','ar2':'AR2_CLEAN_GDP_BOUNDARY',
             'umidas_usd_uzs_mom_dlog':'UMIDAS_USD_CLEAN_GDP_BOUNDARY',
             'ensemble_ar2_umidas_usd':'PRODUCTION_ENSEMBLE_CLEAN_GDP_BOUNDARY'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protect():
    before=json.loads((OUT/'phase6b1_protected_before.json').read_text())
    after={p:sha(ROOT/p) if (ROOT/p).is_file() else 'MISSING' for p in before}
    changed=[p for p in before if before[p]!=after[p]]
    if changed:
        raise RuntimeError('Protected artifacts changed: '+', '.join(changed))
    return after


def js(name,value):
    (OUT/f'phase6b1_{name}.json').write_text(json.dumps(value,indent=2,default=str,allow_nan=False),encoding='utf-8')


def csv(name,rows,columns=None):
    f=rows if isinstance(rows,pd.DataFrame) else pd.DataFrame(rows)
    if f.empty and columns:
        f=pd.DataFrame(columns=columns)
    f.to_csv(OUT/f'phase6b1_{name}.csv',index=False,float_format='%.12g')
    return f


def clean_benchmarks(dataset,available,target,horizon,mode):
    origin=horizon_month_end(target,horizon)
    assert_boundary(available,target,origin)
    prior=str(pd.Period(target,freq='Q')-1)
    if prior not in available.frame.index:
        return {name:(np.nan,{'failure':'PRIOR_QUARTER_GDP_NOT_AVAILABLE'}) for name in BENCH_NAMES.values()}
    gd=available.frame.value
    if not pd.Index(gd.index).equals(pd.Index(pd.period_range(gd.index[0],gd.index[-1],freq='Q').astype(str))):
        return {name:(np.nan,{'failure':'NONCONSECUTIVE_GDP_TRAINING'}) for name in BENCH_NAMES.values()}
    values={}
    for p,name in [(1,'ar1'),(2,'ar2')]:
        values[BENCH_NAMES[name]]=ar_forecast(gd,p)
    # Preserve the original calendar training sequence and monthly lag kernel.
    original_train=dataset.gdp.loc[dataset.gdp.quarter.lt(target),'quarter'].tolist()
    gated=replace(dataset,gdp=pd.DataFrame({'quarter':gd.index,dataset.target_field:gd.to_numpy()}))
    spec=MidasSpec('umidas_usd_uzs_mom_dlog','usd_uzs_mom_dlog',3,True,None)
    prediction,diag=midas_forecast(gated,spec,original_train,target,horizon=horizon,mode=mode)
    if np.isfinite(prediction) and diag.get('n_train',0)<15:
        prediction=np.nan;diag['failure']='insufficient_effective_training'
    values[BENCH_NAMES[spec.name]]=(prediction,diag)
    ar2=values[BENCH_NAMES['ar2']][0]
    combination=.5*ar2+.5*prediction
    values[BENCH_NAMES['ensemble_ar2_umidas_usd']]=(combination,{'failure':'' if np.isfinite(combination) else 'COMPONENT_UNAVAILABLE'})
    return values


def metrics(frame,sample,comparator=''):
    rows=[]
    for (model,mode),block in frame.groupby(['model','lag_mode']):
        for evidence in ['DEVELOPMENT_PSEUDO_OOS','HISTORICAL_POST_DEVELOPMENT_TEST','POOLED_RESEARCH_ONLY']:
            subset=block if evidence=='POOLED_RESEARCH_ONLY' else block.loc[block.evaluation_group.eq(evidence)]
            for h in ['H1','H2','H3','ALL']:
                f=subset if h=='ALL' else subset.loc[subset.horizon.eq(h)]
                valid=f.dropna(subset=['prediction','actual'])
                errors=valid.actual-valid.prediction
                rows.append(dict(model=model,lag_mode=mode,evaluation_group=evidence,horizon=h,sample=sample,
                                 comparator=comparator,n_forecasts=len(valid),n_target_quarters=valid.target_quarter.nunique(),
                                 rmse=float(np.sqrt((errors**2).mean())) if len(valid) else np.nan,
                                 mae=float(abs(errors).mean()) if len(valid) else np.nan,
                                 bias=float(errors.mean()) if len(valid) else np.nan))
    return pd.DataFrame(rows)


def paired(a,b):
    if a.duplicated(KEYS).any() or b.duplicated(KEYS).any():
        raise ValueError('duplicate_origin')
    m=a.merge(b[KEYS+['prediction','actual']],on=KEYS,suffixes=('','_benchmark'),validate='one_to_one')
    m=m.dropna(subset=['prediction','prediction_benchmark'])
    assert np.allclose(m.actual,m.actual_benchmark,atol=1e-10,rtol=0)
    return m


def source_audit(dataset,meta):
    """Inspect stored GDP provenance and JSON archives without network calls."""
    rows=[]
    for path in ['data/master/gdp_quarterly.parquet','data/processed/gdp_real_yoy.parquet',
                 'metadata/release_calendar.parquet','metadata/release_availability.parquet',
                 'metadata/observations_long.parquet','metadata/vintages.parquet','metadata/download_log.parquet']:
        frame=pd.read_parquet(ROOT/path)
        if 'variable_key' in frame:
            frame=frame.loc[frame.variable_key.eq('gdp_real_yoy')]
        rows.append(dict(path=path,sha256=sha(ROOT/path),GDP_rows=len(frame),
                         assessment='GDP timestamps are current dataset update/retrieval; no per-quarter historical first release',
                         columns=json.dumps(frame.columns.tolist())))
    for path in (ROOT/'data/raw/siat/gdp_real_yoy').glob('*'):
        if not path.is_file():
            continue
        obj=json.loads(path.read_text(encoding='utf-8'))
        evidence=[]
        if isinstance(obj,dict) and 'updated_at' in obj:
            evidence.append('descriptor updated_at='+obj['updated_at'])
        if isinstance(obj,list):
            for block in obj:
                for entry in block.get('metadata',[]):
                    if entry.get('name_en') in ['Date of first publication','Last modified date']:
                        evidence.append(entry['name_en']+'='+entry.get('value_en','')+' (dataset-level, not quarter-specific)')
        rows.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),GDP_rows=None,
                         assessment='; '.join(evidence) or 'raw provenance sidecar; not historical observation release archive'))
    for path in ['docs/release_metadata_audit.md','src/uznowcast/io/siat.py','src/uznowcast/models/data.py',
                 'src/uznowcast/operational/phase5a.py','src/uznowcast/models/phase4b.py','src/uznowcast/models/phase4c.py',
                 'src/uznowcast/models/midas.py','src/uznowcast/models/benchmarks.py',
                 'results/frozen_validation_definition.json','results/challengers/phase5c/phase5c_challenger_protocol.json']:
        rows.append(dict(path=path,sha256=sha(ROOT/path),assessment='Inspected frozen timing/model definition or GDP provenance rule'))
    csv('GDP_source_evidence',rows)


def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s',
                        handlers=[logging.FileHandler(OUT/'phase6b1_pipeline.log',mode='w'),logging.StreamHandler()])
    np.random.seed(602)
    before=protect()
    reproduction=demonstrate()
    assert (OUT/'phase6b1_leak_reproduction.json').exists(),'Run leak reproduction first'
    dataset=load_dataset(ROOT)
    gdp=dataset.gdp.set_index('quarter').gdp_real_yoy_pct
    stored_calendar=pd.read_parquet(ROOT/'metadata/release_calendar.parquet')
    stored_calendar=stored_calendar.loc[stored_calendar.variable_key.eq('gdp_real_yoy')].copy()
    valid_qualities=['VERIFIED_ACTUAL_RELEASE_DATE','ARCHIVED_PUBLICATION_DATE','DOCUMENTED_RULE']
    stored_calendar['release_date_quality']=stored_calendar.source_release_basis.str.upper()
    historical=stored_calendar.loc[stored_calendar.release_date_quality.isin(valid_qualities)].rename(
        columns={'reference_period':'quarter','source_release_date':'release_date'})
    historical['release_date_source']='metadata/release_calendar.parquet: explicit historical release basis'
    metadata=release_metadata(gdp,dataset.release_lag_days['gdp_real_yoy'],historical)
    csv('gdp_release_audit',metadata.reset_index(drop=True))
    source_audit(dataset,metadata)
    definition=json.loads((ROOT/'results/frozen_validation_definition.json').read_text())
    old=pd.read_csv(ROOT/'results/research/phase6b/phase6b_forecasts.csv')
    old=old.loc[old.model.isin(['DFM_DOMESTIC_3__BRIDGE_A','DFM_DOMESTIC_3__BRIDGE_B'])]
    old_states=pd.read_csv(ROOT/'results/research/phase6b/phase6b_factor_series.csv')
    panel=pd.read_csv(ROOT/'data/research/phase6a2/cbu_midas_monthly_panel.csv')
    panel.index=pd.PeriodIndex(panel.reference_period,freq='M').to_timestamp('M')
    panel=panel.loc['2021-01-31':'2026-08-31']
    core=old_core()
    spec=core.Spec('DFM_DOMESTIC_3',core.DOMESTIC)
    forecasts,origin_audit,convergence,states_out,failed,factorchecks,training_audit=[],[],[],[],[],[],[]
    for (target,horizon,mode),orig_rows in old.groupby(KEYS,sort=True):
        origin=horizon_month_end(target,horizon)
        logging.info('DFM unchanged; GDP bridge repair %s %s %s',target,horizon,mode)
        available=available_gdp_as_of(gdp,metadata,origin,target=target)
        prior=str(pd.Period(target,freq='Q')-1)
        prior_available=prior in available.frame.index
        excluded=[q for q in gdp.index if q<target and q not in available.frame.index]
        origin_audit.append(dict(target_quarter=target,horizon=horizon,lag_mode=mode,forecast_origin_date=str(origin.date()),
                                 prior_quarter=prior,prior_GDP_available_at_origin=prior_available,
                                 prior_GDP_actual_release_date=None,prior_GDP_rule_available_date=str(metadata.loc[prior,'available_date'].date()),
                                 release_date_quality=metadata.loc[prior,'release_date_quality'],release_date_verified=False,
                                 available_GDP_quarters=json.dumps(available.frame.index.tolist()),
                                 excluded_pre_target_GDP=json.dumps(excluded),
                                 GDP_availability_changed=bool(excluded),bridge_A_training_changed=bool(excluded)))
        train_end=quarter_start(target)-pd.Timedelta(days=1)
        masked,_=core.masked_panel(panel,spec.fields,target,horizon,dataset.release_lag_days,mode)
        z,means,stds,_,_=core.prepare(masked,panel.services_output_regime,train_end,False)
        training=z.loc[:train_end]
        timeline=pd.date_range(panel.index.min(),quarter_end(target),freq='ME')
        z=z.reindex(timeline)
        fit,factors,loads,params,signs,diag=core.estimate(training,z,spec)
        convergence.append(dict(target_quarter=target,horizon=horizon,lag_mode=mode,**diag))
        if diag.get('failure'):
            raise RuntimeError('Unchanged DFM unexpectedly failed: '+diag['failure'])
        prior_states=old_states.loc[old_states.specification.eq(spec.name)&old_states.target_quarter.eq(target)&
                                    old_states.horizon.eq(horizon)&old_states.lag_mode.eq(mode)&old_states.factor.eq(1)].sort_values('month')
        delta=float(np.max(np.abs(factors[:,0]-prior_states.value.to_numpy())))
        assert delta<1e-8,('DFM changed',target,horizon,mode,delta)
        factorchecks.append(dict(target_quarter=target,horizon=horizon,lag_mode=mode,maximum_factor_difference=delta,
                                 dfm_core_unchanged=True))
        for date,value in zip(timeline,factors[:,0]):
            states_out.append(dict(target_quarter=target,horizon=horizon,lag_mode=mode,month=str(date.date()),value=value,
                                  factor_source='FILTERED_ONE_SIDED' if date<=origin else 'STATE_PREDICTED_NO_TARGET_OBSERVATIONS'))
        for bridge_name in ['BRIDGE_A','BRIDGE_B']:
            model=spec.name+'__'+bridge_name+'_CLEAN'
            base=dict(model=model,target_quarter=target,horizon=horizon,lag_mode=mode,forecast_origin_date=str(origin.date()),
                      actual=float(gdp.loc[target]),evaluation_group='HISTORICAL_POST_DEVELOPMENT_TEST' if target in definition['holdout_quarters'] else 'DEVELOPMENT_PSEUDO_OOS',
                      evidence_class='CALENDAR_PSEUDO_REAL_TIME_RESEARCH',GDP_timing_policy='CONSERVATIVE_REPOSITORY_46_DAY_FALLBACK')
            try:
                value,detail=bridge(factors,timeline,available,target,bridge_name,origin)
                forecasts.append(dict(**base,prediction=value,failure='',n_GDP_quarters=detail['n_GDP_quarters'],
                                      bridge_coefficients=json.dumps(detail['bridge_coefficients'])))
                for q in detail['training_quarters']:
                    lag=str(pd.Period(q,freq='Q')-1) if bridge_name=='BRIDGE_B' else None
                    training_audit.append(dict(model=model,target_quarter=target,horizon=horizon,lag_mode=mode,
                                               forecast_origin_date=str(origin.date()),training_quarter=q,
                                               dependent_GDP_available_date=str(metadata.loc[q,'available_date'].date()),
                                               lag_quarter=lag,lag_GDP_available_date=str(metadata.loc[lag,'available_date'].date()) if lag else None))
            except ValueError as exc:
                forecasts.append(dict(**base,prediction=np.nan,failure=str(exc)))
                failed.append(dict(**base,reason=str(exc)))
    dfm=csv('dfm_forecasts',forecasts)
    csv('origin_information_audit',origin_audit)
    csv('bridge_training_information_audit',training_audit)
    csv('factor_core_identity_checks',factorchecks)
    csv('factor_series',states_out)
    csv('convergence_diagnostics',convergence)
    # Frozen benchmarks audited over ALL their stored historical origins.
    frozen=pd.concat([pd.read_csv(ROOT/'results/phase4b_predictions.csv'),pd.read_csv(ROOT/'results/phase4c_holdout_predictions.csv')],ignore_index=True)
    frozen=frozen.loc[frozen.model.isin(BENCH_NAMES)].copy()
    assert not frozen.duplicated(['model']+KEYS).any()
    audit,bench=[],[]
    for (target,horizon,mode),block in frozen.groupby(KEYS,sort=True):
        origin=horizon_month_end(target,horizon)
        prior=str(pd.Period(target,freq='Q')-1)
        available=available_gdp_as_of(gdp,metadata,origin,target=target)
        clean=clean_benchmarks(dataset,available,target,horizon,mode)
        for record in block.to_dict('records'):
            name=record['model']
            status='CLEAN' if prior in available.frame.index else 'LEAK_CONFIRMED'
            code='src/uznowcast/models/phase4b.py:_benchmark_rows/_midas_rows' if target in definition['development_quarters'] else 'src/uznowcast/models/phase4c.py:_forecast_rows'
            audit.append(dict(benchmark_model=name,target_quarter=target,horizon=horizon,lag_mode=mode,
                              forecast_origin_date=str(origin.date()),latest_GDP_used=prior,latest_GDP_release_date=None,
                              latest_GDP_assumed_available_date=str(metadata.loc[prior,'available_date'].date()),
                              available_at_origin=prior in available.frame.index,leakage_status=status,
                              actual_historical_release_verified=False,actual_timing_status='UNVERIFIABLE',
                              frozen_forecast_issued=bool(np.isfinite(record['prediction'])),
                              source_code_reference=code+'; benchmarks.py:fit_ar/forecast or midas.py:_training_matrix/midas_forecast',
                              notes='Status is against explicit 46-day fallback; actual publication unverified; training/target lag use all chronological prior GDP'))
            prediction,detail=clean[BENCH_NAMES[name]]
            bench.append(dict(model=BENCH_NAMES[name],target_quarter=target,horizon=horizon,lag_mode=mode,
                              forecast_origin_date=str(origin.date()),actual=float(gdp.loc[target]),prediction=prediction,
                              failure=detail.get('failure',''),evaluation_group='HISTORICAL_POST_DEVELOPMENT_TEST' if target in definition['holdout_quarters'] else 'DEVELOPMENT_PSEUDO_OOS',
                              evidence_class='CALENDAR_PSEUDO_REAL_TIME_RESEARCH',
                              frozen_model=name,frozen_prediction=record['prediction'],
                              GDP_timing_policy='CONSERVATIVE_REPOSITORY_46_DAY_FALLBACK'))
            if status=='CLEAN' and np.isfinite(record['prediction']):
                assert np.isclose(prediction,record['prediction'],rtol=0,atol=1e-9),('Frozen model changed',name,target,horizon,mode)
    benchmark_audit=csv('benchmark_gdp_information_audit',audit)
    all_bench=csv('clean_benchmark_forecasts',bench)
    targets=sorted(dfm.target_quarter.unique())
    bench_df=all_bench.loc[all_bench.target_quarter.isin(targets)].copy()
    combos=[]
    usd=bench_df.loc[bench_df.model.eq('UMIDAS_USD_CLEAN_GDP_BOUNDARY')]
    for name,block in dfm.groupby('model'):
        merged=block.merge(usd[KEYS+['prediction']],on=KEYS,suffixes=('','_umidas'),validate='one_to_one')
        for r in merged.to_dict('records'):
            r['model']='COMBO_EQUAL__'+name
            r['prediction']=.5*r['prediction']+.5*r.pop('prediction_umidas')
            if not np.isfinite(r['prediction']):
                r['failure']=r.get('failure') or 'CLEAN_UMIDAS_NOT_AVAILABLE'
            combos.append(r)
    combo=csv('combination_forecasts',combos)
    all_forecasts=pd.concat([dfm,bench_df,combo],ignore_index=True)
    all_forecasts['error']=all_forecasts.actual-all_forecasts.prediction
    all_forecasts=csv('forecasts',all_forecasts)
    for r in all_forecasts.loc[all_forecasts.prediction.isna()].to_dict('records'):
        r['reason']=r.get('failure') or 'FORECAST_UNAVAILABLE'
    csv('failed_origins',all_forecasts.loc[all_forecasts.prediction.isna()].assign(reason=lambda f:f.failure))
    available_metrics=metrics(all_forecasts,'ALL_AVAILABLE_ORIGIN')
    matches,matchedmetrics=[],[]
    for name,block in pd.concat([dfm,combo],ignore_index=True).groupby('model'):
        for comparator,b in bench_df.groupby('model'):
            match=paired(block,b)
            match['benchmark_model']=comparator
            matches.extend(match.to_dict('records'))
            m=metrics(match,'MATCHED_SAMPLE',comparator)
            bb=match.copy();bb['model']=comparator;bb['prediction']=bb.prediction_benchmark
            bm=metrics(bb,'MATCHED_SAMPLE',name)
            for mr,br in zip(m.to_dict('records'),bm.to_dict('records')):
                mr.update(benchmark_rmse=br['rmse'],benchmark_mae=br['mae'],benchmark_n_forecasts=br['n_forecasts'])
                matchedmetrics.append(mr)
    csv('matched_forecasts',matches)
    all_metrics=pd.concat([available_metrics,pd.DataFrame(matchedmetrics)],ignore_index=True)
    csv('horizon_metrics',all_metrics.loc[all_metrics.horizon.ne('ALL')])
    csv('model_metrics',all_metrics.loc[all_metrics.horizon.eq('ALL')])
    csv('combination_metrics',all_metrics.loc[all_metrics.model.str.startswith('COMBO_EQUAL')])
    csv('benchmark_comparison',matchedmetrics)
    old_combo=pd.read_csv(ROOT/'results/research/phase6b/phase6b_combination_forecasts.csv')
    old_combo=old_combo.loc[old_combo.model.eq('COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B')]
    old_b=old.loc[old.model.eq('DFM_DOMESTIC_3__BRIDGE_B')]
    clean_b=dfm.loc[dfm.model.eq('DFM_DOMESTIC_3__BRIDGE_B_CLEAN')]
    clean_combo=combo.loc[combo.model.eq('COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN')]
    revision=old_b[KEYS+['prediction']].rename(columns={'prediction':'old_DFM_B_prediction'})
    for frame,field in [(clean_b,'clean_DFM_B_prediction'),(old_combo,'old_combo_prediction'),(clean_combo,'clean_combo_prediction')]:
        revision=revision.merge(frame[KEYS+['prediction']].rename(columns={'prediction':field}),on=KEYS,validate='one_to_one')
    revision['difference']=revision.clean_DFM_B_prediction-revision.old_DFM_B_prediction
    revision=revision.merge(pd.DataFrame(origin_audit)[KEYS+['GDP_availability_changed','prior_GDP_available_at_origin']],on=KEYS,validate='one_to_one')
    revision['notes']=np.where(revision.prior_GDP_available_at_origin,'same eligible GDP information; numerical identity checked',
                               'withdrawn: PRIOR_QUARTER_GDP_NOT_AVAILABLE; no forecast substituted')
    csv('prediction_revision_audit',revision)
    # Before/after statistics use the SAME surviving origins, not the old full denominator.
    before_after=[]
    for clean_name,old_name,old_source in [('DFM_DOMESTIC_3__BRIDGE_B_CLEAN','DFM_DOMESTIC_3__BRIDGE_B',old),
                                         ('COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN','COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B',old_combo),
                                         ('DFM_DOMESTIC_3__BRIDGE_A_CLEAN','DFM_DOMESTIC_3__BRIDGE_A',old)]:
        clean_rows=all_forecasts.loc[all_forecasts.model.eq(clean_name)]
        m=paired(clean_rows,old_source.loc[old_source.model.eq(old_name)])
        before= m.copy();before['model']=old_name;before['prediction']=before.prediction_benchmark
        cm=metrics(m,'MATCHED_BEFORE_AFTER',old_name)
        om=metrics(before,'MATCHED_BEFORE_AFTER',clean_name)
        for c,o in zip(cm.to_dict('records'),om.to_dict('records')):
            c.update(old_rmse=o['rmse'],old_mae=o['mae'],old_bias=o['bias'],rmse_change=c['rmse']-o['rmse'])
            before_after.append(c)
    csv('before_after_matched_metrics',before_after)
    # Availability sensitivity only; not new model selection or alternative fits.
    sensitivity=[]
    for row in origin_audit:
        prior=str(pd.Period(row['target_quarter'],freq='Q')-1)
        origin=pd.Timestamp(row['forecast_origin_date'])
        nominal=quarter_end(prior)+pd.Timedelta(days=dataset.release_lag_days['gdp_real_yoy'])
        sensitivity.append(dict(**{k:row[k] for k in KEYS},available_under_registry_31_days=nominal<=origin,
                                available_under_primary_46_days=row['prior_GDP_available_at_origin']))
    csv('GDP_timing_sensitivity',sensitivity)
    after=protect();js('protected_after',after)
    inputs=['data/master/gdp_quarterly.parquet','data/research/phase6a2/cbu_midas_monthly_panel.csv',
            'registry/uzbekistan_nowcasting_v1.2_registry.xlsx','results/frozen_validation_definition.json',
            'results/phase4b_predictions.csv','results/phase4c_holdout_predictions.csv',
            'results/research/phase6b/phase6b_forecasts.csv','results/research/phase6b/phase6b_factor_series.csv']
    manifest=dict(status='RESEARCH_RERUN_COMPLETE_PENDING_TEST_FINALIZATION',timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  phase='6B.1',classification='PHASE6B_RESULT_WEAKENED',
                  label='CALENDAR_PSEUDO_REAL_TIME_RESEARCH',GDP_release_metadata_source='GDP source evidence CSV; registry31 + Phase5A conservative15 =46 days',
                  GDP_quarters_verified_release_dates=int(metadata.release_date_verified.sum()),
                  GDP_quarters_fallback_timing=int(metadata.release_date_quality.eq('APPROXIMATE_FALLBACK').sum()),
                  GDP_quarters_unknown_availability=int(metadata.available_date.isna().sum()),
                  GDP_quarters_actual_publication_unknown=int(metadata.release_date.isna().sum()),GDP_conservative_lag_days=46,
                  GDP_fallback_same_for_both_monthly_lag_modes=True,DFM_core_sha256=sha(ROOT/'scripts/research/phase6b/experiment.py'),
                  DFM_core_identity_tolerance=1e-8,DFM_core_identity_max_error=max(r['maximum_factor_difference'] for r in factorchecks),
                  n_Bridge_B_origins_affected=sum(not r['prior_GDP_available_at_origin'] for r in origin_audit),
                  affected_Bridge_B_by_horizon={h:sum(r['horizon']==h and not r['prior_GDP_available_at_origin'] for r in origin_audit) for h in ['H1','H2','H3']},
                  n_benchmark_model_origins_affected=int(benchmark_audit.leakage_status.eq('LEAK_CONFIRMED').sum()),
                  n_benchmark_issued_forecasts_affected=int((benchmark_audit.leakage_status.eq('LEAK_CONFIRMED') & benchmark_audit.frozen_forecast_issued).sum()),
                  n_benchmark_model_origins_affected_in_DFM_window=int(benchmark_audit.loc[benchmark_audit.target_quarter.isin(targets)].leakage_status.eq('LEAK_CONFIRMED').sum()),
                  GDP_targets=targets,monthly_sample=['2021-01','2026-08'],
                  model_forecast_counts={k:int(v) for k,v in all_forecasts.groupby('model').prediction.count().items()},
                  failed_forecast_rows=int(all_forecasts.prediction.isna().sum()),
                  protected_count=len(after),protected_byte_identical=True,protected_artifact_hashes=after,
                  input_hashes={p:sha(ROOT/p) for p in inputs},
                  code_hashes={p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},
                  registry_amended=False,production_modified=False,phase6b_modified=False,dashboard_replaced=False,
                  benchmark_comparison='POLICY_COMPARABLE_CALENDAR_RESEARCH; actual historical releases UNVERIFIABLE',
                  AR_missing_prior_policy='unavailable; no shifted last-available-quarter one-step prediction',
                  post_development_07319='H1 withdrawn; full 12-origin headline not valid; compare surviving H2/H3 origins only')
    js('run_manifest',manifest)
    from report import write_report
    write_report(ROOT,OUT,DOC,manifest,all_forecasts,all_metrics,pd.DataFrame(before_after),pd.DataFrame(origin_audit),benchmark_audit)
    protect()


if __name__=='__main__':
    main()
