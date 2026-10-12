"""Offline satellite transformations, availability and matching checks."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from scripts.phase7b.data import parse,transform,available,match
ROOT=Path(__file__).resolve().parents[2]

def fixture():
    dates=pd.date_range('2020-01-31',periods=25,freq='ME')
    return pd.DataFrame({'radiance':np.arange(1.,26.),'NDVI':np.arange(25.)/100,'EVI':np.arange(25.)/200,'NO2':np.arange(1.,26.)},index=dates)

def test_input_contract():
    f=parse(ROOT/'data/research/satellite/input/uzbekistan_nightlights_monthly.csv')
    assert len(f)==152 and f.count().tolist()==[152,152,152,99]
    assert f.NO2.first_valid_index()==pd.Timestamp('2018-06-30')

def test_calendar_alignment_and_positive_logs():
    f=fixture().drop(pd.Timestamp('2020-02-29'));r=transform(f)
    assert pd.isna(r.loc['2021-02-28','NTL_YOY'])
    assert r.loc['2021-01-31','NTL_YOY']==pytest.approx(100*np.log(13))
    assert r.loc['2021-01-31','NDVI_YOY_DIFF']==pytest.approx(.12)
    f.loc['2020-01-31','radiance']=0
    assert pd.isna(transform(f).loc['2021-01-31','NTL_YOY'])

def test_missing_values_retained():
    f=fixture();f.loc['2020-01-31','NO2']=np.nan
    assert pd.isna(transform(f).loc['2021-01-31','NO2_YOY'])

@pytest.mark.parametrize('lag,last',[(0,'2021-01-31'),(1,'2020-12-31'),(2,'2020-11-30'),(3,'2020-10-31')])
def test_lag_sensitivity(lag,last):
    f=available(fixture(),pd.Timestamp('2021-01-31'),lag)
    assert f.radiance.last_valid_index()==pd.Timestamp(last)
    assert f.loc[f.index>pd.Timestamp(last)].isna().all().all()

def test_no_future_transform_or_parameters():
    f=fixture();old=transform(f);f.loc['2022-01-31']=100000
    pd.testing.assert_frame_equal(old.loc[:'2021-12-31'],transform(f).loc[:'2021-12-31'])
    pd.testing.assert_frame_equal(transform(fixture()),transform(fixture()))

def test_duplicate_month_rejected():
    f=fixture()
    with pytest.raises(ValueError,match='Duplicate'):transform(pd.concat([f,f.iloc[:1]]))

def test_common_samples_and_actuals():
    rows=[dict(origin='2021-01-31',target_quarter='2021Q1',horizon='H1',scenario='X',model=m,prediction=v,actual=5) for m,v in [('M0',5),('S1',np.nan)]]
    f=pd.DataFrame(rows);assert match(f,['M0','S1']).empty
    f.loc[1,'prediction']=6;assert len(match(f,['M0','S1']))==1
    f.loc[1,'actual']=6
    with pytest.raises(ValueError,match='actuals'):match(f,['M0','S1'])

def test_training_only_scaling():
    from uznowcast.models.dfm import standardize
    f=fixture();end=f.index[17];a,m,s=standardize(f,end)
    f.loc[f.index>end]=1e10;b,mm,ss=standardize(f,end)
    pd.testing.assert_series_equal(m,mm);pd.testing.assert_series_equal(s,ss)
    pd.testing.assert_frame_equal(a.loc[:end],b.loc[:end])


def test_csv_rejects_bad_schema_numeric_and_duplicates(tmp_path):
    path=tmp_path/'bad.csv'
    path.write_text('date;radiance;NDVI;EVI;NO2\n2020-01;bad;.2;.1;1\n')
    with pytest.raises(ValueError):parse(path)
    path.write_text('date;radiance;NDVI;EVI;NO2\n2020-01;1;.2;.1;1\n2020-01;2;.2;.1;1\n')
    with pytest.raises(ValueError,match='Duplicate'):parse(path)
    path.write_text('date,value\n2020-01,1\n')
    with pytest.raises(ValueError,match='columns'):parse(path)


def test_seasonal_anomaly_excludes_current_and_future():
    dates=pd.date_range('2014-01-31',periods=60,freq='ME')
    f=pd.DataFrame({c:np.arange(1.,61.) for c in ['radiance','NDVI','EVI','NO2']},index=dates)
    a=transform(f)
    assert a.loc['2017-01-31','NDVI_SEASONAL_ANOMALY']==pytest.approx(37-(1+13+25)/3)
    f.loc['2018-01-31']=1e9
    pd.testing.assert_frame_equal(a.loc[:'2017-12-31'],transform(f).loc[:'2017-12-31'])


def test_generated_outputs_and_offline_dashboard():
    import json,re
    out=ROOT/'results/phase7b'
    manifest=json.loads((out/'run_manifest.json').read_text())
    assert manifest['protected_artifacts_verified']
    assert manifest['production_nowcast']==8.180901340616275
    f=pd.read_csv(out/'phase7b_current_nowcasts.csv',float_precision='round_trip')
    assert f.loc[f.model.eq('C0'),'prediction'].eq(8.180901340616275).all()
    text=(out/'phase7b_satellite_comparison.html').read_text(encoding='utf8')
    assert '<script src=' not in text and 'fetch(' not in text and '__DATA__' not in text
    payload=json.loads(re.search(r'const D=(.*?);\nconst esc',text,re.S).group(1))
    assert len(payload['raw'])==152
    assert payload['raw'][-1]['date']=='2026-08'
    assert 'VINTAGE UNVERIFIED' in text and 'RESEARCH ONLY' in text
    h=pd.read_csv(out/'phase7b_historical_predictions.csv')
    assert not h.duplicated(['origin','target_quarter','horizon','scenario','model']).any()
    assert not h.target_quarter.eq('2026Q3').any()
    control=pd.read_csv(out/'historical_baseline_reproduction.csv')
    assert len(control)==90 and control.error.abs().max()<1e-7


def test_ar1_matching_normalizes_equivalent_origin_dates():
    from scripts.phase7b.run import metrics
    g=pd.DataFrame([dict(origin='2021-01-31 00:00:00',target_quarter='2021Q1',horizon='H1',actual=5.,prediction=4.)])
    ar=pd.DataFrame([dict(origin='2021-01-31',target_quarter='2021Q1',horizon='H1',prediction=3.)])
    assert metrics(g,ar)['oos_r_squared_ar1']==pytest.approx(.75)
