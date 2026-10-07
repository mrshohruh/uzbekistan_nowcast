"""Extend the frozen unrestricted design without changing its lag semantics."""
from dataclasses import replace
import numpy as np
import pandas as pd
from uznowcast.models.midas import MidasSpec, _monthly_lag_vector

KEYS = ('usd_uzs', 'industrial_production', 'm2', 'retail_trade')
SPECS = {'U0': KEYS[:1], 'U1': KEYS[:2], 'U2': (KEYS[0], KEYS[2]),
         'U3': (KEYS[0], KEYS[3]), 'U4': KEYS[:3],
         'U5': (KEYS[0], KEYS[1], KEYS[3]), 'U6': KEYS}


def vector(dataset, keys, quarter, horizon):
    """Last three nonmissing released values per variable, oldest first."""
    return np.concatenate([_monthly_lag_vector(dataset, MidasSpec(key,
        dataset.clean_field_by_key[key], 3), quarter, horizon, 'standard') for key in keys])


def estimate(dataset, available, keys, target, horizon):
    """Same GDP ordering, expanding window and 15-row threshold as production."""
    quarters = available.frame.index.tolist()
    gd = available.frame.value
    rows, outcomes = [], []
    for i, q in enumerate(quarters):
        x = np.r_[1., float(gd.iloc[i-1]) if i else np.nan, vector(dataset, keys, q, horizon)]
        if np.isfinite(x).all() and np.isfinite(gd.loc[q]):
            rows.append(x); outcomes.append(float(gd.loc[q]))
    columns = ['intercept', 'gdp_lag1'] + [f'{k}:lag_{j}' for k in keys for j in range(3)]
    n, k = len(rows), len(columns)
    diag = dict(n_train=n, n_parameters=k, n_over_k=n/k, columns=columns)
    if n < 15:
        return np.nan, dict(diag, failure='fewer_than_15_training_rows')
    X, y = np.array(rows), np.array(outcomes)
    coef, _, rank, singular = np.linalg.lstsq(X, y, rcond=None)
    residual = y-X@coef
    se = np.sqrt(np.maximum(np.diag(np.linalg.pinv(X.T@X))*float(residual@residual)/(n-k), 0)) if n > k and rank == k else np.full(k,np.nan)
    x = np.r_[1.,float(gd.iloc[-1]),vector(dataset,keys,target,horizon)]
    diag.update(coefficients=coef, standard_errors=se, rank=int(rank),
                condition_number=float(np.linalg.cond(X)), residual_df=n-k,
                weak_degrees_of_freedom=n/k < 3, regressor_values=x)
    if not np.isfinite(x).all():
        return np.nan, dict(diag,failure='missing_monthly_lags_at_target')
    return float(coef@x), diag


def gated(dataset, available):
    return replace(dataset, gdp=pd.DataFrame({'quarter':available.frame.index,
        dataset.target_field:available.frame.value.to_numpy()}))


def common_sample(forecasts, models):
    keys = ['origin','target_quarter','horizon','actual','evaluation_group']
    if forecasts.duplicated(['origin','target_quarter','horizon','model']).any():
        raise ValueError('Duplicate origin/model')
    return forecasts.pivot(index=keys,columns='model',values='prediction').reindex(columns=models).dropna().reset_index()


def metrics(frame):
    error = frame.actual-frame.prediction
    return dict(n_origins=len(frame),rmse=float(np.sqrt((error**2).mean())),
        mae=float(error.abs().mean()),bias=float(error.mean()),
        error_std=float(error.std()),max_absolute_error=float(error.abs().max()),
        n_train_min=float(frame.n_train.min()),n_train_median=float(frame.n_train.median()),
        n_train_max=float(frame.n_train.max()), n_parameters=int(frame.n_parameters.iloc[0]) if len(frame) else 0)
