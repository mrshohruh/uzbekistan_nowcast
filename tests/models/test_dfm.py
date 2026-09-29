import numpy as np
import pandas as pd
import pytest

from uznowcast.models.dfm import DFMSpec, _em_pca, dfm_forecast


def test_em_pca_recovers_hidden_factor():
    rng = np.random.default_rng(0)
    T, N = 100, 5
    factor = rng.normal(size=T)
    loadings = rng.normal(size=(1, N))
    X = factor[:, None] @ loadings + rng.normal(scale=0.05, size=(T, N))
    factors, fitted, diag = _em_pca(X, n_factors=1, max_iter=30, tol=1e-8)
    reconstruction = factors @ fitted.T
    # Should reconstruct up to a sign flip
    corr = abs(np.corrcoef(factor, factors[:, 0])[0, 1])
    assert corr > 0.9
    assert diag['fraction_missing'] == 0.0


def test_em_pca_tolerates_missing_values():
    rng = np.random.default_rng(1)
    T, N = 60, 4
    factor = rng.normal(size=T)
    loadings = rng.normal(size=(1, N))
    X = factor[:, None] @ loadings + rng.normal(scale=0.05, size=(T, N))
    # Introduce 20% missing at random
    mask = rng.uniform(size=X.shape) < 0.2
    with_gaps = X.copy()
    with_gaps[mask] = np.nan
    factors, _, diag = _em_pca(with_gaps, n_factors=1, max_iter=50, tol=1e-8)
    assert diag['fraction_missing'] == pytest.approx(mask.mean(), abs=1e-2)
    corr = abs(np.corrcoef(factor, factors[:, 0])[0, 1])
    assert corr > 0.7


def test_dfm_forecast_returns_finite_or_labelled_failure(synthetic_dataset):
    train = tuple(synthetic_dataset.gdp['quarter'].iloc[:16])
    target = synthetic_dataset.gdp['quarter'].iloc[16]
    spec = DFMSpec(name='dfm_syn', fields=tuple(synthetic_dataset.monthly.columns),
                   n_factors=1)
    pred, diag = dfm_forecast(synthetic_dataset, spec, train, target,
                               horizon='H3', mode='standard')
    if np.isnan(pred):
        assert 'failure' in diag
    else:
        assert 'n_train' in diag
        assert 'loadings' in diag


def test_dfm_does_not_rely_on_future_gdp(synthetic_dataset):
    # Poison future GDP; the model should still produce the same forecast
    dataset = synthetic_dataset
    train = tuple(dataset.gdp['quarter'].iloc[:16])
    target = dataset.gdp['quarter'].iloc[16]
    spec = DFMSpec(name='dfm_syn', fields=tuple(dataset.monthly.columns),
                   n_factors=1)
    pred1, _ = dfm_forecast(dataset, spec, train, target, horizon='H3', mode='standard')
    dataset.gdp.loc[17:, 'gdp_real_yoy_pct'] = -999.0
    pred2, _ = dfm_forecast(dataset, spec, train, target, horizon='H3', mode='standard')
    assert (np.isnan(pred1) and np.isnan(pred2)) or pred1 == pytest.approx(pred2)
