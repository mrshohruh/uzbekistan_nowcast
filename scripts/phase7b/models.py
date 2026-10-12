"""Research adapters using unchanged production DFM kernels and strict GDP vintages."""
from dataclasses import replace
import numpy as np
import pandas as pd
from scripts.production.models import FIELDS,sw
from uznowcast.models.data import quarter_start,quarter_end
from scripts.phase7b.data import available
CACHE={}
SPECS={'S1':('NTL_YOY',),'S2':('NDVI_YOY_DIFF',),'S3':('NO2_YOY',),'S4':('NTL_YOY','NDVI_YOY_DIFF'),'S5':('NTL_YOY','NO2_YOY'),'S6':('EVI_YOY_DIFF',),'R1':('NTL_SEASONAL_DIFF',),'R2':('NDVI_SEASONAL_ANOMALY',),'R3':('NTL_YOY',)}

def estimate(panel,dataset,gdp,target,horizon,origin,satellite,fields,lag,winsor=False):
    k=sw.common.kernel();end=quarter_start(target)-pd.Timedelta(days=1)
    base=k.Spec('DFM-4_R1_P2',FIELDS,1,2,'2019-01-31',True,False)
    frame,_=k.mask(panel,base,target,horizon,dataset.release_lag_days,'standard')
    eligible=available(satellite,pd.Timestamp(origin),lag)
    for field in fields: frame[field]=eligible[field].reindex(frame.index)
    spec=k.Spec('SATELLITE',tuple(frame.columns),1,2,'2019-01-31',True,False)
    frame,_=k.training_panel(frame,end,True)
    if winsor:
        for c in fields:
            train=frame.loc[:end,c];frame[c]=frame[c].clip(train.quantile(.01),train.quantile(.99))
    z,_,_=k.standardize(frame,end,False)
    z=z.reindex(pd.date_range(z.index.min(),quarter_end(target),freq='ME'))
    factors,loadings,diag=k.estimate(z.loc[:end],z,spec,CACHE)
    prediction,bridge=k.bridge(factors,gdp,target,origin,'B','mean')
    return prediction,dict(diag,**bridge),factors,loadings[:,0],z
