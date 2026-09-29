"""Monthly arithmetic mean of distinct official activation-date observations."""
import json
import pandas as pd
from uznowcast.parsers.cbu import deduplicate_daily
from uznowcast.transforms.growth import log_growth


def fx_monthly(frame: pd.DataFrame, requested_start, requested_end, extreme_threshold=50.0) -> pd.DataFrame:
    daily = deduplicate_daily(frame)
    daily['month'] = daily.reference_date.dt.to_period('M')
    records = []
    currency_unit = (daily.clean_unit.iloc[0] if 'clean_unit' in daily else 'UZS per currency')
    for month, group in daily.groupby('month', sort=True):
        first = group.iloc[0].drop(labels=['month']).to_dict()
        first.update(reference_period=str(month), reference_date=month.to_timestamp(how='end').normalize(),
                     frequency='M', raw_value=float(group.normalized_daily.mean()),
                     monthly_mean=float(group.normalized_daily.mean()), n_daily=len(group),
                     raw_unit=f'{currency_unit} (mean normalized official activation-date rates)',
                     normalized_daily=None, nominal=None, source_release_date=None,
                     source_release_basis=None, quality_flag='')
        for column in ('source_url', 'raw_file_path', 'checksum'):
            if column in group:
                # Monthly value has multiple parents, never claim a single payload as its source.
                first[column] = json.dumps(sorted(set(group[column])))
        if 'retrieved_at' in group:
            first['retrieved_at'] = max(group.retrieved_at)
            first['vintage_date'] = max(group.retrieved_at)
        start, end = pd.Timestamp(requested_start), pd.Timestamp(requested_end)
        if month.start_time < start or month.end_time.normalize() > end:
            first['quality_flag'] = 'partial_month'
        records.append(first)
    parents = pd.DataFrame(records)
    result = log_growth(parents, 'monthly_mean', 1, extreme_threshold)
    # Do not publish a partial-period comparison as a complete monthly change.
    periods = pd.PeriodIndex(result.reference_date, freq='M')
    partial = set(periods[result.quality_flag.str.contains('partial_month')])
    parents.index = periods
    for i, period in enumerate(periods):
        if period - 1 in parents.index:
            previous = parents.loc[period - 1]
            # A change depends on BOTH monthly means, including their retrieval vintages.
            for column in ('source_url', 'raw_file_path', 'checksum'):
                if column in result:
                    result.loc[i, column] = json.dumps(sorted(set(json.loads(parents.loc[period, column])) |
                                                              set(json.loads(previous[column]))))
            if 'retrieved_at' in result:
                result.loc[i, 'retrieved_at'] = max(parents.loc[period, 'retrieved_at'], previous.retrieved_at)
                result.loc[i, 'vintage_date'] = result.loc[i, 'retrieved_at']
        if period in partial or period - 1 in partial:
            result.loc[i, 'clean_value'] = float('nan')
            if period - 1 in partial:
                result.loc[i, 'quality_flag'] += ';partial_previous_month'
    result['is_complete_month'] = ~result.quality_flag.str.contains('partial_month', regex=False)
    return result
