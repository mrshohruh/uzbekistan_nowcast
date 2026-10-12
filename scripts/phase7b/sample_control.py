"""Supplementary matched-history M0 control; production functions remain unchanged."""
from pathlib import Path
from dataclasses import replace
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from scripts.phase6i.run import current_inputs
from scripts.production.models import dfm,sw
from uznowcast.models.data import load_dataset

def run():
    ds=load_dataset(ROOT);cd,ca,info,co,_,_=current_inputs(ds)
    panel=pd.read_csv(ROOT/'data/current/historical_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip')
    events=pd.read_csv(ROOT/'data/current/gdp_vintages.csv')
    f=pd.read_csv(ROOT/'results/diagnostics/historical_forecasts.csv',float_precision='round_trip')
    origins=f.loc[f.model.eq('UMIDAS_USD')&f.lag_mode.eq('standard')&f.timing_rule.eq('STRICT')&f.prediction.notna()]
    jobs=[(r,False) for r in origins.to_dict('records')]+[(dict(target_quarter=info['target'],horizon=info['horizon'],forecast_origin_date=str(co),actual=float('nan')),True)]
    records=[]
    for r,current in jobs:
        origin=pd.Timestamp(r['forecast_origin_date']);target=r['target_quarter'];h=r['horizon']
        g=ca if current else sw.common.vintage_kernel().available_gdp_vintage_as_of(events,origin,target=target,timing_rule='STRICT')
        d=cd if current else replace(ds,gdp=pd.DataFrame({'quarter':g.frame.index,ds.target_field:g.frame.value.to_numpy()}))
        p=pd.DataFrame(info['panel']).set_index('month').astype(float) if current else panel
        p.index=pd.to_datetime(p.index)
        pred=float('nan');reason=None
        try:pred,_=dfm(p.loc['2019-06-30':],d,g,target,h,origin)
        except ValueError as e:reason=str(e)
        records.append(dict(origin=str(origin),target_quarter=target,horizon=h,actual=r['actual'],prediction=pred,model='M0_NO2_HISTORY_CONTROL',failure=reason))
    pd.DataFrame(records).to_csv(ROOT/'results/phase7b/phase7b_sample_length_control.csv',index=False,float_format='%.17g')
if __name__=='__main__':run()
