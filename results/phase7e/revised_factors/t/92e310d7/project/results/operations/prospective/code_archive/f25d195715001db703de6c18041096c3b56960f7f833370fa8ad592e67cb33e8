"""Only evidenced publication events enter GDP information sets."""
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class VintageGDP:
    frame: pd.DataFrame
    origin: pd.Timestamp
    timing_rule: str

def validate_vintages(events):
    required={'quarter','publication_date','value','source_url','sha256','value_verified','date_verified','time_verified','publication_time'}
    if not required.issubset(events.columns):
        raise ValueError('Incomplete vintage schema')
    if events.duplicated(['quarter','publication_date','publication_time']).any():
        raise ValueError('Duplicate or conflicting vintage event')
    if not events.quarter.str.fullmatch(r'\d{4}Q[1-4]').all():
        raise ValueError('Invalid GDP quarter')
    if not events.source_url.str.startswith(('https://stat.uz/','https://siat.stat.uz/','https://api.siat.stat.uz/')).all():
        raise ValueError('Unofficial GDP source')
    for row in events.itertuples():
        date=pd.Timestamp(row.publication_date)
        if date.normalize()<=pd.Period(row.quarter,freq='Q').end_time.normalize():
            raise ValueError('GDP publication before reference quarter ends')
        if row.time_verified and pd.isna(row.publication_time):
            raise ValueError('Verified time missing')

def available_gdp_vintage_as_of(events,origin,*,target,timing_rule='STRICT'):
    """Latest DOCUMENTED eligible vintage; unknown intervening revisions stay unknown.

    Origin is the frozen calendar date at 00:00 Asia/Tashkent, unless an explicit
    clock time is supplied. Date-only equality uses the requested sensitivity.
    No master GDP values or release-lag fallbacks enter this function.
    """
    validate_vintages(events)
    if timing_rule not in {'STRICT','PERMISSIVE_END_OF_DAY'}:
        raise ValueError('Unknown timing rule')
    origin=pd.Timestamp(origin)
    if origin.tzinfo is None:
        local=origin.tz_localize('Asia/Tashkent')
    else:
        local=origin.tz_convert('Asia/Tashkent')
    records=[]
    for row in events.to_dict('records'):
        if row['quarter']>=target or not row['value_verified'] or not row['date_verified']:
            continue
        if row.get('quality')=='SOURCE_CHART_ORDER_SUSPECT':
            continue
        date=pd.Timestamp(row['publication_date']).normalize()
        same=date.date()==local.date()
        if row['time_verified']:
            stamp=pd.Timestamp(row['publication_time'])
            if stamp.tzinfo is None:
                raise ValueError('Publication timestamp lacks timezone')
            eligible=stamp.tz_convert('Asia/Tashkent')<local
        else:
            eligible=date.date()<local.date() or (same and timing_rule=='PERMISSIVE_END_OF_DAY')
        if eligible:
            row['available_date']=date
            row['published_value']=row['value']
            row['same_day_status']='SAME_DAY_TIME_UNKNOWN' if same and not row['time_verified'] else 'AVAILABLE'
            records.append(row)
    columns=list(events.columns)+['available_date','published_value','same_day_status']
    frame=pd.DataFrame(records,columns=columns)
    if len(frame):
        frame=frame.sort_values(['quarter','publication_date','publication_time'],na_position='first').drop_duplicates('quarter',keep='last')
    frame=frame.set_index('quarter').sort_index()
    result=VintageGDP(frame,origin,timing_rule)
    assert_boundary(result,target)
    return result

def assert_boundary(available,target):
    f=available.frame
    assert not f.index.has_duplicates
    assert (f.index<target).all(),'Target/future GDP leaked'
    assert f.value_verified.all() and f.date_verified.all(),'Unverified GDP leaked'
    assert pd.to_datetime(f.publication_date).dt.date.le(available.origin.date()).all(),'Later vintage leaked'
    assert f.source_url.notna().all() and f.sha256.notna().all()
    assert np.isclose(f.value.to_numpy(dtype=float),f.published_value.to_numpy(dtype=float),rtol=0,atol=0).all(),'Published GDP value substituted'
    local=available.origin.tz_localize('Asia/Tashkent') if available.origin.tzinfo is None else available.origin.tz_convert('Asia/Tashkent')
    for row in f.itertuples():
        if row.time_verified:
            assert pd.Timestamp(row.publication_time).tz_convert('Asia/Tashkent')<local,'Publication after operational cutoff'
        elif pd.Timestamp(row.publication_date).date()==local.date():
            assert available.timing_rule=='PERMISSIVE_END_OF_DAY','Strict same-day GDP leaked'
