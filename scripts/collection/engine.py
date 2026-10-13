"""Collect nine approved source families without fitting or publishing forecasts."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import shutil
import uuid

import numpy as np
import pandas as pd

from scripts.operations.acquisition import ACTIVE, acquire, compare, real_industry_contract
from scripts.operations.state import operational_lock, pending_transactions, read, write, sha
from scripts.collection.http import CollectionDownloader, SourceError, failure_kind
from scripts.collection import pos, versions
from uznowcast.master import build_quarterly
from uznowcast.provenance import atomic_parquet, append_table
from uznowcast.registry import load_registry
from uznowcast.validation.observations import validate_series
from uznowcast.vintages import store_vintages, compare_revisions

KEYS = (*ACTIVE, 'gdp_real_yoy')
EXITS = {'NO_INFORMATION_CHANGE': 0, 'COLLECTION_VALIDATED': 0, 'COLLECTION_COMMITTED': 0,
         'COLLECTION_DEGRADED': 2, 'COLLECTION_ABORTED': 3, 'COLLECTION_BLOCKED': 4}


def seed(root, stage, previous):
    """Copy mutable collection inputs, never copy or execute model code."""
    stage.mkdir(parents=True)
    for relative in ['config/siat_contracts.json', 'config/cbu_contracts.json', 'config/industry_source.json']:
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, target)
    if previous:
        for folder in ['data', 'metadata']:
            shutil.copytree(previous / folder, stage / folder)
    else:
        paths = [f'data/processed/{key}.parquet' for key in KEYS]
        paths += [f'data/processed/{key}_daily.parquet' for key in ['usd_uzs', 'rub_uzs']]
        paths += ['data/master/v1_monthly.parquet', 'data/master/gdp_quarterly.parquet',
                  'metadata/observations_long.parquet', 'metadata/vintages.parquet',
                  'metadata/download_log.parquet']
        if (root / 'metadata/revisions.parquet').exists():
            paths.append('metadata/revisions.parquet')
        for relative in paths:
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        recovery = pd.read_csv(root / 'data/current/predictor_provenance.csv', float_precision='round_trip')
        for key in ['industrial_production', 'pos_turnover']:
            frame = recovery.loc[recovery.variable_key.eq(key) & recovery.selected_for_panel.eq(True)].copy()
            frame['reference_date'] = pd.to_datetime(frame.reference_date)
            frame['quality_flag'] = ''
            frame['vintage_date'] = frame.retrieved_at
            if key == 'pos_turnover':
                values = pd.read_csv(root / 'data/current/recovered_monthly.csv', float_precision='round_trip')
                values = values.set_index('reference_period')
                frame['clean_value'] = frame.reference_period.map(values.pos_turnover_monthly_log_yoy)
                frame = frame.loc[frame.reference_period.le('2024-12')].copy()
            atomic_parquet(frame, stage / f'data/recovery/{key}.parquet')


def daily_changes(old, new, asof):
    """Validate daily candidates before retaining changed activation observations."""
    if new.empty or new.reference_date.duplicated().any() or set(new.frequency) != {'D'}:
        raise ValueError('Invalid/duplicate daily FX periods')
    if not new.reference_date.is_monotonic_increasing:
        raise ValueError('Daily FX not sorted')
    for column in ['raw_value', 'nominal', 'normalized_daily']:
        if not np.isfinite(new[column]).all() or new[column].le(0).any():
            raise ValueError('Invalid daily FX numeric/nominal value')
    if not np.allclose(new.normalized_daily, new.raw_value / new.nominal, rtol=0, atol=1e-12):
        raise ValueError('Daily FX normalization changed')
    if new.reference_date.max().date() > asof.tz_convert('Asia/Tashkent').date():
        raise ValueError('Future daily activation')
    retrieval = pd.to_datetime(new.retrieved_at, utc=True, errors='coerce', format='mixed')
    release = pd.to_datetime(new.source_release_date, utc=True, errors='coerce', format='mixed')
    if retrieval.isna().any() or retrieval.gt(asof).any() or release.gt(asof).any():
        raise ValueError('Future/missing daily retrieval or release')
    by = old.set_index('reference_date')
    changed = []
    for date, row in new.set_index('reference_date').iterrows():
        if date not in by.index or any(float(row[c]) != float(by.loc[date, c])
                                      for c in ['raw_value', 'nominal', 'normalized_daily']):
            changed.append(date)
    additions = new.loc[new.reference_date.isin(changed)].copy()
    merged = pd.concat([old.loc[~old.reference_date.isin(changed)], additions], ignore_index=True)
    return merged.sort_values('reference_date').reset_index(drop=True), additions


def default_fetch(key, client, registry, root, working, asof):
    if key == 'pos_turnover':
        return pos.collect(client, registry.rows[key])
    # Existing exact source adapters/transforms; the working FX daily store is cumulative.
    return acquire(key, client, registry, working if key in ['usd_uzs', 'rub_uzs'] else root,
                   asof.tz_convert('Asia/Tashkent').tz_localize(None), real=key == 'industrial_production')


def _verified_gdp(root, asof):
    verified = set()
    for path in (root / 'results/operations/prospective/realization_records').glob('*.json'):
        if path.name.endswith('.seal.json'):
            continue
        item = read(path)
        if (item['event_kind'] == 'FIRST_RELEASE' and pd.Timestamp(item['ingested_timestamp']) <= asof
                and pd.Timestamp(item['first_release_date']).date() < asof.tz_convert('Asia/Tashkent').date()):
            verified.add(item['target_quarter'])
    return verified


def collect(root: Path, *, store=None, commit=False, offline=False, asof=None,
            fetch=default_fetch, client_factory=CollectionDownloader, verify_seal=True):
    root = Path(root).resolve()
    store = Path(store).resolve() if store else root / 'data/collection'
    started = pd.Timestamp(datetime.now(timezone.utc))
    asof = pd.Timestamp(asof) if asof is not None else started
    asof = asof.tz_localize('UTC') if asof.tzinfo is None else asof.tz_convert('UTC')
    if asof > started:
        raise ValueError('Future collection cutoff forbidden')
    if not offline and asof < started - pd.Timedelta(minutes=1):
        raise ValueError('Historical cutoff requires --offline; never backdate live retrievals')
    run_id = 'collect_' + started.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8]
    run = store / 'runs' / run_id
    run.mkdir(parents=True, exist_ok=False)
    handler = logging.FileHandler(run / 'collection.log', encoding='utf-8')
    logger = logging.getLogger('uznowcast.collection')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    result = dict(run_id=run_id, started_at_utc=started.isoformat(),
                  local_time=started.tz_convert('Asia/Tashkent').isoformat(),
                  cutoff_utc=asof.isoformat(), mode='COMMIT_COLLECTION_VERSION' if commit else 'DRY_RUN',
                  production_promoted=False, forecasts_calculated=False, scheduled_days=[1, 11, 21],
                  timezone='Asia/Tashkent', source_status=[], status='COLLECTION_ABORTED')
    stage = run / 'stage'
    journal_started = False
    try:
        with operational_lock(root):
            if pending_transactions(root):
                raise versions.InterruptedRun('Legacy interrupted promotion requires recovery')
            versions.assert_no_pending(store)
            if verify_seal:
                from scripts.operations.state import model_lock, verify_current_version
                model_lock(root)
                verify_current_version(root)
            registry = load_registry(root / 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx')
            previous = versions.current_snapshot(store)
            seed(root, stage, previous)
            write(run / 'journal.json', dict(status='COLLECTING', run_id=run_id))
            journal_started = True
            client = client_factory(root, run / 'receipts', run_id, offline=offline)
            # Collection versions contribute their own receipts to the next cache.
            history = pd.read_parquet(stage / 'metadata/download_log.parquet')
            for item in history.loc[history.http_status.eq(200) & history.raw_file_path.notna()].sort_values('retrieved_at').to_dict('records'):
                client.cache[(item['variable_key'], item['source_url'])] = item
            changes, archive_audit, observed, validation_reports = [], [], [], {}
            changed = False
            critical = False
            verified_gdp = _verified_gdp(root, asof)
            for key in KEYS:
                status = dict(variable_key=key, reachability='LIVE_NOT_TESTED' if offline else 'NOT_TESTED',
                              download='NOT_TESTED', parser='NOT_TESTED', validation='NOT_TESTED',
                              admission='NOT_TESTED', state='UNCHANGED', retained_previous=True)
                try:
                    candidate = fetch(key, client, registry, root, stage, asof)
                    daily = candidate.attrs.pop('daily', None)
                    audit = candidate.attrs.pop('archive_audit', [])
                    archive_audit.extend(dict(item, variable_key=key) for item in audit)
                    status.update(archive_failed_articles=sum(a['status'] == 'ARTICLE_FAILED' for a in audit),
                                  archive_missing_periods=sum(a['status'] == 'MISSING_PERIOD' for a in audit),
                                  archive_status='PARTIAL' if audit else 'NOT_APPLICABLE_OR_COMPLETE')
                    row = real_industry_contract(root, registry)[0] if key == 'industrial_production' else registry.rows[key]
                    validation = validate_series(candidate, row)
                    validation_reports[key] = validation
                    status.update(download='ARCHIVED_RECEIPT' if offline else 'DOWNLOAD_OK', parser='PARSE_OK',
                                  reachability='LIVE_NOT_TESTED' if offline else 'REACHABLE',
                                  validation=validation['status'], candidate_latest=candidate.reference_period.max())
                    status['warning_count'] = len(validation['warnings'])
                    status['missing_period_count'] = len(validation['missing_periods'])
                    if 'unit' in candidate and not candidate.unit.eq(row['raw_unit']).all():
                        raise ValueError('Candidate unit differs from approved contract')
                    rel = f'data/recovery/{key}.parquet' if key == 'industrial_production' else f'data/processed/{key}.parquet'
                    old = pd.read_parquet(stage / rel)
                    label = key + '_approved_real' if key == 'industrial_production' else key
                    if key == 'pos_turnover':
                        # Comparable post-2024 admission remains closed even if a candidate claims scope.
                        candidate['scope_verified'] = False
                        withheld = candidate.loc[candidate.reference_period.gt('2024-12')].copy()
                        # Keep unapproved candidate evidence in run diagnostics, outside committed data.
                        if len(withheld):
                            atomic_parquet(withheld, run / 'pos_scope_withheld.parquet')
                            changes.extend(dict(variable=key, variable_key=key, period=r['reference_period'],
                                                old_value=None, new_value=r['clean_value'], accepted=False,
                                                change_type='SCOPE_WITHHELD', reason='SCOPE_VERIFICATION_REQUIRED')
                                           for r in withheld.to_dict('records'))
                        candidate = candidate.loc[candidate.reference_period.le('2024-12')].copy()
                        if candidate.empty:
                            status.update(admission='SCOPE_WITHHELD', state='SCOPE_WITHHELD',
                                          limitation='No approved <=2024-12 POS candidates; previous recovery retained')
                            result['source_status'].append(status)
                            continue
                    accepted, decisions, valid = compare(label, old, candidate, asof if offline else pd.Timestamp.now(tz='UTC'),
                                                        gdp=key == 'gdp_real_yoy', pos=key == 'pos_turnover',
                                                        verified_gdp=verified_gdp)
                    if not valid:
                        changes.extend(dict(d, variable_key=key) for d in decisions)
                        raise SourceError('VALIDATION_FAILED', 'Candidate validation/admission failed; see observation_decisions.csv')
                    daily_result = None
                    if daily is not None:
                        daily_rel = f'data/processed/{key}_daily.parquet'
                        daily_result = daily_changes(pd.read_parquet(stage / daily_rel), daily,
                                                     asof if offline else pd.Timestamp.now(tz='UTC'))
                    admitted = [d['period'] for d in decisions if d['accepted']]
                    # Nothing is written until both monthly and daily validation succeeds.
                    if admitted:
                        atomic_parquet(accepted, stage / rel)
                        latest = candidate.loc[candidate.reference_period.isin(admitted)].copy()
                        if key == 'industrial_production':
                            revisions = compare_revisions(old, latest)
                            if len(revisions):
                                append_table(revisions, stage / 'metadata/recovery_revisions.parquet',
                                             ['variable_key', 'reference_period', 'old_vintage_date', 'new_vintage_date', 'value_field'])
                            append_table(latest, stage / 'metadata/recovery_observations_long.parquet',
                                         ['variable_key', 'reference_period', 'retrieved_at', 'checksum', 'parser_version'])
                        else:
                            observed.append(latest)
                        changed = True
                    if daily_result is not None and len(daily_result[1]):
                        atomic_parquet(daily_result[0], stage / daily_rel)
                        observed.append(daily_result[1])
                        changed = True
                        status['daily_changes'] = len(daily_result[1])
                    changes.extend(dict(d, variable_key=key) for d in decisions)
                    status.update(admission='ACCEPTED' if admitted else 'RETAINED_OR_WITHHELD',
                                  state='UPDATED' if admitted or status.get('daily_changes') else 'UNCHANGED',
                                  approved_latest=accepted.loc[accepted.clean_value.notna(), 'reference_period'].max())
                    if any(item['status'] in {'ARTICLE_FAILED', 'MISSING_PERIOD', 'DUPLICATE_RELEASE'} for item in audit):
                        status['state'] = 'PARTIAL_ARCHIVE'
                    if key == 'pos_turnover':
                        status['limitation'] = 'Production POS eligibility remains <= 2024-12; reviewed recovery unchanged'
                    if key == 'gdp_real_yoy':
                        status['limitation'] = 'Unverified new GDP periods withheld; observed update is not first release'
                except Exception as error:
                    kind = failure_kind(error)
                    status.update(state=kind, error_type=type(error).__name__, error=str(error),
                                  admission='RETAINED_PREVIOUS')
                    if kind == 'NETWORK_ENVIRONMENT_ERROR':
                        status['reachability'] = 'LIVE_NOT_TESTED'
                    own = [e for e in client.events if e.get('variable_key') == key]
                    if own and any(e.get('http_status') == 200 for e in own):
                        status['reachability'] = 'LIVE_NOT_TESTED' if offline else 'REACHABLE'
                        status['download'] = 'ARCHIVED_RECEIPT' if offline else 'DOWNLOAD_OK'
                    if kind in {'SCHEMA_ERROR', 'FORMAT_ERROR'} and status['parser'] == 'NOT_TESTED':
                        status['parser'] = 'FAILED'
                    critical |= key == 'usd_uzs' and kind in {'SCHEMA_ERROR', 'FORMAT_ERROR', 'VALIDATION_FAILED'}
                result['source_status'].append(status)
            pd.DataFrame(changes).to_csv(run / 'observation_decisions.csv', index=False)
            write(run / 'validation_reports.json', validation_reports)
            pd.DataFrame(archive_audit).to_csv(run / 'archive_audit.csv', index=False)
            pd.DataFrame(client.receipts).to_csv(run / 'source_receipts.csv', index=False)
            if critical:
                raise ValueError('Critical USD validation failure; no collection version published')
            if observed:
                store_vintages(pd.concat(observed, ignore_index=True), stage)
            if client.events:
                events = pd.DataFrame(client.events)
                events['build_run_id'] = run_id
                events['event_order'] = range(len(events))
                append_table(events, stage / 'metadata/download_log.parquet', ['build_run_id', 'event_order'])
            # Preserve inactive columns and nominal industry master; update active canonical fields only.
            monthly = pd.read_parquet(stage / 'data/master/v1_monthly.parquet').set_index('date')
            series = {key: pd.read_parquet(stage / f'data/processed/{key}.parquet') for key in ACTIVE
                      if key != 'industrial_production'}
            for key, frame in series.items():
                dates = pd.to_datetime(frame.reference_date)
                monthly = monthly.reindex(monthly.index.union(dates))
                monthly.loc[dates, registry.rows[key]['clean_model_field']] = frame.clean_value.to_numpy()
            monthly = monthly.sort_index().reindex(pd.date_range(monthly.index.min(), monthly.index.max(), freq='ME'))
            monthly = monthly.rename_axis('date').reset_index()
            if not monthly.date.is_unique or monthly.columns.duplicated().any() or 'gdp_real_yoy_pct' in monthly:
                raise ValueError('Invalid collection monthly master')
            atomic_parquet(monthly, stage / 'data/master/v1_monthly.parquet')
            gdp = build_quarterly(pd.read_parquet(stage / 'data/processed/gdp_real_yoy.parquet'), 'gdp_real_yoy_pct')
            atomic_parquet(gdp, stage / 'data/master/gdp_quarterly.parquet')
            # Explicit approved predictor view: POS recovery stays closed after Dec2024,
            # and approved real industry never becomes nominal master output.
            panel = monthly[['date']].copy().set_index('date')
            for key in ACTIVE:
                if key in ['industrial_production', 'pos_turnover']:
                    frame = pd.read_parquet(stage / f'data/recovery/{key}.parquet')
                    if key == 'pos_turnover':
                        frame = frame.loc[frame.reference_period.le('2024-12')]
                    values = pd.Series(frame.clean_value.to_numpy(dtype=float), index=pd.to_datetime(frame.reference_date))
                    panel[key] = values.reindex(panel.index)
                else:
                    panel[key] = monthly.set_index('date')[registry.rows[key]['clean_model_field']]
            atomic_parquet(panel.reset_index(), stage / 'data/master/production_predictors.parquet')
            files = {p.relative_to(stage).as_posix(): sha(p) for p in sorted(stage.rglob('*')) if p.is_file()}
            manifest = dict(status='VALIDATED', run_id=run_id, files=files, source_repository=str(root),
                            previous_version=previous.name if previous else None,
                            registry_hash=sha(root / 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx'),
                            model_definitions_hash=sha(root / 'config/model_definitions.json'),
                            collector_code_hashes={p.name: sha(p) for p in Path(__file__).parent.glob('*.py')},
                            approved_pos_scope_end='2024-12', forecast_execution=False)
            write(run / 'candidate_manifest.json', manifest)
            degraded = any(s['state'] not in {'UPDATED', 'UNCHANGED'} for s in result['source_status'])
            result['information_changed'] = changed
            result['status'] = 'COLLECTION_DEGRADED' if degraded else 'COLLECTION_VALIDATED' if changed else 'NO_INFORMATION_CHANGE'
            if commit and changed:
                version = versions.publish(store, stage, run_id, manifest)
                result.update(committed_version=str(version), collection_committed=True)
                if not degraded:
                    result['status'] = 'COLLECTION_COMMITTED'
            else:
                write(run / 'journal.json', dict(status='DRY_RUN_COMPLETE' if not commit else 'NO_INFORMATION_CHANGE', run_id=run_id))
    except Exception as error:
        result.update(status='COLLECTION_BLOCKED' if isinstance(error, (versions.InterruptedRun, RuntimeError)) else 'COLLECTION_ABORTED',
                      error_type=type(error).__name__, error=str(error))
        if journal_started:
            # A PUBLISHING journal must survive an interruption for explicit recovery.
            state = read(run / 'journal.json')
            if state['status'] != 'PUBLISHING':
                write(run / 'journal.json', dict(state, status='ABORTED'))
    finally:
        result['exit_code'] = EXITS[result['status']]
        result['finished_at_utc'] = pd.Timestamp.now(tz='UTC').isoformat()
        write(run / 'run_manifest.json', result)
        pd.DataFrame(result['source_status']).to_csv(run / 'source_status.csv', index=False)
        logger.removeHandler(handler)
        handler.close()
    return result
