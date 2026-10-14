"""Executed scientific safeguards for the isolated economic-factor research."""
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import re

import numpy as np
import pandas as pd
import pytest

from scripts.phase7d.data import read_workbook, release_gate, INFORMATION_CLASS
from scripts.phase7d.run import information_gdp
from scripts.phase7d.evaluation import matched, metrics
from scripts.phase7e.grouping import inventory, core_columns, group, anchors, BLOCKS
from scripts.phase7e.models import block_factor, estimate, orient, hierarchical, available_lag, SPECS

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/phase7e'


@pytest.fixture(scope='module')
def inputs():
    return read_workbook(next((ROOT/'results/phase7d/input').glob('*.xlsx')),ROOT/'data/master/gdp_quarterly.parquet')


@pytest.fixture(scope='module')
def events():
    return pd.read_csv(ROOT/'data/current/gdp_vintages.csv')


@pytest.fixture(scope='module')
def grouping(inputs):
    return inventory(inputs,'2026-10-05')


@pytest.fixture(scope='module')
def current(inputs,grouping,events):
    _,gdp=information_gdp(events,'2026Q3','2026-10-05')
    cache={}
    return {m:estimate(inputs,grouping,m,'2026Q3','H3','2026-10-05',gdp,events,cache) for m in SPECS}


def test_all_variables_exactly_once(inputs,grouping):
    assert len(grouping)==96 and grouping.original_label.is_unique
    assert set(grouping.original_label)==set(inputs.monthly)|set(inputs.quarterly)
    assert grouping.loc[grouping.frequency.eq('M')].economic_group.value_counts().to_dict()==dict(F5=38,F1=29,F2=14,F3=5,F4=5)
    assert grouping.loc[grouping.frequency.eq('Q')].economic_group.eq('Q_BRIDGE').all()
    assert inputs.gdp.name not in grouping.original_label.tolist()


def test_unknown_or_omitted_indicator_fails(inputs):
    with pytest.raises(ValueError): group('Unknown measurement','M')
    with pytest.raises(ValueError): inventory(replace(inputs,inventory=inputs.inventory.iloc[:-1]),'2026-10-05')
    with pytest.raises(ValueError): inventory(replace(inputs,inventory=pd.concat([inputs.inventory,inputs.inventory.iloc[:1]])),'2026-10-05')


def test_core_labels_match_exact_available_series(inputs,grouping):
    selected=core_columns(inputs.monthly)
    assert sum(len(cs) for cs in selected.values())==17
    assert grouping.economic_core_selected.sum()==17
    assert all(group(c,'M')==b for b,cs in selected.items() for c in cs)
    assert set(c for cs in selected.values() for c in cs).issubset(inputs.monthly)


def test_coverage_and_transformation_audit_preserved(inputs,grouping):
    old=pd.read_csv(ROOT/'results/phase7d/phase7d_monthly_inputs.csv',index_col='reference_period',float_precision='round_trip')
    pd.testing.assert_frame_equal(inputs.monthly.set_axis(inputs.monthly.index.astype(str)),old,check_names=False)
    assert grouping.publication_lag_basis.str.contains('ASSUMED').all()
    assert grouping.source_release_date.isna().all()
    services=inputs.monthly.loc[:,[c for c in inputs.monthly if group(c,'M')=='F2']]
    assert services.loc[:'2023-12'].isna().all().all()
    assert services.first_valid_index()==pd.Period('2024-01','M')


def test_services_not_identified_in_early_history(inputs,grouping):
    with pytest.raises(ValueError,match='fewer than two'):
        block_factor(inputs,grouping,'F2','2024Q4','2024-12-31')


def test_future_predictor_values_cannot_change_forecast(inputs,grouping,events):
    origin='2025-04-30';target='2025Q2'
    _,gdp=information_gdp(events,target,origin)
    a=estimate(inputs,grouping,'E4',target,'H1',origin,gdp,events)
    monthly=inputs.monthly.copy();quarterly=inputs.quarterly.copy()
    for f in [monthly,quarterly]:
        visible=release_gate(f,inputs.inventory,origin)
        # Only alter actually populated but not yet available cells.
        f.mask(f.notna() & visible.isna(),1e9,inplace=True)
    b=estimate(replace(inputs,monthly=monthly,quarterly=quarterly),grouping,'E4',target,'H1',origin,gdp,events)
    assert a.prediction==pytest.approx(b.prediction,abs=1e-12)
    pd.testing.assert_frame_equal(a.factors,b.factors)
    pd.testing.assert_frame_equal(a.loadings,b.loadings)


def test_target_quarter_quarterly_covariates_never_enter(inputs,grouping,events,current):
    changed=inputs.quarterly.copy();changed.loc['2026Q3':]=1e12
    _,gdp=information_gdp(events,'2026Q3','2026-10-05')
    b=estimate(replace(inputs,quarterly=changed),grouping,'E4','2026Q3','H3','2026-10-05',gdp,events)
    assert b.prediction==pytest.approx(current['E4'].prediction,abs=1e-12)
    q=b.availability.loc[b.availability.frequency.eq('Q')]
    assert len(q)==5
    assert q.requested_period.eq('2026Q2').all()


def test_gdp_lag_available_without_future_vintage(events):
    q=pd.Period('2025Q2','Q');origin='2025-04-30'
    a=available_lag(events,q,'H1',origin)
    altered=events.copy()
    altered.loc[pd.to_datetime(altered.publication_date)>pd.Timestamp(origin),'value']=1e9
    assert available_lag(altered,q,'H1',origin)==a
    assert pd.Period(a[1],'Q')<q


def test_factor_orientation_and_no_service_backfill(current):
    r=current['E2']
    assert r.loadings.loc[r.loadings.anchor].loading.gt(0).all()
    assert r.factors.loc[:'2023-12-31','F2'].isna().all()
    assert r.factors.loc['2024-01-31':,'F2'].notna().all()
    f=np.array([[1.],[2.]]);l=np.array([[-.5],[.3]])
    af,al=orient(f,l,0)
    np.testing.assert_allclose(af@al.T,f@l.T)
    assert al[0,0]>0


def test_missing_constant_block_not_forced(inputs,grouping):
    altered=inputs.monthly.copy()
    cols=grouping.loc[grouping.economic_group.eq('F2'),'original_label']
    altered.loc[:,cols]=np.nan
    with pytest.raises(ValueError):block_factor(replace(inputs,monthly=altered),grouping,'F2','2026Q3','2026-10-05')
    altered.loc[:,cols]=1.
    with pytest.raises(ValueError):block_factor(replace(inputs,monthly=altered),grouping,'F2','2026Q3','2026-10-05')


def test_identification_convergence_and_stability(current):
    for result in current.values():
        d=result.diagnostics
        assert d.pca_converged.all() and d.objective_monotone.all()
        assert d.spectral_radius.lt(.98).all()
        assert d.n_estimable.ge(2).all() and d.n_coobserved_months.ge(12).all()
        assert result.bridge['n_gdp_training']>=12
        assert all(n>=4 for n in result.bridge['factor_training_quarter_counts'].values())


@pytest.mark.parametrize('model',list(SPECS))
def test_exact_forecast_decomposition(model,current):
    result=current[model]
    assert abs(result.contributions.value.sum()-result.prediction)<1e-10
    assert result.contributions.units.eq('GDP percentage points').all()
    assert 'AVAILABLE_GDP_LAG' in result.contributions.component.tolist()
    assert result.bridge['target_definition']=='CUMULATIVE_REAL_YTD_GDP_YOY_PERCENT'


def test_full_coverage_and_specification_boundaries(current):
    assert len(current['E2'].loadings)==91
    assert current['E2'].loadings.loading.notna().sum()==91
    assert set(current['E1'].loadings.economic_group)=={'F1','F2','F3','F4'}
    assert current['E4'].bridge['quarterly_declared']==5
    assert current['E2'].bridge['quarterly_declared']==0
    assert len(current['ECONOMIC_CORE'].loadings)==17


def test_hierarchical_training_orthogonality(current):
    r=current['E3']
    assert list(r.factors)==['GLOBAL','F1_RESIDUAL','F2_RESIDUAL','F3_RESIDUAL','F4_RESIDUAL']
    projection=r.bridge['hierarchical_projection']
    assert len(projection)==5
    assert max(abs(p['global_residual_training_covariance']) for p in projection)<1e-8
    assert sum(p['reference_block'] for p in projection)==1


def test_metric_arithmetic_and_matching():
    f=pd.DataFrame([dict(origin=str(i),target_quarter=f'2024Q{i}',horizon='H1',model=m,actual=float(i),prediction=float(i)+e) for i in range(1,4) for m,e in [('E2',1.),('AR1',2.)]])
    c=matched(f,['E2','AR1']);s=metrics(c.loc[c.model.eq('E2')],c)
    assert s['rmse']==1 and s['mae']==1 and s['bias']==-1 and s['median_absolute_error']==1
    assert s['r2_os_ar1']==pytest.approx(.75)
    assert s['n_quarters']==3
    f.loc[0,'prediction']=np.nan
    assert len(matched(f,['E2','AR1']))==4


def test_generated_scientific_artifacts_and_dashboard():
    names=['economic_dfm_dashboard.html','results.md','methodology.md','economic_interpretation.md','model_comparison.csv','factor_timeseries.csv','factor_loadings.csv','gdp_contributions.csv','forecasts.csv','variable_grouping.csv','origin_availability.csv','robustness.csv','validation.json']
    assert all((OUT/('phase7e_'+n)).is_file() for n in names)
    text=(OUT/'phase7e_economic_dfm_dashboard.html').read_text(encoding='utf8')
    match=re.search(r'<script id="phase7e-data" type="application/json">(.*?)</script>',text,re.S)
    d=json.loads(match.group(1))
    assert len(d['inventory'])==96 and len(d['models'])==5
    assert '<script src=' not in text and '<link ' not in text
    assert not re.search(r'\b(fetch\(|XMLHttpRequest|WebSocket\()',text)
    c=pd.read_csv(OUT/'phase7e_gdp_contributions.csv',float_precision='round_trip')
    errors=c.groupby(['model','origin','target_quarter']).apply(lambda x:abs(x.value.sum()-x.prediction.iloc[0]))
    assert errors.max()<1e-10
    f=pd.read_csv(OUT/'phase7e_forecasts.csv')
    assert not f.duplicated(['model','origin','target_quarter','horizon']).any()
    current=[r for r in d['nowcast']['models'] if r['model']=='E2'][0]['prediction']
    assert current==pytest.approx(f.loc[f.model.eq('E2') & f.evaluation_group.eq('CURRENT')].prediction.iloc[0],abs=1e-12)


def test_production_and_phase7d_bytes_preserved():
    baseline=json.loads((OUT/'phase7e_protection_baseline.json').read_text())
    for name in ['results/current/current_nowcast.json','data/master/v1_monthly.parquet','data/master/gdp_quarterly.parquet',
                 'registry/uzbekistan_nowcasting_v1_registry.xlsx','config/model_definitions.json',
                 'results/phase7d/phase7d_forecasts.csv','results/phase7d/phase7d_dfm_dashboard.html','scripts/phase7d/models.py']:
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==baseline[name]
    frozen=json.loads((ROOT/'results/current/current_nowcast.json').read_text())
    assert frozen['final_forecast']==8.180901340616275
    assert frozen['dfm_weight']==frozen['umidas_weight']==.5


def test_expanding_origin_evaluation_is_honest():
    f=pd.read_csv(OUT/'phase7e_forecasts.csv')
    early=f.loc[f.model.isin(SPECS) & f.target_quarter.lt('2025Q1')]
    assert early.prediction.isna().all() and early.failure.notna().all()
    scores=pd.read_csv(OUT/'phase7e_model_comparison.csv')
    assert scores.groupby('sample').n_forecasts.nunique().eq(1).all()
    hold=scores.loc[scores['sample'].eq('MATCHED_HOLDOUT')]
    assert hold.n_quarters.eq(4).all()
    av=pd.read_csv(OUT/'phase7e_origin_availability.csv')
    inv=av.loc[av.model.eq('INVENTORY')]
    assert inv.groupby(['origin','target_quarter','horizon']).original_label.nunique().eq(96).all()
