"""Phase 6G.3 isolated audit/experiment; never call a production writer."""
from pathlib import Path
import json
import logging
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from scripts.phase6g3.protection import OUT, verify, snapshot
from scripts.phase6g3.nominal import load_siat, transform
from scripts.phase6g3.vintages import evidence_events, targets_as_of
from scripts.phase6g3.audit import real_audit
from scripts.phase6g3.experiment import controlled_bridges, scores
from scripts.phase6g2.core import design, fit
from scripts.phase6e.models import frames, sw, FIELDS
from scripts.phase6g.run import production_info
from scripts.phase6f.experiment import dump, sha
from uznowcast.models.data import load_dataset,horizon_month_end

LOG=logging.getLogger('phase6g3')


def csv(name,data):pd.DataFrame(data).to_csv(OUT/(name+'.csv'),index=False,float_format='%.17g')


def first_nominal_growth(events):
    derived=[]
    for date in sorted(events.publication_date.unique()):
        f=targets_as_of(events,pd.Timestamp(date)+pd.Timedelta(days=1),None)
        if not f.empty:
            derived.extend(dict(quarter=q,as_of_publication_date=date,**r) for q,r in f.to_dict('index').items())
    f=pd.DataFrame(derived).sort_values(['quarter','as_of_publication_date'])
    f['previous_growth']=f.groupby('quarter').value.shift()
    f['growth_revision']=f.value-f.previous_growth
    csv('nominal_growth_vintage_history',f)
    return f.drop_duplicates('quarter',keep='first').set_index('quarter')


def run():
    OUT.mkdir(exist_ok=True)
    if not (OUT/'protected_before.json').exists():snapshot()
    verify()
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(OUT/'pipeline.log',encoding='utf8'),logging.StreamHandler()])
    audit=real_audit()
    quarter,meta=load_siat(3695,'1.01.01.0056','quarterly');annual,annualmeta=load_siat(544,'1.01.01.0001','annual')
    latest=transform(pd.Series(quarter.cumulative_nominal_gdp.to_numpy(),index=pd.PeriodIndex(quarter.quarter,freq='Q')))
    if latest.standalone_nominal_gdp.le(0).any():raise ValueError('Nonpositive standalone nominal GDP')
    latest['source_url']=meta['source_url'];latest['retrieved_at']=meta['retrieved_at'];latest['checksum']=meta['checksum']
    latest['raw_file_path']=meta['raw_file_path'];latest['dataset_update_date']=meta['dataset_update_date'];latest['source_release_date']=None
    latest['vintage_class']='LATEST_REVISED_SIAT_SNAPSHOT_NOT_HISTORICAL_RELEASE'
    years=[]
    for year,g in latest.groupby(pd.PeriodIndex(latest.index,freq='Q').year):
        complete=len(g)==4 and g.standalone_nominal_gdp.notna().all()
        official=annual.loc[annual.quarter.eq(str(year)),'cumulative_nominal_gdp']
        total=float(official.iloc[0]) if len(official) else np.nan
        flow_sum=float(g.standalone_nominal_gdp.sum()) if complete else np.nan
        passed=bool(complete and pd.notna(total) and np.isclose(flow_sum,total,atol=1e-6,rtol=0))
        years.append(dict(year=year,complete_year=complete,standalone_sum=flow_sum,official_annual_gdp=total,passed=passed,
            difference=flow_sum-total,annual_source_url=annualmeta['source_url'],annual_checksum=annualmeta['checksum']))
        if complete and not passed:raise ValueError('Nominal annual validation failed '+str(year))
    csv('annual_validation',years)
    csv('nominal_gdp_quarterly',latest[['quarter','cumulative_nominal_gdp','standalone_nominal_gdp','unit','quality_flag','source_url','retrieved_at','checksum','raw_file_path','dataset_update_date','source_release_date','vintage_class']])
    latest['nominal_gdp_ytd_yoy_log']=100*np.log(latest.cumulative_nominal_gdp/latest.cumulative_nominal_gdp.shift(4))
    latest['real_gdp_ytd_yoy_pct']=audit.set_index('quarter').model_target_value.reindex(latest.index)
    latest['real_gdp_ytd_yoy_log']=100*np.log1p(latest.real_gdp_ytd_yoy_pct/100)
    latest['implicit_YTD_price_log_growth']=latest.nominal_gdp_ytd_yoy_log-latest.real_gdp_ytd_yoy_log
    csv('nominal_gdp_growth',latest)
    events=evidence_events();csv('nominal_cumulative_vintage_events',events)
    actual_nominal=first_nominal_growth(events)
    gaps=[]
    for q in latest.index:
        f=events.loc[events.quarter.eq(q)]
        gaps.append(dict(quarter=q,nominal_publication_events=len(f),dated_nominal_level_recovered=bool(len(f)),
            nominal_growth_first_documented_date=actual_nominal.loc[q,'as_of_publication_date'] if q in actual_nominal.index else None,
            first_historical_release_proven=False,notes='Partial dated archive, not exhaustive first releases; no SIAT snapshot backdating'))
    csv('nominal_vintage_coverage',gaps)
    dataset=load_dataset(ROOT)
    panel=pd.read_csv(ROOT/'results/phase6c/phase6c_research_monthly_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip')
    real_events=pd.read_csv(ROOT/'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    frozen=pd.read_csv(ROOT/'results/phase6g/phase6g_origin_level_forecasts.csv',float_precision='round_trip')
    eligibility=pd.read_csv(ROOT/'results/phase6g/phase6g_origin_eligibility.csv')
    keys=eligibility.loc[eligibility.common_origin_eligible,['target_quarter','horizon']]
    info,origin,saved=production_info(ROOT);p,ds,av=frames(info,ROOT,origin)
    contexts=[]
    for r in keys.itertuples(index=False):
        o=horizon_month_end(r.target_quarter,r.horizon)
        a=sw.common.vintage_kernel().available_gdp_vintage_as_of(real_events,o,target=r.target_quarter,timing_rule='STRICT')
        old=frozen.loc[frozen.target_quarter.eq(r.target_quarter)&frozen.horizon.eq(r.horizon)&frozen.model.eq('S0')].iloc[0]
        contexts.append((r.target_quarter,r.horizon,o,panel,dataset,a,float(old.actual),float(old.prediction),False))
    production=json.loads((ROOT/'results/phase6e/phase6e_current_nowcast.json').read_text())
    contexts.append((info['target'],info['horizon'],origin,p,ds,av,np.nan,production['dfm_forecast'],True))
    forecasts=[];now=[];failures=[];origin_audits=[];bridge=[];loadings=[];training_usage=[];reproduction=[];factor_rows=[];cache={}
    for target,horizon,o,p,ds,a,realactual,expected,current in contexts:
        sw.common.vintage_kernel().assert_boundary(a,target)
        frame,spec,masks,end=design(p,ds,target,horizon,'M0')
        accepted,fitted=fit(frame,spec,end,a,target,o,cache)
        difference=accepted-expected
        reproduction.append(dict(target_quarter=target,horizon=horizon,current=current,prediction=accepted,frozen_prediction=expected,error=difference,passed=abs(difference)<1e-7))
        if abs(difference)>=1e-7:raise ValueError('Accepted DFM reproduction failed')
        nominal=targets_as_of(events,o,target)
        for q,r in nominal.to_dict('index').items():
            if pd.Timestamp(r['publication_date']).date()>=o.date() or q>=target:raise ValueError('Nominal GDP information leak')
            training_usage.append(dict(forecast_origin=str(o),target_quarter=target,horizon=horizon,current=current,quarter=q,**r))
        pred={};used=[]
        try:
            pred,bd,used=controlled_bridges(fitted,a,nominal,target)
            if not current and target not in actual_nominal.index:raise ValueError('Nominal target realization not documented')
            for model,prediction in pred.items():
                prior=str(pd.Period(target,'Q')-1)
                prior_value=float(nominal.loc[prior,'value']) if model.startswith('NOMINAL') else float(a.frame.value.loc[prior])
                if current:
                    now.append(dict(model=model,target_quarter=target,nowcast=prediction,unit='nominal standalone YoY log percent' if model.startswith('NOMINAL') else 'real cumulative YTD YoY percent',
                        status='RESEARCH_ONLY_PARTIAL_DOCUMENTED_TARGET_VINTAGES',forecast_origin=str(o),n_training_quarters=len(used)))
                else:
                    actual=float(actual_nominal.loc[target,'value']) if model.startswith('NOMINAL') else realactual
                    forecasts.append(dict(model=model,target_quarter=target,horizon=horizon,forecast_origin=str(o),prediction=prediction,actual=actual,
                        prior_growth=prior_value,actual_publication_date=actual_nominal.loc[target,'as_of_publication_date'] if model.startswith('NOMINAL') else None,
                        training_quarters=json.dumps(used),target_definition='standalone nominal log YoY' if model.startswith('NOMINAL') else 'cumulative real YoY percent'))
            bridge.extend(dict(target_quarter=target,horizon=horizon,current=current,**r) for r in bd)
        except (ValueError,KeyError,np.linalg.LinAlgError) as exc:
            failures.append(dict(target_quarter=target,horizon=horizon,current=current,error=str(exc)))
        origin_audits.append(dict(target_quarter=target,horizon=horizon,forecast_origin=str(o),current=current,controlled_estimable=bool(pred),
            n_training_quarters=len(used),DFM_training_start=str(frame.index.min()),DFM_training_months=len(frame.loc[:end]),
            same_factor_path=True,same_predictors=True,same_publication_masks=True,real_full_bridge_n=fitted['bridge_diagnostics']['n_GDP_quarters'],
            nominal_missing_quarters_removed_from_both_bridges=True,nominal_historical_value_archive_complete=False))
        for field,loading in zip(FIELDS,fitted['loadings']):
            loadings.append(dict(target_quarter=target,horizon=horizon,current=current,indicator=field,factor_loading=loading,
                loading_identical_for_both_targets=True,**fitted['diagnostics']))
        if current:
            now.append(dict(model='ACCEPTED_REAL_DFM',target_quarter=target,nowcast=accepted,unit='real cumulative YTD YoY percent',status='UNCHANGED_PRODUCTION_REFERENCE',forecast_origin=str(o)))
            factor_rows.extend(dict(date=str(t),factor=float(v)) for t,v in fitted['factors'].iloc[:,0].items())
        else:
            forecasts.append(dict(model='ACCEPTED_REAL_DFM',target_quarter=target,horizon=horizon,forecast_origin=str(o),prediction=accepted,actual=realactual,
                prior_growth=float(a.frame.value.loc[str(pd.Period(target,'Q')-1)]),target_definition='cumulative real YoY percent'))
        csv('origin_information_audit',origin_audits);csv('model_failures',failures)
        LOG.info('Completed %s %s current=%s nominal=%s',target,horizon,current,pred.get('NOMINAL_STANDALONE_LOG'))
    f=pd.DataFrame(forecasts);csv('all_attempted_forecasts',f)
    controls=['REAL_SHARED_BRIDGE','NOMINAL_STANDALONE_LOG','ACCEPTED_REAL_DFM']
    wide=f.pivot(index=['target_quarter','horizon'],columns='model',values='prediction')
    common=wide.reindex(columns=controls).dropna().index
    matched=f.set_index(['target_quarter','horizon']).loc[common].reset_index();csv('common_sample_forecasts',matched)
    metrics=scores(matched);csv('horizon_metrics',metrics)
    summary=metrics.loc[metrics.horizon.eq('POOLED')].copy()
    for h in ['H1','H2','H3']:
        summary=summary.merge(metrics.loc[metrics.horizon.eq(h),['model','RMSE']].rename(columns={'RMSE':h+'_RMSE'}),on='model')
    summary=summary.merge(pd.DataFrame(now)[['model','nowcast']],on='model',how='left');csv('target_model_comparison',summary)
    for name,key in [('U_MIDAS','umidas_forecast'),('COMBO_50_50','final_forecast')]:
        now.append(dict(model=name,target_quarter=info['target'],nowcast=production[key],unit='real cumulative YTD YoY percent',status='UNCHANGED_PRODUCTION_REFERENCE'))
    csv('current_nowcasts',now);csv('bridge_coefficients',bridge);csv('factor_loadings',loadings);csv('target_training_vintage_usage',training_usage);csv('reproduction',reproduction);csv('current_factor_series',factor_rows)
    errors=matched.copy();errors['error']=errors.actual-errors.prediction;errors['absolute_error']=errors.error.abs()
    csv('largest_historical_misses',errors.sort_values('absolute_error',ascending=False).groupby('model',sort=False).head(5))
    from scripts.phase6g3.diagnostics import economic_diagnostics
    diagnostics=economic_diagnostics(latest,panel,dataset,pd.DataFrame(factor_rows));csv('target_diagnostics',diagnostics)
    from scripts.phase6g3.report import write_report
    classification=write_report(audit,latest,summary,metrics,pd.DataFrame(now),pd.DataFrame(failures),diagnostics)
    count=verify()
    dump(OUT/'run_manifest.json',dict(classification=classification,research_only=True,production_unchanged=True,protected_hashes_identical=True,
        protected_artifacts=count,attempted_historical_origins=len(keys),matched_historical_origins=len(common),historical_nominal_archive_complete=False,
        raw_nominal_observations=len(latest),nominal_publication_events=len(events),current_cutoff=str(origin),automatic_promotion=False,failures=failures,
        factor_specification='unchanged accepted eight-predictor one-factor AR2 filtered DynamicFactorMQ; training-only standardization',
        controls='same factors/origins/window; both shared bridges use identical documented target-training quarters; accepted full real bridge retained separately',
        code_hashes={p.name:sha(p) for p in (ROOT/'scripts/phase6g3').glob('*.py')},
        inputs={p.relative_to(ROOT).as_posix():sha(p) for p in [saved,ROOT/meta['raw_file_path'],ROOT/annualmeta['raw_file_path'],ROOT/'results/research/phase6b2/phase6b2_gdp_revision_history.csv']},
        outputs={p.name:sha(p) for p in OUT.glob('*.csv')}))
    from scripts.phase6g3.finalize import main as finalize
    finalize()
    print(summary[['model','N','RMSE','normalized_RMSE','nowcast']].to_string(index=False))
    print(classification+'; production unchanged; protected files: '+str(count))


if __name__=='__main__':run()
