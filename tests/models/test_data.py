import numpy as np
import pandas as pd
import pytest

from uznowcast.models.data import (
    build_information_set, effective_release_day, gdp_available_at,
    horizon_month_end, information_cutoff_for_variable, quarter_end,
    quarter_start, tier_variables, usable_target_quarters,
)


def test_quarter_boundaries():
    assert quarter_start('2020-Q1') == pd.Timestamp('2020-01-01')
    assert quarter_end('2020-Q1') == pd.Timestamp('2020-03-31')
    assert quarter_start('2026Q2') == pd.Timestamp('2026-04-01')
    assert quarter_end('2026Q2') == pd.Timestamp('2026-06-30')


def test_horizon_month_ends():
    assert horizon_month_end('2022-Q3', 'H1') == pd.Timestamp('2022-07-31')
    assert horizon_month_end('2022-Q3', 'H2') == pd.Timestamp('2022-08-31')
    assert horizon_month_end('2022-Q3', 'H3') == pd.Timestamp('2022-09-30')
    with pytest.raises(ValueError):
        horizon_month_end('2022-Q3', 'H4')


def test_effective_release_day_modes():
    assert effective_release_day(30, 'standard') == 30
    assert effective_release_day(30, 'conservative') == 45
    assert effective_release_day(0, 'conservative') == 15
    with pytest.raises(ValueError):
        effective_release_day(30, 'bogus')


def test_information_cutoff_drops_unreleased_month():
    origin = pd.Timestamp('2022-07-31')
    # Variable published 30 days after month-end: July 2022 is not released
    # by 2022-07-31, so the cutoff should be June 2022.
    cutoff = information_cutoff_for_variable(origin, 'x', {'x': 30}, 'standard')
    assert cutoff == pd.Timestamp('2022-06-30')


def test_build_information_set_respects_release_lag(synthetic_dataset):
    origin_quarter, horizon = '2022-Q3', 'H1'
    origin = horizon_month_end(origin_quarter, horizon)
    fields = ['ind_prod_yoy_log', 'cpi_headline_mom_log']
    panel = build_information_set(synthetic_dataset, origin_quarter, horizon,
                                  fields, mode='standard')
    # cpi has 5-day lag; July value released Aug 5, so H1 (July 31) sees at
    # most June. Industrial has 30-day lag; H1 sees at most June.
    assert panel.index.max() <= origin
    june = pd.Timestamp('2022-06-30')
    july = pd.Timestamp('2022-07-31')
    assert not np.isnan(panel.loc[june, 'ind_prod_yoy_log'])
    assert np.isnan(panel.loc[july, 'ind_prod_yoy_log'])


def test_no_future_data_at_target_horizon(synthetic_dataset):
    target_quarter, horizon = '2023-Q2', 'H3'
    panel = build_information_set(synthetic_dataset, target_quarter, horizon,
                                  ['ind_prod_yoy_log', 'cpi_headline_mom_log', 'm2_yoy_log'],
                                  mode='standard')
    origin = horizon_month_end(target_quarter, horizon)
    assert panel.index.max() <= origin
    beyond = panel.index[panel.index > pd.Timestamp('2023-12-31')]
    assert len(beyond) == 0


def test_gdp_available_at_respects_release_lag(synthetic_dataset):
    frame = gdp_available_at(synthetic_dataset, '2021-Q2', 'H1', gdp_lag_days=30,
                             mode='standard')
    # 2021-Q1 ends 2021-03-31; released 2021-04-30. Origin H1 for 2021-Q2 is
    # 2021-04-30. So GDP up through 2021-Q1 is available.
    assert frame['quarter'].iloc[-1] == '2021-Q1'


def test_usable_target_quarters(synthetic_dataset):
    quarters = usable_target_quarters(synthetic_dataset)
    assert quarters == synthetic_dataset.gdp['quarter'].tolist()


def test_tier_definitions():
    assert 'm2' in tier_variables('A')
    assert 'industrial_production' in tier_variables('B')
    assert 'construction' in tier_variables('C')
    assert 'russia_ipi' not in tier_variables('C')
    with pytest.raises(ValueError):
        tier_variables('bogus')
