"""Run isolated Phase 7C: python -m scripts.phase7c.run."""
from pathlib import Path
from dataclasses import replace
import sys,json,hashlib,logging,os
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'src'))
from scripts.phase7c.data import KEYS,flows,growth,gate
from scripts.phase7c.models import estimate
from scripts.phase7b.run import metrics
from scripts.phase7b.data import match
from scripts.phase6i.run import current_inputs
from scripts.production.models import FIELDS,dfm,umidas,fit_info,sw
from scripts.operations.prospective.inputs import eligible
from uznowcast.models.data import load_dataset
OUT=ROOT/'results/phase7c'
LOG=logging.getLogger('phase7c')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,f):f.to_csv(OUT/('phase7c_'+name+'.csv'),index=False,float_format='%.17g')
def protect():
    from concurrent.futures import ThreadPoolExecutor
    paths=[]
    for folder in ['src','scripts','config','registry','data','metadata','dashboard','results','docs']:
        for directory,dirs,files in os.walk(ROOT/folder):
            dirs[:]=[d for d in dirs if d!='__pycache__' and not d.startswith(('pytest_tmp','tmp','.'))]
            if Path(directory)==ROOT/'data':
                # Individual reused raw payloads are independently checksum-verified in audit.
                dirs[:]=[d for d in dirs if d!='raw']
            for name in files:
                p=Path(directory)/name;rel=p.relative_to(ROOT).as_posix()
                if p.suffix!='.pyc' and not rel.startswith(('scripts/phase7c/','results/phase7c/')):paths.append((rel,p))
    LOG.info('Hashing %d protected files',len(paths))
    def checksum(item):return item[0],sha(item[1])
    with ThreadPoolExecutor(max_workers=8) as pool:result=dict(pool.map(checksum,paths))
    LOG.info('Protected input hashes captured')
    return result

def audit(ds):
    inventory=[];aud=[];parts={};candidate=pd.DataFrame(index=ds.monthly.index);delays={}
    for key in ['retail_trade','construction','imports_total','exports_total','gold_exports_proxy']:
        p=ROOT/'data/processed'/f'{key}.parquet';f=pd.read_parquet(p);s,x=flows(f);parts[key]=(f,s,x)
        errors=[]
        for raw,h in f[['raw_file_path','checksum']].drop_duplicates().itertuples(index=False,name=None):
            if not (ROOT/raw).exists() or sha(ROOT/raw)!=h:errors.append(raw)
        if errors:raise ValueError('Raw checksum failure: '+str(errors))
        reconcile=max(abs(x.loc[x.index.year==y].sum()-s.loc[s.index.year==y].iloc[-1]) for y in s.index.year.unique())
        for date,value in x.items():
            row=f.loc[pd.to_datetime(f.reference_date).eq(date)].iloc[0]
            aud.append(dict(variable_key=key,date=str(date.date()),raw_ytd=s.loc[date],monthly_flow=value,unit=row.unit,quality_flag='NEGATIVE_INCREMENT' if value<0 else ('MISSING' if pd.isna(value) else row.quality_flag),annual_reconciliation_max_error=reconcile,source_url=row.source_url,source_release_date=row.source_release_date,release_basis=row.source_release_basis,retrieved_at=row.retrieved_at,raw_file_path=row.raw_file_path,checksum=row.checksum))
        if key in KEYS:
            candidate[key]=growth(x).reindex(candidate.index);delays[key]=ds.release_lag_days[key]
    f,s,x=parts['exports_total'];gf,gs,gx=parts['gold_exports_proxy']
    proxy=x-gx
    candidate['NON_GOLD_EXPORT_PROXY']=growth(proxy).reindex(candidate.index)
    # Arithmetic compatibility is insufficient when a parent has impossible increments.
    proxy_valid=bool((gx.dropna()>=0).all() and (proxy.dropna()>0).all() and x.index.equals(gx.index) and f.unit.eq('million USD').all() and gf.unit.eq('million USD').all())
    for key in KEYS:
        field=ds.clean_field_by_key[key];v=ds.monthly[field].dropna()
        registry=next(r for r in ds.registry.scope('v1') if r['variable_key']==key)
        inventory.append(dict(variable_key=key,status='ACTIVE_IN_PRODUCTION' if key in FIELDS else 'AVAILABLE_IN_DATABASE_NOT_ACTIVE',production_active=key in FIELDS,master_column=field,experiment_column=key if key!='exports_non_gold' else 'NON_GOLD_EXPORT_PROXY',transformation=registry['required_transformation'],raw_start='2020-01' if key=='retail_trade' else '2021-01',growth_start=str(v.index.min().to_period('M')),growth_end=str(v.index.max().to_period('M')),n_growth=len(v),assumed_lag_days=ds.release_lag_days[key],primary_eligible=key!='exports_non_gold' or proxy_valid,limitation='current revised vintage; assumed historical lag; Other goods not exact gold' if key=='exports_non_gold' else 'current revised vintage; assumed historical lag; nominal measure'))
    cpi=pd.read_parquet(ROOT/'data/processed/cpi_headline.parquet').set_index('reference_date').raw_value
    cpi.index=pd.to_datetime(cpi.index);cpi=cpi.reindex(pd.date_range(cpi.index.min(),cpi.index.max(),freq='ME'))
    inflation=100*np.log(cpi/100).rolling(12,min_periods=12).sum()
    candidate['retail_cpi_approx']=candidate.retail_trade-inflation.reindex(candidate.index)
    delays['retail_cpi_approx']=max(delays['retail_trade'],ds.release_lag_days['cpi_headline'])
    save('predictor_inventory',pd.DataFrame(inventory));save('data_audit',pd.DataFrame(aud))
    save('candidate_history',candidate.reset_index(names='date'))
    save('correlations',candidate.join(pd.read_csv(ROOT/'data/current/historical_panel.csv',index_col='date',parse_dates=True)[list(FIELDS)]).corr().reset_index(names='indicator'))
    return candidate,delays,inventory,proxy_valid

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(OUT/'pipeline.log',mode='w')])
    before=protect();ds=load_dataset(ROOT);candidate,delays,inventory,proxy_valid=audit(ds)
    cd,ca,info,co,frozen,snapshot=current_inputs(ds);fit=fit_info(info,ROOT,co)
    check={k:dict(recomputed=fit[k],frozen=frozen[v],error=fit[k]-frozen[v]) for k,v in [('dfm','dfm_forecast'),('umidas','umidas_forecast'),('final','final_forecast')]}
    if any(abs(v['error'])>1e-12 for v in check.values()):raise ValueError('Production mismatch')
    if co.date()!=pd.Timestamp('2026-10-05').date():raise ValueError('Wrong frozen cutoff')
    # All challenger current inputs must have been retrieved by the frozen cutoff.
    current_candidate=candidate.copy()
    for key in ['retail_trade','construction','imports_total','cpi_headline']:
        f=pd.read_parquet(ROOT/'data/processed'/f'{key}.parquet')
        if len(eligible(f,pd.Timestamp(co).tz_localize('Asia/Tashkent').tz_convert('UTC')))!=len(f):raise ValueError('Candidate vintage later than cutoff: '+key)
    source=pd.read_csv(ROOT/'results/diagnostics/historical_forecasts.csv',float_precision='round_trip')
    common=source.loc[source.lag_mode.eq('standard')&source.timing_rule.eq('STRICT')]
    origins=common.loc[common.model.eq('UMIDAS_USD')&common.prediction.notna()].merge(common.loc[common.model.eq('DFM-4_R1_P2__BRIDGE_B_mean')&common.prediction.notna(),['target_quarter','horizon']],on=['target_quarter','horizon'],validate='one_to_one')
    ar=common.loc[common.model.eq('AR1')].rename(columns={'forecast_origin_date':'origin'})
    panel=pd.read_csv(ROOT/'data/current/historical_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip');events=pd.read_csv(ROOT/'data/current/gdp_vintages.csv')
    specs={'R1':('retail_trade',),'R2':('construction',),'R3':('imports_total',),'R1_REAL_APPROX':('retail_cpi_approx',)}
    rows=[];loads=[];signals=[];controls=[];stability=[];diagnostics=[];reproduction=[]
    jobs=[(r,False) for r in origins.to_dict('records')]+[(dict(target_quarter=info['target'],horizon=info['horizon'],forecast_origin_date=str(co),actual=np.nan),True)]
    for r,current in jobs:
        target,h,origin=r['target_quarter'],r['horizon'],pd.Timestamp(r['forecast_origin_date'])
        g=ca if current else sw.common.vintage_kernel().available_gdp_vintage_as_of(events,origin,target=target,timing_rule='STRICT')
        sw.common.vintage_kernel().assert_boundary(g,target)
        dataset=cd if current else replace(ds,gdp=pd.DataFrame({'quarter':g.frame.index,ds.target_field:g.frame.value.to_numpy()}))
        p=fit['panel'] if current else panel
        if current:d,u,bf=fit['dfm'],fit['umidas'],fit['dfit']['factors']
        else:
            d,b=dfm(p,dataset,g,target,h,origin);bf=b['factors'];u,_,_=umidas(dataset,g,target,h,origin)
            for m,v in [('DFM-4_R1_P2__BRIDGE_B_mean',d),('UMIDAS_USD',u)]:
                ref=float(common.loc[common.model.eq(m)&common.target_quarter.eq(target)&common.horizon.eq(h),'prediction'].iloc[0]);reproduction.append(dict(target_quarter=target,horizon=h,model=m,error=v-ref))
                if abs(v-ref)>1e-7:raise ValueError('Historical baseline mismatch')
        for extra,label,winsor in [(0,'PRIMARY_ASSUMED_REGISTRY_LAG',False),(15,'LAG_PLUS_15D',False),(30,'LAG_PLUS_30D',False),(0,'TRAINING_ONLY_WINSOR_1_99',True)]:
            meta=dict(origin=str(origin),target_quarter=target,horizon=h,scenario=label,actual=r['actual'],current=current,interpretation='RETROSPECTIVE_EXPLORATORY')
            for m,v in [('M0',d),('U0',u),('C0',.5*(d+u))]:rows.append(dict(meta,model=m,prediction=v,failure=None))
            for m,fields in specs.items():
                if m=='R1_REAL_APPROX' and extra:continue
                prediction=np.nan;failure=None
                try:
                    prediction,fac,ll,z,diag=estimate(p,dataset,g,target,h,origin,current_candidate if current else candidate,fields,delays,extra,winsor=winsor)
                    diagnostics.append(dict(meta,model=m,**diag))
                    aligned=fac.iloc[:,0].to_frame('challenger').join(bf.iloc[:,0].rename('M0')).dropna();corr=aligned.corr().iloc[0,1]
                    stability.append(dict(meta,model=m,factor_correlation=abs(corr),sign_aligned_factor_rmse=np.sqrt(((aligned.challenger*(1 if corr>=0 else -1)-aligned.M0)**2).mean()),nowcast_change=prediction-d))
                    for c,l in zip(z.columns,ll):
                        loads.append(dict(meta,model=m,indicator=c,loading=l))
                        for date,value in z[c].loc[z.index.to_period('Q')==pd.Period(target,'Q')].items():signals.append(dict(meta,model=m,indicator=c,date=str(date.date()),standardized_value=value,loading_signal=l*value,units='descriptive standardized signal; NOT GDP pp'))
                    if extra==0 and not winsor:
                        control=np.nan;control_failure=None
                        try:control,_,_,_,dd=estimate(p,dataset,g,target,h,origin,candidate,fields,delays,control=True)
                        except ValueError as e:control_failure=str(e)
                        controls.append(dict(meta,model=m,control_model='M0_IDENTICAL_TRAINING_START',prediction=control,control_failure=control_failure,challenger_prediction=prediction,training_start=diag['estimation_start'],n_training_months=diag['n_training_months'],n_GDP_quarters=diag.get('n_GDP_quarters'),n_missing_cells=diag['n_missing_cells']))
                except ValueError as e:failure=str(e)
                rows.append(dict(meta,model=m,prediction=prediction,failure=failure))
                rows.append(dict(meta,model='C_'+m,prediction=.5*(prediction+u),failure=failure))
            LOG.info('Completed %s %s %s',target,h,label)
        save('historical_predictions',pd.DataFrame(rows).loc[lambda x:~x.current])
    allf=pd.DataFrame(rows);hist=allf.loc[~allf.current];cur=allf.loc[allf.current].copy();cur['status']=np.where(cur.model.isin(['M0','U0','C0']),'FROZEN_PRODUCTION_REFERENCE','RESEARCH_ONLY')
    cur['last_available_candidate_month']=cur.apply(lambda r: str(gate(candidate[specs[r.model.removeprefix('C_')][0]],co,delays[specs[r.model.removeprefix('C_')][0]]+(15 if r.scenario=='LAG_PLUS_15D' else 30 if r.scenario=='LAG_PLUS_30D' else 0)).last_valid_index()) if r.model.removeprefix('C_') in specs else None,axis=1)
    save('current_nowcasts',cur);save('factor_loadings',pd.DataFrame(loads));save('factor_signals',pd.DataFrame(signals));save('sample_controls',pd.DataFrame(controls));save('factor_stability',pd.DataFrame(stability));save('estimation_diagnostics',pd.DataFrame(diagnostics));save('baseline_reproduction',pd.DataFrame(reproduction))
    comparison=[];hm=[];robust=[]
    for scenario,block in hist.groupby('scenario'):
        for model in [*specs,*['C_'+m for m in specs]]:
            if model not in block.model.unique():continue
            baseline='C0' if model.startswith('C_') else 'M0';keys=match(block,[baseline,model]);selected=block.merge(keys,on=['origin','target_quarter','horizon','scenario'])
            qs=sorted(selected.target_quarter.unique());mid=len(qs)//2
            for m in [baseline,model]:
                f=selected.loc[selected.model.eq(m)]
                comparison.append(dict(scenario=scenario,comparison=model,model=m,sample='PAIRWISE_MATCHED',**metrics(f,ar),exact_origins=';'.join(f.origin+'|'+f.target_quarter+'|'+f.horizon)))
                for h in ['H1','H2','H3']:hm.append(dict(scenario=scenario,comparison=model,model=m,horizon=h,**metrics(f.loc[f.horizon.eq(h)],ar)))
                for label,qset in [('EARLY',qs[:mid]),('RECENT',qs[mid:])]+[('LEAVE_OUT_'+q,[v for v in qs if v!=q]) for q in qs]:robust.append(dict(scenario=scenario,comparison=model,model=m,subset=label,**metrics(f.loc[f.target_quarter.isin(qset)],ar)))
            a=selected.loc[selected.model.eq(baseline)].set_index(['target_quarter','horizon','origin']);b=selected.loc[selected.model.eq(model)].set_index(['target_quarter','horizon','origin']);loss=((a.prediction-a.actual)**2-(b.prediction-b.actual)**2).groupby(level=0).mean().dropna()
            if len(loss):
                rng=np.random.default_rng(7);boot=rng.choice(loss.to_numpy(),(4000,len(loss)),replace=True).mean(axis=1)
                robust.append(dict(scenario=scenario,comparison=model,model=model,subset='QUARTER_CLUSTER_BOOTSTRAP_MSE_GAIN',mean_mse_gain=loss.mean(),ci_lower=np.quantile(boot,.025),ci_upper=np.quantile(boot,.975),n_quarters=len(loss)))
    comp=pd.DataFrame(comparison);save('model_comparison',comp);save('horizon_metrics',pd.DataFrame(hm));save('robustness',pd.DataFrame(robust))
    from scripts.phase7c.report import report
    from concurrent.futures import ThreadPoolExecutor
    def verify(item):
        p,h=item
        return p if not (ROOT/p).exists() or sha(ROOT/p)!=h else None
    with ThreadPoolExecutor(max_workers=8) as pool:changed=[p for p in pool.map(verify,before.items()) if p]
    if changed:raise ValueError('Protected inputs changed: '+str(changed))
    manifest=dict(classification='PHASE7C_INCONCLUSIVE',active_predictors=list(FIELDS),proxy_validated=proxy_valid,proxy_exclusion='negative parent monthly increment; Other goods not verified as exact gold',protected_artifacts_verified=True,protected_sha256=before,production_reproduction=check,production_nowcast=frozen['final_forecast'],snapshot=snapshot,cutoff=str(co),historical_origin_count=len(origins),historical_vintage_warning='RETROSPECTIVE_EXPLORATORY; registry delays assumed, not first-publication dates',groupings='Deferred: short balanced histories and unvalidated export proxy; no defensible best set selected')
    primary=comp.loc[comp.scenario.eq('PRIMARY_ASSUMED_REGISTRY_LAG')]
    gains=[]
    for model in specs:
        pair=primary.loc[primary.comparison.eq(model)]
        if len(pair)==2 and pair.n_origins.max()>0:gains.append(float(pair.loc[pair.model.eq('M0'),'rmse'].iloc[0]-pair.loc[pair.model.eq(model),'rmse'].iloc[0]))
    if gains and max(gains)<=0:
        manifest['classification']='PHASE7C_NO_INCREMENTAL_IMPROVEMENT'
        manifest['groupings']='Deferred: individual additions worsen matched accuracy; export proxy fails validation; no defensible best set selected'
    report(inventory,comp,pd.DataFrame(hm),hist,cur,pd.DataFrame(robust),manifest)
    manifest['artifact_sha256']={p.name:sha(p) for p in OUT.glob('*') if p.is_file() and p.name not in ['run_manifest.json','pipeline.log']}
    (OUT/'run_manifest.json').write_text(json.dumps(sw.common.safe(manifest),indent=2,allow_nan=False),encoding='utf8')
    print(manifest['classification']);print(cur.loc[cur.scenario.eq('PRIMARY_ASSUMED_REGISTRY_LAG'),['model','prediction','failure']].to_string(index=False))
if __name__=='__main__':run()
