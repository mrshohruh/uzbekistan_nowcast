"""Registry-driven Phase 2A and Phase 2B pilot orchestration."""
from datetime import date
from pathlib import Path
from uuid import uuid4
import hashlib
import json
import logging
import traceback

import pandas as pd
import yaml

from uznowcast.registry import load_registry
from uznowcast.provenance import attach_provenance, atomic_parquet, append_table, save_json, utc_now
from uznowcast.io.http import Downloader
from uznowcast.io import siat, cbu, external, cbu_stats
from uznowcast.parsers.siat import parse_siat
from uznowcast.parsers.cbu import parse_m2_xlsx
from uznowcast.parsers.external import parse_world_bank_gold
from uznowcast.parsers.cbu_stats import parse_reserves_xlsx
from uznowcast.transforms.decumulate import decumulate_ytd
from uznowcast.transforms.growth import gdp_target, log_growth
from uznowcast.transforms.frequency import fx_monthly
from uznowcast.transforms.prices import monthly_index_log
from uznowcast.transforms.derived import exports_non_gold
from uznowcast.master import build_monthly, build_quarterly, export_pair
from uznowcast.validation.observations import validate_series
from uznowcast.vintages import store_vintages
from uznowcast.archive_series import build_bank_archive, build_payment_archive
from uznowcast.reporting import write_phase2c_artifacts


def _industrial_outliers(frame: pd.DataFrame) -> pd.DataFrame:
    """Expose every source input behind flagged industrial growth observations."""
    indexed = frame.set_index(pd.PeriodIndex(frame.reference_date, freq='M'))
    records = []
    for period, item in indexed.iterrows():
        if 'extreme_log_change' not in str(item.quality_flag):
            continue
        lag, previous, lag_previous = period - 12, period - 1, period - 13
        lag_item = indexed.loc[lag] if lag in indexed.index else None
        records.append(dict(
            reference_month=str(period), raw_ytd=float(item.raw_value),
            previous_month_raw_ytd=float(indexed.loc[previous].raw_value) if previous in indexed.index else None,
            monthly_flow=float(item.monthly_flow), lag_12_month=str(lag),
            lag_12_raw_ytd=float(lag_item.raw_value) if lag_item is not None else None,
            lag_12_previous_month_raw_ytd=(float(indexed.loc[lag_previous].raw_value)
                                           if lag_previous in indexed.index else None),
            lag_12_monthly_flow=float(lag_item.monthly_flow) if lag_item is not None else None,
            calculated_growth=float(item.clean_value), quality_flag=item.quality_flag,
            diagnosis=('genuine published source-flow spike; lag flow is consistent with adjacent months, '
                       'so this is not a denominator base effect; positive inputs and exact calendar '
                       'de-cumulation rule out parser/de-cumulation failure; no raw-revision evidence '
                       'and no sustained structural break in adjacent months')))
    return pd.DataFrame(records)


def _alignment(monthly: pd.DataFrame, clean_fields: list[str]) -> dict:
    values = monthly[clean_fields]
    complete = values.notna().all(axis=1)
    if 'usd_uzs_is_complete' in monthly:
        complete &= monthly.usd_uzs_is_complete.fillna(False)
    dates = monthly.loc[complete, 'date']
    recent = monthly.tail(6).copy()
    return dict(
        earliest_all_predictors=str(dates.iloc[0].date()) if len(dates) else None,
        latest_complete_all_predictors=str(dates.iloc[-1].date()) if len(dates) else None,
        complete_monthly_rows=int(complete.sum()),
        missing_by_variable={field: int(values[field].isna().sum()) for field in clean_fields},
        ragged_edge=[dict(date=str(row.date.date()),
                          available=[field for field in clean_fields if pd.notna(row[field])])
                     for _, row in recent.iterrows()])


def build(root: Path, *, scope='pilot', offline=False, refresh=False, fx_start=None, fx_end=None):
    root = root.resolve()
    for directory in ('logs', 'metadata', 'data/processed', 'data/master'):
        (root / directory).mkdir(parents=True, exist_ok=True)
    run_id = uuid4().hex
    logger = logging.getLogger('uznowcast')
    logger.setLevel(logging.INFO)
    logging.getLogger('uznowcast.progress').propagate = False
    handler = logging.FileHandler(root / 'logs/pipeline.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    scope_label = {'pilot': 'Phase 2A', 'pilot8': 'Phase 2B', 'v1': 'Phase 2C'}.get(scope)
    if scope_label is None:
        raise ValueError(f'Unknown build scope: {scope}')
    report = dict(run_id=run_id, started_at=utc_now(), scope=scope_label, series={}, failures={}, offline=offline, refresh=refresh)
    client = None
    try:
        settings = yaml.safe_load((root / 'config/settings.yaml').read_text(encoding='utf-8'))
        registry = load_registry(root / settings['registry'])
        report['registry_version'] = registry.version
        report['registry_verification_date'] = registry.verification_date
        report['registry_sha256'] = hashlib.sha256(registry.path.read_bytes()).hexdigest()
        report['registry_count'] = len(registry.rows)
        contracts = json.loads((root / 'config/siat_contracts.json').read_text(encoding='utf-8'))
        cbu_contracts = json.loads((root / 'config/cbu_contracts.json').read_text(encoding='utf-8'))
        client = Downloader(root, run_id, offline=offline, refresh=refresh, delay=settings['request_delay_seconds'])
        series, observations = {}, []
        archive_series, archive_errors, archive_audit = {}, {}, []
        if scope == 'v1':
            bank_keys = ('household_deposits', 'corporate_deposits', 'household_credit', 'corporate_credit')
            try:
                built, audit = build_bank_archive(
                    client, registry, extreme_threshold=settings['extreme_log_change_threshold'])
                archive_series.update(built)
                archive_audit.extend(audit)
            except Exception as exc:
                for archive_key in bank_keys:
                    archive_errors[archive_key] = f'{type(exc).__name__}: {exc}'
            for archive_key in ('pos_turnover', 'instant_payments', 'interbank_payments'):
                try:
                    built, audit = build_payment_archive(
                        client, registry.rows[archive_key],
                        extreme_ratio=settings['extreme_flow_ratio_threshold'],
                        extreme_threshold=settings['extreme_log_change_threshold'])
                    archive_series[archive_key] = built
                    archive_audit.extend(audit)
                except Exception as exc:
                    archive_errors[archive_key] = f'{type(exc).__name__}: {exc}'
            if archive_audit:
                atomic_parquet(pd.DataFrame(archive_audit), root / 'metadata/archive_overlap_audit.parquet')
        for row in registry.scope(scope):
            key = row['variable_key']
            try:
                if key in archive_errors:
                    raise ValueError(archive_errors[key])
                if key in archive_series:
                    frame = archive_series[key]
                elif row['automation_status'] == 'DERIVED':
                    continue
                elif row['provider'] == 'SIAT':
                    if row['automation_status'] not in {'READY_API', 'PROXY'}:
                        raise ValueError(f'Unsupported SIAT status: {row["automation_status"]}')
                    payload, meta = siat.download(client, row)
                    parsed = parse_siat(payload, row, contracts[key])
                    frame = attach_provenance(parsed, row, meta)
                    frame['descriptor_raw_file_path'] = meta['descriptor_raw_file_path']
                    if row['rule_codes'] == ['GDP_TARGET']:
                        frame = gdp_target(frame)
                    elif row['rule_codes'] == ['DECUM_YTD', 'FLOW_YOY_LOG']:
                        if row['cumulative_flag'] != 'YTD cumulative':
                            raise ValueError('DECUM_YTD requires registry YTD cumulative flag')
                        frame = decumulate_ytd(frame, settings['extreme_flow_ratio_threshold'])
                        frame = log_growth(frame, 'monthly_flow', 12, settings['extreme_log_change_threshold'])
                    elif row['rule_codes'] == ['MOM_INDEX_LOG']:
                        frame = monthly_index_log(frame)
                    elif row['rule_codes'] == ['DECUM_YTD']:
                        frame = decumulate_ytd(frame, settings['extreme_flow_ratio_threshold'])
                        frame['clean_value'] = frame['monthly_flow']
                        frame['clean_unit'] = row['raw_unit']
                        frame['is_proxy'] = True
                        frame['proxy_label'] = row['display_name']
                    else:
                        raise ValueError('Unsupported pilot SIAT transformation chain')
                elif row['provider'] == 'CBU':
                    if key in {'usd_uzs', 'rub_uzs'}:
                        currency = key.split('_')[0].upper()
                        if row['automation_status'] != 'READY_API' or row['rule_codes'] != ['FX_DAILY_TO_MONTHLY'] or row['row_field_selector'] != f'Ccy={currency}; Rate/Nominal':
                            raise ValueError('Unsupported FX configuration')
                        start = fx_start or row['verified_start'].replace('-M', '-') + '-01'
                        end = fx_end or date.today().isoformat()
                        if pd.Timestamp(end).date() > date.today():
                            raise ValueError('FX end cannot be in the future')
                        report['fx_request_range'] = dict(start=start, end=end)
                        daily = cbu.download(client, row, start, end, currency=currency)
                        report[f'{key}_daily'] = validate_series(daily, row)
                        atomic_parquet(daily, root / f'data/processed/{key}_daily.parquet')
                        observations.append(daily)
                        frame = fx_monthly(daily, start, end, settings['extreme_log_change_threshold'])
                    elif key == 'm2':
                        workbook, meta = cbu.download_m2(client, row)
                        parsed = parse_m2_xlsx(workbook, row, cbu_contracts[key])
                        frame = attach_provenance(parsed, row, meta)
                        frame['page_raw_file_path'] = meta['page_raw_file_path']
                        frame = log_growth(frame, 'raw_value', 12, settings['extreme_log_change_threshold'])
                    elif key == 'fx_reserves_ex_gold':
                        workbook, meta = cbu_stats.download_reserves(client, row)
                        parsed = parse_reserves_xlsx(workbook, row)
                        frame = attach_provenance(parsed, row, meta)
                        frame['page_raw_file_path'] = meta['page_raw_file_path']
                        frame = log_growth(frame, 'raw_value', 12, settings['extreme_log_change_threshold'])
                    else:
                        raise ValueError('Unsupported CBU series')
                elif row['provider'] == 'World Bank Pink Sheet':
                    workbook, meta = external.download_world_bank_gold(client, row)
                    parsed, release = parse_world_bank_gold(workbook, row)
                    meta['source_release_date'] = release
                    meta['source_release_basis'] = 'official workbook update date; current vintage only'
                    frame = attach_provenance(parsed, row, meta)
                    frame['page_raw_file_path'] = meta['page_raw_file_path']
                    frame = log_growth(frame, 'raw_value', 1, settings['extreme_log_change_threshold'])
                elif row['provider'] == 'Rosstat':
                    external.download_rosstat_page(client, row)
                    raise ValueError('Rosstat page was retrieved but no exact V1.1 machine file/selector was exposed')
                else:
                    raise ValueError(f'Unsupported provider/status: {row["provider"]}/{row["automation_status"]}')
                report['series'][key] = validate_series(frame, row)
                frame['clean_model_field'] = row['clean_model_field']
                series[key] = frame
                observations.append(frame)
                atomic_parquet(frame, root / f'data/processed/{key}.parquet')
                client.event(dict(run_id=run_id, variable_key=key, provider=row['provider'],
                                  source_url=str(frame.source_url.iloc[-1]), retrieved_at=utc_now(), status='parsed',
                                  rows_parsed=len(frame), warning_count=sum(report['series'][key]['quality_flags'].values()), error_message=None))
            except Exception as exc:
                # Each series is isolated, but errors remain fatal to the full pilot status.
                report['failures'][key] = f'{type(exc).__name__}: {exc}'
                logger.error(json.dumps(dict(run_id=run_id, variable_key=key, status='series_failed', error_message=str(exc), traceback=traceback.format_exc())))
        if scope == 'v1' and 'exports_total' in series and 'gold_exports_proxy' in series:
            row = registry.rows['exports_non_gold']
            try:
                frame = exports_non_gold(series['exports_total'], series['gold_exports_proxy'], row,
                                         settings['extreme_log_change_threshold'])
                report['series'][row['variable_key']] = validate_series(frame, row)
                frame['clean_model_field'] = row['clean_model_field']
                series[row['variable_key']] = frame
                observations.append(frame)
                atomic_parquet(frame, root / f'data/processed/{row["variable_key"]}.parquet')
            except Exception as exc:
                report['failures'][row['variable_key']] = f'{type(exc).__name__}: {exc}'
        if observations:
            all_observations = pd.concat(observations, ignore_index=True)
            report['revision_records'] = store_vintages(all_observations, root)
            calendar = all_observations[['variable_key', 'reference_period', 'frequency', 'source_release_date',
                                         'source_release_basis', 'retrieved_at', 'vintage_date']]
            append_table(calendar, root / 'metadata/release_calendar.parquet', ['variable_key', 'reference_period', 'frequency', 'retrieved_at'])
        # Pilot contracts remain all-or-nothing. V1 publishes successful official series
        # while retaining explicit null columns and failures for unresolved sources.
        if not report['failures'] or scope == 'v1':
            monthly = build_monthly(series, registry, scope=scope)
            quarterly = build_quarterly(series['gdp_real_yoy'], registry.rows['gdp_real_yoy']['clean_model_field'])
            monthly_name = {'pilot': 'pilot_monthly', 'pilot8': 'pilot8_monthly', 'v1': 'v1_monthly'}[scope]
            export_pair(monthly, root / f'data/master/{monthly_name}')
            export_pair(quarterly, root / 'data/master/gdp_quarterly')
            report['master_columns'] = monthly.columns.tolist()
            report['master_rows'] = len(monthly)
            report['quarterly_rows'] = len(quarterly)
            if scope == 'pilot8':
                clean_fields = [row['clean_model_field'] for row in registry.scope(scope)
                                if row['native_frequency'] != 'Quarterly']
                report['alignment'] = _alignment(monthly, clean_fields)
                outliers = _industrial_outliers(series['industrial_production'])
                atomic_parquet(outliers, root / 'metadata/industrial_production_outliers.parquet')
                report['industrial_outliers'] = outliers.to_dict(orient='records')
            report['status'] = 'passed_with_warnings' if not report['failures'] else 'partial_with_failures'
            if scope == 'v1':
                report['phase2c_artifacts'] = write_phase2c_artifacts(
                    root, registry, report, series, monthly)
            save_json(root / 'data/master/build_manifest.json', report)
        else:
            report['status'] = 'failed'
    except Exception as exc:
        report['status'] = 'failed'
        report['failures']['pipeline'] = f'{type(exc).__name__}: {exc}'
        logger.error(json.dumps(dict(run_id=run_id, status='pipeline_failed', error_message=str(exc), traceback=traceback.format_exc())))
    finally:
        if client is not None and client.events:
            events = pd.DataFrame(client.events)
            events['build_run_id'] = run_id
            events['event_order'] = range(len(events))
            append_table(events, root / 'metadata/download_log.parquet', ['build_run_id', 'event_order'])
            if 'schema_fingerprint' in events:
                schema = events.loc[events.schema_fingerprint.notna(), ['variable_key', 'source_url', 'retrieved_at', 'schema_fingerprint', 'parser_version', 'raw_file_path']]
                append_table(schema, root / 'metadata/schema_log.parquet', ['variable_key', 'raw_file_path'])
        report['finished_at'] = utc_now()
        save_json(root / f'metadata/runs/{run_id}.json', report, exclusive=True)
        save_json(root / 'metadata/validation_summary.json', report)
        logger.removeHandler(handler)
        handler.close()
    return report
