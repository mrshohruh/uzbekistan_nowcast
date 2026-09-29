"""Forecast-error metrics for Phase 4A comparisons."""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd


def _clean(errors: Sequence[float]) -> np.ndarray:
    array = np.asarray(errors, dtype=float)
    return array[~np.isnan(array)]


def rmse(errors: Sequence[float]) -> float:
    values = _clean(errors)
    if values.size == 0:
        return float('nan')
    return float(math.sqrt((values ** 2).mean()))


def mae(errors: Sequence[float]) -> float:
    values = _clean(errors)
    if values.size == 0:
        return float('nan')
    return float(np.abs(values).mean())


def bias(errors: Sequence[float]) -> float:
    values = _clean(errors)
    if values.size == 0:
        return float('nan')
    return float(values.mean())


def n_forecasts(errors: Sequence[float]) -> int:
    return int(_clean(errors).size)


def relative(metric: float, benchmark: float) -> float:
    if not benchmark or math.isnan(benchmark) or math.isnan(metric):
        return float('nan')
    return float(metric / benchmark)


def summarize(errors: Sequence[float]) -> dict:
    return dict(rmse=rmse(errors), mae=mae(errors), bias=bias(errors),
                n_forecasts=n_forecasts(errors))


def compare_to_benchmark(model_metrics: dict, benchmark_metrics: dict) -> dict:
    return dict(model_metrics,
                rmse_relative=relative(model_metrics['rmse'], benchmark_metrics['rmse']),
                mae_relative=relative(model_metrics['mae'], benchmark_metrics['mae']))


def diebold_mariano(model_errors: Sequence[float], benchmark_errors: Sequence[float],
                    *, loss: str = 'squared') -> dict:
    """Small-sample Diebold-Mariano t-statistic (Newey-West variance with h=1).

    Returns diagnostics only. Phase 4A does not use DM to declare winners
    when the evaluation sample is small; the caller decides whether to
    report the p-value at all.
    """
    m = np.asarray(model_errors, dtype=float)
    b = np.asarray(benchmark_errors, dtype=float)
    mask = ~(np.isnan(m) | np.isnan(b))
    m, b = m[mask], b[mask]
    if m.size < 4:
        return dict(t_stat=float('nan'), n=int(m.size), note='sample too small')
    if loss == 'squared':
        d = m ** 2 - b ** 2
    elif loss == 'absolute':
        d = np.abs(m) - np.abs(b)
    else:
        raise ValueError(f'Unknown loss: {loss!r}')
    n = len(d)
    mean = d.mean()
    # Newey-West variance with lag 1 (adequate for one-step-ahead forecasts).
    gamma0 = ((d - mean) ** 2).sum() / n
    gamma1 = ((d[1:] - mean) * (d[:-1] - mean)).sum() / n
    variance = gamma0 + 2 * (1 - 1 / 2) * gamma1
    if variance <= 0:
        return dict(t_stat=float('nan'), n=int(n), note='non-positive DM variance')
    t_stat = mean / math.sqrt(variance / n)
    return dict(t_stat=float(t_stat), n=int(n), note='NW lag=1')
