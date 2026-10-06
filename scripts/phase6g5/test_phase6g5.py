"""Offline transformation, leakage, matched scoring and preservation checks."""
import json
import numpy as np
import pandas as pd
import pytest
from scripts.phase6g4.test_phase6g4 import synthetic
from scripts.phase6g4.core import signals, design, MODELS
from scripts.phase6g5.run import OUT, ROOT, verify
from scripts.phase6g5.report import vif, score
from scripts.phase6e.models import sw

def read(name):return pd.read_csv(OUT/f'phase6g5_{name}.csv',float_precision='round_trip')

def test_exact_transformations_and_base_invariance():
    m,cp,_,_=synthetic();s=signals(m,cp)
    np.testing.assert_allclose(s.real_m2_level,s.m2_level/s.cpi_index)
    x=s.dropna()
    np.testing.assert_allclose(x.real_m2,x.nominal_m2-x.cpi,atol=1e-11)
    np.testing.assert_allclose(x.cpi,100*np.log(x.cpi_index/s.cpi_index.shift(12).reindex(x.index)),atol=1e-11)
    expected=100*np.log((cp/100).rolling(12).apply(np.prod,raw=True))
    np.testing.assert_allclose(s.cpi.dropna(),expected.reindex(s.cpi.dropna().index),atol=1e-11)
    assert signals(m*10,cp).real_m2.sub(s.real_m2).dropna().abs().max()<1e-10

@pytest.mark.parametrize('model',MODELS)
def test_future_predictor_perturbation_does_not_change_design(model):
    m,cp,p,d=synthetic();s=signals(m,cp)
    a=design(p,d,s,'2025Q2','H2',model)[0]
    m.loc['2025-05-31':]=1e20;cp.loc['2025-05-31':]=999
    p.loc['2025-06-30':]=1e20
    b=design(p,d,signals(m,cp),'2025Q2','H2',model)[0]
    pd.testing.assert_frame_equal(a,b)

def test_future_and_unreleased_gdp_cannot_enter():
    events=pd.read_csv(ROOT/'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    k=sw.common.vintage_kernel();origin=pd.Timestamp('2025-05-31')
    a=k.available_gdp_vintage_as_of(events,origin,target='2025Q2')
    altered=events.copy()
    altered.loc[altered.quarter.ge('2025Q2')|pd.to_datetime(altered.publication_date).ge(origin),'value']=1e20
    b=k.available_gdp_vintage_as_of(altered,origin,target='2025Q2')
    pd.testing.assert_frame_equal(a.frame,b.frame);k.assert_boundary(a,'2025Q2')

def test_identical_origins_training_spans_and_actuals():
    f=read('common_sample_forecasts')
    assert f.groupby(['target_quarter','horizon']).model.nunique().eq(5).all()
    assert not f.duplicated(['model','target_quarter','horizon']).any()
    assert f.groupby(['target_quarter','horizon']).actual.nunique().eq(1).all()
    s=read('sample_comparison').query("sample == 'COMMON' and status == 'OK' and not current")
    for col in ['sample_start','sample_end','training_n']:
        assert s.groupby(['target_quarter','horizon'])[col].nunique().eq(1).all()

def test_metrics_are_computed_from_identical_errors():
    f=read('common_sample_forecasts');c=read('model_comparison')
    for row in c.itertuples():
        m=score(f.loc[f.model.eq(row.model)])
        assert abs(row.common_sample_pooled_rmse-m['rmse'])<1e-12
        assert row.n_matched_origins==m['n']

def test_vif_detects_identity_without_rejection_rule():
    rng=np.random.default_rng(4);x=pd.DataFrame(rng.normal(size=(50,2)),columns=['nominal_m2','cpi'])
    x['real_m2']=x.nominal_m2-x.cpi
    assert all(np.isinf(r['vif']) and r['diagnostic_only'] for r in vif(x))

def test_m0_reproduction_and_deterministic_full_refit():
    assert read('reproduction').passed.all()
    d=json.loads((OUT/'phase6g5_determinism.json').read_text())
    assert d['identical'] and d['files_checked']>=20

def test_production_configuration_and_artifacts_unchanged():
    assert verify()>900
    manifest=json.loads((OUT/'run_manifest.json').read_text())
    assert manifest['production_unchanged'] and not manifest['automatic_promotion']

def test_dashboard_and_final_classification():
    page=(OUT/'phase6g5_m0_m1_m2_m3_m4_comparison.html').read_text(encoding='utf8')
    assert 'NOT percentage-point GDP contributions' in page
    for label in ['Current M0','CPI only','Nominal M2 + CPI','Real M2 + CPI','Real M2 only']:assert label in page
    assert (OUT/'phase6g5_results.md').read_text(encoding='utf8').strip().splitlines()[-1]=='PHASE6G5_RETAIN_M0'

def test_missing_cpi_never_filled_and_duplicate_months_fail():
    m,cp,_,_=synthetic();cp.iloc[20]=np.nan
    assert signals(m,cp).cpi_index.iloc[20:].isna().all()
    with pytest.raises(ValueError,match='Duplicate'):signals(pd.concat([m,m.iloc[:1]]),cp)
