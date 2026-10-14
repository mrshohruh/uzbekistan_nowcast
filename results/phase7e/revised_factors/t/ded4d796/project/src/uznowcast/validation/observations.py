"""Visible coverage, gaps, source caveats and transformation diagnostics."""
import re

import numpy as np
import pandas as pd


_PERIOD_TOKEN = re.compile(r'^\s*(\d{4})[-\s]?([MQ])?(\d{1,2})?')


def _parse_registry_period(raw: str, native_freq: str) -> pd.Period:
    """Extract the leading YYYY-M## or YYYY-Q# token from an annotated registry cell.

    V1.1 verified_start/verified_end cells may carry trailing evidence text such as
    '2022-M10 (verified same-schema archive)' or '2026-M08 release family'. The
    validator strips that annotation and preserves only the reference-period token.
    """
    match = _PERIOD_TOKEN.match(str(raw))
    if not match:
        raise ValueError(f'Cannot parse registry period token: {raw!r}')
    year, marker, index = match.groups()
    if native_freq == 'Q':
        if marker != 'Q' or not index:
            raise ValueError(f'Quarterly period expected: {raw!r}')
        return pd.Period(f'{year}Q{int(index)}', freq='Q')
    if marker not in (None, 'M') or not index:
        raise ValueError(f'Monthly period expected: {raw!r}')
    return pd.Period(f'{year}-{int(index):02d}', freq='M')


def validate_series(frame, row):
    if frame.empty or frame.reference_period.duplicated().any():
        raise ValueError('Empty or duplicate series')
    if not frame.reference_date.is_monotonic_increasing:
        raise ValueError('Series not sorted')
    freq = frame.frequency.iloc[0]
    if len(set(frame.frequency)) != 1 or freq not in {'M', 'Q', 'D'}:
        raise ValueError('Invalid frequency')
    numeric = frame[['raw_value', 'clean_value']].to_numpy(dtype=float)
    if np.isinf(numeric).any():
        raise ValueError('Infinite value')
    periods = pd.PeriodIndex(frame.reference_date, freq=freq)
    gaps = pd.period_range(periods.min(), periods.max(), freq=freq).difference(periods)
    flags = frame.quality_flag.fillna('').str.split(';').explode()
    counts = {str(k): int(v) for k, v in flags[flags != ''].value_counts().items()}
    warning = ['Historical first-release dates unavailable; retrieved vintages are not first-release history.', row['structural_breaks_caveats']]
    native_freq = 'Q' if row['native_frequency'] == 'Quarterly' else 'M'
    start = _parse_registry_period(row['verified_start'], native_freq)
    actual_start = pd.Period(frame.reference_date.min(), freq=native_freq)
    if actual_start > start:
        warning.append(f'Coverage starts after registry verified start: {actual_start} > {start}')
    if str(row['verified_end']).strip().lower() != 'current':
        end = _parse_registry_period(row['verified_end'], native_freq)
        actual_end = pd.Period(frame.reference_date.max(), freq=native_freq)
        if actual_end < end:
            warning.append(f'Coverage ends before registry verified end: {actual_end} < {end}')
    if freq == 'D':
        warning.append('Calendar-day gaps are reported, not filled; official activation dates only.')
    if row['variable_key'] == 'gdp_real_yoy':
        warning.append('Published quarterly convention retained; no standalone-quarter reconstruction from reported growth rates.')
    clean = frame.loc[frame.clean_value.notna(), 'reference_period']
    reconciliation = []
    # Reconciliation only applies to true YTD-cumulative-decumulated series. Derived
    # series (e.g. exports_non_gold) already store the monthly value in raw_value,
    # so a December-YTD equality has no meaning and the check is skipped.
    is_ytd_source = ('monthly_flow' in frame
                     and 'raw_value' in frame
                     and not frame[['raw_value', 'monthly_flow']].dropna().pipe(
                         lambda df: np.allclose(df.raw_value, df.monthly_flow, equal_nan=True)
                         if len(df) else True))
    if is_ytd_source:
        for year, group in frame.groupby(frame.reference_date.dt.year):
            if len(group) == 12 and group.monthly_flow.notna().all():
                total, december = group.monthly_flow.sum(), group.raw_value.iloc[-1]
                if not np.isclose(total, december, rtol=1e-10, atol=1e-6):
                    raise ValueError(f'Annual de-cumulation does not reconcile: {year}')
                reconciliation.append(dict(year=int(year), monthly_sum=float(total), december_ytd=float(december), passed=True))
    if (frame.raw_value < 0).any():
        warning.append('Negative raw observations require review')
    return dict(status='passed_with_warnings', rows=len(frame), start=str(periods.min()), end=str(periods.max()),
                clean_start=clean.iloc[0] if len(clean) else None, clean_end=clean.iloc[-1] if len(clean) else None,
                clean_count=len(clean), missing_periods=list(map(str, gaps)), quality_flags=counts,
                negative_raw_count=int((frame.raw_value < 0).sum()), warnings=warning,
                registry_verified_start=row['verified_start'], registry_verified_end=row['verified_end'],
                annual_reconciliation=reconciliation)
