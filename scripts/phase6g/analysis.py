"""Pure, exact-common-origin ensemble diagnostics; bias = actual − prediction."""
from __future__ import annotations
import numpy as np
import pandas as pd

KEYS=['target_quarter','horizon']
MODELS=['P0','G1','G2','S0','S1','S2','U0']
CAVEAT='AVAILABILITY_AWARE_PSEUDO_REAL_TIME; HISTORICAL_PREDICTOR_VALUE_VINTAGES_UNVERIFIED'


def ensembles(s0,s1,s2,u):
    return dict(S0=s0,S1=s1,S2=s2,U0=u,P0=.5*s0+.5*u,G1=.5*s1+.5*u,G2=.5*s2+.5*u)


def common_keys(forecasts):
    """Every model must have a finite forecast and identical actual at an origin."""
    if forecasts.duplicated(KEYS+['model']).any():
        raise ValueError('Duplicate model/origin')
    f=forecasts.loc[forecasts.model.isin(MODELS)].copy()
    valid=np.isfinite(f.prediction) & np.isfinite(f.actual)
    for _,g in f.loc[valid].groupby(KEYS):
        if not np.allclose(g.actual,g.actual.iloc[0],rtol=0,atol=1e-12):
            raise ValueError('Different actual vintages at origin')
    wide=f.loc[valid].pivot(index=KEYS,columns='model',values='prediction').reindex(columns=MODELS)
    return wide.dropna().reset_index()[KEYS]


def strict_common(forecasts,eligible):
    keys=common_keys(forecasts)
    approved=eligible.loc[eligible.common_origin_eligible,KEYS]
    keys=keys.merge(approved,on=KEYS,validate='one_to_one')
    return forecasts.merge(keys,on=KEYS,validate='many_to_one')


def metric_rows(forecasts,sample):
    rows=[]
    for h in ['H1','H2','H3','POOLED']:
        block=forecasts if h=='POOLED' else forecasts.loc[forecasts.horizon.eq(h)]
        for model,g in block.groupby('model'):
            g=g.loc[np.isfinite(g.actual) & np.isfinite(g.prediction)]
            if g.empty: continue
            benchmark='S0' if model.startswith('S') else 'P0'
            base=block.loc[block.model.eq(benchmark),KEYS+['actual','prediction']].rename(columns={'prediction':'base_prediction','actual':'base_actual'})
            paired=g.merge(base,on=KEYS,validate='one_to_one').dropna(subset=['base_prediction'])
            e=g.actual-g.prediction
            pe=paired.actual-paired.prediction;be=paired.base_actual-paired.base_prediction
            sse=float(np.sum(e**2));bsse=float(np.sum(be**2))
            rmse=float(np.sqrt(np.mean(e**2)))
            paired_rmse=float(np.sqrt(np.mean(pe**2))) if len(paired) else np.nan
            brmse=float(np.sqrt(np.mean(be**2))) if len(paired) else np.nan
            rows.append(dict(model=model,sample=sample,horizon=h,N=len(g),n_quarters=g.target_quarter.nunique(),RMSE=rmse,
                MAE=float(e.abs().mean()),bias=float(e.mean()),median_abs_error=float(e.abs().median()),max_abs_error=float(e.abs().max()),
                forecast_correlation=float(g.prediction.corr(g.actual)) if len(g)>=3 and g.prediction.nunique()>1 and g.actual.nunique()>1 else None,
                SSE=sse,OOS_R2=1-float(np.sum(pe**2))/bsse if bsse>0 else None,benchmark=benchmark,OOS_N=len(paired),
                benchmark_common_RMSE=brmse,delta_RMSE_vs_benchmark=paired_rmse-brmse,
                relative_RMSE_improvement_pct=100*(brmse-paired_rmse)/brmse if brmse>0 else None,
                mean_absolute_revision_vs_benchmark=float((paired.prediction-paired.base_prediction).abs().mean()) if len(paired) else None,
                evidence_class=CAVEAT))
    return pd.DataFrame(rows)


def origin_errors(forecasts,sample):
    wide=forecasts.pivot(index=KEYS,columns='model',values='prediction').reindex(columns=MODELS)
    actual=forecasts.groupby(KEYS).actual.first().reindex(wide.index)
    result=wide.reset_index()
    result['actual']=actual.to_numpy()
    for model in MODELS:
        result[model+'_error']=result.actual-result[model]
        result['abs_error_'+model]=result[model+'_error'].abs()
    result['G2_minus_P0']=result.G2-result.P0
    result['identity_error']=result.G2_minus_P0-.5*(result.S2-result.S0)
    if result.identity_error.abs().max()>1e-12:
        raise ValueError('Ensemble revision identity failed')
    result['sample']=sample;result['evidence_class']=CAVEAT
    return result


def win_rates(errors,sample,tolerance=1e-12):
    rows=[]
    for h in ['H1','H2','H3','POOLED']:
        g=errors if h=='POOLED' else errors.loc[errors.horizon.eq(h)]
        for m in ['G1','G2']:
            diff=g['abs_error_'+m]-g.abs_error_P0
            diff=diff.dropna()
            if diff.empty: continue
            wins=int(diff.lt(-tolerance).sum());ties=int(diff.abs().le(tolerance).sum())
            rows.append(dict(model=m,sample=sample,horizon=h,N=len(diff),wins=wins,ties=ties,worse=len(diff)-wins-ties,
                win_rate_pct=100*wins/len(diff),evidence_class=CAVEAT))
    return pd.DataFrame(rows)


def correlations(errors,sample):
    rows=[]
    for h in ['H1','H2','H3','POOLED']:
        g=errors if h=='POOLED' else errors.loc[errors.horizon.eq(h)]
        for m in ['S0','S1','S2']:
            pair=g[[m+'_error','U0_error']].dropna()
            n=len(pair)
            rho=pair.corr().iloc[0,1] if n>=3 and pair.nunique().min()>1 else None
            mse_a=float(np.mean(pair.iloc[:,0]**2)) if n else None
            mse_u=float(np.mean(pair.U0_error**2)) if n else None
            cross=float(np.mean(pair.iloc[:,0]*pair.U0_error)) if n else None
            rows.append(dict(model_a=m,model_b='U0',sample=sample,horizon=h,N=n,error_correlation=rho,
                component_MSE=mse_a,umidas_MSE=mse_u,mean_error_product=cross,
                ensemble_MSE=.25*mse_a+.25*mse_u+.5*cross if n else None,
                interpretation='Descriptive error correlation; correlated horizons within quarters; correlation alone omits bias',evidence_class=CAVEAT))
    return pd.DataFrame(rows)


def leave_one_quarter_out(forecasts,sample):
    rows=[]
    for q in sorted(forecasts.target_quarter.unique()):
        f=forecasts.loc[forecasts.target_quarter.ne(q)]
        scores=metric_rows(f,sample)
        for h in ['H1','H2','H3','POOLED']:
            g=scores.loc[scores.horizon.eq(h)].set_index('model')
            if 'P0' not in g.index:continue
            for m in ['G1','G2']:
                if m not in g.index:continue
                delta=float(g.loc[m,'RMSE']-g.loc['P0','RMSE'])
                rows.append(dict(excluded_quarter=q,model=m,sample=sample,horizon=h,N=int(g.loc[m,'N']),
                    P0_RMSE=float(g.loc['P0','RMSE']),challenger_RMSE=float(g.loc[m,'RMSE']),
                    G2_RMSE=float(g.loc[m,'RMSE']) if m=='G2' else None,G1_RMSE=float(g.loc[m,'RMSE']) if m=='G1' else None,
                    delta_RMSE=delta,G2_better=delta<0 if m=='G2' else None,challenger_better=delta<0,evidence_class=CAVEAT))
    return pd.DataFrame(rows)


def revisions(forecasts,sample):
    """Calendar chronology is H1→H2→H3; also expose requested reverse view."""
    rows=[]
    for (model,q),g in forecasts.groupby(['model','target_quarter']):
        g=g.set_index('horizon')
        if not {'H1','H2','H3'}.issubset(g.index) or g.prediction.isna().any():continue
        r12=float(g.loc['H2','prediction']-g.loc['H1','prediction'])
        r23=float(g.loc['H3','prediction']-g.loc['H2','prediction'])
        consistent=bool(r12*r23>=-1e-12)
        rows.append(dict(model=model,target_quarter=q,sample=sample,H1_to_H2=r12,H2_to_H3=r23,
            H3_to_H2=-r23,H2_to_H1=-r12,mean_abs_revision=.5*(abs(r12)+abs(r23)),mean_signed_revision=.5*(r12+r23),
            max_abs_revision=max(abs(r12),abs(r23)),directionally_consistent=consistent,
            chronological_order='H1_H2_H3',evidence_class=CAVEAT))
    return pd.DataFrame(rows)


def weights(errors,sample):
    rows=[]
    for w in [.25,.5,.75]:
        for h in ['H1','H2','H3','POOLED']:
            g=errors if h=='POOLED' else errors.loc[errors.horizon.eq(h)]
            if g.empty:continue
            pred=w*g.S2+(1-w)*g.U0
            control=w*g.S0+(1-w)*g.U0
            e=g.actual-pred;ce=g.actual-control;pe=g.actual-g.P0
            rmse=float(np.sqrt(np.mean(e**2)))
            rows.append(dict(dfm_weight=w,umidas_weight=1-w,sample=sample,horizon=h,N=len(g),RMSE=rmse,
                unchanged_M2_same_weight_RMSE=float(np.sqrt(np.mean(ce**2))),P0_50_50_RMSE=float(np.sqrt(np.mean(pe**2))),
                delta_vs_same_weight=rmse-float(np.sqrt(np.mean(ce**2))),delta_vs_P0_50_50=rmse-float(np.sqrt(np.mean(pe**2))),
                diagnostic_only=True,evidence_class=CAVEAT))
    return pd.DataFrame(rows)


def bootstrap_quarters(errors,sample,draws=2000,seed=617):
    """Paired quarter-cluster resampling; exploratory, not independent horizons."""
    grouped=errors.groupby('target_quarter')
    losses=np.array([[np.sum(g.G2_error**2),np.sum(g.P0_error**2),len(g)] for _,g in grouped])
    if len(losses)<4:return pd.DataFrame()
    rng=np.random.default_rng(seed)
    selected=rng.integers(0,len(losses),size=(draws,len(losses)))
    sums=losses[selected].sum(axis=1)
    delta=np.sqrt(sums[:,0]/sums[:,2])-np.sqrt(sums[:,1]/sums[:,2])
    return pd.DataFrame([dict(sample=sample,n_quarters=len(losses),draws=draws,seed=seed,
        RMSE_difference_CI_lower=float(np.quantile(delta,.025)),RMSE_difference_CI_upper=float(np.quantile(delta,.975)),
        paired_mean_squared_loss_difference=float(np.mean(errors.G2_error**2-errors.P0_error**2)),
        interpretation='Exploratory paired quarter-cluster bootstrap; small sample/serial dependence limit inference',evidence_class=CAVEAT)])
