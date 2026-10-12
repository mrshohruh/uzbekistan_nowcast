"""Derived registry series with explicit parent lineage."""
import json

import numpy as np
import pandas as pd

from uznowcast.transforms.growth import log_growth


def exports_non_gold(total: pd.DataFrame, proxy: pd.DataFrame, row: dict,
                     extreme_threshold=50.0) -> pd.DataFrame:
    """Subtract de-cumulated proxy flow from de-cumulated total-export flow."""
    if row['rule_codes'] != ['DECUM_YTD', 'NON_GOLD_DERIVE', 'FLOW_YOY_LOG']:
        raise ValueError('Non-gold exports transformation contract changed')
    keys = ['reference_period', 'reference_date', 'frequency']
    columns = keys + ['monthly_flow', 'retrieved_at', 'vintage_date', 'source_release_date',
                      'raw_file_path', 'checksum', 'source_url', 'quality_flag']
    merged = total[columns].merge(proxy[columns], on=keys, suffixes=('_total', '_proxy'), how='inner')
    records = []
    for _, item in merged.iterrows():
        value = item.monthly_flow_total - item.monthly_flow_proxy
        flags = [item.quality_flag_total, item.quality_flag_proxy]
        if pd.notna(value) and value < 0:
            flags.append('impossible_negative_derived_value')
        retrieved = max(item.retrieved_at_total, item.retrieved_at_proxy)
        releases = [value for value in (item.source_release_date_total, item.source_release_date_proxy)
                    if pd.notna(value)]
        records.append(dict(reference_period=item.reference_period, reference_date=item.reference_date,
                            frequency='M', raw_value=value, monthly_flow=value, clean_value=np.nan,
                            quality_flag=';'.join(filter(None, flags)), retrieved_at=retrieved,
                            vintage_date=retrieved, source_release_date=max(releases) if releases else None,
                            source_release_basis='inherits slower observed parent update',
                            raw_file_path=json.dumps([item.raw_file_path_total, item.raw_file_path_proxy]),
                            checksum=json.dumps([item.checksum_total, item.checksum_proxy]),
                            source_url=json.dumps([item.source_url_total, item.source_url_proxy]),
                            parent_variables='exports_total;gold_exports_proxy'))
    result = pd.DataFrame(records)
    result = log_growth(result, 'monthly_flow', 12, extreme_threshold)
    result['variable_key'] = row['variable_key']
    result['provider'] = row['provider']
    result['source_id'] = row['native_indicator_dataset_id']
    result['schema_fingerprint'] = 'derived-from-parent-series'
    result['parser_version'] = total.parser_version.iloc[0]
    result['raw_unit'] = row['raw_unit']
    result['unit'] = row['raw_unit']
    result['transformation'] = row['required_transformation']
    result['is_preliminary'] = None
    result['revision_status'] = 'derived_vintage'
    return result
