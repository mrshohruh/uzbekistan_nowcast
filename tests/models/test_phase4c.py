"""Phase 4C protocol-lock and frozen holdout evaluation tests."""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
import pytest

from uznowcast.models.data import ModelingDataset
from uznowcast.models.phase4c import (
    EXPECTED_HOLDOUT, FROZEN_PRIMARY_CANDIDATES, _rules_sha256,
    ensemble_diagnostics, evaluate_phase4c, holdout_metrics,
    horizon_updates, load_phase4c_dataset, model_comparison,
)


def _phase4c_dataset(synthetic_dataset) -> ModelingDataset:
    dataset = synthetic_dataset
    dataset.monthly['usd_uzs_mom_dlog'] = np.linspace(
        -1.0, 2.0, len(dataset.monthly))
    clean = dict(dataset.clean_field_by_key)
    clean['usd_uzs'] = 'usd_uzs_mom_dlog'
    gdp = dataset.gdp.copy()
    gdp['quarter'] = gdp['quarter'].str.replace('-', '', regex=False)
    return ModelingDataset(
        gdp=gdp, monthly=dataset.monthly.copy(),
        registry=dataset.registry,
        release_lag_days={**dataset.release_lag_days, 'usd_uzs': 0},
        clean_field_by_key=clean,
        monthly_key_by_field={field: key for key, field in clean.items()},
    )


def _opened_protocol() -> dict:
    rules = {
        'holdout_quarters': list(EXPECTED_HOLDOUT),
        'primary_candidates': list(FROZEN_PRIMARY_CANDIDATES),
    }
    return {
        'status': 'HOLDOUT_OPENED_PROTOCOL_LOCKED',
        'evaluation_rules': rules,
        'evaluation_rules_sha256': _rules_sha256(rules),
    }


def test_phase4c_evaluates_only_frozen_models(synthetic_dataset):
    dataset = _phase4c_dataset(synthetic_dataset)
    predictions = evaluate_phase4c(dataset, _opened_protocol())
    assert set(predictions['model']) == {
        'historical_mean', *FROZEN_PRIMARY_CANDIDATES}
    assert set(predictions['target_quarter']) == set(EXPECTED_HOLDOUT)
    assert len(predictions) == 5 * 4 * 3 * 2
    assert predictions['architecture_frozen'].all()


def test_phase4c_expanding_window_adds_only_prior_holdout(synthetic_dataset):
    dataset = _phase4c_dataset(synthetic_dataset)
    predictions = evaluate_phase4c(dataset, _opened_protocol())
    last_train = (predictions.groupby('target_quarter')['training_last_quarter']
                  .first().to_dict())
    assert last_train == {
        '2025Q3': '2025Q2', '2025Q4': '2025Q3',
        '2026Q1': '2025Q4', '2026Q2': '2026Q1',
    }


def test_phase4c_reports_all_required_comparisons(synthetic_dataset):
    dataset = _phase4c_dataset(synthetic_dataset)
    predictions = evaluate_phase4c(dataset, _opened_protocol())
    metrics = holdout_metrics(predictions)
    updates = horizon_updates(predictions)
    ensemble = ensemble_diagnostics(predictions)
    comparison = model_comparison(metrics)
    assert set(metrics['horizon']) == {'H1', 'H2', 'H3', 'POOLED_H1_H3'}
    assert len(metrics.loc[metrics['horizon'] == 'POOLED_H1_H3']) == 5
    assert metrics['matched_ar2_rmse'].notna().all()
    assert len(updates) == 5 * 2 * 4
    assert {'revision_H1_to_H2', 'revision_H2_to_H3'} <= set(updates.columns)
    assert len(ensemble) == 4 * 3 * 2
    assert (ensemble['ensemble_weight_ar2'] == 0.5).all()
    assert (ensemble['ensemble_weight_umidas_usd'] == 0.5).all()
    assert {'standard_rmse', 'conservative_rmse',
            'standard_relative_rmse_to_ar2'} <= set(comparison.columns)


def test_phase4c_rejects_unlocked_protocol(synthetic_dataset):
    dataset = _phase4c_dataset(synthetic_dataset)
    with pytest.raises(RuntimeError, match='locked opened protocol'):
        evaluate_phase4c(dataset, {'status': 'READY_TO_OPEN_HOLDOUT'})


def test_holdout_loader_records_first_load_before_target_read(
        tmp_path, monkeypatch, synthetic_dataset):
    from uznowcast.models import phase4c

    (tmp_path / 'results').mkdir()
    rules = {
        'holdout_quarters': list(EXPECTED_HOLDOUT),
        'primary_candidates': list(FROZEN_PRIMARY_CANDIDATES),
    }
    protocol = {
        'status': 'READY_TO_OPEN_HOLDOUT',
        'hash_checks_passed': True,
        'evaluation_rules': rules,
        'evaluation_rules_sha256': _rules_sha256(rules),
        'holdout_access_audit': {
            'first_load_started_at_utc': None,
            'first_load_completed_at_utc': None,
            'first_load_step': None,
            'loaded_quarters': [],
        },
    }
    (tmp_path / 'results/phase4c_evaluation_protocol.json').write_text(
        json.dumps(protocol), encoding='utf-8')
    (tmp_path / 'results/phase4b_candidate_freeze.json').write_text(
        '{}', encoding='utf-8')
    (tmp_path / 'results/frozen_validation_definition.json').write_text(
        '{}', encoding='utf-8')
    monkeypatch.setattr(
        phase4c, '_hash_checks',
        lambda root, phase4b, frozen: [{'passed': True}])
    dataset = _phase4c_dataset(synthetic_dataset)

    def audited_load(*args, **kwargs):
        saved = json.loads((
            tmp_path / 'results/phase4c_evaluation_protocol.json'
        ).read_text(encoding='utf-8'))
        assert saved['holdout_access_audit']['first_load_started_at_utc']
        assert saved['holdout_access_audit']['first_load_step']
        return dataset

    monkeypatch.setattr(phase4c, 'load_dataset', audited_load)
    _, loaded_protocol = load_phase4c_dataset(tmp_path)
    assert loaded_protocol['status'] == 'HOLDOUT_OPENED_PROTOCOL_LOCKED'
    assert loaded_protocol['holdout_access_audit'][
        'first_load_completed_at_utc'] is not None
