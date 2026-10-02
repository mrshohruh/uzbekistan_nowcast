"""Offline tests of the information boundary and research governance."""
import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from experiment import (DOMESTIC, SERVICES, REGIME, KEYS, Spec, masked_panel,
                        prepare, sign_normalize, matched_pair, estimate, bridge)
from uznowcast.models.data import horizon_month_end, information_cutoff_for_variable


def sample():
    index = pd.date_range('2021-01-31','2025-03-31',freq='ME')
    rng = np.random.default_rng(10)
    frame = pd.DataFrame(rng.normal(size=(len(index),4)), index=index, columns=DOMESTIC+(SERVICES,))
    regimes = pd.Series(np.where(index>=pd.Timestamp('2024-09-30'), REGIME, 'before_2024_09'),index=index)
    frame.loc[regimes.eq(REGIME),SERVICES] += 20
    return frame, regimes


@pytest.mark.parametrize('horizon', ['H1','H2','H3'])
@pytest.mark.parametrize('mode', ['standard','conservative'])
def test_exact_frozen_masks(horizon, mode):
    frame, _ = sample()
    lags = dict(zip(DOMESTIC,[33,27,24]))
    masked, cutoffs = masked_panel(frame,DOMESTIC,'2025Q1',horizon,lags,mode)
    origin=horizon_month_end('2025Q1',horizon)
    assert masked.index.max() == origin
    for f in DOMESTIC:
        cutoff=information_cutoff_for_variable(origin,f,lags,mode)
        assert cutoffs[f] == str(cutoff.date())
        pd.testing.assert_series_equal(masked[f].loc[:cutoff],frame[f].loc[:cutoff])
        assert masked.loc[masked.index>cutoff,f].isna().all()


def test_training_only_scaling_and_break():
    frame, regimes = sample()
    end=pd.Timestamp('2024-12-31')
    z,means,stds,diag,adjusted=prepare(frame,regimes,end,True)
    changed=frame.copy()
    changed.loc[changed.index>end] += 100000
    z2,m2,s2,d2,a2=prepare(changed,regimes,end,True)
    pd.testing.assert_series_equal(means,m2)
    pd.testing.assert_series_equal(stds,s2)
    assert diag == d2
    pd.testing.assert_frame_equal(z.loc[:end],z2.loc[:end])
    expected=frame.loc[(frame.index<=end)&regimes.eq(REGIME),SERVICES].mean()-frame.loc[(frame.index<=end)&~regimes.eq(REGIME),SERVICES].mean()
    assert diag['regime_adjustment'] == pytest.approx(expected)
    assert z.loc[:end].mean().abs().max()<1e-12
    assert np.allclose(z.loc[:end].std(),1)


def test_unseen_services_regime_not_estimated_from_future():
    frame, regimes=sample()
    _,_,_,diag,adjusted=prepare(frame,regimes,pd.Timestamp('2024-08-31'),True)
    assert not diag['regime_identified']
    assert diag['regime_adjustment']==0
    pd.testing.assert_frame_equal(frame,adjusted)


def test_import_alias_and_explicit_services_fallback():
    from experiment import IMPORTS
    frame,_=sample()
    frame[IMPORTS]=frame.industrial_production
    masked,cutoffs=masked_panel(frame,(IMPORTS,SERVICES),'2025Q1','H2',{'imports_total':26})
    origin=horizon_month_end('2025Q1','H2')
    assert cutoffs[IMPORTS]==str(information_cutoff_for_variable(origin,'imports_total',{'imports_total':26}).date())
    assert cutoffs[SERVICES]==str(information_cutoff_for_variable(origin,'services_output',{}).date())


def test_sign_invariant_reconstruction():
    load=np.array([[-2.,3.],[1.,-2.]])
    factor=np.array([[4.,5.],[1.,2.]])
    l,f,sign=sign_normalize(load,factor)
    assert (l[0]>0).all()
    np.testing.assert_allclose(f@l.T,factor@load.T)


def test_matching_excludes_unmatched_and_rejects_duplicates():
    frame=pd.DataFrame(dict(target_quarter=['2024Q1','2024Q2'],horizon=['H1','H1'],lag_mode=['standard']*2,actual=[5.,6.],prediction=[4.,5.]))
    benchmark=frame.iloc[[1]].copy()
    assert matched_pair(frame,benchmark).target_quarter.tolist()==['2024Q2']
    rematched=matched_pair(matched_pair(frame,benchmark),benchmark)
    assert rematched.target_quarter.tolist()==['2024Q2']
    with pytest.raises(ValueError,match='duplicate'):
        matched_pair(pd.concat([frame,frame]),benchmark)
    benchmark.actual=99
    with pytest.raises(ValueError,match='mismatch'):
        matched_pair(frame,benchmark)


def test_filter_one_sided_with_fixed_training_parameters():
    from statsmodels.tsa.statespace.dynamic_factor import DynamicFactor
    frame,_=sample()
    model=DynamicFactor(frame[list(DOMESTIC)],k_factors=1,factor_order=1,error_cov_type='diagonal')
    params=np.array([1.,.8,.7,.5,.5,.5,.6])
    prefix=model.filter(params).factors.filtered[:,:36]
    changed=frame[list(DOMESTIC)].copy()
    changed.iloc[36:]+=1000
    other=DynamicFactor(changed,k_factors=1,factor_order=1,error_cov_type='diagonal').filter(params)
    np.testing.assert_allclose(prefix,other.factors.filtered[:,:36])
    assert 'factors.filtered' in inspect.getsource(estimate)
    assert 'smoothed' not in inspect.getsource(estimate)


def test_no_future_observations_in_origin():
    frame,regimes=sample()
    masked,_=masked_panel(frame,DOMESTIC+(SERVICES,),'2024Q4','H1',{'industrial_production':33,'construction':27,'retail_trade':24})
    changed=frame.copy();changed.loc[changed.index>pd.Timestamp('2024-10-31')]+=999999
    masked2,_=masked_panel(changed,DOMESTIC+(SERVICES,),'2024Q4','H1',{'industrial_production':33,'construction':27,'retail_trade':24})
    pd.testing.assert_frame_equal(masked,masked2)


def test_bridge_ignores_future_target_values():
    index=pd.date_range('2021-01-31','2024-03-31',freq='ME')
    rng=np.random.default_rng(30)
    factors=rng.normal(size=(len(index),1))
    gdp=pd.Series(rng.normal(size=17),index=pd.period_range('2020Q1','2024Q1',freq='Q').astype(str))
    value=bridge(factors,index,gdp,'2024Q1','BRIDGE_B')[0]
    gdp.loc['2024Q1']=999999
    assert bridge(factors,index,gdp,'2024Q1','BRIDGE_B')[0]==value


def test_protected_inventory_unchanged():
    import hashlib
    root=Path(__file__).resolve().parents[3]
    baseline=json.loads((root/'results/research/phase6b/phase6b_protected_before.json').read_text())
    assert len(baseline)>400
    for path,checksum in baseline.items():
        assert hashlib.sha256((root/path).read_bytes()).hexdigest()==checksum,path


def test_protection_fails_loudly_without_modifying_files(monkeypatch):
    import run
    real_hash=run.sha
    baseline=json.loads((run.OUT/'phase6b_protected_before.json').read_text())
    chosen=next(iter(baseline))
    monkeypatch.setattr(run,'sha',lambda path:'SIMULATED_CHANGED_HASH' if path==run.ROOT/chosen else real_hash(path))
    with pytest.raises(RuntimeError,match='Protected artifacts changed'):
        run.protect()


def test_saved_forecasts_use_only_filtered_states():
    root=Path(__file__).resolve().parents[3]
    path=root/'results/research/phase6b/phase6b_factor_series.csv'
    if not path.exists():
        pytest.skip('experiment not run yet')
    states=pd.read_csv(path)
    assert not states.loc[states.forecast_eligible.eq(True),'factor_source'].str.contains('SMOOTHED').any()
    forecasts=pd.read_csv(root/'results/research/phase6b/phase6b_forecasts.csv')
    assert (forecasts.n_GDP_quarters.dropna()>=12).all()
    assert not forecasts.target_quarter.eq('2026Q3').any()
