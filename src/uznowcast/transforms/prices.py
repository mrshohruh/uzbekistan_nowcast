"""Price-index transformations that preserve published index values."""
import numpy as np
import pandas as pd


def monthly_index_log(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert a previous-month=100 index to a monthly log-percent change."""
    result = frame.sort_values('reference_date').copy().reset_index(drop=True)
    periods = pd.PeriodIndex(result.reference_date, freq='M')
    if periods.has_duplicates:
        raise ValueError('Duplicate monthly price-index input')
    clean, flags = [], []
    for _, item in result.iterrows():
        raw = item.raw_value
        flag = item.quality_flag if isinstance(item.quality_flag, str) else ''
        if pd.isna(raw):
            value = np.nan
            flag = ';'.join(filter(None, [flag, 'missing_raw']))
        elif raw <= 0:
            value = np.nan
            flag = ';'.join(filter(None, [flag, 'nonpositive_price_index']))
        else:
            value = 100 * np.log(raw / 100.0)
        clean.append(value)
        flags.append(flag)
    result['clean_value'] = clean
    result['quality_flag'] = flags
    result['clean_unit'] = 'percent monthly log change'
    return result
