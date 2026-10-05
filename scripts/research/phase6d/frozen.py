"""Verify the Phase 6C freeze and define immutable prospective challengers."""
import json
from datetime import datetime, timezone

from common import (ROOT, OUT, FIELDS, MODELS, WEIGHT_DFM, WEIGHT_UMIDAS,
                    file_hash, freeze, digest, verify_hashes, protection)

CODE_PATHS = ['scripts/research/phase6c/kernel.py','scripts/research/phase6b2/vintages.py',
              'scripts/research/phase6b2/run.py','src/uznowcast/models/data.py',
              'src/uznowcast/models/midas.py','src/uznowcast/models/benchmarks.py',
              'src/uznowcast/shadow/storage.py','src/uznowcast/registry.py']
SOURCE_NAMES = ['protocol.json','selection_freeze.json','run_manifest.json','model_definitions.csv',
                'forecasts.csv','combination_metrics.csv','transformations.csv','research_monthly_panel.csv',
                'predictor_audit.csv','determinism_checks.json']


def initialize(out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'phase6d_frozen_challengers.json'
    if path.exists():
        bundle = json.loads(path.read_text())
        verify_hashes(ROOT, bundle['source_artifact_hashes'])
        verify_hashes(ROOT, bundle['code_hashes'])
        verify_hashes(ROOT, bundle['static_specification_hashes'])
        if bundle['weights']['COMBO_DEV_WEIGHT'] != {'dfm':WEIGHT_DFM,'umidas':WEIGHT_UMIDAS}:
            raise ValueError('Frozen weights changed')
        freeze(path, bundle)
        return bundle
    source = ROOT / 'results/phase6c'
    selection = json.loads((source/'phase6c_selection_freeze.json').read_text())
    protocol = json.loads((source/'phase6c_protocol.json').read_text())
    manifest = json.loads((source/'phase6c_run_manifest.json').read_text())
    for name,h in manifest['outputs'].items():
        if file_hash(source/name)!=h:
            raise ValueError('Phase6C manifest mismatch: '+name)
    spec = selection['selected_factor_specification']
    assert selection['final_model']=='DFM-4_R1_P2__BRIDGE_B_mean'
    assert tuple(spec['fields'])==FIELDS and spec['factors']==1 and spec['order']==2
    assert not spec['winsor'] and spec['start']=='2019-01-31' and spec['balanced']
    assert selection['selected_bridge']=='B' and selection['selected_aggregation']=='mean'
    assert selection['frozen_combination_DFM_weight']==WEIGHT_DFM
    assert protocol['final_model']==selection['final_model']
    import pandas as pd
    transforms = pd.read_csv(source/'phase6c_transformations.csv').set_index('variable')
    definitions = {name: dict(model=name) for name in MODELS}
    definitions['PHASE6C_DFM'].update(source_model=selection['final_model'],factor_specification=spec,
        bridge='B', aggregation='mean', transformations={k:transforms.loc[k].to_dict() for k in FIELDS},
        standardization='masked_training_mean_sample_std_before_target_quarter',
        likelihood=dict(estimator='DynamicFactorMQ_EM',maxiter=500,tolerance=1e-5,idiosyncratic_ar1=False),
        GDP_boundary='Phase6B2 strict documented vintage accessor; no unknown-value fallback')
    definitions['UMIDAS_USD'].update(source_model='umidas_usd_uzs_mom_dlog',field='usd_uzs_mom_dlog',
        monthly_lags=3, with_gdp_lag=True, polynomial_order=None, minimum_effective_training=15)
    definitions['AR1'].update(order=1)
    definitions['AR2'].update(order=2)
    definitions['PRODUCTION_ENSEMBLE'].update(components={'AR2':.5,'UMIDAS_USD':.5},shadow_reproduction_only=True)
    weights = {'COMBO_50_50':{'dfm':.5,'umidas':.5},
               'COMBO_DEV_WEIGHT':{'dfm':WEIGHT_DFM,'umidas':WEIGHT_UMIDAS}}
    for name,w in weights.items():
        definitions[name].update(components=['PHASE6C_DFM','UMIDAS_USD'],weights=w)
    bundle = dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        phase6c_actual_freeze_timestamp=selection['specification_freeze_recorded_at'],
        phase6c_retrospective_selection_cutoff=selection['selection_cutoff'],
        phase6c_historical_specification_hash=selection['specification_sha256'],
        challengers=definitions, specification_hashes={m:digest(d) for m,d in definitions.items()},
        weights=weights, code_hashes={p:file_hash(ROOT/p) for p in CODE_PATHS},
        source_artifact_hashes={('results/phase6c/phase6c_'+n):file_hash(source/('phase6c_'+n)) for n in SOURCE_NAMES},
        static_specification_hashes={'registry/uzbekistan_nowcasting_v1.2_registry.xlsx':file_hash(ROOT/'registry/uzbekistan_nowcasting_v1.2_registry.xlsx')})
    freeze(path, bundle)
    freeze(out/'phase6d_protocol.json', dict(initialized_at_utc=bundle['frozen_at_utc'], shadow_only=True,
        no_retuning=True, primary_target='VERIFIED_FIRST_RELEASE',primary_lag_mode='standard',
        timing_rule='STRICT', horizon_definition='Phase6C calendar horizon_month_end, unchanged',
        late_initialization='Actual timestamp retained; late/pre-horizon snapshots excluded from on-time H1/H2/H3 metrics and scored separately',
        primary_snapshot='First available pre-release snapshot per target/model/horizon/operational_stage',
        CSV_ledger_policy='Append-only bytes with sealed immutable batches; realized scores kept in separate view',
        source_release_policy='SIAT dataset update is never used as first publication; explicit reviewed official first-release evidence required',
        governance=['INITIALIZED','EARLY_EVIDENCE','INSUFFICIENT_EVIDENCE','PRELIMINARY_REVIEW','GOVERNANCE_REVIEW_ELIGIBLE'],
        specification_hashes=bundle['specification_hashes']))
    freeze(out/'phase6d_protected_start.json', protection())
    return bundle
