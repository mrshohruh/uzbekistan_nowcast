"""Descriptive signals, concentration, pure real-money and matched scoring."""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson
from scripts.phase6g import analysis as ga
from scripts.phase6e.models import sw
from uznowcast.models.data import quarter_start

CAVEAT=ga.CAVEAT
KEYS=ga.KEYS


def real_money(nominal,cpi_mom):
    """Real YoY log money = nominal YoY − twelve consecutive monthly CPI logs."""
    index=pd.date_range(min(nominal.index.min(),cpi_mom.index.min()),max(nominal.index.max(),cpi_mom.index.max()),freq='ME')
    inflation=cpi_mom.reindex(index).rolling(12,min_periods=12).sum()
    return nominal.reindex(index)-inflation,inflation


def shares(values):
    """Null stays null; denominator uses available non-null absolute signals."""
    total=values.abs().sum(min_count=1)
    return 100*values.abs()/total if pd.notna(total) and total>0 else values*np.nan


def drivers(fit,model,target,horizon,origin,transformations,current=False):
    k=sw.common.kernel();end=quarter_start(target)-pd.Timedelta(days=1)
    z,mean,scale=k.standardize(fit['frame'],end,False)
    load=pd.Series(fit['loadings'],index=z.columns)
    rows=[]
    for key in z:
        s=z[key].dropna();q=z.loc[z.index.to_period('Q')==pd.Period(target,'Q'),key].dropna()
        signal=float(load[key]*q.mean()) if len(q) else np.nan
        rows.append(dict(model=model,forecast_origin=str(origin),target_quarter=target,horizon=horizon,current=current,indicator=key,
            latest_period=str(s.index.max().to_period('M')-(2 if key=='m2' and model=='D2' else 0)) if len(s) else None,
            latest_factor_cell_period=str(s.index.max().to_period('M')) if len(s) else None,months_available=len(q),missing_months=3-len(q),
            standardized_signal=float(q.mean()) if len(q) else None,standardized_current_value=float(q.mean()) if len(q) else None,
            latest_standardized_value=float(s.iloc[-1]) if len(s) else None,training_mean=float(mean[key]),training_std=float(scale[key]),
            factor_loading=float(load[key]),descriptive_signal=signal,absolute_loading_share_pct=float(100*abs(load[key])/load.abs().sum()),
            transformation=transformations[key],available_flag=bool(len(q)),evidence_class=CAVEAT))
    f=pd.DataFrame(rows);f['absolute_signal_share_pct']=shares(f.descriptive_signal)
    return f


def concentration(drivers):
    rows=[]
    for (model,target,horizon,current),g in drivers.groupby(['model','target_quarter','horizon','current']):
        available=g.loc[g.available_flag & g.descriptive_signal.notna()]
        m2=g.loc[g.indicator.eq('m2')]
        largest=available.loc[available.absolute_signal_share_pct.idxmax()] if len(available) else None
        m=m2.iloc[0] if len(m2) else None
        rows.append(dict(model=model,forecast_origin=g.forecast_origin.iloc[0],target_quarter=target,horizon=horizon,current=current,
            available_indicator_count=int(g.available_flag.sum()),available_target_quarter_month_count=int(g.months_available.sum()),
            m2_months_available=int(m.months_available) if m is not None else None,m2_signal=m.descriptive_signal if m is not None else None,
            m2_signal_share_pct=m.absolute_signal_share_pct if m is not None else None,m2_loading_share_pct=m.absolute_loading_share_pct if m is not None else None,
            m2_zscore=m.standardized_current_value if m is not None else None,
            largest_signal_indicator=largest.indicator if largest is not None else None,largest_signal_share_pct=largest.absolute_signal_share_pct if largest is not None else None,
            signal_HHI=float(np.sum((available.absolute_signal_share_pct/100)**2)) if len(available) else None,evidence_class=CAVEAT))
    return pd.DataFrame(rows)


def distribution(values,current,name):
    values=pd.Series(values).dropna()
    rank=100*float((values<=current).mean()) if len(values) and pd.notna(current) else None
    # Empirical quartiles/deciles, explicitly descriptive rather than policy cutoffs.
    label='EXTREME' if current>values.quantile(.9) else 'ELEVATED' if current>values.quantile(.75) else 'NORMAL_RANGE'
    return dict(statistic=name,N=len(values),mean=values.mean(),median=values.median(),std=values.std(ddof=1),min=values.min(),max=values.max(),
        p25=values.quantile(.25),p75=values.quantile(.75),p90=values.quantile(.9),current=current,current_percentile=rank,
        descriptive_range=label,classification_rule='Above empirical p90 EXTREME; above p75 ELEVATED; otherwise NORMAL_RANGE; not a model-selection rule',evidence_class=CAVEAT)


def metrics(forecasts,sample):
    rows=[]
    for h in ['H1','H2','H3','POOLED']:
        block=forecasts if h=='POOLED' else forecasts.loc[forecasts.horizon.eq(h)]
        for model,g in block.groupby('model'):
            g=g.dropna(subset=['prediction','actual'])
            base='E0' if model.startswith('E') else 'D0'
            paired=g.merge(block.loc[block.model.eq(base),KEYS+['prediction']].rename(columns={'prediction':'benchmark'}),on=KEYS,validate='one_to_one').dropna(subset=['benchmark'])
            if paired.empty:continue
            error=paired.actual-paired.prediction;be=paired.actual-paired.benchmark
            rmse=float(np.sqrt(np.mean(error**2)));brmse=float(np.sqrt(np.mean(be**2)))
            rows.append(dict(model=model,sample=sample,horizon=h,N=len(paired),RMSE=rmse,MAE=float(error.abs().mean()),bias=float(error.mean()),
                median_absolute_error=float(error.abs().median()),max_absolute_error=float(error.abs().max()),
                OOS_R2=1-float(sum(error**2)/sum(be**2)) if sum(be**2)>0 else None,
                forecast_correlation=paired.actual.corr(paired.prediction) if paired.actual.nunique()>1 and paired.prediction.nunique()>1 else None,
                benchmark=base,benchmark_RMSE=brmse,delta_RMSE=rmse-brmse,relative_RMSE_change_pct=100*(rmse-brmse)/brmse if brmse else None,evidence_class=CAVEAT))
    return pd.DataFrame(rows)


def common_sample(forecasts,models):
    if forecasts.duplicated(KEYS+['model']).any():raise ValueError('Duplicate origin')
    f=forecasts.loc[forecasts.model.isin(models)]
    for _,g in f.groupby(KEYS):
        if not np.allclose(g.actual,g.actual.iloc[0],rtol=0,atol=1e-12):raise ValueError('Actual vintages differ')
    keys=f.pivot(index=KEYS,columns='model',values='prediction').reindex(columns=models).dropna().reset_index()[KEYS]
    return f.merge(keys,on=KEYS,validate='many_to_one')


def bridge_diagnostics(fit,available,target):
    fq=sw.common.kernel().quarterly(fit['factors'],'mean');gd=available.frame.value
    x=[];y=[]
    for q in fq.index:
        if str(q)<target and str(q) in gd and str(q-1) in gd:
            x.append([1.,float(fq.loc[q].iloc[0]),float(gd.loc[str(q-1)])]);y.append(float(gd.loc[str(q)]))
    x=np.asarray(x);result=sm.OLS(y,x).fit();influence=result.get_influence()
    return [dict(term=t,coefficient=float(b),standard_error=float(se),VIF=float(variance_inflation_factor(x,j)) if j else None,
        condition_number=float(np.linalg.cond(x)),Durbin_Watson=float(durbin_watson(result.resid)),
        max_leverage=float(influence.hat_matrix_diag.max()),max_Cooks_distance=float(influence.cooks_distance[0].max()),n_train=len(y),evidence_class=CAVEAT)
        for j,(t,b,se) in enumerate(zip(['intercept','factor','GDP_lag1'],result.params,result.bse))]
