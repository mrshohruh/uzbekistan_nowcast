"""Resolve current CBU statistical workbooks whose registry JSON snapshots are stale."""
from html import unescape
import re
from urllib.parse import urljoin

import pandas as pd


def download_reserves(downloader, row):
    page, page_meta = downloader.get_bytes(
        row, row['human_source_url'], allowed_content_types=('text/html',))
    text = page.decode('utf-8', errors='strict')
    update = re.search(
        r'Update date:.*?id=["\']pc-pdus["\'].*?(\d{1,2}\s+[A-Za-z]+\s+\d{4}),\s*(\d{2}:\d{2})',
        text, flags=re.I | re.S)
    if not update:
        raise ValueError('CBU reserves page update timestamp not found')
    release = pd.Timestamp(f'{update.group(1)} {update.group(2)}', tz='Asia/Tashkent').isoformat()
    links = re.findall(r'href=["\']([^"\']*IR_Uzbekistan_MCD_STA\.xlsx)["\']', text, re.I)
    urls = {urljoin(row['human_source_url'], unescape(link)) for link in links}
    if len(urls) != 1:
        raise ValueError(f'CBU reserves page expected one current workbook, found {len(urls)}')
    workbook, meta = downloader.get_bytes(
        row, urls.pop(),
        allowed_content_types=('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',),
        source_release_date=release, source_release_basis='official CBU page update timestamp')
    meta = dict(meta)
    meta['page_raw_file_path'] = page_meta['raw_file_path']
    meta['source_release_date'] = release
    meta['source_release_basis'] = 'official CBU page update timestamp'
    return workbook, meta
