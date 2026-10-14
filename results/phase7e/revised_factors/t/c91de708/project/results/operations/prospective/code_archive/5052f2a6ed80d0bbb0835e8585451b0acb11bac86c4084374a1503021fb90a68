"""Bounded, rate-limited HTTP requests, archived before JSON interpretation."""
import json
import logging
import os
import time
from urllib.parse import urlparse
import requests

from uznowcast.provenance import archive_response, read_raw, read_raw_bytes, utc_now
from uznowcast.validation.schema import schema_fingerprint

LOG = logging.getLogger('uznowcast')


def _install_system_trust():
    """Opt-in: route TLS through the OS trust store instead of certifi.

    Enabled by UZNOWCAST_USE_SYSTEM_TRUST=1. Verification stays enabled; the only
    change is which set of root CAs `ssl.create_default_context()` reads. Providers
    whose leaf certificate is signed by a CA the operator has installed into the
    OS trust store (e.g. Rosstat's Russian Trusted Root, if installed) then verify
    normally. Providers whose CA is not present continue to fail with a real
    certificate-verify error.
    """
    if os.environ.get('UZNOWCAST_USE_SYSTEM_TRUST') != '1':
        return False
    try:
        import truststore
    except ImportError as exc:
        raise RuntimeError(
            'UZNOWCAST_USE_SYSTEM_TRUST=1 requires the truststore package: '
            'pip install truststore') from exc
    truststore.inject_into_ssl()
    return True

PROVIDER_HOSTS = {
    'SIAT': {'api.siat.stat.uz'},
    'CBU': {'cbu.uz'},
    'CBU bank-statistics archive': {'cbu.uz'},
    'World Bank Pink Sheet': {'www.worldbank.org', 'thedocs.worldbank.org'},
    'Rosstat': {'rosstat.gov.ru', 'www.rosstat.gov.ru'},
}


def _check_official_url(row, url):
    parsed = urlparse(url)
    expected = PROVIDER_HOSTS.get(row['provider'])
    if parsed.scheme != 'https' or expected is None or parsed.hostname not in expected:
        raise ValueError(f'Unexpected provider URL: {url}')


class Downloader:
    def __init__(self, root, run_id, *, offline=False, refresh=False, delay=0.2):
        self.root, self.run_id = root, run_id
        self.offline, self.refresh, self.delay = offline, refresh, delay
        self.system_trust = _install_system_trust() if not offline else False
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'UzNowcastResearch/0.1 (public macroeconomic data pilot)'
        self.cache, self.memo, self.events = {}, {}, []
        for path in (root / 'data/raw').rglob('*.json'):
            meta = json.loads(path.read_text(encoding='utf-8'))
            if meta.get('http_status') == 200 and meta.get('raw_file_path'):
                key = (meta['variable_key'], meta['source_url'])
                if meta['retrieved_at'] > self.cache.get(key, {}).get('retrieved_at', ''):
                    self.cache[key] = meta

    def event(self, record):
        self.events.append(record)
        LOG.info(json.dumps(record, default=str))

    def get(self, row, url, *, source_release_date=None, source_release_basis=None):
        _check_official_url(row, url)
        key = (row['variable_key'], url)
        if key in self.memo:
            return self.memo[key]
        if key in self.cache and (self.offline or not self.refresh):
            meta = dict(self.cache[key])
            meta['raw_file_path'] = meta['raw_file_path'].replace('\\', '/')
            obj = read_raw(self.root, meta)
            fingerprint = schema_fingerprint(obj)
            if meta.get('parser_version') == 'schema-inspection-1':
                # Keep exploratory raw sidecars immutable; normalize only this build's metadata.
                meta['schema_fingerprint'] = fingerprint
            elif meta.get('schema_fingerprint') != fingerprint:
                raise ValueError(f'Cached schema fingerprint mismatch: {url}')
            result = obj, meta
            self.event(dict(meta, build_run_id=self.run_id, status='cache', warning_count=0, error_message=None))
            self.memo[key] = result
            return result
        if self.offline:
            raise ValueError(f'Offline cache missing: {url}')
        for attempt in range(3):
            meta = dict(run_id=self.run_id, variable_key=row['variable_key'], provider=row['provider'],
                        source_url=url, retrieved_at=utc_now(), http_status=None)
            try:
                time.sleep(self.delay)
                response = self.session.get(url, timeout=(15, 45), allow_redirects=False)
                meta = archive_response(self.root, row, url, response, self.run_id,
                                        source_release_date, source_release_basis)
                retryable = response.status_code == 429 or response.status_code >= 500
                if response.status_code != 200:
                    self.event(dict(meta, status='http_error', error_message=f'HTTP {response.status_code}', warning_count=0))
                    if retryable and attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                    raise ValueError(f'HTTP {response.status_code}: {url}')
                if not response.content or 'json' not in meta['content_type'].lower():
                    raise ValueError(f'Empty or unexpected content type: {meta["content_type"]}')
                obj = read_raw(self.root, meta)
                previous = self.cache.get(key)
                drift = bool(previous and previous.get('parser_version') != 'schema-inspection-1'
                             and previous.get('schema_fingerprint') != meta['schema_fingerprint'])
                self.event(dict(meta, status='downloaded', warning_count=int(drift),
                                error_message=None, schema_drift=drift))
                self.memo[key] = obj, meta
                return obj, meta
            except (requests.Timeout, requests.ConnectionError) as exc:
                self.event(dict(meta, status='network_error', error_message=str(exc), warning_count=0))
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
            except (ValueError, requests.RequestException) as exc:
                self.event(dict(meta, status='failed', error_message=str(exc), warning_count=0))
                raise

    def get_bytes(self, row, url, *, allowed_content_types, source_release_date=None,
                  source_release_basis=None):
        """Fetch and archive a non-JSON official file using the same cache/retry policy."""
        _check_official_url(row, url)
        key = (row['variable_key'], url)
        if key in self.memo:
            return self.memo[key]
        if key in self.cache and (self.offline or not self.refresh):
            meta = dict(self.cache[key])
            meta['raw_file_path'] = meta['raw_file_path'].replace('\\', '/')
            content = read_raw_bytes(self.root, meta)
            result = content, meta
            self.event(dict(meta, build_run_id=self.run_id, status='cache', warning_count=0,
                            error_message=None))
            self.memo[key] = result
            return result
        if self.offline:
            raise ValueError(f'Offline cache missing: {url}')
        for attempt in range(3):
            meta = dict(run_id=self.run_id, variable_key=row['variable_key'], provider=row['provider'],
                        source_url=url, retrieved_at=utc_now(), http_status=None)
            try:
                time.sleep(self.delay)
                response = self.session.get(url, timeout=(15, 45), allow_redirects=False)
                meta = archive_response(self.root, row, url, response, self.run_id,
                                        source_release_date, source_release_basis)
                retryable = response.status_code == 429 or response.status_code >= 500
                if response.status_code != 200:
                    self.event(dict(meta, status='http_error', error_message=f'HTTP {response.status_code}',
                                    warning_count=0))
                    if retryable and attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                    raise ValueError(f'HTTP {response.status_code}: {url}')
                content_type = meta['content_type'].lower()
                if not response.content or not any(expected_type in content_type
                                                    for expected_type in allowed_content_types):
                    raise ValueError(f'Empty or unexpected content type: {meta["content_type"]}')
                content = read_raw_bytes(self.root, meta)
                previous = self.cache.get(key)
                drift = bool(previous and previous.get('parser_version') != 'schema-inspection-1'
                             and previous.get('schema_fingerprint') != meta['schema_fingerprint'])
                self.event(dict(meta, status='downloaded', warning_count=int(drift),
                                error_message=None, schema_drift=drift))
                self.memo[key] = content, meta
                return content, meta
            except (requests.Timeout, requests.ConnectionError) as exc:
                self.event(dict(meta, status='network_error', error_message=str(exc), warning_count=0))
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
            except (ValueError, requests.RequestException) as exc:
                self.event(dict(meta, status='failed', error_message=str(exc), warning_count=0))
                raise
