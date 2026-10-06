"""Offline nominal GDP arithmetic, vintage boundaries and output contracts."""
import json
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from scripts.phase6g3.nominal import transform, parse
from scripts.phase6g3.vintages import available, targets_as_of
from scripts.phase6g3.protection import OUT,verify


def test_decumulation_growth_reset_and_annual_sum():
    q=pd.period_range('2020Q1',periods=8,freq='Q')
    f=transform(pd.Series([100,300,600,1000,110,330,660,1100],index=q))
    np.testing.assert_allclose(f.standalone_nominal_gdp,[100,200,300,400,110,220,330,440])
    assert f.nominal_gdp_yoy_log.iloc[:4].isna().all()
    np.testing.assert_allclose(f.nominal_gdp_yoy_log.iloc[4:],100*np.log(1.1))
    np.testing.assert_allclose(f.nominal_gdp_yoy_pct.iloc[4:],10.)
    assert f.standalone_nominal_gdp.iloc[4]==110
    assert f.standalone_nominal_gdp.iloc[:4].sum()==1000


def test_missing_quarter_nonpositive_and_no_future_use():
    q=pd.period_range('2020Q1',periods=8,freq='Q')
    s=pd.Series([100,300,600,1000,110,330,660,1100],index=q)
    f=transform(s.drop(q[1]))
    assert pd.isna(f.loc['2020Q2','standalone_nominal_gdp'])
    assert pd.isna(f.loc['2020Q3','standalone_nominal_gdp'])
    before=transform(s);s.iloc[-1]=100000
    pd.testing.assert_frame_equal(before.iloc[:-1],transform(s).iloc[:-1])
    s.iloc[5]=100
    f=transform(s)
    assert 'NONPOSITIVE' in f.loc['2021Q2','quality_flag']
    assert pd.isna(f.loc['2021Q2','nominal_gdp_yoy_log'])
    with pytest.raises(ValueError):transform(pd.concat([s,s]))


def test_strict_publication_and_revision_selection():
    f=pd.DataFrame([dict(quarter='2020Q1',publication_date='2020-04-30',value=100),
                    dict(quarter='2020Q1',publication_date='2020-06-01',value=200),
                    dict(quarter='2020Q2',publication_date='2020-07-30',value=350)])
    assert available(f,'2020-04-30','2020Q2').empty
    assert available(f,'2020-05-01','2020Q2').loc['2020Q1','value']==100
    assert available(f,'2020-06-01','2020Q2').loc['2020Q1','value']==100
    assert available(f,'2020-08-01','2020Q2').index.tolist()==['2020Q1']


def test_growth_release_requires_every_parent_and_revises():
    rows=[]
    for quarter,value in [('2019Q1',100),('2019Q2',300),('2020Q1',110),('2020Q2',330)]:
        rows.append(dict(quarter=quarter,value=value,publication_date='2020-07-30',checksum=quarter,source_url='https://stat.uz/test',precision_billion_UZS=.1))
    events=pd.DataFrame(rows)
    assert targets_as_of(events,'2020-07-30','2020Q3').empty
    result=targets_as_of(events,'2020-07-31','2020Q3')
    assert result.loc['2020Q2','value']==pytest.approx(100*np.log(1.1))
    events=pd.concat([events,pd.DataFrame([dict(rows[2],value=120,publication_date='2020-08-01')])],ignore_index=True)
    assert targets_as_of(events,'2020-08-01','2020Q3').loc['2020Q2','value']==result.loc['2020Q2','value']
    assert targets_as_of(events,'2020-08-02','2020Q3').loc['2020Q2','value']==pytest.approx(100*np.log(210/200))
    assert targets_as_of(events.loc[events.quarter.ne('2019Q1')],'2020-08-02','2020Q3').empty


def test_exact_national_selector_and_unit_contract():
    payload=[dict(metadata=[dict(name_en='Indicator identification number (code)',value_en='1.01.01.0056'),
                            dict(name_en='Periodicity',value_en='quarterly'),dict(name_en='Unit of measurement',value_en='national currency, billion soums')],
        data=[dict(Code='1700',Klassifikator='UZ',Klassifikator_ru='UZ',Klassifikator_uzc='UZ',Klassifikator_en='Republic of Uzbekistan',**{'2020-Q1':100.,'2020-Q2':300.}),
              dict(Code='1703',Klassifikator_en='Regional row',**{'2020-Q1':999.})])]
    result=parse(payload,'1.01.01.0056','quarterly')
    assert result.cumulative_nominal_gdp.tolist()==[100.,300.]
    payload[0]['metadata'][2]['value_en']='million USD'
    with pytest.raises(ValueError):parse(payload,'1.01.01.0056','quarterly')


def test_normalization_and_unfair_cross_target_rmse():
    from scripts.phase6g3.experiment import scores
    rows=[]
    for model,scale in [('REAL',1),('NOMINAL',10)]:
        for q,actual,pred in [('2020Q1',1,2),('2020Q2',3,4)]:
            for h in ['H1','H2','H3']:
                rows.append(dict(model=model,target_quarter=q,horizon=h,actual=actual*scale,prediction=pred*scale,prior_growth=0))
    scored=scores(pd.DataFrame(rows)).loc[lambda x:x.horizon.eq('POOLED')].set_index('model')
    assert scored.loc['NOMINAL','RMSE']==10*scored.loc['REAL','RMSE']
    assert scored.loc['NOMINAL','normalized_RMSE']==scored.loc['REAL','normalized_RMSE']


def test_saved_outputs_boundaries_and_identical_bridge_sample():
    audit=pd.read_csv(OUT/'gdp_target_audit.csv')
    assert len(audit)==34 and audit.internally_consistent.all()
    assert audit.cumulative_or_standalone.eq('CUMULATIVE_YEAR_TO_DATE').all()
    annual=pd.read_csv(OUT/'annual_validation.csv');assert annual.loc[annual.complete_year,'passed'].all()
    f=pd.read_csv(OUT/'common_sample_forecasts.csv')
    assert f.groupby(['target_quarter','horizon']).model.nunique().eq(3).all()
    controlled=f.loc[f.model.ne('ACCEPTED_REAL_DFM')]
    assert controlled.groupby(['target_quarter','horizon']).training_quarters.nunique().eq(1).all()
    usage=pd.read_csv(OUT/'target_training_vintage_usage.csv')
    assert (usage.quarter<usage.target_quarter).all()
    for r in usage.itertuples():
        assert all(pd.Timestamp(x).date()<pd.Timestamp(r.forecast_origin).date() for x in json.loads(r.parent_publication_dates).values())
    assert pd.read_csv(OUT/'reproduction.csv').passed.all()
    assert pd.read_csv(OUT/'factor_loadings.csv').loading_identical_for_both_targets.all()
    assert json.loads((OUT/'run_manifest.json').read_text())['production_unchanged']
    verify()
