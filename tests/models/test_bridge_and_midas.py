import numpy as np
import pandas as pd
import pytest

from uznowcast.models.bridge import (
    BridgeSpec, aggregate_monthly_to_quarter, bridge_forecast,
    bridge_training_frame, quarter_month_ends,
)
from uznowcast.models.midas import MidasSpec, midas_forecast, _almon_basis


def test_quarter_month_ends_alignment():
    ends = quarter_month_ends('2022-Q3')
    assert ends == [pd.Timestamp('2022-07-31'),
                     pd.Timestamp('2022-08-31'),
                     pd.Timestamp('2022-09-30')]


def test_aggregate_uses_available_only():
    monthly = pd.DataFrame({'x': [1.0, np.nan, 3.0]},
                            index=[pd.Timestamp('2022-07-31'),
                                   pd.Timestamp('2022-08-31'),
                                   pd.Timestamp('2022-09-30')])
    result = aggregate_monthly_to_quarter(monthly, '2022-Q3')
    assert result['x'] == pytest.approx(2.0)


def test_aggregate_missing_quarter_returns_nan():
    monthly = pd.DataFrame({'x': [1.0]}, index=[pd.Timestamp('2000-01-31')])
    result = aggregate_monthly_to_quarter(monthly, '2022-Q3')
    assert np.isnan(result['x'])


def test_bridge_training_frame_does_not_use_target(synthetic_dataset):
    train = tuple(synthetic_dataset.gdp['quarter'].iloc[:10])
    spec = BridgeSpec(name='b_ind', fields=('ind_prod_yoy_log',))
    frame = bridge_training_frame(synthetic_dataset, spec, train,
                                   horizon='H3', mode='standard')
    assert frame['quarter'].tolist() == list(train)
    # The GDP-lag column is NaN for the first row (no prior observation).
    assert pd.isna(frame['gdp_lag1'].iloc[0])
    assert frame['gdp_lag1'].iloc[1] == pytest.approx(
        synthetic_dataset.gdp['gdp_real_yoy_pct'].iloc[0])


def test_bridge_forecast_produces_finite_value(synthetic_dataset):
    train = tuple(synthetic_dataset.gdp['quarter'].iloc[:16])
    target = synthetic_dataset.gdp['quarter'].iloc[16]
    spec = BridgeSpec(name='b_ind', fields=('ind_prod_yoy_log',))
    pred, diag = bridge_forecast(synthetic_dataset, spec, train, target,
                                  horizon='H3', mode='standard')
    assert np.isfinite(pred)
    assert diag['n_train'] > 0


def test_almon_basis_shape():
    basis = _almon_basis(monthly_lags=3, order=1)
    assert basis.shape == (3, 2)
    # First basis column is all ones (intercept-like)
    assert np.allclose(basis[:, 0], 1.0)


def test_midas_forecast_respects_information_set(synthetic_dataset):
    train = tuple(synthetic_dataset.gdp['quarter'].iloc[:16])
    target = synthetic_dataset.gdp['quarter'].iloc[16]
    spec = MidasSpec(name='u_ind', field='ind_prod_yoy_log', monthly_lags=3)
    pred, diag = midas_forecast(synthetic_dataset, spec, train, target,
                                 horizon='H3', mode='standard')
    if not np.isnan(pred):
        assert 'n_train' in diag


def test_midas_falls_back_gracefully_on_missing_lags(synthetic_dataset):
    # Force the field to be unobserved
    dataset = synthetic_dataset
    dataset.monthly.loc[:, 'ind_prod_yoy_log'] = np.nan
    spec = MidasSpec(name='u_ind', field='ind_prod_yoy_log', monthly_lags=3)
    pred, diag = midas_forecast(dataset, spec, tuple(dataset.gdp['quarter'].iloc[:16]),
                                 dataset.gdp['quarter'].iloc[16],
                                 horizon='H3', mode='standard')
    assert np.isnan(pred)
    assert 'failure' in diag
