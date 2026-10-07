"""Same-vintage YTD flow reconstruction."""
import numpy as np
import pandas as pd

def safe_flows(group):
 """De-cumulate only consecutive months of a consistent within-year raw vintage."""
 group=group.copy().sort_values('reference_period');group['period']=pd.PeriodIndex(group.reference_period,freq='M')
 if group.period.duplicated().any():raise ValueError('Duplicate reference months in flow input')
 levels=group.set_index('period').raw_value
 byperiod=group.set_index('period');flows={};log=[]
 for _,r in group.iterrows():
  p=r.period;prev=p-1;value=np.nan;reason=None
  if p.month==1:value=r.raw_value;reason='JANUARY_RESET'
  elif prev not in byperiod.index:reason='MISSING_PREVIOUS_MONTH'
  elif byperiod.loc[prev,'unit']!=r.unit:reason='UNIT_MISMATCH_WITHHELD'
  elif byperiod.loc[prev,'raw_file_path']!=r.raw_file_path:reason='VINTAGE_MISMATCH_WITHHELD'
  else:
   value=r.raw_value-levels.loc[prev];reason='WITHIN_YEAR_SAME_VINTAGE_DIFFERENCE'
   if value<0:value=np.nan;reason='NON_MONOTONIC_YTD_WITHHELD'
  flows[p]=value
  log.append({'variable_key':r.variable_key,'reference_period':str(p),'raw_ytd':r.raw_value,'previous_period':str(prev) if p.month>1 else None,'monthly_flow':value,'decision':reason,'source_url':r.source_url,'raw_file_path':r.raw_file_path,'cumulative_total_reconciliation':'same-vintage difference algebraically reconciles; incomplete years not certified'})
 flow=pd.Series(flows,dtype=float).sort_index();lag=flow.shift(12) if len(flow) and flow.index.equals(pd.period_range(flow.index.min(),flow.index.max(),freq='M')) else flow.reindex(pd.period_range(flow.index.min(),flow.index.max(),freq='M')).shift(12)
 current=flow.reindex(lag.index);positive=(current>0)&(lag>0)
 yoy=pd.Series(np.nan,index=current.index);yoy.loc[positive]=100*np.log(current.loc[positive]/lag.loc[positive])
 pct=pd.Series(np.nan,index=current.index);pct.loc[positive]=100*(current.loc[positive]/lag.loc[positive]-1)
 return flow,yoy,pct,log
