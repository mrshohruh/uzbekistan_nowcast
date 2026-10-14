"""Separate economic measurement factors and a release-aware GDP ridge bridge."""
from dataclasses import dataclass
import numpy as np
import pandas as pd

from scripts.phase7d.data import release_gate
from scripts.phase7d.models import standardize, missing_pca, dynamics, filter_states, quarterly_covariates
from scripts.phase7d.run import information_gdp
from scripts.phase7e.grouping import BLOCKS, anchors, core_columns, family
from uznowcast.models.data import horizon_month_end

SPECS = {'E1': ['F1', 'F2', 'F3', 'F4'], 'E2': list(BLOCKS),
         'E3': list(BLOCKS), 'E4': list(BLOCKS), 'ECONOMIC_CORE': list(BLOCKS)}
MIN_HISTORY = 12
MIN_BLOCK_MONTHS = 12
MIN_BRIDGE_QUARTERS = 12
MIN_FACTOR_QUARTERS = 4
LAG_CACHE = {}


@dataclass
class Block:
    path: pd.Series
    loadings: pd.DataFrame
    availability: pd.DataFrame
    diagnostics: dict


@dataclass
class Result:
    prediction: float
    factors: pd.DataFrame
    loadings: pd.DataFrame
    availability: pd.DataFrame
    diagnostics: pd.DataFrame
    contributions: pd.DataFrame
    bridge: dict


def orient(f, l, anchor_position):
    if abs(l[anchor_position, 0]) < 1e-8: raise ValueError('Orientation anchor loading unidentified')
    sign = 1. if l[anchor_position, 0] > 0 else -1.
    return f*sign, l*sign


def block_factor(inputs, grouping, block, target, origin, core=False, extra_days=0, winsor=False, configuration=None):
    """Missing observations remain null; no factor before measured block onset."""
    columns = core_columns(inputs.monthly)[block] if core else grouping.loc[grouping.economic_group.eq(block), 'original_label'].tolist()
    if configuration is not None:
        columns = configuration.columns(inputs.monthly, grouping, block, core)
    quarter = pd.Period(target, 'Q')
    end = (quarter-1).end_time.normalize()
    dates = pd.date_range(inputs.monthly.index.min().to_timestamp('M'), quarter.end_time.normalize(), freq='ME')
    visible = release_gate(inputs.monthly[columns], inputs.inventory, origin, extra_days)
    visible.index = visible.index.to_timestamp('M')
    visible = visible.reindex(dates)
    z, means, scales, estimable = standardize(visible, end, winsor=winsor, minimum=MIN_HISTORY)
    usable = estimable.index[estimable].tolist()
    av = pd.DataFrame([dict(original_label=c, economic_group=block, frequency='M',
        available_history=int(visible.loc[:end, c].count()), latest_available_period=str(visible[c].last_valid_index()),
        target_quarter_observed_months=int(visible.loc[visible.index.to_period('Q')==quarter, c].count()),
        status='ESTIMATED' if estimable[c] else 'UNIDENTIFIABLE_FEWER_THAN_12_OR_CONSTANT',
        training_mean=means[c], training_scale=scales[c], release_lag_extra_days=extra_days) for c in columns])
    if len(usable) < 2: raise ValueError(f'{block}: fewer than two indicators with 12 released training observations')
    full_train = z.loc[:end, usable]
    observed_months = full_train.notna().sum(axis=1).ge(2)
    if observed_months.sum() < MIN_BLOCK_MONTHS: raise ValueError(f'{block}: fewer than 12 genuinely co-observed months')
    onset = observed_months.index[observed_months][0]
    train = full_train.loc[onset:]
    groups = pd.Series([family(c, block) for c in usable], index=usable)
    counts = groups.value_counts()
    # Mean squared weight is one; each family has equal total squared precision.
    weights = np.array([np.sqrt(len(usable)/(len(counts)*counts[g])) for g in groups])
    f, l, noise, diag = missing_pca(train.to_numpy(), 1, weights)
    if not diag['pca_converged'] or not diag['objective_monotone']:
        raise ValueError(f'{block}: missing-data PCA did not converge monotonically')
    anchor = anchors(usable, block) if configuration is None else configuration.anchor(usable, block)
    f, l = orient(f, l, usable.index(anchor))
    fit, stabilized = dynamics(f, l, noise)
    path = filter_states(z.loc[onset:, usable].to_numpy(), fit)[:, 0]
    train_path = path[:len(train)]
    center, scale = train_path.mean(), train_path.std(ddof=1)
    if scale < 1e-8: raise ValueError(f'{block}: degenerate filtered state variance')
    signal = pd.Series((path-center)/scale, index=z.loc[onset:].index, name=block).reindex(dates)
    energy = (l[:, 0]*scale)**2
    effective = (energy.sum()**2/(energy**2).sum())
    loading = pd.DataFrame([dict(original_label=c, economic_group=block, factor=block,
        loading=float(l[usable.index(c), 0]*scale) if c in usable else np.nan,
        loading_energy_share=float(energy[usable.index(c)]/energy.sum()) if c in usable else 0.,
        family=family(c, block), measurement_weight=float(weights[usable.index(c)]) if c in usable else np.nan,
        anchor=c==anchor, status='ESTIMATED' if c in usable else 'NOT_IDENTIFIABLE_AT_ORIGIN',
        units='standardized predictor units per training-standardized latent factor') for c in columns])
    corr = train.corr(min_periods=12).to_numpy()
    upper = corr[np.triu_indices(len(corr), 1)]
    comparable = train_path.shape[0]
    diag.update(economic_group=block, factor=block, anchor=anchor, n_declared=len(columns),
        n_estimable=len(usable), n_coobserved_months=int(observed_months.sum()),
        block_onset=str(onset.date()), n_training_months=len(train),
        observed_cells=int(train.count().sum()), missing_cells=int(train.isna().sum().sum()),
        observed_share=float(train.notna().to_numpy().mean()), training_factor_mean=float(center),
        training_factor_scale=float(scale), ar1=float(fit.transition[0,0]), ar2=float(fit.transition[0,1]),
        spectral_radius=float(max(abs(np.linalg.eigvals(fit.transition)))), stabilized=bool(stabilized[0]),
        mean_pairwise_correlation=float(np.nanmean(upper)), median_absolute_correlation=float(np.nanmedian(abs(upper))),
        loading_concentration=float((energy/energy.sum())@ (energy/energy.sum())),
        effective_loading_count=float(effective), positive_loading_share=float((l[:,0]>0).mean()),
        filter_method='ONE_SIDED_NO_SMOOTHING', training_cutoff=str(end.date()),
        target_observed_cells=int(visible.loc[visible.index.to_period('Q')==quarter].count().sum()),
        total_filtered_months=comparable)
    return Block(signal, loading, av, diag)


def hierarchical(base, target):
    """Two-stage global plus orthogonal block residuals; F5 is reference block.

    No independent causal-shock identification is claimed. Orthogonality is a
    training-only projection restriction, not a jointly fitted measurement MLE.
    """
    end = (pd.Period(target,'Q')-1).end_time.normalize()
    train = base.loc[:end]
    onset = train.index[train.notna().sum(axis=1).ge(2)][0]
    train = train.loc[onset:]
    f,l,r,diag = missing_pca(train.to_numpy(), 1, np.ones(base.shape[1]))
    if not diag['pca_converged']: raise ValueError('E3 global factor nonconvergence')
    f,l = orient(f,l,list(base.columns).index('F1'))
    fit, stabilized = dynamics(f,l,r)
    global_path = filter_states(base.loc[onset:].to_numpy(),fit)[:,0]
    m = global_path[:len(train)].mean();s=global_path[:len(train)].std(ddof=1)
    global_path = pd.Series((global_path-m)/s,index=base.loc[onset:].index).reindex(base.index)
    out = pd.DataFrame({'GLOBAL':global_path})
    rows=[]
    for c in base:
        pair=pd.concat([base[c],global_path.rename('global')],axis=1).loc[:end].dropna()
        if len(pair)<12: raise ValueError(f'E3 {c}: insufficient global projection history')
        x=np.column_stack([np.ones(len(pair)),pair['global']])
        intercept,slope=np.linalg.lstsq(x,pair[c],rcond=None)[0]
        residual=base[c]-intercept-slope*global_path
        scale=residual.loc[:end].std(ddof=1)
        if scale<1e-6: raise ValueError(f'E3 {c}: no identifiable block residual')
        covariance=float(np.cov(pair['global'],residual.loc[pair.index],ddof=1)[0,1])
        if abs(covariance)>1e-8: raise ValueError('E3 training projection restriction failed')
        if c!='F5': out[c+'_RESIDUAL']=residual/scale
        rows.append(dict(block=c,global_loading=float(slope),projection_intercept=float(intercept),
            residual_scale=float(scale),global_residual_training_covariance=covariance,
            residual_in_bridge=c!='F5',reference_block=c=='F5'))
    return out,rows


def available_lag(events, q, horizon, origin=None):
    cutoff=origin if origin is not None else horizon_month_end(str(q),horizon)
    key=(pd.util.hash_pandas_object(events,index=True).to_numpy().tobytes(),str(q),str(cutoff))
    if key in LAG_CACHE: return LAG_CACHE[key]
    _,hist=information_gdp(events,str(q),cutoff)
    hist=hist.loc[hist.index<str(q)].dropna()
    if hist.empty: return np.nan,None
    result=float(hist.iloc[-1]),str(hist.index[-1])
    LAG_CACHE[key]=result
    return result


def bridge(factors, inputs, gdp, events, target, horizon, origin, quarterly=False, extra_days=0):
    target=pd.Period(target,'Q')
    # Require >=two genuine monthly factor values per quarter, not pre-onset priors.
    grouped=factors.groupby(factors.index.to_period('Q'))
    fq=grouped.mean().where(grouped.count().ge(2))
    cov=inputs.quarterly if quarterly else inputs.quarterly.iloc[:,:0]
    columns=[*factors.columns,'AVAILABLE_GDP_LAG',*cov.columns]
    rows=[];y=[];quarters=[]
    for q in fq.index:
        if q>=target or str(q) not in gdp.index or pd.isna(gdp.loc[str(q)]): continue
        lag,_=available_lag(events,q,horizon)
        if not np.isfinite(lag): continue
        values,_=quarterly_covariates(cov,inputs.inventory,q,horizon,extra_days=extra_days)
        rows.append([*fq.loc[q],lag,*values]);y.append(float(gdp.loc[str(q)]));quarters.append(str(q))
    x=pd.DataFrame(rows,columns=columns)
    if len(x)<MIN_BRIDGE_QUARTERS: raise ValueError('Fewer than 12 released GDP bridge training quarters')
    if (x[list(factors.columns)].count()<MIN_FACTOR_QUARTERS).any():
        raise ValueError('At least one block has fewer than four genuinely observed factor quarters in bridge')
    lag,lag_period=available_lag(events,target,horizon,origin)
    values,qa=quarterly_covariates(cov,inputs.inventory,target,horizon,origin,extra_days)
    if not np.isfinite(lag): raise ValueError('No released lagged GDP benchmark')
    current=pd.Series([*fq.loc[target],lag,*values],index=columns)
    if current[list(factors.columns)].isna().any(): raise ValueError('Unavailable current block factor')
    means=x.mean().fillna(0);scales=x.std(ddof=1).where(lambda s:s.gt(1e-8),1.).fillna(1.)
    estimable=x.count().ge(4)
    z=(x-means)/scales
    missing=z.isna().astype(float)
    z=z.fillna(0)
    z.loc[:,~estimable]=0
    design=np.column_stack([np.ones(len(x)),z,missing])
    tx=np.r_[1.,((current-means)/scales).fillna(0).where(estimable,0),current.isna().astype(float)]
    penalty=np.diag(np.r_[0.,np.full(len(columns),10.),np.full(len(columns),20.)])
    coef=np.linalg.solve(design.T@design+penalty,design.T@np.asarray(y))
    prediction=float(tx@coef)
    contributions=[dict(component='Intercept',value=float(coef[0]),signal=1.,coefficient=float(coef[0]),units='GDP percentage points')]
    for i,c in enumerate(columns):
        contributions.append(dict(component=c,value=float(tx[i+1]*coef[i+1]),signal=float(current[c]) if pd.notna(current[c]) else np.nan,
            standardized_bridge_signal=float(tx[i+1]),coefficient=float(coef[i+1]),units='GDP percentage points',
            signal_units='training-standardized latent factor' if c in factors else 'GDP pp' if c=='AVAILABLE_GDP_LAG' else inputs.inventory.set_index('original_label').at[c,'clean_unit']))
        contributions.append(dict(component='MISSING_'+c,value=float(tx[1+len(columns)+i]*coef[1+len(columns)+i]),signal=float(pd.isna(current[c])),coefficient=float(coef[1+len(columns)+i]),units='GDP percentage points'))
    error=prediction-sum(r['value'] for r in contributions)
    if abs(error)>1e-10: raise ValueError('GDP decomposition failed')
    for a in qa:
        a['economic_group']='Q_BRIDGE';a['status']=a['status'] if estimable[a['original_label']] else 'UNIDENTIFIABLE_BRIDGE_NEUTRAL_PRIOR'
    diagnostic=dict(n_gdp_training=len(y),bridge_training_quarters=';'.join(quarters),bridge_ridge_penalty=10.,
        missing_indicator_penalty=20.,lagged_gdp_period=lag_period,lagged_gdp_value=lag,
        decomposition_error=error,bridge_parameters=len(coef),quarterly_declared=len(cov.columns),
        quarterly_estimable=int(estimable.reindex(cov.columns).sum()),
        factor_training_quarter_counts=x[list(factors.columns)].count().to_dict(),
        pre_service_rows_are_null=True, target_definition='CUMULATIVE_REAL_YTD_GDP_YOY_PERCENT')
    return prediction,pd.DataFrame(contributions),qa,diagnostic


def estimate(inputs, grouping, model, target, horizon, origin, gdp, events, cache=None, extra_days=0, winsor=False, configuration=None):
    core=model=='ECONOMIC_CORE'
    parts=[]
    for block in SPECS[model]:
        key=(str(target),str(origin),block,core,extra_days,winsor)
        if configuration is not None:
            key = (*key, configuration.cache_token)
        if cache is not None and key in cache:
            part=cache[key]
            if isinstance(part,str): raise ValueError(part)
        else:
            try: part=block_factor(inputs,grouping,block,target,origin,core,extra_days,winsor,configuration)
            except (ValueError,np.linalg.LinAlgError) as exc:
                if cache is not None: cache[key]=str(exc)
                raise
            if cache is not None: cache[key]=part
        parts.append(part)
    factors=pd.concat([p.path for p in parts],axis=1)
    hierarchy=[]
    if model=='E3': factors,hierarchy=hierarchical(factors,target)
    prediction,contributions,qa,diag=bridge(factors,inputs,gdp,events,target,horizon,origin,model=='E4',extra_days)
    diag['hierarchical_projection']=hierarchy
    av=pd.concat([p.availability for p in parts]+([pd.DataFrame(qa)] if qa else []),ignore_index=True)
    return Result(prediction,factors,pd.concat([p.loadings for p in parts],ignore_index=True),av,
                  pd.DataFrame([p.diagnostics for p in parts]),contributions,diag)
