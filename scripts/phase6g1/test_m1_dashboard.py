"""Offline lag, common-sample and shared-scale dashboard contracts."""
import json
import re
import numpy as np
import pandas as pd
import pytest
from scripts.phase6g1.m1_dashboard import ROOT,OUT,FILES,LABEL,driver_frame,summary
from scripts.phase6f.experiment import sha,lagged_dfm
from scripts.phase6e.models import sw

def payload(path):
    return json.loads(re.search(r'<script id="driver-payload" type="application/json">(.*?)</script>',path.read_text(encoding='utf-8'),re.S).group(1))

def models():return pd.read_csv(FILES[2],float_precision='round_trip').set_index('model')

def test_exact_nowcasts_and_fixed_weights():
    m=models();np.testing.assert_allclose(m.dfm_nowcast,[8.301152885464585,8.3713078492157,8.413700638995717],rtol=0,atol=1e-12)
    np.testing.assert_allclose(m.u_midas_nowcast,8.060649795767965,rtol=0,atol=1e-12)
    np.testing.assert_allclose(m.ensemble_50_50,.5*(m.dfm_nowcast+m.u_midas_nowcast),rtol=0,atol=1e-12)

def test_metrics_copied_from_same_phase6f_sample():
    m=models();source=pd.read_csv(ROOT/'results/phase6f/phase6f_horizon_metrics.csv',float_precision='round_trip')
    for model in m.index:
        s=source.loc[source.model.eq(model)&source['sample'].eq('PAIRWISE_COMMON')].set_index('horizon')
        assert s.loc['POOLED','N']==12 and (s.loc[['H1','H2','H3'],'N']==4).all()
        for h in ['H1','H2','H3']:assert m.loc[model,h+'_RMSE']==s.loc[h,'RMSE']
        assert m.loc[model,'pooled_RMSE']==s.loc['POOLED','RMSE']
    assert set(m.sample_label)=={LABEL}

def test_signals_and_both_denominators():
    p=payload(FILES[4])
    for rows in p['drivers'].values():
        f=pd.DataFrame(rows)
        np.testing.assert_allclose(f.signal,f.quarter_mean_z*f.loading,equal_nan=True)
        np.testing.assert_allclose(f.signal_share_pct,100*f.signal.abs()/f.signal.abs().sum(),equal_nan=True)
        np.testing.assert_allclose(f.loading_share_pct,100*f.loading.abs()/f.loading.abs().sum())
        assert f.signal.abs().dropna().is_monotonic_decreasing

def test_pos_not_current_value_or_signal():
    for rows in payload(FILES[4])['drivers'].values():
        r=next(x for x in rows if x['indicator']=='pos_turnover')
        assert r['signal'] is None and r['latest_value'] is None and r['signal_share_pct'] is None
        assert r['direction']=='unavailable' and r['quarter_months_available']==0
        assert r['loading'] is not None

def test_lag_dates_and_underlying_transformed_values():
    p=payload(FILES[4]);raw=pd.read_parquet(ROOT/'data/processed/m2.parquet').set_index('reference_period')
    for lag in [0,1,2]:
        r=next(x for x in p['drivers']['M'+str(lag)] if x['indicator']=='m2')
        assert pd.Period(r['source_period'],'M')+lag==pd.Period(r['factor_cell_period'],'M')
        assert r['latest_period']==r['source_period'] and r['latest_factor_cell_period']==r['factor_cell_period']
        assert r['latest_value']==pytest.approx(raw.loc[r['source_period'],'clean_value'])
    m1=next(x for x in p['drivers']['M1'] if x['indicator']=='m2')
    assert m1['source_period']=='2026-08' and m1['factor_cell_period']=='2026-09'

def test_own_training_statistics():
    ix=pd.date_range('2025-01-31',periods=21,freq='ME')
    frame=pd.DataFrame({'m2':np.arange(21.)+10},index=ix)
    f,mu,sd=driver_frame(dict(frame=frame,loadings=np.array([.5])),1,'2026Q3',{'m2':'money'})
    assert mu.m2==pytest.approx(frame.iloc[:18].m2.mean())
    assert f.quarter_mean_z.iloc[0]==pytest.approx(((frame.iloc[18:].m2-mu.m2)/sd.m2).mean())
    frame.iloc[18:]=1e9
    _,other_mean,other_sd=driver_frame(dict(frame=frame,loadings=np.array([.5])),1,'2026Q3',{'m2':'money'})
    pd.testing.assert_series_equal(mu,other_mean);pd.testing.assert_series_equal(sd,other_sd)

def test_release_gating_precedes_lagging(monkeypatch):
    # Invoke the actual Phase 6F lagged fit with a fake estimator/bridge,
    # capturing the design supplied to estimation. July is unreleased at H1;
    # its huge value must not enter the August lagged factor cell.
    from types import SimpleNamespace
    kernel=sw.common.kernel();ix=pd.date_range('2019-01-31','2026-07-31',freq='ME')
    fields=('m2',);panel=pd.DataFrame({'m2':np.arange(len(ix),dtype=float)+1},index=ix)
    panel.iloc[-1]=1e9
    import scripts.phase6f.experiment as experiment
    monkeypatch.setattr(experiment,'FIELDS',fields)
    captured={}
    def estimate(train,z,spec,cache):
        captured['z']=z;return pd.DataFrame({'factor':0.},index=z.index),np.array([[.5]]),{}
    monkeypatch.setattr(kernel,'estimate',estimate)
    monkeypatch.setattr(kernel,'bridge',lambda *args:(8.,{}))
    monkeypatch.setattr(experiment.sw.common,'kernel',lambda:kernel)
    _,fit=lagged_dfm(panel,SimpleNamespace(release_lag_days={'m2':25}),None,'2026Q3','H1',pd.Timestamp('2026-07-31'),1)
    assert pd.isna(captured['z'].loc['2026-08-31','m2'])
    assert fit['frame'].loc['2026-07-31','m2']==panel.loc['2026-06-30','m2']

def test_shared_scale_bar_geometry():
    html=FILES[4].read_text(encoding='utf-8');p=payload(FILES[4]);scale=p['shared_scale']
    blocks=re.findall(r'<div class="bars" data-model="(M\d)" data-scale="([^"]+)">',html)
    assert len(blocks)==3 and all(float(s)==scale for _,s in blocks)
    for model,rows in p['drivers'].items():
        block=html.split(f'data-model="{model}"')[1].split('</section>')[0]
        widths=[float(x) for x in re.findall(r'width:([0-9.e+-]+)%',block)]
        np.testing.assert_allclose(widths,[0 if r['signal'] is None else 48*abs(r['signal'])/scale for r in rows])

def test_payload_comparison_csv_consistency():
    p=payload(FILES[4]);f=pd.read_csv(FILES[1]).set_index('indicator')
    for model,rows in p['drivers'].items():
        for r in rows:
            value=f.loc[r['indicator'],model+'_signal']
            assert r['signal'] is None if pd.isna(value) else r['signal']==pytest.approx(value,abs=1e-12)

def test_unchanged_umidas_and_tooltip():
    p=payload(FILES[3]);prior=pd.read_csv(ROOT/'results/phase6e/phase6e_current_drivers.csv')
    fx=prior.loc[prior.source_model.eq('U_MIDAS')].set_index('indicator')
    for r in p['UMIDAS']:assert r['signal']==pytest.approx(fx.loc[r['indicator'],'contribution_or_signal'],abs=1e-12)
    html=FILES[3].read_text(encoding='utf-8')
    for text in ['What is driving the M2-L1 nowcast?','Underlying M2 source period: 2026-08','Factor-cell period: 2026-09',
        'M2 YoY transformed value:','DFM loading:','Current factor signal:','U-MIDAS is unchanged across M0, M1 and M2.','not GDP contributions']:
        assert text in html

def test_factual_summary_horizon_gains():
    lines=summary(models().reset_index())
    assert 'largest horizon gain is H2' in lines[0]
    assert 'largest horizon gain is H3' in lines[1]
    assert 'M2 lowers pooled RMSE versus M1' in lines[2]

def test_determinism_and_protected_artifacts():
    v=json.loads((OUT/'phase6g1_m1_driver_validation.json').read_text())
    assert v['deterministic_two_complete_reruns'] and v['production_unchanged']
    assert all(sha(ROOT/name)==digest for name,digest in v['output_hashes'].items())
    assert all(g['mask_before_economic_lag'] and g['source_release_gate_passed'] for g in v['gates'])
    protected=json.loads((OUT/'phase6g1_protected_before.json').read_text())
    assert all(sha(ROOT/name)==digest for name,digest in protected.items())
