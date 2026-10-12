"""Auditable calendar-aligned transformations of archived official observations."""
import numpy as np
import pandas as pd

KEYS = ('retail_trade', 'construction', 'imports_total', 'exports_non_gold')

def flows(frame):
    s = frame.set_index(pd.to_datetime(frame.reference_date)).raw_value.sort_index()
    if s.index.to_period('M').duplicated().any():
        raise ValueError('Duplicate month')
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq='ME'))
    f = s.groupby(s.index.year).diff()
    f.loc[f.index.month == 1] = s.loc[s.index.month == 1]
    return s, f

def growth(s):
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq='ME'))
    return 100*np.log(s.where(s.gt(0))/s.shift(12).where(s.shift(12).gt(0)))

def gate(s, origin, days):
    return s.where(s.index + pd.to_timedelta(days, unit='D') <= pd.Timestamp(origin))
