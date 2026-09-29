import numpy as np
import pandas as pd
import pytest

from uznowcast.models.benchmarks import (
    ar_forecast, fit_ar, historical_mean_forecast,
)


def test_historical_mean_matches_pandas():
    series = pd.Series([5.0, 6.0, 7.0])
    value, diag = historical_mean_forecast(series)
    assert value == pytest.approx(6.0)
    assert diag['n_train'] == 3


def test_historical_mean_requires_at_least_one_observation():
    with pytest.raises(ValueError):
        historical_mean_forecast(pd.Series([], dtype=float))


def test_ar1_recovers_known_dgp():
    rng = np.random.default_rng(0)
    n = 500
    values = np.zeros(n)
    for t in range(1, n):
        values[t] = 0.5 + 0.7 * values[t - 1] + rng.normal(0, 0.1)
    series = pd.Series(values)
    fit = fit_ar(series, 1)
    assert fit.coef[0] == pytest.approx(0.5, abs=0.05)
    assert fit.coef[1] == pytest.approx(0.7, abs=0.05)


def test_ar_forecast_respects_training_only():
    series = pd.Series([5.0, 5.5, 6.0, 5.8, 6.1, 6.4, 6.2])
    pred1, diag1 = ar_forecast(series.iloc[:5], 1)
    pred2, diag2 = ar_forecast(series.iloc[:6], 1)
    assert diag1['n_train'] == 4  # 5 obs → 4 AR(1) rows
    assert diag2['n_train'] == 5
    # AR(1) forecasts must depend only on the last observed value + fit
    assert pred1 != pred2


def test_ar_forecast_errors_on_short_sample():
    series = pd.Series([1.0])
    with pytest.raises(ValueError):
        ar_forecast(series, 1)
