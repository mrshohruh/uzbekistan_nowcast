"""Unregularized balanced-panel PCA and published static factor selectors."""
from dataclasses import dataclass
import numpy as np
import pandas as pd


def penalties(n:int,t:int)->dict[str,float]:
    if min(n,t)<2:raise ValueError('Both panel dimensions must exceed one')
    m=min(n,t)
    return dict(ICp1=(n+t)/(n*t)*np.log(n*t/(n+t)),
                ICp2=(n+t)/(n*t)*np.log(m),ICp3=np.log(m)/m)


@dataclass
class Selection:
    summary: dict
    criteria: pd.DataFrame
    spectrum: pd.DataFrame
    loadings: pd.DataFrame
    scores: pd.DataFrame


def select(frame:pd.DataFrame,requested_cap:int=10,conservative:bool=True)->Selection:
    """X is finite and normalized using the corresponding origin's training.

    Demean within the retained observed rows; never impute or shrink eigenvalues.
    PC scores satisfy F'F/T=I. Residual MSE is SSE/(N*T), not residual df MSE.
    Numerical-null tails cannot be used as ER denominators or log residuals.
    """
    if frame.index.has_duplicates or frame.columns.has_duplicates:raise ValueError('Duplicate panel dimensions')
    x=frame.to_numpy(dtype=float)
    if not np.isfinite(x).all():raise ValueError('Formal criteria require genuinely complete finite panels')
    t,n=x.shape
    if min(t,n)<2:raise ValueError('Too few panel observations/variables')
    x=x-x.mean(axis=0)
    if (np.std(x,axis=0,ddof=1)<1e-10).any():raise ValueError('Constant balanced-sample variable')
    u,s,vt=np.linalg.svd(x,full_matrices=False)
    eig=s**2/t
    tolerance=max(float(eig[0])*1e-10,1e-12)
    rank=int(np.sum(eig>tolerance))
    if rank<2:raise ValueError('Rank <2: no nonsaturated positive factor candidate; selectors unavailable')
    dimension_cap=min(n,t)//2 if conservative else max(1,min(n,t)-2)
    maximum=min(requested_cap,dimension_cap,rank-1)
    if maximum<1:raise ValueError('No nonsaturated positive candidate')
    p=penalties(n,t)
    rows=[]
    for k in range(maximum+1):
        residual=float(eig[k:].sum()/n)
        if residual<=tolerance/n:raise ValueError('Nonpositive/numerically saturated residual variance')
        rows.append(dict(k=k,residual_variance=residual,**{name:float(np.log(residual)+k*cost) for name,cost in p.items()}))
    curve=pd.DataFrame(rows)
    # np.argmin/argmax choose the smallest k on exact ties.
    chosen={name:int(curve.iloc[np.argmin(curve[name].to_numpy())].k) for name in p}
    ratio=eig[:maximum]/eig[1:maximum+1]
    er=int(np.argmax(ratio)+1)
    spectrum=pd.DataFrame(dict(component=np.arange(1,len(eig)+1),eigenvalue=eig,
        explained_variance=eig/eig.sum(),cumulative_explained_variance=np.cumsum(eig)/eig.sum(),
        numerically_positive=eig>tolerance))
    spectrum['eigenvalue_ratio']=np.r_[ratio,np.full(len(eig)-len(ratio),np.nan)]
    signs=np.array([1. if vt[j,np.argmax(abs(vt[j]))]>=0 else -1. for j in range(maximum)])
    loading=vt[:maximum].T*(s[:maximum]/np.sqrt(t))*signs
    f=u[:,:maximum]*np.sqrt(t)*signs
    loads=pd.DataFrame([dict(original_variable=c,factor=j+1,loading=float(loading[i,j]),eigenvector=float(vt[j,i]*signs[j]),
        units='weighted origin-standardized input per population-unit-variance static PC') for i,c in enumerate(frame.columns) for j in range(maximum)])
    return Selection(dict(n_variables=n,n_months=t,numerical_rank=rank,k_max=maximum,
        **chosen,ER=er,methods_disagree=len(set([*chosen.values(),er]))>1,
        hits_search_boundary=any(k==maximum for k in [*chosen.values(),er]),
        er_positive_candidates=maximum,er_cannot_select_zero=True,
        penalty_ICp1=p['ICp1'],penalty_ICp2=p['ICp2'],penalty_ICp3=p['ICp3'],
        residual_normalization='SSE/(N*T)',eigenvalue_normalization='X_centered.T@X_centered/T',
        numerical_tolerance=tolerance,small_dimension_warning=min(n,t)<60),
        curve,spectrum,loads,pd.DataFrame(f,index=frame.index,columns=range(1,maximum+1)))
