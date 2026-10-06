"""Run only isolated research outputs: python -m scripts.phase6g4.run."""
from pathlib import Path
import sys,json,logging,os
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from scripts.phase6g4.core import MODELS,signals,design,fit
from scripts.phase6e.models import FIELDS,frames,sw
from scripts.phase6g.run import production_info,HOLDOUT
from scripts.phase6g2.run import hashes
from scripts.phase6f.experiment import sha,dump
from uznowcast.models.data import load_dataset,horizon_month_end
OUT=ROOT/'results/phase6g4'

def csv(name,rows):
    pd.DataFrame(rows).to_csv(OUT/f'phase6g4_{name}.csv',index=False,float_format='%.17g')

def protected():
    before=hashes()
    for folder in ['results/phase6g2','results/phase6g3','scripts/phase6g2','scripts/phase6g3','dashboard','config']:
        for base,dirs,files in os.walk(ROOT/folder):
            dirs[:]=[d for d in dirs if not d.startswith(('__pycache__','test','t_','validation','browser'))]
            for name in files:
                p=Path(base)/name;before[p.relative_to(ROOT).as_posix()]=sha(p)
    return before

def verify():
    before=json.loads((OUT/'phase6g4_protected_before.json').read_text())
    after={p:sha(ROOT/p) if (ROOT/p).is_file() else None for p in before}
    dump(OUT/'phase6g4_protected_after.json',after)
    if before!=after:raise ValueError('Protected artifacts changed')
    return len(before)

def run():
    OUT.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(OUT/'phase6g4_pipeline.log',encoding='utf8'),logging.StreamHandler()])
    dump(OUT/'phase6g4_protected_before.json',protected())
    ds=load_dataset(ROOT)
    rawm=pd.read_parquet(ROOT/'data/processed/m2.parquet')
    rawc=pd.read_parquet(ROOT/'data/processed/cpi_headline.parquet')
    def level(f):return pd.Series(f.raw_value.to_numpy(),index=pd.PeriodIndex(f.reference_period,freq='M').to_timestamp('M'))
    for f in [rawm,rawc]:
        for path,block in f.groupby('raw_file_path'):
            if set(block.checksum)!={sha(ROOT/path)}:raise ValueError('Source checksum mismatch')
    s=signals(level(rawm),level(rawc));csv('signals',s.rename_axis('date').reset_index())
    panel=pd.read_csv(ROOT/'results/phase6c/phase6c_research_monthly_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip')
    matched=pd.concat([panel.m2,s.nominal_m2],axis=1,sort=True).dropna()
    np.testing.assert_allclose(matched.iloc[:,0],matched.iloc[:,1],atol=1e-10,rtol=0)
    info,origin,snapshot=production_info(ROOT);cp,cds,av=frames(info,ROOT,origin)
    if pd.to_datetime(rawc.retrieved_at,utc=True).max()>origin.tz_localize('Asia/Tashkent').tz_convert('UTC'):
        raise ValueError('CPI snapshot postdates frozen current cutoff')
    events=pd.read_csv(ROOT/'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    frozen=pd.read_csv(ROOT/'results/phase6g/phase6g_origin_level_forecasts.csv',float_precision='round_trip')
    keys=pd.read_csv(ROOT/'results/phase6g/phase6g_origin_eligibility.csv').query('common_origin_eligible')[['target_quarter','horizon']]
    contexts=[]
    for q,h in keys.itertuples(index=False):
        o=horizon_month_end(q,h);a=sw.common.vintage_kernel().available_gdp_vintage_as_of(events,o,target=q,timing_rule='STRICT')
        old=frozen.loc[frozen.target_quarter.eq(q)&frozen.horizon.eq(h)&frozen.model.eq('S0')].iloc[0]
        contexts.append((q,h,o,panel,ds,a,old.actual,old.prediction,False))
    expected=json.loads((ROOT/'results/phase6e/phase6e_current_nowcast.json').read_text())['dfm_forecast']
    contexts.append((info['target'],info['horizon'],origin,cp,cds,av,np.nan,expected,True))
    forecasts=[];now=[];samples=[];loads=[];diags=[];audits=[];repro=[];drivers=[];sensitivity=[];cache={}
    for q,h,o,p,d,a,actual,expected,current in contexts:
        sw.common.vintage_kernel().assert_boundary(a,q)
        designs={};errors={}
        for model in MODELS:
            try:designs[model]=design(p,d,s,q,h,model)
            except ValueError as e:errors[model]=str(e)
        start=max((v[0].index.min() for v in designs.values()),default=None)
        for regime in ['NATIVE','COMMON']:
            base=None
            for model in MODELS:
                reason=errors.get(model,'')
                if regime=='COMMON' and errors:reason='At least one model lacks legitimate training history: '+json.dumps(errors)
                if reason:
                    samples.append(dict(sample=regime,model=model,target_quarter=q,horizon=h,current=current,status='DROPPED',reason=reason));continue
                frame,spec,audit,end=designs[model]
                if regime=='COMMON':frame=frame.loc[start:]
                try:
                    pred,f=fit(frame,spec,end,a,q,o,cache)
                    if model==MODELS[0]:base=f
                    if model==MODELS[0] and regime=='NATIVE':
                        delta=pred-expected;repro.append(dict(target_quarter=q,horizon=h,current=current,error=delta,passed=abs(delta)<1e-7))
                        if abs(delta)>=1e-7:raise RuntimeError('Benchmark reproduction failure')
                    common=dict(sample=regime,model=model,target_quarter=q,horizon=h,forecast_origin=str(o))
                    if current:
                        latest=lambda x:str(x.last_valid_index().to_period('M')) if x.last_valid_index() is not None else None
                        cutoff=horizon_month_end(q,h)
                        gated=s.mask(s.index.to_series()+pd.Timedelta(days=max(d.release_lag_days['m2'],d.release_lag_days['cpi_headline']))>cutoff)
                        cpi_used=s.cpi.mask(s.index+pd.Timedelta(days=d.release_lag_days['cpi_headline'])>cutoff)
                        now.append(dict(**common,nowcast_2026q3=pred,information_cutoff=str(o),stage_cutoff=str(cutoff),latest_m2=latest(frame.m2) if 'm2' in frame else None,latest_cpi=latest(cpi_used) if model!=MODELS[0] else None,latest_real_m2=latest(gated.real_m2),status='RESEARCH_ONLY'))
                        for field in [x for x in ['m2','cpi'] if x in frame]:
                            last=frame[field].last_valid_index()
                            if last is not None and last>end:
                                for direction in [-1,1]:
                                    shocked=frame.copy();shocked.loc[last,field]+=direction*f['scales'][field]
                                    value,_=fit(shocked,spec,end,a,q,o,cache)
                                    sensitivity.append(dict(**common,variable=field,reference_period=str(last.to_period('M')),shock_training_sd=direction,nowcast=value,change_pp=value-pred,training_parameters_unchanged=True))
                    else:forecasts.append(dict(**common,actual=actual,prediction=pred))
                    samples.append(dict(**common,current=current,status='OK',reason='',sample_start=str(frame.index.min()),sample_end=str(end),training_n=len(frame.loc[:end])))
                    corr=f['factors'].iloc[:,0].corr(base['factors'].iloc[:,0]) if base is not None else np.nan;sign=-1 if corr<0 else 1
                    ranking=pd.Series(abs(f['loadings']),index=frame.columns).rank(ascending=False,method='min')
                    for field,loading in zip(frame.columns,f['loadings']):
                        loads.append(dict(**common,current=current,variable='real_m2' if field=='m2' and model in MODELS[3:] else field,factor=1,loading=loading*sign,abs_loading=abs(loading),rank=ranking[field]))
                        if current:
                            zq=f['z'].loc[f['z'].index.to_period('Q')==pd.Period(q,'Q'),field].dropna()
                            drivers.append(dict(**common,variable=field,months=len(zq),descriptive_signal=loading*zq.mean(),interpretation='loading times quarterly mean z; not additive GDP contribution'))
                    diags.append(dict(**common,current=current,factor_correlation_vs_M0=abs(corr),**f['diagnostics']))
                    for row in audit:audits.append(dict(**common,current=current,**{k:v for k,v in row.items() if k not in common}))
                except ValueError as e:samples.append(dict(sample=regime,model=model,target_quarter=q,horizon=h,current=current,status='DROPPED',reason=str(e)))
        csv('origin_forecasts',forecasts);csv('sample_comparison',samples)
        logging.info('Completed %s %s current=%s',q,h,current)
    csv('current_nowcasts',now);csv('factor_loadings',loads);csv('dfm_diagnostics',diags);csv('information_audit',audits);csv('reproduction',repro);csv('current_drivers',drivers);csv('recent_sensitivity',sensitivity)
    n=verify()
    dump(OUT/'phase6g4_run_manifest.json',dict(protected_count=n,production_unchanged=True,automatic_promotion=False,historical_predictor_vintages_verified=False,
        snapshot=str(snapshot.relative_to(ROOT)),target='unchanged gdp_real_yoy_pct; SIAT real YTD YoY index minus 100',fields=list(FIELDS),
        cpi_audit='No direct CPI; PPI is present',m2_transformation='100*ln(M2_t/M2_t-12)',cpi_transformation='100*ln(chained_CPI_t/chained_CPI_t-12)',
        cpi_base='January 2021 chained level = official January previous-month index /100; arbitrary normalization',
        cpi_source=rawc.source_url.iloc[0],m2_source=rawm.source_url.iloc[0],cpi_notes=rawc.source_notes.iloc[0],
        release_lags=ds.release_lag_days,cutoff=str(origin),input_hashes={str(p.relative_to(ROOT)):sha(p) for p in [snapshot,ROOT/'data/processed/m2.parquet',ROOT/'data/processed/cpi_headline.parquet',ROOT/'results/research/phase6b2/phase6b2_gdp_revision_history.csv',ROOT/'results/phase6c/phase6c_research_monthly_panel.csv']}))
    from scripts.phase6g4.report import generate
    generate()

if __name__=='__main__':run()
