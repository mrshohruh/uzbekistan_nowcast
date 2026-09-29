"""Walk dated official FX snapshots backwards by their observed activation dates."""
from datetime import timedelta
from html import unescape
import logging
import re
from urllib.parse import urljoin
import pandas as pd

from uznowcast.parsers.cbu import parse_fx, deduplicate_daily
from uznowcast.provenance import attach_provenance


def download(downloader, row, start, end, currency='USD'):
    start, cursor = pd.Timestamp(start), pd.Timestamp(end)
    if start > cursor:
        raise ValueError('FX start must precede end')
    frames, count = [], 0
    while cursor >= start:
        url = row['machine_download_url'].replace('{YYYY-MM-DD}', cursor.strftime('%Y-%m-%d'))
        payload, meta = downloader.get(row, url)
        daily = parse_fx(payload, currency=currency)
        if len(daily) != 1:
            raise ValueError(f'CBU dated snapshot expected exactly one {currency} activation date')
        activation = daily.reference_date.iloc[0]
        if activation > cursor:
            raise ValueError(f'CBU activation after requested date: {activation} > {cursor}')
        frames.append(attach_provenance(daily, row, meta))
        # Date is the date of activation, not an independently observed release date.
        # A snapshot valid on cursor implies no later activation up to cursor.
        cursor = activation - timedelta(days=1)
        count += 1
        if count % 100 == 0:
            logging.getLogger('uznowcast.progress').info('FX archived %s snapshots; reached %s', count, activation.date())
    result = deduplicate_daily(pd.concat(frames, ignore_index=True))
    return result.loc[result.reference_date >= start].reset_index(drop=True)


def download_m2(downloader, row):
    """Resolve the current DCS workbook from the registry's official READY_PAGE."""
    if row['automation_status'] != 'READY_PAGE' or str(row['dataset_page_id']) != '111578':
        raise ValueError('Unexpected M2 page configuration')
    page, page_meta = downloader.get_bytes(
        row, row['human_source_url'], allowed_content_types=('text/html',))
    text = page.decode('utf-8', errors='strict')
    update = re.search(
        r'Update date:.*?id=["\']pc-pdus["\'].*?(\d{1,2}\s+[A-Za-z]+\s+\d{4}),\s*(\d{2}:\d{2})',
        text, flags=re.I | re.S)
    if not update:
        raise ValueError('CBU M2 page update timestamp not found')
    release = pd.Timestamp(f'{update.group(1)} {update.group(2)}', tz='Asia/Tashkent').isoformat()
    links = re.findall(r'href=["\']([^"\']*DCS_Uzbekistan_Online\.xlsx)["\']', text, flags=re.I)
    urls = {urljoin(row['human_source_url'], unescape(link)) for link in links}
    if len(urls) != 1:
        raise ValueError(f'CBU M2 page expected one DCS workbook link, found {len(urls)}')
    basis = 'official CBU page update timestamp'
    workbook, meta = downloader.get_bytes(
        row, urls.pop(),
        allowed_content_types=('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',),
        source_release_date=release, source_release_basis=basis)
    meta = dict(meta)
    meta['page_raw_file_path'] = page_meta['raw_file_path']
    meta['source_release_date'] = release
    meta['source_release_basis'] = basis
    return workbook, meta
