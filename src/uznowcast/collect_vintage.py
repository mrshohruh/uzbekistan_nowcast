"""Prospective vintage-collection driver.

Runs the registry-driven downloaders with ``refresh=True`` so every current
official source is re-fetched, archived and checksummed. The existing
``build`` pipeline already:

* writes each response to an immutable file under ``data/raw/``;
* records the retrieval timestamp on every downloader event;
* records the source update/release timestamp when the provider exposes it
  (SIAT ``updated_at``, CBU statistical page timestamp, CBU archive article
  release timestamp, World Bank Pink Sheet workbook update date);
* computes a SHA-256 checksum plus schema fingerprint of the payload;
* only stores a new vintage row when the observation identity (``variable_key``,
  ``reference_period``, ``frequency``, ``retrieved_at``, ``checksum``,
  ``parser_version``) changes;
* leaves every earlier vintage in ``metadata/observations_long.parquet`` and
  ``metadata/vintages.parquet`` untouched, and appends detected revisions to
  ``metadata/revisions.parquet``.

``collect-vintage`` reuses that machinery and post-processes the report into a
human-readable prospective run summary written to
``metadata/vintage_runs/{run_id}.json``.

This is intentionally a *collection* command: it does not smooth, interpolate,
splice, or add a nowcasting model. The Rosstat variable
(``russia_ipi``) is not collected here unless the operator opts in through
``UZNOWCAST_USE_SYSTEM_TRUST=1``; otherwise it fails with the same visible
error the standard build reports.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json

import pandas as pd

from uznowcast.pipeline import build
from uznowcast.provenance import save_json


def _pre_snapshot(root: Path) -> dict:
    def _rows(path: Path) -> int:
        return int(len(pd.read_parquet(path))) if path.exists() else 0
    return dict(
        observations=_rows(root / 'metadata/observations_long.parquet'),
        vintages=_rows(root / 'metadata/vintages.parquet'),
        revisions=_rows(root / 'metadata/revisions.parquet'),
    )


def _download_summary(root: Path, run_id: str) -> dict:
    path = root / 'metadata/download_log.parquet'
    if not path.exists():
        return dict(events=0, downloaded=0, cached=0, failed=0)
    frame = pd.read_parquet(path)
    if 'build_run_id' in frame:
        frame = frame.loc[frame.build_run_id == run_id]
    counts = frame.status.value_counts().to_dict() if 'status' in frame else {}
    return dict(
        events=int(len(frame)),
        downloaded=int(counts.get('downloaded', 0)),
        cached=int(counts.get('cache', 0)),
        failed=int(counts.get('failed', 0) + counts.get('http_error', 0)
                   + counts.get('network_error', 0)),
    )


def _series_summary(root: Path, run_id: str, report: dict) -> list[dict]:
    events_path = root / 'metadata/download_log.parquet'
    events = pd.read_parquet(events_path) if events_path.exists() else pd.DataFrame()
    if not events.empty and 'build_run_id' in events:
        events = events.loc[events.build_run_id == run_id]
    entries = []
    for key, info in report.get('series', {}).items():
        variable_events = events.loc[events.variable_key == key] if not events.empty else events
        downloaded = int((variable_events.get('status') == 'downloaded').sum()) if not variable_events.empty else 0
        cached = int((variable_events.get('status') == 'cache').sum()) if not variable_events.empty else 0
        release_dates = pd.Series(dtype='object')
        if 'source_release_date' in variable_events:
            release_dates = variable_events.source_release_date.dropna()
        entries.append(dict(
            variable_key=key, status='automated',
            rows=info.get('rows'),
            start=info.get('start'), end=info.get('end'),
            clean_count=info.get('clean_count'),
            new_payloads=downloaded, cache_hits=cached,
            latest_source_release_date=(release_dates.max() if not release_dates.empty else None),
        ))
    for key, error in report.get('failures', {}).items():
        entries.append(dict(variable_key=key, status='failed', error=error,
                            rows=0, new_payloads=0, cache_hits=0))
    return entries


def collect(root: Path, *, scope: str = 'v1') -> dict:
    """Run a prospective vintage-collection pass.

    Always uses ``refresh=True``: cached payloads are re-fetched from the
    official sources so any changed observation or schema is detected. The
    existing archive/vintage machinery guarantees older files are never
    overwritten and no observation is ever silently modified.
    """
    root = root.resolve()
    started_at = datetime.now(timezone.utc).isoformat()
    before = _pre_snapshot(root)
    report = build(root, scope=scope, offline=False, refresh=True)
    after = _pre_snapshot(root)
    run_id = report['run_id']
    summary = dict(
        collector_run_id=uuid4().hex,
        build_run_id=run_id,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc).isoformat(),
        scope=scope,
        status=report.get('status'),
        registry_version=report.get('registry_version'),
        registry_verification_date=report.get('registry_verification_date'),
        registry_sha256=report.get('registry_sha256'),
        download_events=_download_summary(root, run_id),
        observations_before=before['observations'],
        observations_after=after['observations'],
        new_observation_rows=after['observations'] - before['observations'],
        vintages_before=before['vintages'],
        vintages_after=after['vintages'],
        new_vintage_rows=after['vintages'] - before['vintages'],
        revisions_before=before['revisions'],
        revisions_after=after['revisions'],
        new_revision_rows=after['revisions'] - before['revisions'],
        automated=list(report.get('series', {}).keys()),
        unresolved=list(report.get('failures', {}).keys()),
        series=_series_summary(root, run_id, report),
        note=('Older vintages retained; new payloads only stored where the '
              'observation identity or checksum changed. Rosstat russia_ipi '
              'remains unresolved unless UZNOWCAST_USE_SYSTEM_TRUST=1 and the '
              'operator has installed the Russian Trusted Root CA into the OS '
              'trust store.'),
    )
    destination = root / f'metadata/vintage_runs/{summary["collector_run_id"]}.json'
    save_json(destination, summary, exclusive=True)
    save_json(root / 'metadata/vintage_collection_latest.json', summary)
    return summary
