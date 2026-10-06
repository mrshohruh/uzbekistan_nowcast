"""Offline mathematical, release-boundary, reproduction and publication checks."""
import json
from pathlib import Path
from copy import deepcopy
import re
import numpy as np
import pandas as pd
import pytest

from scripts.phase6e.diagnostics import matched_forecasts,metrics,shapley,append_history,MODELS,KEYS
from scripts.phase6e.models import sw,FIELDS,frames
from scripts.phase6e.run import ROOT,verify_protected

OUT=ROOT/'results/phase6e'


def read(name):return json.loads((OUT/name).read_text(encoding='utf8'))
def csv(name):return pd.read_csv(OUT/name,float_precision='round_trip')


@pytest.mark.parametrize('model',['PHASE6C_DFM','U_MIDAS'])
def test_all_holdout_forecasts_reproduce(model):
    f=csv('phase6e_historical_reproduction.csv');f=f.loc[f.model.eq(model)]
    assert len(f)==12 and f.error.abs().max()<1e-7


def test_current_frozen_forecasts_reproduce():
    c=read('phase6e_current_nowcast.json')
    ledger=pd.read_csv(ROOT/'results/phase6d/phase6d_prospective_forecast_ledger.csv',float_precision='round_trip')
    withdrawn=pd.read_csv(ROOT/'results/phase6d/phase6d_withdrawal_registry.csv')
    ledger=ledger.loc[~ledger.snapshot_id.isin(withdrawn.snapshot_id)].sort_values('run_timestamp_utc').groupby('model').tail(1).set_index('model')
    assert abs(c['dfm_forecast']-ledger.loc['PHASE6C_DFM','forecast'])<1e-7
    assert abs(c['umidas_forecast']-ledger.loc['UMIDAS_USD','forecast'])<1e-7
    assert abs(c['final_forecast']-.5*c['dfm_forecast']-.5*c['umidas_forecast'])<1e-10


def test_frozen_dev_weights_and_exact_combinations():
    f=csv('phase6e_matched_forecasts.csv').pivot(index=KEYS,columns='model',values='prediction')
    bundle=json.loads((ROOT/'results/phase6d/phase6d_frozen_challengers.json').read_text())
    w=bundle['weights']['COMBO_DEV_WEIGHT']
    assert w=={'dfm':0.5438822544881572,'umidas':0.4561177455118428}
    np.testing.assert_allclose(f.COMBO_DEV_WEIGHT,w['dfm']*f.PHASE6C_DFM+w['umidas']*f.U_MIDAS,rtol=0,atol=1e-12)
    np.testing.assert_allclose(f.COMBO_50_50,.5*f.PHASE6C_DFM+.5*f.U_MIDAS,rtol=0,atol=1e-12)


def test_identical_origin_samples():
    f=csv('phase6e_matched_forecasts.csv')
    assert not f.duplicated(KEYS+['model']).any()
    assert f.groupby(KEYS).model.nunique().eq(7).all()
    assert f.groupby(KEYS).actual.nunique().eq(1).all()
    assert f.groupby('model').size().eq(12).all()


def test_promotion_is_conditional_and_legacy_preserved():
    f=csv('phase6e_model_comparison.csv').sort_values('rmse')
    p=read('phase6e_production_policy.json')
    assert f.iloc[0].model=='COMBO_50_50' and p['model']=='COMBO_50_50'
    assert p['promotion_basis']=='matched historical holdout superiority'
    assert p['prospective_validation_status']=='pending'
    assert (ROOT/p['rollback_pointer']).is_file()
    assert f.loc[f.model.eq('LEGACY_PRODUCTION_V1'),'production_status'].iloc[0]=='LEGACY'


def test_target_vintage_mismatch_rejected():
    f=pd.read_csv(ROOT/'results/phase6c/phase6c_forecasts.csv')
    mask=f.model.eq('AR1') & f.evaluation_group.eq('HOLDOUT')
    f.loc[mask,'actual']+=.1
    with pytest.raises(ValueError,match='vintages differ'):
        matched_forecasts(f,{'dfm':.54,'umidas':.46})


def test_duplicate_origin_rejected():
    f=pd.read_csv(ROOT/'results/phase6c/phase6c_forecasts.csv')
    row=f.loc[f.model.eq('AR1') & f.evaluation_group.eq('HOLDOUT') & f.lag_mode.eq('standard')].head(1)
    with pytest.raises(ValueError,match='Duplicate'):
        matched_forecasts(pd.concat([f,row]),{'dfm':.54,'umidas':.46})


def test_gdp_release_and_future_boundary():
    vk=sw.common.vintage_kernel()
    events=pd.read_csv(ROOT/'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    available=vk.available_gdp_vintage_as_of(events,pd.Timestamp('2026-07-30'),target='2026Q3',timing_rule='STRICT')
    assert '2026Q2' not in available.frame.index
    assert (available.frame.index<'2026Q3').all()
    assert pd.to_datetime(available.frame.publication_date).lt(pd.Timestamp('2026-07-30')).all()


def test_predictor_not_admitted_before_release_or_retrieval():
    from scripts.operations.shadow_worker import input_module
    f=pd.DataFrame({'retrieved_at':['2026-09-10T00:00:00Z']*3,
                    'source_release_date':['2026-09-11T00:00:00Z',None,'2026-09-09T00:00:00Z']})
    result=input_module.eligible(f,pd.Timestamp('2026-09-10T12:00:00Z'))
    assert result.index.tolist()==[1,2]
    assert input_module.eligible(f,pd.Timestamp('2026-09-09T00:00:00Z')).empty


def test_horizon_mask_excludes_unreleased_months():
    k=sw.common.kernel();spec=k.Spec('test',FIELDS,1,2)
    panel=pd.DataFrame(1.,index=pd.date_range('2019-01-31','2026-09-30',freq='ME'),columns=FIELDS)
    masked,audit=k.mask(panel,spec,'2026Q3','H3',dict.fromkeys(FIELDS,30),'standard')
    assert masked.loc['2026-09-30'].isna().all()
    assert all(r['latest_usable_observation']<=r['cutoff']<=r['origin'] for r in audit)


def test_umidas_terms_reconcile_at_every_origin():
    f=csv('phase6e_umidas_contributions.csv')
    assert set(f.term)=={'intercept','gdp_lag1','lag_0','lag_1','lag_2'}
    g=f.groupby(['forecast_origin','target_quarter','horizon'])
    assert g.size().eq(5).all()
    np.testing.assert_allclose(g.contribution_pp.sum(),g.prediction.first(),rtol=0,atol=1e-10)
    np.testing.assert_allclose(f.contribution_pp,f.coefficient*f.regressor_value,rtol=0,atol=1e-10)


def test_dfm_loading_shares_and_current_missing_pos():
    f=csv('phase6e_dfm_loadings.csv');assert set(f.indicator)==set(FIELDS)
    assert abs(f.normalized_loading_share_pct.sum()-100)<1e-10
    np.testing.assert_allclose(f.normalized_loading_share_pct,100*f.absolute_loading/f.absolute_loading.sum(),atol=1e-10)
    pos=f.loc[f.indicator.eq('pos_turnover')].iloc[0]
    assert pos.data_period=='2024-12' and pd.isna(pos.quarter_signal)
    d=csv('phase6e_current_drivers.csv')
    assert pd.isna(d.loc[d.indicator.eq('pos_turnover'),'contribution_or_signal'].iloc[0])


def test_exact_news_reconciles_both_models_and_ensemble():
    f=csv('phase6e_news_decomposition.csv')
    for _,g in f.groupby(['old_as_of_date','new_as_of_date','source_model']):
        assert abs(g.news_impact_pp.sum()-(g.new_forecast.iloc[0]-g.old_forecast.iloc[0]))<1e-10
    for _,g in f.groupby(['old_as_of_date','new_as_of_date']):
        wide=g.pivot(index='indicator',columns='source_model',values='news_impact_pp')
        np.testing.assert_allclose(wide.COMBO_50_50,.5*wide.PHASE6C_DFM+.5*wide.U_MIDAS,rtol=0,atol=1e-10)


def test_shapley_interactions_order_invariance():
    def value(keys):return np.array([int('a' in keys)+2*int('b' in keys)+6*int('a' in keys and 'b' in keys)])
    a,delta=shapley(['a','b'],value);b,_=shapley(['b','a'],value)
    np.testing.assert_allclose(a['a'],[4]);np.testing.assert_allclose(a['b'],[5])
    np.testing.assert_allclose(a['a'],b['a']);np.testing.assert_allclose(sum(a.values()),delta)


def test_shapley_empty_and_single_group():
    a,d=shapley([],lambda _:np.array([2.,3.]));assert a=={};np.testing.assert_array_equal(d,[0,0])
    a,d=shapley(['x'],lambda keys:np.array([2.,3.])+len(keys)*np.array([.2,-.3]))
    np.testing.assert_allclose(a['x'],d)


def test_actual_model_news_with_predictor_and_gdp_revision_groups():
    from scripts.phase6e.models import fit_info
    from scripts.phase6e.diagnostics import news
    manifest=read('phase6e_run_manifest.json')
    path=ROOT/manifest['current_state_manifest']
    info=json.loads((path.parent/'shadow_reproduction.json').read_text())['info']
    origin=pd.Timestamp(manifest['as_of']).tz_convert('Asia/Tashkent').tz_localize(None)
    old_fit=fit_info(info,ROOT,origin)
    changed=deepcopy(info)
    for row in reversed(changed['panel']):
        if row['industrial_production'] is not None:
            row['industrial_production']+=.2;break
    for row in reversed(changed['panel']):
        if row['usd_uzs'] is not None:
            row['usd_uzs']+=.1;break
    for row in reversed(changed['benchmark_monthly']):
        if row['usd_uzs_mom_dlog'] is not None:
            row['usd_uzs_mom_dlog']+=.1;break
    changed['GDP'][-1]['value']+=.1
    changed['GDP'][-1]['published_value']+=.1
    new_fit=fit_info(changed,ROOT,origin)
    result=pd.DataFrame(news(info,changed,ROOT,origin,origin,old_fit,new_fit))
    assert set(result.indicator)>={'industrial_production','usd_uzs','gdp_real_yoy','PARAMETER_REESTIMATION'}
    for model,group in result.groupby('source_model'):
        assert abs(group.news_impact_pp.sum()-group.total_revision_pp.iloc[0])<1e-10
    assert abs(new_fit['final']-old_fit['final'])>1e-8


def test_r2_and_os_are_recomputed_on_same_origins():
    f=csv('phase6e_matched_forecasts.csv');m=csv('phase6e_r2_metrics.csv')
    for row in m.itertuples():
        block=f if row.horizon=='ALL' else f.loc[f.horizon.eq(row.horizon)]
        g=block.loc[block.model.eq(row.model)].set_index(KEYS).sort_index()
        ar=block.loc[block.model.eq('AR1')].set_index(KEYS).sort_index()
        assert g.index.equals(ar.index) and len(g)==row.n
        error=g.actual-g.prediction;sse=(error**2).sum()
        assert abs(row.r2-(1-sse/((g.actual-g.actual.mean())**2).sum()))<1e-12
        assert abs(row.r2_os_vs_ar1-(1-sse/((ar.actual-ar.prediction)**2).sum()))<1e-12


def test_history_is_append_only_and_identical_inputs_deduplicated(tmp_path):
    path=tmp_path/'history.csv'
    row=dict(as_of_date='2026-10-05',target_quarter='2026Q3',horizon='H3',production_model='COMBO_50_50',
             DFM_forecast=8.,UMIDAS_forecast=7.,final_forecast=7.5,input_data_fingerprint='a',change_from_previous=None)
    _,added=append_history(path,row);assert added
    before=path.read_bytes();_,added=append_history(path,dict(row,as_of_date='2026-10-06'));assert not added
    assert path.read_bytes()==before
    f,added=append_history(path,dict(row,input_data_fingerprint='b',final_forecast=7.6));assert added
    assert path.read_bytes().startswith(before) and abs(f.change_from_previous.iloc[-1]-.1)<1e-12


def test_dashboard_headline_is_calculated_and_local():
    html=(ROOT/'dashboard/uzbekistan_nowcast_v2.html').read_text(encoding='utf8')
    c=read('phase6e_current_nowcast.json')
    headline=float(re.search(r'data-nowcast="([^"]+)"',html).group(1))
    assert headline==c['final_forecast']
    assert '<script src=' not in html and '<link ' not in html and 'fetch(' not in html
    assert not re.search(r'>\s*(?:NaN|[+-]?inf(?:inity)?)\s*<',html,re.I)
    assert 'prospective validation pending' in html
    assert (ROOT/'dashboard/current/uzbekistan_nowcast.html').read_bytes()==(ROOT/'dashboard/uzbekistan_nowcast_v2.html').read_bytes()


def test_frozen_artifacts_unchanged():
    result=verify_protected(ROOT,read('phase6e_pre_change_state.json'))
    assert not result['frozen_artifacts_modified']


def test_deterministic_independent_build():
    path=OUT/'phase6e_determinism.json'
    if not path.exists():pytest.skip('Independent rerun executed after first build')
    result=read(path.name)
    assert result['status']=='PASS' and result['differences']==[]
