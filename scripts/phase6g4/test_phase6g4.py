"""Offline identities, information discipline and persisted research contracts."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
import numpy as np
import pandas as pd
from types import SimpleNamespace
from scripts.phase6g4.core import signals,design,MODELS
from scripts.phase6e.models import FIELDS
from scripts.phase6g4.run import OUT,ROOT,verify

def synthetic():
    ix=pd.date_range('2018-01-31','2026-08-31',freq='ME')
    m=pd.Series(100*np.exp(np.arange(len(ix))*.02),index=ix)
    cp=pd.Series(100*np.exp(.005+np.sin(np.arange(len(ix)))*.001),index=ix)
    p=pd.DataFrame({field:np.arange(len(ix))+100. for field in FIELDS},index=ix)
    p['m2']=100*(np.log(m)-np.log(m.shift(12)))
    d=SimpleNamespace(release_lag_days={**{field:25 for field in FIELDS},'cpi_headline':10})
    return m,cp,p,d

def test_levels_and_exact_growth_identity():
    m,cp,_,_=synthetic();s=signals(m,cp)
    np.testing.assert_allclose(s.real_m2_level,s.m2_level/s.cpi_index)
    g=s.dropna(subset=['real_m2','nominal_m2','cpi'])
    np.testing.assert_allclose(g.real_m2,g.nominal_m2-g.cpi,atol=1e-11,rtol=0)

def test_no_future_cpi_or_m2_enters_origins():
    m,cp,p,d=synthetic();s=signals(m,cp)
    baseline=design(p,d,s,'2025Q2','H2',MODELS[3])[0]
    m.loc['2025-05-31':]=1e20;cp.loc['2025-05-31':]=999
    changed=design(p,d,signals(m,cp),'2025Q2','H2',MODELS[3])[0]
    pd.testing.assert_frame_equal(baseline,changed)
    assert baseline.m2.last_valid_index()<=pd.Timestamp('2025-04-30')
    assert baseline.cpi.last_valid_index()<=pd.Timestamp('2025-04-30')

def test_other_predictors_and_target_unchanged():
    m,cp,p,d=synthetic();s=signals(m,cp)
    base=design(p,d,s,'2025Q2','H2',MODELS[0])[0]
    for model in MODELS[1:]:
        frame=design(p,d,s,'2025Q2','H2',model)[0]
        pd.testing.assert_frame_equal(base.drop(columns='m2').reindex(frame.index),frame[list(x for x in FIELDS if x!='m2')])
    forecasts=pd.read_csv(OUT/'phase6g4_origin_forecasts.csv')
    old=pd.read_csv(ROOT/'results/phase6g/phase6g_origin_level_forecasts.csv').query("model == 'S0'")
    joined=forecasts.merge(old[['target_quarter','horizon','actual']],on=['target_quarter','horizon'],suffixes=('_new','_old'))
    np.testing.assert_array_equal(joined.actual_new,joined.actual_old)

def test_common_origins_and_training_spans_identical():
    f=pd.read_csv(OUT/'phase6g4_common_forecasts.csv')
    assert len(f)>0
    assert f.groupby(['target_quarter','horizon']).model.nunique().eq(5).all()
    s=pd.read_csv(OUT/'phase6g4_sample_comparison.csv')
    s=s.loc[s['sample'].eq('COMMON')&s.status.eq('OK')]
    for field in ['sample_start','sample_end','training_n']:
        assert s.groupby(['target_quarter','horizon'])[field].nunique().eq(1).all()

def test_m0_reproduces_saved_benchmark():
    f=pd.read_csv(OUT/'phase6g4_reproduction.csv')
    assert f.passed.all() and f.current.any()
    assert f.error.abs().max()<1e-7

def test_deterministic_rerun_and_production_unchanged():
    check=json.loads((OUT/'phase6g4_determinism.json').read_text())
    assert check['identical'] and check['files_checked']>10
    assert verify()>0

def test_missing_index_is_not_filled():
    m,cp,_,_=synthetic();cp.iloc[20]=np.nan
    assert signals(m,cp).cpi_index.iloc[20:].isna().all()
