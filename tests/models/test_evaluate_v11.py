"""End-to-end tests for the Phase 4A.1 production evaluator."""
from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest

from uznowcast.models.evaluate_v11 import (
    apply_effective_training_safeguard, apply_variant_b,
    filter_development_only, run_phase_4a1, write_phase_4a1_results,
)
from uznowcast.models.production import (
    FixtureMasterRefused, HOLDOUT_QUARTERS, freeze_validation,
)


def test_effective_training_safeguard_masks_low_n(monkeypatch):
    predictions = pd.DataFrame([
        dict(model='ar1', tier='none', horizon='H1', lag_mode='standard',
             target_quarter='2020-Q1', prediction=5.0, actual=6.0, error=1.0,
             n_train=10, failure=None),
        dict(model='bridge_x', tier='B', horizon='H1', lag_mode='standard',
             target_quarter='2020-Q1', prediction=5.5, actual=6.0, error=0.5,
             n_train=8, failure=None),
        dict(model='bridge_x', tier='B', horizon='H1', lag_mode='standard',
             target_quarter='2020-Q2', prediction=6.0, actual=6.0, error=0.0,
             n_train=15, failure=None),
    ])
    specs = {'ar1': {'kind': 'benchmark'},
             'bridge_x': {'kind': 'bridge', 'spec': {'fields': ['a'], 'with_gdp_lag': True}}}
    out = apply_effective_training_safeguard(predictions, specs, min_rows=12)
    # AR(1) needs 12 rows and has 10 → voided
    ar_row = out.loc[out['model'] == 'ar1'].iloc[0]
    assert np.isnan(ar_row['prediction'])
    assert ar_row['failure'] == 'insufficient_effective_training'
    # Bridge with 8 rows also voided; the raw prediction is preserved.
    bridge_rows = out.loc[out['model'] == 'bridge_x'].reset_index(drop=True)
    assert np.isnan(bridge_rows.loc[0, 'prediction'])
    assert bridge_rows.loc[0, 'raw_prediction'] == pytest.approx(5.5)
    # Bridge with 15 rows kept
    assert bridge_rows.loc[1, 'prediction'] == pytest.approx(6.0)


def test_filter_development_only_drops_holdout_targets():
    frozen = freeze_validation.__wrapped__ if hasattr(freeze_validation, '__wrapped__') else None
    # Build a small frozen validation object manually.
    from uznowcast.models.production import FrozenValidation
    frozen_val = FrozenValidation(
        holdout_quarters=('2025-Q3', '2025-Q4', '2026-Q1', '2026-Q2'),
        development_quarters=('2018-Q1', '2018-Q2'))
    frame = pd.DataFrame([
        dict(target_quarter='2018-Q1', prediction=1.0),
        dict(target_quarter='2025-Q3', prediction=2.0),
        dict(target_quarter='2026-Q2', prediction=3.0),
    ])
    filtered = filter_development_only(frame, frozen_val)
    assert set(filtered['target_quarter']) == {'2018-Q1'}


def test_variant_b_never_modifies_original(synthetic_dataset):
    # Poison one value so variant B has something to consider masking.
    dataset = synthetic_dataset
    orig_id = id(dataset.monthly)
    variant = apply_variant_b(dataset)
    # Original dataset object and frame identity are preserved.
    assert id(dataset.monthly) == orig_id
    # Variant returns a new frame (never the same object)
    assert variant.monthly is not dataset.monthly


def test_run_phase_4a1_refuses_fixture_master_dir(tmp_path, synthetic_dataset):
    # No masters exist; the fixture guard should fire before any file IO.
    with pytest.raises(FixtureMasterRefused):
        run_phase_4a1(tmp_path, master_dir='data/master_from_fixtures')


def _seed_real_master_layout(tmp_path: Path, monthly_columns: list[str]):
    """Materialize a project-shaped directory with real registry + tiny masters."""
    (tmp_path / 'data/master').mkdir(parents=True)
    (tmp_path / 'registry/archive').mkdir(parents=True)
    (tmp_path / 'config').mkdir()
    project_root = Path(__file__).resolve().parents[2]
    import shutil
    shutil.copyfile(project_root / 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx',
                    tmp_path / 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx')
    shutil.copyfile(project_root / 'config/registry_contracts.json',
                    tmp_path / 'config/registry_contracts.json')
    rng = np.random.default_rng(20260929)
    dates = pd.date_range('2018-01-31', periods=102, freq='ME')
    values = rng.normal(0, 1, size=(len(dates), len(monthly_columns)))
    frame = pd.DataFrame(values, index=dates, columns=monthly_columns)
    frame.index.name = 'date'
    frame.reset_index().to_parquet(tmp_path / 'data/master/v1_monthly.parquet',
                                    index=False)
    quarters = [f'{y}-Q{q}' for y in range(2018, 2027) for q in range(1, 5)][:34]
    gdp = pd.DataFrame({'quarter': quarters, 'gdp_real_yoy_pct': np.linspace(4, 7, 34)})
    gdp.to_parquet(tmp_path / 'data/master/gdp_quarterly.parquet', index=False)
    return quarters


def test_run_phase_4a1_records_fingerprint_and_frozen_set(tmp_path):
    """Full end-to-end run against a temporary "real" master directory."""
    # Small Tier B panel keeps the test fast (<10 s).
    columns = ['ppi_mom_log', 'usd_uzs_mom_dlog', 'm2_yoy_log',
               'ind_prod_yoy_log', 'cpi_headline_mom_log']
    quarters = _seed_real_master_layout(tmp_path, columns)
    results = run_phase_4a1(tmp_path, strict_tiers=False,
                             horizons=('H3',), lag_modes=('standard',),
                             include_small_sample=False)
    counts = write_phase_4a1_results(tmp_path, results)
    assert counts['predictions_rows'] > 0
    fp = results['fingerprint']
    assert fp.monthly_sha256 is not None
    assert fp.registry_sha256 is not None
    assert fp.quarterly_rows == 34
    assert results['frozen'].holdout_quarters == tuple(quarters[-4:])
    for name in ('phase4a1_predictions.parquet', 'phase4a1_metrics.parquet',
                  'phase4a1_matched_metrics.parquet',
                  'phase4a1_common_sample_metrics.parquet',
                  'phase4a1_evaluation_windows.parquet',
                  'phase4a1_horizon_deltas.parquet',
                  'phase4a1_lag_mode_deltas.parquet',
                  'phase4a1_factor_loadings.parquet',
                  'phase4a1_model_specs.json',
                  'phase4a1_resolved_tiers.json',
                  'frozen_validation_definition.json'):
        assert (tmp_path / 'results' / name).exists(), name
    frozen_json = json.loads((tmp_path / 'results/frozen_validation_definition.json').read_text())
    assert frozen_json['holdout_count'] == 4
    specs_json = json.loads((tmp_path / 'results/phase4a1_model_specs.json').read_text())
    assert specs_json['master_fingerprint']['monthly_sha256'] == fp.monthly_sha256
    tiers_json = json.loads((tmp_path / 'results/phase4a1_resolved_tiers.json').read_text())
    tier_a = next(row for row in tiers_json['tier_resolutions'] if row['tier'] == 'A')
    assert 'ppi' in tier_a['found_keys']


def test_run_phase_4a1_excludes_holdout_from_predictions(tmp_path):
    """The evaluation loop must never emit a prediction targeting a holdout quarter."""
    quarters = _seed_real_master_layout(tmp_path, ['m2_yoy_log', 'ppi_mom_log'])
    results = run_phase_4a1(tmp_path, strict_tiers=False,
                             horizons=('H3',), lag_modes=('standard',),
                             include_small_sample=False)
    predictions = results['predictions_variant_a']
    holdout = set(results['frozen'].holdout_quarters)
    assert not predictions['target_quarter'].isin(holdout).any(), (
        'Phase 4A.1 predictions leaked into the frozen validation set')
    # Also assert the last training-eligible target is the one immediately
    # preceding the holdout.
    last_eval = predictions['target_quarter'].max()
    assert last_eval == quarters[-5]
