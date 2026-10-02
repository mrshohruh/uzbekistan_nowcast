"""Isolated calendar pseudo-real-time state-space DFM experiment."""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.dynamic_factor import DynamicFactor

from uznowcast.models.data import horizon_month_end, information_cutoff_for_variable

DOMESTIC = ('industrial_production', 'construction', 'retail_trade')
IMPORTS = 'imports_total_monthly_log_yoy'
SERVICES = 'services_output'
REGIME = 'expanded_coverage_2024_09_onward'
LABEL = 'CALENDAR_PSEUDO_REAL_TIME_RESEARCH'
KEYS = ['target_quarter', 'horizon', 'lag_mode']


@dataclass(frozen=True)
class Spec:
    name: str
    fields: tuple[str, ...]
    factors: int = 1
    adjust_services: bool = False


SPECS = (
    Spec('DFM_DOMESTIC_3', DOMESTIC),
    Spec('DFM_DOMESTIC_3_SERVICES', DOMESTIC + (SERVICES,), adjust_services=True),
    Spec('DFM_DOMESTIC_3_SERVICES_RAW_BREAK', DOMESTIC + (SERVICES,)),
    Spec('DFM_DOMESTIC_3_IMPORTS', DOMESTIC + (IMPORTS,)),
    Spec('DFM_TWO_FACTOR_IMPORTS', DOMESTIC + (IMPORTS,), factors=2),
)


def masked_panel(panel, fields, target, horizon, lags, mode='standard'):
    """Reuse Phase 5C calendar and release cutoff functions verbatim."""
    origin = horizon_month_end(target, horizon)
    frame = panel.loc[panel.index <= origin, list(fields)].copy()
    cutoffs = {}
    for field in fields:
        key = 'imports_total' if field == IMPORTS else field
        # Services is absent from V1.2: use the frozen cutoff function's
        # documented 30-day fallback, explicitly recorded, never a release date.
        cutoff = information_cutoff_for_variable(origin, key, lags, mode)
        frame.loc[frame.index > cutoff, field] = np.nan
        cutoffs[field] = str(cutoff.date())
    return frame, cutoffs


def prepare(frame, regimes, training_end, adjust_services=False):
    """Estimate level dummy and scaling solely before the target quarter."""
    adjusted = frame.copy()
    train_mask = frame.index <= training_end
    diagnostics = {'regime_adjustment': 0., 'regime_identified': False}
    if SERVICES in frame:
        post = regimes.reindex(frame.index).eq(REGIME)
        pre_values = frame.loc[train_mask & ~post, SERVICES].dropna()
        post_values = frame.loc[train_mask & post, SERVICES].dropna()
        effect = float(post_values.mean() - pre_values.mean()) if len(pre_values) and len(post_values) else 0.
        diagnostics.update(regime_adjustment=effect, regime_identified=bool(len(pre_values) and len(post_values)),
                           n_pre=len(pre_values), n_post=len(post_values), applied=adjust_services)
        if adjust_services:
            adjusted.loc[post, SERVICES] -= effect
    training = adjusted.loc[train_mask]
    means, stds = training.mean(), training.std(ddof=1)
    if not np.isfinite(stds).all() or (stds <= 0).any():
        raise ValueError('invalid_training_scale')
    return (adjusted - means) / stds, means, stds, diagnostics, adjusted


def pca(frame):
    if frame.isna().any().any():
        raise ValueError('PCA requires complete stored observations; no interpolation')
    z = (frame - frame.mean()) / frame.std(ddof=1)
    corr = z.corr()
    eigenvalues, vectors = np.linalg.eigh(corr.to_numpy())
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues, vectors = eigenvalues[order], vectors[:, order]
    if vectors[0, 0] < 0:
        vectors[:, 0] *= -1
    return corr, eigenvalues, 100 * eigenvalues / eigenvalues.sum(), vectors[:, 0]


def sign_normalize(loadings, factors):
    """Fix industrial-positive sign for each factor, without future data."""
    signs = np.where(loadings[0] < 0, -1., 1.)
    return loadings * signs, factors * signs, signs


def estimate(training, standardized, spec):
    """Fit on training months; filter the masked origin; never smooth forecasts."""
    model = DynamicFactor(training, k_factors=spec.factors, factor_order=1,
                          error_cov_type='diagonal', error_order=0,
                          enforce_stationarity=True)
    attempts = []
    best = None
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        for method in ('lbfgs', 'bfgs'):
            fit = model.fit(method=method, maxiter=400, disp=False,
                            **({'start_params': best.params} if best is not None else {}))
            attempts.append({'optimizer': method, 'converged': bool(fit.mle_retvals.get('converged')), 'llf': float(fit.llf)})
            best = fit
            if fit.mle_retvals.get('converged'):
                break
    fit = best
    params = dict(zip(fit.param_names, np.asarray(fit.params)))
    loadings = np.array([[params[f'loading.f{j+1}.{field}'] for j in range(spec.factors)] for field in training.columns])
    # apply() holds training estimates fixed and filters only supplied data.
    origin_fit = fit.apply(standardized, refit=False)
    factors = origin_fit.factors.filtered.T
    loadings, factors, signs = sign_normalize(loadings, factors)
    transition = np.array([[params[f'L1.f{j+1}.f{i+1}'] for j in range(spec.factors)] for i in range(spec.factors)])
    radius = float(max(abs(np.linalg.eigvals(transition))))
    diag = dict(converged=bool(fit.mle_retvals.get('converged')), estimation_attempted=True, log_likelihood=float(fit.llf),
                warnings=' | '.join(str(w.message) for w in caught), optimizer_attempts=json.dumps(attempts),
                transition=json.dumps(transition.tolist()), factor_ar_coefficient=float(transition[0, 0]),
                spectral_radius=radius, n_months=len(training), n_observations=int(training.notna().sum().sum()),
                factor_source='FILTERED_ONE_SIDED', covariance_condition=float(np.linalg.cond(fit.cov_params())))
    if not diag['converged'] or radius >= .9999 or not np.isfinite(factors).all():
        diag['failure'] = 'nonconvergence_or_near_unit_root'
    elif spec.factors == 2 and diag['covariance_condition'] > 1e12:
        diag['failure'] = 'NOT_ESTIMABLE_WITH_CURRENT_SAMPLE: weak_rotational_identification'
    return fit, factors, loadings, params, signs, diag


def bridge(factors, index, gdp, target, bridge_name):
    """Full-quarter means of filtered states, including model-predicted missing states."""
    fq = pd.DataFrame(factors, index=index).groupby(index.to_period('Q')).mean()
    counts = pd.Series(1, index=index).groupby(index.to_period('Q')).sum()
    fq = fq.loc[counts.eq(3)]
    quarters = [q for q in fq.index if str(q) < target and str(q) in gdp.index]
    if len(quarters) < 12:
        raise ValueError('fewer_than_12_complete_GDP_training_quarters')
    x, y = [], []
    for q in quarters:
        lag = str(q - 1)
        row = [1., *fq.loc[q].tolist()]
        if bridge_name == 'BRIDGE_B':
            if lag not in gdp.index:
                continue
            row.append(float(gdp.loc[lag]))
        x.append(row)
        y.append(float(gdp.loc[str(q)]))
    x = np.asarray(x)
    if len(y) < 12 or np.linalg.matrix_rank(x) < x.shape[1]:
        raise ValueError('insufficient_or_rank_deficient_bridge_training')
    coef = np.linalg.lstsq(x, y, rcond=None)[0]
    target_row = [1., *fq.loc[pd.Period(target, freq='Q')].tolist()]
    if bridge_name == 'BRIDGE_B':
        target_row.append(float(gdp.loc[str(pd.Period(target, freq='Q') - 1)]))
    return float(np.asarray(target_row) @ coef), len(y), coef.tolist(), float(np.linalg.cond(x))


def matched_pair(research, benchmark):
    """Exact one-to-one origin matching, never align by row position."""
    if research.duplicated(KEYS).any() or benchmark.duplicated(KEYS).any():
        raise ValueError('duplicate_forecast_origin')
    research = research.drop(columns=['prediction_benchmark', 'actual_benchmark'], errors='ignore')
    result = research.merge(benchmark[KEYS + ['prediction', 'actual']], on=KEYS,
                            suffixes=('', '_benchmark'), validate='one_to_one')
    result = result.dropna(subset=['prediction', 'prediction_benchmark'])
    if not np.allclose(result.actual, result.actual_benchmark, rtol=0, atol=1e-10):
        raise ValueError('frozen_GDP_target_mismatch')
    return result
