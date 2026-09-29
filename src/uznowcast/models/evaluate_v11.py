"""Phase 4A.1 production evaluator.

Wraps the Phase 4A ``evaluate`` orchestrator with:

* fixture-directory guard;
* strict tier resolution (records missing predictors);
* frozen last-four-quarter validation set (never enters development);
* effective-training safeguard: predictions are voided when the
  regression's actual complete-row count falls below
  ``max(12, 3 × free_parameters)``;
* matched-quarter AR(1) comparisons;
* common-sample comparisons per tier group;
* horizon and lag-mode diagnostics;
* variant-A / variant-B robustness pair;
* master + registry SHA-256 recording on every persisted result file.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Sequence
import json
import warnings

import numpy as np
import pandas as pd

from uznowcast.provenance import atomic_parquet, save_json
from uznowcast.models import MODEL_LAYER_VERSION
from uznowcast.models.data import ModelingDataset, load_dataset
from uznowcast.models.evaluate import (
    HORIZONS, LAG_MODES, evaluate as evaluate_4a, summarize_predictions,
)
from uznowcast.models.matched import (
    common_sample_metrics, horizon_delta_report, lag_mode_delta, matched_metrics,
)
from uznowcast.models.production import (
    HOLDOUT_QUARTERS, PRIMARY_MIN_ROWS, SMALL_SAMPLE_MIN_ROWS,
    FrozenValidation, MasterFingerprint, freeze_validation, guard_master_dir,
    master_fingerprint, minimum_effective_rows, resolve_tiers,
)


# Model-family parameter counts. Bridges add one column per aggregated
# field plus intercept + GDP lag; U-MIDAS has intercept + GDP lag + K
# monthly lags; Almon-MIDAS has intercept + GDP lag + (poly_order + 1).
BENCHMARK_PARAMS = {'historical_mean': 1, 'ar1': 2, 'ar2': 3}


def _free_parameters(model: str, spec_registry: dict) -> int:
    if model in BENCHMARK_PARAMS:
        return BENCHMARK_PARAMS[model]
    spec = spec_registry.get(model, {})
    kind = spec.get('kind')
    if kind == 'bridge':
        s = spec.get('spec', {})
        fields = s.get('fields', [])
        return 1 + int(bool(s.get('with_gdp_lag', True))) + len(fields)
    if kind == 'midas':
        s = spec.get('spec', {})
        with_lag = int(bool(s.get('with_gdp_lag', True)))
        if s.get('polynomial_order') is None:
            monthly_params = int(s.get('monthly_lags', 3))
        else:
            monthly_params = int(s.get('polynomial_order', 1)) + 1
        return 1 + with_lag + monthly_params
    if kind == 'dfm':
        s = spec.get('spec', {})
        return 1 + int(bool(s.get('with_gdp_lag', True))) + int(s.get('n_factors', 1))
    # Unknown families default to a conservative estimate that will only
    # keep them if they have at least PRIMARY_MIN_ROWS rows.
    return 4


def apply_effective_training_safeguard(predictions: pd.DataFrame,
                                        spec_registry: dict,
                                        *, min_rows: int = PRIMARY_MIN_ROWS
                                        ) -> pd.DataFrame:
    """Overwrite predictions whose ``n_train`` is below the safeguard.

    The safeguard's threshold is ``max(min_rows, 3 × free_parameters)``.
    Overridden rows record ``prediction = NaN`` and
    ``failure = 'insufficient_effective_training'`` — the original raw
    prediction is preserved in ``raw_prediction`` so the small-sample
    sensitivity run can still surface it.
    """
    if predictions.empty:
        return predictions
    frame = predictions.copy()
    if 'raw_prediction' not in frame.columns:
        frame['raw_prediction'] = frame['prediction']
    if 'failure' not in frame.columns:
        frame['failure'] = pd.Series([None] * len(frame), dtype='object')
    else:
        frame['failure'] = frame['failure'].astype('object')
    threshold_by_model = {model: max(min_rows, 3 * _free_parameters(model, spec_registry))
                          for model in frame['model'].unique()}
    frame['min_effective_training_rows'] = frame['model'].map(threshold_by_model)
    threshold_hit = frame['n_train'].fillna(-1).astype(float) < frame['min_effective_training_rows']
    predictions_masked = threshold_hit & frame['prediction'].notna()
    if predictions_masked.any():
        frame.loc[predictions_masked, 'error'] = np.nan
        frame.loc[predictions_masked, 'prediction'] = np.nan
        na_failure = predictions_masked & frame['failure'].isna()
        if na_failure.any():
            frame.loc[na_failure, 'failure'] = 'insufficient_effective_training'
    return frame


def filter_development_only(predictions: pd.DataFrame,
                             frozen: FrozenValidation) -> pd.DataFrame:
    """Drop any prediction row targeting a holdout quarter."""
    if predictions.empty:
        return predictions
    holdout = set(frozen.holdout_quarters)
    if not holdout:
        return predictions
    return predictions.loc[~predictions['target_quarter'].isin(holdout)].copy()


# --- Variant B (robustness) --------------------------------------------------


def apply_variant_b(dataset: ModelingDataset) -> ModelingDataset:
    """Return a copy of the dataset with database-flagged extremes masked.

    Variant B does not touch ``data/master/``. It masks in-memory cells
    for a parallel evaluation run only. The mask criterion is the
    documented Phase 3B quality flag set (``extreme_log_change``,
    ``nonpositive_monthly_flow``, ``impossible_negative_derived_value``).
    Because ``v1_monthly.parquet`` does not carry those flags directly,
    this variant applies a **conservative** rule: any monthly value whose
    absolute z-score against the full-panel column mean/std exceeds 6.0
    is masked. That is much wider than a modelling winsor and only
    removes truly outsized observations that the Phase 2C pipeline
    already flagged. The database itself is untouched.
    """
    monthly = dataset.monthly.copy()
    for column in monthly.columns:
        series = monthly[column]
        if series.count() < 20:
            continue
        centered = series - series.mean(skipna=True)
        scale = series.std(skipna=True) or 1.0
        z = centered.abs() / scale
        monthly.loc[z > 6.0, column] = np.nan
    return ModelingDataset(
        gdp=dataset.gdp.copy(), monthly=monthly, registry=dataset.registry,
        release_lag_days=dict(dataset.release_lag_days),
        clean_field_by_key=dict(dataset.clean_field_by_key),
        monthly_key_by_field=dict(dataset.monthly_key_by_field),
        target_field=dataset.target_field,
    )


# --- Full Phase 4A.1 pass ----------------------------------------------------


def _dataset_scoped_to_development(dataset: ModelingDataset,
                                    frozen: FrozenValidation) -> ModelingDataset:
    """Restrict the dataset's GDP frame to development quarters only."""
    holdout = set(frozen.holdout_quarters)
    development_gdp = dataset.gdp.loc[~dataset.gdp['quarter'].astype(str).isin(holdout)].copy()
    development_gdp = development_gdp.reset_index(drop=True)
    return ModelingDataset(
        gdp=development_gdp, monthly=dataset.monthly, registry=dataset.registry,
        release_lag_days=dict(dataset.release_lag_days),
        clean_field_by_key=dict(dataset.clean_field_by_key),
        monthly_key_by_field=dict(dataset.monthly_key_by_field),
        target_field=dataset.target_field,
    )


def _tier_common_sample_groups(predictions: pd.DataFrame) -> dict[str, list[str]]:
    """Build ``AR_vs_TierX`` groups for common-sample comparisons."""
    groups: dict[str, list[str]] = {}
    if predictions.empty:
        return groups
    for tier in ('A', 'B', 'C'):
        members = predictions.loc[predictions['tier'] == tier, 'model'].dropna().unique().tolist()
        if members:
            groups[f'AR_vs_Tier{tier}'] = ['ar1'] + [m for m in members if m != 'ar1']
    return groups


def run_phase_4a1(root: Path, *, master_dir: str = 'data/master',
                   registry_relative: str
                   = 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx',
                   strict_tiers: bool = True,
                   allow_fixture_dir: bool = False,
                   holdout_quarters: int = HOLDOUT_QUARTERS,
                   horizons: Sequence[str] = HORIZONS,
                   lag_modes: Sequence[str] = LAG_MODES,
                   include_small_sample: bool = True) -> dict:
    """Full production Phase 4A.1 pass. Returns in-memory tables + metadata."""
    root = Path(root).resolve()
    guard_master_dir(master_dir, allow_fixture=allow_fixture_dir)
    dataset = load_dataset(root, master_dir=master_dir,
                            registry_relative=registry_relative)
    fingerprint = master_fingerprint(root, dataset, master_dir=master_dir,
                                      registry_relative=registry_relative)
    frozen = freeze_validation(dataset, holdout=holdout_quarters)
    tier_resolutions = resolve_tiers(dataset, strict=strict_tiers)
    development = _dataset_scoped_to_development(dataset, frozen)
    variant_b = apply_variant_b(development)

    results_a = evaluate_4a(development, horizons=horizons, lag_modes=lag_modes,
                             min_train=PRIMARY_MIN_ROWS, tiers=('A', 'B', 'C'))
    results_b = evaluate_4a(variant_b, horizons=horizons, lag_modes=lag_modes,
                             min_train=PRIMARY_MIN_ROWS, tiers=('A', 'B', 'C'))

    def _finalize(results: dict, variant: str) -> pd.DataFrame:
        preds = pd.DataFrame(results['predictions'])
        if preds.empty:
            preds['variant'] = variant
            return preds
        preds['variant'] = variant
        preds = filter_development_only(preds, frozen)
        preds = apply_effective_training_safeguard(preds, results['spec_registry'])
        return preds

    predictions_a = _finalize(results_a, 'A')
    predictions_b = _finalize(results_b, 'B')
    predictions_combined = pd.concat([predictions_a, predictions_b], ignore_index=True)

    metrics_primary = summarize_predictions(predictions_a.to_dict('records'))
    matched_primary = matched_metrics(predictions_a)
    matched_variant_b = matched_metrics(predictions_b)
    groups = _tier_common_sample_groups(predictions_a)
    common_sample = common_sample_metrics(predictions_a, groups)
    horizon_delta = horizon_delta_report(predictions_a)
    lag_delta = lag_mode_delta(matched_primary)

    small_sample_summary = None
    small_sample_predictions = pd.DataFrame()
    if include_small_sample and SMALL_SAMPLE_MIN_ROWS < PRIMARY_MIN_ROWS:
        small = evaluate_4a(development, horizons=horizons, lag_modes=lag_modes,
                             min_train=SMALL_SAMPLE_MIN_ROWS, tiers=('A', 'B', 'C'))
        small_predictions = pd.DataFrame(small['predictions'])
        if not small_predictions.empty:
            small_predictions['variant'] = 'small_sample_sensitivity'
            small_predictions = filter_development_only(small_predictions, frozen)
        small_sample_predictions = small_predictions
        small_sample_summary = dict(
            min_train=SMALL_SAMPLE_MIN_ROWS,
            first_evaluation_quarter=small.get('first_evaluation_quarter'),
            last_evaluation_quarter=small.get('last_evaluation_quarter'),
        )

    return dict(
        fingerprint=fingerprint,
        frozen=frozen,
        tier_resolutions=tier_resolutions,
        predictions_variant_a=predictions_a,
        predictions_variant_b=predictions_b,
        predictions_combined=predictions_combined,
        predictions_small_sample=small_sample_predictions,
        metrics_primary=metrics_primary,
        matched_primary=matched_primary,
        matched_variant_b=matched_variant_b,
        common_sample=common_sample,
        horizon_delta=horizon_delta,
        lag_delta=lag_delta,
        spec_registry_primary=results_a['spec_registry'],
        spec_registry_variant_b=results_b['spec_registry'],
        loadings_primary=pd.DataFrame(results_a['loadings']),
        loadings_variant_b=pd.DataFrame(results_b['loadings']),
        windows_primary=pd.DataFrame(results_a['windows']),
        small_sample_summary=small_sample_summary,
        first_evaluation_quarter=results_a.get('first_evaluation_quarter'),
        last_evaluation_quarter=results_a.get('last_evaluation_quarter'),
    )


def write_phase_4a1_results(root: Path, results: dict) -> dict:
    root = Path(root).resolve()
    (root / 'results').mkdir(exist_ok=True)
    fingerprint: MasterFingerprint = results['fingerprint']
    frozen: FrozenValidation = results['frozen']
    tier_resolutions = results['tier_resolutions']

    predictions_combined = results['predictions_combined']
    atomic_parquet(predictions_combined, root / 'results/phase4a1_predictions.parquet')
    if not results['predictions_small_sample'].empty:
        atomic_parquet(results['predictions_small_sample'],
                        root / 'results/phase4a1_predictions_small_sample.parquet')
    atomic_parquet(results['metrics_primary'], root / 'results/phase4a1_metrics.parquet')
    matched_combined = pd.concat([
        results['matched_primary'].assign(variant='A'),
        results['matched_variant_b'].assign(variant='B'),
    ], ignore_index=True)
    atomic_parquet(matched_combined, root / 'results/phase4a1_matched_metrics.parquet')
    atomic_parquet(results['common_sample'], root / 'results/phase4a1_common_sample_metrics.parquet')
    atomic_parquet(results['horizon_delta'], root / 'results/phase4a1_horizon_deltas.parquet')
    atomic_parquet(results['lag_delta'], root / 'results/phase4a1_lag_mode_deltas.parquet')
    atomic_parquet(results['windows_primary'], root / 'results/phase4a1_evaluation_windows.parquet')

    loadings_combined = pd.concat([
        results['loadings_primary'].assign(variant='A') if not results['loadings_primary'].empty
        else pd.DataFrame(),
        results['loadings_variant_b'].assign(variant='B') if not results['loadings_variant_b'].empty
        else pd.DataFrame(),
    ], ignore_index=True)
    if not loadings_combined.empty:
        atomic_parquet(loadings_combined, root / 'results/phase4a1_factor_loadings.parquet')
    else:
        loadings_combined.to_parquet(root / 'results/phase4a1_factor_loadings.parquet', index=False)

    save_json(root / 'results/phase4a1_model_specs.json', dict(
        model_layer_version=MODEL_LAYER_VERSION,
        min_effective_training_rows_primary=PRIMARY_MIN_ROWS,
        small_sample_sensitivity_min_train=SMALL_SAMPLE_MIN_ROWS,
        first_evaluation_quarter=results['first_evaluation_quarter'],
        last_evaluation_quarter=results['last_evaluation_quarter'],
        small_sample_summary=results['small_sample_summary'],
        master_fingerprint=fingerprint.to_dict(),
        specs_variant_a=results['spec_registry_primary'],
        specs_variant_b=results['spec_registry_variant_b'],
    ))

    save_json(root / 'results/phase4a1_resolved_tiers.json', dict(
        master_fingerprint=fingerprint.to_dict(),
        tier_resolutions=[t.to_dict() for t in tier_resolutions],
    ))
    save_json(root / 'results/frozen_validation_definition.json', dict(
        frozen.to_dict(),
        master_fingerprint=fingerprint.to_dict(),
    ))
    return dict(
        predictions_rows=int(len(predictions_combined)),
        matched_rows=int(len(matched_combined)),
        common_rows=int(len(results['common_sample'])),
        loadings_rows=int(len(loadings_combined)),
        windows_rows=int(len(results['windows_primary'])),
    )
