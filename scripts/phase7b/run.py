"""Offline Phase 7B: python -m scripts.phase7b.run. Writes research paths only."""
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone
import sys,json,hashlib,logging
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'src'))
from scripts.phase7b.data import parse,transform,COLUMNS,match,descriptive_diagnostics
from scripts.phase7b.models import SPECS,estimate
from scripts.phase6i.run import current_inputs
from scripts.production.models import dfm,umidas,fit_info,sw
from uznowcast.models.data import load_dataset
OUT=ROOT/'results/phase7b';DATA=ROOT/'data/research/satellite'
LOG=logging.getLogger('phase7b')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,f):f.to_csv(OUT/name,index=False,float_format='%.17g')
def protect():
    import os
    paths=[]
    for folder in ['src','scripts','config','registry','data','metadata','dashboard','results','docs']:
        for directory,dirs,files in os.walk(ROOT/folder):
            dirs[:]=[d for d in dirs if d!='__pycache__' and not d.startswith(('pytest_tmp','tmp','.' ))]
            for name in files:
                p=Path(directory)/name;rel=p.relative_to(ROOT).as_posix()
                if p.suffix!='.pyc' and not rel.startswith(('scripts/phase7b/','results/phase7b/','data/research/satellite/')):paths.append(p)
    LOG.info('Hashing %d protected scientific files (excluding test temporary directories)',len(paths))
    from concurrent.futures import ThreadPoolExecutor
    result={}
    def checksum(p):return str(p.relative_to(ROOT)),sha(p)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i,(p,h) in enumerate(pool.map(checksum,paths)):
            result[p]=h
            if i%1000==0:LOG.info('Hashed %d/%d',i,len(paths))
    return result
def audit(f):
    expected=pd.date_range('2014-01-31','2026-08-31',freq='ME')
    counts=f.count().to_dict()
    valid=f.index.equals(expected) and counts==dict(radiance=152,NDVI=152,EVI=152,NO2=99) and f.NO2.first_valid_index()==pd.Timestamp('2018-06-30')
    invalid=(f.radiance.le(0)|f.NO2.dropna().le(0).reindex(f.index,fill_value=False)|f.NDVI.abs().gt(1)|f.EVI.abs().gt(1))
    coverage=[]
    for c in COLUMNS:
        for date,value in f[c].items():coverage.append(dict(date=str(date.to_period('M')),indicator=c,observed=pd.notna(value),value=value,quality_flag='INVESTIGATE_RANGE' if invalid.loc[date] else ('MISSING' if pd.isna(value) else 'SOURCE_METADATA_UNVERIFIED')))
    save('satellite_coverage.csv',pd.DataFrame(coverage));save('satellite_descriptive_statistics.csv',f.describe().T.reset_index(names='indicator'))
    save('satellite_correlations.csv',f.corr().reset_index(names='indicator'))
    monthly=f.groupby(f.index.month).mean();save('satellite_seasonality.csv',monthly.reset_index(names='calendar_month'))
    yearly=f.groupby(f.index.year).mean();save('satellite_annual_means.csv',yearly.reset_index(names='year'))
    jumps=100*np.log(f.radiance/f.radiance.shift());med=jumps.median();mad=(jumps-med).abs().median()
    flags=pd.DataFrame({'date':f.index.strftime('%Y-%m'),'radiance_log_mom':jumps.to_numpy(),'radiance_jump_flag':((jumps-med).abs()>6*1.4826*mad).to_numpy(),'range_flag':invalid.to_numpy()})
    for c in COLUMNS:
        s=f[c];m=s.median();d=(s-m).abs().median();flags[c+'_outlier_flag']=((s-m).abs()>6*1.4826*d).to_numpy()
    save('satellite_quality_flags.csv',flags)
    text=f'''# Satellite data audit\n\nSOURCE_METADATA_UNVERIFIED; historical satellite vintages unverified. CSV supplied by colleague; no substitute downloaded.\n\nCoverage contract: {valid}. {len(f)} chronological months, {f.index.min():%Y-%m}–{f.index.max():%Y-%m}. Nonmissing counts: {counts}. NO2 begins {f.NO2.first_valid_index():%Y-%m}; earlier missing values remain null. Numeric parsing rejects malformed cells and infinities; duplicate months fail. Range investigation flags: {int(invalid.sum())}. NDVI/EVI working screening interval [-1,1] is provisional until products and units are confirmed. NO2 units remain unknown; no unsupported physical upper bound imposed.\n\nNDVI/EVI correlation: {f.NDVI.corr(f.EVI):.6f}, computed on aligned nonmissing months. EVI is tested separately.\n\nRadiance jumps flagged using a descriptive six-MAD threshold: {int(flags.radiance_jump_flag.sum())}. These full-sample audit thresholds are never used for model fitting. Values are retained. Annual means around 2016–2017: {yearly.loc[2015:2018,'radiance'].to_dict()}. Changes can reflect processing, cloud/snow contamination or economic activity; no causal or sensor-change claim is established. Review flagged months against product documentation.\n\nMonthly climatology and annual means describe seasonality/trends in satellite_seasonality.csv and satellite_annual_means.csv; seasonal patterns must not be interpreted as GDP changes. Correlation matrix, descriptive statistics and all observation-level flags are preserved. Sensor processing discontinuities cannot be verified without product versions.\n\nNeeded from colleague: sensor/product identifiers and versions, units/scales, polygon and geographic weighting, cloud/snow masks and quality filters, compositing and aggregation code, calibration changes (particularly 2016–2017), extraction date, original source links, revision history and historical first-publication dates.\n'''
    (OUT/'satellite_data_audit.md').write_text(text,encoding='utf8')
    if not valid or invalid.any():raise ValueError('Satellite coverage/range validation failed; see audit')
    return counts

def metrics(g,ar):
    g=g.loc[g.prediction.notna()&g.actual.notna()];e=g.actual-g.prediction
    sst=((g.actual-g.actual.mean())**2).sum();sse=(e**2).sum()
    g=g.copy();ar=ar.copy();g['origin']=pd.to_datetime(g.origin,format='mixed');ar['origin']=pd.to_datetime(ar.origin,format='mixed')
    a=g.merge(ar[['origin','target_quarter','horizon','prediction']],on=['origin','target_quarter','horizon'],suffixes=('','_ar'),validate='many_to_one');den=((a.actual-a.prediction_ar)**2).sum()
    return dict(n_origins=len(g),n_quarters=g.target_quarter.nunique(),rmse=np.sqrt((e**2).mean()),mae=e.abs().mean(),bias=e.mean(),r_squared=1-sse/sst if sst>0 else np.nan,oos_r_squared_ar1=1-((a.actual-a.prediction)**2).sum()/den if len(a)==len(g) and den>0 else np.nan,first_quarter=g.target_quarter.min() if len(g) else None,last_quarter=g.target_quarter.max() if len(g) else None)

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(OUT/'pipeline.log',mode='w',encoding='utf8')])
    path=DATA/'input/uzbekistan_nightlights_monthly.csv'
    if not path.exists():raise FileNotFoundError('Place colleague CSV at '+str(path))
    before=json.loads((OUT/'protection_baseline.json').read_text()) if '--resume-protection' in sys.argv else protect();(OUT/'protection_baseline.json').write_text(json.dumps(before));original=sha(path);archive=DATA/'raw'/original/'uzbekistan_nightlights_monthly.csv';archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():
        with archive.open('xb') as h:h.write(path.read_bytes())
    if sha(archive)!=original:raise ValueError('Immutable archive mismatch')
    (archive.parent/'sha256.txt').write_text(original+'\n',encoding='ascii') if not (archive.parent/'sha256.txt').exists() else None
    f=parse(path);counts=audit(f);descriptive_diagnostics(f,OUT);sat=transform(f);sat.to_csv(DATA/'satellite_transformed_monthly.csv',index_label='date',float_format='%.17g')
    (DATA/'transformation_definitions.json').write_text(json.dumps({'NTL_YOY':'100 ln(radiance_t/radiance_t-12), positive pairs only','NO2_YOY':'100 ln(NO2_t/NO2_t-12), positive pairs only','NDVI_YOY_DIFF':'NDVI_t-NDVI_t-12','EVI_YOY_DIFF':'EVI_t-EVI_t-12','NTL_SEASONAL_DIFF':'radiance_t-radiance_t-12','seasonal_anomaly':'level minus expanding same-calendar-month mean of strictly earlier years, >=3 prior measurements','availability':'reference month end plus lag calendar months; hypothetical, not observed publication','winsorization':'R3 only: training-window 1%/99% satellite thresholds'},indent=2))
    dataset=load_dataset(ROOT);current=current_inputs(dataset);cd,ca,info,co,frozen,snapshot=current
    fit=fit_info(info,ROOT,co)
    check={k:dict(recomputed=fit[k],frozen=frozen[v],error=fit[k]-frozen[v]) for k,v in [('dfm','dfm_forecast'),('umidas','umidas_forecast'),('final','final_forecast')]}
    if any(abs(v['error'])>1e-12 for v in check.values()):raise ValueError('Production reproduction failed')
    (OUT/'production_reproduction.json').write_text(json.dumps(check,indent=2))
    panel=pd.read_csv(ROOT/'data/current/historical_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip')
    events=pd.read_csv(ROOT/'data/current/gdp_vintages.csv')
    source=pd.read_csv(ROOT/'results/diagnostics/historical_forecasts.csv',float_precision='round_trip')
    origins=source.loc[source.model.eq('UMIDAS_USD')&source.lag_mode.eq('standard')&source.timing_rule.eq('STRICT')&source.prediction.notna()].copy()
    baseline_origins=source.loc[source.model.eq('DFM-4_R1_P2__BRIDGE_B_mean')&source.lag_mode.eq('standard')&source.timing_rule.eq('STRICT')&source.prediction.notna(),['target_quarter','horizon']]
    origins=origins.merge(baseline_origins,on=['target_quarter','horizon'],validate='one_to_one')
    save('phase7b_origin_exclusions.csv',source.loc[source.model.eq('DFM-4_R1_P2__BRIDGE_B_mean')&source.lag_mode.eq('standard')&source.timing_rule.eq('STRICT')&source.prediction.isna(),['target_quarter','horizon','failure']])
    ar=source.loc[source.model.eq('AR1')&source.lag_mode.eq('standard')&source.timing_rule.eq('STRICT')].rename(columns={'forecast_origin_date':'origin'})
    LOG.info('Verified data: %s; historical origins %d',counts,len(origins))
    predictions=[];loads=[];signals=[];factors=[];failures=[];reproduction=[]
    jobs=[(r,False) for r in origins.to_dict('records')]+[(dict(target_quarter=info['target'],horizon=info['horizon'],forecast_origin_date=str(co),actual=np.nan,evaluation_group='CURRENT'),True)]
    for row,iscurrent in jobs:
        target,horizon,origin=row['target_quarter'],row['horizon'],pd.Timestamp(row['forecast_origin_date'])
        gdp=ca if iscurrent else sw.common.vintage_kernel().available_gdp_vintage_as_of(events,origin,target=target,timing_rule='STRICT')
        sw.common.vintage_kernel().assert_boundary(gdp,target)
        ds=cd if iscurrent else replace(dataset,gdp=pd.DataFrame({'quarter':gdp.frame.index,dataset.target_field:gdp.frame.value.to_numpy()}))
        p=fit['panel'] if iscurrent else panel
        if iscurrent:d,u,basef=fit['dfm'],fit['umidas'],fit['dfit']['factors']
        else:
            d,bfit=dfm(p,ds,gdp,target,horizon,origin);basef=bfit['factors'];u,_,_=umidas(ds,gdp,target,horizon,origin)
            for model,val in [('PHASE6C_DFM',d),('UMIDAS_USD',u)]:
                ref=source.loc[source.model.eq('DFM-4_R1_P2__BRIDGE_B_mean' if model=='PHASE6C_DFM' else model)&source.target_quarter.eq(target)&source.horizon.eq(horizon)&source.lag_mode.eq('standard')&source.timing_rule.eq('STRICT'),'prediction']
                if len(ref)!=1 or abs(val-float(ref.iloc[0]))>1e-7:raise ValueError('Historical baseline reproduction failed '+target+horizon+model)
                reproduction.append(dict(target_quarter=target,horizon=horizon,model=model,recomputed=val,frozen=float(ref.iloc[0]),error=val-float(ref.iloc[0])))
        for lag in range(4):
            scenario='REVISED_DATA_EXPLORATORY' if lag==0 else f'ASSUMED_LAG_{lag}M'
            common=dict(origin=str(origin),target_quarter=target,horizon=horizon,scenario=scenario,lag_months=lag,actual=row['actual'],evaluation_group=row['evaluation_group'])
            for m,v in [('M0',d),('U0',u),('C0',.5*d+.5*u)]:predictions.append(dict(common,model=m,prediction=v,failure=None))
            independent={}
            for m,fields in SPECS.items():
                if m in ['R1','R2','R3'] and lag:continue
                reason=None;pred=np.nan
                try:
                    if m=='S4' and not independent.get('S1',False) or m=='S4' and not independent.get('S2',False):raise ValueError('Independent S1/S2 not estimable')
                    if m=='S5' and not independent.get('S1',False) or m=='S5' and not independent.get('S3',False):raise ValueError('Independent S1/S3 not estimable')
                    pred,diag,fac,loading,z=estimate(p,ds,gdp,target,horizon,origin,sat,fields,lag,m=='R3')
                    for field,l in zip(z.columns,loading):
                        loads.append(dict(common,model=m,indicator=field,loading=l,n_training_months=diag['n_training_months'],n_GDP_quarters=diag['n_GDP_quarters']))
                        for date,value in z[field].loc[z.index.to_period('Q')==pd.Period(target,'Q')].items():signals.append(dict(common,model=m,indicator=field,date=str(date.date()),standardized_value=value,loading_signal=l*value,units='standardized descriptive; not GDP pp'))
                    aligned=fac.iloc[:,0].to_frame('challenger').join(basef.iloc[:,0].rename('baseline')).dropna()
                    corr=aligned.corr().iloc[0,1];sign=1 if corr>=0 else -1
                    factors.append(dict(common,model=m,absolute_factor_correlation=abs(corr),aligned_factor_rmse=np.sqrt(((aligned.challenger*sign-aligned.baseline)**2).mean()),n_aligned_months=len(aligned)))
                    for date,value in fac.iloc[:,0].items():
                        if iscurrent and lag==0:factors.append(dict(common,model=m,date=str(date.date()),factor_value=value*sign,units='descriptive filtered factor'))
                    independent[m]=True
                except ValueError as e:
                    reason=str(e);independent[m]=False;failures.append(dict(common,model=m,reason=reason));LOG.info('%s %s %s %s: %s',target,horizon,scenario,m,reason[:100])
                predictions.append(dict(common,model=m,prediction=pred,failure=reason))
                if m.startswith('S'):predictions.append(dict(common,model='C'+m[1:],prediction=.5*pred+.5*u,failure=reason))
            LOG.info('Completed %s %s %s',target,horizon,scenario)
            save('phase7b_historical_predictions.csv',pd.DataFrame(predictions).loc[lambda x:x.evaluation_group.ne('CURRENT')])
    allf=pd.DataFrame(predictions);historical=allf.loc[allf.evaluation_group.ne('CURRENT')];cur=allf.loc[allf.evaluation_group.eq('CURRENT')].copy();cur['status']='RESEARCH ONLY; VINTAGE UNVERIFIED';cur.loc[cur.model.isin(['M0','U0','C0']),'status']='FROZEN PRODUCTION REFERENCE'
    save('phase7b_current_nowcasts.csv',cur);save('phase7b_factor_loadings.csv',pd.DataFrame(loads));save('phase7b_factor_signals.csv',pd.DataFrame(signals));save('phase7b_factor_stability.csv',pd.DataFrame(factors));save('phase7b_failures.csv',pd.DataFrame(failures));save('historical_baseline_reproduction.csv',pd.DataFrame(reproduction))
    comparison=[];hmetrics=[];robust=[]
    for scenario,block in historical.groupby('scenario'):
        for challenger in [*SPECS,*['C'+m[1:] for m in SPECS if m.startswith('S')]]:
            if challenger not in block.model.unique():continue
            bm='C0' if challenger.startswith('C') else 'M0'
            keys=match(block,[bm,challenger]);selected=block.merge(keys,on=['origin','target_quarter','horizon','scenario'],validate='many_to_one')
            for sample,b in [('MATCHED',selected),('FULL_AVAILABLE',block)]:
                for model in [bm,challenger]:
                    g=b.loc[b.model.eq(model)]
                    comparison.append(dict(scenario=scenario,comparison=challenger,sample=sample,model=model,**metrics(g,ar)))
                    if sample=='MATCHED':
                        for h in ['H1','H2','H3']:hmetrics.append(dict(scenario=scenario,comparison=challenger,model=model,horizon=h,**metrics(g.loc[g.horizon.eq(h)],ar)))
            matched=selected.loc[selected.model.isin([bm,challenger])]
            qs=sorted(matched.target_quarter.unique());mid=len(qs)//2
            for label,qset in [('EARLY',qs[:mid]),('RECENT',qs[mid:])]+[('LOQO_EXCLUDE_'+q,[v for v in qs if v!=q]) for q in qs]:
                for model in [bm,challenger]:robust.append(dict(scenario=scenario,comparison=challenger,subset=label,model=model,**metrics(matched.loc[matched.model.eq(model)&matched.target_quarter.isin(qset)],ar)))
    comp=pd.DataFrame(comparison);save('phase7b_model_comparison.csv',comp);save('phase7b_horizon_metrics.csv',pd.DataFrame(hmetrics));save('phase7b_lag_sensitivity.csv',comp.loc[comp['sample'].eq('MATCHED')]);save('phase7b_robustness.csv',pd.DataFrame(robust))
    aligned=panel.join(sat);save('satellite_economic_correlations.csv',aligned.corr().loc[sat.columns,panel.columns].reset_index(names='satellite_indicator'));save('satellite_economic_correlation_counts.csv',pd.DataFrame([dict(satellite_indicator=s,economic_indicator=e,n_aligned=int(aligned[[s,e]].dropna().shape[0])) for s in sat for e in panel]))
    from concurrent.futures import ThreadPoolExecutor
    LOG.info('Verifying protected files after experiment')
    def unchanged(item):
        p,h=item;return p if not (ROOT/p).is_file() or sha(ROOT/p)!=h else None
    with ThreadPoolExecutor(max_workers=8) as pool:changed=[p for p in pool.map(unchanged,before.items()) if p]
    if changed or sha(path)!=original:raise ValueError('Protected data changed: '+str(changed))
    manifest=dict(classification='PHASE7B_SATELLITE_INCONCLUSIVE',provenance='SOURCE_METADATA_UNVERIFIED',satellite_vintages='VINTAGE UNVERIFIED',source_sha256=original,source_url=None,source_release_date=None,sensor_product=None,measurement_units=None,archive=str(archive.relative_to(ROOT)),counts=counts,protected_artifacts_verified=True,protected_file_count=len(before),protected_hashes=before,production_reproduction=check,snapshot=snapshot,forecast_cutoff=str(co),run_timestamp=datetime.now(timezone.utc).isoformat(),n_historical_origins=len(origins),GDP_vintage_rule='STRICT unchanged existing vintage kernel',origin_rule='existing H1/H2/H3; reference month end plus assumed calendar-month delay for satellite',production_nowcast=frozen['final_forecast'])
    from scripts.phase7b.sample_control import run as history_control
    history_control()
    from scripts.phase7b.report import report
    report(f,sat,comp,pd.DataFrame(hmetrics),historical,cur,pd.DataFrame(loads),pd.DataFrame(signals),pd.DataFrame(robust),manifest)
    manifest['output_sha256']={p.name:sha(p) for p in OUT.glob('*') if p.is_file() and p.name not in ['run_manifest.json','pipeline.log']}
    (OUT/'run_manifest.json').write_text(json.dumps(sw.common.safe(manifest),indent=2,allow_nan=False),encoding='utf8')
    print(manifest['classification']);print(comp.loc[comp['sample'].eq('MATCHED')].to_string(index=False));print(cur[['model','scenario','prediction','failure']].to_string(index=False))
if __name__=='__main__':run()
