"""Conservative spiders for date-stamped official CBU archive articles/files."""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
from html import unescape
import re
from urllib.parse import urlencode, urljoin

import pandas as pd


class _ArchiveHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.tables: list[list[list[str]]] = []
        self._href = None
        self._anchor: list[str] = []
        self._table = None
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'a':
            self._href, self._anchor = values.get('href'), []
        elif tag == 'table':
            self._table = []
        elif tag == 'tr' and self._table is not None:
            self._row = []
        elif tag in {'td', 'th'} and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._href is not None:
            self._anchor.append(data)
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self._href is not None:
            self.links.append((self._href, _space(' '.join(self._anchor))))
            self._href, self._anchor = None, []
        elif tag in {'td', 'th'} and self._cell is not None:
            self._row.append(_space(' '.join(self._cell)))
            self._cell = None
        elif tag == 'tr' and self._row is not None:
            if any(self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == 'table' and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def _space(value: str) -> str:
    return re.sub(r'\s+', ' ', unescape(value).replace('\xa0', ' ')).strip()


def _parse(content: bytes) -> _ArchiveHTML:
    parser = _ArchiveHTML()
    parser.feed(content.decode('utf-8', errors='replace'))
    return parser


def _listing_url(base: str, section: str, year: int) -> str:
    query = urlencode({
        'arFilter_DATE_ACTIVE_FROM_1': f'01.01.{year}',
        'arFilter_DATE_ACTIVE_FROM_2': f'31.12.{year}',
        'arFilter_ff[SECTION_ID]': section,
        'set_filter': 'Y',
    })
    return f'{base}?{query}'


def enumerate_articles(downloader, row, *, section: str, first_year: int) -> list[tuple[str, str]]:
    articles = {}
    for year in range(first_year, date.today().year + 1):
        content, _ = downloader.get_bytes(
            row, _listing_url(row['human_source_url'], section, year),
            allowed_content_types=('text/html',))
        parser = _parse(content)
        prefix = '/' + row['human_source_url'].split('/', 3)[3].strip('/') + '/'
        for href, title in parser.links:
            if re.fullmatch(re.escape(prefix) + r'\d+/', href) and title:
                articles[urljoin(row['human_source_url'], href)] = title
    return sorted(articles.items())


def download_article(downloader, row, url: str, title: str) -> dict:
    content, page_meta = downloader.get_bytes(row, url, allowed_content_types=('text/html',))
    text = content.decode('utf-8', errors='replace')
    parser = _parse(content)
    update = re.search(
        r'Update date:.*?id=["\']pc-pdus["\'].*?(\d{1,2}\s+[A-Za-z]+\s+\d{4}),\s*(\d{2}:\d{2})',
        text, flags=re.I | re.S)
    release = (pd.Timestamp(f'{update.group(1)} {update.group(2)}', tz='Asia/Tashkent').isoformat()
               if update else None)
    files = []
    for href, label in parser.links:
        if re.search(r'\.(?:xlsx?|pdf)(?:\?|$)', href, re.I):
            files.append(urljoin(url, href))
    files = sorted(set(files))
    if not files:
        raise ValueError(f'CBU archive article has no source file: {url}')
    metas = []
    for file_url in files:
        _, meta = downloader.get_bytes(
            row, file_url,
            allowed_content_types=('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                   'application/vnd.ms-excel', 'application/pdf',
                                   'application/octet-stream'),
            source_release_date=release, source_release_basis='official archive article update timestamp')
        metas.append(meta)
    return dict(url=url, title=title, release=release, tables=parser.tables,
                plain_text=_space(re.sub(r'<[^>]+>', ' ', text)), page_meta=page_meta,
                file_metas=metas)


def relevant_articles(articles, family: str):
    tests = {
        'bank': lambda value: ('total loans and total deposits' in value and
                               ('of banks' in value or 'banking system by regions' in value)),
        'pos': lambda value: 'transactions carried out through pos' in value,
        'instant': lambda value: 'instant payment system' in value,
        'interbank': lambda value: ('payment documents applied within interbank transactions' in value or
                                    'interbank payment system' in value and 'payment documents' in value),
    }
    check = tests[family]
    return [(url, title) for url, title in articles if check(title.lower())]
