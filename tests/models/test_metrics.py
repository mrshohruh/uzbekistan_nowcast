import numpy as np
import pytest

from uznowcast.models.metrics import (
    bias, compare_to_benchmark, diebold_mariano, mae, n_forecasts,
    relative, rmse, summarize,
)


def test_metrics_basic():
    errors = [1.0, -1.0, 2.0, -2.0]
    assert rmse(errors) == pytest.approx(np.sqrt(2.5))
    assert mae(errors) == pytest.approx(1.5)
    assert bias(errors) == pytest.approx(0.0)
    assert n_forecasts(errors) == 4


def test_metrics_ignore_nan():
    errors = [1.0, np.nan, 2.0]
    assert rmse(errors) == pytest.approx(np.sqrt(2.5))
    assert mae(errors) == pytest.approx(1.5)
    assert n_forecasts(errors) == 2


def test_metrics_empty_returns_nan():
    assert np.isnan(rmse([]))
    assert np.isnan(mae([]))
    assert np.isnan(bias([]))
    assert n_forecasts([]) == 0


def test_relative_handles_zero_benchmark():
    assert np.isnan(relative(1.0, 0.0))
    assert np.isnan(relative(np.nan, 1.0))
    assert relative(0.5, 1.0) == pytest.approx(0.5)


def test_compare_to_benchmark_wiring():
    model = summarize([1.0, -1.0, 2.0])
    bench = summarize([2.0, -2.0, 3.0])
    out = compare_to_benchmark(model, bench)
    assert out['rmse_relative'] == pytest.approx(model['rmse'] / bench['rmse'])
    assert out['mae_relative'] == pytest.approx(model['mae'] / bench['mae'])


def test_diebold_mariano_needs_minimum_sample():
    result = diebold_mariano([0.1, 0.2], [0.1, 0.2])
    assert result['note'] == 'sample too small'


def test_diebold_mariano_returns_zero_for_identical_series():
    result = diebold_mariano([0.1, 0.2, 0.3, 0.4, 0.5],
                             [0.1, 0.2, 0.3, 0.4, 0.5])
    assert np.isnan(result['t_stat']) or result['t_stat'] == pytest.approx(0.0)
