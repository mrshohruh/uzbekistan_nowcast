"""Prospective freeze, vintage, timing, paired scoring and governance invariants."""
from copy import deepcopy
from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest

from uznowcast.shadow.storage import append_record, digest, file_hash, freeze, records
from uznowcast.shadow.evaluation import (PRODUCTION, HORIZONS, evidence_status, governance,
                                        influence, matched_metrics, quarter_scores)
from uznowcast.shadow import phase5d as p

ROOT=Path(__file__).resolve().parents[2]


def paired(quarters=4):
    return pd.DataFrame([dict(target_quarter=str(pd.Period('2026Q3',freq='Q')+i),
                              forecast=8.1,production_forecast=8.4,actual=8.0)
                         for i in range(quarters)])


def test_cohort_does_not_depend_on_new_outcomes():
    source=pd.read_csv(ROOT/'results/challengers/phase5c/phase5c_challenger_leaderboard.csv')
    first=p.select_cohort(source)
    changed=source.copy()
    changed['new_actual']=900
    assert first==p.select_cohort(changed)


def test_reject_cannot_enter_even_with_best_rmse():
    source=pd.read_csv(ROOT/'results/challengers/phase5c/phase5c_challenger_leaderboard.csv')
    selected,excluded=p.select_cohort(source)
    assert all(c['phase5c_gate']!='REJECT' for c in selected)
    assert any(c['model_name']=='challenger_umidas_gold_exports_proxy_usd_m_l1' for c in excluded)
    assert len(selected)==3


def test_production_and_freeze_remain_identical():
    seal=p.load(ROOT/p.OUT/'phase5d_freeze_manifest.json')
    protected=dict(seal['protected_hashes'])
    pointer='dashboard/current/uzbekistan_nowcast.html'
    if (ROOT/'results/operations/current_production.json').exists():
        expected=protected.pop(pointer)
        assert file_hash(ROOT/'results/phase6e/legacy_current_dashboard.html')==expected
        active=p.load(ROOT/'results/operations/current_production.json')
        assert file_hash(ROOT/pointer)==file_hash(ROOT/active['dashboard'])
        assert p.load(ROOT/active['policy'])['status']=='PHASE6E_PROMOTED'
    p.verify(ROOT,protected)
    p.verify(ROOT,seal['frozen_hashes'])
    cohort=p.load(ROOT/p.OUT/'phase5d_frozen_challenger_cohort.json')
    assert cohort['production']['weights']=={'ar2':0.5,'umidas_usd_uzs_mom_dlog':0.5}
    assert cohort['production']['lag_structure']=={'ar2':2,'usd_umidas':3}


def test_overwrite_prohibited(tmp_path):
    identity=digest({'key':1})
    append_record(tmp_path,identity,{'value':2})
    append_record(tmp_path,identity,{'value':2})
    with pytest.raises(ValueError,match='Immutable record conflict'):
        append_record(tmp_path,identity,{'value':3})
    assert records(tmp_path)==[{'value':2}]


def test_ledger_detects_tamper(tmp_path):
    identity=digest({'key':1})
    append_record(tmp_path,identity,{'value':2})
    (tmp_path/f'{identity}.json').write_text('{"value":3}')
    with pytest.raises(ValueError,match='corruption'):
        records(tmp_path)


@pytest.mark.parametrize('field',['retrieved_at','source_release_date','eligible_at'])
def test_future_information_rejected(field):
    row={'retrieved_at':'2026-09-01T00:00:00Z',field:'2026-10-01T00:00:00Z'}
    with pytest.raises(ValueError):
        p.validate_information_set({'observations':[row]},'2026-09-30T00:00:00Z')


def test_valid_lag_and_retrieval_information():
    p.validate_information_set({'observations':[{'retrieved_at':'2026-09-29T10:00:00Z',
                               'source_release_date':None,'eligible_at':'2026-09-01T00:00:00Z'}]},
                              '2026-09-30T00:00:00Z')


def test_deterministic_unique_forecast_id():
    row=dict(target_quarter='2026Q3',model=PRODUCTION,horizon='H2',release_lag_mode='standard',
             information_cutoff='2026-09-30',monthly_data_hash='a',quarterly_data_hash='b',model_spec_hash='c')
    assert p.forecast_id(row)==p.forecast_id(dict(reversed(list(row.items()))))
    other=dict(row,horizon='H3')
    assert p.forecast_id(row)!=p.forecast_id(other)


def test_matched_rmse_ignores_unmatched_observations():
    data=paired(4)
    data.loc[0,'production_forecast']=np.nan
    data.loc[0,'forecast']=1000
    metrics=matched_metrics(data)
    assert metrics['matched_n']==3
    assert metrics['rmse']==pytest.approx(0.1)
    assert metrics['production_rmse']==pytest.approx(0.4)
    assert metrics['relative_rmse']==pytest.approx(0.25)
    assert metrics['bias']==pytest.approx(0.1)


def test_no_scoring_without_actual():
    assert quarter_scores(pd.DataFrame(),pd.DataFrame()).empty


def test_historical_realization_not_admitted(tmp_path,monkeypatch):
    monkeypatch.setattr(p,'initialize',lambda root:{'frozen_at_utc':'2026-10-02T00:00:00Z'})
    with pytest.raises(ValueError,match='Historical outcomes'):
        p.register_realization(tmp_path,{'target_quarter':'2026Q2'})


def test_exact_inherited_values_and_no_synthetic_horizons():
    source=pd.read_csv(ROOT/'results/challengers/phase5c/phase5c_current_shadow_nowcasts.csv',float_precision='round_trip').set_index('model')
    rows=records(ROOT/p.OUT/'forecast_records')
    assert len(rows)==12
    for row in rows:
        assert row['horizon'] in HORIZONS
        if row['horizon']=='H2':
            assert row['forecast_value']==source.loc[row['model'],'H2_nowcast']
            assert row['source_hash']==file_hash(ROOT/row['source_file'])
        else:
            assert row['forecast_value'] is None
            assert row['forecast_status']=='UNAVAILABLE'
    production=next(r for r in rows if r['model']==PRODUCTION and r['horizon']=='H2')
    assert production['forecast_value']==7.6239786595896035


@pytest.mark.parametrize('n,expected',[(0,'NOT_YET_EVALUABLE'),(1,'INSUFFICIENT_PROSPECTIVE_EVIDENCE'),
    (3,'INSUFFICIENT_PROSPECTIVE_EVIDENCE'),(4,'EARLY_PROSPECTIVE_EVIDENCE'),
    (6,'MODERATE_PROSPECTIVE_EVIDENCE'),(8,'MATURE_PROSPECTIVE_EVIDENCE')])
def test_quantity_stages(n,expected):
    assert evidence_status(n)==expected


def test_no_early_governance_or_production_promotion():
    checks=dict.fromkeys(['influence','horizons','mae','bias','coverage','failures','revisions',
                          'lag_consistency','reproducible'],True)
    for n in range(4):
        assert governance(n,{'relative_rmse':0.5},checks)=='INSUFFICIENT_PROSPECTIVE_EVIDENCE'
    assert governance(4,{'relative_rmse':0.5},checks)=='GOVERNANCE_REVIEW_ELIGIBLE'
    checks['lag_consistency']=False
    assert governance(8,{'relative_rmse':0.5},checks)=='PROMISING_SHADOW'
    assert governance(8,{'relative_rmse':1.1},checks)=='UNDERPERFORMING'


def test_influence_robust_and_fragile():
    assert influence(paired())['influence_flag']=='ROBUST_PROSPECTIVE_IMPROVEMENT'
    data=paired()
    data['forecast']=8.5
    data.loc[0,'production_forecast']=12
    data.loc[0,'forecast']=8
    assert matched_metrics(data)['relative_rmse']<1
    assert influence(data)['influence_flag']=='FRAGILE_PROSPECTIVE_IMPROVEMENT'
    assert len(influence(data)['dropped_quarter_results'])==4
    assert influence(paired(3))['influence_flag']=='INSUFFICIENT_PROSPECTIVE_EVIDENCE'


def test_dashboard_labels_and_production_untouched():
    dashboard=(ROOT/'dashboard/phase5d_shadow_monitor.html').read_text(encoding='utf-8')
    assert 'NOT AN OFFICIAL MODEL REPLACEMENT' in dashboard
    assert 'PHASE 5D' in dashboard
    assert 'genuinely realized prospective quarters: 0' in dashboard
    manifest=p.load(ROOT/p.OUT/'phase5d_run_manifest.json')
    assert manifest['production_artifacts_modified'] is False
    assert manifest['protected_hash_failures']==[]


def test_quarter_score_filters_post_release_and_matches_horizon():
    f=pd.DataFrame([dict(target_quarter='2026Q3',horizon=h,model=m,release_lag_mode='standard',
                         forecast_timestamp_utc='2026-09-30T12:00:00Z',information_cutoff='2026-09-30T00:00:00Z',
                         forecast_value=value) for h,m,value in [('H2',PRODUCTION,8.4),('H2','challenger',8.1),('H3','challenger',8.2)]])
    actual=pd.DataFrame([dict(target_quarter='2026Q3',release_date='2026-10-25T00:00:00Z',
                             first_observed_value=8.0,evidence_class='LIVE_PROSPECTIVE_REALIZED')])
    scores=quarter_scores(f,actual)
    assert scores[(scores.model=='challenger')&(scores.horizon=='H2')].error.iloc[0]==pytest.approx(.1)
    assert scores[(scores.model=='challenger')&(scores.horizon=='H3')].production_forecast.isna().all()
    f.loc[f.model=='challenger','forecast_timestamp_utc']='2026-11-01T00:00:00Z'
    assert len(quarter_scores(f,actual))==1
    actual['evidence_class']='HISTORICAL_POST_DEVELOPMENT_TEST'
    assert quarter_scores(f,actual).empty


def test_first_vintage_is_primary_and_revisions_separate():
    f=pd.DataFrame([dict(target_quarter='2026Q3',horizon=h,model='challenger',release_lag_mode='standard',
                         forecast_timestamp_utc=stamp,forecast_value=v) for h,v,stamp in
        [('H1',7,'2026-08-01T00:00:00Z'),('H2',8,'2026-09-01T00:00:00Z'),('H2',20,'2026-09-02T00:00:00Z'),('H3',9,'2026-10-01T00:00:00Z')]])
    result=p.revision_table(f).iloc[0]
    assert result.H1_H2_revision==1
    assert result.H2_H3_revision==1
    assert result.H1_H3_revision==2


def test_frozen_content_cannot_change_after_outcome(tmp_path):
    path=tmp_path/'cohort.json'
    freeze(path,{'models':['a']})
    before=file_hash(path)
    with pytest.raises(ValueError):
        freeze(path,{'models':['a','new_winner']})
    assert file_hash(path)==before


def test_future_quarters_use_current_cutoff_and_frozen_weights(tmp_path,monkeypatch):
    from uznowcast.models.data import load_dataset
    from uznowcast.models import benchmarks,midas,bridge,data
    cohort=p.load(ROOT/p.OUT/'phase5d_frozen_challenger_cohort.json')
    dataset=load_dataset(ROOT)
    gdp=pd.DataFrame({'quarter':[str(q) for q in pd.period_range('2018Q1','2027Q3',freq='Q')],
                      'gdp_real_yoy_pct':7.,'retrieved_at':'2027-10-20T00:00:00Z','source_release_date':None})
    observations=pd.DataFrame([dict(reference_period=str(month.to_period('M')),reference_date=month,
        retrieved_at='2027-12-31T00:00:00Z',source_release_date=None,frequency='M',clean_value=float(i+1),
        clean_model_field='usd_uzs_mom_dlog') for i,month in enumerate(pd.date_range('2027-10-31','2027-12-31',freq='ME'))])
    late=observations.iloc[0].copy()
    late['retrieved_at']='2028-02-01T00:00:00Z'
    late['clean_value']=9999
    observations=pd.concat([observations,pd.DataFrame([late])],ignore_index=True)
    monkeypatch.setattr(p,'initialize',lambda root:cohort)
    monkeypatch.setattr(p,'now',lambda:'2028-01-31T12:00:00Z')
    monkeypatch.setattr(data,'load_dataset',lambda *a,**k:deepcopy(dataset))
    original=pd.read_parquet
    monkeypatch.setattr(pd,'read_parquet',lambda path:observations.copy() if Path(path).name=='observations_long.parquet' else gdp.copy())
    monkeypatch.setattr(benchmarks,'ar_forecast',lambda *a,**k:(7.,{'n_train':36}))
    monkeypatch.setattr(midas,'midas_forecast',lambda *a,**k:(8.,{'n_train':36}))
    monkeypatch.setattr(bridge,'bridge_forecast',lambda *a,**k:(9.,{}))
    monkeypatch.setattr(p.legacy,'git_text',lambda *a:'test-commit')
    for relative in [p.legacy.MONTHLY_REL,p.legacy.QUARTERLY_REL,Path('metadata/observations_long.parquet')]:
        destination=tmp_path/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(b'test-input')
    (tmp_path/p.OUT).mkdir(parents=True)
    captured=[]
    monkeypatch.setattr(p,'save_forecast',lambda root,row,info:captured.append((row,info)))
    p.generate(tmp_path,'2027Q4')
    assert len(captured)==8
    for row,info in captured:
        assert row['horizon']=='H3'
        assert row['target_quarter']=='2027Q4'
        assert row['information_cutoff']=='2028-01-31T12:00:00Z'
        p.validate_information_set(info,row['information_cutoff'])
        if row['model']=='combination_equal_weight':
            assert row['forecast_value']==pytest.approx((7+7.5+8+9)/4)
        assert all(obs['retrieved_at']!='2028-02-01T00:00:00Z' for obs in info['observations'])
    assert {r['release_lag_mode'] for r,_ in captured}=={'standard','conservative'}


def test_missing_operational_component_is_not_renormalized():
    cohort=p.load(ROOT/p.OUT/'phase5d_frozen_challenger_cohort.json')
    equal=next(c for c in cohort['challengers'] if c['model_name']=='combination_equal_weight')
    components={name:8. for name in equal['components'][:-1]}
    result=sum(equal['weights_by_horizon']['H2'][c]*components.get(c,np.nan) for c in equal['components'])
    assert np.isnan(result)
