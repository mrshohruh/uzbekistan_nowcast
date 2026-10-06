"""Inspect actual frozen model designs and retain fits for counterfactual news."""
from dataclasses import replace
from types import SimpleNamespace
import numpy as np
import pandas as pd

from scripts.operations import shadow_worker as sw
from uznowcast.models.data import load_dataset, quarter_start, quarter_end, build_information_set
from uznowcast.models.midas import MidasSpec, midas_forecast, _monthly_lag_vector

FIELDS = sw.common.FIELDS
SPEC_NAME = 'DFM-4_R1_P2__BRIDGE_B_mean'
UMIDAS_SPEC = MidasSpec('umidas_usd_uzs_mom_dlog', 'usd_uzs_mom_dlog', 3, True, None)


def frames(info, root, origin):
    """Rehydrate archived, already release-gated economic inputs."""
    panel = pd.DataFrame(info['panel']).set_index('month')
    panel.index = pd.to_datetime(panel.index)
    panel = panel.astype(float)
    monthly = pd.DataFrame(info['benchmark_monthly'])
    date = next(c for c in ['date', 'month', 'index'] if c in monthly)
    monthly = monthly.set_index(date).astype(float)
    monthly.index = pd.to_datetime(monthly.index)
    gdp = pd.DataFrame(info['GDP']).set_index('quarter')
    available = SimpleNamespace(frame=gdp, origin=pd.Timestamp(origin), timing_rule='STRICT')
    # Require verified GDP and strictly earlier dated publications, including replay.
    sw.common.vintage_kernel().assert_boundary(available, info['target'])
    dataset = replace(load_dataset(root), monthly=monthly,
                      gdp=pd.DataFrame({'quarter':gdp.index, 'gdp_real_yoy_pct':gdp.value.to_numpy()}))
    return panel, dataset, available


def umidas(dataset, available, target, horizon, origin):
    train = available.frame.index.tolist()
    prediction, diag = midas_forecast(dataset, UMIDAS_SPEC, train, target,
                                     horizon=horizon, mode='standard')
    if not np.isfinite(prediction) or diag.get('n_train', 0) < 15:
        raise ValueError('U-MIDAS unavailable: ' + str(diag))
    x = np.r_[1., float(available.frame.value.loc[train[-1]]),
              _monthly_lag_vector(dataset, UMIDAS_SPEC, target, horizon, 'standard')]
    coef = np.array(diag['coefficients'])
    contributions = x * coef
    fx_periods=build_information_set(dataset,target,horizon,[UMIDAS_SPEC.field],mode='standard')[UMIDAS_SPEC.field].dropna().tail(3).index
    observation_periods=[None,train[-1],*[str(date.to_period('M')) for date in fx_periods]]
    error = float(contributions.sum() - prediction)
    if abs(error) >= 1e-10:
        raise ValueError('U-MIDAS contribution reconstruction failed')
    rows = [dict(forecast_origin=str(origin), target_quarter=target, horizon=horizon,
                 term=term, coefficient=float(b), regressor_value=float(v),
                 contribution_pp=float(c), prediction=prediction, reconstruction_error=error,
                 observation_period=period,lag_order='oldest_to_newest' if term.startswith('lag_') else None)
            for term,b,v,c,period in zip(diag['column_order'],coef,x,contributions,observation_periods)]
    return prediction, rows, dict(coefficients=coef, x=x, diagnostics=diag)


def dfm(panel, dataset, available, target, horizon, origin):
    k = sw.common.kernel()
    spec = k.Spec('DFM-4_R1_P2', FIELDS, 1, 2, '2019-01-31', True, False)
    frame, audit = k.mask(panel, spec, target, horizon, dataset.release_lag_days, 'standard')
    end = quarter_start(target)-pd.Timedelta(days=1)
    frame,_ = k.training_panel(frame, end, True)
    z,means,scales = k.standardize(frame, end, False)
    z = z.reindex(pd.date_range(z.index.min(),quarter_end(target),freq='ME'))
    cache = {}
    factors,loadings,diag = k.estimate(z.loc[:end],z,spec,cache)
    prediction, bridge_diag = k.bridge(factors,available,target,origin,'B','mean')
    fit = next(iter(cache.values()))[0]
    params = dict(zip(fit.param_names,fit.params))
    raw_loadings = np.array([params['loading.0->'+field] for field in FIELDS])
    sign = 1. if raw_loadings[np.argmax(abs(raw_loadings))] >= 0 else -1.
    fq = k.quarterly(factors,'mean')
    gd = available.frame.value
    x,y = [],[]
    for q in fq.index:
        if str(q) < target and str(q) in gd and str(q-1) in gd:
            x.append([1.,float(fq.loc[q].iloc[0]),float(gd.loc[str(q-1)])])
            y.append(float(gd.loc[str(q)]))
    bridge_coef = np.linalg.lstsq(np.array(x),np.array(y),rcond=None)[0]
    return prediction, dict(fit=fit, means=means, scales=scales, z=z, frame=frame,
                            factors=factors, loadings=loadings[:,0], sign=sign,
                            bridge_coef=bridge_coef, diagnostics=diag, release_masks=audit,
                            parameters=params, bridge_diagnostics=bridge_diag)


def fit_info(info, root, origin):
    panel,dataset,available = frames(info,root,origin)
    d,dfit = dfm(panel,dataset,available,info['target'],info['horizon'],origin)
    u,terms,ufit = umidas(dataset,available,info['target'],info['horizon'],origin)
    return dict(dfm=d, umidas=u, final=.5*d+.5*u, terms=terms, dfit=dfit, ufit=ufit,
                panel=panel,dataset=dataset,available=available)


def fixed_prediction(info, root, origin, old_fit):
    """Freeze old scaling, state parameters, GDP bridge and U-MIDAS coefficients."""
    panel,dataset,available = frames(info,root,origin)
    d = old_fit['dfit']
    z = (panel.reindex(d['z'].index)[list(FIELDS)]-d['means'])/d['scales']
    applied = d['fit'].apply(z, refit=False, retain_standardization=False)
    factor = pd.Series(applied.factors.filtered.iloc[:,0].to_numpy()*d['sign'],index=z.index)
    fbar = factor.loc[factor.index.to_period('Q') == pd.Period(info['target'],'Q')].mean()
    prior = str(pd.Period(info['target'],'Q')-1)
    df = float(np.array([1.,fbar,float(available.frame.value.loc[prior])]) @ d['bridge_coef'])
    x = np.r_[1.,float(available.frame.value.iloc[-1]),
              _monthly_lag_vector(dataset,UMIDAS_SPEC,info['target'],info['horizon'],'standard')]
    uf = float(x @ old_fit['ufit']['coefficients'])
    if not np.isfinite([df,uf]).all():
        raise ValueError('Non-comparable counterfactual information set')
    return np.array([df,uf])
