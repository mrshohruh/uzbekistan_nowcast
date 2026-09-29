"""Parsimonious bridge equations.

Each specification aggregates a small number of monthly predictors to
quarterly frequency using only information available at the nowcast
origin, then regresses quarterly GDP on the aggregate plus one autoregressive
lag. Variable selection (which candidate predictors to keep) is done inside
the training sample — the target quarter is never touched during selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from uznowcast.models.data import (
    ModelingDataset, build_information_set, quarter_start, quarter_end,
)


def quarter_month_ends(quarter: str) -> list[pd.Timestamp]:
    start = quarter_start(quarter)
    return [(start + pd.offsets.MonthBegin(offset)).normalize() + pd.offsets.MonthEnd(0)
            for offset in range(3)]


def aggregate_monthly_to_quarter(monthly: pd.DataFrame, quarter: str,
                                 *, method: str = 'mean_available') -> pd.Series:
    """Aggregate the observed months of ``quarter`` to a single quarterly row.

    ``mean_available`` averages the months that are visible at the
    information set (``NaN`` months are ignored). A quarter with **no**
    visible month for a variable returns ``NaN`` for that variable — the
    bridge model then drops the row from training.
    """
    if method != 'mean_available':
        raise ValueError(f'Unknown aggregation method: {method!r}')
    ends = quarter_month_ends(quarter)
    rows = monthly.loc[monthly.index.isin(ends)]
    if rows.empty:
        return pd.Series({column: np.nan for column in monthly.columns}, name=quarter)
    return rows.mean(axis=0, skipna=True).rename(quarter)


@dataclass(frozen=True)
class BridgeSpec:
    """Immutable description of one bridge specification."""

    name: str
    fields: tuple[str, ...]      # monthly clean fields to aggregate
    with_gdp_lag: bool = True

    def parameter_count(self) -> int:
        return int(self.with_gdp_lag) + len(self.fields) + 1


def bridge_training_frame(dataset: ModelingDataset, spec: BridgeSpec,
                          train_quarters: Sequence[str], *,
                          horizon: str, mode: str) -> pd.DataFrame:
    """Build the quarterly training frame with strictly training-only info."""
    rows = []
    fields = list(spec.fields)
    gdp = dataset.gdp.set_index('quarter')[dataset.target_field]
    for i, quarter in enumerate(train_quarters):
        info = build_information_set(dataset, quarter, horizon, fields, mode=mode)
        aggregated = aggregate_monthly_to_quarter(info, quarter)
        row = dict(aggregated)
        row['quarter'] = quarter
        row['target'] = gdp.get(quarter, np.nan)
        if spec.with_gdp_lag:
            prev_quarter = train_quarters[i - 1] if i > 0 else None
            row['gdp_lag1'] = float(gdp.get(prev_quarter, np.nan)) if prev_quarter else np.nan
        rows.append(row)
    frame = pd.DataFrame(rows)
    return frame


def _design_matrix(frame: pd.DataFrame, spec: BridgeSpec) -> tuple[np.ndarray, np.ndarray, list[str]]:
    columns = list(spec.fields)
    if spec.with_gdp_lag:
        columns = ['gdp_lag1'] + columns
    subset = frame.dropna(subset=columns + ['target'])
    if subset.empty:
        raise ValueError('bridge training frame is empty after dropping NaNs')
    Y = subset['target'].to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(subset))] + [subset[column].to_numpy(dtype=float)
                                                    for column in columns])
    return X, Y, columns


def fit_bridge(dataset: ModelingDataset, spec: BridgeSpec, train_quarters: Sequence[str],
               *, horizon: str, mode: str) -> tuple[dict, pd.DataFrame]:
    frame = bridge_training_frame(dataset, spec, train_quarters, horizon=horizon, mode=mode)
    X, Y, columns = _design_matrix(frame, spec)
    coef, *_ = np.linalg.lstsq(X, Y, rcond=None)
    residuals = Y - X @ coef
    diagnostics = dict(
        n_train=int(len(Y)), coefficients=[float(c) for c in coef],
        column_order=['intercept'] + columns,
        residual_variance=float((residuals ** 2).sum() / max(len(Y) - X.shape[1], 1)),
    )
    return diagnostics, frame


def bridge_forecast(dataset: ModelingDataset, spec: BridgeSpec,
                    train_quarters: Sequence[str], target_quarter: str, *,
                    horizon: str, mode: str) -> tuple[float, dict]:
    """Fit the bridge on training quarters and forecast ``target_quarter``."""
    diagnostics, _train = fit_bridge(dataset, spec, train_quarters,
                                     horizon=horizon, mode=mode)
    fields = list(spec.fields)
    info = build_information_set(dataset, target_quarter, horizon, fields, mode=mode)
    aggregate = aggregate_monthly_to_quarter(info, target_quarter)
    columns = diagnostics['column_order']  # includes intercept
    coef = np.array(diagnostics['coefficients'])
    gdp_series = dataset.gdp.set_index('quarter')[dataset.target_field]
    x = [1.0]
    for column in columns[1:]:
        if column == 'gdp_lag1':
            prev_q = train_quarters[-1] if train_quarters else None
            x.append(float(gdp_series.get(prev_q, np.nan)) if prev_q else np.nan)
        else:
            x.append(float(aggregate.get(column, np.nan)))
    if any(np.isnan(val) for val in x):
        return float('nan'), dict(diagnostics, failure='missing_input_at_target')
    return float(coef @ np.array(x)), diagnostics


ECONOMIC_BLOCKS = {
    'activity': ('ind_prod_yoy_log', 'manufacturing_yoy_log', 'mining_yoy_log',
                 'electricity_gas_yoy_log', 'construction_yoy_log',
                 'retail_trade_yoy_log', 'wholesale_trade_yoy_log'),
    'prices': ('cpi_headline_mom_log', 'cpi_food_mom_log', 'cpi_services_mom_log',
               'ppi_mom_log'),
    'external': ('exports_total_yoy_log', 'exports_non_gold_yoy_log',
                 'imports_total_yoy_log', 'gold_exports_proxy_usd_m',
                 'usd_uzs_mom_dlog', 'rub_uzs_mom_dlog', 'gold_price_yoy_log'),
    'monetary': ('m2_yoy_log', 'fx_reserves_exgold_yoy_log'),
}


def default_specs(available_fields: Iterable[str]) -> list[BridgeSpec]:
    """Return the parsimonious bridge specifications Phase 4A evaluates.

    Only fields that actually appear in the monthly master are included.
    Every specification carries the GDP lag; the "single-predictor"
    specifications add exactly one aggregate at a time.
    """
    have = set(available_fields)
    specs: list[BridgeSpec] = []
    for block, fields in ECONOMIC_BLOCKS.items():
        for field in fields:
            if field in have:
                specs.append(BridgeSpec(name=f'bridge_{field}', fields=(field,)))
        block_fields = tuple(field for field in fields if field in have)
        if len(block_fields) >= 2:
            specs.append(BridgeSpec(name=f'bridge_block_{block}', fields=block_fields[:3]))
    return specs
