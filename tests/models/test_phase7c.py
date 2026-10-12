"""Offline economic candidate calendar, availability and production protection checks."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from scripts.phase7c.data import flows,growth,gate

ROOT=Path(__file__).resolve().parents[2]

def test_january_reset_and_reconciliation():
    f=pd.DataFrame({'reference_date':pd.to_datetime(['2020-12-31','2021-01-31','2021-02-28','2021-03-31']), 'raw_value':[100.,10.,25.,21.]})
    _,x=flows(f)
    assert x.iloc[1:].tolist()==[10.,15.,-4.]
    assert x.iloc[1:].sum()==21.

def test_missing_and_duplicate_month():
    f=pd.DataFrame({'reference_date':pd.to_datetime(['2021-01-31','2021-03-31']), 'raw_value':[10.,25.]})
    _,x=flows(f);assert pd.isna(x.iloc[2])
    with pytest.raises(ValueError,match='Duplicate'):flows(pd.concat([f,f.iloc[:1]]))

def test_growth_calendar_positive_and_backward_only():
    s=pd.Series(np.arange(1.,26.),index=pd.date_range('2020-01-31',periods=25,freq='ME'))
    assert growth(s).iloc[12]==pytest.approx(100*np.log(13))
    s.iloc[0]=0;assert pd.isna(growth(s).iloc[12])
    a=growth(s);s.iloc[-1]=1e20;pd.testing.assert_series_equal(a.iloc[:-1],growth(s).iloc[:-1])
    assert pd.isna(growth(s.drop(s.index[1])).loc['2021-02-28'])

def test_delay_gate():
    s=pd.Series([1.,2.],index=pd.to_datetime(['2026-08-31','2026-09-30']))
    assert gate(s,'2026-10-05',24).last_valid_index()==pd.Timestamp('2026-08-31')

def test_outputs_production_and_proxy():
    out=ROOT/'results/phase7c';m=json.loads((out/'run_manifest.json').read_text())
    assert m['protected_artifacts_verified']
    assert m['production_nowcast']==8.180901340616275
    assert not m['proxy_validated']
    assert all(abs(v['error'])<1e-12 for v in m['production_reproduction'].values())
    h=pd.read_csv(out/'phase7c_historical_predictions.csv')
    assert not h.target_quarter.eq('2026Q3').any()
    assert not h.duplicated(['origin','target_quarter','horizon','scenario','model']).any()
    assert not h.model.isin(['R4','C_R4']).any()
    text=(out/'phase7c_economic_coverage_dashboard.html').read_text(encoding='utf8')
    assert '<script src=' not in text and 'fetch(' not in text and '__DATA__' not in text
