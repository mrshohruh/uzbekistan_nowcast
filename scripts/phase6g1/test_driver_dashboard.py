"""Offline checks for calculated research drivers and self-contained payload."""
import json
import re
import numpy as np
import pandas as pd
import pytest
from scripts.phase6g1.driver_dashboard import ROOT,OUT,HTML,COLUMNS,calculate
from scripts.phase6f.experiment import sha

def payload():
    return json.loads(re.search(r'<script id="driver-payload" type="application/json">(.*?)</script>',HTML.read_text(encoding='utf-8'),re.S).group(1))

def drivers():return pd.read_csv(OUT/'phase6g1_d2_current_drivers.csv',float_precision='round_trip')

def test_driver_formula_and_normalization():
    f=drivers();assert list(f)==COLUMNS
    np.testing.assert_allclose(f.signal,f.quarter_mean_z*f.loading,equal_nan=True)
    np.testing.assert_allclose(f.normalized_share_pct,100*f.signal.abs()/f.signal.abs().sum(),equal_nan=True)
    np.testing.assert_allclose(f.loading_share_pct,100*f.loading.abs()/f.loading.abs().sum())
    assert f.normalized_share_pct.sum()==pytest.approx(100.)
    assert f.loading_share_pct.sum()==pytest.approx(100.)
    assert f.signal.dropna().abs().is_monotonic_decreasing

def test_frozen_reproduction_and_comparison():
    f=pd.read_csv(OUT/'phase6g1_d0_vs_d2_driver_comparison.csv').set_index('indicator')
    m=f.loc['m2']
    assert m.D0_signal==pytest.approx(.72607378641098619,abs=1e-12)
    assert m.D0_signal_share_pct==pytest.approx(67.407878026807396,abs=1e-10)
    assert m.D2_signal_share_pct==pytest.approx(78.927310162613054,abs=1e-10)
    assert m.D2_loading_share_pct==pytest.approx(47.019632336906135,abs=1e-10)
    for model in ['D0','D2']:
        np.testing.assert_allclose(f[model+'_signal'],f[model+'_loading']*f[model+'_quarter_mean_z'],equal_nan=True)

def test_lag_source_date_and_value():
    f=drivers().set_index('indicator');m=f.loc['m2']
    assert pd.Period(m.latest_period,'M')+2==pd.Period(m.latest_factor_cell_period,'M')
    assert m.latest_period=='2026-07' and m.latest_factor_cell_period=='2026-09'
    source=pd.read_parquet(ROOT/'data/processed/m2.parquet').set_index('reference_period')
    assert m.latest_value==pytest.approx(source.loc[m.latest_period,'clean_value'])
    assert m.quarter_months_available==3

def test_pos_remains_missing_in_csv_and_payload():
    pos=drivers().set_index('indicator').loc['pos_turnover']
    assert pd.isna(pos.signal) and pd.isna(pos.normalized_share_pct) and pd.isna(pos.quarter_mean_z)
    assert pos.direction=='unavailable' and pos.quarter_months_available==0
    p=next(r for r in payload()['D2'] if r['indicator']=='pos_turnover')
    assert p['signal'] is None and p['normalized_share_pct'] is None
    html=HTML.read_text(encoding='utf-8')
    row=re.search(r'<div class="barrow"[^>]*data-indicator="pos_turnover".*?</b></div>',html).group(0)
    assert 'width:0%' in row and '>Unavailable<' in row

def test_payload_matches_csv_and_nowcasts():
    p=payload();f=drivers().set_index('indicator')
    for r in p['D2']:
        for key in ['signal','loading','quarter_mean_z','normalized_share_pct','loading_share_pct']:
            assert r[key] is None if pd.isna(f.loc[r['indicator'],key]) else r[key]==pytest.approx(f.loc[r['indicator'],key],abs=1e-12)
    n=p['nowcasts']
    assert n['D2']==pytest.approx(8.413700638995717,abs=1e-12)
    assert n['E2']==pytest.approx(.5*(n['D2']+n['U_MIDAS']),abs=1e-12)

def test_unchanged_umidas_channel():
    expected=pd.read_csv(ROOT/'results/phase6e/phase6e_current_drivers.csv')
    expected=expected.loc[expected.source_model.eq('U_MIDAS')].set_index('indicator')
    for row in payload()['UMIDAS']:
        assert row['signal']==pytest.approx(expected.loc[row['indicator'],'contribution_or_signal'],abs=1e-12)
    assert 'U-MIDAS is unchanged across the M2-lag comparison.' in HTML.read_text(encoding='utf-8')

def test_exact_visual_template_and_tooltip():
    html=HTML.read_text(encoding='utf-8');production=(ROOT/'dashboard/uzbekistan_nowcast_v2.html').read_text(encoding='utf-8')
    assert re.search(r'<style>(.*?)</style>',html,re.S).group(1)==re.search(r'<style>(.*?)</style>',production,re.S).group(1)
    for text in ['What is driving the M2-L2 nowcast?','Underlying M2 period: 2026-07','Factor-cell period: 2026-09',
        'Lag treatment: shifted two months in the DFM factor design','Quarter mean z:','Loading:','Signal share:','Loading share:',
        'not GDP contributions','Broad money · M2 (2-month lag)']:
        assert text in html
    assert 'NaN' not in html

def test_scaling_uses_own_training_data_and_missing_quarter():
    ix=pd.date_range('2025-01-31',periods=21,freq='ME')
    frame=pd.DataFrame({'m2':np.arange(21.)+10,'pos_turnover':np.arange(21.)+1},index=ix)
    frame.loc['2026-07-01':,'pos_turnover']=np.nan
    fit=dict(frame=frame,loadings=np.array([.5,-.2]))
    transformation={'m2':'money','pos_turnover':'pos'}
    result,mean,sd=calculate(fit,'D2','2026Q3',transformation)
    m=result.set_index('indicator').loc['m2']
    assert mean.m2==pytest.approx(frame.loc[:'2026-06-30','m2'].mean())
    assert m.quarter_mean_z==pytest.approx(((frame.loc['2026-07-01':,'m2']-mean.m2)/sd.m2).mean())
    frame.loc['2026-07-01':,'m2']=1e8
    _,later_mean,later_sd=calculate(fit,'D2','2026Q3',transformation)
    pd.testing.assert_series_equal(mean,later_mean);pd.testing.assert_series_equal(sd,later_sd)

def test_production_and_outputs_hashes():
    protected=json.loads((OUT/'phase6g1_protected_before.json').read_text())
    assert all(sha(ROOT/name)==digest for name,digest in protected.items())
    validation=json.loads((OUT/'phase6g1_driver_dashboard_validation.json').read_text())
    assert validation['production_unchanged']
    assert all(sha(ROOT/name)==digest for name,digest in validation['outputs'].items())
