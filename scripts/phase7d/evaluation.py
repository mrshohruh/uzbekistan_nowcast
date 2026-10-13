"""Exact-origin comparisons and uncertainty clustered by target quarter."""
import numpy as np
import pandas as pd

KEYS = ['origin', 'target_quarter', 'horizon']


def matched(forecasts, models):
    block=forecasts.loc[forecasts.model.isin(models)].copy()
    if block.duplicated(KEYS+['model']).any():
        raise ValueError('Duplicate model/origin')
    if block.groupby(KEYS).actual.nunique().gt(1).any():
        raise ValueError('Different actual GDP definitions at an origin')
    complete=block.pivot(index=KEYS,columns='model',values='prediction').reindex(columns=models).dropna().reset_index()[KEYS]
    return block.merge(complete,on=KEYS,validate='many_to_one')


def metrics(frame, benchmarks=None):
    frame=frame.loc[np.isfinite(frame.prediction)&np.isfinite(frame.actual)].sort_values(KEYS)
    n=len(frame);e=frame.actual-frame.prediction
    ss=float((e**2).sum());sst=float(((frame.actual-frame.actual.mean())**2).sum())
    result=dict(n_forecasts=n,n_quarters=int(frame.target_quarter.nunique()),
        rmse=float(np.sqrt(ss/n)) if n else np.nan,mae=float(e.abs().mean()),bias=float(e.mean()),
        median_absolute_error=float(e.abs().median()),max_absolute_error=float(e.abs().max()),
        r2=1-ss/sst if n>=3 and sst>1e-12 else np.nan,
        r2_os_ar1=np.nan,r2_os_historical_mean=np.nan,
        evaluation_start=str(frame.target_quarter.min()) if n else None,
        evaluation_end=str(frame.target_quarter.max()) if n else None,
        first_origin=frame.origin.min() if n else None,last_origin=frame.origin.max() if n else None)
    if benchmarks is not None:
        for name,col in [('AR1','r2_os_ar1'),('HISTORICAL_MEAN','r2_os_historical_mean')]:
            b=benchmarks.loc[benchmarks.model.eq(name),KEYS+['prediction','actual']]
            a=frame.merge(b,on=KEYS,suffixes=('', '_benchmark'),validate='one_to_one')
            if len(a)==n and n>0 and np.allclose(a.actual,a.actual_benchmark,rtol=0,atol=1e-9):
                denominator=float(((a.actual-a.prediction_benchmark)**2).sum())
                result[col]=1-ss/denominator if denominator>1e-12 else np.nan
        for name,b in benchmarks.groupby('model'):
            a=frame.merge(b[KEYS+['prediction']],on=KEYS,suffixes=('', '_benchmark'),validate='one_to_one')
            if len(a)==n and n:
                brmse=float(np.sqrt(((a.actual-a.prediction_benchmark)**2).mean()))
                result['rmse_improvement_pct_vs_'+name]=100*(1-result['rmse']/brmse) if brmse>1e-12 else np.nan
    quarter_error=frame.assign(error=e).groupby('target_quarter').error.mean()
    result['quarter_mean_error_lag1_autocorrelation']=float(quarter_error.autocorr()) if len(quarter_error)>=4 and quarter_error.std()>1e-12 else np.nan
    result['quarter_mean_error_lag2_autocorrelation']=float(quarter_error.autocorr(2)) if len(quarter_error)>=5 and quarter_error.std()>1e-12 else np.nan
    midpoint=len(quarter_error)//2
    result['early_bias']=float(quarter_error.iloc[:midpoint].mean())
    result['recent_bias']=float(quarter_error.iloc[midpoint:].mean())
    return result


def tables(forecasts, models):
    common=matched(forecasts,models)
    refs=forecasts.loc[forecasts.model.isin(['AR1','HISTORICAL_MEAN'])].merge(common[KEYS].drop_duplicates(),on=KEYS)
    records=[];horizons=[]
    for sample,quarters in [('MATCHED_ALL',None),('MATCHED_DEVELOPMENT',lambda q:q<'2025Q3'),('MATCHED_HOLDOUT',lambda q:q>='2025Q3')]:
        part=common if quarters is None else common.loc[quarters(common.target_quarter)]
        for model in models:
            f=part.loc[part.model.eq(model)]
            benchmarks=pd.concat([part,refs.loc[refs.target_quarter.isin(part.target_quarter)]],ignore_index=True).drop_duplicates(KEYS+['model'])
            records.append(dict(sample=sample,model=model,**metrics(f,benchmarks)))
            for h in ['H1','H2','H3']:
                horizons.append(dict(sample=sample,model=model,horizon=h,**metrics(f.loc[f.horizon.eq(h)],benchmarks.loc[benchmarks.horizon.eq(h)])))
    return pd.DataFrame(records),pd.DataFrame(horizons),common


def clustered_gain(common, challenger, benchmark='COMBO_50_50', subset='ALL', seed=7):
    a=common.loc[common.model.eq(challenger)].set_index(KEYS)
    b=common.loc[common.model.eq(benchmark)].set_index(KEYS)
    losses=((b.actual-b.prediction)**2-(a.actual-a.prediction)**2).dropna().groupby(level='target_quarter').mean()
    if len(losses)<4:
        return dict(model=challenger,variant='QUARTER_CLUSTER_BOOTSTRAP',subset=subset,n_quarters=len(losses),mean_mse_gain=np.nan,ci_lower=np.nan,ci_upper=np.nan)
    rng=np.random.default_rng(seed)
    boot=rng.choice(losses.to_numpy(),size=(4000,len(losses)),replace=True).mean(axis=1)
    return dict(model=challenger,benchmark=benchmark,variant='QUARTER_CLUSTER_BOOTSTRAP',subset=subset,n_quarters=len(losses),
        mean_mse_gain=float(losses.mean()),ci_lower=float(np.quantile(boot,.025)),ci_upper=float(np.quantile(boot,.975)))


def prequential_intervals(forecasts):
    """Illustrative past-error bands, never calibrate on current/future errors."""
    result=forecasts.copy();result['interval_lower']=np.nan;result['interval_upper']=np.nan
    result['interval_basis']='UNAVAILABLE_FEWER_THAN_8_PRIOR_QUARTERS'
    result['interval_covered']=np.nan
    for (model,h),part in result.groupby(['model','horizon']):
        for i,row in part.sort_values('target_quarter').iterrows():
            prior=part.loc[(part.target_quarter<row.target_quarter)&part.prediction.notna()]
            if prior.target_quarter.nunique()<8 or pd.isna(row.prediction):continue
            width=float((prior.actual-prior.prediction).abs().quantile(.9))
            result.loc[i,['interval_lower','interval_upper']]=[row.prediction-width,row.prediction+width]
            result.loc[i,'interval_basis']='PAST_HORIZON_ERRORS_90PCT_ABSOLUTE_QUANTILE_ILLUSTRATIVE'
            result.loc[i,'interval_covered']=float(abs(row.actual-row.prediction)<=width)
    return result
