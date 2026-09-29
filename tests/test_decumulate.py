import numpy as np
import pandas as pd
import pytest
from uznowcast.transforms.decumulate import decumulate_ytd
from uznowcast.transforms.growth import log_growth


def frame(months, values):
    return pd.DataFrame({'reference_date':pd.to_datetime(months),'raw_value':values,'quality_flag':''})


def test_january_through_march():
    got=decumulate_ytd(frame(['2024-01-31','2024-02-29','2024-03-31'],[10,25,45]))
    assert got.monthly_flow.tolist()==[10,15,20]
    assert got.raw_value.tolist()==[10,25,45]


def test_december_january_reset():
    got=decumulate_ytd(frame(['2023-12-31','2024-01-31','2024-02-29'],[200,12,25]))
    assert np.isnan(got.monthly_flow.iloc[0])
    assert got.monthly_flow.iloc[1:].tolist()==[12,13]


def test_missing_previous_and_negative():
    got=decumulate_ytd(frame(['2024-01-31','2024-03-31','2024-04-30'],[10,30,29]))
    assert np.isnan(got.monthly_flow.iloc[1])
    assert 'missing_previous_month' in got.quality_flag.iloc[1]
    assert got.monthly_flow.iloc[2]==-1
    assert 'nonpositive' in got.quality_flag.iloc[2]


def test_duplicate_month():
    with pytest.raises(ValueError,match='Duplicate'):
        decumulate_ytd(frame(['2024-01-01','2024-01-31'],[1,2]))


def test_growth_calendar_alignment_and_positivity():
    f=frame(['2023-01-31','2023-03-31','2024-01-31','2024-02-29','2024-03-31'],[10,0,20,40,50])
    got=log_growth(f,'raw_value',12)
    assert got.clean_value.iloc[2]==pytest.approx(100*np.log(2))
    assert np.isnan(got.clean_value.iloc[3])
    assert 'nonpositive_growth_input' in got.quality_flag.iloc[4]


def test_decumulation_before_yoy():
    f=frame(['2023-01-31','2023-02-28','2024-01-31','2024-02-29'],[10,30,20,50])
    got=log_growth(decumulate_ytd(f),'monthly_flow',12)
    assert got.clean_value.iloc[-1]==pytest.approx(100*np.log(30/20))
