"""M0 dynamic factor estimation and GDP bridge kernels."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.dynamic_factor_mq import DynamicFactorMQ
from uznowcast.models.data import (horizon_month_end, information_cutoff_for_variable,
                                    quarter_start, quarter_end)

HOLDOUT = ('2025Q3', '2025Q4', '2026Q1', '2026Q2')
KEYS = ['target_quarter', 'horizon', 'lag_mode', 'timing_rule']
FREEZE_DATE = pd.Timestamp('2025-07-30')


@dataclass(frozen=True)
class Spec:
    name: str
    fields: tuple[str, ...]
    factors: int = 1
    order: int = 1
    start: str = '2019-01-31'
    balanced: bool = False
    winsor: bool = False


def mask(panel, spec, target, horizon, lags, mode):
    origin = horizon_month_end(target, horizon)
    index = pd.date_range(spec.start, origin, freq='ME')
    frame = panel.reindex(index)[list(spec.fields)].copy()
    audit = []
    for field in spec.fields:
        if field not in lags:
            raise ValueError('undocumented_release_lag:' + field)
        cutoff = information_cutoff_for_variable(origin, field, lags, mode)
        frame.loc[frame.index > cutoff, field] = np.nan
        latest = frame[field].last_valid_index()
        audit.append(dict(target_quarter=target, horizon=horizon, lag_mode=mode,
                          timing_rule='STRICT', variable=field, origin=origin,
                          cutoff=cutoff, latest_usable_observation=latest,
                          lag_days=lags[field], availability_class='REGISTRY_LAG_PSEUDO_REAL_TIME',
                          observed_source_release_date=None))
        assert latest is None or latest <= cutoff <= origin
    return frame, audit


def standardize(frame, training_end, winsor=False):
    """No holdout, current-quarter or future statistics enter scaling."""
    train = frame.loc[:training_end]
    mean, scale = train.mean(), train.std(ddof=1)
    if train.count().lt(12).any() or not np.isfinite(scale).all() or scale.le(0).any():
        raise ValueError('insufficient_history_or_invalid_scale')
    adjusted = frame.copy()
    if winsor:
        # Explicit research sensitivity, not asserted to be a production rule.
        lower, upper = train.quantile(.01), train.quantile(.99)
        adjusted = adjusted.clip(lower=lower, upper=upper, axis=1)
    return (adjusted - mean) / scale, mean, scale


def training_panel(frame, training_end, balanced):
    if balanced:
        starts = [frame[c].first_valid_index() for c in frame]
        if any(s is None for s in starts):
            raise ValueError('unobserved_predictor')
        frame = frame.loc[max(starts):]
    training = frame.loc[:training_end]
    if len(training) < 36:
        raise ValueError('fewer_than_36_training_months')
    return frame, training


def estimate(training, z, spec, cache=None):
    """EM MLE with arbitrary missing cells; only filtered states feed bridges.

    Independent factor AR blocks identify the multi-factor dynamics. Missing
    initialization used internally by statsmodels is never written as observed
    data. The measurement likelihood uses only the observed cells.
    """
    digest = hashlib.sha256(pd.util.hash_pandas_object(training, index=True).values.tobytes()).hexdigest()
    key = (tuple(training.columns), spec.factors, spec.order, digest)
    cached = cache.get(key) if cache is not None else None
    if cached is None:
        model = DynamicFactorMQ(training, factors=spec.factors, factor_orders=spec.order,
                                idiosyncratic_ar1=False, standardize=False)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            fit = model.fit_em(maxiter=500, tolerance=1e-5, disp=False,
                               mstep_method='missing', llf_decrease_action='revert')
        history = np.asarray(fit.mle_retvals.get('llf', []))
        change = (abs(history[-1] - history[-2]) / max(1., abs(history[-2]))) if len(history) > 1 else np.inf
        diagnostics = dict(n_training_months=len(training), n_observed_cells=int(training.count().sum()),
                           n_missing_cells=int(training.isna().sum().sum()), iterations=int(fit.mle_retvals.get('iter', 0)),
                           relative_likelihood_change=float(change), converged=bool(change < 1e-5),
                           log_likelihood=float(fit.llf), n_states=model.k_states,
                           warnings=' | '.join(str(w.message) for w in caught),
                           estimator='DynamicFactorMQ_EM_MLE', factor_source='FILTERED_ONE_SIDED',
                           estimation_start=str(training.index.min().date()))
        cached = fit, diagnostics
        if cache is not None:
            cache[key] = cached
    fit, diagnostics = cached
    applied = fit.apply(z, refit=False, retain_standardization=False)
    factors = applied.factors.filtered.to_numpy(copy=True)
    params = dict(zip(fit.param_names, np.asarray(fit.params)))
    loadings = np.array([[params[f'loading.{j}->{field}'] for j in range(spec.factors)] for field in training.columns])
    # Deterministic within-fit sign. Cross-fit rotations are assessed separately.
    signs = np.array([1. if loadings[np.argmax(abs(loadings[:, j])), j] >= 0 else -1. for j in range(spec.factors)])
    factors *= signs
    loadings *= signs
    transition = np.asarray(applied.model.ssm['transition'])
    radius = float(max(abs(np.linalg.eigvals(transition))))
    diag = dict(diagnostics, spectral_radius=radius,
                transition=json.dumps(transition.tolist()), bic=float(fit.bic), aic=float(fit.aic))
    if not diag['converged'] or radius >= .9999 or not np.isfinite(factors).all():
        raise ValueError('nonconvergence_or_unstable_transition:' + json.dumps(diag))
    return pd.DataFrame(factors, index=z.index), loadings, diag


def quarterly(factors, aggregation='mean'):
    grouped = factors.groupby(factors.index.to_period('Q'))
    counts = grouped.size()
    result = grouped.mean() if aggregation == 'mean' else grouped.last()
    return result.loc[counts.eq(3)]


def bridge(factors, available, target, origin, kind='A', aggregation='mean'):
    """Released GDP only; missing target-quarter states are Kalman predictions."""
    assert available.origin == pd.Timestamp(origin)
    gdp = available.frame.value
    assert (gdp.index < target).all()
    assert pd.to_datetime(available.frame.publication_date).lt(pd.Timestamp(origin).normalize()).all()
    fq = quarterly(factors, aggregation)
    target_q = pd.Period(target, freq='Q')
    prior = str(target_q - 1)
    if kind in ('B', 'C') and prior not in gdp.index:
        raise ValueError('PRIOR_QUARTER_GDP_NOT_AVAILABLE')
    x, y, used = [], [], []
    for q in fq.index:
        if str(q) >= target or str(q) not in gdp.index:
            continue
        if kind in ('B', 'C') and str(q - 1) not in gdp.index:
            continue
        if kind == 'C' and q - 1 not in fq.index:
            continue
        row = [1., *fq.loc[q].tolist()]
        if kind == 'C':
            row.extend(fq.loc[q - 1].tolist())
        if kind in ('B', 'C'):
            row.append(float(gdp.loc[str(q - 1)]))
        x.append(row); y.append(float(gdp.loc[str(q)])); used.append(str(q))
    x = np.asarray(x)
    if len(y) < max(12, 3 * (x.shape[1] if x.ndim == 2 else 1)):
        raise ValueError('insufficient_GDP_training_quarters')
    if np.linalg.matrix_rank(x) != x.shape[1]:
        raise ValueError('rank_deficient_GDP_bridge')
    row = [1., *fq.loc[target_q].tolist()]
    if kind == 'C':
        row.extend(fq.loc[target_q - 1].tolist())
    if kind in ('B', 'C'):
        row.append(float(gdp.loc[prior]))
    coef = np.linalg.lstsq(x, y, rcond=None)[0]
    return float(np.asarray(row) @ coef), dict(n_GDP_quarters=len(y), training_quarters=json.dumps(used),
                                              condition=float(np.linalg.cond(x)))


