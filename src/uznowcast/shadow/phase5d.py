"""Frozen prospective shadow cohort, vintage ledger, scoring and dashboard.

Run ``python -m uznowcast.shadow.phase5d initialize``. Only this module's
Phase 5D paths are writable; production and earlier phases are read-only.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import html
import json
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd

from uznowcast.models import phase5c as legacy
from uznowcast.shadow.storage import append_record, digest, file_hash, freeze, records
from uznowcast.shadow.evaluation import (PRODUCTION, HORIZONS, evidence_status, governance,
                                        influence, matched_metrics, quarter_scores)

OUT = Path('results/shadow/phase5d')
DOC = Path('docs/modeling/phase5d')
PREFIX = 'phase5d_'
REALIZATION_COLUMNS = ['target_quarter','release_date','retrieval_timestamp','first_observed_value',
                      'current_value','first_release_source','current_source','revision_flag',
                      'revision_size','data_hash','evidence_class']
FORECAST_COLUMNS = ['run_id','forecast_id','target_quarter','forecast_date','forecast_timestamp_utc',
                    'information_cutoff','horizon','model','model_family','forecast_value',
                    'forecast_status','release_lag_mode','monthly_data_hash','quarterly_data_hash',
                    'model_spec_hash','git_commit','inherited_from_phase','notes','source_file',
                    'source_hash','realization_status','information_set_hash']


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str, allow_nan=False)+'\n', encoding='utf-8')


def protection(root: Path) -> dict[str,str]:
    baseline = legacy.protected_inventory(root)
    # Include all earlier phase output/code/documentation, canonical production,
    # and all prior manifests, even where not listed in the cleanup inventory.
    for base in ('results','docs/modeling','dashboard','config','src/uznowcast/models',
                 'src/uznowcast/operational'):
        for path in (root/base).rglob('*'):
            if path.is_file() and '__pycache__' not in str(path) and 'phase5d' not in str(path):
                baseline[path.relative_to(root).as_posix()] = file_hash(path)
    start = root/OUT/'phase5d_protected_start.json'
    if start.exists():
        for relative, expected in load(start).items():
            if not (root/relative).exists() or file_hash(root/relative) != expected:
                raise RuntimeError(f'Protected artifact changed: {relative}')
    return baseline


def verify(root: Path, baseline: dict) -> None:
    failures = [p for p,h in baseline.items() if not (root/p).exists() or file_hash(root/p)!=h]
    if failures:
        raise RuntimeError('STOP: protected artifact hash failures: '+', '.join(failures))


def select_cohort(leaderboard: pd.DataFrame) -> tuple[list[dict],list[dict]]:
    mandatory = leaderboard[leaderboard.gate_status.isin(['SHADOW_CHALLENGER','STRONG_SHADOW_CHALLENGER'])]
    research = leaderboard[(leaderboard.gate_status=='RETAIN_FOR_RESEARCH')
                           & (leaderboard.stability_flag=='ACCEPTABLE')
                           & (leaderboard.forecast_count >= 51)
                           & (leaderboard.influence_flag!='FRAGILE_IMPROVEMENT')
                           & leaderboard.current_2026Q3_shadow_nowcast.notna()]
    # Small, reproducible research cohort, determined solely from frozen 5C.
    selected = mandatory.model.tolist()
    ranked = research.sort_values(['relative_RMSE_vs_production','model']).model.tolist()
    for name in ranked:
        if len(selected) >= max(3,len(mandatory)):
            break
        if name not in selected:
            selected.append(name)
    entries, excluded = [], []
    for row in leaderboard.to_dict('records'):
        name = row['model']
        if name == PRODUCTION:
            continue
        item = dict(model_name=name, phase5c_gate=row['gate_status'], family=row['family'],
                    predictors=str(row['predictors']).split('|'), coverage=row['forecast_count']/54,
                    stability_classification=row['stability_flag'],
                    phase5c_matched_relative_rmse=row['relative_RMSE_vs_production'])
        if name in selected:
            if row['gate_status']=='REJECT':
                raise ValueError('REJECT models cannot enter cohort')
            item['reason_for_inclusion'] = ('Phase 5C shadow gate' if name in mandatory.model.values
                else 'Acceptable stability, full matched development coverage, operational current forecast; parsimonious research shadow only')
            entries.append(item)
        else:
            item['reason_for_exclusion'] = ('REJECT gate is binding' if row['gate_status']=='REJECT'
                else 'Not selected under frozen stability/coverage/operational/parsimonious rule')
            excluded.append(item)
    return entries, excluded


def protocol_text(cohort: dict) -> str:
    return '''# Phase 5D prospective shadow protocol

PHASE 5D — PROSPECTIVE SHADOW EVALUATION
NOT AN OFFICIAL MODEL REPLACEMENT

This protocol is immutable. Production is 0.5 × AR(2) + 0.5 × USD/UZS
U-MIDAS(3); no specification, transformation, lag or production artifact changes.
The exact inherited 2026Q3 H2 production value is 7.6239786595896035%.

Cohort selection uses only Phase 5C: include all shadow gates, then fill a small
research cohort with acceptable stability, >=51/54 development observations,
no fragile-influence warning, and an operational inherited forecast. REJECT
is binding. Frozen model definitions, component weights and source hashes are
in phase5d_frozen_challenger_cohort.json. Combination weights are held fixed
at their Phase 5C terminal values; no new outcomes can tune them. Missing
components make a forecast unavailable; weights are never renormalized later.

Evidence classes: DEVELOPMENT_PSEUDO_OOS and HISTORICAL_POST_DEVELOPMENT_TEST
remain historical. LIVE_PROSPECTIVE_SHADOW_PENDING is not accuracy evidence.
LIVE_PROSPECTIVE_REALIZED requires a frozen spec, a pre-release written
forecast, a stored cutoff, an auditable information set and an official outcome.
Start 2026Q3; there is no ending-quarter limit. Inherited H2 forecasts retain
Phase 5C manifest timestamps (run-level provenance, not invented row timestamps).
H1/H3 were not recorded and remain unavailable. They cannot be reconstructed.

H1/H2/H3 mean one/two/three contiguous release-eligible target-quarter USD
monthly aggregates, as in the frozen operational policy. Calendar progression
alone does not advance horizons. Standard registry lags and conservative
standard+15 days (zero-lag daily: 3 days) are inherited. Retrieval timestamps
bound actual availability; lag assumptions alone cannot admit future vintages.
Future forecasts are generated at invocation time, never backdated, from archived
master snapshots with observation retrieval/release eligibility. Unknown source
release dates remain null. Information records include hashes, latest available
months, code commit, registry assumptions and publication cutoff.

Primary GDP convention: FIRST_OBSERVED_OFFICIAL_AFTER_FREEZE. True historical
first releases cannot be reconstructed reliably from existing SIAT snapshots
(their release field is a dataset update timestamp). Preserve first observed
official release and subsequent revised values separately. Never relabel the
first observed value as a proven first publication. Source date evidence and an
archived official raw payload are required for realization registration. Unknown
or ambiguous release timing blocks primary prospective scoring. Freeze precedes
release except inherited 2026Q3, whose specifications and forecasts were frozen
in Phase 5C; if release predated Phase 5D, explicit contemporaneous evidence of
Phase 5C eligibility is required and automated registration refuses it.

Primary forecast convention: first written operational forecast per
quarter/model/horizon/lag mode. Missing forecasts remain missing. All later
vintages are retained but cannot displace the primary forecast.
Errors are forecast minus actual. Matched model/production observations alone
determine RMSE, MAE, bias, median/worst absolute error, relative metrics and
deltas. Report every horizon and pooled H1–H3 separately by lag mode.
Coverage denominator is all realized quarters × requested horizons; missing
records count as unavailable. Failure rate is failed / attempted (excludes
not-yet-available horizons). Revision sizes mean absolute H1→H2/H2→H3/H1→H3
changes, distinct from GDP data revisions.

Quantity stages: 0 NOT_YET_EVALUABLE; 1–3 INSUFFICIENT_PROSPECTIVE_EVIDENCE;
4–5 EARLY_PROSPECTIVE_EVIDENCE; 6–7 MODERATE_PROSPECTIVE_EVIDENCE;
8+ MATURE_PROSPECTIVE_EVIDENCE. No stage promotes a challenger.
At >=4 matched quarters, drop each quarter and require every relative RMSE <1
for ROBUST_PROSPECTIVE_IMPROVEMENT; otherwise flag fragile improvement.
Review eligibility requires >=4 matched quarters, pooled relative RMSE <1,
all horizons covered with >=4 matched quarters and relative RMSE <=1.05,
relative MAE <=1.02, |bias| <=0.5 percentage points, coverage >=90% of
production and >=80% absolute, failure rate <=5%, mean absolute forecast
revision <=max(0.5,1.5×production), robust influence, consistent conservative
lag results (relative RMSE <1, horizon deterioration <=0.05), and reproducible
specifications. Missing evidence fails a check. Four/five-quarter eligibility
is EARLY only; serious replacement decisions should wait 6–8 quarters and
require separate explicit authorization. PRODUCTION_MODEL is forbidden for
challengers. Single-quarter winner labels are descriptive only.

Limitations: Phase 5C historical outcomes are not pristine holdout evidence;
combination robustness under conservative lags was not tested in Phase 5C,
so inherited combinations remain research shadows and cannot pass that gate
until genuine prospective evidence accumulates. All three research candidates
share components and are correlated. No inference of significance from tiny N.
The immutable JSON ledger is authoritative; CSV/Parquet and dashboard are
derived mirrors. Hashes of old phases, frozen specs/protocol, ledgers and
information snapshots are checked on every run. No automatic source repair.
'''+ '\nFrozen challengers: '+', '.join(c['model_name'] for c in cohort['challengers'])+'\n'


def initialize(root: Path) -> dict:
    baseline = protection(root)
    out = root/OUT
    out.mkdir(parents=True, exist_ok=True)
    seal = out/'phase5d_freeze_manifest.json'
    if seal.exists():
        verify(root, load(seal)['protected_hashes'])
        verify(root, load(seal)['frozen_hashes'])
        phase5c_manifest=load(root/legacy.OUTPUT_REL/'phase5c_run_manifest.json')
        if file_hash(root/legacy.REGISTRY_REL)!=phase5c_manifest['registry_hash']:
            raise ValueError('Frozen registry changed; prospective lag/transform rules cannot be revised')
        return load(out/'phase5d_frozen_challenger_cohort.json')
    p = root/legacy.OUTPUT_REL
    manifest = load(p/'phase5c_run_manifest.json')
    if manifest['production_artifacts_modified'] or manifest['protected_hash_failures']:
        raise ValueError('Phase 5C protection failure')
    for relative, expected in manifest['candidate_specification_hashes'].items():
        if file_hash(root/relative)!=expected:
            raise ValueError(f'Phase 5C spec hash mismatch: {relative}')
    for relative, key in [(legacy.REGISTRY_REL,'registry_hash'),(legacy.MONTHLY_REL,'monthly_master_hash'),
                          (legacy.QUARTERLY_REL,'quarterly_master_hash'),
                          (legacy.PRODUCTION_NOWCAST_REL,'production_baseline_hash')]:
        if file_hash(root/relative)!=manifest[key]:
            raise ValueError(f'Phase 5C input hash mismatch: {relative}')
    # Parse every required evidence file before constructing the cohort.
    evidence = {f.name: pd.read_csv(f) for f in p.glob('*.csv')}
    load(p/'phase5c_challenger_protocol.json')
    (root/'docs/modeling/phase5c/phase5c_challenger_results.md').read_text(encoding='utf-8')
    policy = load(root/'results/phase5b/phase5b_production_policy.json')
    load(root/'results/phase5a_run_manifest.json')
    entries, excluded = select_cohort(evidence['phase5c_challenger_leaderboard.csv'])
    weights = evidence['phase5c_combination_weights.csv']
    current = evidence['phase5c_current_shadow_nowcasts.csv'].set_index('model')
    for item in entries:
        name = item['model_name']
        if item['family'] != 'forecast_combination':
            raise ValueError('Additional frozen family needs explicit supported spec adapter')
        components = current.loc[name,'notes'].split('components=')[1].split('|')
        item.update(predictors=['usd_uzs_mom_dlog'], transformation='registry clean fields; no additional transformation',
                    lag_structure={'ar2':2,'production_usd_umidas':3,'challenger_usd_umidas':1,
                                   'bridge_usd':'available-month mean + GDP lag 1'},
                    components=components, weights_by_horizon={})
        for h in HORIZONS:
            w = weights[(weights.model==name)&(weights.horizon==h)]
            latest = w[w.target_quarter==w.target_quarter.max()].set_index('component').weight.to_dict()
            v = [latest.get(c,np.nan) for c in components]
            if name=='combination_equal_weight' or any(not np.isfinite(x) for x in v) or sum(v)<=0:
                v = [1/len(components)]*len(components)
            else:
                v = [x/sum(v) for x in v]
            item['weights_by_horizon'][h] = dict(zip(components,v))
        item['spec_hash'] = digest(item)
        metrics = evidence['phase5c_combination_metrics.csv']
        selected_metrics = metrics[metrics.model==name]
        if selected_metrics.empty or selected_metrics.estimation_failure_rate.max()>0.05:
            raise ValueError(f'Unacceptable Phase 5C failure evidence: {name}')
        item['phase5c_estimation_failure_rate'] = float(selected_metrics.estimation_failure_rate.max())
        item['release_lag_robustness'] = 'UNTESTED_COMBINATION_RESEARCH_ONLY; prospective gate required'
    cohort = dict(phase='5D',version='5d.0',frozen_at_utc=now(), first_target='2026Q3',
                  production=dict(model_name=PRODUCTION, weights=policy['ensemble_weights'],
                                  lag_structure={'ar2':2,'usd_umidas':3},
                                  specification='0.5 AR(2) + 0.5 USD/UZS U-MIDAS(3)',
                                  policy_hash=file_hash(root/'results/phase5b/phase5b_production_policy.json')),
                  challengers=entries, excluded=excluded,
                  phase5c_evidence_hashes={f.relative_to(root).as_posix():file_hash(f) for f in p.iterdir() if f.is_file()})
    freeze(out/'phase5d_frozen_challenger_cohort.json',cohort)
    doc=root/DOC/'phase5d_prospective_shadow_protocol.md'
    doc.parent.mkdir(parents=True,exist_ok=True)
    text=protocol_text(cohort)
    if doc.exists() and doc.read_text(encoding='utf-8')!=text:
        raise ValueError('Frozen protocol conflict')
    if not doc.exists():
        with doc.open('x',encoding='utf-8') as handle:
            handle.write(text)
    freeze(seal,dict(frozen_at_utc=cohort['frozen_at_utc'],protected_hashes=baseline,
                     frozen_hashes={str(OUT/'phase5d_frozen_challenger_cohort.json').replace('\\','/'):file_hash(out/'phase5d_frozen_challenger_cohort.json'),
                                    doc.relative_to(root).as_posix():file_hash(doc)}))
    verify(root,baseline)
    return cohort


def forecast_id(row: dict) -> str:
    return digest({k:row[k] for k in ('target_quarter','model','horizon','release_lag_mode',
                                    'information_cutoff','monthly_data_hash','quarterly_data_hash','model_spec_hash')})


def validate_information_set(info: dict, cutoff: str) -> None:
    bound=pd.Timestamp(cutoff)
    if bound.tzinfo is None:
        bound=bound.tz_localize('UTC')
    for obs in info.get('observations',[]):
        retrieved=pd.Timestamp(obs['retrieved_at'])
        if retrieved.tzinfo is None:
            raise ValueError('Observation retrieval must include timezone')
        if retrieved>bound:
            raise ValueError('Future retrieval in earlier information set')
        if obs.get('source_release_date') and pd.Timestamp(obs['source_release_date'])>bound:
            raise ValueError('Future release in earlier information set')
        if obs.get('eligible_at') and pd.Timestamp(obs['eligible_at'])>bound:
            raise ValueError('Registry release lag violation')


def save_forecast(root: Path, row: dict, info: dict, *, inherited: bool=False) -> None:
    cohort=initialize(root)
    allowed={PRODUCTION}|{c['model_name'] for c in cohort['challengers']}
    if row['model'] not in allowed or row['horizon'] not in HORIZONS or row['release_lag_mode'] not in ('standard','conservative'):
        raise ValueError('Unfrozen model/horizon/lag mode')
    if pd.Period(row['target_quarter'],freq='Q')<pd.Period('2026Q3',freq='Q'):
        raise ValueError('Pre-prospective target')
    cutoff=pd.Timestamp(row['information_cutoff'])
    stamp=pd.Timestamp(row['forecast_timestamp_utc'])
    if cutoff>stamp:
        raise ValueError('Information cutoff after forecast writing')
    if not inherited and stamp<pd.Timestamp(cohort['frozen_at_utc']):
        raise ValueError('Backdated forecast')
    if inherited:
        source=root/legacy.OUTPUT_REL/'phase5c_current_shadow_nowcasts.csv'
        manifest=load(root/legacy.OUTPUT_REL/'phase5c_run_manifest.json')
        historical=pd.read_csv(source,float_precision='round_trip').set_index('model')
        value=float(historical.loc[row['model'],'H2_nowcast']) if row['horizon']=='H2' else None
        if (row['target_quarter']!='2026Q3' or row['forecast_value']!=value
                or row['forecast_timestamp_utc']!=manifest['timestamp_utc']
                or row['source_hash']!=file_hash(source) or row['release_lag_mode']!='standard'):
            raise ValueError('Inherited forecast must match the frozen Phase 5C record exactly')
    expected=(digest(cohort['production']) if row['model']==PRODUCTION else
              next(c['spec_hash'] for c in cohort['challengers'] if c['model_name']==row['model']))
    if row['model_spec_hash']!=expected:
        raise ValueError('Specification hash mismatch')
    validate_information_set(info,row['information_cutoff'])
    if row['forecast_status']=='AVAILABLE' and not np.isfinite(row['forecast_value']):
        raise ValueError('Available forecast must be finite')
    if row['forecast_status']!='AVAILABLE' and row['forecast_value'] is not None:
        raise ValueError('Missing forecast must remain null')
    row=dict(row)
    row['forecast_id']=forecast_id(row)
    row['information_set_hash']=digest(info)
    append_record(root/OUT/'information_sets',row['information_set_hash'],info)
    append_record(root/OUT/'forecast_records',row['forecast_id'],row)


def inherit(root: Path,cohort: dict) -> None:
    p=root/legacy.OUTPUT_REL
    source=p/'phase5c_current_shadow_nowcasts.csv'
    # round_trip preserves the exact floating values in the frozen CSV.
    table=pd.read_csv(source,float_precision='round_trip').set_index('model')
    manifest=load(p/'phase5c_run_manifest.json')
    production=load(root/legacy.PRODUCTION_NOWCAST_REL)
    for model in [PRODUCTION]+[c['model_name'] for c in cohort['challengers']]:
        spec=digest(cohort['production']) if model==PRODUCTION else next(c['spec_hash'] for c in cohort['challengers'] if c['model_name']==model)
        for h in HORIZONS:
            available=h=='H2'
            row=dict(run_id=manifest['run_id'],target_quarter='2026Q3',forecast_date='2026-09-30',
                     forecast_timestamp_utc=manifest['timestamp_utc'],information_cutoff=production['information_cutoff']+'T00:00:00Z',
                     horizon=h,model=model,model_family=str(table.loc[model,'model_family']),
                     forecast_value=float(table.loc[model,'H2_nowcast']) if available else None,
                     forecast_status='AVAILABLE' if available else 'UNAVAILABLE',release_lag_mode='standard',
                     monthly_data_hash=manifest['monthly_master_hash'],quarterly_data_hash=manifest['quarterly_master_hash'],
                     model_spec_hash=spec,git_commit=manifest['git_commit'],inherited_from_phase='5C',
                     notes='Immutable inherited H2; run-level timestamp' if available else 'No historical forecast recorded; never synthesized',
                     source_file=source.relative_to(root).as_posix(),source_hash=file_hash(source),
                     realization_status='LIVE_PROSPECTIVE_SHADOW_PENDING')
            info=dict(forecast_timestamp=row['forecast_timestamp_utc'],target_quarter='2026Q3',horizon=h,
                      information_cutoff=row['information_cutoff'],source_publication_cutoff=production['information_cutoff'],
                      last_available_month_by_predictor={'usd_uzs_mom_dlog':'2026-08-31'},
                      registry_lag_assumption='Frozen Phase 5C standard registry timing',
                      monthly_panel_hash=row['monthly_data_hash'],quarterly_target_hash=row['quarterly_data_hash'],
                      model_specification_hash=spec,code_commit_hash=manifest['git_commit'],
                      provenance_limitation='Inherited Phase 5C information convention; row-level historical release vintages unavailable',
                      source_information_file='results/phase5b1/phase5b1_information_set.csv',
                      source_information_hash=file_hash(root/'results/phase5b1/phase5b1_information_set.csv'))
            save_forecast(root,row,info,inherited=True)


def register_realization(root: Path, record: dict) -> None:
    """Append an evidenced official vintage; never change the primary value."""
    cohort=initialize(root)
    quarter=pd.Period(record['target_quarter'],freq='Q')
    if quarter<pd.Period('2026Q3',freq='Q'):
        raise ValueError('Historical outcomes cannot be prospective')
    release=pd.Timestamp(record['release_date'])
    retrieved=pd.Timestamp(record['retrieval_timestamp'])
    if release.tzinfo is None or retrieved.tzinfo is None:
        raise ValueError('Realization timestamps must include timezones')
    if release<=pd.Timestamp(cohort['frozen_at_utc']) or release>retrieved or retrieved>pd.Timestamp(now()):
        raise ValueError('Unverified release timing; no automatic retrospective admission')
    if release<=quarter.end_time.tz_localize('UTC'):
        raise ValueError('GDP quarter is not complete at release')
    forecasts=records(root/OUT/'forecast_records')
    if not any(r['target_quarter']==record['target_quarter'] and r['forecast_status']=='AVAILABLE'
               and pd.Timestamp(r['forecast_timestamp_utc'])<release
               and pd.Timestamp(r['information_cutoff'])<release for r in forecasts):
        raise ValueError('No genuinely pre-release frozen forecast for this realization')
    host=urlparse(record['source_url']).hostname or ''
    if not (host=='stat.uz' or host.endswith('.stat.uz')):
        raise ValueError('GDP must use official Statistics Agency/SIAT source')
    raw=(root/record['raw_file']).resolve()
    if not raw.is_relative_to(root.resolve()) or not raw.is_file() or file_hash(raw)!=record['data_hash']:
        raise ValueError('Missing or changed realization raw archive')
    if not record.get('release_date_evidence') or not record.get('parser_version'):
        raise ValueError('Release evidence and parser version required')
    if not np.isfinite(record['value']):
        raise ValueError('Non-numeric GDP')
    # Verify the realization value against the exact frozen official SIAT row,
    # rather than trusting a user-supplied number next to an official URL.
    from uznowcast.registry import load_registry
    from uznowcast.parsers.siat import parse_siat
    registry=load_registry(root/legacy.REGISTRY_REL)
    contract=load(root/'config/siat_contracts.json')['gdp_real_yoy']
    parsed=parse_siat(load(raw),registry.rows['gdp_real_yoy'],contract)
    selected=parsed[parsed.reference_period==record['target_quarter']]
    if len(selected)!=1 or not np.isfinite(selected.raw_value.iloc[0]) or float(selected.raw_value.iloc[0]-100)!=record['value']:
        raise ValueError('GDP realization does not match archived official exact-row value')
    directory=root/OUT/'realization_records'
    existing=records(directory)
    prior=[r for r in existing if r['target_quarter']==record['target_quarter']]
    if prior and retrieved < max(pd.Timestamp(r['retrieval_timestamp']) for r in prior):
        raise ValueError('Cannot insert an earlier realization vintage')
    if any(r['retrieval_timestamp']==record['retrieval_timestamp'] and r!=record for r in prior):
        raise ValueError('Conflicting realization at the same retrieval timestamp')
    append_record(directory,digest(record),record)


def realizations(root: Path) -> pd.DataFrame:
    rows=[]
    source=records(root/OUT/'realization_records')
    for q in sorted({r['target_quarter'] for r in source}):
        vintages=sorted([r for r in source if r['target_quarter']==q],key=lambda r:r['retrieval_timestamp'])
        first,last=vintages[0],vintages[-1]
        rows.append(dict(target_quarter=q,release_date=first['release_date'],retrieval_timestamp=first['retrieval_timestamp'],
                         first_observed_value=first['value'],current_value=last['value'],first_release_source=first['source_url'],
                         current_source=last['source_url'],revision_flag=last['value']!=first['value'],
                         revision_size=last['value']-first['value'],data_hash=first['data_hash'],
                         evidence_class='LIVE_PROSPECTIVE_REALIZED'))
    return pd.DataFrame(rows,columns=REALIZATION_COLUMNS)


def generate(root: Path, target: str) -> None:
    """Generate current-time forecasts only, with frozen component weights.

    Observation metadata bound actual retrieval, and registry lags bound
    economic period availability. No past origin can be reconstructed here.
    """
    from uznowcast.models.data import load_dataset, information_cutoff_for_variable, horizon_month_end
    from uznowcast.models.benchmarks import ar_forecast
    from uznowcast.models.midas import MidasSpec, midas_forecast
    from uznowcast.models.bridge import BridgeSpec, bridge_forecast
    cohort=initialize(root)
    timestamp=now()
    cutoff=pd.Timestamp(timestamp)
    quarter=pd.Period(target,freq='Q')
    if quarter < pd.Period('2026Q3',freq='Q') or quarter.start_time.tz_localize('UTC')>cutoff:
        raise ValueError('Target must be an existing prospective quarter')
    if any(r['target_quarter']==target for r in records(root/OUT/'realization_records')):
        raise ValueError('Cannot forecast an already realized quarter')
    dataset=load_dataset(root,registry_relative=str(legacy.REGISTRY_REL))
    observations=pd.read_parquet(root/'metadata/observations_long.parquet')
    # Snapshot files are immutable even after ingestion updates the master.
    snapshots=root/OUT/'input_snapshots'
    snapshots.mkdir(exist_ok=True)
    hashes={}
    for name,path in [('monthly',legacy.MONTHLY_REL),('quarterly',legacy.QUARTERLY_REL),
                      ('observations',Path('metadata/observations_long.parquet'))]:
        h=file_hash(root/path)
        destination=snapshots/(h+'.parquet')
        if not destination.exists():
            with destination.open('xb') as handle:
                handle.write((root/path).read_bytes())
        elif file_hash(destination)!=h:
            raise ValueError('Input snapshot corruption')
        hashes[name]=h
    implementation_hashes={}
    for path in (root/'src/uznowcast/shadow').glob('*.py'):
        h=file_hash(path)
        implementation_hashes[path.relative_to(root).as_posix()]=h
        destination=snapshots/(h+'.py')
        if not destination.exists():
            with destination.open('xb') as handle:
                handle.write(path.read_bytes())
        elif file_hash(destination)!=h:
            raise ValueError('Forecast code snapshot corruption')
    eligible=observations[pd.to_datetime(observations.retrieved_at,utc=True,errors='coerce')<=cutoff].copy()
    release=pd.to_datetime(eligible.source_release_date,utc=True,errors='coerce')
    eligible=eligible[release.isna()|(release<=cutoff)]
    eligible=eligible[eligible.frequency.astype(str).str.lower().isin(['monthly','m'])]
    eligible=eligible[eligible.clean_value.notna() & eligible.clean_model_field.notna()]
    eligible=eligible.sort_values('retrieved_at').drop_duplicates(['reference_period','clean_model_field'],keep='last')
    dates=pd.to_datetime(eligible.reference_date,errors='coerce').dt.to_period('M').dt.to_timestamp('M')
    eligible=eligible.assign(date=dates)
    gdp=pd.read_parquet(root/legacy.QUARTERLY_REL)
    if target in set(gdp.quarter.astype(str)):
        raise ValueError('Official target outcome already appears in master; forecast refused')
    gdp=gdp[(gdp.quarter.astype(str)<target)
            &(pd.to_datetime(gdp.retrieved_at,utc=True,errors='coerce')<=cutoff)]
    gdp_release=pd.to_datetime(gdp.source_release_date,utc=True,errors='coerce')
    gdp=gdp[gdp_release.isna()|(gdp_release<=cutoff)]
    dataset=replace(dataset,gdp=gdp[['quarter','gdp_real_yoy_pct']].sort_values('quarter').copy())
    commit=legacy.git_text(root,'rev-parse','HEAD')
    for mode in ('standard','conservative'):
        signal=eligible[eligible.clean_model_field=='usd_uzs_mom_dlog'].copy()
        key=dataset.monthly_key_by_field['usd_uzs_mom_dlog']
        lag=dataset.release_lag_days[key]
        extra=(3 if lag==0 else 15) if mode=='conservative' else 0
        signal=signal[signal.date+pd.to_timedelta(lag+extra,unit='D')<=cutoff.tz_localize(None)]
        quarter_months=pd.date_range(quarter.start_time,quarter.end_time,freq='ME')
        contiguous=0
        for month in quarter_months:
            if month in set(signal.date):
                contiguous+=1
            else:
                break
        if contiguous==0:
            continue
        horizon=HORIZONS[contiguous-1]
        panel=eligible.pivot(index='date',columns='clean_model_field',values='clean_value').sort_index()
        # Filter each predictor using actual current-time eligibility as well as
        # the inherited horizon-specific information convention in model functions.
        latest={}
        admitted=[]
        for field in ['usd_uzs_mom_dlog']:
            key=dataset.monthly_key_by_field[field]
            days=dataset.release_lag_days[key]
            days+=(3 if days==0 else 15) if mode=='conservative' else 0
            rows=eligible[(eligible.clean_model_field==field)&
                          (eligible.date+pd.to_timedelta(days,unit='D')<=cutoff.tz_localize(None))]
            panel.loc[panel.index+pd.to_timedelta(days,unit='D')>cutoff.tz_localize(None),field]=np.nan
            last=information_cutoff_for_variable(horizon_month_end(target,horizon),key,dataset.release_lag_days,mode)
            panel.loc[panel.index>last,field]=np.nan
            rows=rows[rows.date<=last]
            latest[field]=rows.date.max().date().isoformat() if not rows.empty else None
            for obs in rows.to_dict('records'):
                admitted.append(dict(reference_period=str(obs['reference_period']),predictor=field,
                                     retrieved_at=str(obs['retrieved_at']),
                                     source_release_date=None if pd.isna(obs['source_release_date']) else str(obs['source_release_date']),
                                     eligible_at=(pd.Timestamp(obs['date']).tz_localize('UTC')+pd.Timedelta(days=days)).isoformat()))
        for obs in gdp.to_dict('records'):
            admitted.append(dict(reference_period=obs['quarter'],predictor='gdp_real_yoy_pct',
                                 retrieved_at=str(obs['retrieved_at']),
                                 source_release_date=None if pd.isna(obs['source_release_date']) else str(obs['source_release_date'])))
        dataset=replace(dataset,monthly=panel)
        train=dataset.gdp.quarter.astype(str).tolist()
        components={}
        errors=[]
        try:
            expected=pd.period_range(train[0],str(quarter-1),freq='Q').astype(str).tolist() if train else []
            if len(train)<12 or train!=expected or dataset.gdp.gdp_real_yoy_pct.isna().any():
                raise ValueError('Insufficient or noncontiguous GDP history for next-quarter forecast')
            components['ar2']=ar_forecast(dataset.gdp.set_index('quarter').gdp_real_yoy_pct.reindex(train),2)[0]
            usd,usd_diagnostics=midas_forecast(dataset,MidasSpec('usd','usd_uzs_mom_dlog',3),train,target,horizon=horizon,mode=mode)
            if not np.isfinite(usd) or int(usd_diagnostics.get('n_train',0))<15:
                raise ValueError('Frozen production U-MIDAS effective training minimum not met')
            components[PRODUCTION]=0.5*components['ar2']+0.5*usd
            components['challenger_umidas_usd_uzs_mom_dlog_l1']=midas_forecast(
                dataset,MidasSpec('usd_l1','usd_uzs_mom_dlog',1),train,target,horizon=horizon,mode=mode)[0]
            components['bridge_usd_uzs_mom_dlog']=bridge_forecast(
                dataset,BridgeSpec('bridge',('usd_uzs_mom_dlog',)),train,target,horizon=horizon,mode=mode)[0]
        except (ValueError,KeyError,np.linalg.LinAlgError) as exc:
            errors.append(str(exc))
        specs=[dict(model_name=PRODUCTION,family='production_benchmark',spec_hash=digest(cohort['production']))]+cohort['challengers']
        for spec in specs:
            model=spec['model_name']
            if model==PRODUCTION:
                value=components.get(model,np.nan)
            else:
                weight=spec['weights_by_horizon'][horizon]
                value=sum(weight[c]*components.get(c,np.nan) for c in spec['components'])
            available=np.isfinite(value)
            row=dict(run_id='phase5d-'+timestamp,target_quarter=target,forecast_date=timestamp[:10],
                     forecast_timestamp_utc=timestamp,information_cutoff=timestamp,horizon=horizon,
                     model=model,model_family=spec['family'],forecast_value=float(value) if available else None,
                     forecast_status='AVAILABLE' if available else 'FAILED',release_lag_mode=mode,
                     monthly_data_hash=hashes['monthly'],quarterly_data_hash=hashes['quarterly'],
                     model_spec_hash=spec['spec_hash'],git_commit=commit,inherited_from_phase=None,
                     notes='; '.join(errors) if errors else ('Frozen prospective forecast' if available else 'Required component unavailable'),
                     source_file='input_snapshots',source_hash=hashes['observations'],
                     realization_status='LIVE_PROSPECTIVE_SHADOW_PENDING')
            info=dict(forecast_timestamp=timestamp,target_quarter=target,horizon=horizon,
                      source_publication_cutoff=timestamp,last_available_month_by_predictor=latest,
                      registry_lag_assumption={k:dataset.release_lag_days[k] for k in dataset.release_lag_days},
                      release_lag_mode=mode,monthly_panel_hash=hashes['monthly'],quarterly_target_hash=hashes['quarterly'],
                      observations_hash=hashes['observations'],model_specification_hash=spec['spec_hash'],
                      code_commit_hash=commit,implementation_hashes=implementation_hashes,observations=admitted)
            save_forecast(root,row,info)


def revision_table(forecasts: pd.DataFrame) -> pd.DataFrame:
    columns=['target_quarter','model','release_lag_mode','H1_H2_revision','H2_H3_revision','H1_H3_revision']
    if forecasts.empty:
        return pd.DataFrame(columns=columns)
    f=forecasts.sort_values('forecast_timestamp_utc').drop_duplicates(
        ['target_quarter','model','release_lag_mode','horizon'])
    rows=[]
    for (q,m,lag),group in f.groupby(['target_quarter','model','release_lag_mode']):
        values=group.set_index('horizon').forecast_value
        row=dict(target_quarter=q,model=m,release_lag_mode=lag)
        for a,b in [('H1','H2'),('H2','H3'),('H1','H3')]:
            row[f'{a}_{b}_revision']=values.get(b,np.nan)-values.get(a,np.nan)
        rows.append(row)
    return pd.DataFrame(rows,columns=columns)


def scorecard(cohort: dict, forecasts: pd.DataFrame, actual: pd.DataFrame,
              scores: pd.DataFrame, revisions: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    rows,diagnostics=[],[]
    quarters=actual.target_quarter.tolist()
    models=[PRODUCTION]+[c['model_name'] for c in cohort['challengers']]
    for mode in ('standard','conservative'):
        for model in models:
            for horizon in (*HORIZONS,'POOLED_H1_H3'):
                h=list(HORIZONS) if horizon=='POOLED_H1_H3' else [horizon]
                subset=scores[(scores.model==model)&scores.horizon.isin(h)&(scores.release_lag_mode==mode)]
                metrics=matched_metrics(subset)
                f=forecasts[(forecasts.model==model)&forecasts.horizon.isin(h)&
                            (forecasts.release_lag_mode==mode)&forecasts.target_quarter.isin(quarters)]
                denominator=len(quarters)*len(h)
                available=f[f.forecast_status=='AVAILABLE'].drop_duplicates(['target_quarter','horizon'])
                attempts=f[f.forecast_status!='UNAVAILABLE']
                n=subset.dropna(subset=['forecast','production_forecast']).target_quarter.nunique()
                r=revisions[(revisions.model==model)&(revisions.release_lag_mode==mode)]
                changes=r[['H1_H2_revision','H2_H3_revision','H1_H3_revision']].to_numpy().flatten()
                changes=np.abs(changes[np.isfinite(changes)])
                row=dict(model=model,horizon=horizon,release_lag_mode=mode,
                         prospective_quarters_available=len(quarters),matched_quarters=n,
                         coverage=len(available)/denominator if denominator else 0,
                         forecast_availability=len(available),failure_rate=float((attempts.forecast_status=='FAILED').mean()) if len(attempts) else np.nan,
                         mean_revision_size=float(changes.mean()) if len(changes) else np.nan,
                         median_revision_size=float(np.median(changes)) if len(changes) else np.nan,
                         maximum_revision_size=float(changes.max()) if len(changes) else np.nan,
                         status=evidence_status(n),**metrics)
                rows.append(row)
            result=influence(scores[(scores.model==model)&(scores.release_lag_mode==mode)])
            diagnostics.append(dict(model=model,release_lag_mode=mode,**result))
    table=pd.DataFrame(rows)
    for model in models:
        if model==PRODUCTION:
            table.loc[table.model==model,'governance_flag']='FROZEN_PRODUCTION_BENCHMARK'
            continue
        standard=table[(table.model==model)&(table.release_lag_mode=='standard')]
        conservative=table[(table.model==model)&(table.release_lag_mode=='conservative')]
        pooled=standard[standard.horizon=='POOLED_H1_H3'].iloc[0]
        production=table[(table.model==PRODUCTION)&(table.release_lag_mode=='standard')&(table.horizon=='POOLED_H1_H3')].iloc[0]
        by_h=standard[standard.horizon.isin(HORIZONS)]
        cons=conservative[conservative.horizon=='POOLED_H1_H3'].iloc[0]
        diag=next(d for d in diagnostics if d['model']==model and d['release_lag_mode']=='standard')
        checks=dict(influence=diag['influence_flag']=='ROBUST_PROSPECTIVE_IMPROVEMENT',
                    horizons=bool((by_h.matched_quarters>=4).all() and (by_h.relative_rmse<=1.05).all()),
                    mae=bool(pooled.relative_mae<=1.02),bias=bool(abs(pooled.bias)<=0.5),
                    coverage=bool(pooled.coverage>=max(0.8,0.9*production.coverage)),
                    failures=bool(pooled.failure_rate<=0.05),
                    revisions=bool(np.isfinite(pooled.mean_revision_size) and np.isfinite(production.mean_revision_size)
                                   and pooled.mean_revision_size<=max(0.5,1.5*production.mean_revision_size)),
                    lag_consistency=bool(cons.matched_quarters>=4 and cons.relative_rmse<1 and
                                         (conservative[conservative.horizon.isin(HORIZONS)].relative_rmse.to_numpy()
                                          -by_h.relative_rmse.to_numpy()<=0.05).all()),
                    reproducible=True)
        flag=governance(int(pooled.matched_quarters),pooled.to_dict(),checks)
        table.loc[table.model==model,'governance_flag']=flag
        table.loc[table.model==model,'governance_checks']=json.dumps(checks,sort_keys=True)
    return table,pd.DataFrame(diagnostics)


def refresh(root: Path,tests: dict|None=None) -> dict:
    start_status=legacy.git_text(root,'status','--porcelain').splitlines()
    cohort=initialize(root)
    seal=load(root/OUT/'phase5d_freeze_manifest.json')
    inherit(root,cohort)
    forecast_records=records(root/OUT/'forecast_records')
    for row in forecast_records:
        info=load(root/OUT/'information_sets'/f"{row['information_set_hash']}.json")
        if digest(info)!=row['information_set_hash'] or forecast_id(row)!=row['forecast_id']:
            raise ValueError('Forecast ledger integrity failure')
        if row.get('inherited_from_phase')=='5C' and file_hash(root/row['source_file'])!=row['source_hash']:
            raise ValueError('Inherited forecast source changed')
    forecasts=pd.DataFrame(forecast_records,columns=FORECAST_COLUMNS).sort_values(
        ['target_quarter','horizon','model','release_lag_mode','forecast_timestamp_utc'])
    actual=realizations(root)
    # Realization status is a derived mirror field; the immutable forecast record
    # retains exactly what was known when the forecast was written.
    forecasts.loc[forecasts.target_quarter.isin(actual.target_quarter),'realization_status']='LIVE_PROSPECTIVE_REALIZED'
    scores=quarter_scores(forecasts,actual)
    revisions=revision_table(forecasts)
    table,diagnostics=scorecard(cohort,forecasts,actual,scores,revisions)
    diagnostics['dropped_quarter_results']=diagnostics.dropped_quarter_results.map(
        lambda value:json.dumps(value,sort_keys=True))
    out=root/OUT
    for name,frame in [('forecast_vintages',forecasts),('gdp_realizations',actual),('quarter_level_scorecard',scores),
                       ('prospective_scorecard',table),('forecast_revisions',revisions),('influence_diagnostics',diagnostics)]:
        frame.to_csv(out/f'{PREFIX}{name}.csv',index=False)
        frame.to_parquet(out/f'{PREFIX}{name}.parquet',index=False)
    n=len(actual)
    status='WAITING_FOR_FIRST_PROSPECTIVE_GDP_RELEASE' if n==0 else evidence_status(n)
    latest=forecasts[forecasts.forecast_status=='AVAILABLE'].sort_values('forecast_timestamp_utc').iloc[-1]
    warnings=['Inherited 2026Q3 H1/H3 were not recorded; no forecasts synthesized.',
              'Phase 5C combination conservative-lag evidence is unavailable; eligibility remains blocked until tested prospectively.',
              'GDP source-release fields in existing target are dataset update timestamps, not reliable historical first releases.',
              'No newly verified GDP realization has been registered.' if not n else 'Primary actual is first observed official vintage, not necessarily first publication.']
    notes_path=out/'phase5d_official_source_check.json'
    if notes_path.exists():
        warnings.extend(load(notes_path).get('warnings',[]))
    code_hashes={f.relative_to(root).as_posix():file_hash(f) for f in (root/'src/uznowcast/shadow').glob('*.py')}
    previous=load(out/'phase5d_run_manifest.json') if (out/'phase5d_run_manifest.json').exists() else {}
    if tests is None and previous.get('code_hashes')==code_hashes:
        tests=previous.get('tests',{})
    manifest=dict(phase='5D',version='5d.0',run_id='phase5d-'+now(),timestamp_utc=now(),
                  git_commit=legacy.git_text(root,'rev-parse','HEAD'),git_branch=legacy.git_text(root,'branch','--show-current'),
                  working_tree_status_at_start=start_status,code_hashes=code_hashes,
                  hashes=dict(phase5c_manifest=file_hash(root/legacy.OUTPUT_REL/'phase5c_run_manifest.json'),
                              frozen_challenger_cohort=file_hash(out/'phase5d_frozen_challenger_cohort.json'),
                              phase5d_protocol=file_hash(root/DOC/'phase5d_prospective_shadow_protocol.md'),
                              registry=file_hash(root/legacy.REGISTRY_REL),monthly_panel=file_hash(root/legacy.MONTHLY_REL),
                              quarterly_panel=file_hash(root/legacy.QUARTERLY_REL),
                              production_baseline=file_hash(root/legacy.PRODUCTION_NOWCAST_REL),
                              model_specifications={c['model_name']:c['spec_hash'] for c in cohort['challengers']}),
                  forecasts_written=int(forecasts.inherited_from_phase.isna().sum()),
                  forecasts_inherited=int(((forecasts.inherited_from_phase=='5C')&(forecasts.forecast_status=='AVAILABLE')).sum()),
                  realizations_added=len(records(out/'realization_records')),prospective_quarters_realized=n,
                  models_evaluated=[PRODUCTION]+[c['model_name'] for c in cohort['challengers']],
                  current_target=str(latest.target_quarter),status=status,evidence_status=evidence_status(n),
                  warnings=warnings,errors=[],tests=tests or {},protected_hash_failures=[],
                  protected_artifacts_checked=len(seal['protected_hashes']),production_artifacts_modified=False)
    # An HTML monitor needs no Streamlit or production dashboard mutation.
    sections=[('Official production nowcast',forecasts[(forecasts.model==PRODUCTION)&(forecasts.forecast_status=='AVAILABLE')]),
              ('H1/H2/H3 and frozen shadow challenger forecasts',forecasts),('Forecast revisions',revisions),
              ('Cumulative prospective RMSE / MAE and relative RMSE',table[table.horizon=='POOLED_H1_H3']),
              ('Horizon-specific performance',table[table.horizon.isin(HORIZONS)]),('Quarter-by-quarter errors',scores),
              ('Stability / influence warnings',diagnostics)]
    page='<!doctype html><html lang="en"><meta charset="utf-8"><title>Phase 5D shadow monitor</title>'
    page+='<style>body{font:15px system-ui;margin:32px;color:#172b4d}table{border-collapse:collapse;font-size:12px;display:block;overflow:auto}td,th{padding:7px;border:1px solid #ccd}h1{color:#16496b}.notice{background:#fff1bf;padding:16px}</style>'
    page+='<h1>PHASE 5D — PROSPECTIVE SHADOW EVALUATION</h1><p class="notice">NOT AN OFFICIAL MODEL REPLACEMENT</p>'
    page+=f'<p>Current target: {html.escape(str(latest.target_quarter))}; genuinely realized prospective quarters: {n}</p>'
    page+=f'<p>Governance evidence status: {status}. Latest forecast timestamp: {html.escape(str(latest.forecast_timestamp_utc))}; information cutoff: {html.escape(str(latest.information_cutoff))}</p>'
    page+='<p>Official inherited production H2: 7.6239786596%. Challenger forecasts are shadow research only. Single observations do not justify replacement.</p>'
    for title,frame in sections:
        page+='<h2>'+title+'</h2>'+frame.to_html(index=False,escape=True,na_rep='N/A')
    page+='<h2>Data-quality notes</h2><ul>'+''.join('<li>'+html.escape(w)+'</li>' for w in warnings)+'</ul></html>'
    (root/'dashboard/phase5d_shadow_monitor.html').write_text(page,encoding='utf-8')
    report=f'''# Phase 5D prospective results

Status: {status}. Prospective realized quarters: {n}.
Production unchanged: `{PRODUCTION}`. Historical 2026Q3 H2: 7.6239786595896035%.
Frozen research challengers: {', '.join(c['model_name'] for c in cohort['challengers'])}.
Four exact H2 forecasts inherited; H1/H3 unavailable. No models re-estimated on initialization.
No replacement is authorized. Best challenger is NOT_YET_EVALUABLE until prospective outcomes exist.

Warnings:
'''+''.join('- '+w+'\n' for w in warnings)+'''
## Operations

`python -m uznowcast.shadow.phase5d initialize` checks freezes and rebuilds mirrors.
`python -m uznowcast.shadow.phase5d forecast --target 2026Q4` generates current-time
forecasts using the frozen cohort and actual retrieval-bounded observations;
target quarters have no configured end. Refresh ingestion separately before forecasting.
`python -m uznowcast.shadow.phase5d realize --record path.json` appends an official
realization: target_quarter, release_date (timezone), retrieval_timestamp (timezone),
value, source_url, raw_file (workspace relative), data_hash (SHA256),
release_date_evidence, parser_version. Archive official raw data before registration.
Unknown or retrospective release evidence is rejected; do not guess timestamps.
`python -m uznowcast.shadow.phase5d refresh` scores matched forecasts and regenerates
the standalone dashboard. Frozen JSON ledgers are authoritative and immutable.
CSV/Parquet are rebuildable mirrors. No operation writes to production.
'''
    (root/DOC/'phase5d_prospective_results.md').write_text(report,encoding='utf-8')
    verify(root,seal['protected_hashes'])
    verify(root,seal['frozen_hashes'])
    write_json(out/'phase5d_run_manifest.json',manifest)
    return manifest


def terminal_summary(root: Path,manifest: dict) -> str:
    cohort=load(root/OUT/'phase5d_frozen_challenger_cohort.json')
    table=pd.read_csv(root/OUT/'phase5d_prospective_scorecard.csv')
    candidates=table[(table.model!=PRODUCTION)&(table.horizon=='POOLED_H1_H3')&
                     (table.release_lag_mode=='standard')&table.relative_rmse.notna()].sort_values('relative_rmse')
    best=str(candidates.model.iloc[0]) if len(candidates) else 'NOT_YET_EVALUABLE'
    relative=f'{candidates.relative_rmse.iloc[0]:.6f}' if len(candidates) else 'N/A'
    eligible=bool((table.governance_flag=='GOVERNANCE_REVIEW_ELIGIBLE').any())
    return f'''PHASE 5D PROSPECTIVE SHADOW FRAMEWORK COMPLETE
Production model: {PRODUCTION}
Production modified: NO
Frozen challengers: {', '.join(c['model_name'] for c in cohort['challengers'])}
Excluded REJECT models: {sum(c['phase5c_gate']=='REJECT' for c in cohort['excluded'])}
First prospective target: 2026Q3
Prospective realized quarters: {manifest['prospective_quarters_realized']}
Current target: {manifest['current_target']}
Evidence status: {manifest['evidence_status']}
Best prospective challenger: {best}
Matched prospective relative RMSE: {relative}
Governance review eligible: {'YES' if eligible else 'NO'}
Protected artifacts checked: {manifest['protected_artifacts_checked']}
Protected hash failures: 0
Repository tests: {manifest['tests'].get('repository','not yet run')}
Phase 5D tests: {manifest['tests'].get('phase5d','not yet run')}
Warnings: {'; '.join(manifest['warnings'])}
Next action: {'GOVERNANCE_REVIEW_MAY_BE_CONSIDERED' if eligible else ('WAIT_FOR_NEW_GDP_RELEASE' if not manifest['prospective_quarters_realized'] else 'CONTINUE_SHADOW_TRACKING')}'''


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['initialize','refresh','forecast','realize'])
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--target')
    parser.add_argument('--record',type=Path)
    args=parser.parse_args()
    root=args.root.resolve()
    initialize(root)
    if args.command=='forecast':
        if not args.target:
            parser.error('--target required')
        generate(root,args.target)
    elif args.command=='realize':
        if not args.record:
            parser.error('--record required')
        register_realization(root,load(args.record))
    manifest=refresh(root)
    print(terminal_summary(root,manifest))


if __name__=='__main__':
    main()
