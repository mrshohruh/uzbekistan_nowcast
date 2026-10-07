import numpy as np
import pandas as pd
import pytest
from uznowcast.gdp_vintages import available_gdp_vintage_as_of,validate_vintages,assert_boundary

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

def test_accessor_deterministic_and_does_not_mutate_events():
    f=events();before=f.copy(deep=True)
    pd.testing.assert_frame_equal(get(f,'2024-04-30'),get(f,'2024-04-30'))
    pd.testing.assert_frame_equal(f,before)

def test_revised_value_cannot_be_injected_into_returned_information_set():
    result=available_gdp_vintage_as_of(events(),'2024-04-30',target='2024Q2')
    result.frame.loc['2024Q1','value']=6.4
    with pytest.raises(AssertionError,match='substituted'):
        assert_boundary(result,'2024Q2')
