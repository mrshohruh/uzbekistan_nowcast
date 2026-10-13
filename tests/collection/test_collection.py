"""Isolated collection scenarios; no production publication or forecast fitting."""
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
import openpyxl
import pandas as pd
import pytest
import requests

from scripts.collection import engine, pos, versions
from scripts.collection.http import CollectionDownloader, SourceError
from scripts.operations.state import operational_lock, read, write, sha
from uznowcast.registry import load_registry
from uznowcast.io.cbu_archive import download_article
from uznowcast.parsers.cbu import parse_fx
from uznowcast.provenance import attach_provenance
from uznowcast.transforms.frequency import fx_monthly

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / 'tests/fixtures/collection'
CUTOFF = pd.Timestamp('2026-10-12T08:00:00Z')


@pytest.fixture
def isolated(tmp_path):
    root = tmp_path / 'r'
    paths = [f'data/processed/{k}.parquet' for k in engine.KEYS]
    paths += [f'data/processed/{k}_daily.parquet' for k in ['usd_uzs', 'rub_uzs']]
    paths += ['registry/uzbekistan_nowcasting_v1.2_registry.xlsx', 'config/registry_contracts.json',
              'config/model_definitions.json', 'config/industry_source.json', 'config/siat_contracts.json',
              'config/cbu_contracts.json', 'data/master/v1_monthly.parquet',
              'data/master/gdp_quarterly.parquet', 'data/current/predictor_provenance.csv',
              'data/current/recovered_monthly.csv', 'metadata/observations_long.parquet',
              'metadata/vintages.parquet', 'metadata/revisions.parquet', 'metadata/download_log.parquet']
    for rel in paths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)
    return root


def old_candidate(key, client, registry, root, working, asof):
    if key == 'industrial_production':
        f = pd.read_parquet(working / 'data/recovery/industrial_production.parquet')
    else:
        f = pd.read_parquet(working / f'data/processed/{key}.parquet')
    return f.copy()


def run(root, fetch=old_candidate, commit=False):
    return engine.collect(root, offline=True, asof=CUTOFF, commit=commit,
                          fetch=fetch, verify_seal=False)


def snapshot(result, root):
    return versions.current_snapshot(root / 'data/collection') or Path(root / 'data/collection/runs' / result['run_id'] / 'stage')


def updated(key, target='m2', revision=False):
    def fetch(k, *args):
        f = old_candidate(k, *args)
        if k != target:
            return f
        row = f.iloc[-1].copy()
        if not revision:
            p = pd.Period(row.reference_period, 'M') + 1
            row['reference_period'] = str(p)
            row['reference_date'] = p.to_timestamp('M')
        row['raw_value'] *= 1.01
        row['clean_value'] += .1
        row['retrieved_at'] = '2026-10-12T07:00:00+00:00'
        row['vintage_date'] = row['retrieved_at']
        row['source_release_date'] = None
        row['checksum'] = 'synthetic-test-only-change'
        return pd.concat([f.loc[~f.reference_period.eq(row.reference_period)], row.to_frame().T], ignore_index=True).astype(
            {'raw_value': float, 'clean_value': float, 'reference_date': 'datetime64[ns]'})
    return fetch


def test_no_new_observations_does_not_publish(isolated):
    before = sha(isolated / 'data/master/v1_monthly.parquet')
    result = run(isolated, commit=True)
    assert result['status'] == 'NO_INFORMATION_CHANGE' and result['exit_code'] == 0
    assert not versions.current_snapshot(isolated / 'data/collection')
    assert before == sha(isolated / 'data/master/v1_monthly.parquet')
    assert not result['forecasts_calculated']


def test_new_valid_observation_commits_only_collection_version(isolated):
    before = sha(isolated / 'data/master/v1_monthly.parquet')
    result = run(isolated, updated('m2'), commit=True)
    assert result['status'] == 'COLLECTION_COMMITTED'
    version = snapshot(result, isolated)
    frame = pd.read_parquet(version / 'data/processed/m2.parquet')
    assert frame.reference_period.max() == '2026-09'
    assert sha(isolated / 'data/master/v1_monthly.parquet') == before
    assert not result['production_promoted'] and not result['forecasts_calculated']


def test_historical_revision_retains_both_vintages(isolated):
    result = run(isolated, updated('m2', revision=True), commit=True)
    version = snapshot(result, isolated)
    revisions = pd.read_parquet(version / 'metadata/revisions.parquet')
    assert ((revisions.variable_key == 'm2') & (revisions.reference_period == '2026-08')).any()
    old = pd.read_parquet(isolated / 'metadata/observations_long.parquet')
    new = pd.read_parquet(version / 'metadata/observations_long.parquet')
    assert len(new) > len(old)


@pytest.mark.parametrize('failed', [('m2',), ('m2', 'ppi', 'rub_uzs')])
def test_unavailable_sources_retain_prior_values(isolated, failed):
    def fetch(k, *args):
        if k in failed:
            raise SourceError('NETWORK_ERROR', 'synthetic outage')
        return updated('gold_price', target='gold_price')(k, *args)
    result = run(isolated, fetch, commit=True)
    assert result['status'] == 'COLLECTION_DEGRADED' and result['exit_code'] == 2
    version = snapshot(result, isolated)
    for key in failed:
        assert sha(version / f'data/processed/{key}.parquet') == sha(isolated / f'data/processed/{key}.parquet')


@pytest.mark.parametrize('mutation', ['duplicate', 'unit', 'frequency', 'invalid'])
def test_invalid_source_data_never_enters_master(isolated, mutation):
    def fetch(k, *args):
        f = old_candidate(k, *args)
        if k == 'usd_uzs':
            if mutation == 'duplicate':
                f = pd.concat([f, f.tail(1)], ignore_index=True)
            elif mutation == 'unit':
                f['unit'] = 'wrong unit'
            elif mutation == 'frequency':
                f['frequency'] = 'Q'
            else:
                f.loc[f.index[-2], 'raw_value'] = -1
                f.loc[f.index[-2], 'clean_value'] = np.inf
        return f
    result = run(isolated, fetch, commit=True)
    assert result['status'] == 'COLLECTION_ABORTED' and result['exit_code'] == 3
    assert versions.current_snapshot(isolated / 'data/collection') is None


@pytest.mark.parametrize('key', ['usd_uzs', 'rub_uzs'])
def test_daily_fx_without_complete_month_is_retained(isolated, key):
    def fetch(k, client, registry, root, working, asof):
        if k != key:
            return old_candidate(k, client, registry, root, working, asof)
        old = pd.read_parquet(working / f'data/processed/{key}_daily.parquet')
        row = registry.rows[key]
        rate = str(float(old.iloc[-1].raw_value) * 1.001)
        new = parse_fx([dict(Ccy=key.split('_')[0].upper(), Date='02.10.2026', Rate=rate, Nominal='1')],
                       currency=key.split('_')[0].upper())
        new = attach_provenance(new, row, dict(source_url='https://cbu.uz/synthetic-test-only',
                     retrieved_at='2026-10-12T07:00:00Z', raw_file_path='test-only', checksum='test-only', schema_fingerprint='test-only'))
        daily = pd.concat([old, new], ignore_index=True).sort_values('reference_date')
        monthly = fx_monthly(daily, '2013-01-01', '2026-10-12')
        # Keep frozen completed months exactly to isolate partial-month persistence.
        candidate = old_candidate(k, client, registry, root, working, asof)
        partial = monthly.loc[monthly.reference_period.eq('2026-10')]
        candidate = pd.concat([candidate.loc[~candidate.reference_period.eq('2026-10')], partial], ignore_index=True)
        candidate.attrs['daily'] = daily
        return candidate
    result = run(isolated, fetch, commit=True)
    version = snapshot(result, isolated)
    assert result['status'] == 'COLLECTION_COMMITTED'
    daily = pd.read_parquet(version / f'data/processed/{key}_daily.parquet')
    assert daily.reference_date.max() == pd.Timestamp('2026-10-02')
    monthly = pd.read_parquet(version / f'data/processed/{key}.parquet')
    assert monthly.loc[monthly.reference_period.eq('2026-10'), 'clean_value'].isna().all()
    history = pd.read_parquet(version / 'metadata/observations_long.parquet')
    assert ((history.variable_key == key) & (history.reference_period == '2026-10-02')).any()


def test_incomplete_pos_archive_is_degraded_with_errors(isolated):
    def fetch(k, *args):
        f = old_candidate(k, *args)
        if k == 'pos_turnover':
            f.attrs['archive_audit'] = [dict(status='ARTICLE_FAILED', article_url='test-only', error='bad unit'),
                                       dict(status='MISSING_PERIOD', reference_period='2023-03')]
        return f
    result = run(isolated, fetch)
    assert result['status'] == 'COLLECTION_DEGRADED'
    audit = pd.read_csv(isolated / 'data/collection/runs' / result['run_id'] / 'archive_audit.csv')
    assert set(audit.status) == {'ARTICLE_FAILED', 'MISSING_PERIOD'}


def test_identical_repeat_keeps_pointer_and_observation_identity(isolated):
    first = run(isolated, updated('m2'), commit=True)
    pointer = (isolated / 'data/collection/current.json').read_bytes()
    second = run(isolated, commit=True)
    assert second['status'] == 'NO_INFORMATION_CHANGE'
    assert (isolated / 'data/collection/current.json').read_bytes() == pointer
    frame = pd.read_parquet(snapshot(first, isolated) / 'metadata/observations_long.parquet')
    assert not frame.duplicated(['variable_key', 'reference_period', 'frequency', 'retrieved_at', 'checksum', 'parser_version']).any()


def test_interrupted_run_blocks_then_recovers_without_promotion(isolated):
    store = isolated / 'data/collection'
    write(store / 'runs/crashed/journal.json', dict(status='COLLECTING', run_id='crashed'))
    blocked = run(isolated)
    assert blocked['status'] == 'COLLECTION_BLOCKED'
    with operational_lock(isolated):
        assert versions.recover(store, 'crashed') == 'ABORTED_RECOVERED'
    assert run(isolated)['status'] == 'NO_INFORMATION_CHANGE'


def test_concurrent_collection_is_excluded(isolated):
    with operational_lock(isolated):
        result = run(isolated)
        assert result['exit_code'] == 4
        assert (isolated / 'data/staging/operations.lock').exists()


def test_gdp_without_first_release_remains_withheld(isolated):
    def fetch(k, *args):
        f = old_candidate(k, *args)
        if k == 'gdp_real_yoy':
            row = f.iloc[-1].copy()
            row['reference_period'] = '2026Q3'
            row['reference_date'] = pd.Timestamp('2026-09-30')
            row['raw_value'], row['clean_value'] = 108., 8.
            row['retrieved_at'] = row['vintage_date'] = '2026-10-12T07:00:00Z'
            row['source_release_date'] = None
            f = pd.concat([f, row.to_frame().T], ignore_index=True).astype({'reference_date': 'datetime64[ns]', 'raw_value': float, 'clean_value': float})
        return f
    result = run(isolated, fetch)
    f = pd.read_parquet(snapshot(result, isolated) / 'data/processed/gdp_real_yoy.parquet')
    assert f.reference_period.max() == '2026Q2'
    decisions = pd.read_csv(isolated / 'data/collection/runs' / result['run_id'] / 'observation_decisions.csv')
    assert decisions.reason.str.contains('GDP_VALUE_DETECTED_UNVERIFIED').any()


def test_claimed_pos_scope_does_not_extend_eligibility(isolated):
    def fetch(k, *args):
        f = old_candidate(k, *args)
        if k == 'pos_turnover':
            f['scope_verified'] = True
            selected = f.reference_period.gt('2024-12') & f.clean_value.notna() & f.clean_value.abs().lt(40)
            index = f.loc[selected].index[-1]
            f.loc[index, 'clean_value'] += .1
            f.loc[index, 'retrieved_at'] = f.loc[index, 'vintage_date'] = '2026-10-12T07:00:00Z'
        return f
    result = run(isolated, fetch)
    recovery = pd.read_parquet(snapshot(result, isolated) / 'data/recovery/pos_turnover.parquet')
    assert recovery.reference_period.max() == '2024-12'
    decisions = pd.read_csv(isolated / 'data/collection/runs' / result['run_id'] / 'observation_decisions.csv')
    assert decisions.reason.str.contains('SCOPE_VERIFICATION_REQUIRED').any()


def test_real_industry_version_has_separate_provenance(isolated):
    def fetch(k, *args):
        f = old_candidate(k, *args)
        if k == 'industrial_production':
            row = f.iloc[-1].copy()
            row['reference_period'] = '2026-09'
            row['reference_date'] = pd.Timestamp('2026-09-30')
            row['raw_value'], row['clean_value'] = 108., 8.
            row['retrieved_at'] = row['vintage_date'] = '2026-10-12T07:00:00Z'
            row['source_release_date'] = None
            f = pd.concat([f, row.to_frame().T], ignore_index=True).astype({'raw_value': float, 'clean_value': float, 'reference_date': 'datetime64[ns]'})
        return f
    result = run(isolated, fetch, commit=True)
    version = snapshot(result, isolated)
    assert sha(version / 'data/processed/industrial_production.parquet') == sha(isolated / 'data/processed/industrial_production.parquet')
    f = pd.read_parquet(version / 'metadata/recovery_observations_long.parquet')
    assert f.reference_period.max() == '2026-09'
    assert (f.clean_value == f.raw_value - 100).all()


class ReceiptClient:
    def __init__(self, altered=None):
        self.receipts = json.loads((FIX / 'pos_receipts.json').read_text())
        self.altered = altered
    def get_bytes(self, row, url, **kwargs):
        for name, meta in self.receipts.items():
            if meta['source_url'] == url:
                content = (FIX / name).read_bytes()
                assert sha(FIX / name) == meta['checksum']
                return self.altered if self.altered is not None and name.endswith('.xlsx') else content, meta
        raise ValueError('Unexpected URL')


def official_article(client):
    row = load_registry(ROOT / 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx').rows['pos_turnover']
    url = client.receipts['pos_apreily_page.html']['source_url']
    title = "Information as of Apreily 1, 2023, transactions carried out through POS-terminals in Yanuary-March of 2023"
    return row, download_article(client, row, url, title)


def test_official_apreily_receipts_parse_period_units_and_total():
    client = ReceiptClient()
    row, article = official_article(client)
    parsed = pos.parse_article(article, client, row)
    assert parsed['reference_period'] == '2023-03'
    assert parsed['raw_value'] == pytest.approx(52919100.966056414)
    assert parsed['unit'] == 'million UZS'
    assert parsed['extraction_basis'] == 'attachment_xlsx'
    assert parsed['checksum'] != parsed['page_checksum']
    assert parsed['source_url'].endswith('.xlsx') and parsed['article_url'].endswith('/992617/')


@pytest.mark.parametrize('cell,value', [('F3', 'Amount in billion UZS'), ('F39', 'bad'),
                                       ('B1', 'Information as of April 1, 2024')])
def test_pos_rejects_changed_unit_numeric_or_year(cell, value):
    workbook = openpyxl.load_workbook(BytesIO((FIX / 'pos_apreily.xlsx').read_bytes()))
    workbook.worksheets[0][cell] = value
    stream = BytesIO(); workbook.save(stream); workbook.close()
    client = ReceiptClient(stream.getvalue())
    row, article = official_article(client)
    with pytest.raises(ValueError):
        pos.parse_article(article, client, row)


def test_pos_period_crosscheck_and_unknown_month():
    with pytest.raises(ValueError):
        pos.reporting_period('as of Apreily 1, 2023 in January-February of 2023')
    with pytest.raises(ValueError):
        pos.reporting_period('as of Unknownmonth 1, 2023')


def test_reader_keeps_old_version_on_pointer_failure(tmp_path):
    store = tmp_path / 's'
    def make(name):
        run = store / 'runs' / name
        stage = run / 'stage'; stage.mkdir(parents=True)
        (stage / 'a').write_text(name)
        return stage, dict(status='VALIDATED', files={'a': sha(stage / 'a')})
    stage, manifest = make('old'); versions.publish(store, stage, 'old', manifest)
    stage, manifest = make('new')
    def interrupted(source, target):
        if Path(target).name == 'current.json':
            raise OSError('synthetic interruption before pointer')
        source.rename(target)
    with pytest.raises(OSError):
        versions.publish(store, stage, 'new', manifest, replace=interrupted)
    assert versions.current_snapshot(store).name == 'old'
    assert versions.recover(store, 'new') == 'ABORTED_RECOVERED'


def test_reader_rejects_corrupted_version(tmp_path):
    store = tmp_path / 's'; stage = store / 'runs/x/stage'; stage.mkdir(parents=True)
    (stage / 'a').write_text('valid')
    version = versions.publish(store, stage, 'x', dict(status='VALIDATED', files={'a': sha(stage / 'a')}))
    (version / 'a').write_text('corrupt')
    with pytest.raises(ValueError):
        versions.current_snapshot(store)


@pytest.mark.parametrize('exception,kind', [(requests.exceptions.SSLError('bad CA'), 'TLS_ERROR'),
                                         (requests.exceptions.ProxyError('bad proxy'), 'NETWORK_ENVIRONMENT_ERROR')])
def test_permanent_transport_errors_not_retried(tmp_path, exception, kind):
    calls = []
    def get(*args, **kwargs):
        calls.append(kwargs)
        raise exception
    session = SimpleNamespace(headers={}, get=get)
    client = CollectionDownloader(tmp_path, tmp_path / 'raw', 'x', session=session, sleep=lambda _: None)
    row = load_registry(ROOT / 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx').rows['usd_uzs']
    with pytest.raises(SourceError) as caught:
        client.get(row, 'https://cbu.uz/test-only')
    assert caught.value.kind == kind and len(calls) == 1
    assert 'verify' not in calls[0]  # requests default certificate verification preserved.


def test_temporary_http_retries_archive_every_response(tmp_path):
    responses = iter([503, 429, 200])
    def get(url, **kwargs):
        return SimpleNamespace(status_code=next(responses), content=b'[{"x":1}]', url=url,
                               headers={'Content-Type': 'application/json'})
    client = CollectionDownloader(tmp_path, tmp_path / 'raw', 'x',
                                 session=SimpleNamespace(headers={}, get=get), sleep=lambda _: None)
    row = load_registry(ROOT / 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx').rows['usd_uzs']
    obj, meta = client.get(row, 'https://cbu.uz/test-only')
    assert obj == [{'x': 1}] and len(client.receipts) == 3
    assert len(list((tmp_path / 'raw').rglob('*.payload'))) == 3


def test_temporary_network_retries_are_bounded(tmp_path):
    calls = []
    def get(*args, **kwargs):
        calls.append(1); raise requests.Timeout('synthetic timeout')
    client = CollectionDownloader(tmp_path, tmp_path / 'raw', 'x',
                                 session=SimpleNamespace(headers={}, get=get), sleep=lambda _: None)
    row = load_registry(ROOT / 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx').rows['usd_uzs']
    with pytest.raises(SourceError):
        client.get(row, 'https://cbu.uz/test-only')
    assert len(calls) == 3


def test_corrupt_candidate_cannot_be_published(tmp_path):
    store = tmp_path / 's'; stage = store / 'runs/x/stage'; stage.mkdir(parents=True)
    (stage / 'a').write_text('valid')
    manifest = dict(status='VALIDATED', files={'a': sha(stage / 'a')})
    (stage / 'a').write_text('changed after validation')
    with pytest.raises(ValueError):
        versions.publish(store, stage, 'x', manifest)
    assert not (store / 'current.json').exists()


def test_published_pointer_can_finish_interrupted_journal(tmp_path):
    store = tmp_path / 's'; stage = store / 'runs/x/stage'; stage.mkdir(parents=True)
    (stage / 'a').write_text('valid')
    versions.publish(store, stage, 'x', dict(status='VALIDATED', files={'a': sha(stage / 'a')}))
    write(store / 'runs/x/journal.json', dict(status='PUBLISHING', run_id='x'))
    assert versions.recover(store, 'x') == 'COMMITTED'
    assert versions.current_snapshot(store).name == 'x'


def test_daily_revision_retains_original_and_reports_changed_date():
    old = pd.read_parquet(ROOT / 'data/processed/usd_uzs_daily.parquet')
    new = old.copy()
    new.loc[new.index[-1], 'raw_value'] += 1
    new.loc[new.index[-1], 'normalized_daily'] = new.iloc[-1].raw_value / new.iloc[-1].nominal
    new.loc[new.index[-1], 'clean_value'] = new.iloc[-1].normalized_daily
    new.loc[new.index[-1], 'retrieved_at'] = '2026-10-12T07:00:00Z'
    original = old.iloc[-1].raw_value
    merged, changed = engine.daily_changes(old, new, CUTOFF)
    assert len(changed) == 1 and merged.iloc[-1].raw_value == original + 1
    assert old.iloc[-1].raw_value == original


def test_pos_duplicate_total_rejected():
    client = ReceiptClient(); row, article = official_article(client)
    workbook = openpyxl.load_workbook(BytesIO((FIX / 'pos_apreily.xlsx').read_bytes()))
    sheet = workbook.worksheets[0]
    sheet.append(['Total', None, 1, 2, 3, 4])
    stream = BytesIO(); workbook.save(stream); workbook.close()
    client.altered = stream.getvalue()
    with pytest.raises(ValueError, match='Total'):
        pos.parse_article(article, client, row)


def test_pos_duplicate_releases_and_missing_periods_reported(monkeypatch):
    registry = load_registry(ROOT / 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx')
    articles = [('a', 'transactions carried out through POS'), ('b', 'transactions carried out through POS'),
                ('c', 'transactions carried out through POS')]
    monkeypatch.setattr(pos, 'enumerate_articles', lambda *a, **k: articles)
    monkeypatch.setattr(pos, 'download_article', lambda client, row, url, title: {'url': url})
    def parse(article, client, row):
        token = article['url']; period = '2023-01' if token in ['a', 'b'] else '2023-03'
        return dict(reference_period=period, reference_date=pd.Period(period, 'M').to_timestamp('M'),
                    raw_value=10. if token == 'a' else 11. if token == 'b' else 30., clean_value=np.nan,
                    source_release_date=None, checksum=token, article_url=token, quality_flag='', frequency='M')
    monkeypatch.setattr(pos, 'parse_article', parse)
    frame = pos.collect(None, registry.rows['pos_turnover'])
    assert not frame.reference_period.duplicated().any()
    assert {item['status'] for item in frame.attrs['archive_audit']} == {'DUPLICATE_RELEASE', 'MISSING_PERIOD'}


def test_source_reports_archive_failure_even_when_admission_fails(isolated):
    def fetch(k, *args):
        f = old_candidate(k, *args)
        if k == 'pos_turnover':
            f.attrs['archive_audit'] = [dict(status='ARTICLE_FAILED', article_url='test-only', error='bad header')]
            f.loc[f.index[0], 'raw_value'] = -1
            f.loc[f.index[0], 'clean_value'] = 1.
        return f
    result = run(isolated, fetch)
    status = next(s for s in result['source_status'] if s['variable_key'] == 'pos_turnover')
    assert status['archive_status'] == 'PARTIAL' and status['archive_failed_articles'] == 1
    assert status['state'] == 'VALIDATION_FAILED' and status['admission'] == 'RETAINED_PREVIOUS'
