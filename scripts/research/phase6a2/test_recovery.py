"""Offline tests of source selection, vintage safety and calendar coverage."""
import json
from pathlib import Path
import pandas as pd
import pytest
from extract import national_service_table,trade_values,report_period
from build import safe_flows,longest

@pytest.fixture
def official():
 return json.loads((Path(__file__).parent/'fixtures/official_table_extracts.json').read_text(encoding='utf-8'))

def test_national_services_row_and_growth_not_per_capita(official):
 level,growth,_,_=national_service_table(official['service_2019'])
 assert level==190356.0 and growth==112.5

def test_overlaid_services_pdf_headline_crosscheck(official):
 level,growth,_,_=national_service_table(official['service_2019_03'])
 assert level==40168.7 and growth==111.1

def test_reject_services_component_with_generic_footer():
 text='Communication services by region; Volume billion soums; Growth rates; Republic of Uzbekistan 6000.0 120.0; Main indicators of the service sector in the Republic of Uzbekistan'
 with pytest.raises(ValueError):national_service_table([text])

def test_current_year_gold_and_export_columns(official):
 rows=trade_values(official['trade_2026_08']);d={r[0]:r[1] for r in rows}
 assert d['exports_total_official_ytd']==22866.9
 assert d['gold_non_monetary_official_ytd']==2803.8
 assert d['exports_ex_gold_exact']==pytest.approx(20063.1)
 assert d['exports_ex_gold_exact']!=pytest.approx(22866.9-2863.3)

def test_import_gold_never_used_for_exports():
 rows=trade_values(['Exports amounted to 100.0 million USD','text','text','III. Import indicators Non-monetary gold (excluding gold ores and concentrates) 20.0'])
 assert not any(r[0]=='exports_ex_gold_exact' for r in rows)

def test_conflicting_direct_gold_total_is_candidate():
 rows=trade_values(['Exports amounted to 100.0 million USD','exports without gold reached 75.0 million USD; Non-monetary gold (except gold ores and concentrates) 20.0'])
 assert not any(r[0]=='exports_ex_gold_exact' for r in rows)
 assert {r[0] for r in rows}>={'exports_ex_gold_direct_mismatch_candidate','exports_ex_gold_subtraction_mismatch_candidate'}

def test_document_reference_period_not_file_year(official):
 assert str(report_period(official['trade_2026_08']))=='2026-08'

def group(periods,values,paths=None,units=None):
 return pd.DataFrame({'variable_key':'test','reference_period':periods,'raw_value':values,'raw_file_path':paths or ['same']*len(periods),'unit':units or ['million UZS']*len(periods),'source_url':'https://cbu.uz/'})

def test_january_reset_never_subtracts_december():
 flow,_,_,log=safe_flows(group(['2019-12','2020-01','2020-02'],[1000,20,35]))
 assert flow.loc[pd.Period('2020-01')]==20
 assert flow.loc[pd.Period('2020-02')]==15

@pytest.mark.parametrize('periods,values,paths,units,reason',[
 (['2020-01','2020-03'],[20,40],None,None,'MISSING_PREVIOUS_MONTH'),
 (['2020-01','2020-02'],[20,10],None,None,'NON_MONOTONIC_YTD_WITHHELD'),
 (['2020-01','2020-02'],[20,40],['old','new'],None,'VINTAGE_MISMATCH_WITHHELD'),
 (['2020-01','2020-02'],[20,40],None,['million UZS','billion UZS'],'UNIT_MISMATCH_WITHHELD')])
def test_unsafe_flow_is_missing(periods,values,paths,units,reason):
 flow,_,_,log=safe_flows(group(periods,values,paths,units))
 assert pd.isna(flow.iloc[-1]);assert log[-1]['decision']==reason

def test_duplicate_month_rejected():
 with pytest.raises(ValueError,match='Duplicate'):safe_flows(group(['2020-01','2020-01'],[20,30]))

def test_yoy_calendar_gap_and_positivity():
 periods=pd.period_range('2020-01','2021-02',freq='M');values=[10*(p.month) for p in periods]
 flow,yoy,pct,_=safe_flows(group(periods.astype(str),values))
 assert yoy.loc[pd.Period('2021-01')]==0
 assert pct.loc[pd.Period('2021-02')]==0
 bad=group(['2020-01','2021-01'],[0,5]);_,yoy,_,_=safe_flows(bad)
 assert pd.isna(yoy.loc[pd.Period('2021-01')])

def test_common_sample_longest_excludes_missing_month():
 mask=pd.Series([True,True,False,True,True,True],index=pd.period_range('2020-01',periods=6,freq='M'))
 assert longest(mask)==('2020-04','2020-06',3)
