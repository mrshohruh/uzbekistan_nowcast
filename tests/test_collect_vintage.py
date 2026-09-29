"""Unit tests for the prospective vintage-collection command.

The tests are strictly offline: network access is blocked by the shared
``no_network`` fixture and every downloader call is stubbed. The goal is to
prove that ``collect-vintage`` reuses the existing archive/vintage machinery
with ``refresh=True`` and produces a run summary that preserves the fields
Phase 3B requires (retrieval and source-release timestamps, checksum-derived
identity, run-level counts, immutable audit trail).
"""
from __future__ import annotations

from pathlib import Path
import json

import pandas as pd

from uznowcast import collect_vintage as collect_module


def _stub_build(monkeypatch, tmp_path: Path) -> dict:
    (tmp_path / 'metadata').mkdir()
    (tmp_path / 'metadata/vintage_runs').mkdir()
    events = pd.DataFrame([
        dict(build_run_id='run-x', variable_key='gdp_real_yoy', status='downloaded',
             source_release_date='2026-09-25T09:40:00+00:00'),
        dict(build_run_id='run-x', variable_key='gdp_real_yoy', status='cache',
             source_release_date=None),
        dict(build_run_id='other', variable_key='m2', status='downloaded',
             source_release_date='2026-09-25T09:40:00+00:00'),
    ])
    events.to_parquet(tmp_path / 'metadata/download_log.parquet', index=False)
    observations = pd.DataFrame([dict(variable_key='gdp_real_yoy', vintage_date='2026-09-29T00:00:00Z')])
    observations.to_parquet(tmp_path / 'metadata/observations_long.parquet', index=False)
    pd.DataFrame(dict(variable_key=['gdp_real_yoy'], frequency=['Q'])).to_parquet(
        tmp_path / 'metadata/vintages.parquet', index=False)

    def fake_build(root, *, scope, offline, refresh, fx_start=None, fx_end=None):
        # collect-vintage must always call build with refresh=True, offline=False.
        assert refresh is True
        assert offline is False
        return dict(
            run_id='run-x',
            status='passed_with_warnings',
            registry_version='V1.1',
            registry_verification_date='2026-09-29',
            registry_sha256='deadbeef',
            series={'gdp_real_yoy': dict(rows=34, start='2018-03-31', end='2026-06-30',
                                          clean_count=34, quality_flags={})},
            failures={'russia_ipi': 'ValueError: Offline cache missing: ...'},
        )

    monkeypatch.setattr(collect_module, 'build', fake_build)
    return dict(events=events)


def test_collect_vintage_produces_immutable_summary(monkeypatch, tmp_path):
    _stub_build(monkeypatch, tmp_path)
    summary = collect_module.collect(tmp_path, scope='v1')
    assert summary['status'] == 'passed_with_warnings'
    assert summary['build_run_id'] == 'run-x'
    assert summary['registry_version'] == 'V1.1'
    assert summary['download_events']['downloaded'] == 1  # only this run's event counts
    assert summary['download_events']['cached'] == 1
    assert summary['automated'] == ['gdp_real_yoy']
    assert summary['unresolved'] == ['russia_ipi']
    gdp = next(row for row in summary['series'] if row['variable_key'] == 'gdp_real_yoy')
    assert gdp['status'] == 'automated'
    assert gdp['new_payloads'] == 1
    assert gdp['cache_hits'] == 1
    assert gdp['latest_source_release_date'] == '2026-09-25T09:40:00+00:00'
    russia = next(row for row in summary['series'] if row['variable_key'] == 'russia_ipi')
    assert russia['status'] == 'failed'
    assert 'Offline cache missing' in russia['error']

    # The prospective run summary is written to an exclusive path under the
    # metadata/vintage_runs/ ledger and mirrored to vintage_collection_latest.
    latest = json.loads((tmp_path / 'metadata/vintage_collection_latest.json').read_text())
    assert latest['collector_run_id'] == summary['collector_run_id']
    per_run_path = tmp_path / f'metadata/vintage_runs/{summary["collector_run_id"]}.json'
    assert per_run_path.exists()
    assert json.loads(per_run_path.read_text())['build_run_id'] == 'run-x'


def test_collect_vintage_always_refreshes(monkeypatch, tmp_path):
    calls = []

    def fake_build(root, *, scope, offline, refresh, fx_start=None, fx_end=None):
        calls.append(dict(offline=offline, refresh=refresh, scope=scope))
        return dict(run_id='r', status='passed_with_warnings', series={}, failures={})

    monkeypatch.setattr(collect_module, 'build', fake_build)
    collect_module.collect(tmp_path, scope='v1')
    assert calls == [dict(offline=False, refresh=True, scope='v1')]
