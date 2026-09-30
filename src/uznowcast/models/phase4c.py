"""Phase 4C evaluation of the frozen four-quarter GDP holdout.

The protocol and hash checks are persisted before this module permits a GDP
target-column read.  Model architecture is imported from the Phase 4B freeze;
Phase 4C contains no tuning or model-selection path.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from uznowcast.models.benchmarks import ar_forecast, historical_mean_forecast
from uznowcast.models.data import ModelingDataset, horizon_month_end, load_dataset
from uznowcast.models.ensemble import fixed_ar2_usd_ensemble
from uznowcast.models.metrics import summarize
from uznowcast.models.midas import MidasSpec, midas_forecast
from uznowcast.provenance import atomic_parquet, save_json


PHASE4C_EVALUATOR_VERSION = '4c.0'
PROTOCOL_PATH = 'results/phase4c_evaluation_protocol.json'
PHASE4B_FREEZE_PATH = 'results/phase4b_candidate_freeze.json'
FROZEN_VALIDATION_PATH = 'results/frozen_validation_definition.json'
EXPECTED_HOLDOUT: tuple[str, ...] = ('2025Q3', '2025Q4', '2026Q1', '2026Q2')
FROZEN_PRIMARY_CANDIDATES: tuple[str, ...] = (
    'ar1', 'ar2', 'umidas_usd_uzs_mom_dlog',
    'ensemble_ar2_umidas_usd',
)
HORIZONS: tuple[str, ...] = ('H1', 'H2', 'H3')
LAG_MODES: tuple[str, ...] = ('standard', 'conservative')
PRIMARY_LAG_MODE = 'standard'
ROBUSTNESS_LAG_MODE = 'conservative'
PRIMARY_METRIC = 'rmse'
SECONDARY_METRICS: tuple[str, ...] = ('mae', 'bias')


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _rules_sha256(rules: dict) -> str:
    canonical = json.dumps(rules, sort_keys=True, separators=(',', ':'))
    return sha256(canonical.encode('utf-8')).hexdigest()


def _validate_freeze_contract(phase4b: dict, frozen: dict) -> None:
    if phase4b.get('status') != 'CANDIDATE_ARCHITECTURE_FROZEN_BEFORE_HOLDOUT':
        raise ValueError('Phase 4B candidate freeze is not in frozen status')
    if phase4b.get('holdout_outcomes_used') is not False:
        raise ValueError('Phase 4B freeze does not certify unopened outcomes')
    if tuple(phase4b.get('primary_candidate_models', ())) != FROZEN_PRIMARY_CANDIDATES:
        raise ValueError('Phase 4B primary candidate set differs from Phase 4C protocol')
    if tuple(phase4b.get('holdout_quarters', ())) != EXPECTED_HOLDOUT:
        raise ValueError('Phase 4B holdout labels differ from Phase 4C protocol')
    if tuple(frozen.get('holdout_quarters', ())) != EXPECTED_HOLDOUT:
        raise ValueError('Frozen validation labels differ from Phase 4C protocol')
    specs = phase4b.get('specifications', {})
    usd = specs.get('umidas_usd_uzs_mom_dlog', {})
    if usd.get('predictor_fields') != ['usd_uzs_mom_dlog']:
        raise ValueError('Frozen USD U-MIDAS predictor changed')
    if usd.get('lag_lengths') != {'monthly': 3, 'quarterly_gdp': 1}:
        raise ValueError('Frozen USD U-MIDAS lag lengths changed')
    ensemble = specs.get('ensemble_ar2_umidas_usd', {})
    if ensemble.get('ensemble_weights') != {
            'ar2': 0.5, 'umidas_usd_uzs_mom_dlog': 0.5}:
        raise ValueError('Frozen ensemble weights changed')
    if phase4b.get('preprocessing_variant') != 'variant_A_unmasked_verified_v1.2_master':
        raise ValueError('Frozen preprocessing variant changed')
    if phase4b.get('dfm_decision', {}).get('selected_dfm') is not None:
        raise ValueError('Phase 4B unexpectedly selected a DFM')


def _hash_checks(root: Path, phase4b: dict, frozen: dict) -> list[dict]:
    files = (
        ('v1_monthly.parquet', root / 'data/master/v1_monthly.parquet',
         'monthly_sha256'),
        ('gdp_quarterly.parquet', root / 'data/master/gdp_quarterly.parquet',
         'quarterly_sha256'),
        ('uzbekistan_nowcasting_v1.2_registry.xlsx',
         root / 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx',
         'registry_sha256'),
    )
    phase4b_hashes = phase4b.get('master_hashes', {})
    frozen_hashes = frozen.get('master_fingerprint', {})
    checks: list[dict] = []
    for name, path, key in files:
        expected_phase4b = phase4b_hashes.get(key)
        expected_frozen = frozen_hashes.get(key)
        observed = _sha256_file(path)
        passed = bool(expected_phase4b and expected_frozen
                      and expected_phase4b == expected_frozen == observed)
        checks.append(dict(
            file=name,
            path=str(path.relative_to(root)).replace('\\', '/'),
            expected_phase4b_sha256=expected_phase4b,
            expected_frozen_validation_sha256=expected_frozen,
            observed_sha256=observed,
            passed=passed,
        ))
    return checks


def prepare_phase4c_protocol(root: Path, *, overwrite: bool = False) -> dict:
    """Write the immutable evaluation rules before any holdout outcome read."""
    root = Path(root).resolve()
    protocol_path = root / PROTOCOL_PATH
    if protocol_path.exists() and not overwrite:
        existing = _read_json(protocol_path)
        if existing.get('holdout_access_audit', {}).get(
                'first_load_started_at_utc') is not None:
            raise RuntimeError('Phase 4C holdout was already opened; protocol cannot be reset')
        raise FileExistsError(f'Phase 4C protocol already exists: {protocol_path}')
    phase4b_path = root / PHASE4B_FREEZE_PATH
    frozen_path = root / FROZEN_VALIDATION_PATH
    phase4b = _read_json(phase4b_path)
    frozen = _read_json(frozen_path)
    _validate_freeze_contract(phase4b, frozen)
    checked_at = _utc_now()
    checks = _hash_checks(root, phase4b, frozen)
    all_passed = all(check['passed'] for check in checks)
    rules = dict(
        holdout_quarters=list(EXPECTED_HOLDOUT),
        primary_candidates=list(FROZEN_PRIMARY_CANDIDATES),
        retained_benchmarks=['historical_mean', 'ar1', 'ar2'],
        main_accuracy_benchmark='ar2',
        horizons=list(HORIZONS),
        primary_release_lag_assumption=PRIMARY_LAG_MODE,
        robustness_release_lag_assumption=ROBUSTNESS_LAG_MODE,
        primary_metric=PRIMARY_METRIC,
        secondary_metrics=list(SECONDARY_METRICS),
        comparison_sample_rule='matched observations only',
        estimation_rule=(
            'expanding window; target quarter and all later GDP outcomes are '
            'excluded; prior holdout outcomes enter only subsequent origins'),
        information_rule=(
            'use only monthly observations visible under the frozen Phase 4B '
            'standard/conservative release-lag assumptions'),
        required_reports=[
            'quarter-level actuals forecasts and errors',
            'horizon-specific RMSE MAE and bias',
            'pooled H1-H3 standard-lag RMSE',
            'relative RMSE versus matched AR(2)',
            'standard versus conservative sensitivity',
            'H1-to-H2 and H2-to-H3 forecast revisions',
            'ensemble component forecasts and errors',
        ],
        architecture_mutation_after_holdout='forbidden',
        dfm_policy='Phase 4B approximate DFMs remain diagnostic only; no Kalman DFM',
        frozen_specifications={
            model: phase4b['specifications'][model]
            for model in ('historical_mean',) + FROZEN_PRIMARY_CANDIDATES
        },
        preprocessing_variant=phase4b['preprocessing_variant'],
        release_lag_assumptions=phase4b['release_lag_assumptions'],
    )
    protocol = dict(
        phase='4C',
        evaluator_version=PHASE4C_EVALUATOR_VERSION,
        status=('READY_TO_OPEN_HOLDOUT' if all_passed
                else 'BLOCKED_HASH_MISMATCH'),
        protocol_written_at_utc=checked_at,
        evaluation_rules=rules,
        evaluation_rules_sha256=_rules_sha256(rules),
        source_artifacts={
            'phase4b_candidate_freeze': PHASE4B_FREEZE_PATH,
            'phase4b_candidate_freeze_sha256': _sha256_file(phase4b_path),
            'frozen_validation_definition': FROZEN_VALIDATION_PATH,
            'frozen_validation_definition_sha256': _sha256_file(frozen_path),
        },
        hash_checks_completed_at_utc=checked_at,
        hash_checks_passed=all_passed,
        hash_checks=checks,
        holdout_access_audit={
            'authorized_after_protocol_and_hash_checks': all_passed,
            'first_load_step': None,
            'first_load_started_at_utc': None,
            'first_load_completed_at_utc': None,
            'loaded_quarters': [],
            'post_load_rule_mutations': [],
        },
    )
    protocol_path.parent.mkdir(exist_ok=True)
    save_json(protocol_path, protocol)
    if not all_passed:
        raise RuntimeError('Phase 4C blocked: one or more frozen input hashes differ')
    return protocol


def _validate_ready_protocol(root: Path) -> dict:
    protocol_path = root / PROTOCOL_PATH
    protocol = _read_json(protocol_path)
    if protocol.get('status') != 'READY_TO_OPEN_HOLDOUT':
        raise RuntimeError('Phase 4C protocol is not ready to open the holdout')
    if protocol.get('hash_checks_passed') is not True:
        raise RuntimeError('Phase 4C hash checks did not pass')
    rules = protocol.get('evaluation_rules', {})
    if _rules_sha256(rules) != protocol.get('evaluation_rules_sha256'):
        raise RuntimeError('Phase 4C evaluation rules changed after protocol write')
    if tuple(rules.get('primary_candidates', ())) != FROZEN_PRIMARY_CANDIDATES:
        raise RuntimeError('Phase 4C candidate set changed after protocol write')
    if tuple(rules.get('holdout_quarters', ())) != EXPECTED_HOLDOUT:
        raise RuntimeError('Phase 4C holdout labels changed after protocol write')
    return protocol


def load_phase4c_dataset(root: Path, *, master_dir: str = 'data/master',
                         registry_relative: str
                         = 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx'
                         ) -> tuple[ModelingDataset, dict]:
    """Open frozen GDP outcomes only after protocol and hash revalidation."""
    root = Path(root).resolve()
    protocol = _validate_ready_protocol(root)
    if protocol['holdout_access_audit']['first_load_started_at_utc'] is not None:
        raise RuntimeError('Phase 4C holdout outcomes have already been opened')
    phase4b = _read_json(root / PHASE4B_FREEZE_PATH)
    frozen = _read_json(root / FROZEN_VALIDATION_PATH)
    rechecks = _hash_checks(root, phase4b, frozen)
    if not all(check['passed'] for check in rechecks):
        raise RuntimeError('Phase 4C pre-open hash revalidation failed')

    # Persist authorization and the exact first-load step immediately before
    # the call that materializes the quarterly target column.
    started = _utc_now()
    protocol['holdout_access_audit'].update(
        first_load_step='load_phase4c_dataset:load_dataset quarterly target read',
        first_load_started_at_utc=started,
        pre_open_hash_revalidation=rechecks,
    )
    save_json(root / PROTOCOL_PATH, protocol)
    dataset = load_dataset(
        root, master_dir=master_dir, registry_relative=registry_relative)
    completed = _utc_now()
    holdout_rows = dataset.gdp.loc[
        dataset.gdp['quarter'].astype(str).isin(EXPECTED_HOLDOUT)]
    if tuple(holdout_rows['quarter'].astype(str)) != EXPECTED_HOLDOUT:
        raise ValueError('Loaded GDP master does not contain the exact frozen holdout')
    if holdout_rows[dataset.target_field].isna().any():
        raise ValueError('One or more frozen holdout GDP outcomes are missing')
    protocol['status'] = 'HOLDOUT_OPENED_PROTOCOL_LOCKED'
    protocol['holdout_access_audit'].update(
        first_load_completed_at_utc=completed,
        loaded_quarters=list(EXPECTED_HOLDOUT),
    )
    save_json(root / PROTOCOL_PATH, protocol)
    return dataset, protocol


def _forecast_rows(dataset: ModelingDataset, target_quarter: str,
                   train_quarters: Sequence[str], horizon: str,
                   lag_mode: str) -> list[dict]:
    gdp = dataset.gdp.set_index('quarter')[dataset.target_field]
    actual = float(gdp.loc[target_quarter])
    train = gdp.reindex(train_quarters).dropna()
    origin = str(horizon_month_end(target_quarter, horizon).date())
    common = dict(
        horizon=horizon,
        lag_mode=lag_mode,
        target_quarter=target_quarter,
        actual=actual,
        forecast_origin_date=origin,
        training_first_quarter=str(train_quarters[0]),
        training_last_quarter=str(train_quarters[-1]),
        architecture_frozen=True,
    )
    rows: list[dict] = []
    mean_prediction, _ = historical_mean_forecast(train)
    rows.append(dict(
        **common, model='historical_mean', candidate_role='benchmark',
        tier='none', n_train=len(train), prediction=mean_prediction,
        error=actual - mean_prediction, failure=None,
    ))
    for order, name in ((1, 'ar1'), (2, 'ar2')):
        prediction, _ = ar_forecast(train, order)
        rows.append(dict(
            **common, model=name, candidate_role='primary', tier='none',
            n_train=len(train), prediction=prediction,
            error=actual - prediction, failure=None,
        ))
    spec = MidasSpec(
        name='umidas_usd_uzs_mom_dlog', field='usd_uzs_mom_dlog',
        monthly_lags=3, with_gdp_lag=True, polynomial_order=None)
    prediction, diagnostics = midas_forecast(
        dataset, spec, train_quarters, target_quarter,
        horizon=horizon, mode=lag_mode)
    n_train = diagnostics.get('n_train')
    failure = diagnostics.get('failure')
    if not np.isnan(prediction) and (n_train is None or int(n_train) < 15):
        prediction = float('nan')
        failure = 'insufficient_effective_training'
    rows.append(dict(
        **common, model=spec.name, candidate_role='primary', tier='A',
        n_train=n_train, prediction=prediction,
        error=(actual - prediction if not np.isnan(prediction) else np.nan),
        failure=failure,
    ))
    return rows


def evaluate_phase4c(dataset: ModelingDataset, protocol: dict) -> pd.DataFrame:
    """Generate frozen holdout predictions with sequential expanding windows."""
    if protocol.get('status') != 'HOLDOUT_OPENED_PROTOCOL_LOCKED':
        raise RuntimeError('Holdout evaluation requires a locked opened protocol')
    quarters = dataset.gdp['quarter'].astype(str).tolist()
    rows: list[dict] = []
    for target in EXPECTED_HOLDOUT:
        target_index = quarters.index(target)
        train_quarters = tuple(quarters[:target_index])
        if target in train_quarters or set(quarters[target_index:]) & set(train_quarters):
            raise AssertionError('Holdout target leakage into expanding training window')
        for horizon in HORIZONS:
            for lag_mode in LAG_MODES:
                rows.extend(_forecast_rows(
                    dataset, target, train_quarters, horizon, lag_mode))
    base = pd.DataFrame(rows)
    ensemble = fixed_ar2_usd_ensemble(base)
    context = base[[
        'target_quarter', 'horizon', 'lag_mode', 'forecast_origin_date',
        'training_first_quarter', 'training_last_quarter',
        'architecture_frozen',
    ]].drop_duplicates()
    ensemble = ensemble.merge(
        context, on=['target_quarter', 'horizon', 'lag_mode'],
        how='left', validate='one_to_one')
    predictions = pd.concat([base, ensemble], ignore_index=True, sort=False)
    if set(predictions['model']) != {'historical_mean', *FROZEN_PRIMARY_CANDIDATES}:
        raise AssertionError('Phase 4C predictions contain a non-frozen model')
    return predictions.sort_values(
        ['target_quarter', 'horizon', 'lag_mode', 'model']).reset_index(drop=True)


def holdout_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    """Horizon metrics and standard-lag pooled H1-H3 metrics."""
    rows: list[dict] = []

    def add_row(model: str, role: str, horizon: str, lag_mode: str,
                valid: pd.DataFrame, benchmark: pd.DataFrame) -> None:
        stats = summarize(valid['error'].tolist())
        bench_stats = summarize(benchmark['error'].tolist())
        rows.append(dict(
            model=model, candidate_role=role, horizon=horizon,
            lag_mode=lag_mode, N=stats['n_forecasts'],
            rmse=stats['rmse'], mae=stats['mae'], bias=stats['bias'],
            matched_ar2_rmse=bench_stats['rmse'],
            matched_ar2_mae=bench_stats['mae'],
            matched_ar2_bias=bench_stats['bias'],
            relative_rmse_to_ar2=(stats['rmse'] / bench_stats['rmse']
                                  if bench_stats['rmse'] else np.nan),
            comparison_quarters='|'.join(valid['target_quarter'].astype(str)),
        ))

    for (model, horizon, lag_mode), group in predictions.groupby(
            ['model', 'horizon', 'lag_mode'], dropna=False):
        valid = group.loc[group['prediction'].notna() & group['actual'].notna()]
        keys = valid[['target_quarter', 'horizon', 'lag_mode']]
        benchmark = predictions.loc[
            (predictions['model'] == 'ar2')
            & (predictions['horizon'] == horizon)
            & (predictions['lag_mode'] == lag_mode)
            & predictions['target_quarter'].isin(keys['target_quarter'])
            & predictions['prediction'].notna()
        ]
        add_row(model, str(group['candidate_role'].iloc[0]), horizon,
                lag_mode, valid, benchmark)

    standard = predictions.loc[predictions['lag_mode'] == PRIMARY_LAG_MODE]
    for model, group in standard.groupby('model'):
        valid = group.loc[group['prediction'].notna() & group['actual'].notna()]
        benchmark = standard.loc[
            (standard['model'] == 'ar2')
            & standard.set_index(['target_quarter', 'horizon']).index.isin(
                valid.set_index(['target_quarter', 'horizon']).index)
        ]
        add_row(model, str(group['candidate_role'].iloc[0]),
                'POOLED_H1_H3', PRIMARY_LAG_MODE, valid, benchmark)
    return pd.DataFrame(rows).sort_values(
        ['horizon', 'lag_mode', 'rmse']).reset_index(drop=True)


def horizon_updates(predictions: pd.DataFrame) -> pd.DataFrame:
    """Quarter-level H1→H2 and H2→H3 forecast revisions."""
    rows: list[dict] = []
    for (model, lag_mode, quarter), group in predictions.groupby(
            ['model', 'lag_mode', 'target_quarter']):
        forecasts = group.set_index('horizon')['prediction']
        actual = float(group['actual'].iloc[0])
        values = {h: float(forecasts.get(h, np.nan)) for h in HORIZONS}
        rows.append(dict(
            model=model, lag_mode=lag_mode, target_quarter=quarter,
            actual=actual,
            H1_prediction=values['H1'], H2_prediction=values['H2'],
            H3_prediction=values['H3'],
            H1_error=actual - values['H1'],
            H2_error=actual - values['H2'],
            H3_error=actual - values['H3'],
            revision_H1_to_H2=values['H2'] - values['H1'],
            revision_H2_to_H3=values['H3'] - values['H2'],
        ))
    return pd.DataFrame(rows).sort_values(
        ['model', 'lag_mode', 'target_quarter']).reset_index(drop=True)


def ensemble_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    frame = predictions.loc[
        predictions['model'] == 'ensemble_ar2_umidas_usd'].copy()
    frame['ar2_component_error'] = (
        frame['actual'] - frame['ar2_component_prediction'])
    frame['umidas_usd_component_error'] = (
        frame['actual'] - frame['umidas_usd_component_prediction'])
    correlations: dict[tuple[str, str], float] = {}
    for keys, block in frame.groupby(['horizon', 'lag_mode']):
        correlations[keys] = float(block['ar2_component_error'].corr(
            block['umidas_usd_component_error']))
    frame['component_error_correlation'] = [
        correlations[(row.horizon, row.lag_mode)] for row in frame.itertuples()]
    return frame[[
        'target_quarter', 'horizon', 'lag_mode', 'forecast_origin_date',
        'actual', 'ar2_component_prediction', 'ar2_component_error',
        'umidas_usd_component_prediction', 'umidas_usd_component_error',
        'prediction', 'error', 'ensemble_weight_ar2',
        'ensemble_weight_umidas_usd', 'component_error_correlation',
    ]].sort_values(['lag_mode', 'horizon', 'target_quarter']).reset_index(drop=True)


def model_comparison(metrics: pd.DataFrame) -> pd.DataFrame:
    """Standard-primary ranking with conservative-lag sensitivity."""
    rows: list[dict] = []
    for (model, horizon), block in metrics.groupby(['model', 'horizon']):
        standard = block.loc[block['lag_mode'] == PRIMARY_LAG_MODE]
        conservative = block.loc[block['lag_mode'] == ROBUSTNESS_LAG_MODE]
        if standard.empty:
            continue
        std = standard.iloc[0]
        con = conservative.iloc[0] if not conservative.empty else None
        rows.append(dict(
            model=model,
            candidate_role=std['candidate_role'],
            horizon=horizon,
            standard_N=int(std['N']),
            standard_rmse=float(std['rmse']),
            standard_mae=float(std['mae']),
            standard_bias=float(std['bias']),
            standard_relative_rmse_to_ar2=float(std['relative_rmse_to_ar2']),
            conservative_N=(int(con['N']) if con is not None else np.nan),
            conservative_rmse=(float(con['rmse']) if con is not None else np.nan),
            conservative_mae=(float(con['mae']) if con is not None else np.nan),
            conservative_bias=(float(con['bias']) if con is not None else np.nan),
            conservative_relative_rmse_to_ar2=(
                float(con['relative_rmse_to_ar2']) if con is not None else np.nan),
            conservative_minus_standard_rmse=(
                float(con['rmse'] - std['rmse']) if con is not None else np.nan),
        ))
    result = pd.DataFrame(rows)
    result['standard_rmse_rank'] = result.groupby('horizon')[
        'standard_rmse'].rank(method='min')
    return result.sort_values(
        ['horizon', 'standard_rmse_rank', 'model']).reset_index(drop=True)


def run_phase4c(root: Path, *, master_dir: str = 'data/master',
                registry_relative: str
                = 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx') -> dict:
    dataset, protocol = load_phase4c_dataset(
        root, master_dir=master_dir, registry_relative=registry_relative)
    predictions = evaluate_phase4c(dataset, protocol)
    metrics = holdout_metrics(predictions)
    updates = horizon_updates(predictions)
    ensemble = ensemble_diagnostics(predictions)
    comparison = model_comparison(metrics)
    return dict(
        protocol=protocol,
        predictions=predictions,
        metrics=metrics,
        horizon_updates=updates,
        ensemble_diagnostics=ensemble,
        model_comparison=comparison,
    )


def _write_table(frame: pd.DataFrame, path: Path) -> None:
    atomic_parquet(frame, path)
    frame.to_csv(path.with_suffix('.csv'), index=False)


def write_phase4c_results(root: Path, results: dict) -> dict:
    root = Path(root).resolve()
    output = root / 'results'
    output.mkdir(exist_ok=True)
    tables = {
        'phase4c_holdout_predictions.parquet': results['predictions'],
        'phase4c_holdout_metrics.parquet': results['metrics'],
        'phase4c_horizon_updates.parquet': results['horizon_updates'],
        'phase4c_ensemble_diagnostics.parquet': results['ensemble_diagnostics'],
        'phase4c_model_comparison.parquet': results['model_comparison'],
    }
    for name, frame in tables.items():
        _write_table(frame, output / name)
    protocol = _read_json(root / PROTOCOL_PATH)
    protocol['status'] = 'HOLDOUT_EVALUATION_COMPLETE_ARCHITECTURE_UNCHANGED'
    protocol['evaluation_completed_at_utc'] = _utc_now()
    protocol['output_rows'] = {
        name: int(len(frame)) for name, frame in tables.items()}
    save_json(root / PROTOCOL_PATH, protocol)
    return dict(
        protocol=PROTOCOL_PATH,
        rows=protocol['output_rows'],
        holdout_first_loaded_at_utc=(
            protocol['holdout_access_audit']['first_load_started_at_utc']),
    )

