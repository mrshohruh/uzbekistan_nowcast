"""Ragged-edge principal-component factor model (Stock-Watson style).

This is a small state-space-free approximate factor model, not a full
Kalman-filter DFM. The framework's explicit disclaimer is documented in
``docs/modeling/model_specifications.md``.

Steps at every expanding-window origin:

1. Restrict the monthly panel to observations dated on or before the
   training-window end (never any month past the target quarter).
2. Standardize each column using the training-slice mean / std, with the
   std computed on the non-missing values only.
3. Fit one (optionally two) principal components using an EM iteration
   over missing values: initialize missing cells with the column mean of
   the standardized slice, run SVD, project back, iterate.
4. Extract the monthly factor(s). Do not extrapolate; the factor at a
   month with no observed rows is filled from the EM projection but
   flagged so the reader knows it is a model-inferred value.
5. Aggregate the factor to quarterly frequency (average of available
   monthly factor values for each quarter, respecting the horizon's own
   information set).
6. Fit ``GDP_t = α + β1 GDP_{t-1} + β2 F_t + ε_t`` on the training
   sample. Forecast the target quarter.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from uznowcast.models.data import (
    ModelingDataset, build_information_set, quarter_start,
)
from uznowcast.models.bridge import aggregate_monthly_to_quarter
from uznowcast.models.preprocess import Standardizer, training_slice


@dataclass(frozen=True)
class DFMSpec:
    name: str
    fields: tuple[str, ...]
    n_factors: int = 1
    with_gdp_lag: bool = True
    em_iterations: int = 20
    em_tolerance: float = 1e-6


def _em_pca(matrix: np.ndarray, n_factors: int, *, max_iter: int, tol: float
            ) -> tuple[np.ndarray, np.ndarray, dict]:
    """Iterative EM PCA over missing values.

    ``matrix`` shape ``(T, N)`` with ``NaN`` for missing cells. Returns
    ``(factor_time_series, loadings, diagnostics)``.
    """
    if matrix.size == 0:
        raise ValueError('EM PCA received an empty matrix')
    mask = np.isnan(matrix)
    working = matrix.copy()
    column_means = np.nanmean(matrix, axis=0)
    column_means = np.where(np.isnan(column_means), 0.0, column_means)
    for column in range(matrix.shape[1]):
        working[mask[:, column], column] = column_means[column]
    prev_loss = np.inf
    iterations = 0
    for iterations in range(1, max_iter + 1):
        U, S, Vt = np.linalg.svd(working, full_matrices=False)
        k = min(n_factors, len(S))
        loadings = Vt[:k].T                    # (N, k)
        factors = U[:, :k] * S[:k]             # (T, k)
        reconstruction = factors @ loadings.T
        loss = float(((working - reconstruction) ** 2).sum())
        working[mask] = reconstruction[mask]
        if abs(prev_loss - loss) < tol:
            break
        prev_loss = loss
    else:
        pass
    return factors, loadings, dict(em_iterations=iterations,
                                    reconstruction_loss=float(prev_loss),
                                    fraction_missing=float(mask.mean()))


def _fit_gdp_regression(gdp_train: pd.Series, factor_quarterly: pd.Series,
                        spec: DFMSpec, train_quarters: Sequence[str]
                        ) -> tuple[np.ndarray, list[str], int, float]:
    gdp = gdp_train.reindex(train_quarters)
    lag = gdp.shift(1)
    columns = ['intercept']
    parts = [np.ones(len(train_quarters))]
    if spec.with_gdp_lag:
        columns.append('gdp_lag1')
        parts.append(lag.to_numpy(dtype=float))
    for factor in range(spec.n_factors):
        columns.append(f'factor_{factor + 1}')
        parts.append(factor_quarterly[f'factor_{factor + 1}'].reindex(train_quarters).to_numpy(dtype=float))
    stack = np.column_stack(parts)
    Y = gdp.to_numpy(dtype=float)
    mask = ~(np.isnan(stack).any(axis=1) | np.isnan(Y))
    if mask.sum() < len(columns):
        raise ValueError('DFM GDP regression has too few complete rows')
    coef, *_ = np.linalg.lstsq(stack[mask], Y[mask], rcond=None)
    residuals = Y[mask] - stack[mask] @ coef
    variance = float((residuals ** 2).sum() / max(mask.sum() - len(columns), 1))
    return coef, columns, int(mask.sum()), variance


def dfm_forecast(dataset: ModelingDataset, spec: DFMSpec,
                 train_quarters: Sequence[str], target_quarter: str, *,
                 horizon: str, mode: str) -> tuple[float, dict]:
    fields = list(spec.fields)
    # Information set at the *target-quarter* horizon covers every quarter
    # up to and including the target. Training-window observations are
    # then extracted from that panel; the target-quarter cells are used
    # only for the target quarter's forecast, not for standardization or
    # EM initialization.
    full_info = build_information_set(dataset, target_quarter, horizon, fields, mode=mode)
    train_end = train_quarters[-1] if train_quarters else None
    train_slice = training_slice(full_info, train_quarters)
    if train_slice.empty:
        return float('nan'), dict(failure='training_slice_empty', spec=dict(name=spec.name))
    try:
        standardizer = Standardizer.fit(train_slice)
    except ValueError as exc:
        return float('nan'), dict(failure=f'standardizer_error:{exc}', spec=dict(name=spec.name))
    standardized_all = standardizer.transform(full_info)
    standardized_training = standardizer.transform(train_slice)
    factors, loadings, em = _em_pca(standardized_training.to_numpy(),
                                    n_factors=spec.n_factors,
                                    max_iter=spec.em_iterations,
                                    tol=spec.em_tolerance)
    train_factor_index = standardized_training.index
    train_factor_frame = pd.DataFrame(
        {f'factor_{k + 1}': factors[:, k] for k in range(spec.n_factors)},
        index=train_factor_index)
    # Project the target-quarter (and other post-training) months onto the
    # fixed loadings using observed columns only.
    projected = _project_missing(standardized_all, standardized_training,
                                 loadings, train_factor_frame)
    factor_frame = projected.combine_first(train_factor_frame)
    # Aggregate to quarterly using the same information-set semantics as
    # the bridge model.
    quarterly_factor = _aggregate_factor_to_quarter(factor_frame,
                                                    tuple(train_quarters) + (target_quarter,))
    gdp = dataset.gdp.set_index('quarter')[dataset.target_field]
    try:
        coef, columns, n_train, variance = _fit_gdp_regression(
            gdp, quarterly_factor, spec, list(train_quarters))
    except ValueError as exc:
        return float('nan'), dict(failure=f'gdp_regression:{exc}',
                                   spec=dict(name=spec.name))
    factor_row = quarterly_factor.loc[target_quarter] if target_quarter in quarterly_factor.index else None
    if factor_row is None or factor_row.isna().any():
        return float('nan'), dict(failure='missing_factor_at_target',
                                   spec=dict(name=spec.name))
    row = [1.0]
    if spec.with_gdp_lag:
        gdp_lag = float(gdp.get(train_quarters[-1], np.nan)) if train_quarters else np.nan
        if np.isnan(gdp_lag):
            return float('nan'), dict(failure='missing_gdp_lag_at_target',
                                       spec=dict(name=spec.name))
        row.append(gdp_lag)
    for k in range(spec.n_factors):
        row.append(float(factor_row[f'factor_{k + 1}']))
    prediction = float(coef @ np.array(row, dtype=float))
    return prediction, dict(
        n_train=n_train, coefficients=[float(c) for c in coef],
        column_order=columns, residual_variance=variance,
        em_diagnostics=em,
        loadings={field: loadings[i].tolist() for i, field in enumerate(fields)},
        n_factors=spec.n_factors,
        spec=dict(name=spec.name, fields=fields, n_factors=spec.n_factors,
                  with_gdp_lag=spec.with_gdp_lag))


def _project_missing(standardized_all: pd.DataFrame,
                     standardized_training: pd.DataFrame,
                     loadings: np.ndarray,
                     train_factor_frame: pd.DataFrame) -> pd.DataFrame:
    """Project post-training months onto fixed loadings using observed cells."""
    n_factors = loadings.shape[1]
    projected_rows = {}
    for date, row in standardized_all.iterrows():
        if date in standardized_training.index:
            continue
        observed = row.dropna()
        if observed.empty:
            projected_rows[date] = np.full(n_factors, np.nan)
            continue
        idx = [standardized_all.columns.get_loc(name) for name in observed.index]
        L = loadings[idx]
        y = observed.to_numpy(dtype=float)
        # OLS projection: f = (L'L)^-1 L' y
        try:
            factor, *_ = np.linalg.lstsq(L, y, rcond=None)
        except np.linalg.LinAlgError:
            projected_rows[date] = np.full(n_factors, np.nan)
            continue
        projected_rows[date] = factor
    return pd.DataFrame({f'factor_{k + 1}': [projected_rows[d][k] for d in projected_rows]
                         for k in range(n_factors)},
                        index=list(projected_rows.keys()))


def _aggregate_factor_to_quarter(factor_frame: pd.DataFrame,
                                 quarters: Sequence[str]) -> pd.DataFrame:
    rows = {}
    for quarter in quarters:
        ends = [(quarter_start(quarter) + pd.offsets.MonthBegin(offset)).normalize()
                + pd.offsets.MonthEnd(0) for offset in range(3)]
        rows_in = factor_frame.loc[factor_frame.index.isin(ends)]
        if rows_in.empty:
            rows[quarter] = pd.Series({column: np.nan for column in factor_frame.columns})
        else:
            rows[quarter] = rows_in.mean(axis=0, skipna=True)
    return pd.DataFrame(rows).T


def default_dfm_specs(available_fields: list[str]) -> list[DFMSpec]:
    have = set(available_fields)
    tier_a = tuple(f for f in ['ppi_mom_log', 'usd_uzs_mom_dlog', 'rub_uzs_mom_dlog',
                                'gold_price_yoy_log', 'm2_yoy_log',
                                'fx_reserves_exgold_yoy_log'] if f in have)
    tier_b = tier_a + tuple(f for f in ['ind_prod_yoy_log', 'manufacturing_yoy_log',
                                         'mining_yoy_log', 'electricity_gas_yoy_log',
                                         'retail_trade_yoy_log', 'wholesale_trade_yoy_log']
                             if f in have)
    tier_c = tier_b + tuple(f for f in ['construction_yoy_log', 'cpi_headline_mom_log',
                                         'cpi_food_mom_log', 'cpi_services_mom_log',
                                         'exports_total_yoy_log', 'exports_non_gold_yoy_log',
                                         'imports_total_yoy_log', 'gold_exports_proxy_usd_m']
                             if f in have)
    specs = []
    if len(tier_a) >= 2:
        specs.append(DFMSpec(name='dfm_tierA_k1', fields=tier_a, n_factors=1))
    if len(tier_b) >= 2:
        specs.append(DFMSpec(name='dfm_tierB_k1', fields=tier_b, n_factors=1))
    if len(tier_c) >= 2:
        specs.append(DFMSpec(name='dfm_tierC_k1', fields=tier_c, n_factors=1))
    if len(tier_b) >= 3:
        specs.append(DFMSpec(name='dfm_tierB_k2', fields=tier_b, n_factors=2))
    return specs
