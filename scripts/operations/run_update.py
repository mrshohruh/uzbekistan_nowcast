"""One safe entry point for source refresh, current production and frozen shadow operations."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import logging
import os
import shutil
from pathlib import Path
import sys
import uuid
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.operations.state import (sha,read,write,preflight,verify,operational_lock,promote,pending_transactions,model_lock,validate_current_manifest,verify_current_version,rollback_completed)
from scripts.operations.acquisition import (ACTIVE,CHANGE_COLUMNS,RECEIPT_COLUMNS,OperationsDownloader,acquire,compare,real_industry_contract,critical_validation_error)
from scripts.operations.workspace import seed,worker,current_check
from scripts.operations.pos_review import reviewed_pos
from uznowcast.registry import load_registry
from uznowcast.master import build_monthly,build_quarterly
from uznowcast.provenance import atomic_parquet,append_table
from uznowcast.vintages import store_vintages
from uznowcast.models.data import load_dataset,information_cutoff_for_variable
from uznowcast.operational.forecast import generate_nowcasts,detect_target_quarter
from uznowcast.operational.forecast import detect_operational_stage
from uznowcast.storage import records


SHADOW_MUTABLE={f'results/operations/prospective/{name}' for name in [
    'run_manifest.json','data_status.csv','prospective_target_registry.csv','realization_registry.csv',
    'revision_history.csv','scored_forecasts.csv','primary_scored_forecasts.csv','prospective_metrics.csv',
    'combination_diagnostics.csv','combination_correlations.csv','research_challenger_registry.csv',
    'report.md','results.md']}
LEDGER='results/operations/prospective/prospective_forecast_ledger.csv'


def csv(out,name,rows,columns=None):
    pd.DataFrame(rows,columns=columns).to_csv(out/name,index=False)


def cutoff(args):
    now=pd.Timestamp(datetime.now(timezone.utc))
    if not args.as_of:return now,False
    day=pd.Timestamp(args.as_of).tz_localize('Asia/Tashkent')
    today=now.tz_convert('Asia/Tashkent').normalize()
    if day>today:raise ValueError('Future --as-of dates are forbidden')
    return min(now,day+pd.Timedelta(days=1)-pd.Timedelta(microseconds=1)).tz_convert('UTC'),day<today


def inventory(root,registry,asof,states=None):
    rows=[];real=real_industry_contract(root,registry)[0]
    research=pd.read_csv(root/'data/current/predictor_provenance.csv')
    for key in (*ACTIVE,'gdp_real_yoy'):
        row=real if key=='industrial_production' else registry.rows[key]
        path=root/f'data/processed/{key}.parquet';frame=pd.read_parquet(path)
        if key=='industrial_production':
            frame=research.loc[research.variable_key.eq(key)&research.selected_for_panel.eq(True)].copy()
            overlay=root/'data/operations/shadow_observations.parquet'
            if overlay.exists():
                extra=pd.read_parquet(overlay);frame=pd.concat([frame,extra.loc[extra.variable_key.eq(key)]],ignore_index=True)
        if key=='pos_turnover':frame=frame.loc[frame.reference_period.le('2024-12')]
        frame=frame.loc[frame.clean_value.notna()]
        latest=frame.reference_period.max() if len(frame) else None
        lag=int(registry.rows[key]['typical_publication_lag_days'])
        local=asof.tz_convert('Asia/Tashkent').tz_localize(None)
        if key=='gdp_real_yoy':
            candidate=local-pd.Timedelta(days=lag);expected=candidate.to_period('Q')
            if expected.end_time.normalize()>candidate:expected-=1
        else:expected=information_cutoff_for_variable(local,key,{key:lag},'standard').to_period('M')
        stale=max(0,expected.ordinal-pd.Period(latest,expected.freq).ordinal) if latest else None
        state=(states or {}).get(key,'CACHED_NOT_NETWORK_CHECKED')
        rows.append(dict(variable=key,source=row['provider'],source_url_or_identifier=row['machine_download_url'] or row['human_source_url'],
            frequency=row['native_frequency'],release_lag=lag,latest_stored_observation=latest,expected_latest_observation=str(expected),
            current_status=state,model_usage='PRODUCTION_AND_SHADOW' if key in {'usd_uzs','gdp_real_yoy'} else 'FROZEN_DFM',
            latest_usable_month=latest,expected_latest_month=str(expected),months_stale=stale,
            missing_recent=None,source_status=state,model_status='USABLE_WITH_GAPS' if latest else 'UNUSABLE',
            warning='POS scope after December 2024 withheld; never filled' if key=='pos_turnover' else 'Unknown releases remain null; lag is planning metadata',
            classification='RED' if latest is None or stale>2 else 'AMBER' if stale or state=='SOURCE_UNAVAILABLE' else 'GREEN'))
    return rows


def validate_masters(staged,registry):
    monthly=pd.read_parquet(staged/'data/master/v1_monthly.parquet');gdp=pd.read_parquet(staged/'data/master/gdp_quarterly.parquet')
    expected=['date']+[r['clean_model_field'] for r in registry.scope('v1') if r['native_frequency']!='Quarterly']
    if list(monthly.columns)!=expected or monthly.date.duplicated().any() or not monthly.date.is_monotonic_increasing:
        raise ValueError('Candidate monthly master schema/date validation failed')
    if 'gdp_real_yoy_pct' in monthly or gdp.quarter.duplicated().any():raise ValueError('Invalid GDP separation or duplicate quarters')
    if np.isinf(monthly.select_dtypes('number').to_numpy()).any():raise ValueError('Infinite master observations')


def production(staged,preview,asof):
    dataset=load_dataset(staged);target=detect_target_quarter(dataset,str(min(asof.tz_localize(None),pd.Period(preview['target'],'Q').end_time).date()))
    if target['target_quarter']!=preview['target']:raise ValueError('Production and shadow target context differ')
    stage=detect_operational_stage(dataset,preview['target'],str(asof.tz_convert('Asia/Tashkent').date()))
    hashes=dict(monthly_master_hash=sha(staged/'data/master/v1_monthly.parquet'),quarterly_master_hash=sha(staged/'data/master/gdp_quarterly.parquet'),
        registry_hash=sha(staged/'registry/uzbekistan_nowcasting_v1.2_registry.xlsx'))
    frame,_=generate_nowcasts(dataset,str(asof.tz_convert('Asia/Tashkent').date()),target,stage,hashes,asof.isoformat())
    if len(frame)!=4 or not np.isfinite(frame.prediction).all():raise ValueError('Critical production predictor/GDP lag unusable')
    return [dict(target_quarter=preview['target'],horizon=stage['horizon'],model=r['model'],forecast=float(r['prediction']),
        as_of_date=str(asof.tz_convert('Asia/Tashkent').date()),information_cutoff=asof.isoformat(),status='CURRENT_STATE_REPRODUCTION') for r in frame.to_dict('records')]


def shadow_delta(root,preview):
    withdrawn={read(p)['snapshot_id'] for p in (root/'results/operations/prospective/withdrawal_records').glob('*.json') if not p.name.endswith('.seal.json')}
    ledger=pd.read_csv(root/LEDGER)
    previous=ledger.loc[ledger.target_quarter.eq(preview['target']) & ~ledger.snapshot_id.isin(withdrawn)].sort_values('run_timestamp_utc').groupby('model').tail(1)
    values={r['model']:r for r in previous.to_dict('records')}
    return [dict(model=model,previous_forecast=values.get(model,{}).get('forecast'),current_forecast=value,
        revision=value-values[model]['forecast'] if model in values and value is not None else None,
        previous_information_cutoff=values.get(model,{}).get('information_cutoff'),current_information_cutoff=preview.get('cutoff_utc'),
        attribution='Descriptive changed inputs only; no causal decomposition') for model,value in preview['forecasts'].items()]


def run(args,root=ROOT):
    stamp=datetime.now(timezone.utc);run_id='update_'+stamp.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
    out=root/'results/operations'/run_id;out.mkdir(parents=True,exist_ok=False)
    logger=logging.getLogger('uznowcast');logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    handler=logging.FileHandler(out/'operations.log',encoding='utf-8');handler.setFormatter(logging.Formatter('%(message)s'));logger.addHandler(handler)
    staged=root/'data/staging'/run_id/'project'
    status='UPDATE_ABORTED';failure=None;preview=None;before=None;states={};changes=[];receipts=[];production_rows=[];promotion=[]
    appended=False;master_changed={'monthly':False,'quarterly':False};frozen_changed=False;client=None;actual_promoted={}
    mode='CHECK_ONLY' if args.check_only else 'DRY_RUN' if args.dry_run else 'LIVE'
    try:
        with operational_lock(root):
            if pending_transactions(root):raise RuntimeError('Unfinished promotion transaction requires recovery before update')
            asof,historical=cutoff(args)
            read_only=args.check_only or args.dry_run or historical
            if historical and not args.no_network:raise ValueError('Historical --as-of requires --no-network; current downloads cannot recreate old information')
            before=preflight(root);write(out/'pre_run_state.json',before)
            verify_current_version(root)
            registry=load_registry(root/'registry/uzbekistan_nowcasting_v1.2_registry.xlsx')
            csv(out,'source_status_before.csv',inventory(root,registry,asof))
            seed(root,staged)
            observations=[];critical_invalid=False;gdp_candidate=None
            if not args.no_network and not args.run_nowcast:
                acquisition_root=root/'data/staging'/run_id/'acquisition';acquisition_root.mkdir()
                client=OperationsDownloader(root,acquisition_root,run_id,args.force_source)
                for key in (*ACTIVE,'gdp_real_yoy'):
                    variants=[False,True] if key=='industrial_production' else [False]
                    states[key]='UNCHANGED'
                    for real in variants:
                        label=key+'_approved_real' if real else key
                        change_start=len(changes);promotion_start=len(promotion);observation_start=len(observations);source_backups={}
                        try:
                            new=acquire(key,client,registry,root,asof.tz_convert('Asia/Tashkent').tz_localize(None),real=real)
                            if key=='pos_turnover':
                                reviewed=reviewed_pos(root,registry.rows[key],pd.Timestamp(datetime.now(timezone.utc)))
                                if reviewed is not None:
                                    new=reviewed.loc[reviewed.clean_value.notna()].copy()
                                    if new.empty:raise ValueError('Reviewed POS table has no feasible frozen YoY growth')
                            daily=new.attrs.pop('daily',None)
                            if key=='gdp_real_yoy':gdp_candidate=new.copy()
                            if real:
                                overlay=staged/'data/operations/shadow_observations.parquet'
                                if overlay.exists():old=pd.read_parquet(overlay).loc[lambda f:f.variable_key.eq(key)]
                                else:
                                    # Recover the archived float representation exactly;
                                    # default CSV parsing can manufacture sub-ULP revisions.
                                    history=pd.read_csv(root/'data/current/predictor_provenance.csv',float_precision='round_trip')
                                    old=history.loc[history.variable_key.eq(key)&history.selected_for_panel.eq(True)].copy()
                                    old['frequency']='M';old['reference_date']=pd.to_datetime(old.reference_date)
                                rel='data/operations/shadow_observations.parquet'
                            else:rel=f'data/processed/{key}.parquet';old=pd.read_parquet(root/rel)
                            source_backups[rel]=(staged/rel).read_bytes() if (staged/rel).exists() else None
                            if daily is not None:
                                daily_rel=f'data/processed/{key}_daily.parquet';source_backups[daily_rel]=(staged/daily_rel).read_bytes()
                            decision_time=asof if args.as_of else pd.Timestamp(datetime.now(timezone.utc))
                            verified_gdp={r['target_quarter'] for r in records(root/'results/operations/prospective/realization_records')
                                if r['event_kind']=='FIRST_RELEASE' and pd.Timestamp(r['ingested_timestamp'])<=decision_time
                                and pd.Timestamp(r['first_release_date']).date()<decision_time.tz_convert('Asia/Tashkent').date()}
                            accepted,rows,valid=compare(label,old,new,decision_time,gdp=key=='gdp_real_yoy',pos=key=='pos_turnover',verified_gdp=verified_gdp)
                            changes.extend(rows)
                            if not valid:
                                states[key]='VALIDATION_FAILED';critical_invalid|=key=='usd_uzs';continue
                            accepted_periods=[r['period'] for r in rows if r['accepted']]
                            if not accepted_periods and any(r['change_type']=='PARTIAL_CURRENT_MONTH' for r in rows):
                                states[key]='PARTIAL_CURRENT_MONTH'
                            if accepted_periods:
                                states[key]='UPDATED'
                                if real:
                                    existing=pd.read_parquet(staged/rel) if (staged/rel).exists() else pd.DataFrame()
                                    retain=existing.loc[~existing.variable_key.eq(key)] if len(existing) else existing
                                    accepted=pd.concat([retain,accepted],ignore_index=True)
                                atomic_parquet(accepted,staged/rel);promotion.append(rel)
                                changed=new.loc[new.reference_period.isin(accepted_periods)]
                                if key=='pos_turnover' and 'scope_verified' in changed:
                                    approved=changed.loc[changed.scope_verified.eq(True)].copy()
                                    overlay_rel='data/operations/shadow_observations.parquet'
                                    source_backups[overlay_rel]=(staged/overlay_rel).read_bytes() if (staged/overlay_rel).exists() else None
                                    overlay_old=pd.read_parquet(staged/overlay_rel) if (staged/overlay_rel).exists() else pd.DataFrame()
                                    if len(overlay_old):overlay_old=overlay_old.loc[~(overlay_old.variable_key.eq(key)&overlay_old.reference_period.isin(approved.reference_period))]
                                    atomic_parquet(pd.concat([overlay_old,approved],ignore_index=True),staged/overlay_rel);promotion.append(overlay_rel)
                                if not real:observations.append(changed)
                                if daily is not None:
                                    daily_rel=f'data/processed/{key}_daily.parquet';atomic_parquet(daily,staged/daily_rel);promotion.append(daily_rel)
                                    observations.append(daily)
                        except Exception as exc:
                            critical_invalid|=critical_validation_error(key,exc)
                            for restored,data in source_backups.items():
                                if data is None:
                                    if (staged/restored).exists():(staged/restored).unlink()
                                else:(staged/restored).write_bytes(data)
                            del promotion[promotion_start:];del observations[observation_start:]
                            for item in changes[change_start:]:item.update(accepted=False,reason='Source staging failed: '+str(exc))
                            states[key]='SOURCE_UNAVAILABLE'
                            changes.append(dict(variable=label,period=None,old_value=None,new_value=None,
                                change_type='SCHEMA_CHANGE' if isinstance(exc,ValueError) else 'INVALID',absolute_change=None,relative_change=None,
                                accepted=False,reason=f'{type(exc).__name__}: {exc}; existing data retained'))
                receipts=client.receipts
                # Use the real end-of-acquisition clock; no retrieved value is backdated to run start.
                if not args.as_of:asof=pd.Timestamp(datetime.now(timezone.utc))
            else:
                states={key:'CACHED_NOT_NETWORK_CHECKED' for key in (*ACTIVE,'gdp_real_yoy')}
                for key in states:
                    frame=pd.read_parquet(root/f'data/processed/{key}.parquet')
                    receipts.append(dict(variable=key,source=registry.rows[key]['provider'],retrieval_timestamp=None,
                        source_reference=registry.rows[key]['human_source_url'],http_status=None,raw_file=None,sha256=sha(root/f'data/processed/{key}.parquet'),
                        latest_observation=frame.reference_period.max(),status='CACHED_DATA_ONLY_NO_NEW_RETRIEVAL'))
            csv(out,'source_receipts.csv',receipts,RECEIPT_COLUMNS);csv(out,'data_changes.csv',changes,CHANGE_COLUMNS)
            revisions=[dict(variable=r['variable'],period=r['period'],old_value=r['old_value'],new_value=r['new_value'],
                source=registry.rows[r['variable'].removesuffix('_approved_real')]['provider'],retrieval_timestamp=asof.isoformat(),
                revision_reason_if_available=r['reason']) for r in changes if r['change_type']=='REVISION' and r['accepted']]
            csv(out,'revisions.csv',revisions,['variable','period','old_value','new_value','source','retrieval_timestamp','revision_reason_if_available'])
            if critical_invalid:raise ValueError('Critical USD/UZS candidate validation failed; no staged data promoted')
            if observations:
                store_vintages(pd.concat(observations,ignore_index=True),staged)
                promotion.extend(['metadata/observations_long.parquet','metadata/vintages.parquet'])
                if (staged/'metadata/revisions.parquet').exists():promotion.append('metadata/revisions.parquet')
            if client and client.events:
                events=pd.DataFrame(client.events);events['build_run_id']=run_id;events['event_order']=range(len(events))
                append_table(events,staged/'metadata/download_log.parquet',['build_run_id','event_order']);promotion.append('metadata/download_log.parquet')
            series={p.stem:pd.read_parquet(p) for p in (staged/'data/processed').glob('*.parquet') if p.stem in registry.rows}
            series={key:f for key,f in series.items() if len(f)}
            candidates={'monthly':build_monthly(series,registry,scope='v1'),'quarterly':build_quarterly(series['gdp_real_yoy'],'gdp_real_yoy_pct')}
            for kind,name in [('monthly','v1_monthly'),('quarterly','gdp_quarterly')]:
                rel=f'data/master/{name}.parquet'
                if not candidates[kind].equals(pd.read_parquet(root/rel)):
                    atomic_parquet(candidates[kind],staged/rel);promotion.append(rel);master_changed[kind]=True
                    excel=f'data/master/{name}.xlsx';candidates[kind].to_excel(staged/excel,index=False);promotion.append(excel)
            validate_masters(staged,registry)
            check=current_check(root,staged,gdp_candidate,client,asof)
            preview=worker(staged,dict(cutoff_utc=asof.isoformat(),check=check,historical=historical,calculate=not(args.check_only or args.update_data)))
            preview['cutoff_utc']=asof.isoformat();write(out/'shadow_reproduction.json',preview)
            if not args.check_only and not args.update_data:
                production_rows=production(staged,preview,asof)
            csv(out,'production_forecasts.csv',production_rows,['target_quarter','horizon','model','forecast','as_of_date','information_cutoff','status'])
            csv(out,'shadow_forecasts.csv',[dict(model=m,forecast=v,status='FAILED' if v is None else 'PENDING_REALIZATION') for m,v in preview['forecasts'].items()])
            if preview['failures'] and not args.check_only and not args.update_data:raise ValueError('Frozen model input failure: '+json.dumps(preview['failures']))
            delta=shadow_delta(root,preview);csv(out,'forecast_revisions.csv',delta)
            changed=[r for r in changes if r['accepted']]
            csv(out,'changed_model_inputs.csv',changed,CHANGE_COLUMNS)
            duplicate=preview['duplicate_snapshot'] is not None
            if not read_only and not args.update_data and not duplicate:
                request=dict(cutoff_utc=asof.isoformat(),check=check,historical=False,expected_fingerprint=preview['information_fingerprint'])
                written=worker(staged,request,'append');appended=True
                # Existing writer must reproduce the validated preview before promotion.
                new_rows=read(staged/'results/operations/prospective/snapshots'/written['appended_snapshot']/'forecasts.json')
                for row in new_rows:
                    if row['forecast'] is None or abs(row['forecast']-preview['forecasts'][row['model']])>1e-8:raise ValueError('Staged writer/preview forecast mismatch')
                if not (staged/LEDGER).read_bytes().startswith((root/LEDGER).read_bytes()):raise ValueError('Ledger is not append-only')
                verify(staged,before['protected_hashes'],allowed=SHADOW_MUTABLE|{LEDGER})
                for p in (staged/'results/operations/prospective').rglob('*'):
                    if not p.is_file():continue
                    rel=p.relative_to(staged).as_posix()
                    if not (root/rel).exists() or sha(p)!=sha(root/rel):promotion.append(rel)
                promotion.append('results/diagnostics/prospective_monitor.html')
            elif not duplicate and (args.no_network or historical):
                # Dry/reproduction runs report eligibility, never backdate or create history.
                preview['append_note']='Meaningful information change detected; reproduction mode does not append'
            verify(root,before['protected_hashes'])
            promotion=[p for p in dict.fromkeys(promotion) if not (root/p).exists() or sha(staged/p)!=sha(root/p)]
            # Commit the ledger last after immutable snapshot files/batches are present.
            promotion.sort(key=lambda p:p==LEDGER)
            actual_promoted={}
            if promotion and not read_only:
                for p,h in before['current_data_hashes'].items():
                    if not (root/p).exists() or sha(root/p)!=h:raise RuntimeError('Current data changed during staging: '+p)
                prior={p:before['current_data_hashes'].get(p,before['protected_hashes'].get(p,sha(root/p) if (root/p).exists() else None)) for p in promotion}
                def committed_validation():
                    verify(root,before['protected_hashes'],allowed={p for p in promotion if p in SHADOW_MUTABLE or p==LEDGER})
                    validate_masters(root,registry);model_lock(root)
                actual_promoted=promote(root,staged,promotion,run_id,prior,validate=committed_validation)
            elif read_only:appended=False
            allowed={p for p in promotion if p in SHADOW_MUTABLE or p==LEDGER} if not read_only else set()
            verify(root,before['protected_hashes'],allowed=allowed)
            source_after=inventory(staged,registry,asof,states)
            available={r['variable']:r for r in preview['data_status']}
            for row in source_after:
                if row['variable'] in available:
                    used=available[row['variable']]
                    row.update(latest_usable_month=str(pd.Timestamp(used['latest_usable_month']).to_period('M')) if used['latest_usable_month'] else None,missing_recent=used['missing_recent'])
            csv(out,'source_status_after.csv',source_after)
            _,bundle=model_lock(root)
            manifest=dict(scope='CURRENT_OPERATIONAL_STATE',timestamp_utc=asof.isoformat(),run_id=run_id,data_version=run_id if actual_promoted else 'UNCHANGED',
                master_hashes={k:sha((root if not read_only else staged)/f'data/master/{name}.parquet') for k,name in [('monthly','v1_monthly'),('quarterly','gdp_quarterly')]},
                registry_hash=sha(root/'registry/uzbekistan_nowcasting_v1.2_registry.xlsx'),code_hashes=before['frozen_hashes'],
                operations_code_hashes={p.name:sha(p) for p in (root/'scripts/operations').glob('*.py')},source_hashes={r['raw_file']:r['sha256'] for r in receipts if r.get('raw_file')},
                model_specification_hashes=bundle['specification_hashes'],latest_observations={r['variable']:r['latest_usable_month'] for r in source_after},
                forecasts=preview['forecasts'],production_forecasts=production_rows,information_fingerprint=preview['information_fingerprint'],
                relationship='Successor current-state evidence to results/operations/initial_state_manifest.json; never replaces a historical release',
                reconciliation_manifest_hash=sha(root/'results/operations/initial_state_manifest.json'),
                does_not_replace_historical_release=True,historical_release_reproduction=False,publication_ready=False,
                promoted=bool(actual_promoted),candidate_only=read_only,mode=mode)
            validate_current_manifest(manifest,bundle['specification_hashes'])
            write(out/'current_state_manifest.json',manifest)
            warnings=[f'{key}: {state}' for key,state in states.items() if state in {'SOURCE_UNAVAILABLE','VALIDATION_FAILED'}]
            warnings += [r['warning'] for r in source_after if r['classification']!='GREEN']
            if args.no_network:warnings.append('NO_NETWORK: provider availability and new external observations were not checked')
            if historical:warnings.append('Historical reproduction uses observed retrieval gates and never appends snapshots')
            status='NO_INFORMATION_CHANGE' if duplicate and not changed else 'UPDATE_SUCCESS_WITH_WARNINGS' if warnings else 'UPDATE_SUCCESS'
            if read_only and changed:status='UPDATE_SUCCESS_WITH_WARNINGS';warnings.append('Candidate changes validated only; dry/check mode promoted nothing')
            current_realization=any(r['event_kind']=='FIRST_RELEASE' and r['target_quarter']==preview['target'] for r in records(root/'results/operations/prospective/realization_records'))
            scoring_changed=appended and (staged/'results/operations/prospective/scored_forecasts.csv').exists() and sha(staged/'results/operations/prospective/scored_forecasts.csv')!=before['protected_hashes'].get('results/operations/prospective/scored_forecasts.csv')
            result=dict(run_id=run_id,timestamp=stamp.isoformat(),cutoff_utc=asof.isoformat(),mode=mode,status=status,
                target_quarter=preview['target'],horizon=preview['horizon'],operational_stage=preview['stage'],information_fingerprint=preview['information_fingerprint'],
                snapshot_appended=appended,duplicate_snapshot=preview['duplicate_snapshot'],snapshot_reason='DUPLICATE_INFORMATION_SET' if duplicate else 'DRY_RUN_NO_APPEND' if read_only else 'MEANINGFUL_INFORMATION_CHANGE' if appended else 'DATA_ONLY_NO_APPEND',
                master_monthly_changed=master_changed['monthly'] and not read_only,master_quarterly_changed=master_changed['quarterly'] and not read_only,
                candidate_master_changes=master_changed,promoted_hashes=actual_promoted,source_states=states,
                new_observations=sum(r['accepted'] and r['change_type']=='NEW_OBSERVATION' for r in changes),historical_revisions=len(revisions),
                rejected_observations=sum(r['change_type']=='INVALID' for r in changes),
                GDP_detected_unverified=any('GDP_VALUE_DETECTED_UNVERIFIED' in r['reason'] for r in changes),
                GDP_realization_verified=current_realization,forecasts_scored=scoring_changed,
                governance=read(staged/'results/operations/prospective/run_manifest.json').get('governance','INITIALIZED'),warnings=warnings,
                protected_artifacts_changed_unexpectedly=False,protected_files_checked=len(before['protected_hashes']),tests=read(root/'results/operations/implementation_test_results.json') if (root/'results/operations/implementation_test_results.json').exists() else None)
            write(out/'run_manifest.json',result)
            report(out,result,preview,production_rows,source_after,delta)
    except Exception as exc:
        rollback_error=None
        if actual_promoted:
            try:rollback_completed(root,run_id,actual_promoted)
            except Exception as problem:rollback_error=str(problem)
        failure=dict(run_id=run_id,status='UPDATE_ABORTED',timestamp=datetime.now(timezone.utc).isoformat(),error_type=type(exc).__name__,reason=str(exc),
            master_promotion_attempted=bool(promotion),snapshot_staged=appended,rollback_error=rollback_error)
        write(out/'update_failure.json',failure)
        if before:
            try:verify(root,before['protected_hashes'])
            except Exception:frozen_changed=True
        write(out/'run_manifest.json',dict(**failure,protected_artifacts_changed_unexpectedly=frozen_changed))
        (out/'update_report.md').write_text('# Update aborted\n\n'+str(exc)+'\n\nRaw source evidence is retained. Inspect any transaction journal before retrying.\n',encoding='utf-8')
    finally:
        # The staged project contains reproducible runtime projections only.
        if staged.exists():
            if not staged.resolve().is_relative_to((root/'data/staging').resolve()):raise ValueError('Unsafe staging cleanup')
            shutil.rmtree(staged)
            if not any(staged.parent.iterdir()):staged.parent.rmdir()
        # Even an early failure leaves named, machine-readable reports; empty is not success.
        defaults={'source_status_before.csv':None,'source_status_after.csv':None,'source_receipts.csv':RECEIPT_COLUMNS,
          'data_changes.csv':CHANGE_COLUMNS,'revisions.csv':['variable','period','old_value','new_value','source','retrieval_timestamp','revision_reason_if_available'],
          'production_forecasts.csv':['target_quarter','horizon','model','forecast','as_of_date','information_cutoff','status'],
          'forecast_revisions.csv':['model','previous_forecast','current_forecast','revision','previous_information_cutoff','current_information_cutoff'],
          'changed_model_inputs.csv':CHANGE_COLUMNS}
        for name,columns in defaults.items():
            if not (out/name).exists():csv(out,name,[],columns or ['status'])
        print_summary(out)
        logger.removeHandler(handler);handler.close()
    return 1 if failure else 0


def report(out,result,preview,production_rows,source_after,delta):
    items=[f"Run date/time: {result['timestamp']} ({result['mode']}). Cutoff: {result['cutoff_utc']}.",
      f"Target quarter: {result['target_quarter']}.",f"Horizon/stage: {result['horizon']} / {result['operational_stage']}.",
      'Source checks: '+json.dumps(result['source_states']),
      f"New observations: {result['new_observations']}; see data_changes.csv (candidate-only in dry/check mode).",
      f"Accepted historical revisions: {result['historical_revisions']}; previous values and provenance retained in versioned backups and observations_long.",
      'Failed sources: '+str([k for k,v in result['source_states'].items() if v=='SOURCE_UNAVAILABLE']),
      'Stale/missing indicators:\n\n'+pd.DataFrame(source_after)[['variable','latest_usable_month','months_stale','classification']].to_string(index=False),
      f"Current masters changed: monthly={result['master_monthly_changed']}, quarterly={result['master_quarterly_changed']}. Candidate changes: {result['candidate_master_changes']}.",
      f"Phase 6D snapshot appended: {result['snapshot_appended']}; {result['snapshot_reason']}. Existing immutable snapshots and ledger prefix retained.",
      'Current frozen shadow forecasts:\n\n'+pd.DataFrame([dict(model=k,forecast=v) for k,v in preview['forecasts'].items()]).to_string(index=False)+'\n\nSeparate production current-vintage/registry-lag reproduction:\n\n'+pd.DataFrame(production_rows).to_string(index=False),
      'Change versus previous same-target snapshot:\n\n'+pd.DataFrame(delta).to_string(index=False)+'\n\nChanged inputs are descriptive, not an exact causal decomposition.',
      f"GDP value detected but unverified: {result['GDP_detected_unverified']}. Verified realization registered: {result['GDP_realization_verified']}. API update dates are never first releases.",
      f"Scoring occurred in the current monitor: {result['forecasts_scored']}. Only the existing Phase 6D documented-first-release scoring policy is used; no model retuning.",
      f"Governance: {result['governance']}; no automatic model promotion.",
      'Operator warnings: '+json.dumps(result['warnings'])]
    (out/'update_report.md').write_text('# Automated nowcast update\n\nStatus: **'+result['status']+'**\n\n'+'\n\n'.join(f'{i}. {v}' for i,v in enumerate(items,1)),encoding='utf-8')


def print_summary(out):
    result=read(out/'run_manifest.json');preview=read(out/'shadow_reproduction.json') if (out/'shadow_reproduction.json').exists() else {}
    states=result.get('source_states',{})
    lines=['AUTOMATED NOWCAST UPDATE COMPLETE',f'Run ID: {result["run_id"]}',f'Timestamp: {result["timestamp"]}',
      f'Target quarter: {result.get("target_quarter","BLOCKED")}',f'Operational horizon: {result.get("horizon","BLOCKED")} ({result.get("operational_stage","")})',
      f'Information cutoff: {result.get("cutoff_utc","")}',f'Sources checked: {len(states)}',
      f'Sources updated: {sum(v=="UPDATED" for v in states.values())}',f'Sources unchanged: {sum(v=="UNCHANGED" for v in states.values())}',
      f'Sources failed: {sum(v=="SOURCE_UNAVAILABLE" for v in states.values())}',f'New observations: {result.get("new_observations",0)}',
      f'Historical revisions: {result.get("historical_revisions",0)}',f'Rejected observations: {result.get("rejected_observations",0)}',
      'Master monthly changed: '+('YES' if result.get('master_monthly_changed') else 'NO'),'Master quarterly changed: '+('YES' if result.get('master_quarterly_changed') else 'NO')]
    status=pd.read_csv(out/'source_status_after.csv')
    for row in status.to_dict('records'):
        if 'variable' in row:lines.append(f'Latest {row["variable"]}: {row["latest_usable_month"]}')
    for key,value in preview.get('forecasts',{}).items():lines.append(f'{key}: {value}')
    lines += ['Forecast snapshot appended: '+('YES' if result.get('snapshot_appended') else 'NO'),f'Reason: {result.get("snapshot_reason",result.get("reason"))}',
      'GDP realization available: '+('YES' if result.get('GDP_realization_verified') else 'NO'),
      'GDP realization verified: '+('YES' if result.get('GDP_realization_verified') else 'NO'),
      'Forecasts scored: '+('YES' if result.get('forecasts_scored') else 'NO'),f'Governance status: {result.get("governance","BLOCKED")}',
      'Protected artifacts changed unexpectedly: '+('YES' if result.get('protected_artifacts_changed_unexpectedly') else 'NO'),
      f'Tests passed: {(result.get("tests") or {}).get("passed","NOT_RUN")}',f'Tests failed: {(result.get("tests") or {}).get("failed","NOT_RUN")}',
      'FINAL STATUS: '+result['status']]
    if any(v=='CACHED_NOT_NETWORK_CHECKED' for v in states.values()):lines.insert(8,'Source check mode: cached data only; provider availability/new external data not checked')
    text='\n'.join(lines);(out/'console_summary.txt').write_text(text+'\n',encoding='utf-8');print(text)


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group()
    for flag in ['check-only','update-data','run-nowcast']:group.add_argument('--'+flag,action='store_true')
    p.add_argument('--dry-run',action='store_true');p.add_argument('--no-network',action='store_true')
    p.add_argument('--as-of');p.add_argument('--force-source',action='append',default=[],choices=[*ACTIVE,'gdp_real_yoy']);p.add_argument('--verbose',action='store_true')
    return p


if __name__=='__main__':sys.exit(run(parser().parse_args()))
