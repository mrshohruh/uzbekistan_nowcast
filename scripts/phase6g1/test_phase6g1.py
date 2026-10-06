"""Offline mathematical and persisted research-contract checks."""
import json
import numpy as np
import pandas as pd
import pytest
from scripts.phase6g1 import diagnostics as d
from scripts.phase6g1.run import ROOT
from scripts.phase6f.experiment import sha

OUT=ROOT/'results/phase6g1'

def read(name):
    return pd.read_csv(OUT/f'phase6g1_{name}.csv')

def test_missing_signals_excluded_without_imputation():
    result=d.shares(pd.Series([2.,-1.,np.nan]))
    assert result.iloc[0]==pytest.approx(200/3)
    assert result.iloc[1]==pytest.approx(100/3)
    assert pd.isna(result.iloc[2])

def test_zero_and_all_missing_denominators():
    assert d.shares(pd.Series([0.,0.])).isna().all()
    assert d.shares(pd.Series([np.nan,np.nan])).isna().all()

def test_training_only_standardization():
    ix=pd.date_range('2020-01-31',periods=15,freq='ME')
    frame=pd.DataFrame({'m2':np.arange(15.)},index=ix)
    kernel=d.sw.common.kernel()
    z,mean,scale=kernel.standardize(frame,ix[11],False)
    assert mean.m2==pytest.approx(5.5)
    assert scale.m2==pytest.approx(np.std(np.arange(12.),ddof=1))
    frame.iloc[12:]=1e9
    other,m,s=kernel.standardize(frame,ix[11],False)
    pd.testing.assert_series_equal(mean,m);pd.testing.assert_series_equal(scale,s)
    pd.testing.assert_frame_equal(z.iloc[:12],other.iloc[:12])

def test_real_money_requires_twelve_consecutive_months():
    ix=pd.date_range('2020-01-31',periods=14,freq='ME')
    nominal=pd.Series(20.,index=ix);cpi=pd.Series(1.,index=ix)
    real,inflation=d.real_money(nominal,cpi)
    assert real.iloc[:11].isna().all()
    assert real.iloc[11]==8.
    cpi.iloc[5]=np.nan
    assert d.real_money(nominal,cpi)[0].isna().all()

def test_future_cpi_cannot_change_past_real_money():
    ix=pd.date_range('2020-01-31',periods=24,freq='ME')
    nominal=pd.Series(20.,index=ix);cpi=pd.Series(1.,index=ix)
    before=d.real_money(nominal,cpi)[0];cpi.iloc[-1]=100.
    pd.testing.assert_series_equal(before.iloc[:-1],d.real_money(nominal,cpi)[0].iloc[:-1])

def sample_forecasts():
    return pd.DataFrame([dict(forecast_origin='2024-03-31',target_quarter='2024Q1',horizon='H3',model=model,prediction=value,actual=6.)
                         for model,value in [('D0',6.1),('D1',np.nan)]])

def test_common_sample_does_not_replace_failed_model():
    assert d.common_sample(sample_forecasts(),['D0','D1']).empty

def test_common_sample_rejects_duplicate_origin():
    f=sample_forecasts()
    with pytest.raises(ValueError,match='Duplicate origin'):d.common_sample(pd.concat([f,f]),['D0','D1'])

def test_common_sample_rejects_different_actual_vintages():
    f=sample_forecasts();f.loc[f.model.eq('D1'),'actual']=7.
    with pytest.raises(ValueError,match='Actual vintages differ'):d.common_sample(f,['D0','D1'])

def test_reproduction_gate_complete():
    f=read('reproduction_check')
    assert len(f)==140 and f.passed.all()
    assert f.error.abs().max()<1e-9

def test_raw_signal_reconstruction():
    f=read('m2_signal_reconstruction')
    np.testing.assert_allclose(100*np.log(f.raw_M2_level/f.raw_M2_year_ago),f.transformed_value,atol=1e-10)
    np.testing.assert_allclose((f.transformed_value-f.training_mean)/f.training_std,f.standardized_value)
    np.testing.assert_allclose(f.quarter_mean_z*f.factor_loading,f.signal_M2)
    np.testing.assert_allclose(100*f.signal_M2.abs()/f.absolute_signal_sum,f.signal_share_pct)

def test_driver_nulls_and_seven_field_no_m2():
    f=read('current_driver_comparison');g=f[f.model.eq('D1')]
    assert len(g)==7 and 'm2' not in set(g.indicator)
    for _,group in f.groupby('model'):
        assert group.absolute_signal_share_pct.sum()==pytest.approx(100.)
        assert group.absolute_loading_share_pct.sum()==pytest.approx(100.)
        assert group.loc[~group.available_flag,'absolute_signal_share_pct'].isna().all()

def test_fixed_ensemble_current():
    f=read('current_nowcasts')
    np.testing.assert_allclose(2*f.ensemble_nowcast-f.DFM_nowcast,8.060649795767965)

def test_publication_gates():
    f=read('origin_availability')
    assert f.publication_mask_pass.all() and f.CPI_parent_mask_pass.all() and f.GDP_boundary_pass.all()
    assert not f.revision_value_leakage_resolved.any()

def test_determinism_and_protected_files():
    result=json.loads((OUT/'phase6g1_determinism.json').read_text())
    assert result['identical_csv_hashes'] and result['first']==result['second']
    for name,digest in result['second'].items():assert sha(OUT/name)==digest
    before=json.loads((OUT/'phase6g1_protected_before.json').read_text())
    after=json.loads((OUT/'phase6g1_protected_after.json').read_text())
    assert before==after and len(before)>=680
    for name,digest in before.items():assert sha(ROOT/name)==digest

def test_benchmark_and_reduced_samples_explicit():
    f=read('model_comparison')
    assert 44 in set(f.N) and 36 in set(f.N) and 18 in set(f.N)

def test_report_final_recommendation():
    report=(OUT/'phase6g1_results.md').read_text(encoding='utf-8')
    assert report.rstrip().endswith('MODEL RECOMMENDATION:\nKEEP_CURRENT_DFM_AND_MONITOR_M2')
    assert 'M2 DIAGNOSIS:\nM2_DOMINANT_BUT_USEFUL' in report
