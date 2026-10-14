"""Deterministic monthly predictors and a separate quarterly GDP target."""
import pandas as pd


def build_monthly(series: dict, registry, scope='pilot') -> pd.DataFrame:
    inputs, columns = [], []
    for row in registry.scope(scope):
        if row['native_frequency'] == 'Quarterly':
            continue
        key, field = row['variable_key'], row['clean_model_field']
        if key not in series:
            continue
        frame = series[key]
        if set(frame.frequency) != {'M'} or frame.reference_date.duplicated().any():
            raise ValueError(f'Master requires unique monthly observations: {key}')
        index = pd.PeriodIndex(frame.reference_date, freq='M')
        if index.has_duplicates or field in columns:
            raise ValueError('Duplicate monthly date/clean field')
        inputs.append(pd.Series(frame.clean_value.to_numpy(dtype=float), index=index, name=field))
        columns.append(field)
    if not inputs:
        raise ValueError('No monthly predictors built')
    joined = pd.concat(inputs, axis=1).sort_index()
    joined = joined.reindex(pd.period_range(joined.index.min(), joined.index.max(), freq='M'))
    if scope == 'v1':
        expected = [row['clean_model_field'] for row in registry.scope(scope)
                    if row['native_frequency'] != 'Quarterly']
        joined = joined.reindex(columns=expected)
    if scope == 'pilot8' and 'usd_uzs' in series:
        fx = series['usd_uzs']
        fx_index = pd.PeriodIndex(fx.reference_date, freq='M')
        complete = (fx.is_complete_month if 'is_complete_month' in fx else
                    ~fx.quality_flag.str.contains('partial_month', regex=False))
        joined['usd_uzs_is_complete'] = pd.Series(complete.to_numpy(dtype=bool), index=fx_index).reindex(joined.index)
        joined['usd_uzs_quality_flag'] = pd.Series(
            fx.quality_flag.fillna('').to_numpy(dtype=str), index=fx_index).reindex(joined.index)
    joined.index = joined.index.to_timestamp(how='end').normalize()
    return joined.rename_axis('date').reset_index()


def build_quarterly(frame: pd.DataFrame, field: str) -> pd.DataFrame:
    if set(frame.frequency) != {'Q'} or frame.reference_period.duplicated().any():
        raise ValueError('GDP must have unique quarterly periods')
    columns = ['reference_period', 'clean_value', 'source_release_date', 'retrieved_at',
               'vintage_date', 'revision_status', 'source_release_basis', 'quality_flag']
    return frame[columns].sort_values('reference_period').rename(columns={'reference_period': 'quarter', 'clean_value': field}).reset_index(drop=True)


def export_pair(frame: pd.DataFrame, base):
    from uznowcast.provenance import atomic_parquet
    atomic_parquet(frame, base.with_suffix('.parquet'))
    frame.to_excel(base.with_suffix('.xlsx'), index=False)
