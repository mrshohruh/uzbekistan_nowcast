"""GDP gate regressions and preservation of the immutable monthly DFM core."""
import inspect
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0,str(Path(__file__).parent))
from boundary import release_metadata,available_gdp_as_of,bridge,AvailableGDP
from reproduce import ROOT,old_core
from uznowcast.models.data import horizon_month_end,information_cutoff_for_variable


def inputs():
    gdp=pd.read_parquet(ROOT/'data/master/gdp_quarterly.parquet').set_index('quarter').gdp_real_yoy_pct
    meta=release_metadata(gdp,31)
    state=pd.read_csv(ROOT/'results/research/phase6b/phase6b_factor_series.csv')
    state=state.loc[state.specification.eq('DFM_DOMESTIC_3') & state.target_quarter.eq('2024Q2') &
                    state.horizon.eq('H1') & state.lag_mode.eq('standard') & state.factor.eq(1)].sort_values('month')
    return gdp,meta,state.value.to_numpy().reshape(-1,1),pd.DatetimeIndex(pd.to_datetime(state.month))


def forecast(gdp,meta,factors,index,origin,name):
    avail=available_gdp_as_of(gdp,meta,origin,target='2024Q2')
    try:
        value,diag=bridge(factors,index,avail,'2024Q2',name,origin)
        return value,diag
    except ValueError as exc:
        return None,str(exc)


@pytest.mark.parametrize('name',['BRIDGE_A','BRIDGE_B'])
def test_unreleased_prior_GDP_immutability(name):
    gdp,meta,factors,index=inputs()
    origin=pd.Timestamp('2024-04-30')
    old=forecast(gdp,meta,factors,index,origin,name)
    changed=gdp.copy();changed.loc['2024Q1']=999999
    repaired=forecast(changed,meta,factors,index,origin,name)
    assert repaired==old
    if name=='BRIDGE_B':
        assert repaired==(None,'PRIOR_QUARTER_GDP_NOT_AVAILABLE')
    else:
        original=old_core()
        before=original.bridge(factors,index,gdp.loc[gdp.index<'2024Q2'],'2024Q2',name)[0]
        after=original.bridge(factors,index,changed.loc[changed.index<'2024Q2'],'2024Q2',name)[0]
        assert before!=after,'Regression must expose old Bridge A training leakage'


def test_released_prior_GDP_responsiveness():
    gdp,meta,factors,index=inputs()
    origin=pd.Timestamp('2024-05-31')
    before=forecast(gdp,meta,factors,index,origin,'BRIDGE_B')[0]
    changed=gdp.copy();changed.loc['2024Q1']+=1
    after=forecast(changed,meta,factors,index,origin,'BRIDGE_B')[0]
    assert before is not None and abs(before-after)>1e-6


@pytest.mark.parametrize('name',['BRIDGE_A','BRIDGE_B'])
def test_target_GDP_immutability(name):
    gdp,meta,factors,index=inputs()
    before=forecast(gdp,meta,factors,index,pd.Timestamp('2024-05-31'),name)
    changed=gdp.copy();changed.loc['2024Q2']=999999
    assert before==forecast(changed,meta,factors,index,pd.Timestamp('2024-05-31'),name)


def test_every_bridge_dependent_and_lag_is_available():
    gdp,meta,factors,index=inputs()
    origin=pd.Timestamp('2024-05-31')
    _,diag=forecast(gdp,meta,factors,index,origin,'BRIDGE_B')
    assert meta.loc[diag['training_quarters'],'available_date'].le(origin).all()
    assert meta.loc[diag['lagged_quarters'],'available_date'].le(origin).all()


def test_bridge_rejects_unrestricted_series_and_unreleased_rows():
    gdp,meta,factors,index=inputs();origin=pd.Timestamp('2024-04-30')
    with pytest.raises(TypeError):
        bridge(factors,index,gdp,'2024Q2','BRIDGE_A',origin)
    frame=meta.loc[meta.index<'2024Q2'].copy();frame['value']=gdp.reindex(frame.index)
    with pytest.raises(AssertionError,match='unreleased'):
        bridge(factors,index,AvailableGDP(frame,origin),'2024Q2','BRIDGE_A',origin)


def test_target_never_allowed_even_with_bad_release_metadata():
    gdp,meta,factors,index=inputs();origin=pd.Timestamp('2024-05-31')
    meta.loc['2024Q2','available_date']=pd.Timestamp('2024-01-01')
    available=available_gdp_as_of(gdp,meta,origin,target='2024Q2')
    assert '2024Q2' not in available.frame.index
    assert '2024Q2' in available_gdp_as_of(gdp,meta,origin).frame.index
    with pytest.raises(AssertionError,match='target_GDP'):
        bridge(factors,index,available_gdp_as_of(gdp,meta,origin),'2024Q2','BRIDGE_A',origin)


def test_unknown_dates_unavailable_and_equality_boundary_inclusive():
    gdp,meta,_,_=inputs();origin=meta.loc['2024Q1','available_date']
    assert '2024Q1' in available_gdp_as_of(gdp,meta,origin).frame.index
    assert '2024Q1' not in available_gdp_as_of(gdp,meta,origin-pd.Timedelta(days=1)).frame.index
    meta.loc['2024Q1','available_date']=pd.NaT
    assert '2024Q1' not in available_gdp_as_of(gdp,meta,origin).frame.index


def test_release_hierarchy_prefers_verified_dates_and_rejects_updates():
    gdp,_,_,_=inputs()
    historical=pd.DataFrame([
        dict(quarter='2024Q1',release_date='2024-04-25',release_date_quality='VERIFIED_ACTUAL_RELEASE_DATE',release_date_source='official verified publication fixture'),
        dict(quarter='2024Q1',release_date='2024-04-20',release_date_quality='DOCUMENTED_RULE',release_date_source='historical metadata fixture'),
        dict(quarter='2023Q4',release_date='2024-01-01',release_date_quality='DATASET_UPDATE_TIMESTAMP',release_date_source='not an observation release')])
    meta=release_metadata(gdp,31,historical)
    assert meta.loc['2024Q1','available_date']==pd.Timestamp('2024-04-25')
    assert meta.loc['2024Q1','release_date_verified']
    assert meta.loc['2023Q4','release_date_quality']=='APPROXIMATE_FALLBACK'
    assert pd.isna(meta.loc['2023Q4','release_date'])
    # Missing both historical evidence and a justified lag never means available.
    unknown=release_metadata(gdp,None)
    assert available_gdp_as_of(gdp,unknown,pd.Timestamp('2030-01-01')).frame.empty


def test_observed_release_cannot_be_overridden_by_earlier_fallback():
    gdp,meta,_,_=inputs()
    meta.loc['2024Q1','release_date_quality']='VERIFIED_ACTUAL_RELEASE_DATE'
    meta.loc['2024Q1','release_date']=pd.Timestamp('2024-06-01')
    meta.loc['2024Q1','available_date']=pd.Timestamp('2024-01-01')
    assert '2024Q1' not in available_gdp_as_of(gdp,meta,pd.Timestamp('2024-05-31')).frame.index


@pytest.mark.parametrize('horizon',['H1','H2','H3'])
@pytest.mark.parametrize('mode',['standard','conservative'])
def test_exact_ragged_edge_and_future_monthly_immutability(horizon,mode):
    core=old_core()
    idx=pd.date_range('2021-01-31','2024-06-30',freq='ME')
    rng=np.random.default_rng(44)
    frame=pd.DataFrame(rng.normal(size=(len(idx),3)),index=idx,columns=core.DOMESTIC)
    lags=dict(zip(core.DOMESTIC,[33,27,24]))
    masked,cutoffs=core.masked_panel(frame,core.DOMESTIC,'2024Q2',horizon,lags,mode)
    origin=horizon_month_end('2024Q2',horizon)
    changed=frame.copy()
    for field in core.DOMESTIC:
        cutoff=information_cutoff_for_variable(origin,field,lags,mode)
        assert cutoffs[field]==str(cutoff.date())
        changed.loc[changed.index>cutoff,field]=999999
        assert masked.loc[masked.index>cutoff,field].isna().all()
    masked2,_=core.masked_panel(changed,core.DOMESTIC,'2024Q2',horizon,lags,mode)
    pd.testing.assert_frame_equal(masked,masked2)
    timeline=masked.reindex(idx)
    assert timeline.loc[timeline.index>origin].isna().all().all()


def test_filter_not_smoother_and_future_fixed_parameter_invariance():
    from statsmodels.tsa.statespace.dynamic_factor import DynamicFactor
    rng=np.random.default_rng(8);frame=pd.DataFrame(rng.normal(size=(45,3)),columns=['a','b','c'])
    kwargs=dict(k_factors=1,factor_order=1,error_cov_type='diagonal',error_order=0,enforce_stationarity=True)
    params=np.array([1.,.8,.7,.5,.5,.5,.6])
    prefix=DynamicFactor(frame,**kwargs).filter(params).factors.filtered[:,:36]
    changed=frame.copy();changed.iloc[36:]=999999
    np.testing.assert_allclose(prefix,DynamicFactor(changed,**kwargs).filter(params).factors.filtered[:,:36])
    source=inspect.getsource(old_core().estimate)
    assert 'factors.filtered' in source and 'smoothed' not in source


def test_training_only_scaling_unchanged():
    core=old_core();rng=np.random.default_rng(9)
    index=pd.date_range('2021-01-31','2024-06-30',freq='ME')
    frame=pd.DataFrame(rng.normal(size=(len(index),3)),index=index,columns=core.DOMESTIC)
    regime=pd.Series('before_2024_09',index=index)
    before=core.prepare(frame,regime,pd.Timestamp('2024-03-31'),False)
    changed=frame.copy();changed.loc['2024-04-30':]=999999
    after=core.prepare(changed,regime,pd.Timestamp('2024-03-31'),False)
    pd.testing.assert_series_equal(before[1],after[1]);pd.testing.assert_series_equal(before[2],after[2])


def test_protected_artifacts():
    from run import protect
    assert len(protect())>=538


def test_clean_benchmark_unreleased_prior_immutability():
    from run import clean_benchmarks
    from uznowcast.models.data import load_dataset
    from dataclasses import replace
    gdp,meta,_,_=inputs();origin=pd.Timestamp('2024-04-30');dataset=load_dataset(ROOT)
    a=available_gdp_as_of(gdp,meta,origin,target='2024Q2')
    before=clean_benchmarks(dataset,a,'2024Q2','H1','standard')
    changed=gdp.copy();changed.loc['2024Q1']=999999
    b=available_gdp_as_of(changed,meta,origin,target='2024Q2')
    other=replace(dataset,gdp=pd.DataFrame({'quarter':changed.index,'gdp_real_yoy_pct':changed.to_numpy()}))
    after=clean_benchmarks(other,b,'2024Q2','H1','standard')
    assert list(before)==list(after)
    for k in before:
        assert np.isnan(before[k][0]) and np.isnan(after[k][0])
        assert before[k][1]==after[k][1]


def test_saved_training_audit_and_core_identity():
    path=ROOT/'results/research/phase6b1/phase6b1_bridge_training_information_audit.csv'
    if not path.exists():
        pytest.skip('run not completed')
    audit=pd.read_csv(path)
    assert pd.to_datetime(audit.dependent_GDP_available_date).le(pd.to_datetime(audit.forecast_origin_date)).all()
    lag=audit.dropna(subset=['lag_GDP_available_date'])
    assert pd.to_datetime(lag.lag_GDP_available_date).le(pd.to_datetime(lag.forecast_origin_date)).all()
    core=pd.read_csv(path.parent/'phase6b1_factor_core_identity_checks.csv')
    assert core.maximum_factor_difference.max()<1e-8
    forecasts=pd.read_csv(path.parent/'phase6b1_forecasts.csv')
    b=forecasts.loc[forecasts.model.eq('DFM_DOMESTIC_3__BRIDGE_B_CLEAN') & forecasts.horizon.eq('H1')]
    assert len(b)==20 and b.prediction.isna().all()
    assert b.failure.eq('PRIOR_QUARTER_GDP_NOT_AVAILABLE').all()
