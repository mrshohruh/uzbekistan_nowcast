"""Offline Phase 6I mathematical and frozen-artifact regression checks."""
from dataclasses import replace
import json
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from scripts.phase6i.models import SPECS, KEYS, vector, estimate, common_sample
from scripts.phase6i.run import ROOT, current_inputs
from scripts.production.models import umidas, sw
from scripts.operations.state import sha
from scripts.operations.prospective.inputs import eligible
from uznowcast.models.data import load_dataset, build_information_set, horizon_month_end, information_cutoff_for_variable

OUT=ROOT/'results/phase6i'


@pytest.fixture(scope='module')
def dataset():return load_dataset(ROOT)


def read(name):return pd.read_csv(OUT/f'phase6i_{name}.csv',float_precision='round_trip')


def test_exact_u0_reproduction():
    r=read('u0_reproduction')
    assert len(r)==49
    np.testing.assert_allclose(r.research,r.production_recomputed,rtol=0,atol=1e-12)
    np.testing.assert_allclose(r.research,r.frozen,rtol=0,atol=1e-7)


@pytest.mark.parametrize('key',KEYS)
def test_registry_transformations(dataset,key):
    frame=pd.read_parquet(ROOT/f'data/processed/{key}.parquet')
    if key=='usd_uzs':
        frame=frame.loc[frame.frequency.eq('M')]
        level='monthly_mean';lag=1
    else:
        level='raw_value' if key=='m2' else 'monthly_flow';lag=12
    frame=frame.sort_values('reference_period').drop_duplicates('reference_period',keep='last')
    series=pd.Series(frame[level].to_numpy(),index=pd.PeriodIndex(frame.reference_period,freq='M'))
    series=series.reindex(pd.period_range(series.index.min(),series.index.max(),freq='M'))
    expected=100*np.log(series/series.shift(lag))
    actual=pd.Series(frame.clean_value.to_numpy(),index=pd.PeriodIndex(frame.reference_period,freq='M')).reindex(series.index)
    valid=expected.notna()&actual.notna()&np.isfinite(expected)
    assert valid.sum()>12
    np.testing.assert_allclose(actual[valid],expected[valid],rtol=0,atol=1e-9)
    assert dataset.clean_field_by_key['retail_trade']=='retail_yoy_log'


@pytest.mark.parametrize('horizon',['H1','H2','H3'])
def test_alignment_and_horizon_availability(dataset,horizon):
    target='2025Q2'
    v=vector(dataset,KEYS,target,horizon)
    for i,key in enumerate(KEYS):
        field=dataset.clean_field_by_key[key]
        info=build_information_set(dataset,target,horizon,[field])[field].dropna()
        cutoff=information_cutoff_for_variable(horizon_month_end(target,horizon),key,dataset.release_lag_days)
        assert info.index.max()<=cutoff
        np.testing.assert_array_equal(v[i*3:(i+1)*3],info.tail(3))


def test_no_future_predictor_leakage(dataset):
    monthly=dataset.monthly.copy()
    origin=horizon_month_end('2024Q4','H2')
    for key in KEYS:
        cutoff=information_cutoff_for_variable(origin,key,dataset.release_lag_days)
        monthly.loc[monthly.index>cutoff,dataset.clean_field_by_key[key]]=1e12
    changed=replace(dataset,monthly=monthly)
    np.testing.assert_array_equal(vector(dataset,KEYS,'2024Q4','H2'),vector(changed,KEYS,'2024Q4','H2'))


def test_current_retrieval_and_release_gating():
    f=pd.DataFrame({'retrieved_at':['2026-09-01T00:00Z','2026-11-01T00:00Z','2026-09-01T00:00Z'],
                    'source_release_date':[None,None,'2026-11-02T00:00Z']})
    assert eligible(f,pd.Timestamp('2026-10-05T00:00Z')).index.tolist()==[0]


def test_gdp_strict_boundary():
    events=pd.read_csv(ROOT/'data/current/gdp_vintages.csv')
    available=sw.common.vintage_kernel().available_gdp_vintage_as_of(events,pd.Timestamp('2025-01-31'),target='2025Q1',timing_rule='STRICT')
    assert all(q<'2025Q1' for q in available.frame.index)
    sw.common.vintage_kernel().assert_boundary(available,'2025Q1')


def test_common_sample_construction():
    f=pd.DataFrame([dict(origin=str(i),target_quarter='2025Q1',horizon='H1',actual=5.,evaluation_group='HOLDOUT',model=m,prediction=np.nan if (i==1 and m=='U1') else 4.) for i in range(3) for m in ['U0','U1']])
    assert common_sample(f,['U0','U1']).origin.tolist()==['0','2']
    with pytest.raises(ValueError):common_sample(pd.concat([f,f.iloc[:1]]),['U0','U1'])


def test_strict_sample_identical():
    f=read('common_sample_forecasts')
    assert not f[['U0','U1','U2','U3','U4','U5','U6']].isna().any().any()
    scores=read('horizon_metrics')
    strict=scores.loc[scores['sample'].eq('strict_common')]
    assert strict.groupby(['evaluation_group','horizon']).n_origins.nunique().eq(1).all()


def test_current_reconstruction_and_deterministic_fit(dataset):
    ds,available,info,origin,current,_=current_inputs(dataset)
    for model,keys in SPECS.items():
        a,diag=estimate(ds,available,keys,info['target'],info['horizon'])
        b,_=estimate(ds,available,keys,info['target'],info['horizon'])
        assert a==b
        assert abs(a-np.dot(diag['coefficients'],diag['regressor_values']))<1e-12
        stored=read('current_nowcasts').set_index('model').loc[model,'current_nowcast']
        assert abs(a-stored)<1e-12
    assert current['final_forecast']==8.180901340616275


def test_missing_predictor_fails(dataset):
    ds,available,info,*_=current_inputs(dataset)
    monthly=ds.monthly.copy();monthly['retail_yoy_log']=np.nan
    value,diag=estimate(replace(ds,monthly=monthly),available,SPECS['U6'],info['target'],info['horizon'])
    assert np.isnan(value) and diag['failure']=='fewer_than_15_training_rows'


def test_protected_artifacts_unchanged():
    manifest=json.loads((OUT/'phase6i_run_manifest.json').read_text())
    assert manifest['protected_hashes_before']==manifest['protected_hashes_after']
    for path,expected in manifest['protected_hashes_before'].items():
        assert sha(ROOT/path)==expected,path
    assert manifest['production_changed'] is False


def test_self_contained_dashboard():
    content=(OUT/'phase6i_umidas_comparison.html').read_text(encoding='utf8')
    assert '<svg' in content and '<script src=' not in content and '<link ' not in content
    assert 'PRODUCTION UNCHANGED' in content
