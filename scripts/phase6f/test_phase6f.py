"""Offline availability, lag, sample and actual reconstruction evidence checks."""
import json
import numpy as np
import pandas as pd
import pytest
from scripts.phase6f.experiment import ROOT, economic_lag, latest_available, score, sha, parse_fdi

OUT=ROOT/'results/phase6f'


def test_calendar_m2_lag_does_not_jump_gap():
    s=pd.Series([10.,30.],index=pd.to_datetime(['2024-01-31','2024-03-31']))
    assert economic_lag(s,1).isna().all()
    assert economic_lag(s,2).iloc[-1]==10


def test_duplicate_m2_rejected():
    with pytest.raises(ValueError):
        economic_lag(pd.Series([1,2],index=pd.to_datetime(['2024-01-31']*2)),1)


def events():
    return pd.DataFrame(dict(period=['2024Q1','2024Q2','2024Q3'],value=[1.,2.,3.],
        availability_date=['2024-06-30','2024-09-30','2024-12-30'],retrieved_at=['2024-06-29T00:00:00Z','2024-09-29T00:00:00Z','2024-12-29T00:00:00Z']))


def test_fdi_publication_boundary_and_additional_quarter():
    assert latest_available(events(),'2024-09-29').period=='2024Q1'
    assert latest_available(events(),'2024-09-30').period=='2024Q2'
    assert latest_available(events(),'2024-09-30',1).period=='2024Q1'


def test_future_value_vintage_never_available_strict():
    e=events();e['retrieved_at']='2026-10-06T00:00:00Z'
    assert latest_available(e,'2024-12-31') is None
    assert latest_available(e,'2024-12-31',strict_vintage=False).period=='2024Q3'


def test_extra_quarter_does_not_skip_missing_period():
    assert latest_available(events().iloc[[0,2]],'2025-01-01',1) is None


def test_exact_common_sample_metric():
    f=pd.DataFrame(dict(model=['M0','M0','X'],target_quarter=['2024Q1','2024Q2','2024Q2'],horizon=['H1']*3,
        actual=[0.,10.,10.],prediction=[100.,9.,10.],evidence_class=['test']*3))
    r=score(f);x=r.loc[r.model.eq('X') & r.horizon.eq('POOLED')].iloc[0]
    assert x.N==1 and x.benchmark_common_RMSE==1 and x.RMSE==0 and x.OOS_R2==1


def test_all_benchmark_reconstructions_and_current_combo():
    f=pd.read_csv(OUT/'phase6f_benchmark_reconstruction.csv')
    assert len(f)==13 and f.error.abs().max()<1e-7
    c=pd.read_csv(OUT/'phase6f_current_nowcasts.csv').set_index('model')
    assert abs(c.loc['COMBO_50_50','nowcast']-8.180901340616275)<1e-7
    assert c.loc[['B3','B4','B5'],'nowcast'].isna().all()


def test_no_false_real_time_claims_or_timing_leaks():
    f=pd.read_csv(OUT/'phase6f_origin_availability.csv')
    assert not f.leakage_flag.any() and not f.valid_real_time_forecast.any()
    assert (pd.to_datetime(f.m2_assumed_availability_date,format='mixed')<=pd.to_datetime(f.forecast_origin,format='mixed')).all()
    g=f.dropna(subset=['fdi_assumed_availability_date'])
    assert (pd.to_datetime(g.fdi_assumed_availability_date,format='mixed')<=pd.to_datetime(g.forecast_origin,format='mixed')).all()


def test_actual_protected_artifacts_unchanged():
    before=json.loads((OUT/'phase6f_protected_before.json').read_text())
    after=json.loads((OUT/'phase6f_protected_after.json').read_text())
    assert before==after
    assert all(sha(ROOT/p)==h for p,h in before.items())


def test_fdi_exact_official_schema_and_quarterly_output():
    receipt=json.loads((OUT/'raw/receipt.json').read_text())
    f=parse_fdi(ROOT/receipt['raw_file'])
    assert f.period.min()=='2005Q1' and f.period.max()=='2026Q2'
    assert len(f)==86 and not f.period.duplicated().any()


def test_deterministic_numerical_outputs():
    evidence=OUT/'phase6f_determinism.json'
    if not evidence.exists():
        pytest.skip('Full independent rerun evidence not yet produced')
    assert json.loads(evidence.read_text())['identical_csv_hashes']
