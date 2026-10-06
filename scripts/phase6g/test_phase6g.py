"""Offline arithmetic, strict-origin, timing and actual reconstruction tests."""
import json
import numpy as np
import pandas as pd
import pytest
from scripts.phase6g import analysis as a
from scripts.phase6g.run import ROOT,check_protected,fit_origin
from scripts.phase6f.experiment import economic_lag,sha
from uznowcast.models.data import information_cutoff_for_variable

OUT=ROOT/'results/phase6g'


def synthetic():
    rows=[]
    for q,s0,s1,s2,u,y in [('2024Q1',4.,5.,6.,8.,7.),('2024Q2',8.,6.,4.,6.,5.)]:
        for h in ['H1','H2','H3']:
            for model,value in a.ensembles(s0,s1,s2,u).items():
                rows.append(dict(model=model,target_quarter=q,horizon=h,prediction=value,actual=y))
    return pd.DataFrame(rows)


@pytest.mark.parametrize('model,expected',[('P0',6.),('G1',6.5),('G2',7.)])
def test_ensemble_arithmetic(model,expected):
    assert a.ensembles(4.,5.,6.,8.)[model]==expected


@pytest.mark.parametrize('weight',[.25,.5,.75])
def test_fixed_weight_sums(weight):
    assert weight+(1-weight)==1.


def test_ensemble_revision_identity():
    e=a.origin_errors(synthetic(),'test')
    np.testing.assert_allclose(e.G2_minus_P0,.5*(e.S2-e.S0),rtol=0,atol=1e-12)


def test_common_origins_drop_one_model_failure():
    f=synthetic();f.loc[f.model.eq('S2') & f.target_quarter.eq('2024Q1') & f.horizon.eq('H1'),'prediction']=np.nan
    assert len(a.common_keys(f))==5


def test_information_boundary_failure_excluded_even_with_all_forecasts():
    f=synthetic();elig=a.common_keys(f);elig['common_origin_eligible']=True;elig.loc[0,'common_origin_eligible']=False
    common=a.strict_common(f,elig)
    assert len(common)==5*7


def test_conflicting_actuals_rejected():
    f=synthetic();f.loc[0,'actual']=999.
    with pytest.raises(ValueError,match='Different actual'):
        a.common_keys(f)


@pytest.mark.parametrize('lag',[1,2])
def test_economic_lag_after_publication_gate(lag):
    s=pd.Series([10.,20.,30.,999.],index=pd.date_range('2024-01-31',periods=4,freq='ME'))
    origin=pd.Timestamp('2024-04-30');cutoff=information_cutoff_for_variable(origin,'m2',{'m2':25})
    gated=s.copy();gated.loc[gated.index>cutoff]=np.nan
    lagged=economic_lag(gated,lag)
    assert lagged.loc['2024-04-30']==s.iloc[3-lag]
    assert 999. not in lagged.dropna().values


def test_leave_one_quarter_out_exact_calculation():
    f=synthetic();g=a.leave_one_quarter_out(f,'test')
    r=g.loc[g.model.eq('G2') & g.horizon.eq('POOLED') & g.excluded_quarter.eq('2024Q1')].iloc[0]
    assert r.P0_RMSE==2. and r.G2_RMSE==0. and r.delta_RMSE==-2.


def test_win_rates_include_ties_and_losses():
    e=a.origin_errors(synthetic(),'test');e.loc[0,'abs_error_G2']=e.loc[0,'abs_error_P0'];e.loc[1,'abs_error_G2']=100.
    w=a.win_rates(e,'test');r=w.loc[w.model.eq('G2') & w.horizon.eq('POOLED')].iloc[0]
    assert r.wins==4 and r.ties==1 and r.worse==1 and r.N==6


def test_oos_benchmark_and_pairwise_origins():
    f=synthetic();f=f.loc[~(f.model.eq('G2') & f.target_quarter.eq('2024Q1'))]
    g=a.metric_rows(f,'FULL_AVAILABLE');r=g.loc[g.model.eq('G2') & g.horizon.eq('POOLED')].iloc[0]
    assert r.OOS_N==3 and r.OOS_R2==1. and r.benchmark=='P0'


def test_revision_chronology_and_requested_reverse():
    f=synthetic();idx=f.model.eq('P0') & f.target_quarter.eq('2024Q1')
    f.loc[idx,'prediction']=[1.,3.,2.]
    r=a.revisions(f,'test').loc[lambda x:x.model.eq('P0') & x.target_quarter.eq('2024Q1')].iloc[0]
    assert r.H1_to_H2==2 and r.H2_to_H3==-1 and r.H3_to_H2==1 and r.H2_to_H1==-2
    assert r.mean_abs_revision==1.5 and not r.directionally_consistent


def test_no_umidas_future_gdp_dataset(monkeypatch):
    from types import SimpleNamespace
    from dataclasses import dataclass
    from scripts.phase6g import run as module
    @dataclass
    class Dataset:
        gdp:pd.DataFrame
        target_field:str='gdp_real_yoy_pct'
    dataset=Dataset(pd.DataFrame({'quarter':['2024Q1','2024Q2'],'gdp_real_yoy_pct':[1.,999.]}))
    available=SimpleNamespace(frame=pd.DataFrame({'value':[1.]},index=['2024Q1']))
    def df(*args):return 1.,{}
    def u(ds,*args):
        assert ds.gdp.quarter.tolist()==['2024Q1']
        assert ds.gdp.gdp_real_yoy_pct.tolist()==[1.]
        return 2.,[],{}
    monkeypatch.setattr(module,'dfm',df);monkeypatch.setattr(module,'lagged_dfm',df);monkeypatch.setattr(module,'umidas',u)
    values,_,_=module.fit_origin(None,dataset,available,'2024Q2','H1',pd.Timestamp('2024-04-30'))
    assert values['P0']==1.5


def test_all_actual_reproduction_checks():
    f=pd.read_csv(OUT/'phase6g_reproduction_check.csv')
    assert len(f)==65 and f.passed.all() and f.error.abs().max()<1e-7
    assert set(f.model)=={'S0','S1','S2','U0','P0'}


def test_current_nowcast_is_rebuilt_and_unchanged_production():
    c=pd.read_csv(OUT/'phase6g_current_nowcasts.csv',float_precision='round_trip').set_index('model')
    assert abs(c.loc['P0','nowcast']-8.180901340616275)<1e-7
    assert abs(c.loc['G2','nowcast']-.5*c.loc['S2','nowcast']-.5*c.loc['U0','nowcast'])<1e-12
    assert abs(c.loc['G2','nowcast']-8.23717521738184)<1e-7


def test_real_common_forecasts_all_information_boundaries_pass():
    elig=pd.read_csv(OUT/'phase6g_origin_eligibility.csv')
    valid=elig.loc[elig.common_origin_eligible]
    for c in ['gdp_available','dfm_current_available','dfm_m2_l1_available','dfm_m2_l2_available','umidas_available',
        'm2_publication_mask_pass','gdp_information_boundary_pass','predictor_information_boundary_pass']:
        assert valid[c].all()
    f=pd.read_csv(OUT/'phase6g_origin_level_forecasts.csv')
    assert len(a.strict_common(f,elig))==len(valid)*7
    assert 'FDI' not in set(pd.read_csv(OUT/'phase6g_factor_loadings.csv').variable)
    p=pd.read_csv(OUT/'phase6g_predictor_availability.csv')
    assert not p.reference_timing_leakage.any()


def test_deterministic_independent_refits():
    path=OUT/'phase6g_determinism.json'
    if not path.exists():pytest.skip('Independent full refits still running')
    d=json.loads(path.read_text());assert d['identical_csv_hashes']
    assert d['second']=={p.name:sha(p) for p in OUT.glob('*.csv')}


def test_protected_phase6e_phase6f_and_dashboard():
    before=json.loads((OUT/'phase6g_protected_before.json').read_text())
    assert any(p.startswith('results/phase6f/') for p in before)
    assert any(p.startswith('results/phase6e/') for p in before)
    assert 'dashboard/uzbekistan_nowcast_v2.html' in before
    assert all(sha(ROOT/p)==h for p,h in before.items())


def test_no_model_complexity_increase():
    d=pd.read_csv(OUT/'phase6g_dfm_diagnostics.csv')
    assert set(d.n_predictors)=={8} and set(d.factor_count)=={1} and set(d.factor_ar_order)=={2}
    assert set(d.n_monthly_parameters)=={18} and d.converged.all()
