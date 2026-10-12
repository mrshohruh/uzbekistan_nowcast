"""Offline evidence checks; no network or production writes."""
import json
import numpy as np
import pandas as pd
import pytest
from scripts.phase7a.data import transform,annual_siat
from scripts.phase7a.run import ROOT,sources,monthly

def test_monthly_definition_and_no_fabricated_history():
    f=monthly(sources())
    assert len(f)==93 and f.electricity_consumption_gwh.notna().sum()==3
    assert f.loc[f.electricity_consumption_gwh.notna(),'date'].tolist()==['2026-06-30','2026-07-31','2026-08-31']
    assert not transform(f).transformation_valid.any()
    assert f.loc[f.date.eq('2026-06-30'),'publication_date'].iloc[0]=='2026-07-09 15:45:00'
    assert f.loc[f.date.eq('2026-09-30'),'electricity_consumption_gwh'].isna().all()

def test_growth_uses_calendar_month_not_row_shift():
    f=pd.DataFrame({'date':['2020-01-31','2021-01-31','2021-03-31'],'electricity_consumption_gwh':[100,110,120]})
    r=transform(f)
    assert r.electricity_yoy_log_growth.iloc[1]==pytest.approx(100*np.log(1.1))
    assert pd.isna(r.electricity_yoy_log_growth.iloc[2])

@pytest.mark.parametrize('level',[0,-1,np.nan])
def test_logs_reject_nonpositive_and_missing(level):
    r=transform(pd.DataFrame({'date':['2020-01-31','2021-01-31'],'electricity_consumption_gwh':[level,10]}))
    assert not r.transformation_valid.any()

def test_duplicate_month_fails():
    with pytest.raises(ValueError,match='Duplicate'):transform(pd.DataFrame({'date':['2020-01-01','2020-01-31'],'electricity_consumption_gwh':[1,2]}))

def test_siat_is_annual_exact_national_row():
    r=sources()['siat_payload'];f=annual_siat((ROOT/r['raw_file']).read_bytes())
    assert len(f)==10 and f.period_type.eq('annual').all()
    assert f.loc[f.year.eq(2024),'electricity_consumption_gwh'].iloc[0]==65490.5

def test_challenger_withheld_and_production_constant():
    f=pd.read_csv(ROOT/'results/phase7a/phase7a_current_nowcasts.csv')
    assert f.loc[f.model.isin(['E1','C1']),'forecast'].isna().all()
    assert f.loc[f.model.eq('C0'),'forecast'].iloc[0]==pytest.approx(8.180901340616275,abs=1e-14)
    m=json.loads((ROOT/'results/phase7a/run_manifest.json').read_text())
    assert m['protected_artifacts_verified'] and m['matched_challenger_origins']==0

def test_dashboard_local_and_missing_data_explicit():
    text=(ROOT/'results/phase7a/phase7a_electricity_comparison.html').read_text(encoding='utf8')
    assert '<script src=' not in text and 'fetch(' not in text
    assert 'PHASE7A_INSUFFICIENT_DATA' in text and 'Not estimable' in text
    assert '__DATA__' not in text and '<svg' in text
