"""Calendar transformations and unchanged accepted DFM estimation kernels."""
import numpy as np
import pandas as pd
from scripts.phase6e.models import FIELDS, sw
from scripts.phase6f.experiment import economic_lag
from uznowcast.models.data import quarter_start, quarter_end

MODELS = ['M0', 'M1', 'M2', 'Q0', 'Q1', 'Q2']


def log_change(levels, months):
    """Exact calendar-month log change; gaps/nonpositive parents stay missing."""
    if levels.index.has_duplicates or months not in (3, 12):
        raise ValueError('Duplicate dates or unsupported transformation')
    full = levels.sort_index().reindex(pd.date_range(levels.index.min(), levels.index.max(), freq='ME'))
    positive = full.where(full > 0)
    return 100 * (np.log(positive) - np.log(positive.shift(months)))


def design(panel, dataset, target, horizon, model, common_start=None):
    k = sw.common.kernel()
    spec = k.Spec('DFM-4_R1_P2', FIELDS, 1, 2, '2019-01-31', True, False)
    frame, audit = k.mask(panel, spec, target, horizon, dataset.release_lag_days, 'standard')
    frame['m2'] = economic_lag(frame.m2, int(model[-1]))
    end = quarter_start(target) - pd.Timedelta(days=1)
    frame, _ = k.training_panel(frame, end, True)
    if common_start is not None:
        frame = frame.loc[common_start:]
    return frame, spec, audit, end


def fit(frame, spec, end, available, target, origin, cache):
    k = sw.common.kernel()
    z, means, scales = k.standardize(frame, end, False)
    z = z.reindex(pd.date_range(z.index.min(), quarter_end(target), freq='ME'))
    factors, load, diag = k.estimate(z.loc[:end], z, spec, cache)
    prediction, bridge = k.bridge(factors, available, target, origin, 'B', 'mean')
    return prediction, dict(frame=frame, z=z, means=means, scales=scales,
                            factors=factors, loadings=load[:, 0], diagnostics=diag,
                            bridge_diagnostics=bridge)


def metrics(forecasts):
    """All six models use a global intersection, never pairwise samples."""
    rows = []
    wide = forecasts.pivot(index=['target_quarter', 'horizon'], columns=['sample','model'], values='prediction')
    wanted = pd.MultiIndex.from_product([forecasts['sample'].unique(), MODELS])
    common_origins = wide.reindex(columns=wanted).dropna().index
    for sample, f in forecasts.groupby('sample'):
        f = f.set_index(['target_quarter', 'horizon']).loc[common_origins].reset_index()
        for horizon in ['H1', 'H2', 'H3', 'POOLED']:
            g = f if horizon == 'POOLED' else f.loc[f.horizon.eq(horizon)]
            base = g.loc[g.model.eq('M0')].set_index(['target_quarter', 'horizon'])
            for model, b in g.groupby('model'):
                b = b.set_index(['target_quarter', 'horizon']).sort_index()
                e = b.actual - b.prediction
                be = base.reindex(b.index).actual - base.reindex(b.index).prediction
                counterpart = g.loc[g.model.eq('M'+model[-1])].set_index(['target_quarter', 'horizon']).reindex(b.index)
                rmse = float(np.sqrt(np.mean(e**2)))
                rows.append(dict(sample=sample, model=model, horizon=horizon, N=len(b), RMSE=rmse,
                    MAE=float(e.abs().mean()), bias=float(e.mean()), OOS_R2=1-float(sum(e**2)/sum(be**2)),
                    delta_RMSE_vs_M0=rmse-float(np.sqrt(np.mean(be**2))),
                    delta_RMSE_vs_corresponding_YoY=rmse-float(np.sqrt(np.mean((counterpart.actual-counterpart.prediction)**2)))))
    return pd.DataFrame(rows)
