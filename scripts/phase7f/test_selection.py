"""Offline formula, information-boundary and generated-artifact regression tests."""
from pathlib import Path
import json
import re

import numpy as np
import pandas as pd
import pytest

from scripts.phase7f.criteria import penalties,select
from scripts.phase7f.panels import build_panels,balanced,complete_rows,longest_rectangle,MAIN,Panel
from scripts.phase7f.protection import ROOT,OUT,sha,active_baseline


def diagonal_panel(eigenvalues,repeats=1):
    n=len(eigenvalues)
    x=np.tile(np.r_[np.eye(n),-np.eye(n)],(repeats,1))*np.sqrt(n)*np.sqrt(eigenvalues)
    return pd.DataFrame(x,columns=[f'x{i}' for i in range(n)])


def test_published_penalties_numeric_dimensions():
    p=penalties(4,8)
    assert p['ICp1']==pytest.approx(3/8*np.log(8/3))
    assert p['ICp2']==pytest.approx(3/8*np.log(4))
    assert p['ICp3']==pytest.approx(np.log(4)/4)
    assert penalties(8,4)==p
    with pytest.raises(ValueError):penalties(1,8)


def test_diagonal_spectrum_and_published_er_direction():
    result=select(diagonal_panel([9.,4.,1.,.5]))
    np.testing.assert_allclose(result.spectrum.eigenvalue,[9.,4.,1.,.5])
    assert result.summary['ER']==2
    assert result.spectrum.eigenvalue_ratio.iloc[0]==pytest.approx(9/4)
    assert result.spectrum.eigenvalue_ratio.iloc[1]==pytest.approx(4.)
    assert result.spectrum.eigenvalue_ratio.iloc[2:].isna().all()


def test_residuals_use_nt_not_residual_degrees_of_freedom():
    f=diagonal_panel([9.,4.,1.,.5]);r=select(f)
    u,s,vt=np.linalg.svd(f.to_numpy(),full_matrices=False)
    for row in r.criteria.itertuples():
        reconstruction=(u[:,:row.k]*s[:row.k])@vt[:row.k]
        mse=((f.to_numpy()-reconstruction)**2).sum()/f.size
        assert row.residual_variance==pytest.approx(mse,abs=1e-12)
        for key,cost in penalties(4,8).items():
            assert getattr(row,key)==pytest.approx(np.log(mse)+row.k*cost)


def test_zero_factor_candidate_and_positive_only_er():
    r=select(diagonal_panel(np.ones(6),repeats=2))
    assert r.criteria.k.iloc[0]==0
    assert [r.summary[k] for k in ['ICp1','ICp2','ICp3']]==[0,0,0]
    assert 1<=r.summary['ER']<=r.summary['k_max']
    assert r.summary['er_cannot_select_zero']
    np.testing.assert_allclose(r.spectrum.eigenvalue_ratio.dropna(),1.)


def test_pca_scores_loading_reconstruction_and_orientation():
    f=diagonal_panel([9.,4.,1.,.5]);r=select(f)
    l=r.loadings.pivot(index='original_variable',columns='factor',values='loading').reindex(index=f.columns)
    np.testing.assert_allclose(r.scores.to_numpy().T@r.scores.to_numpy()/len(f),np.eye(r.summary['k_max']),atol=1e-12)
    reconstruction=r.scores.to_numpy()@l.to_numpy().T
    assert np.mean((f.to_numpy()-reconstruction)**2)==pytest.approx(r.criteria.residual_variance.iloc[-1])
    for factor,g in r.loadings.groupby('factor'):
        assert g.iloc[np.argmax(abs(g.loading.to_numpy()))].loading>0
    assert r.spectrum.cumulative_explained_variance.iloc[-1]==pytest.approx(1.)


@pytest.mark.parametrize('problem',['nan','inf','duplicate_column','duplicate_row','rank1','constant'])
def test_invalid_or_degenerate_panels_fail_visibly(problem):
    f=diagonal_panel([9.,4.,1.,.5])
    if problem=='nan':f.iloc[0,0]=np.nan
    if problem=='inf':f.iloc[0,0]=np.inf
    if problem=='duplicate_column':f.columns=['x','x','y','z']
    if problem=='duplicate_row':f.index=[0]*len(f)
    if problem=='rank1':f.loc[:,:]=np.outer(np.arange(len(f)),np.arange(1,5))
    if problem=='constant':f.iloc[:,0]=1.
    with pytest.raises(ValueError):select(f)


def test_caps_do_not_reach_null_eigenvalues():
    f=diagonal_panel(np.arange(1,8,dtype=float))
    r=select(f,requested_cap=999,conservative=False)
    assert r.summary['k_max']<=min(f.shape)-2
    assert r.summary['k_max']<r.summary['numerical_rank']
    assert r.criteria.residual_variance.gt(0).all()
    assert np.isfinite(r.spectrum.eigenvalue_ratio.dropna()).all()


def test_rectangle_selection_is_missingness_only():
    dates=pd.date_range('2020-01-31',periods=48,freq='ME')
    a=pd.DataFrame({'old':np.arange(48,dtype=float),'other':np.arange(48,dtype=float)*2,'late':np.r_[np.full(30,np.nan),np.arange(18)]},index=dates)
    rows,cols=longest_rectangle(a)
    assert len(rows)==48 and list(cols)==['old','other']
    b=a*1e8+999
    rr,cc=longest_rectangle(b)
    assert rows.equals(rr) and cols.equals(cc)


@pytest.fixture(scope='module')
def panels():return build_panels()


def test_exact_model_variables_cutoff_and_training(panels):
    p,c=panels
    assert c['cutoff']=='2026-10-05' and c['training_end']=='2026-06-30'
    assert len(p['PRODUCTION_DFM'].values.columns)==8
    assert list(p['PRODUCTION_DFM'].values)==['industrial_production','ppi','usd_uzs','rub_uzs','gold_price','m2','fx_reserves_ex_gold','pos_turnover']
    assert len(p['E1'].values.columns)==53
    assert all(len(p[n].values.columns)==91 for n in ['E2','E3','E4'])
    assert len(p['ECONOMIC_CORE'].values.columns)==17
    assert p['E4'].quarterly_covariates==5
    assert all(v.values.index.max()<=pd.Timestamp(c['training_end']) for v in p.values())
    assert p['PRODUCTION_DFM'].values.notna().sum().sum()==702


def test_e4_monthly_identity_and_e3_generated_structure(panels):
    p,_=panels
    pd.testing.assert_frame_equal(p['E2'].z,p['E4'].z)
    pd.testing.assert_series_equal(p['E2'].weights,p['E4'].weights)
    assert list(p['E3_STAGE2'].values)==['F1','F2','F3','F4','F5']
    assert list(p['E3_BRIDGE'].values)==['GLOBAL','F1_RESIDUAL','F2_RESIDUAL','F3_RESIDUAL','F4_RESIDUAL']
    assert p['E3_STAGE2'].generated and p['E3_BRIDGE'].generated
    assert p['E3_STAGE2'].current_factors==1 and p['E3_BRIDGE'].current_factors==5


def test_preserve_missing_months_no_imputation(panels):
    p,_=panels
    source=p['E2'].values.copy()
    f,rows,cols,w=balanced(p['E2'],'ORIGINAL_COMPLETE',[],[])
    assert len(rows)==24 and len(cols)==91
    assert source.loc[rows,cols].notna().all().all()
    pd.testing.assert_frame_equal(f,p['E2'].z.loc[rows,cols]*w)
    pd.testing.assert_frame_equal(source,p['E2'].values)
    assert p['GROUP_F2'].values.loc[:'2023-12-31'].isna().all().all()
    assert complete_rows(p['PRODUCTION_DFM']).max()==pd.Timestamp('2024-12-31')


def test_common_full_coverage_insufficient_is_unavailable(panels):
    p,_=panels;common=complete_rows(p[MAIN[0]])
    for n in MAIN[1:]:common=common.intersection(complete_rows(p[n]))
    assert len(common)==9
    with pytest.raises(ValueError,match='T=9'):balanced(p['E2'],'COMMON_STRICT',common,common)


def test_future_rows_do_not_enter_estimator_scaling():
    from scripts.phase7d.models import standardize
    dates=pd.date_range('2020-01-31',periods=30,freq='ME')
    a=pd.DataFrame({'x':np.arange(30,dtype=float),'y':np.sin(np.arange(30))},index=dates)
    b=a.copy();b.iloc[20:]=1e12
    za,ma,sa,_=standardize(a,dates[19],minimum=12)
    zb,mb,sb,_=standardize(b,dates[19],minimum=12)
    pd.testing.assert_series_equal(ma,mb);pd.testing.assert_series_equal(sa,sb)
    pd.testing.assert_frame_equal(za.iloc[:20],zb.iloc[:20])


def test_repeated_selection_reproduces():
    f=diagonal_panel([9.,4.,1.,.5])
    a,b=select(f),select(f)
    assert a.summary==b.summary
    pd.testing.assert_frame_equal(a.criteria,b.criteria)
    pd.testing.assert_frame_equal(a.loadings,b.loadings)


def test_generated_dashboard_csv_and_exclusion_audit():
    text=(OUT/'phase7f_factor_selection_dashboard.html').read_text(encoding='utf8')
    d=json.loads(re.search(r'<script id="phase7f-data" type="application/json">(.*?)</script>',text,re.S).group(1))
    assert set(MAIN).issubset(d['models'])
    assert len(d['groups'])==5 and len(d['samples'])==6
    assert '<script src=' not in text and '<link ' not in text
    assert not re.search(r'\b(fetch\(|XMLHttpRequest|WebSocket\()',text)
    f=pd.read_csv(OUT/'phase7f_factor_selection.csv',float_precision='round_trip')
    assert len(f)==len(d['summary']) and not f.duplicated(['model','sample']).any()
    for r in d['summary']:
        if r['status']=='OK':assert r['ICp1']==f.loc[f.model.eq(r['model']) & f['sample'].eq(r['sample']),'ICp1'].iloc[0]
    a=pd.read_csv(OUT/'phase7f_variable_audit.csv')
    assert not a.duplicated(['model','sample','original_variable']).any()
    assert a.groupby(['model','sample']).size().to_dict()==f.set_index(['model','sample']).declared_variables.to_dict()
    assert a.loc[a['sample'].eq('COMMON_CALENDAR_SUBSET')].balance_status.str.startswith('EXCLUDED').any()
    for name in ['E2','E3','E4']:
        row=f.loc[f.model.eq(name) & f['sample'].eq('ORIGINAL_COMPLETE')].iloc[0]
        assert row.n_variables==91 and row.n_months==24
    assert f.loc[f['sample'].eq('COMMON_STRICT')].status.eq('UNAVAILABLE').all()


def test_production_prior_research_and_registry_preserved():
    baseline=json.loads(active_baseline().read_text())
    for path in ['results/current/current_nowcast.json','config/model_definitions.json','src/uznowcast/models/dfm.py',
                 'data/current/historical_panel.csv','data/master/v1_monthly.parquet','data/master/gdp_quarterly.parquet',
                 'registry/uzbekistan_nowcasting_v1_registry.xlsx','results/phase7d/phase7d_forecasts.csv',
                 'results/phase7e/phase7e_factor_timeseries.csv','scripts/phase7e/models.py',
                 'results/phase7e/phase7e_economic_dfm_dashboard.html']:
        assert sha(ROOT/path)==baseline[path]
    production=json.loads((ROOT/'results/current/current_nowcast.json').read_text())
    assert production['final_forecast']==8.180901340616275
    assert production['dfm_weight']==production['umidas_weight']==.5
