"""Refit frozen specifications, enforce reproduction, then evaluate ensembles.

Run: .venv/Scripts/python.exe -m scripts.phase6g.run
Only results/phase6g is written. No FDI data are read or fitted.
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import argparse
import json
import logging
import sys
import platform

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from scripts.phase6f.experiment import lagged_dfm, protected, sha, dump
from scripts.phase6e.models import dfm, umidas, frames, sw, FIELDS
from uznowcast.models.data import load_dataset, horizon_month_end, quarter_start, quarter_end, information_cutoff_for_variable
from scripts.phase6g import analysis as a

LOG=logging.getLogger('phase6g')
DESCRIPTIONS=dict(P0='Unchanged Phase6E COMBO_50_50',G1='50% M2-L1 DFM + 50% unchanged U-MIDAS',
    G2='50% M2-L2 DFM + 50% unchanged U-MIDAS',S0='Phase6E DFM',S1='Phase6F M2-L1 DFM',S2='Phase6F M2-L2 DFM',U0='Unchanged U-MIDAS USD/UZS')
HOLDOUT=['2025Q3','2025Q4','2026Q1','2026Q2']


def csv(out,name,frame):
    pd.DataFrame(frame).to_csv(out/f'phase6g_{name}.csv',index=False,float_format='%.17g')


def protect(root):
    hashes=protected(root)
    skip=('test_','t_','_pytest','__pycache__','browser_profile','validation_tmp','test_tmp','rerun')
    for folder in ['scripts/phase6f','results/phase6f','results/phase6e']:
        for p in (root/folder).rglob('*'):
            if p.is_file() and not any(s.startswith(skip) for s in p.relative_to(root/folder).parts):
                hashes[p.relative_to(root).as_posix()]=sha(p)
    return hashes


def check_protected(root,before,out):
    after={p:sha(root/p) if (root/p).is_file() else None for p in before}
    changed=[p for p,h in before.items() if after[p]!=h]
    dump(out/'phase6g_protected_after.json',after)
    if changed:raise ValueError('Protected artifacts changed: '+str(changed))
    return len(after)


def production_info(root):
    manifest=json.loads((root/'results/phase6e/phase6e_run_manifest.json').read_text())
    bundle=json.loads((root/'results/phase6d/phase6d_frozen_challengers.json').read_text())
    ledger=pd.read_csv(root/'results/phase6d/phase6d_prospective_forecast_ledger.csv')
    origin=pd.Timestamp(manifest['as_of']).tz_convert('Asia/Tashkent').tz_localize(None)
    for r in ledger.loc[ledger.model.eq('COMBO_50_50')].sort_values('run_timestamp_utc',ascending=False).itertuples():
        path=root/'results/phase6d/snapshots'/r.snapshot_id/'inputs.json'
        info=json.loads(path.read_text())
        if 'benchmark_monthly' in info and sw.fingerprint(info,bundle,r.operational_stage)==manifest['information_fingerprint']:
            return info,origin,path
    raise ValueError('Exact Phase6E production input snapshot unavailable')


def information_audit(panel,dataset,available,target,horizon,origin):
    k=sw.common.kernel()
    sw.common.vintage_kernel().assert_boundary(available,target)
    spec=k.Spec('DFM-4_R1_P2',FIELDS,1,2,'2019-01-31',True,False)
    masked,masks=k.mask(panel,spec,target,horizon,dataset.release_lag_days,'standard')
    nominal=horizon_month_end(target,horizon)
    rows=[]
    for r in masks:
        key=r['variable'];used=masked[key].dropna()
        lag=dataset.release_lag_days[key]
        passed=bool((used.index+pd.Timedelta(days=lag)<=nominal).all() and (used.index<=origin).all())
        rows.append(dict(forecast_origin=str(origin),target_quarter=target,horizon=horizon,variable=key,
            latest_reference_period=str(used.index.max().to_period('M')) if len(used) else None,
            assumed_lag_days=lag,assumed_availability_date=str(used.index.max()+pd.Timedelta(days=lag)) if len(used) else None,
            observed_historical_release_date=None,publication_mask_pass=passed,
            reference_timing_leakage=False if passed else True,revision_value_leakage_resolved=False,evidence_class=a.CAVEAT))
    fx=dataset.monthly['usd_uzs_mom_dlog'].dropna()
    cutoff=information_cutoff_for_variable(nominal,'usd_uzs',dataset.release_lag_days,'standard')
    fx=fx.loc[fx.index<=cutoff]
    fxpass=bool(len(fx)>=3 and (fx.tail(3).index<=origin).all())
    rows.append(dict(forecast_origin=str(origin),target_quarter=target,horizon=horizon,variable='umidas_usd_uzs',
        latest_reference_period=str(fx.index.max().to_period('M')) if len(fx) else None,
        assumed_lag_days=dataset.release_lag_days['usd_uzs'],assumed_availability_date=None,observed_historical_release_date=None,
        publication_mask_pass=fxpass,reference_timing_leakage=not fxpass,revision_value_leakage_resolved=False,evidence_class=a.CAVEAT))
    m2=next(r for r in rows if r['variable']=='m2')
    return dict(gdp_available=str(pd.Period(target,'Q')-1) in available.frame.index,
        m2_latest_reference_period=m2['latest_reference_period'],m2_publication_mask_pass=m2['publication_mask_pass'],
        gdp_information_boundary_pass=True,predictor_information_boundary_pass=all(r['publication_mask_pass'] for r in rows),
        gdp_latest_available_quarter=available.frame.index.max() if len(available.frame) else None,
        gdp_training_vintages=len(available.frame),revision_value_leakage_resolved=False,evidence_class=a.CAVEAT),rows


def fit_origin(panel,dataset,available,target,horizon,origin):
    """Unchanged Phase6E/6F estimators; independently preserve series failures."""
    values={};fits={};failures={}
    for model,lag in [('S0',0),('S1',1),('S2',2)]:
        try:
            pred,fit=dfm(panel,dataset,available,target,horizon,origin) if lag==0 else lagged_dfm(panel,dataset,available,target,horizon,origin,lag)
            values[model]=pred;fits[model]=fit
        except (ValueError,KeyError,np.linalg.LinAlgError) as exc:
            failures[model]=str(exc);values[model]=np.nan
    gated=replace(dataset,gdp=pd.DataFrame({'quarter':available.frame.index,dataset.target_field:available.frame.value.to_numpy()}))
    try:
        values['U0'],_,_=umidas(gated,available,target,horizon,origin)
    except (ValueError,KeyError,np.linalg.LinAlgError) as exc:
        values['U0']=np.nan;failures['U0']=str(exc)
    return a.ensembles(values['S0'],values['S1'],values['S2'],values['U0']),fits,failures


def factor_records(fits,target,horizon,origin,current=False):
    diagnostics=[];loads=[]
    reference=fits.get('S0',{}).get('factors')
    for model,fit in fits.items():
        factor=fit['factors'].iloc[:,0]
        common=factor.index.intersection(reference.index) if reference is not None else factor.index
        corr=factor.loc[common].corr(reference.iloc[:,0].loc[common]) if reference is not None else None
        sign=-1 if corr is not None and corr<0 else 1
        f=sign*factor
        end=quarter_start(target)-pd.Timedelta(days=1)
        transition=np.asarray(json.loads(fit['diagnostics']['transition']))
        diagnostic=dict(model=model,target_quarter=target,horizon=horizon,forecast_origin=str(origin),current=current,
            n_predictors=len(FIELDS),factor_count=1,factor_ar_order=2,n_monthly_parameters=2*len(FIELDS)+2,
            factor_correlation_vs_S0=abs(corr) if corr is not None else None,diagnostic_alignment_sign=sign,
            factor_std=float(f.loc[:end].std(ddof=1)),factor_persistence_lag1=float(f.loc[:end].autocorr(1)),
            factor_AR1=float(transition[0,0]),factor_AR2=float(transition[0,1]),
            missing_data_unstable=False,n_GDP_quarters=fit['bridge_diagnostics']['n_GDP_quarters'],
            status='SUCCESS',evidence_class=a.CAVEAT,**fit['diagnostics'])
        diagnostics.append(diagnostic)
        signed=np.asarray(fit['loadings'])*sign
        total=np.abs(signed).sum()
        for field,loading in zip(FIELDS,signed):
            base=float(fits['S0']['loadings'][list(FIELDS).index(field)]) if 'S0' in fits else None
            loads.append(dict(model=model,target_quarter=target,horizon=horizon,forecast_origin=str(origin),current=current,
                variable=field,loading=float(loading),absolute_loading_share_pct=float(100*abs(loading)/total),
                delta_loading_vs_S0=float(loading-base) if base is not None else None,diagnostic_alignment_sign=sign,
                interpretation='Sign-aligned measurement association; not causal contribution',evidence_class=a.CAVEAT))
    return diagnostics,loads


def benchmark_reproduction(root,out,panel,dataset,events):
    """STOP promotion analysis if any historical/current identity differs."""
    f=pd.read_csv(root/'results/phase6f/phase6f_quarter_level_forecasts.csv',float_precision='round_trip')
    f=f.loc[~f.current & f.model.isin(['M0','M1','M2'])]
    e=pd.read_csv(root/'results/phase6e/phase6e_matched_forecasts.csv',float_precision='round_trip')
    rows=[];forecasts=[];eligibility=[];diag=[];load=[];masks=[]
    for (target,horizon),g in f.groupby(a.KEYS):
        origin=horizon_month_end(target,horizon)
        av=sw.common.vintage_kernel().available_gdp_vintage_as_of(events,origin,target=target,timing_rule='STRICT')
        expected={m:float(g.loc[g.model.eq(old),'prediction'].iloc[0]) for m,old in [('S0','M0'),('S1','M1'),('S2','M2')]}
        block=e.loc[e.target_quarter.eq(target) & e.horizon.eq(horizon)]
        expected['U0']=float(block.loc[block.model.eq('U_MIDAS'),'prediction'].iloc[0])
        expected['P0']=float(block.loc[block.model.eq('COMBO_50_50'),'prediction'].iloc[0])
        expected['S0']=float(block.loc[block.model.eq('PHASE6C_DFM'),'prediction'].iloc[0])
        values,fits,failures=fit_origin(panel,dataset,av,target,horizon,origin)
        for model,wanted in expected.items():
            error=values[model]-wanted
            rows.append(dict(model=model,target_quarter=target,horizon=horizon,forecast_origin=str(origin),current=False,
                frozen=wanted,reconstructed=values[model],error=error,passed=bool(np.isfinite(error) and abs(error)<=1e-7),evidence_class=a.CAVEAT))
        csv(out,'reproduction_check',rows)
        if failures or not all(r['passed'] for r in rows):
            raise ValueError('Historical Phase6E/6F reproduction failed: '+str(failures))
        audit,mask=information_audit(panel,dataset,av,target,horizon,origin)
        eligibility.append(dict(target_quarter=target,horizon=horizon,forecast_origin=str(origin),
            dfm_current_available=True,dfm_m2_l1_available=True,dfm_m2_l2_available=True,umidas_available=True,
            common_origin_eligible=audit['gdp_available'] and audit['predictor_information_boundary_pass'],exclusion_reason='',**audit))
        masks+=mask
        actual=float(block.actual.iloc[0])
        forecasts += [dict(model=m,target_quarter=target,horizon=horizon,forecast_origin=str(origin),prediction=v,actual=actual,
            evaluation_period='ORIGINAL_HOLDOUT',evidence_class=a.CAVEAT) for m,v in values.items()]
        d,l=factor_records(fits,target,horizon,origin);diag+=d;load+=l
        LOG.info('REPRODUCED %s %s P0 %.9f G2 %.9f',target,horizon,values['P0'],values['G2'])
    info,origin,snapshot=production_info(root)
    p,ds,av=frames(info,root,origin)
    current,fits,failures=fit_origin(p,ds,av,info['target'],info['horizon'],origin)
    cf=pd.read_csv(root/'results/phase6f/phase6f_current_nowcasts.csv',float_precision='round_trip').set_index('model')
    for model,old in [('S0','M0'),('S1','M1'),('S2','M2'),('U0','U_MIDAS'),('P0','COMBO_50_50')]:
        wanted=float(cf.loc[old,'nowcast']);error=current[model]-wanted
        rows.append(dict(model=model,target_quarter=info['target'],horizon=info['horizon'],forecast_origin=str(origin),current=True,
            frozen=wanted,reconstructed=current[model],error=error,passed=bool(np.isfinite(error) and abs(error)<=1e-7),evidence_class=a.CAVEAT))
    csv(out,'reproduction_check',rows)
    if failures or not all(r['passed'] for r in rows):
        raise ValueError('Current reproduction failed: '+str(failures))
    d,l=factor_records(fits,info['target'],info['horizon'],origin,True);diag+=d;load+=l
    csv(out,'current_nowcasts',[dict(model=m,description=DESCRIPTIONS[m],target_quarter=info['target'],forecast_origin=str(origin),nowcast=v,
        delta_vs_P0=v-current['P0'],G2_revision_identity_error=(current['G2']-current['P0'])-.5*(current['S2']-current['S0']),
        status='UNCHANGED_PRODUCTION_REFERENCE' if m in ['S0','U0','P0'] else 'RESEARCH_CHALLENGER_ONLY',evidence_class=a.CAVEAT) for m,v in current.items()])
    dump(out/'phase6g_reproduction_gate.json',dict(passed=True,checks=len(rows),maximum_absolute_error=max(abs(r['error']) for r in rows),current_snapshot=str(snapshot.relative_to(root))))
    return forecasts,eligibility,diag,load,masks,current,snapshot


def extend(root,out,panel,dataset,events,records):
    forecasts,eligibility,diagnostics,loadings,masks=records
    registry=pd.read_csv(root/'results/research/phase6b2/phase6b2_gdp_vintage_registry.csv')
    targets=registry.loc[registry.first_release_value_verified & registry.release_date_verified & registry.quarter.lt('2025Q3') & registry.quarter.ge('2019Q1')]
    for r in targets.itertuples():
        for horizon in ['H1','H2','H3']:
            target=r.quarter;origin=horizon_month_end(target,horizon)
            av=sw.common.vintage_kernel().available_gdp_vintage_as_of(events,origin,target=target,timing_rule='STRICT')
            audit,mask=information_audit(panel,dataset,av,target,horizon,origin);masks+=mask
            # Same frozen minimum histories; no fabricated fallback GDP.
            months=len(pd.date_range('2019-01-31',quarter_start(target)-pd.Timedelta(days=1),freq='ME'))
            if months<36:
                failures={m:'Fewer than 36 training months under frozen 2019 start' for m in ['S0','S1','S2']}
                failures['U0']='Origin excluded at frozen DFM minimum-history precheck'
                values={m:np.nan for m in a.MODELS};fits={}
            else:
                values,fits,failures=fit_origin(panel,dataset,av,target,horizon,origin)
            common=all(np.isfinite(v) for v in values.values()) and audit['gdp_available'] and audit['gdp_information_boundary_pass'] and audit['predictor_information_boundary_pass']
            reason='; '.join(f'{m}: {why}' for m,why in failures.items())
            if not common and not reason:reason='Information boundary or missing prior GDP'
            eligibility.append(dict(target_quarter=target,horizon=horizon,forecast_origin=str(origin),
                dfm_current_available=np.isfinite(values['S0']),dfm_m2_l1_available=np.isfinite(values['S1']),dfm_m2_l2_available=np.isfinite(values['S2']),
                umidas_available=np.isfinite(values['U0']),common_origin_eligible=common,exclusion_reason=reason,**audit))
            forecasts += [dict(model=m,target_quarter=target,horizon=horizon,forecast_origin=str(origin),prediction=v,
                actual=float(r.first_release_value),evaluation_period='EARLIER_DEVELOPMENT',evidence_class=a.CAVEAT) for m,v in values.items()]
            d,l=factor_records(fits,target,horizon,origin);diagnostics+=d;loadings+=l
            # Save each excluded/successful origin and its reason immediately.
            csv(out,'origin_eligibility',eligibility)
            csv(out,'origin_level_forecasts',forecasts)
            LOG.info('EXTENSION %s %s eligible=%s P0=%s G2=%s failures=%s',target,horizon,common,values['P0'],values['G2'],reason[:180])
    # Unresolved first-release outcomes cannot be scored as newly invented actuals.
    unresolved=registry.loc[registry.quarter.ge('2019Q1') & registry.quarter.lt('2025Q3') &
        ~(registry.first_release_value_verified & registry.release_date_verified)]
    for r in unresolved.itertuples():
        for h in ['H1','H2','H3']:
            eligibility.append(dict(target_quarter=r.quarter,horizon=h,forecast_origin=str(horizon_month_end(r.quarter,h)),
                gdp_available=False,dfm_current_available=False,dfm_m2_l1_available=False,dfm_m2_l2_available=False,umidas_available=False,
                m2_latest_reference_period=None,m2_publication_mask_pass=False,gdp_information_boundary_pass=False,predictor_information_boundary_pass=False,
                common_origin_eligible=False,exclusion_reason='Verified first-release target outcome/date unresolved; no revised-target fallback',evidence_class=a.CAVEAT))


def calculate_outputs(out,forecasts,eligibility,current):
    full=pd.DataFrame(forecasts);elig=pd.DataFrame(eligibility).sort_values(a.KEYS)
    common=a.strict_common(full,elig)
    if common.empty:raise ValueError('No strict common-origin sample')
    metrics=[a.metric_rows(full,'FULL_AVAILABLE')]
    samples={'EXTENDED_COMMON':common,'ORIGINAL_HOLDOUT_COMMON':common.loc[common.target_quarter.isin(HOLDOUT)],
        'EARLIER_DEVELOPMENT_COMMON':common.loc[~common.target_quarter.isin(HOLDOUT)]}
    errors=[];corr=[];loo=[];wins=[];revisions=[];weights=[];boot=[]
    for sample,f in samples.items():
        if f.empty:continue
        metrics.append(a.metric_rows(f,sample))
        e=a.origin_errors(f,sample);errors.append(e)
        corr.append(a.correlations(e,sample));loo.append(a.leave_one_quarter_out(f,sample));wins.append(a.win_rates(e,sample))
        revisions.append(a.revisions(f,sample));weights.append(a.weights(e,sample));boot.append(a.bootstrap_quarters(e,sample))
    metric=pd.concat(metrics,ignore_index=True)
    tables={'horizon_metrics':metric,'origin_level_errors':pd.concat(errors),'error_correlations':pd.concat(corr),
        'leave_one_quarter_out':pd.concat(loo),'win_rates':pd.concat(wins),'revision_stability':pd.concat(revisions),
        'weight_sensitivity':pd.concat(weights),'statistical_diagnostics':pd.concat(boot),
        'origin_eligibility':elig,'origin_level_forecasts':full.sort_values(a.KEYS+['model'])}
    compare=[]
    for (sample,model),g in metric.groupby(['sample','model']):
        pool=g.loc[g.horizon.eq('POOLED')].iloc[0]
        h={r.horizon:r.RMSE for r in g.itertuples()}
        w=tables['win_rates'];wm=w.loc[w.model.eq(model)&w['sample'].eq(sample)&w.horizon.eq('POOLED')]
        compare.append(dict(model=model,description=DESCRIPTIONS[model],sample=sample,N=int(pool.N),H1_RMSE=h.get('H1'),H2_RMSE=h.get('H2'),H3_RMSE=h.get('H3'),
            pooled_RMSE=pool.RMSE,pooled_MAE=pool.MAE,bias=pool.bias,max_abs_error=pool.max_abs_error,OOS_R2=pool.OOS_R2,
            win_rate_vs_P0=float(wm.win_rate_pct.iloc[0]) if len(wm) else None,**{'2026Q3_nowcast':current[model]},
            delta_current_nowcast_vs_P0=current[model]-current['P0'],delta_RMSE_vs_P0=(pool.delta_RMSE_vs_benchmark if model in ['P0','G1','G2','U0'] else None),
            delta_RMSE_vs_S0=pool.delta_RMSE_vs_benchmark if model.startswith('S') else None,
            comparison_origin_N=int(pool.OOS_N),
            relative_RMSE_improvement_pct=pool.relative_RMSE_improvement_pct,metric_benchmark=pool.benchmark,
            status='RESEARCH_ONLY_AVAILABILITY_AWARE_NOT_FULL_VINTAGE_REAL_TIME',evidence_class=a.CAVEAT))
    tables['model_comparison']=pd.DataFrame(compare)
    for name,frame in tables.items():csv(out,name,frame)
    return tables,samples


def recommend(tables):
    """Predeclared checks; classify results without production mutations."""
    metrics=tables['horizon_metrics'];reasons=[];checks={}
    for sample in ['ORIGINAL_HOLDOUT_COMMON','EXTENDED_COMMON']:
        m=metrics.loc[metrics['sample'].eq(sample)].pivot(index='horizon',columns='model',values='RMSE')
        improvement=float(m.loc['POOLED','P0']-m.loc['POOLED','G2'])
        checks[sample+'_pooled_improvement']=improvement
        checks[sample+'_no_horizon_worsens']=bool((m.G2<=m.P0+1e-12).all())
        loo=tables['leave_one_quarter_out'];g=loo.loc[loo['sample'].eq(sample)&loo.model.eq('G2')&loo.horizon.eq('POOLED')]
        checks[sample+'_every_quarter_exclusion_improves']=bool(len(g) and g.delta_RMSE.lt(0).all())
        w=tables['win_rates'];rate=float(w.loc[w['sample'].eq(sample)&w.model.eq('G2')&w.horizon.eq('POOLED'),'win_rate_pct'].iloc[0])
        checks[sample+'_win_rate_pct']=rate
        rev=tables['revision_stability'];r=rev.loc[rev['sample'].eq(sample)].groupby('model').mean_abs_revision.mean()
        checks[sample+'_revision_ratio']=float(r.G2/r.P0) if r.P0>0 else None
    # Thresholds flag evidence; require both the original holdout and extension
    # to support a shadow recommendation. 25% revision deterioration is a
    # documented research governance screen, not a fitted parameter.
    strong=all(checks[s+'_pooled_improvement']>=.03 and checks[s+'_no_horizon_worsens'] and
        checks[s+'_every_quarter_exclusion_improves'] and checks[s+'_win_rate_pct']>=50 and
        (checks[s+'_revision_ratio'] is None or checks[s+'_revision_ratio']<=1.25) for s in ['ORIGINAL_HOLDOUT_COMMON','EXTENDED_COMMON'])
    if strong:
        classification='PHASE6G_M2L2_ENSEMBLE_IMPROVES';governance='ADVANCE_M2L2_TO_PHASE6H_SHADOW_PRODUCTION'
    elif checks['ORIGINAL_HOLDOUT_COMMON_pooled_improvement']>0 and checks['EXTENDED_COMMON_pooled_improvement']>0:
        classification='PHASE6G_INCONCLUSIVE';governance='KEEP_PHASE6E_PRODUCTION'
    else:
        m=metrics.loc[metrics['sample'].eq('EXTENDED_COMMON')&metrics.horizon.eq('POOLED')].set_index('model')
        if m.loc['G2','RMSE']>=m.loc['P0','RMSE'] and m.loc['S2','RMSE']<m.loc['S0','RMSE']:
            classification='PHASE6G_DFM_IMPROVES_BUT_ENSEMBLE_DOES_NOT'
        elif m.loc['P0','RMSE']-m.loc['G1','RMSE']>=.03 and m.loc['G1','RMSE']<m.loc['G2','RMSE']:
            classification='PHASE6G_M2L1_ENSEMBLE_IMPROVES'
        elif m.loc['G2','RMSE']>=m.loc['P0','RMSE'] and m.loc['G1','RMSE']>=m.loc['P0','RMSE']:
            classification='PHASE6G_NO_ENSEMBLE_IMPROVEMENT'
        else:classification='PHASE6G_INCONCLUSIVE'
        governance='KEEP_PHASE6E_PRODUCTION'
    return dict(classification=classification,recommendation=governance,automatic_promotion=False,checks=checks,
        reason='Controlled fixed-weight ensemble comparison; extended earlier origins overlap model development and are retrospective robustness evidence, not independent validation.',
        historical_M2_value_vintages_verified=False,evidence_class=a.CAVEAT)


def run(root=ROOT):
    out=root/'results/phase6g';out.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(out/'phase6g_pipeline.log',encoding='utf8'),logging.StreamHandler()])
    existing=out/'phase6g_protected_before.json'
    before=json.loads(existing.read_text()) if existing.exists() else protect(root)
    check_protected(root,before,out)
    dump(existing,before)
    dataset=load_dataset(root)
    panel=pd.read_csv(root/'results/phase6c/phase6c_research_monthly_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip')
    events=pd.read_csv(root/'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    inputs=[root/'results/phase6c/phase6c_research_monthly_panel.csv',root/'results/research/phase6b2/phase6b2_gdp_revision_history.csv',
        root/'results/research/phase6b2/phase6b2_gdp_vintage_registry.csv',root/'results/phase6e/phase6e_matched_forecasts.csv',
        root/'results/phase6f/phase6f_quarter_level_forecasts.csv',root/'results/phase6f/phase6f_current_nowcasts.csv',
        root/'data/master/v1_monthly.parquet',root/'data/master/gdp_quarterly.parquet',root/'registry/uzbekistan_nowcasting_v1.2_registry.xlsx']
    input_hashes={str(p.relative_to(root)):sha(p) for p in inputs}
    try:
        forecasts,elig,diag,loads,masks,current,snapshot=benchmark_reproduction(root,out,panel,dataset,events)
    except (ValueError,KeyError,AssertionError,np.linalg.LinAlgError) as exc:
        recommendation=dict(classification='PHASE6G_REPRODUCTION_FAILURE',recommendation='KEEP_PHASE6E_PRODUCTION',reason=str(exc),evidence_class=a.CAVEAT)
        dump(out/'phase6g_recommendation.json',recommendation)
        (out/'phase6g_results.md').write_text('Reproduction failed; promotion testing stopped.\n\n'+str(exc)+'\n\nPHASE6G_REPRODUCTION_FAILURE\n\nKEEP_PHASE6E_PRODUCTION\n',encoding='utf8')
        check_protected(root,before,out)
        dump(out/'phase6g_run_manifest.json',dict(status='PHASE6G_REPRODUCTION_FAILURE',inputs=input_hashes,production_modified=False))
        raise
    LOG.info('Reproduction gate PASSED; beginning earlier-origin extension')
    extend(root,out,panel,dataset,events,(forecasts,elig,diag,loads,masks))
    csv(out,'dfm_diagnostics',diag);csv(out,'factor_loadings',loads);csv(out,'predictor_availability',masks)
    tables,samples=calculate_outputs(out,forecasts,elig,current)
    recommendation=recommend(tables)
    dump(out/'phase6g_recommendation.json',recommendation)
    from scripts.phase6g.report import write_report
    write_report(out,tables,current,recommendation,diag)
    checked=check_protected(root,before,out)
    inputs.append(snapshot)
    for p in inputs:
        old=input_hashes.get(str(p.relative_to(root)))
        if old is not None and sha(p)!=old:raise ValueError('Inputs changed during experiment')
    input_hashes[str(snapshot.relative_to(root))]=sha(snapshot)
    dump(out/'phase6g_run_manifest.json',dict(status=recommendation['classification'],research_only=True,production_modified=False,
        input_hashes=input_hashes,protected_artifacts=checked,protected_hashes_unchanged=True,
        current_cutoff=str(pd.read_csv(out/'phase6g_current_nowcasts.csv').forecast_origin.iloc[0]),
        historical_origin_candidates=len(elig),common_origin_count=len(a.common_keys(samples['EXTENDED_COMMON'])),
        primary_holdout_origins=len(a.common_keys(samples['ORIGINAL_HOLDOUT_COMMON'])),
        historical_value_vintages_verified=False,evidence_class=a.CAVEAT,python=platform.python_version(),
        model_definition=dict(predictors=list(FIELDS),factor_count=1,factor_ar_order=2,bridge='intercept + factor_quarter_mean + GDP(q-1)',
            m2_transform='100*ln(level_t/level_t-12)',m2_publication_lag_days=dataset.release_lag_days['m2'],economic_lags=[0,1,2],weights=[.5,.5],FDI_included=False),
        outputs={p.name:sha(p) for p in out.glob('*.csv')},code_hashes={p.name:sha(p) for p in (root/'scripts/phase6g').glob('*.py')}))


if __name__=='__main__':run()
