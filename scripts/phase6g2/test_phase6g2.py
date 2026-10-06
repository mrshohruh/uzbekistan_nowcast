"""Offline transformation, information boundary and output-contract checks."""
import json
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from scripts.phase6g2.run import OUT, verify
from scripts.phase6g2.core import log_change, design, MODELS
from scripts.phase6g2.core import metrics
from scripts.phase6e.models import FIELDS


def test_three_calendar_months_not_monthly_or_annualized():
    ix=pd.date_range('2020-01-31',periods=18,freq='ME')
    s=pd.Series(np.exp(np.arange(18)*.01),index=ix)
    q=log_change(s,3)
    assert q.iloc[:3].isna().all()
    np.testing.assert_allclose(q.iloc[3:],3,atol=1e-12)
    np.testing.assert_allclose(log_change(s,12).iloc[12:],12,atol=1e-12)


def test_gaps_nonpositive_and_no_future_dependence():
    ix=pd.date_range('2020-01-31',periods=18,freq='ME')
    s=pd.Series(np.arange(18)+100.,index=ix)
    before=log_change(s,3);s.iloc[-1]=99999
    pd.testing.assert_series_equal(before.iloc[:-1],log_change(s,3).iloc[:-1])
    s.iloc[5]=0;s.iloc[6]=-1
    q=log_change(s.drop(ix[4]),3)
    assert q.loc[ix[[4,5,6,7,8,9]]].isna().all()
    with pytest.raises(ValueError):log_change(pd.concat([s,s]),3)


def test_release_mask_precedes_economic_lag_and_scaling():
    ix=pd.date_range('2019-01-31','2024-06-30',freq='ME')
    p=pd.DataFrame({k:np.arange(len(ix))+1. for k in FIELDS},index=ix)
    ds=SimpleNamespace(release_lag_days={k:25 for k in FIELDS})
    frame,_,_,_=design(p,ds,'2024Q2','H2','Q1')
    assert frame.loc['2024-05-31','m2']==p.loc['2024-04-30','m2']
    assert frame.index.min()==pd.Timestamp('2019-02-28')
    p.loc['2024-05-31','m2']=1e10
    changed,_,_,_=design(p,ds,'2024Q2','H2','Q1')
    pd.testing.assert_frame_equal(frame,changed)


def test_common_sample_and_persisted_contract():
    f=pd.read_csv(OUT/'phase6g2_origin_forecasts.csv')
    common=f.loc[f['sample'].eq('COMMON')]
    wide=f.pivot(index=['target_quarter','horizon'],columns=['sample','model'],values='prediction')
    eligible=wide.dropna().index
    assert len(eligible)>0
    counts=common.set_index(['target_quarter','horizon']).loc[eligible].reset_index().groupby(['target_quarter','horizon']).model.nunique()
    assert counts.eq(6).all()
    metrics=pd.read_csv(OUT/'phase6g2_horizon_metrics.csv')
    assert metrics.loc[metrics.horizon.eq('POOLED'),'N'].eq(len(eligible)).all()
    assert set(common.model)==set(MODELS)
    s=pd.read_csv(OUT/'phase6g2_sample_comparison.csv')
    s=s.loc[s['sample'].eq('COMMON')]
    assert s.groupby(['target_quarter','horizon']).complete_panel_start.nunique().eq(1).all()
    assert s.groupby(['target_quarter','horizon']).n_DFM_training_observations.nunique().eq(1).all()
    audit=pd.read_csv(OUT/'phase6g2_fdi_transformation_audit.csv').iloc[0]
    assert not audit.monthly_DFM and not audit.ln_used and not audit.standardized
    assert pd.read_csv(OUT/'phase6g2_reproduction.csv').passed.all()
    assert json.loads((OUT/'phase6g2_run_manifest.json').read_text())['production_unchanged']
    verify()


def test_failed_origin_excluded_from_both_regimes_and_every_model():
    rows=[]
    for sample in ['NATURAL','COMMON']:
        for model in MODELS:
            for quarter in ['2024Q1','2024Q2']:
                for horizon in ['H1','H2','H3']:
                    if sample=='NATURAL' and model=='Q2' and quarter=='2024Q1' and horizon=='H1':continue
                    rows.append(dict(sample=sample,model=model,target_quarter=quarter,horizon=horizon,actual=8.,prediction=7.))
    result=metrics(pd.DataFrame(rows))
    assert result.loc[result.horizon.eq('POOLED'),'N'].eq(5).all()
    assert result.loc[result.horizon.eq('H1'),'N'].eq(1).all()


def test_fdi_negative_invalidates_ordinary_log_and_current_snapshot():
    audit=pd.read_csv(OUT/'phase6g2_fdi_transformation_audit.csv').iloc[0]
    assert audit.negative_count==1 and not audit.ln_valid
    assert np.isfinite(np.arcsinh(np.array([-100.,0.,100.]))).all()
    now=pd.read_csv(OUT/'phase6g2_current_nowcasts.csv')
    fdi=now.loc[now.model.str.contains('FDI_ASINH')]
    assert not fdi.empty and fdi.nowcast.isna().all()
    assert fdi.status.eq('UNAVAILABLE_SNAPSHOT_POSTDATES_FROZEN_CUTOFF').all()
