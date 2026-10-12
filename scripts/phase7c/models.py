"""Unchanged one-factor AR(2) EM likelihood and lagged-GDP bridge."""
import pandas as pd
from scripts.production.models import FIELDS, sw
from uznowcast.models.data import quarter_start, quarter_end
from scripts.phase7c.data import gate

CACHE = {}

def estimate(panel, dataset, gdp, target, horizon, origin, candidate, fields,
             delays, extra=0, control=False, winsor=False):
    k=sw.common.kernel(); end=quarter_start(target)-pd.Timedelta(days=1)
    spec=k.Spec('PHASE7C',FIELDS,1,2,'2019-01-31',True,False)
    frame,_=k.mask(panel,spec,target,horizon,dataset.release_lag_days,'standard')
    for c in fields:
        frame[c]=gate(candidate[c],origin,delays[c]+extra).reindex(frame.index)
    frame,_=k.training_panel(frame,end,True)
    if control: frame=frame[list(FIELDS)]
    if winsor:
        for c in fields:
            if c in frame:
                t=frame.loc[:end,c];frame[c]=frame[c].clip(t.quantile(.01),t.quantile(.99))
    z,_,_=k.standardize(frame,end,False)
    z=z.reindex(pd.date_range(z.index.min(),quarter_end(target),freq='ME'))
    spec=k.Spec('PHASE7C',tuple(z.columns),1,2,'2019-01-31',True,False)
    factors,loadings,diag=k.estimate(z.loc[:end],z,spec,CACHE)
    prediction,bridge=k.bridge(factors,gdp,target,origin,'B','mean')
    return prediction,factors,loadings[:,0],z,dict(diag,**bridge)
