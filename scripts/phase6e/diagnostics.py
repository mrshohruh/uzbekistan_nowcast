"""Exact matched scoring, revision identity and order-invariant news attribution."""
from copy import deepcopy
from math import factorial
import numpy as np
import pandas as pd

from scripts.phase6e.models import FIELDS, fixed_prediction

MODELS = ['AR1','AR2','LEGACY_PRODUCTION_V1','U_MIDAS','PHASE6C_DFM','COMBO_50_50','COMBO_DEV_WEIGHT']
KEYS = ['target_quarter','horizon','lag_mode','timing_rule']
ALIASES = {'PRODUCTION_ENSEMBLE':'LEGACY_PRODUCTION_V1','UMIDAS_USD':'U_MIDAS',
           'DFM-4_R1_P2__BRIDGE_B_mean':'PHASE6C_DFM'}


def matched_forecasts(frame, weights):
    f = frame.loc[frame.evaluation_group.eq('HOLDOUT') & frame.lag_mode.eq('standard') &
                  frame.timing_rule.eq('STRICT') & frame.model.isin(ALIASES.keys() | {'AR1','AR2'})].copy()
    f['model'] = f.model.replace(ALIASES)
    if f.duplicated(KEYS+['model']).any():
        raise ValueError('Duplicate forecast origins')
    # Frozen CSVs differ by a few binary ULPs for identical published decimals.
    # Reject substantive vintage differences; normalize only representation noise.
    for _,g in f.groupby(KEYS):
        if not np.allclose(g.actual,g.actual.iloc[0],rtol=0,atol=1e-12):
            raise ValueError('Candidate target vintages differ')
    wide = f.pivot(index=KEYS, columns='model', values='prediction').reindex(columns=MODELS[:5]).dropna()
    wide['COMBO_50_50'] = .5*wide.PHASE6C_DFM+.5*wide.U_MIDAS
    wide['COMBO_DEV_WEIGHT'] = weights['dfm']*wide.PHASE6C_DFM+weights['umidas']*wide.U_MIDAS
    actual = f.groupby(KEYS).actual.first().reindex(wide.index)
    long = wide.reset_index().melt(id_vars=KEYS,var_name='model',value_name='prediction')
    long = long.merge(actual.rename('actual').reset_index(),on=KEYS,validate='many_to_one')
    origin = f.groupby(KEYS).forecast_origin_date.first().reset_index()
    return long.merge(origin,on=KEYS,validate='many_to_one').sort_values(KEYS+['model']).reset_index(drop=True)


def metrics(f):
    rows=[]
    for h in ['H1','H2','H3','ALL']:
        block = f if h=='ALL' else f.loc[f.horizon.eq(h)]
        ar = block.loc[block.model.eq('AR1'),KEYS+['actual','prediction']].rename(columns={'prediction':'ar1'})
        for model in MODELS:
            g = block.loc[block.model.eq(model)].merge(ar,on=KEYS+['actual'],validate='one_to_one')
            error=g.actual-g.prediction
            sse=float((error**2).sum()); sst=float(((g.actual-g.actual.mean())**2).sum())
            ar_sse=float(((g.actual-g.ar1)**2).sum())
            rows.append(dict(model=model,horizon=h,n=len(g),r2=1-sse/sst if sst>0 else None,
                             r2_os_vs_ar1=1-sse/ar_sse if ar_sse>0 else None,
                             rmse=float(np.sqrt((error**2).mean())),mae=float(error.abs().mean()),bias=float(error.mean())))
    return pd.DataFrame(rows)


def shapley(groups, evaluate):
    """Exact all-subset Shapley; each subset evaluated once, independent of ordering."""
    n=len(groups)
    values={mask:np.asarray(evaluate([groups[i] for i in range(n) if mask & (1<<i)]),dtype=float)
            for mask in range(1<<n)}
    impacts={}
    for i,key in enumerate(groups):
        value=np.zeros_like(values[0])
        for mask in values:
            if mask & (1<<i):continue
            size=mask.bit_count()
            weight=factorial(size)*factorial(n-size-1)/factorial(n)
            value+=weight*(values[mask | (1<<i)]-values[mask])
        impacts[key]=value
    delta=values[(1<<n)-1]-values[0]
    total=sum(impacts.values(),np.zeros_like(delta))
    if not np.allclose(total,delta,rtol=0,atol=1e-10):
        raise ValueError('Shapley reconstruction failed')
    return impacts,delta


def news(old_info,new_info,root,old_origin,new_origin,old_fit,new_fit):
    """Separate observation news from refitting; never disguise refits as releases."""
    if (old_info['target'],old_info['horizon']) != (new_info['target'],new_info['horizon']):
        raise ValueError('Different target/horizon: no comparable real-time vintage')
    a=old_fit['panel'];b=new_fit['panel'].reindex(a.index)
    groups=[field for field in FIELDS if not np.allclose(a[field],b[field],equal_nan=True,rtol=0,atol=0)]
    # USD also has a pre-2019 channel in U-MIDAS.
    if old_info['benchmark_monthly']!=new_info['benchmark_monthly'] and 'usd_uzs' not in groups:
        groups.append('usd_uzs')
    if old_info['GDP']!=new_info['GDP']:groups.append('gdp_real_yoy')
    def evaluate(selected):
        info=deepcopy(old_info)
        p=a.copy()
        for key in selected:
            if key in FIELDS:p[key]=b[key]
        info['panel']=p.reset_index().rename(columns={'index':'month'}).to_dict('records')
        if 'usd_uzs' in selected:info['benchmark_monthly']=new_info['benchmark_monthly']
        if 'gdp_real_yoy' in selected:info['GDP']=new_info['GDP']
        # New GDP releases/revisions must satisfy the new cutoff; the old fit
        # stays fixed throughout every counterfactual subset.
        return fixed_prediction(info,root,new_origin,old_fit)
    impacts,delta=shapley(groups,evaluate)
    old=np.array([old_fit['dfm'],old_fit['umidas']]);new=np.array([new_fit['dfm'],new_fit['umidas']])
    fixed=evaluate(groups)
    if not np.allclose(evaluate([]),old,rtol=0,atol=1e-10):raise ValueError('Old fixed forecast failed')
    # Actual protocol re-estimates on each update. Report that channel explicitly.
    residual=new-fixed
    if np.max(abs(residual))>1e-12:impacts['PARAMETER_REESTIMATION']=residual
    if not impacts:impacts['NO_NEW_INFORMATION']=np.zeros(2)
    rows=[]
    for j,model in enumerate(['PHASE6C_DFM','U_MIDAS','COMBO_50_50']):
        v_old=float(old[j]) if j<2 else float(old.mean())
        v_new=float(new[j]) if j<2 else float(new.mean())
        contributions={key:float(val[j]) if j<2 else float(val.mean()) for key,val in impacts.items()}
        err=sum(contributions.values())-(v_new-v_old)
        if abs(err)>=1e-10:raise ValueError('News decomposition failed')
        for key,value in contributions.items():
            rows.append(dict(old_as_of_date=str(old_origin),new_as_of_date=str(new_origin),target_quarter=new_info['target'],
                             indicator=key,source_model=model,old_forecast=v_old,new_forecast=v_new,news_impact_pp=value,
                             total_revision_pp=v_new-v_old,reconstruction_error=err,
                             decomposition_type='parameter re-estimation' if key=='PARAMETER_REESTIMATION' else 'exact fixed-parameter Shapley',
                             updated_indicator_groups='|'.join(groups)))
    return rows


def append_history(path,row):
    previous=pd.read_csv(path,float_precision='round_trip') if path.exists() else pd.DataFrame()
    if len(previous):
        duplicate=previous.loc[previous.target_quarter.eq(row['target_quarter']) &
                               previous.input_data_fingerprint.eq(row['input_data_fingerprint']) &
                               previous.production_model.eq(row['production_model']) &
                               previous.final_forecast.eq(row['final_forecast'])]
        if len(duplicate):return previous,False
        comparable=previous.loc[previous.target_quarter.eq(row['target_quarter']) & previous.horizon.eq(row['horizon']) &
                                previous.production_model.eq(row['production_model'])]
        row=dict(row,change_from_previous=row['final_forecast']-float(comparable.iloc[-1].final_forecast) if len(comparable) else None)
        # Append bytes: never rewrite earlier history rows.
        pd.DataFrame([row],columns=previous.columns).to_csv(path,mode='a',header=False,index=False,float_format='%.17g')
    else:
        row=dict(row,change_from_previous=None)
        pd.DataFrame([row]).to_csv(path,index=False,float_format='%.17g')
    return pd.read_csv(path,float_precision='round_trip'),True
