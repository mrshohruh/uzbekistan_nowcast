"""Complete optional EVI lag sensitivities using existing research kernels."""
from dataclasses import replace
import pandas as pd,numpy as np
from scripts.phase7b.run import ROOT,OUT,DATA
from scripts.phase7b.data import parse,transform
from scripts.phase7b.models import estimate
from scripts.phase6i.run import current_inputs
from scripts.production.models import sw
from uznowcast.models.data import load_dataset

def run():
    ds=load_dataset(ROOT);cd,ca,info,co,_,_=current_inputs(ds)
    sat=transform(parse(DATA/'input/uzbekistan_nightlights_monthly.csv'))
    panel=pd.read_csv(ROOT/'data/current/historical_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip');events=pd.read_csv(ROOT/'data/current/gdp_vintages.csv')
    hist=pd.read_csv(OUT/'phase7b_historical_predictions.csv',float_precision='round_trip');cur=pd.read_csv(OUT/'phase7b_current_nowcasts.csv',float_precision='round_trip');allf=pd.concat([hist,cur],ignore_index=True)
    loads=pd.read_csv(OUT/'phase7b_factor_loadings.csv',float_precision='round_trip');signals=pd.read_csv(OUT/'phase7b_factor_signals.csv',float_precision='round_trip')
    add=[];ll=[];ss=[]
    jobs=allf.loc[allf.model.eq('U0')&allf.lag_months.gt(0)].to_dict('records')
    for row in jobs:
        target,h,origin=row['target_quarter'],row['horizon'],pd.Timestamp(row['origin']);current=row['evaluation_group']=='CURRENT'
        g=ca if current else sw.common.vintage_kernel().available_gdp_vintage_as_of(events,origin,target=target,timing_rule='STRICT')
        d=cd if current else replace(ds,gdp=pd.DataFrame({'quarter':g.frame.index,ds.target_field:g.frame.value.to_numpy()}))
        p=pd.DataFrame(info['panel']).set_index('month').astype(float) if current else panel;p.index=pd.to_datetime(p.index)
        common={k:row[k] for k in ['origin','target_quarter','horizon','scenario','lag_months','actual','evaluation_group']};pred=np.nan;reason=None
        try:
            pred,diag,fac,loading,z=estimate(p,d,g,target,h,origin,sat,('EVI_YOY_DIFF',),int(row['lag_months']))
            for field,l in zip(z.columns,loading):
                ll.append(dict(common,model='S6',indicator=field,loading=l,n_training_months=diag['n_training_months'],n_GDP_quarters=diag['n_GDP_quarters']))
                for date,value in z[field].loc[z.index.to_period('Q')==pd.Period(target,'Q')].items():ss.append(dict(common,model='S6',indicator=field,date=str(date.date()),standardized_value=value,loading_signal=l*value,units='standardized descriptive; not GDP pp'))
        except ValueError as e:reason=str(e)
        for model,value in [('S6',pred),('C6',.5*pred+.5*row['prediction'])]:add.append(dict(common,model=model,prediction=value,failure=reason,status='RESEARCH ONLY; VINTAGE UNVERIFIED' if current else None))
    f=pd.concat([allf.loc[~(allf.model.isin(['S6','C6'])&allf.lag_months.gt(0))],pd.DataFrame(add)],ignore_index=True)
    f.loc[f.evaluation_group.ne('CURRENT')].sort_values(['origin','scenario','model']).to_csv(OUT/'phase7b_historical_predictions.csv',index=False,float_format='%.17g')
    f.loc[f.evaluation_group.eq('CURRENT')].to_csv(OUT/'phase7b_current_nowcasts.csv',index=False,float_format='%.17g')
    pd.concat([loads,pd.DataFrame(ll)],ignore_index=True).to_csv(OUT/'phase7b_factor_loadings.csv',index=False,float_format='%.17g');pd.concat([signals,pd.DataFrame(ss)],ignore_index=True).to_csv(OUT/'phase7b_factor_signals.csv',index=False,float_format='%.17g')
    print('Completed EVI delay sensitivities:',len(jobs))
if __name__=='__main__':run()
