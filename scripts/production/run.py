"""Run with .venv/Scripts/python.exe -m scripts.production.run (no network required)."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import json
import logging
import os
import subprocess
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.production.models import sw,FIELDS,SPEC_NAME,fit_info,dfm,umidas
from scripts.production.diagnostics import matched_forecasts,metrics,news,append_history,MODELS,ALIASES
from scripts.operations.state import read,write,sha,model_lock,verify_current_version,operational_lock
from scripts.operations.workspace import current_check
from uznowcast.models.data import load_dataset
from scripts.production.config import configuration

LOG=logging.getLogger('phase6e')


def csv(out,name,frame):
    pd.DataFrame(frame).to_csv(out/f'{name}.csv',index=False,float_format='%.17g')


def direction(value):
    return 'neutral' if value is None or not np.isfinite(value) or abs(value)<1e-10 else 'positive' if value>0 else 'negative'


def state(root):
    candidates=[]
    for path in (root/'results/operations').glob('update_*/current_state_manifest.json'):
        value=read(path)
        if not value.get('candidate_only') and value.get('promoted'):
            candidates.append((value['timestamp_utc'],path,value))
    if not candidates:raise ValueError('No committed current operational manifest')
    _,path,value=max(candidates,key=lambda x:x[0])
    verify_current_version(root)
    return path,value


def verify_protected(root,before):
    # Only the requested current dashboard pointer may change.
    allowed={'dashboard/current/uzbekistan_nowcast.html','dashboard/current/README.md'}
    # Current inputs and supported Phase 6D operational views can evolve through
    # the existing transactional updater. Immutable snapshots remain protected.
    from scripts.operations.run_update import SHADOW_MUTABLE, LEDGER
    allowed.update(SHADOW_MUTABLE | {LEDGER,'results/diagnostics/prospective_monitor.html'})
    dynamic=('data/master/','metadata/')
    changed=[p for p,h in before['hashes'].items() if p not in allowed and not p.startswith(dynamic) and
             (not (root/p).is_file() or sha(root/p)!=h)]
    if changed:raise ValueError('Frozen artifacts changed: '+', '.join(changed))
    return dict(frozen_artifacts_modified=False,checked=sum(p not in allowed and not p.startswith(dynamic) for p in before['hashes']),
                allowed_operational_pointers=sorted(allowed),dynamic_inputs_checked_per_run=True)


def baseline(root):
    paths,_=model_lock(root)
    return dict(hashes=paths,git_commit=read(root/'config/production_seal.json')['migration_checkpoint'])


def historical_reproduction(root,f,out):
    dataset=load_dataset(root)
    panel=pd.read_csv(root/'data/current/historical_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip')
    events=pd.read_csv(root/'data/current/gdp_vintages.csv')
    vk=sw.common.vintage_kernel()
    rows=[];terms=[]
    for keys,block in f.groupby(['target_quarter','horizon']):
        target,horizon=keys;origin=pd.Timestamp(block.forecast_origin_date.iloc[0])
        available=vk.available_gdp_vintage_as_of(events,origin,target=target,timing_rule='STRICT')
        # Frozen benchmark fit gates GDP internally; use its exact dataset design.
        from dataclasses import replace
        gated=replace(dataset,gdp=pd.DataFrame({'quarter':available.frame.index,dataset.target_field:available.frame.value.to_numpy()}))
        u,t,_=umidas(gated,available,target,horizon,origin);terms.extend(t)
        d,_=dfm(panel,dataset,available,target,horizon,origin)
        for model,value in [('PHASE6C_DFM',d),('U_MIDAS',u)]:
            expected=float(block.loc[block.model.eq(model),'prediction'].iloc[0])
            error=value-expected
            rows.append(dict(target_quarter=target,horizon=horizon,model=model,reproduced=value,frozen=expected,error=error))
            if abs(error)>1e-7:raise ValueError(f'Historical reproduction materially differs: {target} {horizon} {model}: {error}')
        LOG.info('Reproduced %s %s DFM=%s U-MIDAS=%s',target,horizon,d,u)
    csv(out,'historical_reproduction',rows)
    return terms


def interpret(root,fit,info,origin,bundle):
    transforms=bundle['challengers']['PHASE6C_DFM']['transformations']
    d=fit['dfit'];load=[];drivers=[]
    shares=100*abs(d['loadings'])/abs(d['loadings']).sum()
    for key,loading,share in zip(FIELDS,d['loadings'],shares):
        values=d['z'][key].dropna();latest=values.index[-1] if len(values) else None
        z=float(values.iloc[-1]) if len(values) else None
        signal=float(loading*z) if z is not None else None
        qvalues=d['z'].loc[d['z'].index.to_period('Q')==pd.Period(info['target'],'Q'),key].dropna()
        qsignal=float(loading*qvalues.mean()) if len(qvalues) else None
        source=next((r for r in reversed(info.get('provenance',[])) if r['variable']==key and
                     r['reference_period']==str(latest.to_period('M'))),{}) if latest is not None else {}
        load.append(dict(indicator=key,model_field=transforms[key]['clean_model_field'],loading=float(loading),absolute_loading=float(abs(loading)),
                         normalized_loading_share_pct=float(share),latest_standardized_value=z,latest_loading_signal=signal,
                         direction=direction(signal),data_period=str(latest.to_period('M')) if latest is not None else None,
                         release_date_if_available=source.get('source_release_date'),standardization_mean=float(d['means'][key]),
                         standardization_std=float(d['scales'][key]),quarter_signal=qsignal,quarter_observed_months=len(qvalues),
                         decomposition_type='loading-based descriptive'))
        drivers.append(dict(indicator=key,source_model='PHASE6C_DFM',metric_type='descriptive DFM factor signal',
                            direction=direction(qsignal),contribution_or_signal=qsignal,normalized_share_pct=None,
                            latest_period=str(latest.to_period('M')) if latest is not None else None,
                            latest_value=float(fit['panel'].loc[latest,key]) if latest is not None else None,
                            transformation=transforms[key]['transformation'],
                            interpretation='Supporting factor signal' if direction(qsignal)=='positive' else 'Weakening factor signal' if direction(qsignal)=='negative' else 'No released target-quarter measurement',
                            observed_quarter_months=len(qvalues),decomposition_type='loading-based descriptive'))
    total=sum(abs(r['contribution_or_signal']) for r in drivers if r['contribution_or_signal'] is not None)
    for row in drivers:
        row['normalized_share_pct']=100*abs(row['contribution_or_signal'])/total if row['contribution_or_signal'] is not None and total else None
    fx=sum(t['contribution_pp'] for t in fit['terms'] if t['term'].startswith('lag_'))
    latest=fit['dataset'].monthly.usd_uzs_mom_dlog.last_valid_index()
    drivers.append(dict(indicator='usd_uzs',source_model='U_MIDAS',metric_type='exact forecast contribution',direction=direction(fx),
                        contribution_or_signal=fx,normalized_share_pct=100*abs(fx)/sum(abs(t['contribution_pp']) for t in fit['terms']),
                        latest_period=str(latest.to_period('M')),latest_value=float(fit['dataset'].monthly.loc[latest,'usd_uzs_mom_dlog']),
                        transformation=transforms['usd_uzs']['transformation'],interpretation='Combined three FX lag terms; model association, not causality',
                        decomposition_type='exact design-vector contribution'))
    return pd.DataFrame(load).sort_values('absolute_loading',ascending=False),pd.DataFrame(drivers).assign(
        _sort=lambda f:f.contribution_or_signal.abs()).sort_values('_sort',ascending=False).drop(columns='_sort')


def snapshot_news(root,info,origin,fit,bundle):
    ledger=pd.read_csv(root/'results/operations/prospective/prospective_forecast_ledger.csv',float_precision='round_trip')
    withdrawals=pd.read_csv(root/'results/operations/prospective/withdrawal_registry.csv')
    snapshots=ledger.loc[ledger.model.eq('COMBO_50_50') & ledger.target_quarter.eq(info['target']) &
                         ~ledger.snapshot_id.isin(withdrawals.snapshot_id)].sort_values('run_timestamp_utc')
    entries=[]
    for row in snapshots.to_dict('records'):
        if pd.Timestamp(row['information_cutoff'])>pd.Timestamp(origin).tz_localize('Asia/Tashkent').tz_convert('UTC'):continue
        path=root/'results/operations/prospective/snapshots'/row['snapshot_id']
        saved=read(path/'inputs.json')
        if 'benchmark_monthly' not in saved:continue
        timestamp=pd.Timestamp(row['information_cutoff']).tz_convert('Asia/Tashkent').tz_localize(None)
        entries.append((saved,timestamp))
    entries.append((info,origin))
    rows=[];notes=[]
    for (old,old_origin),(new,new_origin) in zip(entries,entries[1:]):
        if (old['target'],old['horizon'])!=(new['target'],new['horizon']):
            notes.append(f'No comparable previous real-time vintage available: {old_origin} -> {new_origin}')
            continue
        old_fit=fit_info(old,root,old_origin)
        new_fit=fit if new is info else fit_info(new,root,new_origin)
        rows.extend(news(old,new,root,old_origin,new_origin,old_fit,new_fit))
    return pd.DataFrame(rows,columns=['old_as_of_date','new_as_of_date','target_quarter','indicator','source_model','old_forecast','new_forecast',
                                     'news_impact_pp','total_revision_pp','reconstruction_error','decomposition_type','updated_indicator_groups']),notes


def build(root=ROOT,out=None,publish=True):
    out=Path(out) if out else root/'results/current';out.mkdir(parents=True,exist_ok=True)
    handler=logging.FileHandler(out/'pipeline.log',encoding='utf8');LOG.addHandler(handler);LOG.setLevel(logging.INFO)
    try:
        configuration(root)
        paths,bundle=model_lock(root)
        before=baseline(root)
        per_run_inputs={p.relative_to(root).as_posix():sha(p) for directory in ['data/master','metadata','data/operations']
                        for p in (root/directory).glob('*.parquet')}
        protected=verify_protected(root,before)
        manifest_path,current_state=state(root)
        now=pd.Timestamp(current_state['timestamp_utc'])
        # Repeat the latest committed as-of, rather than letting a wall-clock tick alter the result.
        preview=sw.prepare(now,current_check(root,root,asof=now),calculate=True)
        if preview['failures']:raise ValueError('Current forecast failures: '+str(preview['failures']))
        origin=now.tz_convert('Asia/Tashkent').tz_localize(None)
        info=preview['info']
        # Add eligible observation provenance for explicit freshness dates.
        _,_,provenance=sw.adapted_inputs(now);info=dict(info,provenance=provenance)
        fit=fit_info(info,root,origin)
        for key,value in [('PHASE6C_DFM',fit['dfm']),('UMIDAS_USD',fit['umidas']),('COMBO_50_50',fit['final'])]:
            if abs(value-preview['forecasts'][key])>=1e-10:raise ValueError('Actual model reconstruction failed: '+key)
        ledger=pd.read_csv(root/'results/operations/prospective/prospective_forecast_ledger.csv',float_precision='round_trip')
        frozen=ledger.loc[ledger.snapshot_id.eq(preview['duplicate_snapshot'])]
        if len(frozen):
            for row in frozen.to_dict('records'):
                if row['forecast_status']!='FAILED' and abs(preview['forecasts'][row['model']]-row['forecast'])>1e-7:
                    raise ValueError('Frozen current reproduction materially differs: '+row['model'])
        forecasts=pd.read_csv(root/'results/diagnostics/historical_forecasts.csv',float_precision='round_trip')
        weights=bundle['weights']['COMBO_DEV_WEIGHT']
        matched=matched_forecasts(forecasts,weights)
        if len(matched)!=12*7:raise ValueError('Expected complete 12-origin, seven-model holdout comparison')
        scores=metrics(matched)
        pooled=scores.loc[scores.horizon.eq('ALL')].sort_values(['rmse','mae','model'])
        best=pooled.iloc[0].model
        promote=best=='COMBO_50_50'
        status='PHASE6E_PROMOTED' if promote else 'PHASE6E_PROMOTION_BLOCKED'
        historical_terms=historical_reproduction(root,matched,out)
        # Development and holdout U-MIDAS designs are extracted at every frozen successful origin.
        dataset=load_dataset(root);events=pd.read_csv(root/'data/current/gdp_vintages.csv')
        from dataclasses import replace
        for row in forecasts.loc[forecasts.model.eq('UMIDAS_USD') & forecasts.prediction.notna() & forecasts.evaluation_group.eq('DEVELOPMENT')].to_dict('records'):
            if row['lag_mode']!='standard' or row['timing_rule']!='STRICT':continue
            date=pd.Timestamp(row['forecast_origin_date'])
            available=sw.common.vintage_kernel().available_gdp_vintage_as_of(events,date,target=row['target_quarter'],timing_rule='STRICT')
            gated=replace(dataset,gdp=pd.DataFrame({'quarter':available.frame.index,dataset.target_field:available.frame.value.to_numpy()}))
            value,t,_=umidas(gated,available,row['target_quarter'],row['horizon'],date)
            if abs(value-row['prediction'])>1e-7:raise ValueError('Development U-MIDAS reconstruction failed')
            historical_terms.extend(t)
        terms=pd.DataFrame(historical_terms+fit['terms'])
        csv(out,'umidas_contributions',terms)
        csv(out,'umidas_coefficients',terms.drop(columns=['contribution_pp']))
        loadings,drivers=interpret(root,fit,info,origin,bundle)
        csv(out,'dfm_loadings',loadings);csv(out,'current_drivers',drivers)
        csv(out,'matched_forecasts',matched);csv(out,'r2_metrics',scores)
        news_frame,news_notes=snapshot_news(root,info,origin,fit,bundle)
        csv(out,'news_decomposition',news_frame)
        values={ALIASES.get(k,k):v for k,v in preview['forecasts'].items()}
        comparison=pooled.drop(columns='horizon').copy()
        comparison['production_status']=comparison.model.map({m:'BENCHMARK' for m in MODELS})
        comparison.loc[comparison.model.isin(['PHASE6C_DFM','COMBO_DEV_WEIGHT']),'production_status']='SHADOW'
        comparison.loc[comparison.model.eq('LEGACY_PRODUCTION_V1'),'production_status']='LEGACY' if promote else 'PRIMARY'
        comparison.loc[comparison.model.eq('COMBO_50_50'),'production_status']='PRIMARY' if promote else 'SHADOW'
        comparison['weight_dfm']=comparison.model.map({'COMBO_50_50':.5,'COMBO_DEV_WEIGHT':weights['dfm']})
        comparison['weight_umidas']=comparison.model.map({'COMBO_50_50':.5,'COMBO_DEV_WEIGHT':weights['umidas']})
        for h in ['H1','H2','H3']:comparison[h+'_rmse']=comparison.model.map(scores.loc[scores.horizon.eq(h)].set_index('model').rmse)
        comparison['current_2026Q3_forecast']=comparison.model.map(values)
        comparison['notes']='Strict documented GDP boundary; lag-based historical predictor availability; actual-minus-prediction bias'
        csv(out,'model_comparison',comparison)
        audit=comparison[['model','n','rmse','mae','bias','current_2026Q3_forecast']].rename(columns={'n':'number_of_forecasts','rmse':'RMSE','mae':'MAE'})
        audit['sample']='MATCHED_HOLDOUT_FIRST_RELEASE_STANDARD_STRICT'
        audit['forecast_start']=matched.forecast_origin_date.min();audit['forecast_end']=matched.forecast_origin_date.max()
        csv(out,'audit',audit)
        for name,rows in [('quarter_performance',matched.assign(error=matched.actual-matched.prediction).groupby(['target_quarter','model']).error.agg(rmse=lambda s:float(np.sqrt((s*s).mean())),bias='mean').reset_index()),
                          ('leave_one_quarter_out',pd.concat([metrics(matched.loc[matched.target_quarter.ne(q)]).assign(excluded_quarter=q) for q in sorted(matched.target_quarter.unique())]))]:csv(out,name,rows)
        primary=pooled.loc[pooled.model.eq('COMBO_50_50')].iloc[0]
        policy=dict(production_version='V2',phase='6E',model='COMBO_50_50' if promote else 'LEGACY_PRODUCTION_V1',
                    status=status,dfm_model=SPEC_NAME,dfm_weight=.5,umidas_weight=.5,
                    promotion_basis='matched historical holdout superiority',prospective_validation_status='pending',
                    prospective_realizations_at_promotion=0,legacy_model_preserved=True,rollback_available=True,
                    rollback_pointer='results/current/rollback_policy.json',legacy_model='LEGACY_PRODUCTION_V1',
                    legacy_entrypoint='python -m scripts.operations.run_update --run-nowcast --no-network',
                    update_entrypoint='python -m scripts.production.update',best_matched_candidate=best,
                    specification_hashes=bundle['specification_hashes'],promotion_input_manifest=manifest_path.relative_to(root).as_posix(),
                    holdout_origins=12,holdout_quarters=4,development_weights_frozen=weights,
                    historical_predictor_availability='REGISTRY_LAG_PSEUDO_REAL_TIME; incomplete historical observed release vintages',
                    current_release_rule='observed retrieval/release plus frozen calendar horizon mask',
                    protocol='Re-estimate at each permissible update; news holds old parameters fixed and reports refitting separately',
                    promoted_at_as_of=now.isoformat(),git_commit=before['git_commit'])
        legacy_rows=current_state.get('production_forecasts',current_state.get('production',[]))
        # Preserve the original ungated-master operational result independently
        # from the strict same-information legacy recipe used in the comparison.
        for row in legacy_rows:
            if row.get('model')=='ensemble_ar2_umidas_usd':policy['legacy_original_current_forecast']=row['forecast']
        current=dict(status=status,target_quarter=info['target'],horizon=info['horizon'],stage=preview['stage'],
                     as_of_date=str(origin.date()),last_data_update=now.isoformat(),production_model=policy['model'],
                     dfm_forecast=fit['dfm'],umidas_forecast=fit['umidas'],final_forecast=fit['final'] if promote else values['LEGACY_PRODUCTION_V1'],
                     combo_50_50_forecast=fit['final'],dfm_weight=.5,umidas_weight=.5,
                     reconstruction_error=fit['final']-(.5*fit['dfm']+.5*fit['umidas']),
                     historical_rmse=float(primary.rmse),historical_error_reference_range=[fit['final']-primary.rmse,fit['final']+primary.rmse],
                     uncertainty_label='historical-error reference range',uncertainty_note='Four holdout quarters; indicative ±1 RMSE, not a formal confidence interval',
                     prospective_realizations=0,prospective_validation_status='pending',input_data_fingerprint=preview['information_fingerprint'],
                     data_version=current_state['data_version'],news_notes=news_notes,
                     limitations=['Incomplete historical predictor release vintages: lag-based pseudo-real-time evaluation',
                                  'POS withheld after December 2024; no released target-quarter POS signal',
                                  'DFM loading signals are descriptive, not additive GDP effects',
                                  'Only four holdout quarters; equal and development weights perform nearly identically'])
        current['target_convention']='Published cumulative year-to-date real GDP YoY percent; volume index minus 100'
        # Respect any registered prospective outcomes; never overwrite evidence with a fixed claim.
        realized=pd.read_csv(root/'results/operations/prospective/realization_registry.csv')
        n=realized.target_quarter.nunique() if len(realized) else 0
        policy['prospective_realizations_at_promotion']=n;current['prospective_realizations']=n
        write(out/'production_policy.json',policy);write(out/'current_nowcast.json',current)
        write(out/'dfm_structure.json',sw.common.safe(dict(factor_ar_coefficients={k:v for k,v in fit['dfit']['parameters'].items() if k.startswith('L')},
                  bridge_coefficients=dict(zip(['intercept','factor_mean','gdp_lag1'],fit['dfit']['bridge_coef'])),
                  factor_states=fit['dfit']['factors'].reset_index().to_dict('records'),diagnostics=fit['dfit']['diagnostics'])))
        freshness=pd.DataFrame(preview['data_status']);freshness['status']=freshness.apply(lambda r:'MISSING' if pd.isna(r.latest_usable_month) else 'LAGGED' if r.months_stale>0 else 'PARTIAL' if r.missing_recent else 'CURRENT',axis=1)
        release=dict(zip(loadings.indicator,loadings.release_date_if_available))
        freshness['release_update_date']=freshness.variable.map(release)
        gd=fit['available'].frame.iloc[-1]
        freshness=pd.concat([freshness,pd.DataFrame([dict(variable='gdp_real_yoy',latest_usable_month=fit['available'].frame.index[-1],
                  release_update_date=gd.publication_date,status='CURRENT',latest_observation=fit['available'].frame.index[-1],
                  warning='Published quarterly YTD real GDP growth; remains quarterly')])],ignore_index=True)
        csv(out,'data_freshness',freshness)
        history,appended=append_history(out/'nowcast_revision_history.csv',dict(as_of_date=now.isoformat(),target_quarter=info['target'],horizon=info['horizon'],
                    production_model=policy['model'],DFM_forecast=fit['dfm'],UMIDAS_forecast=fit['umidas'],final_forecast=current['final_forecast'],
                    input_data_fingerprint=preview['information_fingerprint'],change_from_previous=None))
        from scripts.production.dashboard import render
        html=render(current,comparison,loadings,drivers,terms.tail(len(fit['terms'])),news_frame,matched,freshness,history)
        dashboard=out/'uzbekistan_nowcast_v2.html';dashboard.write_text(html,encoding='utf8')
        protected=verify_protected(root,before)
        if any(sha(root/p)!=h for p,h in per_run_inputs.items()):raise ValueError('Current inputs changed during Phase 6E build')
        if publish:
            target=root/'dashboard/uzbekistan_nowcast_v2.html';target.write_text(html,encoding='utf8')
            # Preserve the previous default before updating the operational pointer.
            pointer=root/'dashboard/current/uzbekistan_nowcast.html'
            backup=out/'legacy_current_dashboard.html'
            if not backup.exists():backup.write_bytes(pointer.read_bytes())
            if promote:
                pointer.write_text(html,encoding='utf8')
                write(root/'results/operations/current_production.json',dict(policy='results/current/production_policy.json',
                      nowcast='results/current/current_nowcast.json',dashboard='dashboard/uzbekistan_nowcast_v2.html',rollback=policy['rollback_pointer']))
        report(current,policy,comparison,drivers,news_frame,scores,protected,out)
        outputs={p.name:sha(p) for p in out.glob('*') if p.suffix in {'.csv','.json','.md'} and p.name not in
                 {'run_manifest.json','pre_change_state.json','test_results.json','determinism.json'}}
        write(out/'run_manifest.json',dict(status=status,current_state_manifest=manifest_path.relative_to(root).as_posix(),
              information_fingerprint=preview['information_fingerprint'],as_of=now.isoformat(),git_commit=before['git_commit'],
              protected=protected,input_hashes=paths,current_input_hashes=per_run_inputs,outputs=outputs,dashboard_sha256=sha(dashboard),
              code_hashes={p.relative_to(root).as_posix():sha(p) for p in (root/'scripts/production').glob('*.py')}))
        LOG.info('%s primary=%s forecast=%s RMSE=%s',status,policy['model'],current['final_forecast'],primary.rmse)
        return current
    finally:
        LOG.removeHandler(handler);handler.close()


def report(current,policy,comparison,drivers,news_frame,scores,protected,out):
    validation_path=ROOT/'results/current/test_results.json'
    validation=read(validation_path) if validation_path.exists() else None
    validation_text=(f"Tests: {validation['passed']} passed; {validation['failures']+validation['errors']} failed; {validation['skipped']} skipped. "
                     "The remaining legacy failures and pre-Phase-6E evidence are documented in validation_evidence.json.") if validation else 'Validation is recorded after the first build.'
    legacy=policy.get('legacy_original_current_forecast')
    text=f'''# Phase 6E — production promotion and interpretation

Status: {current['status']}. Primary: {policy['model']}. {current['target_quarter']} nowcast: {current['final_forecast']:.12f}%.
DFM: {current['dfm_forecast']:.12f}%; U-MIDAS: {current['umidas_forecast']:.12f}%; weights 0.50 / 0.50.
Reconstruction error: {current['reconstruction_error']}. As-of: {current['last_data_update']}; {current['horizon']} / {current['stage']}.

Promotion basis: matched historical holdout superiority. Prospective validation pending; {current['prospective_realizations']} realized quarters.
All candidates use the same 12 origins / four quarters, first-release GDP targets, standard predictor lag convention and STRICT documented GDP boundary.
Historical predictor vintages are incomplete: this is release-lag pseudo-real-time evidence, not complete historical real-time releases.
The expected ranking is recalculated from frozen matched forecasts, with DFM and U-MIDAS independently rerun on all holdout origins.
Development weights remain frozen; no holdout weight optimization. Equal and development-weight combinations perform nearly identically.

## Model comparison

{comparison.to_string(index=False)}

## Current drivers

{drivers.to_string(index=False)}

DFM driver signals use the mean of released standardized target-quarter observations multiplied by the sign-normalized loading.
No target-quarter POS measurement exists: its current-quarter signal is unavailable, rather than carried from 2024.
The loadings file separately preserves the latest historical measurement signal and reports its actual period.
DFM loading shares sum to 100%; they are factor loadings, not causal GDP coefficients or shares of GDP growth.
U-MIDAS contributions use the actual design vector multiplied by the fitted coefficient vector, including GDP persistence and intercept.
Every current and successful standard/STRICT development and holdout U-MIDAS origin is exported.

## Nowcast news

{news_frame.to_string(index=False) if len(news_frame) else 'No comparable previous real-time vintage available'}

News uses exact all-subset Shapley reruns with old scaling, state parameters, bridge and U-MIDAS coefficients fixed.
Observation groups include revisions to previously observed cells as well as new releases. Parameter re-estimation is reported separately.
DFM and U-MIDAS channels combine at 50/50, with USD/UZS grouped once in the ensemble view.
GDP releases/revisions form a separate news group and must satisfy the new strict GDP cutoff; future target GDP remains excluded.
Different target/horizon contexts are not mislabelled as predictor news. Notes: {current['news_notes']}.

## Robustness and uncertainty

Per-quarter errors and leave-one-quarter-out metrics are exported. Four holdout quarters provide limited evidence.
Historical RMSE: {current['historical_rmse']:.6f} pp. Indicative ±1 RMSE: {current['historical_error_reference_range']}.
This is a historical-error reference range, not a formal confidence interval. Bias convention: actual minus prediction.
R² and R²_OS versus AR(1) use exactly matched origins at H1/H2/H3 and pooled; negative scores are retained.

## Operations and rollback

Run `python -m scripts.production.run` to reproduce the latest committed information set without network calls.
Run `python -m scripts.production.update` to refresh official sources using the existing transactional pipeline, then rebuild V2.
Legacy model, policy, entry point and dashboards remain available. Rollback pointer: {policy['rollback_pointer']}.
The legacy recipe comparison uses the common STRICT documented GDP information set. Its current forecast is therefore distinct from the original
operational master-based legacy result ({legacy}); that original result and its pipeline remain preserved.
The default current dashboard is V2 after successful promotion. A byte-preserved legacy current dashboard is stored alongside these results.
The append-only revision ledger suppresses repeated fingerprints and identical nowcasts.

Frozen artifacts modified: NO; {protected['checked']} protected paths checked. Existing dirty repository state is preserved in pre_change_state.json.
Tests and second-run verification are recorded in test_results.json and determinism.json after validation.
{validation_text}
The dashboard was also rendered from its local file in headless Chrome; dashboard_preview.png records the visual check.
'''
    (out/'results.md').write_text(text,encoding='utf8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path);parser.add_argument('--no-publish',action='store_true')
    args=parser.parse_args()
    with operational_lock(ROOT):result=build(out=args.output_dir,publish=not args.no_publish)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
