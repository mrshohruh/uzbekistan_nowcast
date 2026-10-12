"""Recompute summaries/rendering only, retaining the completed protection audit."""
from pathlib import Path
import json,platform
from xml.etree import ElementTree
import pandas as pd
import numpy as np
from scripts.phase7b.run import ROOT,OUT,DATA,metrics,sha
from scripts.phase7b.data import parse,transform,match
from scripts.phase7b.models import SPECS
from scripts.phase7b.report import report
from scripts.operations.prospective.common import safe

def refresh():
    manifest=json.loads((OUT/'run_manifest.json').read_text())
    if not manifest['protected_artifacts_verified']:raise ValueError('No verified scientific protection audit')
    if sha(DATA/'input/uzbekistan_nightlights_monthly.csv')!=manifest['source_sha256']:raise ValueError('Satellite input changed')
    def read(name):return pd.read_csv(OUT/name,float_precision='round_trip')
    f=read('phase7b_historical_predictions.csv');ar=pd.read_csv(ROOT/'results/diagnostics/historical_forecasts.csv',float_precision='round_trip');ar=ar.loc[ar.model.eq('AR1')&ar.lag_mode.eq('standard')&ar.timing_rule.eq('STRICT')].rename(columns={'forecast_origin_date':'origin'})
    comparison=[];hmetrics=[];robust=[]
    for scenario,block in f.groupby('scenario'):
        for challenger in [*SPECS,*['C'+m[1:] for m in SPECS if m.startswith('S')]]:
            if challenger not in block.model.unique():continue
            bm='C0' if challenger.startswith('C') else 'M0';keys=match(block,[bm,challenger]);selected=block.merge(keys,on=['origin','target_quarter','horizon','scenario'],validate='many_to_one')
            for sample,b in [('MATCHED',selected),('FULL_AVAILABLE',block)]:
                for model in [bm,challenger]:
                    g=b.loc[b.model.eq(model)];comparison.append(dict(scenario=scenario,comparison=challenger,sample=sample,model=model,**metrics(g,ar)))
                    if sample=='MATCHED':
                        for h in ['H1','H2','H3']:hmetrics.append(dict(scenario=scenario,comparison=challenger,model=model,horizon=h,**metrics(g.loc[g.horizon.eq(h)],ar)))
            matched=selected.loc[selected.model.isin([bm,challenger])];qs=sorted(matched.target_quarter.unique());mid=len(qs)//2
            for label,qset in [('EARLY',qs[:mid]),('RECENT',qs[mid:])]+[('LOQO_EXCLUDE_'+q,[v for v in qs if v!=q]) for q in qs]:
                for model in [bm,challenger]:robust.append(dict(scenario=scenario,comparison=challenger,subset=label,model=model,**metrics(matched.loc[matched.model.eq(model)&matched.target_quarter.isin(qset)],ar)))
    comp=pd.DataFrame(comparison);hm=pd.DataFrame(hmetrics);rb=pd.DataFrame(robust)
    for name,frame in [('phase7b_model_comparison.csv',comp),('phase7b_horizon_metrics.csv',hm),('phase7b_robustness.csv',rb),('phase7b_lag_sensitivity.csv',comp.loc[comp['sample'].eq('MATCHED')])]:frame.to_csv(OUT/name,index=False,float_format='%.17g')
    failures=pd.concat([f,read('phase7b_current_nowcasts.csv')],ignore_index=True)
    failures=failures.loc[failures.prediction.isna()&failures.model.str.startswith(('S','R'))].copy()
    failures['reason']=failures.failure
    failures.to_csv(OUT/'phase7b_failures.csv',index=False,float_format='%.17g')
    raw=parse(DATA/'input/uzbekistan_nightlights_monthly.csv')
    report(raw,transform(raw),comp,hm,f,read('phase7b_current_nowcasts.csv'),read('phase7b_factor_loadings.csv'),read('phase7b_factor_signals.csv'),rb,manifest)
    if (OUT/'phase7b_tests.xml').exists():manifest['tests']=dict(ElementTree.parse(OUT/'phase7b_tests.xml').getroot().find('testsuite').attrib)
    for name in ['browser_validation','determinism']:
        if (OUT/(name+'.json')).exists():manifest[name]=json.loads((OUT/(name+'.json')).read_text())
    import statsmodels
    manifest['environment']=dict(python=platform.python_version(),pandas=pd.__version__,numpy=np.__version__,statsmodels=statsmodels.__version__)
    manifest['summary_refresh_note']='Summaries/rendering refreshed after completing optional EVI sensitivities and normalizing equivalent AR1 origin date representations. Previously completed full protected-file verification is retained; production code/data were not modified.'
    manifest['source_code_sha256']={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'scripts/phase7b').glob('*.py')}
    manifest['output_sha256']={p.name:sha(p) for p in OUT.glob('*') if p.is_file() and p.name!='run_manifest.json'}
    (OUT/'run_manifest.json').write_text(json.dumps(safe(manifest),indent=2,allow_nan=False),encoding='utf8')
    print(manifest['classification']);print(manifest['best_exploratory_DFM']);print(manifest['best_exploratory_combination'])
if __name__=='__main__':refresh()
