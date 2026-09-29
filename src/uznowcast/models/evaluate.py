"""Expanding-window Phase 4A evaluator.

Runs benchmarks, bridge equations, MIDAS specifications and the DFM under
one or more release-lag assumptions, over three quarterly horizons, and
writes reproducible ``predictions``, ``metrics``, ``model_specs``,
``evaluation_windows`` and ``factor_loadings`` files under ``results/``.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path
from typing import Callable, Iterable, Sequence
import json
import time

import numpy as np
import pandas as pd

from uznowcast.provenance import atomic_parquet, save_json
from uznowcast.models import MODEL_LAYER_VERSION
from uznowcast.models.data import (
    ModelingDataset, load_dataset, tier_variables,
    usable_target_quarters, gdp_available_at,
)
from uznowcast.models.splits import Split, expanding_window, evaluation_span
from uznowcast.models.benchmarks import historical_mean_forecast, ar_forecast
from uznowcast.models.bridge import BridgeSpec, bridge_forecast, default_specs as default_bridge_specs
from uznowcast.models.midas import MidasSpec, midas_forecast, default_midas_specs
from uznowcast.models.dfm import DFMSpec, dfm_forecast, default_dfm_specs
from uznowcast.models.metrics import (
    summarize, compare_to_benchmark, diebold_mariano,
)


HORIZONS: tuple[str, ...] = ('H1', 'H2', 'H3')
MIN_TRAIN_GDP = 8      # smallest expanding-window training sample
LAG_MODES: tuple[str, ...] = ('standard', 'conservative')


def _fields_for_tier(dataset: ModelingDataset, tier: str) -> list[str]:
    return dataset.predictor_fields(tier)


def _model_targets(dataset: ModelingDataset) -> list[str]:
    return usable_target_quarters(dataset)


def _predictions_row(**kwargs) -> dict:
    return kwargs


def _record_benchmark(dataset: ModelingDataset, splits: list[Split],
                      records: list[dict], spec_registry: dict,
                      horizon: str, mode: str) -> None:
    gdp = dataset.gdp.set_index('quarter')[dataset.target_field]
    for split in splits:
        train_series = gdp.reindex(split.train)
        actual = float(gdp.get(split.target, np.nan))
        try:
            mean_pred, mean_diag = historical_mean_forecast(train_series.dropna())
        except ValueError as exc:
            mean_pred, mean_diag = float('nan'), dict(failure=str(exc))
        records.append(_predictions_row(
            model='historical_mean', tier='none', horizon=horizon, lag_mode=mode,
            target_quarter=split.target, n_train=len(train_series),
            prediction=mean_pred, actual=actual,
            error=(actual - mean_pred) if not np.isnan(mean_pred) else float('nan')))
        for p, name in ((1, 'ar1'), (2, 'ar2')):
            if len(train_series.dropna()) <= p + 1:
                records.append(_predictions_row(
                    model=name, tier='none', horizon=horizon, lag_mode=mode,
                    target_quarter=split.target, n_train=len(train_series),
                    prediction=float('nan'), actual=actual, error=float('nan'),
                    failure='insufficient_training_sample'))
                continue
            try:
                pred, diag = ar_forecast(train_series.dropna(), p)
            except ValueError as exc:
                pred, diag = float('nan'), dict(failure=str(exc))
            records.append(_predictions_row(
                model=name, tier='none', horizon=horizon, lag_mode=mode,
                target_quarter=split.target, n_train=len(train_series),
                prediction=pred, actual=actual,
                error=(actual - pred) if not np.isnan(pred) else float('nan')))
    spec_registry.setdefault('historical_mean', dict(kind='benchmark', description='expanding mean of GDP'))
    spec_registry.setdefault('ar1', dict(kind='benchmark', description='OLS AR(1) on GDP'))
    spec_registry.setdefault('ar2', dict(kind='benchmark', description='OLS AR(2) on GDP'))


def _record_bridge(dataset: ModelingDataset, splits: list[Split],
                   records: list[dict], spec_registry: dict,
                   horizon: str, mode: str, tier: str,
                   available_fields: list[str]) -> None:
    specs = default_bridge_specs(available_fields)
    gdp = dataset.gdp.set_index('quarter')[dataset.target_field]
    for spec in specs:
        for split in splits:
            actual = float(gdp.get(split.target, np.nan))
            try:
                pred, diag = bridge_forecast(dataset, spec, split.train, split.target,
                                             horizon=horizon, mode=mode)
            except ValueError as exc:
                pred, diag = float('nan'), dict(failure=str(exc))
            records.append(_predictions_row(
                model=spec.name, tier=tier, horizon=horizon, lag_mode=mode,
                target_quarter=split.target, n_train=diag.get('n_train'),
                prediction=pred, actual=actual,
                error=(actual - pred) if not np.isnan(pred) else float('nan'),
                failure=diag.get('failure')))
        spec_registry.setdefault(spec.name, dict(kind='bridge', spec=dict(
            fields=list(spec.fields), with_gdp_lag=spec.with_gdp_lag)))


def _record_midas(dataset: ModelingDataset, splits: list[Split],
                  records: list[dict], spec_registry: dict,
                  horizon: str, mode: str, tier: str,
                  available_fields: list[str]) -> None:
    specs = default_midas_specs(available_fields)
    gdp = dataset.gdp.set_index('quarter')[dataset.target_field]
    for spec in specs:
        for split in splits:
            actual = float(gdp.get(split.target, np.nan))
            pred, diag = midas_forecast(dataset, spec, split.train, split.target,
                                         horizon=horizon, mode=mode)
            records.append(_predictions_row(
                model=spec.name, tier=tier, horizon=horizon, lag_mode=mode,
                target_quarter=split.target, n_train=diag.get('n_train'),
                prediction=pred, actual=actual,
                error=(actual - pred) if not np.isnan(pred) else float('nan'),
                failure=diag.get('failure')))
        spec_registry.setdefault(spec.name, dict(kind='midas', spec=dict(
            field=spec.field, monthly_lags=spec.monthly_lags,
            polynomial_order=spec.polynomial_order,
            with_gdp_lag=spec.with_gdp_lag)))


def _record_dfm(dataset: ModelingDataset, splits: list[Split],
                records: list[dict], spec_registry: dict,
                horizon: str, mode: str, tier: str,
                available_fields: list[str],
                loadings_out: list[dict]) -> None:
    specs = default_dfm_specs(available_fields)
    gdp = dataset.gdp.set_index('quarter')[dataset.target_field]
    for spec in specs:
        for split in splits:
            actual = float(gdp.get(split.target, np.nan))
            pred, diag = dfm_forecast(dataset, spec, split.train, split.target,
                                       horizon=horizon, mode=mode)
            records.append(_predictions_row(
                model=spec.name, tier=tier, horizon=horizon, lag_mode=mode,
                target_quarter=split.target, n_train=diag.get('n_train'),
                prediction=pred, actual=actual,
                error=(actual - pred) if not np.isnan(pred) else float('nan'),
                failure=diag.get('failure')))
            if 'loadings' in diag:
                for field, values in diag['loadings'].items():
                    loadings_out.append(dict(
                        model=spec.name, tier=tier, horizon=horizon, lag_mode=mode,
                        target_quarter=split.target, variable_key=dataset.monthly_key_by_field.get(field, field),
                        clean_field=field, loading=values,
                        em_iterations=diag.get('em_diagnostics', {}).get('em_iterations'),
                        fraction_missing=diag.get('em_diagnostics', {}).get('fraction_missing')))
        spec_registry.setdefault(spec.name, dict(kind='dfm', spec=dict(
            fields=list(spec.fields), n_factors=spec.n_factors,
            with_gdp_lag=spec.with_gdp_lag)))


def evaluate(dataset: ModelingDataset, *, horizons: Sequence[str] = HORIZONS,
             lag_modes: Sequence[str] = LAG_MODES, min_train: int = MIN_TRAIN_GDP,
             tiers: Sequence[str] = ('A', 'B', 'C')) -> dict:
    """Run the full Phase 4A evaluation and return in-memory tables."""
    quarters = _model_targets(dataset)
    all_splits = expanding_window(quarters, min_train=min_train)
    predictions: list[dict] = []
    spec_registry: dict = {}
    loadings: list[dict] = []
    windows: list[dict] = []

    for split in all_splits:
        windows.append(dict(target_quarter=split.target, n_train=len(split.train),
                            first_train_quarter=split.train[0],
                            last_train_quarter=split.train[-1]))

    for horizon in horizons:
        for mode in lag_modes:
            _record_benchmark(dataset, all_splits, predictions, spec_registry, horizon, mode)
            for tier in tiers:
                available = _fields_for_tier(dataset, tier)
                if not available:
                    continue
                _record_bridge(dataset, all_splits, predictions, spec_registry,
                               horizon, mode, tier, available)
                _record_midas(dataset, all_splits, predictions, spec_registry,
                              horizon, mode, tier, available)
                _record_dfm(dataset, all_splits, predictions, spec_registry,
                            horizon, mode, tier, available, loadings)
    return dict(predictions=predictions, spec_registry=spec_registry,
                loadings=loadings, windows=windows,
                first_evaluation_quarter=quarters[min_train] if len(quarters) > min_train else None,
                last_evaluation_quarter=quarters[-1] if quarters else None,
                min_train=min_train)


def summarize_predictions(predictions: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(predictions)
    if frame.empty:
        return frame
    grouped = frame.groupby(['model', 'tier', 'horizon', 'lag_mode'], dropna=False)
    rows = []
    for keys, group in grouped:
        errors = group['error'].tolist()
        info = summarize(errors)
        rows.append(dict(zip(('model', 'tier', 'horizon', 'lag_mode'), keys), **info,
                         first_eval_quarter=group['target_quarter'].min(),
                         last_eval_quarter=group['target_quarter'].max()))
    result = pd.DataFrame(rows)
    for horizon in result['horizon'].unique():
        for mode in result['lag_mode'].unique():
            benchmark = result[(result['model'] == 'ar1') & (result['horizon'] == horizon)
                               & (result['lag_mode'] == mode)]
            if benchmark.empty:
                continue
            bench_rmse = float(benchmark['rmse'].iloc[0])
            bench_mae = float(benchmark['mae'].iloc[0])
            mask = (result['horizon'] == horizon) & (result['lag_mode'] == mode)
            result.loc[mask, 'rmse_relative_to_ar1'] = result.loc[mask, 'rmse'] / bench_rmse
            result.loc[mask, 'mae_relative_to_ar1'] = result.loc[mask, 'mae'] / bench_mae
    return result


def write_results(root: Path, results: dict) -> dict:
    root = Path(root).resolve()
    (root / 'results').mkdir(exist_ok=True)
    predictions = pd.DataFrame(results['predictions'])
    metrics = summarize_predictions(results['predictions'])
    loadings = pd.DataFrame(results['loadings'])
    windows = pd.DataFrame(results['windows'])

    atomic_parquet(predictions, root / 'results/phase4a_predictions.parquet')
    atomic_parquet(metrics, root / 'results/phase4a_metrics.parquet')
    if not loadings.empty:
        atomic_parquet(loadings, root / 'results/phase4a_factor_loadings.parquet')
    else:
        loadings.to_parquet(root / 'results/phase4a_factor_loadings.parquet', index=False)
    atomic_parquet(windows, root / 'results/phase4a_evaluation_windows.parquet')
    save_json(root / 'results/phase4a_model_specs.json',
              dict(model_layer_version=MODEL_LAYER_VERSION,
                   min_train=results['min_train'],
                   first_evaluation_quarter=results['first_evaluation_quarter'],
                   last_evaluation_quarter=results['last_evaluation_quarter'],
                   specs=results['spec_registry']))
    return dict(predictions_rows=len(predictions), metrics_rows=len(metrics),
                loadings_rows=len(loadings), windows_rows=len(windows))
