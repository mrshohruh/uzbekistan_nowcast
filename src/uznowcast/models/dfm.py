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
    em_iterations: int = 100
    em_tolerance: float = 1e-4
    min_observed_months: int = 12


def _em_pca(matrix: np.ndarray, n_factors: int, *, max_iter: int, tol: float
            ) -> tuple[np.ndarray, np.ndarray, dict]:
    """Iterative EM PCA over missing values.

    ``matrix`` shape ``(T, N)`` with ``NaN`` for missing cells. Returns
    ``(factor_time_series, loadings, diagnostics)``.
    """
    if matrix.size == 0:
        raise ValueError('EM PCA received an empty matrix')
    if max_iter < 1:
        raise ValueError('EM PCA max_iter must be positive')
    if tol <= 0:
        raise ValueError('EM PCA tolerance must be positive')
    if n_factors < 1:
        raise ValueError('EM PCA n_factors must be positive')
    mask = np.isnan(matrix)
    observed = ~mask
    if not observed.any():
        raise ValueError('EM PCA received a fully missing matrix')
    working = matrix.copy()
    column_means = np.nanmean(matrix, axis=0)
    column_means = np.where(np.isnan(column_means), 0.0, column_means)
    for column in range(matrix.shape[1]):
        working[mask[:, column], column] = column_means[column]
    prev_loss: float | None = None
    iterations = 0
    converged = False
    relative_change = float('nan')
    loss_path: list[float] = []
    for iterations in range(1, max_iter + 1):
        U, S, Vt = np.linalg.svd(working, full_matrices=False)
        k = min(n_factors, len(S))
        loadings = Vt[:k].T                    # (N, k)
        factors = U[:, :k] * S[:k]             # (T, k)
        reconstruction = factors @ loadings.T
        # Compare reconstruction only against genuinely observed cells.
        # Imputed cells are latent state, not ground truth.
        loss = float(np.mean((matrix[observed] - reconstruction[observed]) ** 2))
        loss_path.append(loss)
        working[mask] = reconstruction[mask]
        if prev_loss is not None:
            relative_change = float(abs(prev_loss - loss) /
                                    max(abs(prev_loss), np.finfo(float).eps))
        if prev_loss is not None and relative_change <= tol:
            converged = True
            break
        prev_loss = loss
    return factors, loadings, dict(
        converged=converged,
        iteration_count=iterations,
        em_iterations=iterations,  # backward-compatible diagnostic label
        max_iterations=max_iter,
        tolerance=float(tol),
        reconstruction_loss_path=loss_path,
        final_loss=float(loss_path[-1]),
        reconstruction_loss=float(loss_path[-1]),
        relative_loss_change=relative_change,
        fraction_missing=float(mask.mean()),
    )


def _resolve_factor_fields(
        training: pd.DataFrame,
        requested_fields: Sequence[str],
        *,
        min_observed_months: int,
        field_to_key: dict[str, str] | None = None,
        unavailable_fields: Sequence[str] = (),
        ) -> tuple[pd.DataFrame, list[dict]]:
    """Resolve every configured field before factor estimation.

    The returned report contains one row per configured field, including
    fields absent from the master.  A field must have at least
    ``min_observed_months`` in-window observations and non-zero variance.
    Nothing is silently removed.
    """
    field_to_key = field_to_key or {}
    unavailable = set(unavailable_fields)
    rows: list[dict] = []
    included: list[str] = []
    n_months = int(len(training))
    for field in requested_fields:
        base = dict(
            variable_key=field_to_key.get(field, field),
            clean_field=field,
            total_months=n_months,
        )
        if field in unavailable or field not in training.columns:
            rows.append(dict(
                **base, status='unavailable', reason='field_not_in_monthly_master',
                observed_months=0, missing_months=n_months,
                coverage_fraction=0.0, unique_values=0,
            ))
            continue
        series = training[field]
        observed = int(series.notna().sum())
        unique = int(series.nunique(dropna=True))
        coverage = float(observed / n_months) if n_months else 0.0
        detail = dict(
            **base, observed_months=observed,
            missing_months=n_months - observed,
            coverage_fraction=coverage, unique_values=unique,
        )
        if observed < int(min_observed_months):
            rows.append(dict(
                **detail, status='excluded',
                reason='insufficient_in_window_coverage',
            ))
            continue
        if unique < 2 or float(series.std(skipna=True)) == 0.0:
            rows.append(dict(
                **detail, status='excluded', reason='zero_variance',
            ))
            continue
        included.append(field)
        rows.append(dict(**detail, status='included', reason='included'))
    return training[included].copy(), rows


def _panel_diagnostics(panel: pd.DataFrame) -> dict:
    observed = int(panel.notna().sum().sum())
    total = int(panel.shape[0] * panel.shape[1])
    missing = total - observed
    return dict(
        first_month=(str(panel.index.min().date()) if len(panel) else None),
        last_month=(str(panel.index.max().date()) if len(panel) else None),
        n_months=int(panel.shape[0]),
        n_variables=int(panel.shape[1]),
        total_cells=total,
        observed_cells=observed,
        missing_cells=missing,
        fraction_missing=(float(missing / total) if total else float('nan')),
    )


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
    requested_fields = list(spec.fields)
    fields = [field for field in requested_fields if field in dataset.monthly.columns]
    unavailable_fields = [field for field in requested_fields
                          if field not in dataset.monthly.columns]
    # Information set at the *target-quarter* horizon covers every quarter
    # up to and including the target. Training-window observations are
    # then extracted from that panel; the target-quarter cells are used
    # only for the target quarter's forecast, not for standardization or
    # EM initialization.
    if not fields:
        resolutions = [dict(
            variable_key=dataset.monthly_key_by_field.get(field, field),
            clean_field=field, total_months=0, observed_months=0,
            missing_months=0, coverage_fraction=0.0, unique_values=0,
            status='unavailable', reason='field_not_in_monthly_master',
        ) for field in requested_fields]
        return float('nan'), dict(
            failure='no_configured_fields_available',
            field_resolutions=resolutions,
            spec=dict(name=spec.name),
        )
    full_info = build_information_set(dataset, target_quarter, horizon, fields, mode=mode)
    train_slice = training_slice(full_info, train_quarters)
    if train_slice.empty:
        return float('nan'), dict(failure='training_slice_empty', spec=dict(name=spec.name))
    resolved_training, resolutions = _resolve_factor_fields(
        train_slice, requested_fields,
        min_observed_months=spec.min_observed_months,
        field_to_key=dataset.monthly_key_by_field,
        unavailable_fields=unavailable_fields,
    )
    panel = _panel_diagnostics(resolved_training)
    if resolved_training.shape[1] < max(spec.n_factors, 2):
        return float('nan'), dict(
            failure='insufficient_resolved_factor_fields',
            field_resolutions=resolutions,
            panel_diagnostics=panel,
            spec=dict(name=spec.name),
        )
    try:
        standardizer = Standardizer.fit(resolved_training)
    except ValueError as exc:
        return float('nan'), dict(
            failure=f'standardizer_error:{exc}', spec=dict(name=spec.name),
            field_resolutions=resolutions, panel_diagnostics=panel,
        )
    included_fields = list(resolved_training.columns)
    standardized_all = standardizer.transform(full_info[included_fields])
    standardized_training = standardizer.transform(resolved_training)
    factors, loadings, em = _em_pca(standardized_training.to_numpy(),
                                    n_factors=spec.n_factors,
                                    max_iter=spec.em_iterations,
                                    tol=spec.em_tolerance)
    loading_map = {field: loadings[i].tolist()
                   for i, field in enumerate(included_fields)}
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
        return float('nan'), dict(
            failure=f'gdp_regression:{exc}', spec=dict(name=spec.name),
            field_resolutions=resolutions, panel_diagnostics=panel,
            em_diagnostics=em, loadings=loading_map,
        )
    factor_row = quarterly_factor.loc[target_quarter] if target_quarter in quarterly_factor.index else None
    if factor_row is None or factor_row.isna().any():
        return float('nan'), dict(
            failure='missing_factor_at_target', spec=dict(name=spec.name),
            field_resolutions=resolutions, panel_diagnostics=panel,
            em_diagnostics=em, loadings=loading_map,
        )
    row = [1.0]
    if spec.with_gdp_lag:
        gdp_lag = float(gdp.get(train_quarters[-1], np.nan)) if train_quarters else np.nan
        if np.isnan(gdp_lag):
            return float('nan'), dict(
                failure='missing_gdp_lag_at_target', spec=dict(name=spec.name),
                field_resolutions=resolutions, panel_diagnostics=panel,
                em_diagnostics=em, loadings=loading_map,
            )
        row.append(gdp_lag)
    for k in range(spec.n_factors):
        row.append(float(factor_row[f'factor_{k + 1}']))
    prediction = float(coef @ np.array(row, dtype=float))
    return prediction, dict(
        n_train=n_train, coefficients=[float(c) for c in coef],
        column_order=columns, residual_variance=variance,
        em_diagnostics=em,
        panel_diagnostics=panel,
        field_resolutions=resolutions,
        loadings=loading_map,
        n_factors=spec.n_factors,
        spec=dict(name=spec.name, fields=requested_fields,
                  resolved_fields=included_fields,
                  n_factors=spec.n_factors,
                  with_gdp_lag=spec.with_gdp_lag,
                  em_iterations=spec.em_iterations,
                  em_tolerance=spec.em_tolerance,
                  min_observed_months=spec.min_observed_months))


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
                                'gold_price_mom_dlog', 'm2_yoy_log',
                                'fx_reserves_exgold_yoy_log'] if f in have)
    tier_b = tier_a + tuple(f for f in ['ind_prod_yoy_log', 'manufacturing_yoy_log',
                                         'mining_yoy_log', 'utilities_yoy_log',
                                         'retail_yoy_log', 'wholesale_yoy_log']
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
