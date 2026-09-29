"""Baseline GDP benchmarks: expanding historical mean and AR(p)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def historical_mean_forecast(gdp_train: pd.Series) -> tuple[float, dict]:
    """Expanding-window mean of the training-sample GDP series.

    Returns the point forecast and a small diagnostics dict.
    """
    if gdp_train.empty:
        raise ValueError('historical mean requires at least one training observation')
    value = float(gdp_train.mean())
    return value, dict(n_train=int(gdp_train.notna().sum()))


@dataclass(frozen=True)
class ARFit:
    """OLS fit of ``y_t = c + β1 y_{t-1} + ... + βp y_{t-p} + ε``."""

    p: int
    coef: np.ndarray  # intercept + p AR coefficients
    n_train: int
    residual_variance: float

    def forecast(self, history: np.ndarray) -> float:
        if history.size < self.p:
            raise ValueError('AR forecast needs p lagged observations')
        lags = history[-self.p:][::-1]
        return float(self.coef[0] + np.dot(self.coef[1:], lags))


def fit_ar(gdp_train: pd.Series, p: int) -> ARFit:
    """Fit an AR(p) via OLS on the strictly-in-sample training slice."""
    if p < 1:
        raise ValueError('AR order must be at least 1')
    values = gdp_train.dropna().to_numpy(dtype=float)
    if values.size <= p:
        raise ValueError(f'AR({p}) needs more than {p} training observations; got {values.size}')
    Y = values[p:]
    X_cols = [np.ones_like(Y)]
    for lag in range(1, p + 1):
        X_cols.append(values[p - lag: -lag])
    X = np.column_stack(X_cols)
    coef, *_ = np.linalg.lstsq(X, Y, rcond=None)
    residuals = Y - X @ coef
    variance = float((residuals ** 2).sum() / max(len(Y) - X.shape[1], 1))
    return ARFit(p=p, coef=coef, n_train=len(Y), residual_variance=variance)


def ar_forecast(gdp_train: pd.Series, p: int) -> tuple[float, dict]:
    """Fit AR(p) on training data and produce the next-period point forecast."""
    fit = fit_ar(gdp_train, p)
    prediction = fit.forecast(gdp_train.dropna().to_numpy(dtype=float))
    return prediction, dict(
        n_train=fit.n_train, p=fit.p,
        intercept=float(fit.coef[0]),
        ar_coefficients=[float(c) for c in fit.coef[1:]],
        residual_variance=fit.residual_variance,
    )
