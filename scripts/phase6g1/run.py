"""M2 dominance: exact preflight followed by three fixed controlled variants."""
from dataclasses import replace
from pathlib import Path
import json
import logging
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from scripts.phase6e.models import dfm,umidas,frames,sw,FIELDS
from scripts.phase6f.experiment import lagged_dfm,sha,dump
from scripts.phase6g.run import production_info,protect
from scripts.phase6g1 import diagnostics as d
from uznowcast.models.data import load_dataset,quarter_start,quarter_end,horizon_month_end

LOG=logging.getLogger('phase6g1')
MODELS=['D0','D1','D2','D3']
DESCRIPTIONS=dict(D0='Current nominal M2 DFM',D1='Seven-predictor DFM without M2',D2='Nominal M2 economic L2 DFM',D3='Real M2 YoY log growth DFM')


def csv(out,name,f):pd.DataFrame(f).to_csv(out/f'phase6g1_{name}.csv',index=False,float_format='%.17g')


def check_protected(root,out,before):
    after={p:sha(root/p) if (root/p).is_file() else None for p in before}
    dump(out/'phase6g1_protected_after.json',after)
    if before!=after:raise ValueError('Protected artifacts changed')


def generic_dfm(panel,dataset,available,target,horizon,origin,model,cpi):
    k=sw.common.kernel();p=panel.copy();fields=tuple(x for x in FIELDS if x!='m2') if model=='D1' else FIELDS
    if model=='D3':
        nominal=p.m2.mask(p.index+pd.Timedelta(days=dataset.release_lag_days['m2'])>horizon_month_end(target,horizon))
        cp=cpi.mask(cpi.index+pd.Timedelta(days=dataset.release_lag_days['cpi_headline'])>horizon_month_end(target,horizon))
        real,_=d.real_money(nominal,cp);p['m2']=real.reindex(p.index)
    spec=k.Spec(model,fields,1,2,'2019-01-31',True,False)
    frame,audit=k.mask(p,spec,target,horizon,dataset.release_lag_days,'standard')
    end=quarter_start(target)-pd.Timedelta(days=1)
    frame,_=k.training_panel(frame,end,True);z,mean,scale=k.standardize(frame,end,False)
    z=z.reindex(pd.date_range(z.index.min(),quarter_end(target),freq='ME'))
    factors,load,diag=k.estimate(z.loc[:end],z,spec,{})
    pred,bd=k.bridge(factors,available,target,origin,'B','mean')
    return pred,dict(frame=frame,z=z,means=mean,scales=scale,factors=factors,loadings=load[:,0],diagnostics=diag,bridge_diagnostics=bd)


def fit_control(panel,dataset,available,target,horizon,origin,model,cpi):
    if model=='D0':return dfm(panel,dataset,available,target,horizon,origin)
    if model=='D2':return lagged_dfm(panel,dataset,available,target,horizon,origin,2)
    return generic_dfm(panel,dataset,available,target,horizon,origin,model,cpi)


def fit_u(dataset,available,target,horizon,origin):
    gated=replace(dataset,gdp=pd.DataFrame({'quarter':available.frame.index,dataset.target_field:available.frame.value.to_numpy()}))
    return umidas(gated,available,target,horizon,origin)[0]


def current_signal_gate(root,out,fit,info,origin,transforms):
    dr=d.drivers(fit,'D0',info['target'],info['horizon'],origin,transforms,True)
    expected=pd.read_csv(root/'results/phase6e/phase6e_current_drivers.csv',float_precision='round_trip')
    m=dr.loc[dr.indicator.eq('m2')].iloc[0]
    old=expected.loc[expected.indicator.eq('m2')&expected.source_model.eq('PHASE6C_DFM')].iloc[0]
    if abs(m.descriptive_signal-old.contribution_or_signal)>1e-12 or abs(m.absolute_signal_share_pct-old.normalized_share_pct)>1e-10:
        raise ValueError('M2 descriptive signal/share reconstruction failure')
    loadold=pd.read_csv(root/'results/phase6e/phase6e_dfm_loadings.csv',float_precision='round_trip').set_index('indicator')
    if abs(m.absolute_loading_share_pct-loadold.loc['m2','normalized_loading_share_pct'])>1e-10:raise ValueError('Loading share reconstruction failure')
    raw=pd.read_parquet(root/'data/processed/m2.parquet').set_index('reference_period')
    z=fit['z'];q=z.loc[z.index.to_period('Q')==pd.Period(info['target'],'Q'),'m2'].dropna()
    denominator=float(dr.descriptive_signal.abs().sum(min_count=1));denominator_fields=dr.loc[dr.available_flag,'indicator'].tolist()
    rows=[]
    for month,value in q.items():
        r=raw.loc[str(month.to_period('M'))]
        prior=float(raw.loc[str(month.to_period('M')-12),'raw_value'])
        transformed=100*np.log(float(r.raw_value)/prior)
        if abs(transformed-float(fit['frame'].loc[month,'m2']))>1e-10:raise ValueError('M2 raw-to-transformed reconstruction failed')
        rows.append(dict(reference_period=str(month.to_period('M')),raw_M2_level=float(r.raw_value),raw_M2_year_ago=prior,raw_ratio=float(r.raw_value)/prior,
            recomputed_log_growth=float(transformed),raw_unit=r.raw_unit,
            transformed_value=float(fit['frame'].loc[month,'m2']),training_mean=m.training_mean,training_std=m.training_std,
            standardized_value=float(value),factor_loading=m.factor_loading,sign_alignment=fit['sign'],quarter_observations=len(q),
            quarter_mean_z=float(q.mean()),aggregation='mean of released target-quarter z-scores',signal_M2=m.descriptive_signal,
            latest_month_signal=float(q.iloc[-1]*m.factor_loading),absolute_signal_sum=denominator,signal_share_pct=m.absolute_signal_share_pct,
            loading_share_pct=m.absolute_loading_share_pct,denominator_indicators=json.dumps(denominator_fields),
            source_url=r.source_url,retrieved_at=r.retrieved_at,evidence_class=d.CAVEAT))
    csv(out,'m2_signal_reconstruction',rows)
    return dr


def preflight(root,out,panel,dataset,events,transforms):
    info,origin,snapshot=production_info(root);p,ds,av=frames(info,root,origin)
    pred,fit=dfm(p,ds,av,info['target'],info['horizon'],origin)
    # Reconstruct 0.726 BEFORE estimating a no-M2/real-M2 challenger.
    current_signal_gate(root,out,fit,info,origin,transforms)
    p2,fit2=lagged_dfm(p,ds,av,info['target'],info['horizon'],origin,2)
    u=fit_u(ds,av,info['target'],info['horizon'],origin)
    frozen=pd.read_csv(root/'results/phase6f/phase6f_current_nowcasts.csv',float_precision='round_trip').set_index('model')
    rows=[]
    for name,value,old in [('D0',pred,'M0'),('D2',p2,'M2'),('U_MIDAS',u,'U_MIDAS'),('E0',.5*pred+.5*u,'COMBO_50_50')]:
        error=value-float(frozen.loc[old,'nowcast'])
        rows.append(dict(check=name,scope='CURRENT',reconstructed=value,frozen=float(frozen.loc[old,'nowcast']),error=error,passed=abs(error)<1e-7,evidence_class=d.CAVEAT))
    current=dict(info=info,origin=origin,panel=p,dataset=ds,available=av,predictions={'D0':pred,'D2':p2},fits={'D0':fit,'D2':fit2},u=u,snapshot=snapshot)
    elig=pd.read_csv(root/'results/phase6g/phase6g_origin_eligibility.csv')
    keys=elig.loc[elig.common_origin_eligible,d.KEYS].sort_values(d.KEYS)
    old=pd.read_csv(root/'results/phase6g/phase6g_origin_level_forecasts.csv',float_precision='round_trip').set_index(d.KEYS+['model'])
    cache=[]
    for r in keys.itertuples(index=False):
        target,horizon=r;origin=horizon_month_end(target,horizon)
        av=sw.common.vintage_kernel().available_gdp_vintage_as_of(events,origin,target=target,timing_rule='STRICT')
        values={};fits={}
        for model,oldmodel in [('D0','S0'),('D2','S2')]:
            values[model],fits[model]=fit_control(panel,dataset,av,target,horizon,origin,model,None)
            expected=float(old.loc[(target,horizon,oldmodel),'prediction']);error=values[model]-expected
            rows.append(dict(check=model,scope='HISTORICAL',target_quarter=target,horizon=horizon,reconstructed=values[model],frozen=expected,error=error,passed=abs(error)<1e-7,evidence_class=d.CAVEAT))
        u=fit_u(dataset,av,target,horizon,origin);expected=float(old.loc[(target,horizon,'U0'),'prediction'])
        rows.append(dict(check='U_MIDAS',scope='HISTORICAL',target_quarter=target,horizon=horizon,reconstructed=u,frozen=expected,error=u-expected,passed=abs(u-expected)<1e-7,evidence_class=d.CAVEAT))
        actual=float(old.loc[(target,horizon,'P0'),'actual'])
        cache.append(dict(target=target,horizon=horizon,origin=origin,available=av,values=values,fits=fits,u=u,actual=actual))
        csv(out,'reproduction_check',rows)
        LOG.info('REPRODUCED %s %s',target,horizon)
    oldmetrics=pd.read_csv(root/'results/phase6g/phase6g_horizon_metrics.csv',float_precision='round_trip')
    for model,oldmodel in [('D0','S0'),('D2','S2'),('E0','P0'),('E2','G2')]:
        prediction=np.array([v['values'][model] if model.startswith('D') else .5*v['values']['D'+model[-1]]+.5*v['u'] for v in cache])
        actual=np.array([v['actual'] for v in cache]);rmse=float(np.sqrt(np.mean((actual-prediction)**2)))
        expected=float(oldmetrics.loc[oldmetrics['sample'].eq('EXTENDED_COMMON')&oldmetrics.horizon.eq('POOLED')&oldmetrics.model.eq(oldmodel),'RMSE'].iloc[0])
        rows.append(dict(check=model+'_RMSE',scope='EXTENDED_44',reconstructed=rmse,frozen=expected,error=rmse-expected,passed=abs(rmse-expected)<1e-12,evidence_class=d.CAVEAT))
    csv(out,'reproduction_check',rows)
    if not all(r['passed'] for r in rows):raise ValueError('Frozen Phase6E/6F/6G reconstruction failed')
    return current,cache


def audit_sources(root,out,current):
    obs=pd.read_parquet(root/'metadata/observations_long.parquet')
    pos=obs.loc[obs.variable_key.eq('pos_turnover')].copy()
    if len(pos):
        csv(out,'pos_audit',[dict(series='Canonical CBU archive POS',latest_repository_period=pos.reference_period.max(),latest_clean_period=pos.loc[pos.clean_value.notna(),'reference_period'].max(),
            latest_production_period='2024-12',newer_records_exist=True,
            diagnosis='INTENTIONAL_SCOPE_RESTRICTION; newer archive records are not verified as the same POS scope',
            evidence='scripts/research/phase6d/inputs.py lines 40-42: excludes post-2024-12 and requires scope_verified; scripts/operations/acquisition.py post-2024 scope guard',
            notes='Some canonical raw archive totals include BC/POS/ATM workbook scope; frozen verified POS-only extraction is retained. No silent replacement. Modern clean values also contain gaps/extreme-change flags.',evidence_class=d.CAVEAT)])
    overlap=pd.read_csv(root/'results/operations/source_validation_fix_industry_overlap.csv')
    lag=current['dataset'].release_lag_days['industrial_production']
    csv(out,'industrial_production_audit',[dict(reference_period=r.reference_period,official_raw_index=r.raw_value_live,clean_value=r.clean_value_live,
        source='Official SIAT 577 physical-volume index; native code 1.02.01.0004; national 1700',
        current_H3_available=pd.Period(r.reference_period,'M').to_timestamp('M')+pd.Timedelta(days=lag)<=horizon_month_end('2026Q3','H3'),
        assumed_lag_days=lag,nominal_H3_origin='2026-09-30',actual_frozen_cutoff=str(current['origin']),
        diagnosis='August exists (index 108, clean 8), but Aug31+33 days = Oct3 is after nominal H3 Sep30. Late initialization retains frozen H3 mask; no ingestion omission.',
        evidence='results/operations/source_validation_fix_industry_overlap.csv; source_validation_fix_report.md',
        notes='No September real-index observation is present in this approved 92-observation archived comparison; this does not establish live-source absence today.',evidence_class=d.CAVEAT)
        for r in overlap.loc[overlap.reference_period.ge('2026-07')].itertuples()])


def collect_fit(fit,model,target,horizon,origin,available,transforms,current=False,baseline=None):
    dr=d.drivers(fit,model,target,horizon,origin,transforms,current)
    f=fit['factors'].iloc[:,0];base=baseline['factors'].iloc[:,0] if baseline else f
    corr=f.corr(base);sign=-1 if corr<0 else 1
    end=quarter_start(target)-pd.Timedelta(days=1);train=f.loc[:end]*sign
    tr=np.asarray(json.loads(fit['diagnostics']['transition']))
    diag=dict(model=model,target_quarter=target,horizon=horizon,current=current,forecast_origin=str(origin),factor_correlation_vs_D0=abs(corr),
        diagnostic_alignment_sign=sign,factor_std=float(train.std(ddof=1)),factor_empirical_AR1=float(train.autocorr(1)),factor_min=float(train.min()),factor_max=float(train.max()),
        factor_AR2_L1=float(tr[0,0]),factor_AR2_L2=float(tr[0,1]),predictor_count=len(fit['frame'].columns),evidence_class=d.CAVEAT,**fit['diagnostics'])
    load=dr[['model','forecast_origin','target_quarter','horizon','current','indicator','factor_loading','absolute_loading_share_pct','evidence_class']].copy()
    load['factor_loading']*=sign;load['diagnostic_alignment_sign']=sign
    bridge=[dict(model=model,target_quarter=target,horizon=horizon,current=current,**r) for r in d.bridge_diagnostics(fit,available,target)]
    return dr,diag,load,bridge


def run(root=ROOT):
    out=root/'results/phase6g1';out.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(out/'phase6g1_pipeline.log',encoding='utf8'),logging.StreamHandler()])
    before=json.loads((out/'phase6g1_protected_before.json').read_text());check_protected(root,out,before)
    dataset=load_dataset(root);panel=pd.read_csv(root/'results/phase6c/phase6c_research_monthly_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip')
    events=pd.read_csv(root/'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    transforms={k:'Frozen Phase6E transformed predictor' for k in FIELDS}
    bundle=json.loads((root/'results/phase6d/phase6d_frozen_challengers.json').read_text())
    transforms.update({k:v['transformation'] for k,v in bundle['challengers']['PHASE6C_DFM']['transformations'].items() if k in FIELDS})
    try:current,cache=preflight(root,out,panel,dataset,events,transforms)
    except (ValueError,KeyError,AssertionError) as exc:
        dump(out/'phase6g1_recommendation.json',dict(classification='PHASE6G1_REPRODUCTION_FAILURE',recommendation='KEEP_CURRENT_DFM',reason=str(exc)))
        (out/'phase6g1_results.md').write_text('Reproduction failed. Interpretation stopped.\n\nPHASE6G1_REPRODUCTION_FAILURE\n',encoding='utf8')
        check_protected(root,out,before);raise
    LOG.info('Current signal and complete extended-history reproduction gate PASSED')
    cp=pd.read_parquet(root/'data/processed/cpi_headline.parquet');cp=cp.sort_values('reference_date').drop_duplicates('reference_period',keep='last')
    cpi=pd.Series(cp.clean_value.to_numpy(),index=pd.to_datetime(cp.reference_date))
    real,inflation=d.real_money(panel.m2,cpi)
    csv(out,'real_m2_observations',pd.DataFrame({'date':real.index,'real_M2_yoy':real,'CPI_yoy_log':inflation}).reset_index(drop=True))
    audit_sources(root,out,current)
    forecasts=[];drivers=[];diagnostics=[];loads=[];bridges=[];failures=[];correlations=[];now=[];availability=[]
    contexts=[dict(v,current=False,panel=panel,dataset=dataset) for v in cache]
    contexts.append(dict(target=current['info']['target'],horizon=current['info']['horizon'],origin=current['origin'],available=current['available'],
        values=current['predictions'],fits=current['fits'],u=current['u'],actual=np.nan,current=True,panel=current['panel'],dataset=current['dataset']))
    for ctx in contexts:
        target,horizon,origin=ctx['target'],ctx['horizon'],ctx['origin'];av=ctx['available'];values=ctx['values'];fits=ctx['fits']
        for model in ['D1','D3']:
            try:values[model],fits[model]=fit_control(ctx['panel'],ctx['dataset'],av,target,horizon,origin,model,cpi)
            except (ValueError,KeyError,np.linalg.LinAlgError) as exc:
                values[model]=np.nan;failures.append(dict(model=model,target_quarter=target,horizon=horizon,current=ctx['current'],reason=str(exc),evidence_class=d.CAVEAT))
        for model,value in values.items():
            ensemble=.5*value+.5*ctx['u']
            if ctx['current']:now.append(dict(model=model,DFM_nowcast=value,ensemble_nowcast=ensemble,difference_vs_production=ensemble-(.5*current['predictions']['D0']+.5*current['u']),
                status='AVAILABLE_RESEARCH_ONLY' if np.isfinite(value) else 'UNAVAILABLE',evidence_class=d.CAVEAT))
            else:
                for name,pred in [(model,value),('E'+model[-1],ensemble)]:
                    forecasts.append(dict(model=name,target_quarter=target,horizon=horizon,forecast_origin=str(origin),actual=ctx['actual'],prediction=pred,evidence_class=d.CAVEAT))
            if model not in fits:continue
            sw.common.vintage_kernel().assert_boundary(av,target)
            nominal=horizon_month_end(target,horizon)
            for field in fits[model]['frame']:
                observed=fits[model]['frame'][field].dropna().index
                source=(observed.to_period('M')-2).to_timestamp('M') if model=='D2' and field=='m2' else observed
                lag=ctx['dataset'].release_lag_days[field]
                passed=bool((source+pd.Timedelta(days=lag)<=nominal).all())
                cp_pass=True
                if model=='D3' and field=='m2':cp_pass=bool((source+pd.Timedelta(days=ctx['dataset'].release_lag_days['cpi_headline'])<=nominal).all())
                if not passed or not cp_pass:raise ValueError('Predictor publication timing leakage')
                availability.append(dict(model=model,target_quarter=target,horizon=horizon,current=ctx['current'],indicator=field,
                    latest_source_period=str(source.max().to_period('M')) if len(source) else None,publication_mask_pass=passed,
                    CPI_parent_mask_pass=cp_pass,GDP_boundary_pass=True,revision_value_leakage_resolved=False,evidence_class=d.CAVEAT))
            tr=dict(transforms)
            if model=='D2':tr['m2']='Economic L2 of released nominal YoY log M2'
            if model=='D3':tr['m2']='Nominal M2 YoY log minus twelve-month sum of monthly CPI log inflation; separately publication gated'
            dr,diag,ld,bd=collect_fit(fits[model],model,target,horizon,origin,av,tr,ctx['current'],fits['D0'])
            drivers.append(dr);diagnostics.append(diag);loads.append(ld);bridges+=bd
            if not ctx['current'] and model in ['D0','D2']:
                end=quarter_start(target)-pd.Timedelta(days=1);training=fits[model]['frame'].loc[:end]
                for key in training:
                    if key=='m2':continue
                    pair=training[['m2',key]].dropna()
                    correlations.append(dict(model=model,target_quarter=target,horizon=horizon,indicator=key,N=len(pair),correlation=pair.m2.corr(pair[key]),evidence_class=d.CAVEAT))
        csv(out,'model_failures',failures)
        LOG.info('AUDIT %s %s D1=%s D3=%s',target,horizon,values.get('D1'),values.get('D3'))
    all_drivers=pd.concat(drivers,ignore_index=True);conc=d.concentration(all_drivers)
    csv(out,'current_driver_comparison',all_drivers.loc[all_drivers.current]);csv(out,'historical_signal_shares',all_drivers.loc[~all_drivers.current])
    csv(out,'signal_concentration',conc);csv(out,'ragged_edge_analysis',conc.loc[conc.model.eq('D0')]);csv(out,'m2_zscores',conc.loc[conc.model.eq('D0')])
    csv(out,'factor_loadings',pd.concat(loads));csv(out,'factor_diagnostics',diagnostics);csv(out,'bridge_diagnostics',bridges)
    csv(out,'m2_correlations',correlations);csv(out,'current_nowcasts',now);csv(out,'origin_level_forecasts',forecasts)
    csv(out,'origin_availability',availability)
    from scripts.phase6g1.results import build_results
    recommendation=build_results(out,pd.DataFrame(forecasts),conc,all_drivers,pd.DataFrame(now),pd.DataFrame(diagnostics))
    check_protected(root,out,before)
    inputs=[root/'results/phase6c/phase6c_research_monthly_panel.csv',root/'results/phase6g/phase6g_origin_eligibility.csv',root/'results/phase6g/phase6g_origin_level_forecasts.csv',
        root/'results/research/phase6b2/phase6b2_gdp_revision_history.csv',root/'data/processed/cpi_headline.parquet',root/'data/processed/m2.parquet',current['snapshot']]
    dump(out/'phase6g1_run_manifest.json',dict(classification=recommendation['classification'],recommendation=recommendation['recommendation'],research_only=True,
        production_modified=False,protected_artifacts=len(before),protected_hashes_unchanged=True,evidence_class=d.CAVEAT,
        current_cutoff=str(current['origin']),principal_models=['D0','D1','D2'],D3_limited_CPI_history=True,
        cpi_publication_lag_days=dataset.release_lag_days['cpi_headline'],m2_publication_lag_days=dataset.release_lag_days['m2'],
        input_hashes={str(p.relative_to(root)):sha(p) for p in inputs},outputs={p.name:sha(p) for p in out.glob('*.csv')},
        code_hashes={p.name:sha(p) for p in (root/'scripts/phase6g1').glob('*.py')}))


if __name__=='__main__':run()
