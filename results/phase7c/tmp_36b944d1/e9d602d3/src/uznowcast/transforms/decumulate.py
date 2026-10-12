"""Calendar-aware YTD to monthly flows with explicit quality flags."""
import numpy as np
import pandas as pd


def decumulate_ytd(frame: pd.DataFrame, extreme_ratio=3.0) -> pd.DataFrame:
    result = frame.sort_values('reference_date').copy().reset_index(drop=True)
    periods = pd.PeriodIndex(result.reference_date, freq='M')
    if periods.has_duplicates:
        raise ValueError('Duplicate month in YTD input')
    values = pd.Series(result.raw_value.to_numpy(), index=periods)
    monthly, flags = [], []
    for period, value in values.items():
        flag = []
        if pd.isna(value):
            flow = np.nan
            flag.append('missing_raw')
        elif period.month == 1:
            flow = value
            previous_dec = values.get(period - 1, np.nan)
            if pd.notna(previous_dec) and value >= previous_dec:
                flag.append('unexpected_january_reset')
        else:
            previous = values.get(period - 1, np.nan)
            flow = value - previous
            if pd.isna(previous):
                flag.append('missing_previous_month')
        if pd.notna(flow) and flow <= 0:
            flag.append('nonpositive_monthly_flow')
        monthly.append(flow)
        flags.append(';'.join(flag))
    result['monthly_flow'] = monthly
    flow_series = pd.Series(monthly, index=periods)
    for i, period in enumerate(periods):
        previous = flow_series.get(period - 1, np.nan)
        current = monthly[i]
        if previous > 0 and current > 0 and max(current / previous, previous / current) > extreme_ratio:
            flags[i] = ';'.join(filter(None, [flags[i], 'extreme_monthly_increment']))
    result['quality_flag'] = flags
    return result
