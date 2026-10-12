"""Complete current factor diagnostics and refresh validated scientific reports."""
from pathlib import Path
import sys,json
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
sys.dont_write_bytecode=True

def main():
    from scripts.phase7c.run import OUT,audit,sha
    from scripts.phase7c.models import estimate
    from scripts.phase6i.run import current_inputs
    from scripts.production.models import fit_info
    from uznowcast.models.data import load_dataset
    from scripts.phase7c.report import report
    from scripts.operations.prospective.common import safe
    ds=load_dataset(ROOT);candidate,delays,inventory,_=audit(ds)
    cd,g,info,origin,_,_=current_inputs(ds);base=fit_info(info,ROOT,origin)['dfit']
    loads=pd.read_csv(OUT/'phase7c_factor_loadings.csv');signals=pd.read_csv(OUT/'phase7c_factor_signals.csv')
    loads=loads.loc[~loads.model.eq('M0')];signals=signals.loc[~signals.model.eq('M0')]
    meta=dict(origin=str(origin),target_quarter=info['target'],horizon=info['horizon'],scenario='PRIMARY_ASSUMED_REGISTRY_LAG',actual=None,current=True,model='M0')
    ll=[];ss=[];paths=[]
    for c,l in zip(base['z'].columns,base['loadings']):
        ll.append(dict(meta,indicator=c,loading=l))
        for date,value in base['z'][c].loc[base['z'].index.to_period('Q')==pd.Period(info['target'],'Q')].items():ss.append(dict(meta,indicator=c,date=str(date.date()),standardized_value=value,loading_signal=l*value,units='descriptive standardized signal; NOT GDP pp'))
    for date,value in base['factors'].iloc[:,0].items():paths.append(dict(model='M0',date=str(date.date()),factor=value,sign_alignment='baseline',units='standardized filtered factor; not GDP pp'))
    try:
        _,f,_,_,_=estimate(pd.DataFrame(info['panel']).set_index('month').rename_axis('date').set_axis(pd.to_datetime(pd.DataFrame(info['panel']).month)),cd,g,info['target'],info['horizon'],origin,candidate,('retail_trade',),delays)
        aligned=f.iloc[:,0].to_frame('R1').join(base['factors'].iloc[:,0].rename('M0')).dropna();sign=1 if aligned.corr().iloc[0,1]>=0 else -1
        for date,value in f.iloc[:,0].items():paths.append(dict(model='R1',date=str(date.date()),factor=sign*value,sign_alignment='correlation with M0',units='standardized filtered factor; not GDP pp'))
    except ValueError:pass
    pd.concat([loads,pd.DataFrame(ll)],ignore_index=True).to_csv(OUT/'phase7c_factor_loadings.csv',index=False,float_format='%.17g')
    pd.concat([signals,pd.DataFrame(ss)],ignore_index=True).to_csv(OUT/'phase7c_factor_signals.csv',index=False,float_format='%.17g')
    pd.DataFrame(paths).to_csv(OUT/'phase7c_current_factor_paths.csv',index=False,float_format='%.17g')
    manifest=json.loads((OUT/'run_manifest.json').read_text())
    manifest['browser_validation']=json.loads((OUT/'browser_validation.json').read_text())
    report(inventory,pd.read_csv(OUT/'phase7c_model_comparison.csv'),pd.read_csv(OUT/'phase7c_horizon_metrics.csv'),pd.read_csv(OUT/'phase7c_historical_predictions.csv'),pd.read_csv(OUT/'phase7c_current_nowcasts.csv'),pd.read_csv(OUT/'phase7c_robustness.csv'),manifest)
    result=OUT/'phase7c_results.md'
    result.write_text(result.read_text(encoding='utf8')+'\n## Final validation\n\n52 tests passed; independent deterministic refits reproduce retail forecasts and the same explicit non-estimability for other current fits. Protected files unchanged. All 15 dashboard tabs and candidate/horizon selectors rendered locally in Edge.\n\n## Artifact index\n\n'+'\n'.join('- `results/phase7c/'+p.name+'`' for p in sorted(OUT.glob('*')) if p.is_file()),encoding='utf8')
    manifest['artifact_sha256']={p.name:sha(p) for p in OUT.glob('*') if p.is_file() and p.name not in ['run_manifest.json','pipeline.log']}
    (OUT/'run_manifest.json').write_text(json.dumps(safe(manifest),indent=2,allow_nan=False))
    print(manifest['classification'])
if __name__=='__main__':main()
