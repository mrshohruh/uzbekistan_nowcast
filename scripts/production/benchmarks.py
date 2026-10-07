"""Frozen GDP-gated benchmarks for the current operational monitor."""
from dataclasses import replace
import numpy as np
import pandas as pd
from uznowcast.gdp_vintages import assert_boundary
from uznowcast.models.benchmarks import ar_forecast
from uznowcast.models.midas import MidasSpec,midas_forecast
MODELS=('AR1','AR2','UMIDAS_USD','PRODUCTION_ENSEMBLE')
def benchmarks(dataset,available,target,horizon,mode,*,diagnostic=False):
    if not diagnostic:
        assert_boundary(available,target)
    gd=available.frame.value
    prior=str(pd.Period(target,freq='Q')-1)
    if prior not in gd.index:
        return {m:(np.nan,'PRIOR_QUARTER_GDP_NOT_AVAILABLE') for m in MODELS[:4]}
    sequence=pd.period_range(gd.index[0],gd.index[-1],freq='Q').astype(str)
    if not gd.index.equals(pd.Index(sequence,name=gd.index.name)):
        return {m:(np.nan,'NONCONSECUTIVE_DOCUMENTED_GDP') for m in MODELS[:4]}
    result={}
    for p,name in [(1,'AR1'),(2,'AR2')]:
        prediction,diag=ar_forecast(gd,p)
        result[name]=(prediction,diag.get('failure',''))
    original_train=dataset.gdp.loc[dataset.gdp.quarter.lt(target),'quarter'].tolist()
    gated=replace(dataset,gdp=pd.DataFrame({'quarter':gd.index,dataset.target_field:gd.to_numpy()}))
    spec=MidasSpec('umidas_usd_uzs_mom_dlog','usd_uzs_mom_dlog',3,True,None)
    prediction,diag=midas_forecast(gated,spec,original_train,target,horizon=horizon,mode=mode)
    if np.isfinite(prediction) and diag.get('n_train',0)<15:
        prediction=np.nan;diag['failure']='insufficient_effective_training'
    result['UMIDAS_USD']=(prediction,diag.get('failure',''))
    pred=.5*result['AR2'][0]+.5*prediction
    result['PRODUCTION_ENSEMBLE']=(pred,'' if np.isfinite(pred) else 'COMPONENT_UNAVAILABLE')
    return result
