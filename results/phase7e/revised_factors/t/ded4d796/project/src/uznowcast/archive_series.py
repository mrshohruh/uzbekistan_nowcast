"""Build registry archive-spider series from official CBU article families."""
import json

import pandas as pd

from uznowcast import PARSER_VERSION
from uznowcast.io.cbu_archive import (download_article, enumerate_articles, relevant_articles)
from uznowcast.parsers.cbu_archive import (latest_releases, parse_bank_article,
                                           parse_instant_article, parse_interbank_article,
                                           parse_pos_article)
from uznowcast.transforms.decumulate import decumulate_ytd
from uznowcast.transforms.growth import log_growth


def _provenance(frame: pd.DataFrame, row: dict) -> pd.DataFrame:
    result = frame.copy()
    result['variable_key'] = row['variable_key']
    result['provider'] = row['provider']
    result['source_id'] = row['native_indicator_dataset_id']
    result['parser_version'] = PARSER_VERSION
    result['raw_unit'] = row['raw_unit']
    result['unit'] = row['raw_unit']
    result['transformation'] = row['required_transformation']
    result['is_preliminary'] = None
    result['revision_status'] = 'archive_release'
    return result


def build_bank_archive(downloader, registry, *, extreme_threshold=50.0):
    primary = registry.rows['household_deposits']
    articles = relevant_articles(
        enumerate_articles(downloader, primary, section='3497', first_year=2022), 'bank')
    if not articles:
        raise ValueError('CBU bank-statistics archive returned no matching loan/deposit articles')
    grouped = {key: [] for key in ('household_deposits', 'corporate_deposits',
                                    'household_credit', 'corporate_credit')}
    parse_audit = []
    for url, title in articles:
        try:
            release = parse_bank_article(download_article(downloader, primary, url, title))
            for key, record in release.items():
                grouped[key].append(record)
        except Exception as exc:
            parse_audit.append(dict(variable_key='bank_archive_family', reference_period=None,
                                    conflicting_values=None, releases=None, article_url=url,
                                    parse_error=f'{type(exc).__name__}: {exc}'))
    output, audit = {}, parse_audit
    for key, records in grouped.items():
        frame, overlaps = latest_releases(records)
        row = registry.rows[key]
        frame = _provenance(frame, row)
        frame = log_growth(frame, 'raw_value', 12, extreme_threshold)
        output[key] = frame
        audit.extend(dict(variable_key=key, reference_period=item['reference_period'],
                          conflicting_values=item['conflicting_values'],
                          releases=json.dumps(item['releases'], default=str)) for item in overlaps)
    return output, audit


def build_payment_archive(downloader, row, *, extreme_ratio=3.0, extreme_threshold=50.0):
    family = {'pos_turnover': 'pos', 'instant_payments': 'instant',
              'interbank_payments': 'interbank'}[row['variable_key']]
    parser = {'pos': parse_pos_article, 'instant': parse_instant_article,
              'interbank': parse_interbank_article}[family]
    first_year = int(str(row['verified_start'])[:4])
    articles = relevant_articles(
        enumerate_articles(downloader, row, section='3499', first_year=first_year), family)
    if not articles:
        raise ValueError(f'CBU payment archive returned no matching {family} articles')
    records, audit = [], []
    for url, title in articles:
        try:
            records.append(parser(download_article(downloader, row, url, title)))
        except Exception as exc:
            audit.append(dict(variable_key=row['variable_key'], reference_period=None,
                              conflicting_values=None, releases=None, article_url=url,
                              parse_error=f'{type(exc).__name__}: {exc}'))
    if not records:
        raise ValueError(f'No {family} archive articles passed exact parser validation')
    frame, overlaps = latest_releases(records)
    frame = _provenance(frame, row)
    if row['rule_codes'] == ['DECUM_YTD', 'FLOW_YOY_LOG']:
        frame = decumulate_ytd(frame, extreme_ratio)
        frame = log_growth(frame, 'monthly_flow', 12, extreme_threshold)
    elif row['rule_codes'] == ['PAYMENT_AGG', 'FLOW_YOY_LOG']:
        frame = log_growth(frame, 'raw_value', 12, extreme_threshold)
    else:
        raise ValueError(f'Unexpected payment transform contract: {row["variable_key"]}')
    audit.extend(dict(variable_key=row['variable_key'], reference_period=item['reference_period'],
                      conflicting_values=item['conflicting_values'],
                      releases=json.dumps(item['releases'], default=str)) for item in overlaps)
    return frame, audit
