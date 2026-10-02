"""GDP boundary, evidence, matching, and preservation regression tests."""
import sys
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).parent))
from vintages import available_gdp_vintage_as_of,validate_vintages,assert_boundary
from evidence import ROOT,OUT,metadata
from run import matched,metrics,protect,MODELS

def events():
    return pd.DataFrame([
        dict(quarter='2024Q1',publication_date='2024-04-25',value=6.2),
        dict(quarter='2024Q1',publication_date='2025-04-29',value=6.4),
        dict(quarter='2024Q2',publication_date='2024-07-24',value=6.4),
        dict(quarter='2024Q3',publication_date='2024-10-25',value=6.6),
    ]).assign(source_url='https://stat.uz/official-fixture',sha256='f'*64,value_verified=True,
        date_verified=True,time_verified=False,publication_time=None,quality='VERIFIED')

def get(frame,date,target='2024Q2',rule='STRICT'):
    return available_gdp_vintage_as_of(frame,date,target=target,timing_rule=rule).frame

def test_not_available_before_first_release():
    assert get(events(),'2024-04-24').empty

def test_first_value_and_revision_gating():
    assert get(events(),'2024-04-30').loc['2024Q1','value']==6.2
    assert get(events(),'2025-04-28','2025Q2').loc['2024Q1','value']==6.2
    assert get(events(),'2025-04-30','2025Q2').loc['2024Q1','value']==6.4

def test_target_and_future_excluded_even_after_publication():
    assert get(events(),'2026-01-01').index.tolist()==['2024Q1']

def test_date_only_same_day_both_predefined_rules():
    assert get(events(),'2024-04-25').empty
    f=get(events(),'2024-04-25',rule='PERMISSIVE_END_OF_DAY')
    assert f.loc['2024Q1','same_day_status']=='SAME_DAY_TIME_UNKNOWN'
    assert f.loc['2024Q1','value']==6.2

@pytest.mark.parametrize('clock,expected',[('2024-04-25T09:59:59+05:00',True),('2024-04-25T10:00:00+05:00',False),('2024-04-25T10:00:01+05:00',False)])
def test_verified_publication_clock_precedes_cutoff(clock,expected):
    f=events();f.loc[0,['time_verified','publication_time']]=[True,clock]
    assert ('2024Q1' in get(f,'2024-04-25T10:00:00+05:00').index)==expected

def test_duplicate_and_conflicting_vintages_rejected():
    with pytest.raises(ValueError,match='Duplicate'):
        validate_vintages(pd.concat([events(),events().iloc[[0]]]))

def test_unknown_and_suspect_evidence_excluded():
    f=events();f.loc[0,'date_verified']=False
    assert get(f,'2024-04-30').empty
    f=events();f.loc[0,'quality']='SOURCE_CHART_ORDER_SUSPECT'
    assert get(f,'2024-04-30').empty

def forecast_fixture():
    return pd.DataFrame([dict(model=m,target_quarter='2024Q1',horizon='H1',lag_mode='standard',timing_rule='STRICT',
        prediction=1.,actual_first_release=2.,actual_latest_revised=3.,evaluation_group='DEVELOPMENT_PSEUDO_OOS') for m in MODELS])

def test_exact_origin_matching_excludes_missing_component():
    f=forecast_fixture()
    assert len(matched(f))==8
    f.loc[f.model.eq('UMIDAS_USD'),'prediction']=np.nan
    assert matched(f).empty

def test_duplicate_model_origin_rejected():
    f=forecast_fixture()
    with pytest.raises(ValueError,match='Duplicate'):
        matched(pd.concat([f,f.iloc[[0]]]))

def test_target_definitions_separate():
    m=metrics(forecast_fixture(),'TEST')
    m=m.loc[m.model.eq('DFM_B')&m.horizon.eq('ALL')&m.evaluation_group.eq('POOLED_RESEARCH_ONLY')]
    assert m.set_index('target_definition').rmse.to_dict()=={'FIRST_RELEASE':1.,'LATEST_REVISED':2.}

def test_accessor_deterministic_and_does_not_mutate_events():
    f=events();before=f.copy(deep=True)
    pd.testing.assert_frame_equal(get(f,'2024-04-30'),get(f,'2024-04-30'))
    pd.testing.assert_frame_equal(f,before)

def test_revised_value_cannot_be_injected_into_returned_information_set():
    result=available_gdp_vintage_as_of(events(),'2024-04-30',target='2024Q2')
    result.frame.loc['2024Q1','value']=6.4
    with pytest.raises(AssertionError,match='substituted'):
        assert_boundary(result,'2024Q2')

def test_deterministic_full_factor_and_forecast_rerun():
    d=json.loads((OUT/'phase6b2_determinism_checks.json').read_text())
    assert d['factor_outputs_identical'] and d['all_csv_outputs_identical']
    from run import sha
    for filename,expected in d['sha256'].items():
        assert sha(OUT/filename)==expected

def test_official_registry_earliest_release_and_known_revision():
    f=pd.read_csv(OUT/'phase6b2_gdp_vintage_registry.csv').set_index('quarter')
    assert len(f)==34
    assert f.loc['2024Q1','first_release_date']=='2024-04-25'
    assert f.loc['2024Q1','first_release_value']==6.2
    assert f.loc['2024Q1','current_master_value']==pytest.approx(6.4)
    assert f.loc['2024Q4','first_release_date']=='2025-01-24'
    assert f.loc['2026Q2','first_release_date']=='2026-07-30'
    assert not f.loc['2018Q1','release_date_verified']
    assert pd.isna(f.loc['2018Q1','first_release_date'])

def test_all_used_official_evidence_hashes():
    f=pd.read_csv(OUT/'phase6b2_gdp_release_sources.csv')
    from run import sha
    assert len(f)>30
    for r in f.itertuples():
        assert sha(ROOT/r.raw_file_path)==r.sha256

def test_dfm_core_and_all_factor_paths_unchanged():
    checks=pd.read_csv(OUT/'phase6b2_factor_core_identity_checks.csv')
    assert len(checks)==60 and checks.dfm_core_unchanged.all()
    assert checks.maximum_factor_difference.max()<1e-8
    baseline=json.loads((OUT/'phase6b2_protected_before.json').read_text())
    from run import sha
    assert sha(ROOT/'scripts/research/phase6b/experiment.py')==baseline['scripts/research/phase6b/experiment.py']

def test_protected_artifacts_unchanged():
    assert protect()==592

def test_output_origins_equal_for_both_timing_rules():
    f=pd.read_csv(OUT/'phase6b2_matched_forecasts.csv')
    a=f.loc[f.timing_rule.eq('STRICT')].drop(columns='timing_rule').reset_index(drop=True)
    b=f.loc[f.timing_rule.eq('PERMISSIVE_END_OF_DAY')].drop(columns='timing_rule').reset_index(drop=True)
    sort=['model','target_quarter','horizon','lag_mode']
    pd.testing.assert_frame_equal(a.sort_values(sort).reset_index(drop=True),b.sort_values(sort).reset_index(drop=True))
