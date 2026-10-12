"""Satellite input validation and strictly backward-looking transformations."""
from pathlib import Path
import numpy as np
import pandas as pd

COLUMNS=['radiance','NDVI','EVI','NO2']

def parse(path: Path):
    f=pd.read_csv(path,sep=';',dtype=str)
    if list(f.columns)!=['date',*COLUMNS]: raise ValueError('Unexpected CSV columns')
    dates=pd.to_datetime(f.date,format='%Y-%m',errors='raise').dt.to_period('M')
    if dates.duplicated().any(): raise ValueError('Duplicate months')
    if not dates.is_monotonic_increasing: raise ValueError('Months not chronological')
    f.index=dates.dt.to_timestamp('M');f=f.drop(columns='date')
    for c in COLUMNS:
        f[c]=pd.to_numeric(f[c],errors='raise')
        if np.isinf(f[c]).any(): raise ValueError('Infinite value: '+c)
    return f

def transform(f):
    if f.index.to_period('M').duplicated().any(): raise ValueError('Duplicate months')
    previous=f.copy();previous.index=(previous.index.to_period('M')+12).to_timestamp('M')
    previous=previous.reindex(f.index)
    r=pd.DataFrame(index=f.index)
    for c,name in [('radiance','NTL_YOY'),('NO2','NO2_YOY')]:
        valid=f[c].gt(0)&previous[c].gt(0)
        r[name]=100*np.log(f[c].where(valid)/previous[c].where(valid))
    for c in ['NDVI','EVI']: r[c+'_YOY_DIFF']=f[c]-previous[c]
    r['NTL_SEASONAL_DIFF']=f.radiance-previous.radiance
    # Expanding climatology excludes the observation itself and all later months.
    for c in ['radiance','NDVI']:
        climatology=f[c].groupby(f.index.month).transform(lambda s:s.shift().expanding(min_periods=3).mean())
        r[c.upper()+'_SEASONAL_ANOMALY']=f[c]-climatology
    return r

def available(frame,origin,lag):
    """Hypothesis: available at month end plus lag calendar months; lag 0 exploratory."""
    release=(frame.index.to_period('M')+lag).to_timestamp('M')
    return frame.where(np.broadcast_to(np.asarray(release<=pd.Timestamp(origin))[:,None],frame.shape))

def match(frame,models):
    keys=['origin','target_quarter','horizon','scenario']
    if frame.duplicated(keys+['model']).any(): raise ValueError('Duplicate model/origin')
    actuals=frame.groupby(keys).actual.nunique()
    if actuals.gt(1).any(): raise ValueError('Inconsistent actuals')
    return frame.pivot(index=keys,columns='model',values='prediction').reindex(columns=models).dropna().reset_index()[keys]


def descriptive_diagnostics(f,out):
    """Full-sample descriptive audit only; never used in model estimation."""
    rows=[]
    for c in f:
        s=f[c].dropna();t=s.index.to_period('M').astype('int64').to_numpy()
        rows.append(dict(indicator=c,n=len(s),linear_slope_per_month=np.polyfit(t-t.min(),s.to_numpy(),1)[0],trend_correlation=np.corrcoef(t,s)[0,1],seasonal_mean_range=s.groupby(s.index.month).mean().max()-s.groupby(s.index.month).mean().min(),units='original unverified measurement units; descriptive only'))
    pd.DataFrame(rows).to_csv(out/'satellite_trend_diagnostics.csv',index=False)
    y=f.groupby(f.index.year).mean();r=y.diff();r['radiance_annual_mean_pct_change']=100*y.radiance.pct_change()
    r.reset_index(names='year').to_csv(out/'satellite_break_diagnostics.csv',index=False)
    p=out/'satellite_data_audit.md';s=p.read_text(encoding='utf8')
    note='\nAdditional diagnostics: satellite_trend_diagnostics.csv records per-month linear trend slopes, time correlations and calendar-month mean ranges in unverified original measurement units. satellite_break_diagnostics.csv records changes in annual means without declaring sensor breaks. Radiance mean rises approximately 74.84% from 2016 to 2017; that discontinuity requires product and processing verification. No observations were corrected or deleted.\n'
    if 'Additional diagnostics:' not in s:p.write_text(s+note,encoding='utf8')
