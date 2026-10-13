"""Evidence-checked CBU POS extraction without changing approved eligibility."""
from __future__ import annotations

from io import BytesIO
import json
import re

import numpy as np
import openpyxl
import pandas as pd

from uznowcast import PARSER_VERSION
from uznowcast.io.cbu_archive import enumerate_articles, relevant_articles, download_article
from uznowcast.parsers.cbu_archive import _period_from_asof, latest_releases
from uznowcast.transforms.decumulate import decumulate_ytd
from uznowcast.transforms.growth import log_growth


def reporting_period(text: str) -> pd.Period:
    """Normalize spellings corroborated by archived official reporting ranges."""
    normalized = re.sub(r'\bapreily\b', 'April', text, flags=re.I)
    normalized = re.sub(r'\byanuary\b', 'January', normalized, flags=re.I)
    normalized = re.sub(r'\bavgust\b', 'August', normalized, flags=re.I)
    try:
        period = _period_from_asof(normalized)
    except KeyError as error:
        raise ValueError(f'Unknown official month spelling: {error}') from error
    # Corroborate explicit YTD reporting range with the as-of date where present.
    ranges = re.findall(r'in\s+January-([A-Za-z]+)\s+(?:of\s+)?(\d{4})', normalized, re.I)
    for month, year in ranges:
        stated = pd.Period(pd.Timestamp(f'{month} 1, {year}'), freq='M')
        if stated != period:
            raise ValueError('POS as-of date and reporting range disagree')
    return period


def _extract(rows, expected: pd.Period):
    """Select by amount header and explicit million-sum unit, never last cell."""
    titles = [str(c) for row in rows[:3] for c in row if c]
    if not titles or reporting_period(' '.join(titles)) != expected:
        raise ValueError('POS workbook/page period mismatch')
    headers = []
    for row in rows:
        for column, cell in enumerate(row):
            text = str(cell or '')
            if re.search(r'amount of transactions.*POS.terminals', text, re.I | re.S):
                if not re.search(r'(?:mln\.?|million)\s*(?:sum|soum|uzs)', text, re.I):
                    raise ValueError('POS amount header lacks explicit million UZS unit')
                headers.append(column)
    if len(headers) != 1:
        raise ValueError(f'POS exact amount column matched {len(headers)} columns')
    totals = [row for row in rows if any(str(c or '').strip().lower() == 'total' for c in row)]
    if len(totals) != 1:
        raise ValueError('POS expected one exact Total row')
    if headers[0] >= len(totals[0]):
        raise ValueError('POS Total row lacks the amount column')
    value = totals[0][headers[0]]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        if not isinstance(value, str) or not re.fullmatch(r'[\d\s\u00a0]+(?:\.\d+)?', value):
            raise ValueError('POS amount is not an unambiguous numeric value')
        value = float(re.sub(r'[\s\u00a0]', '', value))
    if not np.isfinite(value) or value <= 0:
        raise ValueError('POS amount must be finite and positive')
    return float(value)


def parse_article(article, client, row):
    period = reporting_period(article['title'])
    matches = []
    attachment_evidence = []
    for meta in article['file_metas']:
        attachment_evidence.append({k: meta.get(k) for k in
                                    ('source_url', 'raw_file_path', 'checksum', 'retrieved_at')})
        if not meta['source_url'].lower().endswith('.xlsx'):
            continue  # Unsupported formats remain explicit in the article error report.
        content, _ = client.get_bytes(row, meta['source_url'], allowed_content_types=(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/octet-stream'))
        workbook = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
        try:
            sheets = [s for s in workbook if s.title.strip().lower().endswith('eng')]
            if len(sheets) != 1:
                raise ValueError('POS workbook requires one evidenced English sheet')
            matches.append((_extract(list(sheets[0].values), period), meta, 'attachment_xlsx'))
        finally:
            workbook.close()
    if not matches and article['tables']:
        candidates = []
        for table in article['tables']:
            # HTML title is an independently observed parent, not an attachment.
            candidates.append(_extract([[article['title']], *table], period))
        if len(candidates) == 1:
            matches.append((candidates[0], article['page_meta'], 'page_html'))
    if len(matches) != 1:
        raise ValueError('POS no unique supported, unit-verified page/XLSX extraction')
    value, meta, basis = matches[0]
    return dict(variable_key='pos_turnover', reference_period=str(period),
                reference_date=period.to_timestamp('M'), frequency='M', raw_value=value,
                clean_value=np.nan, unit=row['raw_unit'], raw_unit=row['raw_unit'],
                quality_flag='', provider=row['provider'], source_id=row['native_indicator_dataset_id'],
                source_url=meta['source_url'], raw_file_path=meta['raw_file_path'],
                checksum=meta['checksum'], schema_fingerprint=meta['schema_fingerprint'],
                retrieved_at=meta['retrieved_at'], vintage_date=meta['retrieved_at'],
                source_release_date=article['release'], source_release_basis='official article update, not first release',
                page_raw_file_path=article['page_meta']['raw_file_path'],
                page_checksum=article['page_meta']['checksum'], article_url=article['url'],
                attachment_evidence=json.dumps(attachment_evidence, sort_keys=True),
                extraction_basis=basis, archive_as_of_date=str(period),
                parser_version=PARSER_VERSION + '-collection-pos-1',
                transformation=row['required_transformation'], clean_model_field=row['clean_model_field'],
                revision_status='archive_release', is_preliminary=None, scope_verified=False)


def collect(client, row):
    articles = relevant_articles(enumerate_articles(client, row, section='3499',
                                first_year=int(str(row['verified_start'])[:4])), 'pos')
    records, audit = [], []
    for url, title in articles:
        try:
            records.append(parse_article(download_article(client, row, url, title), client, row))
        except Exception as error:
            audit.append(dict(article_url=url, status='ARTICLE_FAILED', error_type=type(error).__name__,
                              error=str(error)))
    if not records:
        raise ValueError('No POS archive article passed validation; ' + json.dumps(audit))
    frame, overlaps = latest_releases(records)
    audit.extend(dict(item, status='DUPLICATE_RELEASE') for item in overlaps)
    transformed = log_growth(decumulate_ytd(frame, 3.), 'monthly_flow', 12, 50.)
    periods = pd.PeriodIndex(frame.reference_period, freq='M')
    gaps = pd.period_range(periods.min(), periods.max(), freq='M').difference(periods)
    audit.extend(dict(status='MISSING_PERIOD', reference_period=str(p)) for p in gaps)
    transformed.attrs['archive_audit'] = audit
    return transformed
