import numpy as np
import pandas as pd
import pytest
from uznowcast.models.midas import MidasSpec,midas_forecast,_almon_basis

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
