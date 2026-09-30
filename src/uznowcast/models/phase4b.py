"""Phase 4B candidate finalization on the unopened development sample.

The quarterly target is read with a Parquet predicate that selects only the
development-quarter labels recorded by Phase 4A.1.  Holdout labels are read
from the freeze metadata, but their GDP outcome column is never scanned.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from uznowcast.models import MODEL_LAYER_VERSION
from uznowcast.models.benchmarks import ar_forecast, historical_mean_forecast
from uznowcast.models.data import ModelingDataset
from uznowcast.models.dfm import DFMSpec, dfm_forecast
from uznowcast.models.ensemble import fixed_ar2_usd_ensemble
from uznowcast.models.metrics import summarize
from uznowcast.models.midas import MidasSpec, midas_forecast
from uznowcast.models.production import guard_master_dir, resolve_tiers
from uznowcast.models.splits import expanding_window
from uznowcast.provenance import atomic_parquet, save_json
from uznowcast.registry import load_registry


HORIZONS: tuple[str, ...] = ('H1', 'H2', 'H3')
LAG_MODES: tuple[str, ...] = ('standard', 'conservative')
EXPECTED_HOLDOUT: tuple[str, ...] = ('2025Q3', '2025Q4', '2026Q1', '2026Q2')
MIN_TRAIN_QUARTERS = 12
PRIMARY_MIN_MATCHED_FORECASTS = 12
DFM_EM_MAX_ITERATIONS = 100
DFM_EM_TOLERANCE = 1e-4
DFM_MIN_OBSERVED_MONTHS = 12
DFM_TOLERANCES_TESTED: tuple[float, ...] = (1e-4, 1e-5, 1e-6)


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _read_freeze_definition(root: Path) -> dict:
    path = root / 'results/frozen_validation_definition.json'
    payload = json.loads(path.read_text(encoding='utf-8'))
    holdout = tuple(map(str, payload.get('holdout_quarters', ())))
    if holdout != EXPECTED_HOLDOUT:
        raise ValueError(f'Unexpected frozen holdout: {holdout!r}')
    development = tuple(map(str, payload.get('development_quarters', ())))
    if not development or set(development) & set(holdout):
        raise ValueError('Frozen development/holdout definition is invalid')
    return payload


def _verify_frozen_hashes(root: Path, frozen: dict) -> None:
    fingerprint = frozen.get('master_fingerprint', {})
    for path_key, hash_key in (
            ('monthly_path', 'monthly_sha256'),
            ('registry_path', 'registry_sha256')):
        relative = fingerprint.get(path_key)
        expected = fingerprint.get(hash_key)
        if not relative or not expected:
            raise ValueError(f'Frozen fingerprint missing {path_key}/{hash_key}')
        path = root / Path(str(relative).replace('\\', '/'))
        observed = _file_sha256(path)
        if observed != expected:
            raise ValueError(
                f'Frozen input hash mismatch for {relative}: '
                f'expected {expected}, observed {observed}')
    # Carry the Phase 4A.1 quarterly hash forward without re-reading the full
    # file as opaque bytes. Phase 4B accesses that Parquet only through the
    # label-only scan and development-row predicate in _read_development_gdp.
    quarterly_relative = fingerprint.get('quarterly_path')
    quarterly_hash = fingerprint.get('quarterly_sha256')
    if not quarterly_relative or not quarterly_hash:
        raise ValueError('Frozen fingerprint missing quarterly path/hash')
    if not (root / Path(str(quarterly_relative).replace('\\', '/'))).exists():
        raise FileNotFoundError(quarterly_relative)


def _read_development_gdp(
        path: Path,
        *,
        development_quarters: Sequence[str],
        holdout_quarters: Sequence[str],
        target_field: str = 'gdp_real_yoy_pct',
        ) -> pd.DataFrame:
    """Read target outcomes only for development rows.

    The first read scans only quarter labels.  The second read requests the
    target column behind an explicit development-quarter predicate.  This
    order is a guardrail: candidate architecture is finalized without ever
    materializing a frozen-holdout GDP value.
    """
    labels = pd.read_parquet(path, columns=['quarter'])
    labels = labels['quarter'].astype(str).tolist()
    if tuple(labels[-len(holdout_quarters):]) != tuple(holdout_quarters):
        raise ValueError('GDP master tail does not match frozen holdout labels')
    requested = list(map(str, development_quarters))
    frame = pd.read_parquet(
        path,
        columns=['quarter', target_field],
        filters=[('quarter', 'in', requested)],
    )
    frame = frame[['quarter', target_field]].copy()
    frame['quarter'] = frame['quarter'].astype(str)
    if frame['quarter'].isin(holdout_quarters).any():
        raise AssertionError('Holdout GDP outcome entered the Phase 4B dataset')
    if set(frame['quarter']) != set(requested):
        missing = sorted(set(requested) - set(frame['quarter']))
        raise ValueError(f'Development GDP quarters missing after filtered read: {missing}')
    if frame['quarter'].duplicated().any():
        raise ValueError('Development GDP has duplicate quarters')
    order = {quarter: i for i, quarter in enumerate(requested)}
    return (frame.assign(_order=frame['quarter'].map(order))
            .sort_values('_order').drop(columns='_order').reset_index(drop=True))


def load_phase4b_development_dataset(
        root: Path,
        *,
        master_dir: str = 'data/master',
        registry_relative: str = 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx',
        ) -> tuple[ModelingDataset, dict]:
    """Load monthly predictors and development-only GDP for Phase 4B."""
    root = Path(root).resolve()
    guard_master_dir(master_dir)
    frozen = _read_freeze_definition(root)
    _verify_frozen_hashes(root, frozen)
    registry = load_registry(root / registry_relative)
    monthly = pd.read_parquet(root / master_dir / 'v1_monthly.parquet')
    monthly['date'] = pd.to_datetime(monthly['date'])
    monthly = monthly.sort_values('date').set_index('date')
    auxiliary = {column for column in monthly.columns
                 if column.endswith('_quality_flag') or column.endswith('_is_complete')}
    monthly = monthly.drop(columns=list(auxiliary))
    gdp = _read_development_gdp(
        root / master_dir / 'gdp_quarterly.parquet',
        development_quarters=frozen['development_quarters'],
        holdout_quarters=frozen['holdout_quarters'],
    )
    clean_field_by_key = {row['variable_key']: row['clean_model_field']
                          for row in registry.scope('v1')}
    monthly_key_by_field = {field: key for key, field in clean_field_by_key.items()}
    release_lag_days = {
        row['variable_key']: int(row['typical_publication_lag_days'])
        for row in registry.scope('v1')
        if row.get('typical_publication_lag_days') is not None
    }
    dataset = ModelingDataset(
        gdp=gdp,
        monthly=monthly,
        registry=registry,
        release_lag_days=release_lag_days,
        clean_field_by_key=clean_field_by_key,
        monthly_key_by_field=monthly_key_by_field,
    )
    resolve_tiers(dataset, strict=True)
    return dataset, frozen


def _benchmark_rows(dataset: ModelingDataset, splits, horizon: str,
                    lag_mode: str) -> list[dict]:
    gdp = dataset.gdp.set_index('quarter')[dataset.target_field]
    rows: list[dict] = []
    for split in splits:
        train = gdp.reindex(split.train).dropna()
        actual = float(gdp.loc[split.target])
        mean, _ = historical_mean_forecast(train)
        rows.append(dict(
            model='historical_mean', tier='none', horizon=horizon,
            lag_mode=lag_mode, target_quarter=split.target,
            n_train=len(train), prediction=mean, actual=actual,
            error=actual - mean, failure=None, candidate_role='benchmark',
        ))
        for order, name in ((1, 'ar1'), (2, 'ar2')):
            prediction, _ = ar_forecast(train, order)
            rows.append(dict(
                model=name, tier='none', horizon=horizon,
                lag_mode=lag_mode, target_quarter=split.target,
                n_train=len(train), prediction=prediction, actual=actual,
                error=actual - prediction, failure=None,
                candidate_role='primary',
            ))
    return rows


def _midas_rows(dataset: ModelingDataset, splits, horizon: str,
                lag_mode: str) -> list[dict]:
    specs = (
        (MidasSpec(
            name='umidas_usd_uzs_mom_dlog', field='usd_uzs_mom_dlog',
            monthly_lags=3, with_gdp_lag=True, polynomial_order=None,
        ), 'primary', 15),
        (MidasSpec(
            name='almon_usd_uzs_mom_dlog', field='usd_uzs_mom_dlog',
            monthly_lags=3, with_gdp_lag=True, polynomial_order=1,
        ), 'secondary_robustness', 12),
    )
    gdp = dataset.gdp.set_index('quarter')[dataset.target_field]
    rows: list[dict] = []
    for spec, role, minimum_rows in specs:
        for split in splits:
            prediction, diagnostics = midas_forecast(
                dataset, spec, split.train, split.target,
                horizon=horizon, mode=lag_mode,
            )
            n_train = diagnostics.get('n_train')
            failure = diagnostics.get('failure')
            raw_prediction = prediction
            if (not np.isnan(prediction)
                    and (n_train is None or int(n_train) < minimum_rows)):
                prediction = float('nan')
                failure = 'insufficient_effective_training'
            actual = float(gdp.loc[split.target])
            rows.append(dict(
                model=spec.name, tier='A', horizon=horizon,
                lag_mode=lag_mode, target_quarter=split.target,
                n_train=n_train, prediction=prediction, actual=actual,
                error=(actual - prediction if not np.isnan(prediction)
                       else float('nan')),
                failure=failure, candidate_role=role,
                raw_prediction=raw_prediction,
                min_effective_training_rows=minimum_rows,
            ))
    return rows


def _dfm_specs(dataset: ModelingDataset) -> tuple[DFMSpec, ...]:
    return tuple(
        DFMSpec(
            name=f'dfm_tier{tier}_k1',
            fields=tuple(dataset.predictor_fields(tier)),
            n_factors=1,
            with_gdp_lag=True,
            em_iterations=DFM_EM_MAX_ITERATIONS,
            em_tolerance=DFM_EM_TOLERANCE,
            min_observed_months=DFM_MIN_OBSERVED_MONTHS,
        )
        for tier in ('A', 'B', 'C')
    )


def _dfm_rows(dataset: ModelingDataset, splits, horizon: str, lag_mode: str,
              specs: Sequence[DFMSpec]) -> tuple[list[dict], list[dict],
                                                 list[dict], list[dict]]:
    gdp = dataset.gdp.set_index('quarter')[dataset.target_field]
    predictions: list[dict] = []
    fit_diagnostics: list[dict] = []
    field_resolutions: list[dict] = []
    loadings: list[dict] = []
    for spec in specs:
        tier = spec.name.removeprefix('dfm_tier').split('_', 1)[0]
        for split in splits:
            prediction, diagnostics = dfm_forecast(
                dataset, spec, split.train, split.target,
                horizon=horizon, mode=lag_mode,
            )
            n_train = diagnostics.get('n_train')
            failure = diagnostics.get('failure')
            raw_prediction = prediction
            if (not np.isnan(prediction)
                    and (n_train is None or int(n_train) < MIN_TRAIN_QUARTERS)):
                prediction = float('nan')
                failure = 'insufficient_effective_training'
            actual = float(gdp.loc[split.target])
            predictions.append(dict(
                model=spec.name, tier=tier, horizon=horizon,
                lag_mode=lag_mode, target_quarter=split.target,
                n_train=n_train, prediction=prediction, actual=actual,
                error=(actual - prediction if not np.isnan(prediction)
                       else float('nan')),
                failure=failure, candidate_role='diagnostic_dfm',
                raw_prediction=raw_prediction,
                min_effective_training_rows=MIN_TRAIN_QUARTERS,
            ))
            context = dict(
                model=spec.name, tier=tier, horizon=horizon,
                lag_mode=lag_mode, target_quarter=split.target,
            )
            panel = diagnostics.get('panel_diagnostics', {})
            em = diagnostics.get('em_diagnostics', {})
            fit_diagnostics.append(dict(
                **context,
                failure=failure,
                first_month=panel.get('first_month'),
                last_month=panel.get('last_month'),
                n_months=panel.get('n_months'),
                n_variables=panel.get('n_variables'),
                total_cells=panel.get('total_cells'),
                observed_cells=panel.get('observed_cells'),
                missing_cells=panel.get('missing_cells'),
                fraction_missing=panel.get('fraction_missing'),
                converged=em.get('converged', False),
                iteration_count=em.get('iteration_count'),
                max_iterations=em.get('max_iterations', spec.em_iterations),
                tolerance=em.get('tolerance', spec.em_tolerance),
                final_loss=em.get('final_loss'),
                relative_loss_change=em.get('relative_loss_change'),
                reconstruction_loss_path=json.dumps(
                    em.get('reconstruction_loss_path', [])),
                loading_stability_to_previous=np.nan,
            ))
            for resolution in diagnostics.get('field_resolutions', []):
                field_resolutions.append(dict(**context, **resolution))
            for field, values in diagnostics.get('loadings', {}).items():
                loadings.append(dict(
                    **context,
                    variable_key=dataset.monthly_key_by_field.get(field, field),
                    clean_field=field,
                    loading_factor_1=float(values[0]),
                ))
    return predictions, fit_diagnostics, field_resolutions, loadings


def _attach_loading_stability(diagnostics: pd.DataFrame,
                              loadings: pd.DataFrame) -> pd.DataFrame:
    if diagnostics.empty or loadings.empty:
        return diagnostics
    out = diagnostics.copy()
    keys = ['model', 'horizon', 'lag_mode']
    for group_keys, block in loadings.groupby(keys, dropna=False):
        previous: pd.Series | None = None
        for target in sorted(block['target_quarter'].unique()):
            current_rows = block.loc[block['target_quarter'] == target]
            current = current_rows.set_index('clean_field')['loading_factor_1']
            stability = float('nan')
            if previous is not None:
                common = current.index.intersection(previous.index)
                if len(common):
                    a = current.loc[common].to_numpy(dtype=float)
                    b = previous.loc[common].to_numpy(dtype=float)
                    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
                    if denominator:
                        stability = float(abs(np.dot(a, b) / denominator))
            mask = ((out['model'] == group_keys[0])
                    & (out['horizon'] == group_keys[1])
                    & (out['lag_mode'] == group_keys[2])
                    & (out['target_quarter'] == target))
            out.loc[mask, 'loading_stability_to_previous'] = stability
            previous = current
    return out


def dfm_tolerance_sensitivity(dataset: ModelingDataset, splits,
                              specs: Sequence[DFMSpec]) -> pd.DataFrame:
    """Test reasonable EM tolerances on representative development fits.

    The first, middle, and last expanding origins are crossed with all tiers,
    horizons, and lag modes.  The frozen 1e-5 setting is included alongside
    a looser and tighter tolerance; holdout quarters are absent by design.
    """
    if not splits:
        return pd.DataFrame()
    selected_indices = sorted({0, len(splits) // 2, len(splits) - 1})
    rows: list[dict] = []
    for tolerance in DFM_TOLERANCES_TESTED:
        for spec in specs:
            trial_spec = replace(spec, em_tolerance=tolerance)
            for index in selected_indices:
                split = splits[index]
                for horizon in HORIZONS:
                    for lag_mode in LAG_MODES:
                        prediction, diagnostics = dfm_forecast(
                            dataset, trial_spec, split.train, split.target,
                            horizon=horizon, mode=lag_mode,
                        )
                        em = diagnostics.get('em_diagnostics', {})
                        rows.append(dict(
                            model=spec.name,
                            target_quarter=split.target,
                            horizon=horizon,
                            lag_mode=lag_mode,
                            tolerance=tolerance,
                            max_iterations=spec.em_iterations,
                            converged=em.get('converged', False),
                            iteration_count=em.get('iteration_count'),
                            final_loss=em.get('final_loss'),
                            relative_loss_change=em.get('relative_loss_change'),
                            prediction=prediction,
                            failure=diagnostics.get('failure'),
                        ))
    return pd.DataFrame(rows)


def development_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    """Metrics with AR(1) and AR(2) recomputed on each exact sample."""
    rows: list[dict] = []
    for (model, horizon, lag_mode), group in predictions.groupby(
            ['model', 'horizon', 'lag_mode'], dropna=False):
        valid = group.loc[group['prediction'].notna() & group['actual'].notna()]
        stats = summarize(valid['error'].tolist())
        quarters = valid['target_quarter'].tolist()
        matched_stats = {}
        for benchmark in ('ar1', 'ar2'):
            bench = predictions.loc[
                (predictions['model'] == benchmark)
                & (predictions['horizon'] == horizon)
                & (predictions['lag_mode'] == lag_mode)
                & predictions['target_quarter'].isin(quarters)
                & predictions['prediction'].notna()
                & predictions['actual'].notna()
            ]
            matched_stats[benchmark] = summarize(bench['error'].tolist())
        ar1_rmse = matched_stats['ar1']['rmse']
        ar2_rmse = matched_stats['ar2']['rmse']
        role = str(group['candidate_role'].iloc[0])
        tier = str(group['tier'].iloc[0])
        rows.append(dict(
            model=model, candidate_role=role, tier=tier,
            horizon=horizon, lag_mode=lag_mode,
            N=stats['n_forecasts'], rmse=stats['rmse'], mae=stats['mae'],
            bias=stats['bias'],
            first_development_quarter=(min(quarters) if quarters else None),
            last_development_quarter=(max(quarters) if quarters else None),
            matched_ar1_rmse=ar1_rmse,
            matched_ar2_rmse=ar2_rmse,
            relative_rmse_to_ar1=(stats['rmse'] / ar1_rmse
                                  if ar1_rmse and not np.isnan(ar1_rmse)
                                  else np.nan),
            relative_rmse_to_ar2=(stats['rmse'] / ar2_rmse
                                  if ar2_rmse and not np.isnan(ar2_rmse)
                                  else np.nan),
        ))
    return pd.DataFrame(rows)


def horizon_updates(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for (model, lag_mode), block in predictions.groupby(['model', 'lag_mode']):
        pivot = block.pivot_table(index='target_quarter', columns='horizon',
                                  values='prediction', aggfunc='first')
        row = dict(model=model, lag_mode=lag_mode)
        for left, right in (('H1', 'H2'), ('H2', 'H3'), ('H1', 'H3')):
            if left not in pivot or right not in pivot:
                valid = pd.Series(False, index=pivot.index)
            else:
                valid = pivot[left].notna() & pivot[right].notna()
            delta = (pivot.loc[valid, right] - pivot.loc[valid, left]
                     if valid.any() else pd.Series(dtype=float))
            row[f'n_{left}_{right}'] = int(valid.sum())
            row[f'mean_abs_update_{left}_{right}'] = (
                float(delta.abs().mean()) if len(delta) else np.nan)
            row[f'share_changed_{left}_{right}'] = (
                float((delta != 0).mean()) if len(delta) else np.nan)
        rows.append(row)
    return pd.DataFrame(rows)


def ensemble_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    ensemble = predictions.loc[
        predictions['model'] == 'ensemble_ar2_umidas_usd'].copy()
    rows: list[pd.DataFrame] = []
    for (horizon, lag_mode), block in ensemble.groupby(['horizon', 'lag_mode']):
        valid = block.loc[block['prediction'].notna() & block['actual'].notna()].copy()
        if valid.empty:
            continue
        valid['ar2_component_error'] = (
            valid['actual'] - valid['ar2_component_prediction'])
        valid['umidas_usd_component_error'] = (
            valid['actual'] - valid['umidas_usd_component_prediction'])
        stats = summarize(valid['error'].tolist())
        correlation = valid['ar2_component_error'].corr(
            valid['umidas_usd_component_error'])
        valid['development_rmse'] = stats['rmse']
        valid['development_mae'] = stats['mae']
        valid['development_bias'] = stats['bias']
        valid['component_error_correlation'] = correlation
        rows.append(valid[[
            'horizon', 'lag_mode', 'target_quarter', 'actual',
            'ar2_component_prediction', 'umidas_usd_component_prediction',
            'prediction', 'ar2_component_error',
            'umidas_usd_component_error', 'error',
            'ensemble_weight_ar2', 'ensemble_weight_umidas_usd',
            'development_rmse', 'development_mae', 'development_bias',
            'component_error_correlation',
        ]])
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _dfm_candidate_decision(metrics: pd.DataFrame, diagnostics: pd.DataFrame,
                            updates: pd.DataFrame) -> dict:
    """Apply a frozen, conservative gate for adding at most one DFM."""
    assessments: list[dict] = []
    for model in ('dfm_tierA_k1', 'dfm_tierB_k1', 'dfm_tierC_k1'):
        metric_rows = metrics.loc[
            (metrics['model'] == model) & (metrics['horizon'] == 'H3')]
        fit_rows = diagnostics.loc[diagnostics['model'] == model]
        update_rows = updates.loc[updates['model'] == model]
        n_ok = (len(metric_rows) == len(LAG_MODES)
                and (metric_rows['N'] >= PRIMARY_MIN_MATCHED_FORECASTS).all())
        accuracy_ok = (n_ok
                       and (metric_rows['relative_rmse_to_ar2'] <= 1.05).all())
        convergence_rate = (float(fit_rows['converged'].mean())
                            if len(fit_rows) else 0.0)
        convergence_ok = convergence_rate >= 0.80
        stability = fit_rows['loading_stability_to_previous'].dropna()
        median_stability = float(stability.median()) if len(stability) else np.nan
        stability_ok = bool(len(stability) and median_stability >= 0.70)
        h3_updates = update_rows['mean_abs_update_H2_H3'].dropna()
        updating_ok = bool(len(h3_updates) and (h3_updates > 0).all())
        qualified = bool(n_ok and accuracy_ok and convergence_ok
                         and stability_ok and updating_ok)
        assessments.append(dict(
            model=model, qualified=qualified, n_ok=bool(n_ok),
            accuracy_ok=bool(accuracy_ok), convergence_ok=bool(convergence_ok),
            stability_ok=bool(stability_ok), updating_ok=bool(updating_ok),
            convergence_rate=convergence_rate,
            median_loading_stability=median_stability,
            worst_h3_relative_rmse_to_ar2=(
                float(metric_rows['relative_rmse_to_ar2'].max())
                if len(metric_rows) else np.nan),
        ))
    qualified = [row for row in assessments if row['qualified']]
    selected = (min(qualified, key=lambda row: row['worst_h3_relative_rmse_to_ar2'])
                ['model'] if qualified else None)
    return dict(
        selected_dfm=selected,
        gate=dict(
            minimum_matched_forecasts=PRIMARY_MIN_MATCHED_FORECASTS,
            maximum_h3_relative_rmse_to_ar2=1.05,
            minimum_convergence_rate=0.80,
            minimum_median_loading_stability=0.70,
            requires_nonzero_h2_to_h3_update=True,
        ),
        assessments=assessments,
    )


def run_phase4b(root: Path, *, master_dir: str = 'data/master',
                registry_relative: str
                = 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx') -> dict:
    dataset, frozen = load_phase4b_development_dataset(
        root, master_dir=master_dir, registry_relative=registry_relative)
    splits = expanding_window(dataset.gdp['quarter'].tolist(),
                              min_train=MIN_TRAIN_QUARTERS)
    predictions: list[dict] = []
    dfm_diagnostics: list[dict] = []
    field_resolutions: list[dict] = []
    loadings: list[dict] = []
    specs = _dfm_specs(dataset)
    for horizon in HORIZONS:
        for lag_mode in LAG_MODES:
            predictions.extend(_benchmark_rows(dataset, splits, horizon, lag_mode))
            predictions.extend(_midas_rows(dataset, splits, horizon, lag_mode))
            dfm_rows, diag_rows, resolution_rows, loading_rows = _dfm_rows(
                dataset, splits, horizon, lag_mode, specs)
            predictions.extend(dfm_rows)
            dfm_diagnostics.extend(diag_rows)
            field_resolutions.extend(resolution_rows)
            loadings.extend(loading_rows)
    predictions_frame = pd.DataFrame(predictions)
    ensemble = fixed_ar2_usd_ensemble(predictions_frame)
    predictions_frame = pd.concat([predictions_frame, ensemble], ignore_index=True)
    holdout = set(frozen['holdout_quarters'])
    if predictions_frame['target_quarter'].isin(holdout).any():
        raise AssertionError('Phase 4B emitted a frozen-holdout prediction')
    diagnostics_frame = _attach_loading_stability(
        pd.DataFrame(dfm_diagnostics), pd.DataFrame(loadings))
    tolerance_frame = dfm_tolerance_sensitivity(dataset, splits, specs)
    metrics = development_metrics(predictions_frame)
    updates = horizon_updates(predictions_frame)
    decision = _dfm_candidate_decision(metrics, diagnostics_frame, updates)
    return dict(
        frozen=frozen,
        dataset=dataset,
        specs=specs,
        predictions=predictions_frame,
        development_metrics=metrics,
        horizon_updates=updates,
        ensemble_diagnostics=ensemble_diagnostics(predictions_frame),
        dfm_diagnostics=diagnostics_frame,
        dfm_field_resolution=pd.DataFrame(field_resolutions),
        dfm_factor_loadings=pd.DataFrame(loadings),
        dfm_tolerance_sensitivity=tolerance_frame,
        dfm_decision=decision,
    )


def _candidate_freeze_payload(results: dict) -> dict:
    frozen = results['frozen']
    selected_dfm = results['dfm_decision']['selected_dfm']
    primary_models = ['ar1', 'ar2', 'umidas_usd_uzs_mom_dlog',
                      'ensemble_ar2_umidas_usd']
    if selected_dfm:
        primary_models.append(selected_dfm)
    dfm_specs = {spec.name: dict(
        predictor_fields=list(spec.fields), n_factors=spec.n_factors,
        with_gdp_lag=spec.with_gdp_lag,
        em_max_iterations=spec.em_iterations,
        em_tolerance=spec.em_tolerance,
        min_observed_months=spec.min_observed_months,
    ) for spec in results['specs']}
    return dict(
        phase='4B',
        status='CANDIDATE_ARCHITECTURE_FROZEN_BEFORE_HOLDOUT',
        holdout_outcomes_used=False,
        model_layer_version=MODEL_LAYER_VERSION,
        primary_candidate_models=primary_models,
        retained_benchmarks=['historical_mean', 'ar1', 'ar2'],
        secondary_robustness_models=['almon_usd_uzs_mom_dlog'],
        diagnostic_models=['dfm_tierA_k1', 'dfm_tierB_k1', 'dfm_tierC_k1'],
        specifications={
            'historical_mean': {
                'equation': 'mean(y_s for all development training quarters s < t)',
                'predictor_fields': [], 'lag_lengths': {},
            },
            'ar1': {
                'equation': 'y_t = alpha + beta_1*y_(t-1) + error_t',
                'predictor_fields': ['gdp_real_yoy_pct'],
                'lag_lengths': {'quarterly_gdp': 1},
            },
            'ar2': {
                'equation': ('y_t = alpha + beta_1*y_(t-1) '
                             '+ beta_2*y_(t-2) + error_t'),
                'predictor_fields': ['gdp_real_yoy_pct'],
                'lag_lengths': {'quarterly_gdp': 2},
            },
            'umidas_usd_uzs_mom_dlog': {
                'equation': ('y_t = alpha + beta*y_(t-1) + '
                             'sum_{l=0..2} gamma_l*x_(m(t,h)-l) + error_t'),
                'predictor_fields': ['usd_uzs_mom_dlog'],
                'lag_lengths': {'monthly': 3, 'quarterly_gdp': 1},
                'polynomial_order': None,
            },
            'almon_usd_uzs_mom_dlog': {
                'equation': 'U-MIDAS(3) with first-order Almon lag restriction',
                'predictor_fields': ['usd_uzs_mom_dlog'],
                'lag_lengths': {'monthly': 3, 'quarterly_gdp': 1},
                'polynomial_order': 1,
            },
            'ensemble_ar2_umidas_usd': {
                'equation': '0.5*AR2 prediction + 0.5*USD U-MIDAS(3) prediction',
                'components': ['ar2', 'umidas_usd_uzs_mom_dlog'],
                'ensemble_weights': {'ar2': 0.5, 'umidas_usd_uzs_mom_dlog': 0.5},
            },
            **dfm_specs,
        },
        dfm_decision=results['dfm_decision'],
        horizons=list(HORIZONS),
        release_lag_assumptions={
            'standard': 'end_of_reference_month + registry typical lag days',
            'conservative': ('end_of_reference_month + max(registry typical '
                             'lag days + 15, 3)'),
        },
        preprocessing_variant='variant_A_unmasked_verified_v1.2_master',
        dfm_convergence_settings={
            'max_iterations': DFM_EM_MAX_ITERATIONS,
            'tolerance': DFM_EM_TOLERANCE,
            'tolerances_tested_on_development': list(DFM_TOLERANCES_TESTED),
            'iteration_cap_is_convergence': False,
        },
        master_hashes={
            key: value for key, value in frozen['master_fingerprint'].items()
            if key.endswith('_sha256')
        },
        development_period_endpoint=frozen['development_quarters'][-1],
        development_quarters=list(frozen['development_quarters']),
        holdout_quarters=list(frozen['holdout_quarters']),
    )


def _write_table(frame: pd.DataFrame, parquet_path: Path) -> None:
    atomic_parquet(frame, parquet_path)
    frame.to_csv(parquet_path.with_suffix('.csv'), index=False)


def write_phase4b_results(root: Path, results: dict) -> dict:
    """Write diagnostics first and the candidate-freeze artifact last."""
    root = Path(root).resolve()
    output = root / 'results'
    output.mkdir(exist_ok=True)
    tables = {
        'phase4b_predictions.parquet': results['predictions'],
        'phase4b_development_metrics.parquet': results['development_metrics'],
        'phase4b_horizon_updates.parquet': results['horizon_updates'],
        'phase4b_ensemble_diagnostics.parquet': results['ensemble_diagnostics'],
        'phase4b_dfm_diagnostics.parquet': results['dfm_diagnostics'],
        'phase4b_dfm_field_resolution.parquet': results['dfm_field_resolution'],
        'phase4b_dfm_factor_loadings.parquet': results['dfm_factor_loadings'],
        'phase4b_dfm_tolerance_sensitivity.parquet': (
            results['dfm_tolerance_sensitivity']),
    }
    for name, frame in tables.items():
        _write_table(frame, output / name)
    save_json(output / 'phase4b_dfm_decision.json', results['dfm_decision'])
    # This must be the last model-selection write: once present, architecture
    # is frozen and subsequent work may only evaluate it on the holdout.
    freeze = _candidate_freeze_payload(results)
    save_json(output / 'phase4b_candidate_freeze.json', freeze)
    return {
        'candidate_freeze': str(output / 'phase4b_candidate_freeze.json'),
        'primary_candidates': freeze['primary_candidate_models'],
        'rows': {name: int(len(frame)) for name, frame in tables.items()},
    }
