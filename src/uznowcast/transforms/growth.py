"""Log growth aligns calendar periods, not row offsets."""
import numpy as np
import pandas as pd


def log_growth(frame: pd.DataFrame, level: str, lag: int, extreme_threshold=50.0) -> pd.DataFrame:
    result = frame.sort_values('reference_date').copy().reset_index(drop=True)
    periods = pd.PeriodIndex(result.reference_date, freq='M')
    if periods.has_duplicates:
        raise ValueError('Duplicate monthly growth input')
    levels = pd.Series(result[level].to_numpy(dtype=float), index=periods)
    clean, flags = [], []
    for i, (period, current) in enumerate(levels.items()):
        previous = levels.get(period - lag, np.nan)
        flag = result.quality_flag.iloc[i] if 'quality_flag' in result else ''
        value = np.nan
        if pd.isna(current) or pd.isna(previous):
            flag = ';'.join(filter(None, [flag, 'missing_growth_input']))
        elif current <= 0 or previous <= 0:
            flag = ';'.join(filter(None, [flag, 'nonpositive_growth_input']))
        else:
            value = 100 * (np.log(current) - np.log(previous))
            if abs(value) > extreme_threshold:
                flag = ';'.join(filter(None, [flag, 'extreme_log_change']))
        clean.append(value)
        flags.append(flag)
    result['clean_value'] = clean
    result['quality_flag'] = flags
    result['clean_unit'] = 'percent log change'
    return result


def gdp_target(frame: pd.DataFrame) -> pd.DataFrame:
    if set(frame.frequency) != {'Q'}:
        raise ValueError('GDP target must remain quarterly')
    result = frame.copy()
    result['clean_value'] = result.raw_value - 100.0
    result['clean_unit'] = 'percent growth (published index minus 100)'
    return result
