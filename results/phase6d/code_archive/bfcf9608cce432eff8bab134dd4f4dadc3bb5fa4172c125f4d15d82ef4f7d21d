"""Parsimonious MIDAS specifications.

Given only 34 GDP quarters, the framework deliberately keeps MIDAS very
small. Two shapes are offered:

* ``UMIDAS(p_m)`` — unrestricted single-predictor MIDAS with the last
  ``p_m`` monthly observations available at the nowcast origin as
  separate right-hand-side regressors, plus one GDP lag.
* ``AlmonMIDAS(p_m, poly_order)`` — the same monthly slice but the
  coefficients are constrained to lie on a low-order polynomial in the
  lag index, cutting the number of free parameters to
  ``poly_order + 1`` per predictor.

Both fit via OLS. Neither uses future information: the monthly slice is
built with the same ``build_information_set`` machinery as the bridge
models, so release lags are respected.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from uznowcast.models.data import (
    ModelingDataset, build_information_set, quarter_start,
)


@dataclass(frozen=True)
class MidasSpec:
    """One MIDAS specification."""

    name: str
    field: str
    monthly_lags: int
    with_gdp_lag: bool = True
    polynomial_order: int | None = None  # None → unrestricted U-MIDAS

    def parameter_count(self) -> int:
        if self.polynomial_order is None:
            monthly_params = self.monthly_lags
        else:
            monthly_params = self.polynomial_order + 1
        return 1 + int(self.with_gdp_lag) + monthly_params


def _monthly_lag_vector(dataset: ModelingDataset, spec: MidasSpec, quarter: str,
                        horizon: str, mode: str) -> np.ndarray:
    """Return the last ``spec.monthly_lags`` observed monthly values.

    Uses the horizon-appropriate information set. Older-to-newer order.
    ``NaN`` propagates: if the required window is not fully observed the
    result contains ``NaN``s and the quarter is later dropped from the
    training frame.
    """
    info = build_information_set(dataset, quarter, horizon, [spec.field], mode=mode)
    series = info[spec.field].dropna()
    if len(series) < spec.monthly_lags:
        return np.full(spec.monthly_lags, np.nan)
    return series.tail(spec.monthly_lags).to_numpy(dtype=float)


def _almon_basis(monthly_lags: int, order: int) -> np.ndarray:
    """Normalized Almon polynomial basis, oldest lag first."""
    lags = np.arange(monthly_lags, dtype=float) / max(monthly_lags - 1, 1)
    basis = np.column_stack([lags ** k for k in range(order + 1)])
    return basis


def _training_matrix(dataset: ModelingDataset, spec: MidasSpec,
                     train_quarters: Sequence[str], horizon: str, mode: str
                     ) -> tuple[np.ndarray, np.ndarray, list[str]]:
    gdp = dataset.gdp.set_index('quarter')[dataset.target_field]
    rows_x, rows_y, columns = [], [], []
    for i, quarter in enumerate(train_quarters):
        monthly_lags = _monthly_lag_vector(dataset, spec, quarter, horizon, mode)
        target = float(gdp.get(quarter, np.nan))
        gdp_lag = float(gdp.get(train_quarters[i - 1], np.nan)) if i > 0 else np.nan
        if any(np.isnan(monthly_lags)) or np.isnan(target):
            continue
        if spec.with_gdp_lag and np.isnan(gdp_lag):
            continue
        row = [1.0]
        column_names = ['intercept']
        if spec.with_gdp_lag:
            row.append(gdp_lag)
            column_names.append('gdp_lag1')
        row.extend(monthly_lags.tolist())
        column_names.extend([f'lag_{k}' for k in range(spec.monthly_lags)])
        rows_x.append(row)
        rows_y.append(target)
        columns = column_names
    if not rows_x:
        raise ValueError(f'MIDAS spec {spec.name} has no training rows')
    X = np.array(rows_x, dtype=float)
    Y = np.array(rows_y, dtype=float)
    return X, Y, columns


def fit_midas(dataset: ModelingDataset, spec: MidasSpec,
              train_quarters: Sequence[str], *, horizon: str, mode: str) -> dict:
    X, Y, columns = _training_matrix(dataset, spec, train_quarters, horizon, mode)
    if spec.polynomial_order is None:
        design = X
        column_names = columns
    else:
        basis = _almon_basis(spec.monthly_lags, spec.polynomial_order)
        base_columns = [c for c in columns if not c.startswith('lag_')]
        base_matrix = X[:, [columns.index(c) for c in base_columns]]
        lag_matrix = X[:, [columns.index(c) for c in columns if c.startswith('lag_')]]
        constrained = lag_matrix @ basis
        design = np.column_stack([base_matrix, constrained])
        column_names = base_columns + [f'almon_{k}' for k in range(spec.polynomial_order + 1)]
    coef, *_ = np.linalg.lstsq(design, Y, rcond=None)
    residuals = Y - design @ coef
    return dict(n_train=int(len(Y)), coefficients=[float(c) for c in coef],
                column_order=column_names,
                residual_variance=float((residuals ** 2).sum()
                                        / max(len(Y) - design.shape[1], 1)),
                spec=dict(name=spec.name, field=spec.field,
                          monthly_lags=spec.monthly_lags,
                          with_gdp_lag=spec.with_gdp_lag,
                          polynomial_order=spec.polynomial_order))


def midas_forecast(dataset: ModelingDataset, spec: MidasSpec,
                   train_quarters: Sequence[str], target_quarter: str, *,
                   horizon: str, mode: str) -> tuple[float, dict]:
    try:
        diagnostics = fit_midas(dataset, spec, train_quarters,
                                horizon=horizon, mode=mode)
    except ValueError as exc:
        return float('nan'), dict(failure=str(exc), spec=dict(
            name=spec.name, field=spec.field,
            monthly_lags=spec.monthly_lags,
            with_gdp_lag=spec.with_gdp_lag,
            polynomial_order=spec.polynomial_order))
    coef = np.array(diagnostics['coefficients'])
    columns = diagnostics['column_order']
    gdp = dataset.gdp.set_index('quarter')[dataset.target_field]
    monthly_lags = _monthly_lag_vector(dataset, spec, target_quarter, horizon, mode)
    if any(np.isnan(monthly_lags)):
        return float('nan'), dict(diagnostics, failure='missing_monthly_lags_at_target')
    x = [1.0]
    if spec.with_gdp_lag:
        gdp_lag = float(gdp.get(train_quarters[-1], np.nan)) if train_quarters else np.nan
        if np.isnan(gdp_lag):
            return float('nan'), dict(diagnostics, failure='missing_gdp_lag_at_target')
        x.append(gdp_lag)
    if spec.polynomial_order is None:
        x.extend(monthly_lags.tolist())
    else:
        basis = _almon_basis(spec.monthly_lags, spec.polynomial_order)
        x.extend((monthly_lags @ basis).tolist())
    if len(x) != len(columns):
        raise ValueError('MIDAS design vector shape mismatch')
    return float(coef @ np.array(x, dtype=float)), diagnostics


def default_midas_specs(available_fields: Iterable[str]) -> list[MidasSpec]:
    """The small Phase 4A MIDAS zoo — one predictor at a time, 3 lags."""
    have = set(available_fields)
    candidates = [
        'ind_prod_yoy_log', 'construction_yoy_log', 'retail_trade_yoy_log',
        'cpi_headline_mom_log', 'ppi_mom_log', 'exports_total_yoy_log',
        'imports_total_yoy_log', 'usd_uzs_mom_dlog', 'm2_yoy_log',
    ]
    specs: list[MidasSpec] = []
    for field in candidates:
        if field not in have:
            continue
        specs.append(MidasSpec(name=f'umidas_{field}', field=field,
                               monthly_lags=3, polynomial_order=None))
        specs.append(MidasSpec(name=f'almon_{field}', field=field,
                               monthly_lags=3, polynomial_order=1))
    return specs
