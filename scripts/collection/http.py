"""Approved-source HTTP with immutable receipts and explicit failure classes."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import pandas as pd
import requests

from uznowcast.io.http import _check_official_url, _install_system_trust
from uznowcast.provenance import archive_response, read_raw_bytes, utc_now
from uznowcast.validation.schema import strict_json_loads


class SourceError(RuntimeError):
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


def failure_kind(error: Exception) -> str:
    if isinstance(error, SourceError):
        return error.kind
    if isinstance(error, requests.exceptions.SSLError):
        return 'TLS_ERROR'
    if isinstance(error, requests.exceptions.ProxyError):
        return 'NETWORK_ENVIRONMENT_ERROR'
    if isinstance(error, (requests.Timeout, requests.ConnectionError)):
        return 'NETWORK_ERROR'
    return 'SCHEMA_ERROR' if isinstance(error, (ValueError, KeyError)) else 'SOURCE_ERROR'


class CollectionDownloader:
    """Reuse source/archiving contracts, never mutate the old download cache."""

    def __init__(self, root: Path, receipt_root: Path, run_id: str, *, offline=False,
                 session=None, attempts=3, sleep=time.sleep):
        self.root, self.receipt_root, self.run_id = root, receipt_root, run_id
        self.offline, self.attempts, self.sleep = offline, attempts, sleep
        self.events, self.receipts, self.memo = [], [], {}
        self.session = session or requests.Session()
        self.session.headers['User-Agent'] = 'UzNowcastCollection/8A.2 (official public data)'
        if not offline:
            _install_system_trust()
        log = root / 'metadata/download_log.parquet'
        self.cache = {}
        if log.exists():
            records = pd.read_parquet(log)
            records = records.loc[records.http_status.eq(200) & records.raw_file_path.notna()]
            for record in records.sort_values('retrieved_at').to_dict('records'):
                self.cache[(record['variable_key'], record['source_url'])] = record

    def _event(self, item):
        self.events.append(item)
        logging.getLogger('uznowcast.collection').info(json.dumps(item, default=str))

    def get_bytes(self, row, url, *, allowed_content_types, source_release_date=None,
                  source_release_basis=None):
        _check_official_url(row, url)
        key = row['variable_key'], url
        if key in self.memo:
            return self.memo[key]
        if self.offline:
            if key not in self.cache:
                raise SourceError('ARCHIVE_MISSING', f'Offline cache missing: {url}')
            meta = dict(self.cache[key])
            content = read_raw_bytes(self.root, meta)
            meta['archive_repository'] = str(self.root)
            self.receipts.append(meta)
            self._event(dict(meta, status='ARCHIVED_RECEIPT', live_status='LIVE_NOT_TESTED'))
        else:
            for attempt in range(self.attempts):
                self.sleep(.2)
                try:
                    response = self.session.get(url, timeout=(15, 45), allow_redirects=False)
                except (requests.exceptions.SSLError, requests.exceptions.ProxyError) as error:
                    self._event(dict(variable_key=row['variable_key'], source_url=url,
                                     retrieved_at=utc_now(), status=failure_kind(error),
                                     error_message=str(error)))
                    raise SourceError(failure_kind(error), str(error)) from error
                except (requests.Timeout, requests.ConnectionError) as error:
                    self._event(dict(variable_key=row['variable_key'], source_url=url,
                                     retrieved_at=utc_now(), status='NETWORK_ERROR',
                                     error_message=str(error), attempt=attempt + 1))
                    if attempt + 1 == self.attempts:
                        raise SourceError('NETWORK_ERROR', str(error)) from error
                    self.sleep(2 ** attempt)
                    continue
                meta = archive_response(self.receipt_root, row, url, response, self.run_id,
                                        source_release_date, source_release_basis)
                # New immutable receipts are outside mutable processing stages.
                meta['raw_file_path'] = str((self.receipt_root / meta['raw_file_path']).resolve())
                meta['archive_repository'] = str(self.receipt_root)
                self.receipts.append(meta)
                code = response.status_code
                self._event(dict(meta, status='DOWNLOAD_OK' if code == 200 else 'HTTP_ERROR'))
                if code != 200:
                    if (code == 429 or code >= 500) and attempt + 1 < self.attempts:
                        self.sleep(2 ** attempt)
                        continue
                    raise SourceError('AUTH_ERROR' if code in (401, 403) else 'HTTP_ERROR',
                                      f'HTTP {code}: {url}')
                content = read_raw_bytes(self.receipt_root, meta)
                break
        if not content or not any(t in str(meta.get('content_type', '')).lower()
                                  for t in allowed_content_types):
            raise SourceError('FORMAT_ERROR', f'Empty/unexpected content type: {url}')
        self.memo[key] = content, meta
        return content, meta

    def get(self, row, url, **kwargs):
        content, meta = self.get_bytes(row, url, allowed_content_types=('json',), **kwargs)
        try:
            return strict_json_loads(content), meta
        except ValueError as error:
            raise SourceError('FORMAT_ERROR', f'Invalid JSON: {url}') from error
