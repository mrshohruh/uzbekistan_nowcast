"""Keep accepted factors fixed; substitute only quarterly bridge target values."""
import json
import numpy as np
import pandas as pd
from scripts.phase6e.models import sw
from scripts.phase6g3.protection import OUT


def controlled_bridges(fit, real, nominal, target):
    """Identical training quarters/design apart from target and its own AR term.

    All quarters remain inside the accepted training window. The extra missing
    nominal history is applied to both controls, never replaced by revised SIAT.
    """
    fq=sw.common.kernel().quarterly(fit['factors'],'mean').iloc[:,0]
    if nominal.empty:raise ValueError('No eligible nominal GDP history')
    qtarget=pd.Period(target,'Q');prior=str(qtarget-1)
    gd=real.frame.value
    if prior not in nominal.index or prior not in gd.index:raise ValueError('Prior-quarter target unavailable')
    used=[str(q) for q in fq.index if str(q)<target and str(q) in gd.index and str(q-1) in gd.index
        and str(q) in nominal.index and str(q-1) in nominal.index]
    if len(used)<12:raise ValueError(f'Insufficient identical nominal/real bridge history: {len(used)} quarters, minimum 12')
    predictions={};diagnostics=[]
    for model,values in [('REAL_SHARED_BRIDGE',gd),('NOMINAL_STANDALONE_LOG',nominal.value)]:
        x=np.array([[1.,float(fq.loc[pd.Period(q,'Q')]),float(values.loc[str(pd.Period(q,'Q')-1)])] for q in used])
        y=values.reindex(used).to_numpy(dtype=float)
        if np.linalg.matrix_rank(x)!=3:raise ValueError('Rank-deficient GDP bridge')
        coefficients=np.linalg.lstsq(x,y,rcond=None)[0]
        row=np.array([1.,float(fq.loc[qtarget]),float(values.loc[prior])])
        prediction=float(row@coefficients)
        if not np.isfinite(prediction):raise ValueError('Nonfinite bridge forecast')
        predictions[model]=prediction
        diagnostics.extend(dict(model=model,term=term,coefficient=float(b),current_value=float(v),contribution_pp=float(b*v),
            n_training_quarters=len(used),training_quarters=json.dumps(used),condition_number=float(np.linalg.cond(x)))
            for term,b,v in zip(['intercept','quarter_mean_factor','GDP_growth_lag1'],coefficients,row))
    return predictions,diagnostics,used


def scores(forecasts):
    rows=[]
    for model,b in forecasts.groupby('model'):
        for h in ['H1','H2','H3','POOLED']:
            g=b if h=='POOLED' else b.loc[b.horizon.eq(h)]
            if g.empty:continue
            error=g.actual-g.prediction
            target_sd=float(g.drop_duplicates('target_quarter').actual.std(ddof=1))
            sse=float(sum(error**2));sst=float(sum((g.actual-g.actual.mean())**2))
            prior_error=g.actual-g.prior_growth
            rmse=float(np.sqrt(np.mean(error**2)))
            rows.append(dict(model=model,horizon=h,N=len(g),N_quarters=g.target_quarter.nunique(),RMSE=rmse,
                MAE=float(error.abs().mean()),bias=float(error.mean()),forecast_correlation=g.prediction.corr(g.actual),
                forecast_R2_vs_actual_mean=1-sse/sst if sst>0 else np.nan,
                OOS_R2_vs_released_target_AR1_naive=1-sse/float(sum(prior_error**2)) if sum(prior_error**2)>0 else np.nan,
                target_std=target_sd,normalized_RMSE=rmse/target_sd if target_sd>0 else np.nan,
                forecast_volatility=float(g.prediction.std(ddof=1)),bias_convention='actual minus forecast',
                actual_definition='first documented derived standalone nominal growth' if model.startswith('NOMINAL') else 'unchanged frozen real first-release target',
                largest_absolute_error=float(error.abs().max())))
    return pd.DataFrame(rows)
