"""Explicit GDP information boundary; no production or Phase 6B writes."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from uznowcast.models.data import quarter_end, horizon_month_end, effective_release_day


@dataclass(frozen=True)
class AvailableGDP:
    frame: pd.DataFrame
    origin: pd.Timestamp


def release_metadata(gdp, base_lag, historical=None):
    """Conservative repository rule, never reinterpret update dates as releases.

    Existing evidence: registry GDP lag 31; Phase 5A detect_target_quarter
    and models.data.effective_release_day conservative policy add 15 days.
    Use that 46-day rule for GDP in BOTH monthly lag experiments.
    """
    lag=effective_release_day(base_lag,'conservative') if base_lag is not None else None
    history=historical if historical is not None else pd.DataFrame(columns=['quarter','release_date','release_date_quality','release_date_source'])
    priority={'VERIFIED_ACTUAL_RELEASE_DATE':0,'ARCHIVED_PUBLICATION_DATE':1,'DOCUMENTED_RULE':2}
    rows=[]
    for q,value in gdp.items():
        following=str(pd.Period(q,freq='Q')+1)
        candidates=history.loc[history.quarter.eq(q) & history.release_date_quality.isin(priority)].copy()
        candidates['date']=pd.to_datetime(candidates.release_date,errors='coerce')
        candidates=candidates.loc[candidates.date.notna()]
        if len(candidates):
            candidates['priority']=candidates.release_date_quality.map(priority)
            selected=candidates.sort_values(['priority','date']).iloc[0]
            actual=cutoff=selected.date
            quality=selected.release_date_quality;source=selected.release_date_source
            verified=quality in ['VERIFIED_ACTUAL_RELEASE_DATE','ARCHIVED_PUBLICATION_DATE']
        else:
            actual=pd.NaT
            cutoff=quarter_end(q)+pd.Timedelta(days=lag) if lag is not None else pd.NaT
            quality='APPROXIMATE_FALLBACK' if lag is not None else 'UNKNOWN'
            source='registry GDP lag + Phase5A conservative policy; no historical date' if lag is not None else 'no qualifying evidence or documented fallback'
            verified=False
        rows.append(dict(quarter=q,gdp_value=float(value),release_date=actual,
                         release_date_source=source,
                         release_date_quality=quality,release_date_verified=verified,
                         available_date=cutoff,assumed_lag_days=lag,
                         H_reference_target=following,
                         available_for_H1=cutoff<=horizon_month_end(following,'H1'),
                         available_for_H2=cutoff<=horizon_month_end(following,'H2'),
                         available_for_H3=cutoff<=horizon_month_end(following,'H3'),
                         notes='available_date is a rule cutoff for fallback rows; current revised values, not historical vintages'))
    return pd.DataFrame(rows).set_index('quarter',drop=False)


def available_gdp_as_of(gdp, metadata, forecast_origin_date, *, target=None):
    """Gate dates first; exclude the target and later quarters second.

    Metadata explicitly distinguishes observed release_date from the assumed
    available_date. Unknown availability dates remain unavailable.
    """
    origin=pd.Timestamp(forecast_origin_date)
    if metadata.index.has_duplicates or gdp.index.has_duplicates:
        raise ValueError('duplicate_GDP_quarter')
    frame=metadata.reindex(gdp.index).copy()
    frame['value']=gdp
    frame['available_date']=pd.to_datetime(frame.available_date)
    if 'release_date' in frame:
        # An observed/documented date always overrides a fallback cutoff.
        trustworthy=frame.release_date_quality.isin(['VERIFIED_ACTUAL_RELEASE_DATE','ARCHIVED_PUBLICATION_DATE','DOCUMENTED_RULE'])
        known=pd.to_datetime(frame.release_date)
        frame.loc[trustworthy,'available_date']=known.loc[trustworthy]
    frame=frame.loc[frame.available_date.notna() & frame.available_date.le(origin) & frame.value.notna()]
    if target is not None:
        frame=frame.loc[frame.index < target]
    return AvailableGDP(frame.sort_index(),origin)


def assert_boundary(available, target, origin):
    if not isinstance(available,AvailableGDP):
        raise TypeError('bridge requires release-gated AvailableGDP, not unrestricted GDP')
    if available.origin != pd.Timestamp(origin):
        raise AssertionError('availability_origin_mismatch')
    frame=available.frame
    assert target not in frame.index, 'target_GDP_present'
    assert (frame.index < target).all(), 'future_GDP_present'
    assert frame.available_date.notna().all() and frame.available_date.le(pd.Timestamp(origin)).all(), 'unreleased_GDP_present'
    if 'release_date' in frame:
        observed=frame.release_date_quality.isin(['VERIFIED_ACTUAL_RELEASE_DATE','ARCHIVED_PUBLICATION_DATE','DOCUMENTED_RULE'])
        dates=pd.to_datetime(frame.loc[observed,'release_date'])
        assert dates.notna().all() and dates.le(pd.Timestamp(origin)).all(), 'unreleased_observed_GDP_present'
    assert not frame.index.has_duplicates


def bridge(factors,index,available_gdp,target,bridge_name,forecast_origin_date):
    """Same Phase 6B OLS bridges, with release-gated targets and regressors."""
    assert_boundary(available_gdp,target,forecast_origin_date)
    gdp=available_gdp.frame.value
    prior=str(pd.Period(target,freq='Q')-1)
    if bridge_name=='BRIDGE_B' and prior not in gdp.index:
        raise ValueError('PRIOR_QUARTER_GDP_NOT_AVAILABLE')
    fq=pd.DataFrame(factors,index=index).groupby(index.to_period('Q')).mean()
    counts=pd.Series(1,index=index).groupby(index.to_period('Q')).sum()
    fq=fq.loc[counts.eq(3)]
    quarters=[q for q in fq.index if str(q)<target and str(q) in gdp.index]
    if len(quarters)<12:
        raise ValueError('fewer_than_12_complete_GDP_training_quarters')
    x,y,used=[],[],[]
    for q in quarters:
        lag=str(q-1)
        row=[1.,*fq.loc[q].tolist()]
        if bridge_name=='BRIDGE_B':
            if lag not in gdp.index:
                continue
            row.append(float(gdp.loc[lag]))
        x.append(row);y.append(float(gdp.loc[str(q)]));used.append(str(q))
    x=np.asarray(x)
    if len(y)<12 or np.linalg.matrix_rank(x)<x.shape[1]:
        raise ValueError('insufficient_or_rank_deficient_bridge_training')
    coef=np.linalg.lstsq(x,y,rcond=None)[0]
    target_row=[1.,*fq.loc[pd.Period(target,freq='Q')].tolist()]
    if bridge_name=='BRIDGE_B':
        target_row.append(float(gdp.loc[prior]))
    return float(np.asarray(target_row)@coef),dict(n_GDP_quarters=len(y),bridge_coefficients=coef.tolist(),
                                                 bridge_condition=float(np.linalg.cond(x)),training_quarters=used,
                                                 lagged_quarters=[str(pd.Period(q,freq='Q')-1) for q in used] if bridge_name=='BRIDGE_B' else [])
