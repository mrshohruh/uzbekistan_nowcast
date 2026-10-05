"""Evidence tests; never write to historical production or shadow artifacts."""
import importlib.util
from pathlib import Path
import json
import pandas as pd
import pytest

MODULE=Path(__file__).with_name('reconcile.py')
spec=importlib.util.spec_from_file_location('production_reconciliation',MODULE)
reconcile=importlib.util.module_from_spec(spec);spec.loader.exec_module(reconcile)
ROOT=reconcile.ROOT
OUT=reconcile.OUT


def test_historical_manifest_byte_identical():
    baseline=reconcile.read(OUT/'baseline.json')
    for path in ['results/production/run_manifest.json','results/production/current_nowcast.json',
                 'results/phase5b1/phase5b1_run_manifest.json','results/phase4b_candidate_freeze.json']:
        assert reconcile.sha(ROOT/path)==baseline[path]


def test_expected_historical_hashes_not_rewritten():
    old=reconcile.read(ROOT/'results/production/run_manifest.json')
    assert old['input_data_fingerprints']['monthly_master_hash']=='78a7c51b97247d3ccbd72cbcb03b89f6f52f0f091201956bba85c0373856ba7c'
    assert old['input_data_fingerprints']['quarterly_master_hash']=='36793699e48de74ecfe31eeb7eb8f23cf3eb6f2ab9ca929cdd4bb240c1bdfbac'


def test_current_state_cannot_masquerade_as_old_release():
    old=reconcile.read(ROOT/'results/production/run_manifest.json')
    current=dict(**reconcile.read(OUT/'current_calculation.json'),does_not_replace_historical_release=True,historical_release_reproduction=False)
    reconcile.validate_state_identity(current,old)
    for mutation in [{'scope':'HISTORICAL_RELEASE_REPRODUCTION'},{'run_id':old['run_id']},
                     {'timestamp_utc':old['run_timestamp_utc']},{'historical_release_reproduction':True},
                     {'does_not_replace_historical_release':False}]:
        with pytest.raises(ValueError):reconcile.validate_state_identity({**current,**mutation},old)


def test_entire_phase6d_unchanged():
    baseline=reconcile.read(OUT/'baseline.json')
    expected={p:h for p,h in baseline.items() if p.startswith('results/phase6d/') or p.startswith('scripts/research/phase6d/')}
    for path,h in expected.items():assert reconcile.sha(ROOT/path)==h,path
    current={p.relative_to(ROOT).as_posix() for p in (ROOT/'results/phase6d').rglob('*') if p.is_file()}
    assert current=={p for p in expected if p.startswith('results/phase6d/')}


def test_model_code_and_specs_unchanged():
    baseline=reconcile.read(OUT/'baseline.json')
    selected={p:h for p,h in baseline.items() if p.startswith('src/') or
              (p.endswith('.json') and any(x in p for x in ['candidate_freeze','frozen_challengers','production_policy','model_specs']))}
    for path,h in selected.items():assert reconcile.sha(ROOT/path)==h,path


def test_current_forecasts_reproduce_from_current_inputs():
    from uznowcast.models.data import load_dataset
    from uznowcast.operational.phase5a import generate_nowcasts
    saved=reconcile.read(OUT/'current_calculation.json')
    actual,_=generate_nowcasts(load_dataset(ROOT),saved['as_of_date'],saved['target'],saved['operational_stage'],saved['input_hashes'],saved['timestamp_utc'])
    for row in actual.to_dict('records'):
        assert row['prediction']==pytest.approx(saved['forecasts'][row['model']],abs=1e-10)
    shadow=reconcile.read(OUT/'validation_shadow.json')
    assert len(shadow['forecasts'])==7
    assert all(r['absolute_difference']<1e-8 for r in shadow['forecasts'])


def test_unknown_historical_observations_never_fabricated():
    found=reconcile.read(OUT/'historical_input_locations.json')
    differences=pd.read_csv(OUT/'master_difference_summary.csv')
    for kind,locations in found.items():
        if not locations:
            row=differences.loc[differences.dataset.eq(kind)].iloc[0]
            for field in ['n_rows_old','new_rows','changed_existing_rows','removed_rows','schema_changed','economic_values_changed']:
                assert pd.isna(row[field]),(kind,field)
            assert 'cannot be determined' in row.assessment
    searched=pd.read_csv(OUT/'historical_master_search.csv')
    assert all(row.candidate_hash==row.expected_hash for row in searched[searched.exact_match].itertuples())
