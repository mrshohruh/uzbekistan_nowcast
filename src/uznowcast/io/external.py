"""Resolvers for registry-approved external provider files."""
from html import unescape
import re
from urllib.parse import urljoin

import pandas as pd


def download_world_bank_gold(downloader, row):
    page, page_meta = downloader.get_bytes(
        row, row['human_source_url'], allowed_content_types=('text/html',))
    text = page.decode('utf-8', errors='strict')
    links = re.findall(r'href=["\']([^"\']*CMO-Historical-Data-Monthly\.xlsx)["\']', text, re.I)
    urls = {urljoin(row['human_source_url'], unescape(link)) for link in links}
    if len(urls) != 1:
        raise ValueError(f'World Bank page expected one monthly Pink Sheet workbook, found {len(urls)}')
    workbook, meta = downloader.get_bytes(
        row, urls.pop(),
        allowed_content_types=('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',))
    meta = dict(meta)
    meta['page_raw_file_path'] = page_meta['raw_file_path']
    return workbook, meta


def world_bank_release_timestamp(text: str):
    match = re.fullmatch(r'Updated on ([A-Za-z]+ \d{2}, \d{4})', text.strip())
    return pd.Timestamp(match.group(1)).date().isoformat() if match else None


def download_rosstat_page(downloader, row):
    """Attempt the exact registry URL; TLS/schema failures must remain visible."""
    return downloader.get_bytes(row, row['human_source_url'], allowed_content_types=('text/html',))
