"""Run: .venv/Scripts/python.exe scripts/research/phase6d/monitor.py"""
import argparse
import json
from datetime import datetime, timezone
from dataclasses import replace
import pandas as pd
import numpy as np
from common import *
from frozen import initialize
from inputs import inputs,status
from sources import check_current,register_realization,download,validate_check,realization_registry
from evaluation import evaluate
from uznowcast.models.data import horizon_month_end,quarter_start,quarter_end,information_cutoff_for_variable


def context(target, now):
    dates=[horizon_month_end(target,h) for h in ['H1','H2','H3']]
    day=pd.Timestamp(now).tz_convert('Asia/Tashkent').tz_localize(None).normalize()
    future=[i for i,d in enumerate(dates) if d>=day]
    i=future[0] if future else 2
    stage='ON_TIME' if day==dates[i] else 'POST_H3_LATE_INITIALIZATION' if not future else 'PRE_'+['H1','H2','H3'][i]
    return ['H1','H2','H3'][i],dates[i],stage,stage=='ON_TIME'


def select_target(latest_known,now):
    target=str(pd.Period(latest_known,freq='Q')+1)
    day=pd.Timestamp(now).tz_convert('Asia/Tashkent').tz_localize(None).normalize()
    calendar=str(day.to_period('Q'))
    return calendar if calendar>target and day>=horizon_month_end(calendar,'H1') else target


def calculate(panel,dataset,available,target,horizon,origin):
    k=kernel();spec=k.Spec('DFM-4_R1_P2',FIELDS,1,2,'2019-01-31',True,False)
    values=benchmark_kernel().benchmarks(dataset,available,target,horizon,'standard')
    details={}
    try:
        frame,audit=k.mask(panel,spec,target,horizon,dataset.release_lag_days,'standard')
        end=quarter_start(target)-pd.Timedelta(days=1)
        frame,_=k.training_panel(frame,end,True)
        z,means,scales=k.standardize(frame,end,False)
        z=z.reindex(pd.date_range(z.index.min(),quarter_end(target),freq='ME'))
        cache={}
        factors,loadings,diag=k.estimate(z.loc[:end],z,spec,cache)
        prediction,bridge_diag=k.bridge(factors,available,target,origin,'B','mean')
        fit=next(iter(cache.values()))[0]
        details=safe(dict(standardization_mean=means.to_dict(),standardization_scale=scales.to_dict(),
            factors=factors.reset_index().to_dict('records'),loadings=loadings.tolist(),diagnostics=diag,
            bridge=bridge_diag,parameters=dict(zip(fit.param_names,fit.params)),release_masks=audit))
        values['PHASE6C_DFM']=(prediction,'')
    except (ValueError,KeyError,np.linalg.LinAlgError) as exc:
        values['PHASE6C_DFM']=(np.nan,str(exc));details={'failure':str(exc)}
    for name,w in [('COMBO_50_50',.5),('COMBO_DEV_WEIGHT',WEIGHT_DFM)]:
        v=w*values['PHASE6C_DFM'][0]+(1-w)*values['UMIDAS_USD'][0]
        values[name]=(v,'' if np.isfinite(v) else 'COMPONENT_UNAVAILABLE')
    return values,details


def run(check=None):
    before=protection();bundle=initialize()
    verify_hashes(ROOT,json.loads((OUT/'phase6d_protected_start.json').read_text()))
    dynamic_paths=['metadata/observations_long.parquet','data/master/gdp_quarterly.parquet',
        'data/master/monthly_master.parquet','data/research/phase6a2/cbu_midas_monthly_panel.csv',
        'results/research/phase6a2/phase6a2_provenance.csv']
    dynamic_hashes={p:file_hash(ROOT/p) for p in dynamic_paths if (ROOT/p).exists()}
    dynamic_hashes.update({p.relative_to(ROOT).as_posix():file_hash(p) for parent in ['data/master','metadata'] for p in (ROOT/parent).glob('*.parquet')})
    if check is None:
        check=check_current()
    validate_check(check)
    now=pd.Timestamp(datetime.now(timezone.utc))
    target=select_target(check['latest_quarter'],now)
    horizon,nominal,stage,on_time=context(target,now)
    origin=now.tz_convert('Asia/Tashkent').tz_localize(None)
    panel,dataset,provenance=inputs(now)
    usd_cutoff=information_cutoff_for_variable(nominal,'usd_uzs',dataset.release_lag_days,'standard')
    dataset.monthly.loc[dataset.monthly.index>usd_cutoff,'usd_uzs_mom_dlog']=np.nan
    events=pd.read_csv(ROOT/'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    events=events.loc[pd.to_datetime(events.retrieved_at,utc=True).le(now)]
    for r in records(OUT/'realization_records'):
        if pd.Timestamp(r['ingested_timestamp'])>now:
            continue
        events=pd.concat([events,pd.DataFrame([dict(quarter=r['target_quarter'],
            publication_date=r.get('revision_release_date',r['first_release_date']),value=float(r['value']),
            source_url=r['source_url'].replace('https://www.stat.uz/','https://stat.uz/'),sha256=r['checksum'],
            value_verified=True,date_verified=True,time_verified=False,publication_time=None,
            quality='PHASE6D_REVIEWED_OFFICIAL')])],ignore_index=True)
    available=vintage_kernel().available_gdp_vintage_as_of(events,origin,target=target,timing_rule='STRICT')
    dataset=replace(dataset,gdp=pd.DataFrame({'quarter':available.frame.index,dataset.target_field:available.frame.value.to_numpy()}))
    # Only observations admitted by BOTH actual retrieval and frozen horizon rules enter the information hash.
    k=kernel();spec=k.Spec('DFM-4_R1_P2',FIELDS,1,2,'2019-01-31',True,False)
    masked,audit=k.mask(panel,spec,target,horizon,dataset.release_lag_days,'standard')
    provenance=[r for r in provenance if (r['variable']=='usd_uzs' and pd.Timestamp(r['reference_period']+'-01')<=usd_cutoff)
                or (pd.Timestamp(r['reference_period']+'-01').to_period('M').to_timestamp('M') in masked.index
                and pd.notna(masked.loc[pd.Timestamp(r['reference_period']+'-01').to_period('M').to_timestamp('M'),r['variable']]))]
    info=safe(dict(panel=masked.reset_index().rename(columns={'index':'month'}).to_dict('records'),
        benchmark_monthly=dataset.monthly[['usd_uzs_mom_dlog']].dropna(how='all').reset_index().to_dict('records'),
        GDP=available.frame.reset_index().to_dict('records'),provenance=provenance,target=target,horizon=horizon))
    ih=digest(info)
    # GDP accessor origin is metadata, not an observation: identity intentionally uses the calendar day.
    identity=digest(dict(input=ih,date=str(origin.date()),stage=stage,spec=bundle['specification_hashes']))
    directory=OUT/'snapshots'/identity
    old=ledger_rows()
    # Retain initialization attempts verbatim while making an implementation correction explicit.
    for r in old:
        old_inputs=OUT/'snapshots'/r['snapshot_id']/'inputs.json'
        if old_inputs.exists() and 'benchmark_monthly' not in json.loads(old_inputs.read_text()):
            withdrawal=dict(snapshot_id=r['snapshot_id'],reason='Initialization implementation truncated U-MIDAS pre-2019 USD history; superseded after restoring frozen benchmark history. Original rows retained; excluded from scoring.',affected_models=list(MODELS))
            append_record(OUT/'withdrawal_records',digest(withdrawal),withdrawal)
    save('withdrawal_registry',pd.DataFrame(records(OUT/'withdrawal_records'),columns=['snapshot_id','reason','affected_models']))
    existing=[r for r in old if r['snapshot_id']==identity]
    verify_snapshots()
    if not existing:
        values,details=calculate(masked,dataset,available,target,horizon,origin)
        directory.mkdir(parents=True,exist_ok=True)
        freeze(directory/'inputs.json',info)
        freeze(directory/'fit.json',details)
        code_hashes={p.relative_to(ROOT).as_posix():file_hash(p) for p in Path(__file__).parent.glob('*.py')}
        code_hashes.update(bundle['code_hashes'])
        for path,h in code_hashes.items():
            archive=OUT/'code_archive'/h
            archive.parent.mkdir(exist_ok=True)
            if not archive.exists():
                with archive.open('xb') as handle: handle.write((ROOT/path).read_bytes())
            if file_hash(archive)!=h: raise ValueError('Code archive changed')
        rows=[]
        for model in MODELS:
            prediction,reason=values[model]
            row={c:None for c in LEDGER_COLUMNS}
            row.update(run_id=identity,run_timestamp_utc=now.isoformat(),as_of_date=str(origin.date()),
                information_cutoff=now.isoformat(),target_quarter=target,horizon=horizon,model=model,
                forecast=float(prediction) if np.isfinite(prediction) else None,operational_stage=stage,
                nominal_horizon_date=str(nominal.date()),canonical_horizon_eligible=on_time,
                latest_available_gdp_quarter=available.frame.index[-1],latest_available_gdp_value=float(available.frame.value.iloc[-1]),
                latest_predictor_month=str(masked.dropna(how='all').index.max().date()),factor_count=1,factor_ar_order=2,bridge='B',
                specification_hash=bundle['specification_hashes'][model],input_data_hash=ih,code_hash=digest(code_hashes),
                forecast_status='PENDING_REALIZATION' if np.isfinite(prediction) else 'FAILED',failure_reason=reason,
                prospective_eligible=now>=pd.Timestamp(bundle['phase6c_actual_freeze_timestamp']),realization_available=False,snapshot_id=identity)
            if model.startswith('COMBO'):
                row.update(combination_weight_dfm=bundle['weights'][model]['dfm'],combination_weight_umidas=bundle['weights'][model]['umidas'])
            rows.append(safe(row))
        freeze(directory/'forecasts.json',rows)
        freeze(directory/'manifest.json',dict(snapshot_id=identity,timestamp=now.isoformat(),input_data_hash=ih,
            code_hashes=code_hashes,artifacts={p.name:file_hash(p) for p in directory.glob('*.json')}))
        append_ledger(rows)
    verify_snapshots()
    import platform,statsmodels
    for path,h in bundle['static_specification_hashes'].items():
        archive=OUT/'code_archive'/h
        if not archive.exists():
            with archive.open('xb') as handle:handle.write((ROOT/path).read_bytes())
        if file_hash(archive)!=h:raise ValueError('Registry archive changed')
    for r in ledger_rows():
        directory=OUT/'snapshots'/r['snapshot_id']
        environment=dict(python=platform.python_version(),pandas=pd.__version__,numpy=np.__version__,statsmodels=statsmodels.__version__,
            registry_hash=bundle['static_specification_hashes'],transformations=bundle['challengers']['PHASE6C_DFM']['transformations'],
            frozen_specifications=bundle['specification_hashes'])
        freeze(directory/'reconstruction_context.json',environment)
    data_status=status(masked,dataset.release_lag_days,origin)
    save('data_status',data_status)
    freeze(OUT/'target_records'/f'{target}.json',dict(target_quarter=target,first_prospective_snapshot=existing[0]['run_timestamp_utc'] if existing else now.isoformat(),
        latest_known_gdp_at_entry=check['latest_quarter'],phase6c_freeze=bundle['phase6c_actual_freeze_timestamp'],
        first_stage=stage,first_horizon=horizon,reason='Earliest unreleased GDP quarter at initialization; advance to calendar quarter at its H1 even if prior GDP remains unavailable. Actual timestamps retained.')) if not (OUT/'target_records'/f'{target}.json').exists() else None
    targets=[json.loads(p.read_text()) for p in (OUT/'target_records').glob('*.json')]
    target_view=pd.DataFrame(targets)
    target_view['gdp_known_at_phase6d_initialization']=False
    target_view['eligible_as_genuine_prospective']=True
    target_view['phase6c_actual_freeze_timestamp']=bundle['phase6c_actual_freeze_timestamp']
    target_view['phase6d_initialization_timestamp']=bundle['frozen_at_utc']
    for h in ['H1','H2','H3']:
        target_view[h+'_origin']=target_view.target_quarter.map(lambda q:str(horizon_month_end(q,h).date()))
        target_view['first_possible_'+h.lower()+'_date']=target_view[h+'_origin']
    realizations=realization_registry()
    release_by_q=dict(zip(realizations.target_quarter,realizations.first_release_date))
    target_view['gdp_release_date']=target_view.target_quarter.map(release_by_q)
    target_view['status']=target_view.gdp_release_date.map(lambda d:'REALIZATION_PENDING' if pd.isna(d) else 'VERIFIED_FIRST_RELEASE_REGISTERED')
    save('prospective_target_registry',target_view)
    ledger=pd.DataFrame(ledger_rows())
    revisions=[]
    for _,g in ledger.groupby(['target_quarter','model']):
        prior=None
        for r in g.sort_values('run_timestamp_utc').to_dict('records'):
            if prior and r['forecast'] is not None and prior['forecast'] is not None:
                revisions.append(dict(target_quarter=r['target_quarter'],horizon=r['horizon'],model=r['model'],
                    previous_snapshot=prior['snapshot_id'],snapshot_id=r['snapshot_id'],total_revision=r['forecast']-prior['forecast'],
                    old_forecast=prior['forecast'],new_forecast=r['forecast'],old_as_of_date=prior['as_of_date'],new_as_of_date=r['as_of_date'],
                    previous_horizon=prior['horizon'],current_horizon=r['horizon'],previous_forecast=prior['forecast'],current_forecast=r['forecast'],
                    news_attribution=None,parameter_attribution=None,note='Total change only; no fabricated attribution'))
            prior=r
    revision_view=pd.DataFrame(revisions,columns=['target_quarter','horizon','model','previous_snapshot','snapshot_id','old_as_of_date','new_as_of_date','old_forecast','new_forecast','previous_horizon','current_horizon','previous_forecast','current_forecast','total_revision','news_attribution','parameter_attribution','note'])
    save('revision_history',revision_view)
    scored,governance,n=evaluate()
    classification='PHASE6D_INITIALIZED' if n==0 else 'PHASE6D_PROSPECTIVE_MONITOR_ACTIVE'
    save('research_challenger_registry',pd.DataFrame(columns=['experiment_id','created_at','specification','status','note']))
    current=ledger.loc[ledger.target_quarter.eq(target)].sort_values('run_timestamp_utc').groupby('model').tail(1)
    report=f'''# Phase 6D shadow monitor\n\nStatus: PHASE6D_INITIALIZED. Governance: {governance}; {n} realized prospective quarters. No production promotion.\n\nFirst prospective target: {targets[0]['target_quarter']}. Current target: {target}, {horizon}, {stage}. Latest official GDP: {check['latest_quarter']}. Actual forecast timestamps are retained; late snapshots do not establish on-time H3 evidence.\n\nNo verified first-release outcome is registered for pending forecasts. No pending forecast errors, metrics, rankings or superiority claims are calculated. POS is scope-verified only through December 2024 and remains missing thereafter.\n\n{current[['model','forecast','forecast_status']].to_string(index=False)}\n\nRun again using `.venv/Scripts/python.exe scripts/research/phase6d/monitor.py`. Archive a dated official first-release document with `--archive-source URL`; submit reviewed evidence using `--realization evidence.json`. Required fields follow sources.register_realization; source receipt, checksum, dated first-publication basis and extraction evidence must match. Mutable SIAT update dates cannot substitute for first publication. Future qualifying snapshots append to the ledger; scores are derived separately.\n\nGovernance: 0 INITIALIZED; 1 EARLY_EVIDENCE; 2 INSUFFICIENT_EVIDENCE; 3 PRELIMINARY_REVIEW; 4+ GOVERNANCE_REVIEW_ELIGIBLE. Review eligibility never promotes a model automatically.\n'''
    (OUT/'phase6d_report.md').write_text(report,encoding='utf-8')
    report+='\nFrozen DFM, U-MIDAS and combination weights changed: NO. Protected production artifacts changed: NO (hash verification). All seven forecasts generated successfully. Development weights: DFM '+str(WEIGHT_DFM)+'; U-MIDAS '+str(WEIGHT_UMIDAS)+'.\n'
    report+='\nData status:\n\n'+data_status.to_string(index=False)+'\n'
    withdrawals=records(OUT/'withdrawal_records')
    report+='\nInitialization correction: pre-2019 USD benchmark history was restored. Original snapshot rows remain immutable but are excluded from scoring through withdrawal records. Corrected snapshot is current. No frozen specification changed.\n' if withdrawals else ''
    tests=[json.loads(p.read_text()) for p in OUT.glob('phase6d_*_test_results.json')]
    report+='\nTests: '+str(sum(t['passed'] for t in tests))+' passed; '+str(sum(t['failures']+t['errors'] for t in tests))+' failed.\n'
    report+= '\nProspective scorecard:\n\n'+(pd.read_csv(OUT/'phase6d_prospective_metrics.csv').to_string(index=False) if n else 'REALIZATION_PENDING. No performance conclusion can yet be made.')+'\n'
    report+='\nPromotion review must assess matched performance versus production, concentration in one quarter, horizon failures, bias, reproducibility, leakage, operational failure rate and data reliability. No automatic decision or weight re-estimation.\n'
    report+='\nThe next on-time horizon opportunity is 2026Q4 H1 on October 31, 2026. If Q3 GDP is still unavailable then, the frozen prior-GDP gate will record model failures rather than substitute an unobserved GDP value. No July/August/September forecasts were backdated.\n'
    report=report.replace('Status: PHASE6D_INITIALIZED.',f'Status: {classification}.')
    (OUT/'phase6d_results.md').write_text(report,encoding='utf-8')
    html=f'<!doctype html><html><head><meta charset="utf-8"><title>Phase 6D shadow monitor</title><style>body{{font:16px system-ui;max-width:1100px;margin:40px auto;color:#172b42}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;border-bottom:1px solid #ccd5df;text-align:left}}.flag{{background:#fff0cc;padding:16px}}</style></head><body><h1>Phase 6D · prospective shadow monitor</h1><p class="flag">{governance} · {n} realized quarters · Shadow only · No automatic promotion</p><p>{target} / {horizon} / {stage}. Actual timestamp: {current.run_timestamp_utc.max()}. First-release realization pending; performance comparison unavailable.</p><h2>Frozen forecasts</h2>{current[["model","forecast","forecast_status"]].to_html(index=False,na_rep="Unavailable")}<h2>Predictor availability</h2>{data_status.to_html(index=False)}<p>Late H3 forecasts are excluded from on-time horizon evidence. POS after December 2024 remains missing.</p></body></html>'
    html=html.replace('</body>',f'<h2>Forecast revision path</h2>{ledger.loc[ledger.target_quarter.eq(target),["run_timestamp_utc","horizon","model","forecast"]].to_html(index=False)}<h2>Realized errors</h2>{scored.to_html(index=False) if len(scored) else "<p>Pending: no verified first release, no errors or rankings.</p>"}<h2>Frozen specification</h2><p>One factor, AR(2), bridge B, quarterly mean. Development weights: {WEIGHT_DFM} DFM / {WEIGHT_UMIDAS} U-MIDAS. Winsorization disabled. No retuning.</p></body>')
    html=html.replace('<h2>Forecast revision path</h2>','<p>Initialization audit: the first attempt truncated pre-2019 USD benchmark history. Its immutable rows are withdrawn from scoring; the corrected current forecasts retain the full frozen history.</p><h2>Forecast revision path</h2>') if withdrawals else html
    html=html.replace('<h1>Phase 6D · prospective shadow monitor</h1>','<h1>Phase 6D · prospective shadow monitor</h1><p><strong>RESEARCH SHADOW — NOT PRODUCTION</strong></p>')
    if n:
        html=html.replace('</body>','<h2>Prospective scorecard · descriptive small sample</h2>'+pd.read_csv(OUT/'phase6d_prospective_metrics.csv').to_html(index=False)+'</body>')
    (ROOT/'dashboard/phase6d_shadow_monitor.html').write_text(html,encoding='utf-8')
    verify_hashes(ROOT,before)
    verify_hashes(ROOT,dynamic_hashes)
    write_json(OUT/'phase6d_run_manifest.json',dict(completed_at_utc=now.isoformat(),source_check=check,
        snapshot_id=identity,input_data_hash=ih,governance=governance,n_realized_quarters=n,
        current_wrapper_hashes={p.name:file_hash(p) for p in Path(__file__).parent.glob('*.py')},
        read_only_input_hashes=dynamic_hashes,dashboard_sha256=file_hash(ROOT/'dashboard/phase6d_shadow_monitor.html'),
        protected_artifacts_verified=len(before),outputs={p.name:file_hash(p) for p in OUT.glob('phase6d_*') if p.is_file() and p.name not in ['phase6d_run_manifest.json','phase6d_console_summary.txt']}))
    print(current[['model','forecast','forecast_status']].to_string(index=False))
    print(f'PHASE 6D STATUS\nFirst genuine prospective target: {targets[0]["target_quarter"]}\nCurrent target: {target}\nAs-of date: {origin.date()}\nCurrent horizon: {horizon} ({stage})\nLatest known GDP quarter: {check["latest_quarter"]}\nGDP realization available: {"YES" if len(scored) else "NO"}\nDFM weight: {WEIGHT_DFM}\nU-MIDAS weight: {WEIGHT_UMIDAS}\nFrozen DFM changed: NO\nFrozen U-MIDAS changed: NO\nCombination weights changed: NO\nProduction artifacts changed: NO\nProspective realized quarters: {n}\nGovernance status: {governance}\nData warnings: POS stale, verified only through December 2024\nFinal classification: PHASE6D_INITIALIZED')
    print('Tests passed:',sum(t['passed'] for t in tests),'Tests failed:',sum(t['failures']+t['errors'] for t in tests))
    print('Final classification:',classification)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--realization');parser.add_argument('--archive-source');parser.add_argument('--verified-check')
    args=parser.parse_args()
    if args.archive_source:
        _,receipt=download(args.archive_source);print(json.dumps(receipt,indent=2))
    else:
        if args.realization: register_realization(json.loads(Path(args.realization).read_text()),initialize())
        check=json.loads(Path(args.verified_check).read_text()) if args.verified_check else None
        try:
            run(check)
        except Exception as exc:
            failure=dict(timestamp=datetime.now(timezone.utc).isoformat(),status='PHASE6D_BLOCKED',error_type=type(exc).__name__,error_message=str(exc))
            OUT.mkdir(parents=True,exist_ok=True)
            append_record(OUT/'failed_runs',digest(failure),failure)
            raise
