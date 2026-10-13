"""Missing-data PCA + AR(2) Kalman DFM and parsimonious mixed-frequency bridge.

Two-step estimator, not full dynamic maximum likelihood. Missing cells are
latent estimates internal to estimation; original input observations stay null.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.linalg import eigh

from scripts.phase7d.data import release_gate

SPECS = {'DFM_ALL_1F': (1, False), 'DFM_ALL_2F': (2, False),
         'DFM_ALL_3F': (3, False), 'DFM_ALL_GROUPED': (2, True)}
MODELS = ['M0', 'U0', 'COMBO_50_50', 'AR1', 'AR2', *SPECS]
QUARTER_CACHE = {}


def standardize(frame, end, winsor=False, minimum=6):
    train = frame.loc[:end]
    means, scales = train.mean(), train.std(ddof=1)
    estimable = train.count().ge(minimum) & scales.gt(1e-10) & np.isfinite(scales)
    adjusted = frame.copy()
    if winsor:
        adjusted = adjusted.clip(lower=train.quantile(.01), upper=train.quantile(.99), axis=1)
    z = (adjusted-means)/scales
    z.loc[:, ~estimable] = np.nan
    return z, means, scales, estimable


def missing_pca(z: np.ndarray, k: int, weights: np.ndarray, maxiter=1000, tolerance=1e-6, shrinkage=2.):
    """Rank-k soft-impute minimizes observed weighted SSE + nuclear penalty.

At each step missing cells take the preceding rank-k reconstruction and the
    best regularized rank-k matrix is re-estimated. Singular values shrink by
    the fixed training-independent penalty 2, bounding unidentified missing
    blocks instead of allowing missing reconstructions to grow without limit.
    This is generalized missing-data PCA,
not interpolation. Only the origin's training sample participates.
"""
    observed = np.isfinite(z)
    filled = np.where(observed, z, 0.) * weights
    losses = []; objectives=[]; change = np.inf; objective_change=np.inf
    if k >= min(z.shape):
        raise ValueError('Too few rows/columns for factor dimension')
    for iteration in range(maxiter):
        eig, u = eigh(filled@filled.T, subset_by_index=[len(filled)-k, len(filled)-1], check_finite=False)
        u = u[:, ::-1]
        singular=np.sqrt(np.maximum(eig[::-1],0.))
        shrunk=np.maximum(singular-shrinkage,0.)
        if np.count_nonzero(shrunk>1e-8)!=k:
            raise ValueError('Regularized panel has insufficient nonzero factor dimensions')
        factors = u * np.sqrt(len(filled))
        loadings = filled.T@factors/len(filled)*(shrunk/np.maximum(singular,1e-12))
        reconstruction = factors@loadings.T
        loss = float(((filled-reconstruction)[observed]**2).sum())
        losses.append(loss)
        objectives.append(loss+2*shrinkage*shrunk.sum())
        objective_change=abs(objectives[-1]-objectives[-2])/max(objectives[-2],1.) if len(objectives)>1 else np.inf
        replacement = np.where(observed, z*weights, reconstruction)
        change = float(np.linalg.norm(replacement-filled)/max(np.linalg.norm(filled), 1.))
        filled = replacement
        if change < tolerance or (iteration>=20 and objective_change<tolerance):
            break
    loadings = loadings / weights[:, None]
    signs = np.array([1. if loadings[np.argmax(abs(loadings[:, j])), j]>=0 else -1. for j in range(k)])
    factors *= signs; loadings *= signs
    variance = np.nanmean((z-factors@loadings.T)**2, axis=0)
    # A floor guards near-duplicate predictors against extreme precision.
    noise = np.maximum(variance, .15) / weights**2
    return factors, loadings, noise, dict(pca_iterations=iteration+1,
        pca_converged=bool(change<tolerance or objective_change<tolerance), pca_relative_change=change,
        pca_relative_objective_change=objective_change,
        weighted_observed_sse=losses[-1], penalized_objective=objectives[-1],pca_nuclear_penalty=shrinkage,
        objective_monotone=bool(np.all(np.diff(objectives)<=1e-7)),
        estimator='ITERATIVE_MISSING_PCA_AR2_KALMAN_TWO_STEP')


@dataclass
class StateFit:
    loadings: np.ndarray
    noise: np.ndarray
    transition: np.ndarray
    innovation: np.ndarray
    k: int


def dynamics(factors, loadings, noise):
    k = factors.shape[1]
    a = np.zeros((2*k, 2*k)); a[k:, :k] = np.eye(k)
    innovations = []; stabilized = []
    for j in range(k):
        x = np.column_stack([factors[1:-1,j], factors[:-2,j]])
        y = factors[2:,j]
        coef = np.linalg.solve(x.T@x+np.eye(2), x.T@y)
        original = coef.copy()
        while max(abs(np.linalg.eigvals([[coef[0],coef[1]],[1.,0.]])))>=.98:
            coef *= .95
        a[j,j], a[j,k+j] = coef
        innovations.append(max(float(np.mean((y-x@coef)**2)), .01))
        stabilized.append(bool(not np.array_equal(original,coef)))
    innovation = np.zeros((2*k,2*k)); innovation[:k,:k] = np.diag(innovations)
    return StateFit(loadings, noise, a, innovation, k), stabilized


def filter_states(z, fit: StateFit, smooth=False):
    """Information-form measurement update costs O(N k^2), not O(N^3)."""
    d = 2*fit.k; state = np.zeros(d); covariance = np.eye(d)*10
    states=[]; covs=[]; predictions=[]; prediction_covs=[]
    for row in np.asarray(z):
        predicted = fit.transition@state
        pcov = fit.transition@covariance@fit.transition.T+fit.innovation+np.eye(d)*1e-9
        observations = np.isfinite(row)
        h = np.column_stack([fit.loadings[observations], np.zeros((int(observations.sum()),fit.k))])
        precision = 1/fit.noise[observations]
        if observations.any():
            inverse = np.linalg.inv(pcov)
            covariance = np.linalg.inv(inverse+h.T@(precision[:,None]*h))
            state = covariance@(inverse@predicted+h.T@(precision*row[observations]))
        else:
            state, covariance = predicted, pcov
        covariance = (covariance+covariance.T)/2
        states.append(state.copy()); covs.append(covariance.copy())
        predictions.append(predicted); prediction_covs.append(pcov)
    states = np.array(states)
    if smooth:
        # RTS smoothing confined to training observations, never used for target-quarter states.
        for t in range(len(states)-2,-1,-1):
            gain = covs[t]@fit.transition.T@np.linalg.pinv(prediction_covs[t+1])
            states[t] += gain@(states[t+1]-predictions[t+1])
    return states[:,:fit.k]


def quarterly_covariates(quarterly, inventory, target, horizon, origin=None, extra_days=0):
    """At each row's simulated origin use q-1 only, or a causal AR(1) projection.

No actual target-quarter explanatory observation enters the bridge, even when
the workbook later contains it. A not-yet-released q-1 value is predicted from
earlier released observations; no realized quarter is repeated into months.
"""
    from uznowcast.models.data import horizon_month_end
    cutoff = pd.Timestamp(origin) if origin is not None else horizon_month_end(str(target), horizon)
    lag_values=inventory.set_index('original_label').publication_lag_days.reindex(quarterly.columns)
    key=(tuple(quarterly.columns),tuple(quarterly.index.astype(str)),quarterly.to_numpy().tobytes(),
         tuple(lag_values),str(target),horizon,str(cutoff),extra_days)
    if key in QUARTER_CACHE:
        values,audit=QUARTER_CACHE[key]
        return values.copy(),[dict(row) for row in audit]
    visible = release_gate(quarterly, inventory, cutoff, extra_days)
    values={}; audit=[]; prior=target-1
    for c in quarterly:
        history = visible.loc[visible.index<=prior,c].dropna()
        n = len(history)
        if prior in history.index:
            value = float(history.loc[prior]); status='RELEASED_Q_MINUS_1'
        elif n >= 4:
            # Estimate on adjacent pairs only; respect gaps and actual period distance.
            pairs = visible[c].shift().to_frame('lag').join(visible[c].rename('y')).loc[:prior].dropna()
            if len(pairs)>=3:
                x=np.column_stack([np.ones(len(pairs)),pairs.lag.to_numpy()])
                coef=np.linalg.solve(x.T@x+np.diag([0.,1.]),x.T@pairs.y.to_numpy())
                coef[1]=np.clip(coef[1],-.95,.95)
                coef[0]=history.mean()*(1-coef[1])
                value=float(history.iloc[-1])
                for _ in range(prior.ordinal-history.index[-1].ordinal):
                    value=float(coef[0]+coef[1]*value)
                status='TRAINING_ONLY_AR1_PROJECTION_Q_MINUS_1'
            else:
                value=float(history.mean());status='RELEASED_HISTORY_MEAN_PRIOR'
        else:
            value=np.nan;status='INSUFFICIENT_RELEASED_QUARTERLY_HISTORY'
        values[c]=value
        audit.append(dict(original_label=c,frequency='Q',status=status,available_history=n,
            latest_available_period=str(history.index[-1]) if n else None,
            requested_period=str(prior),forecast_origin=str(cutoff),model_input_value=value))
    result=pd.Series(values)
    QUARTER_CACHE[key]=(result.copy(),[dict(row) for row in audit])
    return result, audit


def ridge_bridge(factors, quarterly, inventory, gdp, target, horizon, origin, extra_days=0):
    fq = factors.groupby(factors.index.to_period('Q')).mean()
    quarter_target = pd.Period(target,'Q')
    columns=[*factors.columns, 'GDP_LAG1', *quarterly.columns]
    rows=[]; outcomes=[]; quarters=[]
    for q in fq.index:
        if q>=quarter_target or str(q) not in gdp.index or str(q-1) not in gdp.index:
            continue
        v,_ = quarterly_covariates(quarterly,inventory,q,horizon,extra_days=extra_days)
        rows.append([*fq.loc[q],float(gdp.loc[str(q-1)]),*v])
        outcomes.append(float(gdp.loc[str(q)]));quarters.append(str(q))
    if len(outcomes)<12:
        raise ValueError('Fewer than 12 released GDP bridge training quarters')
    prior=str(quarter_target-1)
    if prior not in gdp.index:
        raise ValueError('Prior GDP quarter unavailable')
    v,qa = quarterly_covariates(quarterly,inventory,quarter_target,horizon,origin,extra_days)
    x = pd.DataFrame(rows,columns=columns)
    current = pd.Series([*fq.loc[quarter_target],float(gdp.loc[prior]),*v],index=columns)
    mean=x.mean().fillna(0);scale=x.std(ddof=1).where(lambda s:s.gt(1e-8),1).fillna(1)
    estimable=x.count().ge(4)
    standardized=(x-mean)/scale
    # Internal neutral Gaussian prior for an unavailable bridge covariate;
    # missing indicators distinguish it from a measured value at its mean.
    missing=standardized.isna().astype(float)
    standardized=standardized.fillna(0)
    standardized.loc[:,~estimable]=0
    design=np.column_stack([np.ones(len(x)),standardized,missing])
    tx=np.r_[1.,((current-mean)/scale).fillna(0).where(estimable,0),current.isna().astype(float)]
    y=np.asarray(outcomes)
    penalty=np.diag(np.r_[0.,np.full(len(columns),10.),np.full(len(columns),20.)])
    coef=np.linalg.solve(design.T@design+penalty,design.T@y)
    prediction=float(tx@coef)
    residual=y-design@coef
    for item in qa:
        c=item['original_label'];item.update(bridge_coefficient=float(coef[1+columns.index(c)]/scale[c]),
            bridge_estimable=bool(estimable[c]),bridge_training_nonmissing=int(x[c].count()))
    return prediction,qa,dict(n_gdp_training=len(y),bridge_ridge_penalty=10.,
        bridge_missing_indicator_penalty=20., bridge_training_quarters=';'.join(quarters),
        bridge_residual_rmse=float(np.sqrt(np.mean(residual**2))),
        bridge_parameters=len(coef), quarterly_estimable=int(estimable.iloc[-len(quarterly.columns):].sum()) if len(quarterly.columns) else 0)


def estimate(inputs, model, target, horizon, origin, gdp, exclude=(), winsor=False,
             exclude_pandemic=False, extra_days=0, cache=None):
    from uznowcast.models.data import quarter_start, quarter_end
    k, balanced=SPECS[model]
    inv=inputs.inventory;dictionary=inv.set_index('original_label')
    panel=inputs.monthly.drop(columns=[c for c in inputs.monthly if dictionary.at[c,'group'] in exclude])
    q=inputs.quarterly.drop(columns=[c for c in inputs.quarterly if dictionary.at[c,'group'] in exclude])
    end=quarter_start(target)-pd.Timedelta(days=1)
    dates=pd.date_range(panel.index.min().to_timestamp('M'),quarter_end(target),freq='ME')
    visible=release_gate(panel,inv,origin,extra_days)
    visible.index=visible.index.to_timestamp('M');visible=visible.reindex(dates)
    if exclude_pandemic:
        visible.loc[visible.index.year.isin([2020,2021])]=np.nan
    z,mean,scale,estimable=standardize(visible,end,winsor)
    columns=estimable.index[estimable].tolist()
    train=z.loc[:end,columns].copy()
    if exclude_pandemic:
        train.loc[train.index.year.isin([2020,2021])]=np.nan
    if len(columns)<k+1 or len(train)<36:
        raise ValueError('Insufficient estimable panel')
    groups=dictionary.group.loc[columns]
    counts=groups.value_counts()
    weights=np.array([1/np.sqrt(counts[g]) for g in groups]) if balanced else np.ones(len(columns))
    key=(model,target,tuple(exclude),winsor,exclude_pandemic,extra_days,
         pd.util.hash_pandas_object(train,index=True).to_numpy().tobytes())
    cached=cache.get(key) if cache is not None else None
    if cached is None:
        f,l,r,diag=missing_pca(train.to_numpy(),k,weights)
        state,stabilized=dynamics(f,l,r)
        diag.update(ar2_stabilized=stabilized,
            transition_spectral_radius=float(max(abs(np.linalg.eigvals(state.transition)))))
        cached=(state,diag)
        if cache is not None:cache[key]=cached
    state,diag=cached
    path=filter_states(z[columns],state)
    # Factor signals: training scale only, one-sided states; positive largest loading.
    training_states=path[:len(train)]
    fmean=training_states.mean(axis=0);fscale=training_states.std(axis=0,ddof=1)
    fscale=np.maximum(fscale,1e-8)
    factors=pd.DataFrame((path-fmean)/fscale,index=z.index,columns=[f'factor_{i+1}' for i in range(k)])
    gd=gdp.copy()
    if exclude_pandemic:
        gd=gd.loc[~pd.PeriodIndex(gd.index,freq='Q').year.isin([2020,2021])]
    prediction,qa,bridge=ridge_bridge(factors,q,inv,gd,target,horizon,origin,extra_days)
    loads=[];availability=[]
    energy=(state.loadings*fscale)**2
    total=energy.sum(axis=0)
    for c in panel:
        history=visible.loc[:end,c]
        status='ESTIMATED' if estimable[c] else 'NOT_IDENTIFIABLE_AT_ORIGIN_FEWER_THAN_6_OR_CONSTANT'
        availability.append(dict(original_label=c,frequency='M',status=status,
            available_history=int(history.count()),latest_available_period=str(visible[c].last_valid_index()),
            requested_period=target,forecast_origin=str(origin),model_input_value=None))
        for j in range(k):
            pos=columns.index(c) if c in columns else None
            loads.append(dict(original_label=c,group=dictionary.at[c,'group'],
                factor=f'factor_{j+1}',loading=float(state.loadings[pos,j]*fscale[j]) if pos is not None else np.nan,
                loading_energy_share=float(energy[pos,j]/total[j]) if pos is not None else 0.,
                group_weight=float(weights[pos]) if pos is not None else None,status=status))
    availability.extend(qa)
    for a in qa:
        loads.append(dict(original_label=a['original_label'],group=dictionary.at[a['original_label'],'group'],
            factor='QUARTERLY_BRIDGE',loading=a['bridge_coefficient'],loading_energy_share=None,
            group_weight=None,status=a['status'],units='GDP pp per transformed quarterly input unit'))
    diag=dict(diag,**bridge,n_monthly_declared=len(panel.columns),n_monthly_estimable=len(columns),
        n_quarterly_declared=len(q.columns), n_declared=len(panel.columns)+len(q.columns),
        n_training_months=len(train),n_observed_cells=int(train.count().sum()),
        n_missing_cells=int(train.isna().sum().sum()),factor_count=k,group_balanced=balanced,
        currently_observed_predictors=int(visible.loc[visible.index.to_period('Q')==pd.Period(target,'Q')].notna().any().sum()),
        n_effective_predictors=len(columns)+bridge['quarterly_estimable'])
    return prediction,factors,pd.DataFrame(loads),z,pd.DataFrame(availability),diag
