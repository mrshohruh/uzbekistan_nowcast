"""Parse exact totals from archived CBU article tables."""
from __future__ import annotations

import re
import numpy as np
import pandas as pd


MONTHS = {name.lower(): number for number, name in enumerate(
    ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
     'September', 'October', 'November', 'December'), 1)}


def _number(value: str) -> float:
    text = value.replace('\xa0', ' ').replace('�', '').strip()
    text = re.sub(r'[^0-9,\.\-]', '', text)
    if not text or text == '-':
        raise ValueError(f'Not a numeric archive cell: {value!r}')
    if ',' in text and '.' not in text:
        text = text.replace(',', '.')
    elif ',' in text:
        text = text.replace(',', '')
    return float(text)


def _total_values(tables, minimum: int) -> list[float]:
    candidates = []
    for table in tables:
        for cells in table:
            positions = [i for i, cell in enumerate(cells) if cell.strip().lower() in {'total', 'total by types of document'}]
            for position in positions:
                values = []
                for cell in cells[position + 1:]:
                    try:
                        values.append(_number(cell))
                    except ValueError:
                        continue
                if len(values) >= minimum:
                    candidates.append(values)
    if len(candidates) != 1:
        raise ValueError(f'CBU archive expected one exact Total row, found {len(candidates)}')
    return candidates[0]


def _period_from_asof(text: str) -> pd.Period:
    match = re.search(r'as of (?:the )?(\d{1,2})\s+([A-Za-z]+)\s*,?\s*(\d{4})', text, re.I)
    if not match:
        match = re.search(r'as of ([A-Za-z]+)\s+(\d{1,2})\s*,?\s*(\d{4})', text, re.I)
        if not match:
            range_match = re.search(r'in\s+[A-Za-z]+-([A-Za-z]+)\s+(?:of\s+)?(\d{4})', text, re.I)
            if range_match and range_match.group(1).lower() in MONTHS:
                return pd.Period(year=int(range_match.group(2)),
                                 month=MONTHS[range_match.group(1).lower()], freq='M')
            single_match = re.search(r'transactions carried out.*?in\s+([A-Za-z]+)\s+(?:of\s+)?(\d{4})', text, re.I)
            if single_match and single_match.group(1).lower() in MONTHS:
                return pd.Period(year=int(single_match.group(2)),
                                 month=MONTHS[single_match.group(1).lower()], freq='M')
            raise ValueError('Archive as-of/reporting date not found')
        month, day, year = MONTHS[match.group(1).lower()], int(match.group(2)), int(match.group(3))
    else:
        day, month, year = int(match.group(1)), MONTHS[match.group(2).lower()], int(match.group(3))
    timestamp = pd.Timestamp(year=year, month=month, day=day)
    return (timestamp - pd.Timedelta(days=1)).to_period('M') if day == 1 else timestamp.to_period('M')


def _period_from_during(text: str) -> pd.Period:
    patterns = [r'during\s+([A-Za-z]+)\s+(\d{4})', r'in\s+([A-Za-z]+)\s+(?:of\s+)?(\d{4})\s+year']
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match and match.group(1).lower() in MONTHS:
            return pd.Period(year=int(match.group(2)), month=MONTHS[match.group(1).lower()], freq='M')
    raise ValueError('Archive monthly reporting period not found')


def _record(article, period, value, *, extra=None):
    meta = article['file_metas'][0]
    item = dict(reference_period=str(period), reference_date=period.to_timestamp(how='end').normalize(),
                frequency='M', raw_value=float(value), clean_value=np.nan, quality_flag='',
                source_release_date=article['release'],
                source_release_basis='official archive article update timestamp',
                archive_as_of_date=str(period), article_url=article['url'],
                page_raw_file_path=article['page_meta']['raw_file_path'],
                raw_file_path=meta['raw_file_path'], checksum=meta['checksum'],
                schema_fingerprint=meta['schema_fingerprint'], source_url=meta['source_url'],
                retrieved_at=meta['retrieved_at'], vintage_date=meta['retrieved_at'])
    if extra:
        item.update(extra)
    return item


def parse_bank_article(article) -> dict[str, dict]:
    period = _period_from_asof(article['title'])
    values = _total_values(article['tables'], 6)
    mapping = {'household_credit': values[1], 'corporate_credit': values[2],
               'household_deposits': values[4], 'corporate_deposits': values[5]}
    return {key: _record(article, period, value) for key, value in mapping.items()}


def parse_pos_article(article) -> dict:
    period = _period_from_asof(article['title'] + ' ' + article['plain_text'])
    values = _total_values(article['tables'], 4)
    return _record(article, period, values[-1])


def parse_instant_article(article) -> dict:
    period = _period_from_during(article['plain_text'])
    values = _total_values(article['tables'], 4)
    return _record(article, period, values[1] / 1_000_000_000,
                   extra={'transaction_count': values[0], 'source_raw_value': values[1],
                          'source_raw_unit': 'UZS', 'unit_conversion_scale': 1e-9})


def parse_interbank_article(article) -> dict:
    period = _period_from_during(article['title'] + ' ' + article['plain_text'])
    if not re.search(r'(?:in\s+)?thousand\s+(?:sum|soum|uzs)', article['plain_text'], re.I):
        raise ValueError('Interbank source unit is not explicitly thousand UZS')
    values = _total_values(article['tables'], 2)
    # Total-row final pair is total transaction count and total amount; source tables state thousand sum.
    return _record(article, period, values[-1] / 1_000_000,
                   extra={'transaction_count': values[-2], 'source_raw_value': values[-1],
                          'source_raw_unit': 'thousand UZS', 'unit_conversion_scale': 1e-6})


def latest_releases(records: list[dict]) -> tuple[pd.DataFrame, list[dict]]:
    """Retain latest archive release per month and report overlaps/revisions."""
    frame = pd.DataFrame(records)
    overlaps = []
    for period, group in frame.groupby('reference_period'):
        if len(group) > 1:
            values = group[['raw_value', 'source_release_date', 'checksum', 'article_url']].to_dict('records')
            overlaps.append(dict(reference_period=period, releases=values,
                                 conflicting_values=group.raw_value.nunique(dropna=False) > 1))
    frame['_release_sort'] = pd.to_datetime(frame.source_release_date, utc=True, errors='coerce')
    frame = frame.sort_values(['reference_period', '_release_sort', 'article_url']).drop_duplicates(
        'reference_period', keep='last').drop(columns='_release_sort').reset_index(drop=True)
    return frame, overlaps
