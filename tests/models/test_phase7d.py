"""Scientific boundaries of the isolated all-variable research pipeline."""
import hashlib
import json
import re
from pathlib import Path
from dataclasses import replace
import numpy as np
import pandas as pd
import pytest

from scripts.phase7d.data import decumulate, price_index, gdp_growth, read_workbook, release_gate
from scripts.phase7d.models import standardize, missing_pca, dynamics, filter_states, quarterly_covariates, SPECS, estimate
from scripts.phase7d.evaluation import matched, metrics, prequential_intervals

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/phase7d'


@pytest.fixture(scope='module')
def workbook():
    path=ROOT/'data/uzbekistan_macro_monthly_quarterly.xlsx'
    if not path.exists():pytest.skip('Uploaded research workbook absent')
    return read_workbook(path,ROOT/'data/master/gdp_quarterly.parquet')


def test_all_96_predictors_accounted(workbook):
    assert workbook.monthly.shape[1]==91
    assert workbook.quarterly.shape[1]==5
    assert len(workbook.inventory)==96
    assert workbook.inventory.original_label.is_unique
    assert set(workbook.inventory.model_input)==set(workbook.monthly)|set(workbook.quarterly)
    assert workbook.gdp.name not in workbook.monthly
    assert workbook.gdp.name not in workbook.quarterly
    assert set(workbook.transformations.original_label)==set(workbook.inventory.original_label)
    assert workbook.audit['gdp_master_concordance']==dict(n_common=30,max_absolute_difference=0.,validated=True)


def test_gdp_index_conversion():
    assert gdp_growth(pd.Series([108.5,100.,99.5])).tolist()==[8.5,0.,-.5]
    with pytest.raises(ValueError):gdp_growth(pd.Series([8.5]))


def test_monthly_decumulation_year_boundary_and_gap():
    dates=pd.period_range('2020-12','2021-04',freq='M')
    result=decumulate(pd.Series([120,10,25,np.nan,50],index=dates),'M')
    assert np.isnan(result.iloc[0])
    assert result.iloc[1:3].tolist()==[10,15]
    assert result.iloc[3:].isna().all()
    sparse=pd.Series([10,50],index=pd.PeriodIndex(['2021-01','2021-03'],freq='M'))
    assert np.isnan(decumulate(sparse,'M').iloc[1])
    with pytest.raises(ValueError):decumulate(pd.Series([1,2],index=pd.PeriodIndex(['2021-01','2021-01'],freq='M')),'M')


def test_quarterly_flow_without_decumulating_averages(workbook):
    dates=pd.period_range('2020Q4','2021Q3',freq='Q')
    assert decumulate(pd.Series([400,100,230,330],index=dates),'Q').iloc[1:].tolist()==[100,130,100]
    wages=workbook.inventory.loc[workbook.inventory.original_label.str.startswith('Average Nominal Wages')].iloc[0]
    assert wages.transformation=='LOG_YOY'
    investment=workbook.inventory.loc[workbook.inventory.original_label.str.startswith('Investments in fixed')].iloc[0]
    assert investment.transformation=='INDEX_MINUS_100'


def test_cpi_ppi_index_basis():
    index=pd.period_range('2021-01',periods=4,freq='M')
    raw=pd.Series([101,102,0,np.nan],index=index)
    result=price_index(raw,'MOM')
    assert result.iloc[0]==pytest.approx(100*np.log(1.01))
    assert result.iloc[1]==pytest.approx(100*np.log(1.02))
    assert result.iloc[2:].isna().all()
    cumulative=pd.Series([101,103],index=index[:2])
    assert price_index(cumulative,'YTD').iloc[1]==pytest.approx(100*np.log(103/101))
    with pytest.raises(ValueError):price_index(raw,'GUESS')


def test_zero_ppi_preserved_in_raw(workbook):
    label=next(c for c in workbook.monthly if c.startswith('PPI') and 'Mining of metal ores' in c)
    mask=workbook.monthly_raw[label].eq(0)
    assert mask.any()
    assert workbook.monthly.loc[mask,label].isna().all()
    assert workbook.monthly_raw.loc[mask,label].eq(0).all()


def test_training_only_normalization_and_winsorization():
    dates=pd.date_range('2020-01-31',periods=12,freq='ME')
    f=pd.DataFrame({'a':np.arange(12,dtype=float),'b':np.arange(12,dtype=float)*2},index=dates)
    z,mean,scale,e=standardize(f,dates[7],winsor=True)
    altered=f.copy();altered.iloc[8:]=1e9
    az,am,ass,ae=standardize(altered,dates[7],winsor=True)
    pd.testing.assert_series_equal(mean,am);pd.testing.assert_series_equal(scale,ass)
    pd.testing.assert_frame_equal(z.iloc[:8],az.iloc[:8])
    assert mean.a==pytest.approx(3.5)


@pytest.mark.parametrize('k',[1,2,3])
def test_ragged_panel_and_factor_dimensions(k):
    rng=np.random.default_rng(123);x=rng.normal(size=(48,8));x[:20,6:]=np.nan;x[-3:,1:4]=np.nan
    original=x.copy()
    f,l,r,diag=missing_pca(x,k,np.ones(8))
    assert f.shape==(48,k) and l.shape==(8,k)
    assert diag['objective_monotone']
    np.testing.assert_equal(original,x)
    fit,_=dynamics(f,l,r)
    states=filter_states(x,fit)
    assert states.shape==(48,k) and np.isfinite(states).all()
    later=x.copy();later[-2:]=1000
    np.testing.assert_allclose(filter_states(later,fit)[:-2],states[:-2])
    assert max(abs(np.linalg.eigvals(fit.transition)))<.98


def test_quarterly_unavailable_never_leaks():
    q=pd.period_range('2020Q1',periods=8,freq='Q')
    f=pd.DataFrame({'credits':np.arange(8,dtype=float)+1},index=q)
    inv=pd.DataFrame({'original_label':['credits'],'publication_lag_days':[90]})
    target=pd.Period('2021Q4','Q');origin='2021-10-31'
    value,audit=quarterly_covariates(f,inv,target,'H1',origin)
    revised=f.copy();revised.loc['2021Q3':]=1e8
    v2,a2=quarterly_covariates(revised,inv,target,'H1',origin)
    pd.testing.assert_series_equal(value,v2)
    assert audit[0]['latest_available_period']=='2021Q2'
    assert audit[0]['requested_period']=='2021Q3'
    assert audit[0]['status']=='TRAINING_ONLY_AR1_PROJECTION_Q_MINUS_1'
    assert pd.isna(release_gate(f,inv,origin).loc['2021Q3','credits'])


def test_quarterly_cache_isolation():
    dates=pd.period_range('2020Q1',periods=8,freq='Q')
    frame=pd.DataFrame({'credits':np.arange(8,dtype=float)+1},index=dates)
    inv=pd.DataFrame({'original_label':['credits'],'publication_lag_days':[90]})
    target=pd.Period('2021Q4','Q')
    values,audit=quarterly_covariates(frame,inv,target,'H1','2021-10-31')
    expected=values.copy();values['credits']=1e9;audit[0]['status']='MUTATED'
    again,other=quarterly_covariates(frame,inv,target,'H1','2021-10-31')
    pd.testing.assert_series_equal(again,expected)
    assert other[0]['status']!='MUTATED'


def test_strict_matched_metrics_and_actual_definition():
    rows=[]
    for q,actual in [('2024Q1',1.),('2024Q2',2.),('2024Q3',3.)]:
        for model,p in [('A',actual+1),('AR1',actual+2)]:rows.append(dict(origin=q,target_quarter=q,horizon='H1',model=model,actual=actual,prediction=p))
    f=pd.DataFrame(rows)
    f.loc[0,'prediction']=np.nan
    common=matched(f,['A','AR1'])
    assert len(common)==4
    a=common.loc[common.model.eq('A')]
    scores=metrics(a,common)
    assert scores['rmse']==1 and scores['bias']==-1
    assert scores['r2_os_ar1']==pytest.approx(.75)
    bad=f.copy();bad.loc[1,'actual']=99
    with pytest.raises(ValueError):matched(bad,['A','AR1'])
    duplicated=pd.concat([f,f.iloc[[0]]])
    with pytest.raises(ValueError):matched(duplicated,['A','AR1'])


def test_zero_denominator_r_squared_is_null():
    f=pd.DataFrame([dict(model='AR1',origin=str(i),target_quarter='2024Q1',horizon=str(i),actual=1.,prediction=1.) for i in range(3)])
    m=metrics(f,f)
    assert np.isnan(m['r2']) and np.isnan(m['r2_os_ar1'])


def test_intervals_do_not_use_future_errors():
    quarters=pd.period_range('2021Q1',periods=12,freq='Q').astype(str)
    f=pd.DataFrame([dict(model='A',origin=q,target_quarter=q,horizon='H1',actual=float(i),prediction=float(i)-1) for i,q in enumerate(quarters)])
    a=prequential_intervals(f);f.loc[10:,'actual']+=1000;b=prequential_intervals(f)
    pd.testing.assert_series_equal(a.interval_lower.iloc[:11],b.interval_lower.iloc[:11])
    assert a.interval_lower.iloc[:8].isna().all()


def test_current_all_variable_representation_and_future_independence(workbook):
    from scripts.phase7d.run import information_gdp
    _,gdp=information_gdp(pd.read_csv(ROOT/'data/current/gdp_vintages.csv'),'2026Q3','2026-10-05')
    result=estimate(workbook,'DFM_ALL_GROUPED','2026Q3','H3','2026-10-05',gdp)
    prediction,factors,loads,z,av,diag=result
    assert diag['n_declared']==96 and diag['n_effective_predictors']==96
    assert factors.shape[1]==2
    assert set(av.original_label)==set(workbook.inventory.original_label)
    monthly=loads.loc[loads.factor.eq('factor_1')]
    for _,group in monthly.groupby('group'):
        assert (group.group_weight**2).sum()==pytest.approx(1.)
    # Adding impossible future input values does not alter the forecast origin.
    extra=workbook.monthly.copy();extra.loc[pd.Period('2027-01','M')]=1e9
    r2=estimate(replace(workbook,monthly=extra),'DFM_ALL_GROUPED','2026Q3','H3','2026-10-05',gdp)
    assert prediction==pytest.approx(r2[0],abs=1e-12)


@pytest.fixture
def generated():
    path=OUT/'phase7d_dfm_dashboard.html'
    if not path.exists():pytest.skip('Run Phase 7D before generated artifact consistency checks')
    text=path.read_text(encoding='utf8')
    match=re.search(r'<script id="phase7d-data" type="application/json">(.*?)</script>',text,re.S)
    assert match
    return json.loads(match.group(1)),text


def test_dashboard_data_consistency(generated):
    d,text=generated
    assert len(d['inventory'])==96
    assert len(d['models'])==9
    assert set(d['models'])==set(['M0','U0','COMBO_50_50','AR1','AR2',*SPECS])
    metrics_csv=pd.read_csv(OUT/'phase7d_model_metrics.csv',float_precision='round_trip')
    assert len(d['metrics'])==len(metrics_csv)
    for a,b in zip(d['metrics'],metrics_csv.to_dict('records')):
        assert a['model']==b['model'] and a['sample']==b['sample']
        assert a['rmse']==pytest.approx(b['rmse'],abs=1e-12)
        assert a['n_forecasts']==b['n_forecasts']
    current=json.loads((OUT/'phase7d_current_nowcast.json').read_text())
    assert d['nowcast']==current
    assert d['manifest']['protected_artifacts_verified'] is True
    assert '<script src=' not in text and 'cdn.' not in text


def test_production_forecast_preservation(generated):
    production=json.loads((ROOT/'results/current/current_nowcast.json').read_text())
    assert production['production_model']=='COMBO_50_50'
    assert production['final_forecast']==8.180901340616275
    manifest=json.loads((OUT/'phase7d_run_manifest.json').read_text())
    assert manifest['protected_artifacts_verified'] is True
    hashes=json.loads((OUT/'phase7d_protection_baseline.json').read_text())
    protected=['results/current/current_nowcast.json','data/master/v1_monthly.parquet',
               'data/master/gdp_quarterly.parquet','config/model_definitions.json']
    for name in protected:
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==hashes[name]


def test_generated_factor_selection_uses_development(generated):
    d,_=generated
    dev=[r for r in d['metrics'] if r['sample']=='MATCHED_DEVELOPMENT' and r['model'] in SPECS]
    best=min(dev,key=lambda r:(r['rmse'],r['model']))
    assert d['nowcast']['model']==best['model']
    assert d['nowcast']['factor_count']==SPECS[best['model']][0]
