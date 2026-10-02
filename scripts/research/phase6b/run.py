"""Run with: .venv/Scripts/python.exe scripts/research/phase6b/run.py"""
from __future__ import annotations

import hashlib
import json
import logging
import platform
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd
import statsmodels
from experiment import (DOMESTIC, IMPORTS, SERVICES, LABEL, KEYS, SPECS, Spec,
                        masked_panel, prepare, pca, estimate, bridge, matched_pair)
from uznowcast.models.data import load_dataset, quarter_start, quarter_end, horizon_month_end

OUT = ROOT / 'results/research/phase6b'
DOC = ROOT / 'docs/modeling/phase6b'
LOG = logging.getLogger('phase6b')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, default=str, allow_nan=False), encoding='utf-8')


def protect():
    baseline = json.loads((OUT / 'phase6b_protected_before.json').read_text())
    after = {p: sha(ROOT / p) if (ROOT / p).is_file() else 'MISSING' for p in baseline}
    changed = [p for p in baseline if baseline[p] != after[p]]
    if changed:
        raise RuntimeError('Protected artifacts changed: ' + ', '.join(changed))
    return after


def table(name, rows, columns=None):
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    if frame.empty and columns is not None:
        frame = pd.DataFrame(columns=columns)
    frame.to_csv(OUT / f'phase6b_{name}.csv', index=False, float_format='%.12g')
    return frame


def benchmarks(gdp):
    """Saved Phase 4B/4C predictions underpin the frozen Phase 5A architecture."""
    frames = []
    for path, evidence in [('results/phase4b_predictions.csv', 'DEVELOPMENT_PSEUDO_OOS'),
                           ('results/phase4c_holdout_predictions.csv', 'HISTORICAL_POST_DEVELOPMENT_TEST')]:
        f = pd.read_csv(ROOT / path)
        f = f.loc[f.model.isin(['ar1', 'ar2', 'umidas_usd_uzs_mom_dlog', 'ensemble_ar2_umidas_usd'])].copy()
        f['source_artifact'] = path
        f['evaluation_group'] = evidence
        frames.append(f)
    b = pd.concat(frames, ignore_index=True)
    if b.duplicated(['model'] + KEYS).any():
        raise ValueError('frozen benchmark duplicate origins')
    if not np.allclose(b.actual, b.target_quarter.map(gdp), atol=1e-10, rtol=0):
        raise ValueError('GDP values differ from frozen forecast outcomes')
    saved = pd.read_csv(ROOT / 'results/challengers/phase5c/phase5c_univariate_predictions.csv')
    saved = saved.loc[saved.model.eq('challenger_umidas_usd_uzs_mom_dlog_l3')]
    audit = matched_pair(b.loc[b.model.eq('umidas_usd_uzs_mom_dlog')], saved)
    if not np.allclose(audit.prediction, audit.prediction_benchmark, atol=1e-12, rtol=0):
        raise ValueError('Phase5C saved USD U-MIDAS differs from frozen baseline')
    table('frozen_umidas_identity_audit', audit)
    return b


def metrics(predictions, sample, comparison=''):
    rows = []
    for (model, mode, evaluation), block in predictions.groupby(['model', 'lag_mode', 'evaluation_group']):
        for horizon in ['H1', 'H2', 'H3', 'ALL']:
            f = block if horizon == 'ALL' else block.loc[block.horizon.eq(horizon)]
            f = f.dropna(subset=['prediction', 'actual'])
            if len(f):
                error = f.actual - f.prediction
                rows.append(dict(model=model, lag_mode=mode, evaluation_group=evaluation, horizon=horizon,
                                 sample=sample, comparison=comparison, n=len(f), quarters=f.target_quarter.nunique(),
                                 first_quarter=f.target_quarter.min(), last_quarter=f.target_quarter.max(),
                                 rmse=float(np.sqrt(np.mean(error**2))), mae=float(abs(error).mean()),
                                 bias=float(error.mean()), bias_convention='actual_minus_forecast'))
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    DOC.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.FileHandler(OUT / 'phase6b_pipeline.log', mode='w'), logging.StreamHandler()])
    np.random.seed(602)
    before = protect()
    dataset = load_dataset(ROOT)
    gdp = dataset.gdp.set_index('quarter').gdp_real_yoy_pct
    definition = json.loads((ROOT / 'results/frozen_validation_definition.json').read_text())
    protocol = json.loads((ROOT / 'results/challengers/phase5c/phase5c_challenger_protocol.json').read_text())
    panel = pd.read_csv(ROOT / 'data/research/phase6a2/cbu_midas_monthly_panel.csv')
    panel.index = pd.PeriodIndex(panel.reference_period, freq='M').to_timestamp('M')
    if panel.index.has_duplicates:
        raise ValueError('duplicate panel month')
    panel = panel.loc['2021-01-31':'2026-08-31'].copy()
    assert panel.index.equals(pd.date_range('2021-01-31', '2026-08-31', freq='ME'))
    assert not panel[list(DOMESTIC) + [IMPORTS, SERVICES]].isna().any().any()
    regimes = panel.services_output_regime
    expected_regime = pd.Series(np.where(panel.index >= pd.Timestamp('2024-09-30'),
                                         'expanded_coverage_2024_09_onward', 'before_2024_09'), index=panel.index)
    assert regimes.equals(expected_regime.rename(regimes.name))
    b = benchmarks(gdp)
    targets = [q for q in definition['development_quarters'] + definition['holdout_quarters']
               if q in gdp.index and quarter_start(q) >= panel.index.min().to_period('M').to_timestamp()
               and quarter_end(q) <= panel.index.max()]
    # Twelve consecutive fully aligned GDP quarters, not 12 arbitrary observations.
    targets = [q for q in targets if len(pd.period_range('2021Q1', str(pd.Period(q, freq='Q') - 1), freq='Q')) >= 12
               and all(str(t) in gdp.index for t in pd.period_range('2021Q1', str(pd.Period(q, freq='Q') - 1), freq='Q'))]
    all_specs = list(SPECS)
    pos_end = pd.Timestamp('2024-12-31')
    if panel.loc[:pos_end, 'pos_turnover_monthly_log_yoy'].notna().all():
        all_specs.append(Spec('DFM_POS_HISTORICAL_ROBUSTNESS_ONLY', DOMESTIC + ('pos_turnover_monthly_log_yoy',)))
    specification = dict(label=LABEL, primary='DFM_DOMESTIC_3', specs=[asdict(s) for s in all_specs],
                         factor_order=1, measurement_error='diagonal_white_noise', factor_variance='identity_innovation',
                         fit_policy='training_before_target; lbfgs then bfgs if necessary; maxiter=400 each',
                         bridges=['BRIDGE_A', 'BRIDGE_B'], quarterly_aggregation='three_month_mean_filtered_and_state_predicted',
                         standardization='training_only_ddof1', services_adjustment='training_OLS_intercept_plus_regime_dummy',
                         factor_source='FILTERED_ONE_SIDED', descriptive_source='SMOOTHED_FULL_SAMPLE_DESCRIPTIVE_ONLY',
                         two_factor_identification='unrestricted_VAR1; reject covariance_condition>1e12',
                         minimum_GDP_quarters=12, seed=602,
                         horizons=protocol['rules']['horizons'], lag_modes=['standard', 'conservative'],
                         release_lags=dataset.release_lag_days, services_mask='inherited_Phase5C_30_day_fallback_not_observed_release',
                         evaluation_definition=definition, combination='separate_equal_weight_combo_per_DFM_bridge; no_ex_post_selection',
                         decision_rule='UNSTABLE if failure rate >20%; otherwise PROMISING if pooled matched RMSE and MAE improve vs U-MIDAS and at least two horizon RMSEs improve; otherwise NO_INCREMENTAL_VALUE; fewer than 8 target quarters INSUFFICIENT_EVIDENCE')
    save_json('phase6b_model_specifications.json', specification)
    pcarows, corrrows = [], []
    sets = [('DOMESTIC_3', DOMESTIC, 77.7), ('DOMESTIC_3_PLUS_IMPORTS', DOMESTIC + (IMPORTS,), 58.4),
            ('DOMESTIC_3_PLUS_SERVICES', DOMESTIC + (SERVICES,), 68.2),
            ('DOMESTIC_3_PLUS_IMPORTS_PLUS_SERVICES', DOMESTIC + (IMPORTS, SERVICES), 54.5)]
    for name, fields, expected in sets:
        corr, eig, variance, loads = pca(panel[list(fields)])
        if abs(variance[0] - expected) > 1.:
            raise RuntimeError(f'Material PCA inconsistency: {name}: {variance[0]} expected approx {expected}')
        if IMPORTS in fields and abs(loads[fields.index(IMPORTS)]) > .12:
            raise RuntimeError('Imports PC1 loading materially inconsistent')
        for i, (e, v) in enumerate(zip(eig, variance), 1):
            pcarows.append(dict(predictor_set=name, component=i, eigenvalue=e, variance_pct=v,
                                pc1_loadings=json.dumps(dict(zip(fields, loads.tolist()))), n_months=len(panel)))
        for a in fields:
            for c in fields:
                corrrows.append(dict(predictor_set=name, variable_1=a, variable_2=c, correlation=corr.loc[a, c]))
    table('pca_diagnostics', pcarows)
    table('correlation_matrix', corrrows)
    forecasts, failures, convergence, loadrows, factorrows, scales, servicesrows, stability = [], [], [], [], [], [], [], []
    origin_pca = []
    eligible = []
    for spec in all_specs:
        spec_panel = panel.loc[:pos_end] if 'POS_HISTORICAL' in spec.name else panel
        disabled_reason = None
        for target in targets:
            if quarter_end(target) > spec_panel.index.max():
                continue
            for horizon in specification['horizons']:
                for mode in specification['lag_modes']:
                    origin = dict(specification=spec.name, target_quarter=target, horizon=horizon, lag_mode=mode)
                    eligible.append(origin)
                    LOG.info('estimate %s %s %s %s', spec.name, target, horizon, mode)
                    train_end = quarter_start(target) - pd.Timedelta(days=1)
                    evaluation = 'HISTORICAL_POST_DEVELOPMENT_TEST' if target in definition['holdout_quarters'] else 'DEVELOPMENT_PSEUDO_OOS'
                    base = dict(**origin, evaluation_group=evaluation, evidence_class=LABEL, actual=float(gdp.loc[target]),
                                forecast_origin_date=str(horizon_month_end(target, horizon).date()))
                    if disabled_reason is not None:
                        failures.append(dict(**origin, bridge='BOTH', reason=disabled_reason))
                        convergence.append(dict(**origin, converged=False, estimation_attempted=False, failure=disabled_reason))
                        for bridge_name in ['BRIDGE_A', 'BRIDGE_B']:
                            forecasts.append(dict(**base, model=spec.name+'__'+bridge_name, bridge=bridge_name, prediction=np.nan, failure=disabled_reason))
                        continue
                    try:
                        masked, cutoffs = masked_panel(spec_panel, spec.fields, target, horizon, dataset.release_lag_days, mode)
                        standardized, means, stds, regime_diag, adjusted = prepare(masked, regimes, train_end, spec.adjust_services)
                        training = standardized.loc[:train_end]
                        diagnostic_panel = training.dropna()
                        _, eigenvalues, explained, pc_loads = pca(diagnostic_panel)
                        for component, (eigenvalue, share) in enumerate(zip(eigenvalues, explained), 1):
                            origin_pca.append(dict(**origin, component=component, eigenvalue=eigenvalue, variance_pct=share,
                                                   n_complete_training_months=len(diagnostic_panel),
                                                   pc1_loadings=json.dumps(dict(zip(spec.fields, pc_loads.tolist())))))
                        # Reindex only the latent-state timeline, never interpolate observations.
                        state_index = pd.date_range(spec_panel.index.min(), quarter_end(target), freq='ME')
                        standardized = standardized.reindex(state_index)
                        for field in spec.fields:
                            scales.append(dict(**origin, variable=field, mean=means[field], std=stds[field], training_end=str(train_end.date()),
                                               n_training_observed=int(training[field].notna().sum()), cutoff=cutoffs[field]))
                        if SERVICES in spec.fields:
                            for date in masked.index:
                                servicesrows.append(dict(**origin, month=str(date.date()), raw_value=masked.loc[date, SERVICES],
                                                         adjusted_value=adjusted.loc[date, SERVICES], training_end=str(train_end.date()), **regime_diag))
                        fit, factors, loads, params, signs, diag = estimate(training, standardized, spec)
                        convergence.append(dict(**origin, **diag, n_GDP_quarters=len(pd.period_range('2021Q1', str(pd.Period(target, freq='Q')-1), freq='Q'))))
                        for j in range(spec.factors):
                            for i, field in enumerate(spec.fields):
                                loading = loads[i, j]
                                loadrows.append(dict(**origin, variable=field, factor=j+1, loading=loading,
                                                     idiosyncratic_variance=params[f'sigma2.{field}']))
                            for date, value in zip(state_index, factors[:, j]):
                                factorrows.append(dict(**origin, month=str(date.date()), factor=j+1, value=value,
                                                       factor_source='FILTERED_ONE_SIDED' if date <= horizon_month_end(target, horizon) else 'STATE_PREDICTED_NO_TARGET_OBSERVATIONS',
                                                       forecast_eligible=not bool(diag.get('failure'))))
                            for i, field in enumerate(spec.fields):
                                z = standardized[field].loc[:train_end]
                                f = pd.Series(factors[:, j], index=state_index).loc[:train_end]
                                stability.append(dict(**origin, variable=field, factor=j+1, predictor_factor_correlation=z.corr(f),
                                                      loading=loads[i, j], factor_ar=diag['factor_ar_coefficient'], covariance_condition=diag['covariance_condition']))
                        if diag.get('failure'):
                            if spec.factors == 2 and 'NOT_ESTIMABLE' in diag['failure']:
                                disabled_reason = diag['failure'] + '; specification_gate_failed_no_further_forced_estimation'
                            raise ValueError(diag['failure'])
                        # Never include target GDP in the bridge estimator.
                        training_gdp = gdp.loc[gdp.index < target]
                        for bridge_name in ['BRIDGE_A', 'BRIDGE_B']:
                            model_name = spec.name + '__' + bridge_name
                            try:
                                prediction, n, coef, condition = bridge(factors, state_index, training_gdp, target, bridge_name)
                                forecasts.append(dict(**base, model=model_name, bridge=bridge_name, prediction=prediction,
                                                      error=float(gdp.loc[target])-prediction, n_GDP_quarters=n,
                                                      bridge_coefficients=json.dumps(coef), bridge_condition=condition, failure=''))
                            except (ValueError, KeyError) as exc:
                                forecasts.append(dict(**base, model=model_name, bridge=bridge_name, prediction=np.nan, failure=str(exc)))
                                failures.append(dict(**origin, bridge=bridge_name, reason=str(exc)))
                    except Exception as exc:
                        if spec.factors == 2:
                            disabled_reason = 'NOT_ESTIMABLE_WITH_CURRENT_SAMPLE: ' + str(exc)
                        LOG.warning('origin failed %s: %s', origin, exc)
                        failures.append(dict(**origin, bridge='BOTH', reason=f'{type(exc).__name__}: {exc}'))
                        for bridge_name in ['BRIDGE_A', 'BRIDGE_B']:
                            forecasts.append(dict(**base, model=spec.name+'__'+bridge_name, bridge=bridge_name, prediction=np.nan, failure=str(exc)))
        # Separate descriptive full-sample fit. These states cannot enter forecasts.
        try:
            z, means, stds, _, _ = prepare(spec_panel[list(spec.fields)], regimes, spec_panel.index.max(), spec.adjust_services)
            fit, factors, loads, params, signs, diag = estimate(z, z, spec)
            convergence.append(dict(specification=spec.name, target_quarter='FULL_SAMPLE_DESCRIPTIVE', horizon='NONE', lag_mode='NONE', **diag))
            smooth = fit.factors.smoothed.T * signs
            for j in range(spec.factors):
                for date, filtered, smoothed in zip(z.index, factors[:, j], smooth[:, j]):
                    factorrows.extend([dict(specification=spec.name, target_quarter='FULL_SAMPLE_DESCRIPTIVE', horizon='NONE', lag_mode='NONE',
                                            month=str(date.date()), factor=j+1, value=value, factor_source=source, forecast_eligible=False)
                                       for value, source in [(filtered, 'FILTERED_FULL_SAMPLE_DESCRIPTIVE_ONLY'), (smoothed, 'SMOOTHED_FULL_SAMPLE_DESCRIPTIVE_ONLY')]])
            for i, field in enumerate(spec.fields):
                for j in range(spec.factors):
                    loadrows.append(dict(specification=spec.name, target_quarter='FULL_SAMPLE_DESCRIPTIVE', horizon='NONE', lag_mode='NONE',
                                         variable=field, factor=j+1, loading=loads[i,j], idiosyncratic_variance=params[f'sigma2.{field}']))
        except Exception as exc:
            failures.append(dict(specification=spec.name, target_quarter='FULL_SAMPLE_DESCRIPTIVE', reason=str(exc)))
    f = table('forecasts', forecasts)
    table('eligible_origins', eligible)
    failed = table('failed_origins', failures, ['specification', *KEYS, 'bridge', 'reason'])
    conv = table('convergence_diagnostics', convergence)
    loading = table('factor_loadings', loadrows)
    table('factor_series', factorrows)
    factor_frame = pd.DataFrame(factorrows)
    time_stability = []
    filtered = factor_frame.loc[factor_frame.factor_source.eq('FILTERED_ONE_SIDED')]
    for keys, block in filtered.groupby(['specification','horizon','lag_mode','factor']):
        previous = None
        for target, current in block.groupby('target_quarter', sort=True):
            values = current.set_index('month').value
            if previous is not None:
                common_months = values.index.intersection(previous.index)
                time_stability.append(dict(specification=keys[0],horizon=keys[1],lag_mode=keys[2],factor=keys[3],
                                           target_quarter=target,n_overlap=len(common_months),
                                           overlap_factor_correlation=values.loc[common_months].corr(previous.loc[common_months]),
                                           overlap_factor_rmse=float(np.sqrt(np.mean((values.loc[common_months]-previous.loc[common_months])**2)))))
            previous = values
    table('factor_time_stability', time_stability)
    table('standardization', scales)
    table('origin_pca_diagnostics', origin_pca)
    table('services_break_diagnostics', servicesrows)
    st = pd.DataFrame(stability).sort_values(['specification','variable','factor','horizon','lag_mode','target_quarter'])
    st['loading_change'] = st.groupby(['specification','variable','factor','horizon','lag_mode']).loading.diff()
    table('factor_stability', st)
    table('imports_diagnostics', loading.loc[loading.variable.eq(IMPORTS)])
    combo = []
    usd = b.loc[b.model.eq('umidas_usd_uzs_mom_dlog')]
    for name, block in f.groupby('model'):
        matched = matched_pair(block, usd)
        for row in matched.to_dict('records'):
            row['prediction'] = .5 * row['prediction'] + .5 * row['prediction_benchmark']
            row['model'] = 'COMBO_EQUAL__' + name
            row['error'] = row['actual'] - row['prediction']
            combo.append(row)
    combos = table('combination_forecasts', combo, list(f.columns))
    all_predictions = pd.concat([f, combos, b], ignore_index=True)
    available = metrics(all_predictions, 'ALL_AVAILABLE_ORIGIN')
    matched_rows, comparison_rows = [], []
    # Pairwise matched panels retain the exact comparator and exact denominator.
    for name, block in pd.concat([f, combos], ignore_index=True).groupby('model'):
        for bench_name, bench in b.groupby('model'):
            m = matched_pair(block, bench)
            m['benchmark_model'] = bench_name
            matched_rows.extend(m.to_dict('records'))
            rm = metrics(m, 'MATCHED_SAMPLE', bench_name)
            bm = m.copy()
            bm['prediction'] = bm.prediction_benchmark
            bm['model'] = bench_name
            mb = metrics(bm, 'MATCHED_SAMPLE', name)
            if not rm.empty:
                lookup = mb.set_index(['horizon','lag_mode','evaluation_group'])
                for row in rm.to_dict('records'):
                    br = lookup.loc[(row['horizon'],row['lag_mode'],row['evaluation_group'])]
                    row.update(benchmark_rmse=br.rmse, benchmark_mae=br.mae, rmse_difference=row['rmse']-br.rmse,
                               mae_difference=row['mae']-br.mae)
                    comparison_rows.append(row)
    matched = table('matched_forecasts', matched_rows)
    comparison = table('benchmark_comparison', comparison_rows)
    combined_metrics = pd.concat([comparison, available], ignore_index=True)
    table('horizon_metrics', combined_metrics.loc[combined_metrics.horizon.ne('ALL')])
    table('model_metrics', combined_metrics.loc[combined_metrics.horizon.eq('ALL')])
    table('combination_metrics', comparison.loc[comparison.model.str.startswith('COMBO_EQUAL')])
    table('quarter_level_errors', all_predictions.assign(error=all_predictions.actual-all_predictions.prediction))
    # A pooled 10-quarter comparison accompanies, never replaces, frozen partitions.
    pooled = all_predictions.loc[all_predictions.target_quarter.isin(targets)].copy()
    pooled['evaluation_group'] = 'POOLED_10_QUARTERS_RESEARCH_ONLY'
    table('pooled_metrics', metrics(pooled, 'ALL_AVAILABLE_ORIGIN'))
    # Global common-origin set across successful primary one-factor variants and benchmarks.
    names = [s.name+'__'+br for s in SPECS if s.factors == 1 for br in ['BRIDGE_A','BRIDGE_B']]
    common = None
    for name in names + b.model.unique().tolist():
        valid = all_predictions.loc[all_predictions.model.eq(name)].dropna(subset=['prediction'])
        keys = set(map(tuple, valid[KEYS].to_numpy()))
        common = keys if common is None else common & keys
    global_common = all_predictions.loc[all_predictions.model.isin(names + b.model.unique().tolist()) &
                                        all_predictions[KEYS].apply(tuple, axis=1).isin(common)].copy()
    global_common['evaluation_group'] = 'POOLED_COMMON_ORIGINS_RESEARCH_ONLY'
    global_metrics = table('common_origin_metrics', metrics(global_common, 'MATCHED_SAMPLE_COMMON_ALL_PRIMARY_MODELS'))
    after = protect()
    save_json('phase6b_protected_after.json', after)
    manifest = dict(status='COMPLETED_RESEARCH_ONLY', completed_at_utc=datetime.now(timezone.utc).isoformat(),
                    label=LABEL, python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__, statsmodels=statsmodels.__version__,
                    monthly_sample=['2021-01','2026-08'], n_months=68, GDP_evaluation_targets=targets,
                    GDP_source='data/master/gdp_quarterly.parquet:gdp_real_yoy_pct',
                    GDP_values_verified_against_frozen_forecasts=True,
                    GDP_vintage_note='current master retrieval metadata differs from original freeze; all target values equal frozen actuals',
                    Phase5C_DFM_origin_predictions='NOT_SAVED_BY_PHASE5C; metrics_only_not_origin_matched',
                    eligible_origin_count=len(eligible), failed_origin_records=len(failed), successful_forecasts=int(f.prediction.notna().sum()),
                    protected_count=len(before), protected_byte_identical=before==after, registry_amended=False, production_promoted=False,
                    baseline_benchmark_sources=b.source_artifact.unique().tolist(),
                    input_hashes={p: sha(ROOT/p) for p in ['data/research/phase6a2/cbu_midas_monthly_panel.csv', 'data/master/gdp_quarterly.parquet',
                                                           'results/frozen_validation_definition.json', 'results/challengers/phase5c/phase5c_challenger_protocol.json',
                                                           'results/phase4b_predictions.csv','results/phase4c_holdout_predictions.csv']},
                    code_hashes={p.name: sha(p) for p in Path(__file__).parent.glob('*.py')})
    save_json('phase6b_run_manifest.json', manifest)
    from report import write_report
    write_report(ROOT, OUT, DOC, f, comparison, global_metrics, pd.DataFrame(pcarows), loading, conv, manifest)
    protect()
    LOG.info('Completed: %s valid forecasts; %s protected artifacts unchanged', manifest['successful_forecasts'], len(before))


if __name__ == '__main__':
    main()
