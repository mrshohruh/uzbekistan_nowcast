"""Exact level deflation and existing information/estimation conventions."""
import numpy as np
import pandas as pd
from scripts.phase6e.models import FIELDS, sw
from scripts.phase6g2.core import fit
from uznowcast.models.data import quarter_start

MODELS = ('M0_CURRENT_M2','M1_CPI_ONLY','M2_NOMINAL_M2_PLUS_CPI',
          'M3_REAL_M2_PLUS_CPI','M4_REAL_M2_ONLY')


def signals(money, indices):
    """Chain official previous-month=100 indices; no gap filling."""
    if money.index.has_duplicates or indices.index.has_duplicates:
        raise ValueError('Duplicate source months')
    ix=pd.date_range(min(money.index.min(),indices.index.min()),max(money.index.max(),indices.index.max()),freq='ME')
    m=money.reindex(ix).where(lambda x:x>0)
    cp=indices.reindex(ix).where(lambda x:x>0)
    # Arbitrary normalization cancels exactly in growth. A gap ends the chain.
    price=(cp.loc[cp.first_valid_index():]/100).cumprod(skipna=False)
    price=price.reindex(ix)
    real=m/price
    growth=lambda x:100*(np.log(x)-np.log(x.shift(12)))
    return pd.DataFrame(dict(m2_level=m,cpi_month_index=cp,cpi_index=price,
                             real_m2_level=real,nominal_m2=growth(m),
                             cpi=growth(price),real_m2=growth(real)))


def design(panel,dataset,s,target,horizon,model,common_start=None):
    k=sw.common.kernel();p=panel.copy();lags=dict(dataset.release_lag_days)
    fields=list(FIELDS)
    if model==MODELS[1]:fields.remove('m2')
    if model in MODELS[1:4]:fields.append('cpi')
    if model in MODELS[3:]:
        # Frozen nominal cells remain authoritative scope restrictions.
        p['m2']=s.real_m2.reindex(p.index).where(panel.m2.notna())
        lags['m2']=max(lags['m2'],lags['cpi_headline'])
    p['cpi']=s.cpi.reindex(p.index);lags['cpi']=lags['cpi_headline']
    spec=k.Spec('DFM-4_R1_P2',tuple(fields),1,2,'2019-01-31',True,False)
    frame,audit=k.mask(p,spec,target,horizon,lags,'standard')
    end=quarter_start(target)-pd.Timedelta(days=1)
    starts=[frame[c].first_valid_index() for c in frame]
    if any(x is None for x in starts):raise ValueError('unobserved_predictor')
    frame=frame.loc[max(starts):]
    if common_start is not None:frame=frame.loc[common_start:]
    k.training_panel(frame,end,True)
    return frame,spec,audit,end
