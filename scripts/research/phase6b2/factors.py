"""Re-estimate the frozen GDP-independent DFM, verifying every factor path."""
from pathlib import Path
import sys
import json
import hashlib
import importlib.util
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from uznowcast.models.data import load_dataset,quarter_start,quarter_end
OUT=ROOT/'results/research/phase6b2'

def frozen_module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

def main():
    core=frozen_module('phase6b2_immutable_core','scripts/research/phase6b/experiment.py')
    dataset=load_dataset(ROOT)
    panel=pd.read_csv(ROOT/'data/research/phase6a2/cbu_midas_monthly_panel.csv')
    panel.index=pd.PeriodIndex(panel.reference_period,freq='M').to_timestamp('M')
    panel=panel.loc['2021-01-31':'2026-08-31']
    old=pd.read_csv(ROOT/'results/research/phase6b/phase6b_factor_series.csv')
    old=old.loc[old.specification.eq('DFM_DOMESTIC_3')&old.factor.eq(1)&old.target_quarter.str.fullmatch(r'\d{4}Q[1-4]',na=False)]
    states,checks=[],[]
    specification=core.Spec('DFM_DOMESTIC_3',core.DOMESTIC)
    for (target,horizon,mode),block in old.groupby(['target_quarter','horizon','lag_mode']):
        end=quarter_start(target)-pd.Timedelta(days=1)
        masked,_=core.masked_panel(panel,specification.fields,target,horizon,dataset.release_lag_days,mode)
        z,*_=core.prepare(masked,panel.services_output_regime,end,False)
        training=z.loc[:end]
        index=pd.date_range(panel.index.min(),quarter_end(target),freq='ME')
        fit,factors,*rest=core.estimate(training,z.reindex(index),specification)
        delta=float(np.max(np.abs(factors[:,0]-block.sort_values('month').value.to_numpy())))
        assert delta<1e-8,(target,horizon,mode,delta)
        checks.append(dict(target_quarter=target,horizon=horizon,lag_mode=mode,maximum_factor_difference=delta,dfm_core_unchanged=True))
        states.extend(dict(target_quarter=target,horizon=horizon,lag_mode=mode,month=str(t.date()),value=float(v)) for t,v in zip(index,factors[:,0]))
        print(target,horizon,mode,delta,flush=True)
    pd.DataFrame(states).to_csv(OUT/'phase6b2_factor_series.csv',index=False,float_format='%.17g')
    pd.DataFrame(checks).to_csv(OUT/'phase6b2_factor_core_identity_checks.csv',index=False,float_format='%.17g')

if __name__=='__main__':
    main()
