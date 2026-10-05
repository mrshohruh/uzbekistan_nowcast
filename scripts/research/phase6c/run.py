"""Research-only sequential DFM redesign; run this file with the project venv."""
from __future__ import annotations

import importlib.util
import json
import logging
import platform
import sys
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd
import statsmodels
from uznowcast.models.data import load_dataset, horizon_month_end, quarter_start, quarter_end
from audit import build_audit, inventory, assert_protected, BLOCK_BY_KEY, sha
from kernel import Spec, HOLDOUT, FREEZE_DATE, KEYS, mask, standardize, training_panel, estimate, bridge, scores, select

OUT = ROOT / 'results/phase6c'
LOG = logging.getLogger('phase6c')


def frozen_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def save(name, frame):
    frame.to_csv(OUT / f'phase6c_{name}.csv', index=False, float_format='%.17g')
    return frame


def save_json(name, value):
    (OUT / f'phase6c_{name}.json').write_text(json.dumps(value, indent=2, default=str), encoding='utf-8')


class Experiment:
    def __init__(self, panel, lags, events, targets, vintage):
        self.panel, self.lags, self.events, self.targets, self.vintage = panel, lags, events, targets, vintage
        self.cache = {}
        self.states = {}
        self.forecasts, self.audit, self.loadings, self.factors, self.diagnostics, self.scales, self.gdp_usage = [], [], [], [], [], [], []
        self.definitions = []

    def evaluate(self, spec, origins, bridges=('A',), aggregation='mean', modes=('standard', 'conservative')):
        self.definitions.append(dict(**asdict(spec), bridges=','.join(bridges), aggregation=aggregation))
        for target, horizon in origins:
            origin = horizon_month_end(target, horizon)
            available = self.vintage.available_gdp_vintage_as_of(self.events, origin, target=target, timing_rule='STRICT')
            actual = self.targets.loc[target, 'first_release_value']
            release = self.targets.loc[target, 'first_release_date']
            for mode in modes:
                stem = (spec.name, target, horizon, mode)
                failure = ''
                try:
                    if stem not in self.states:
                        frame, audit = mask(self.panel, spec, target, horizon, self.lags, mode)
                        self.audit.extend(dict(specification=spec.name, **r) for r in audit)
                        end = quarter_start(target) - pd.Timedelta(days=1)
                        frame, _ = training_panel(frame, end, spec.balanced)
                        z, means, stds = standardize(frame, end, spec.winsor)
                        # Missing future quarter months are forecasts of latent states.
                        full_index = pd.date_range(z.index.min(), quarter_end(target), freq='ME')
                        z = z.reindex(full_index)
                        factors, loadings, diag = estimate(z.loc[:end], z, spec, self.cache)
                        self.states[stem] = factors, diag
                        for variable in spec.fields:
                            self.scales.append(dict(specification=spec.name, target_quarter=target, horizon=horizon,
                                lag_mode=mode, variable=variable, mean=means[variable], scale=stds[variable], training_end=end))
                        self.diagnostics.append(dict(specification=spec.name, target_quarter=target, horizon=horizon,
                                                     lag_mode=mode, status='SUCCESS', **diag))
                        for j in range(spec.factors):
                            for variable, loading in zip(spec.fields, loadings[:, j]):
                                self.loadings.append(dict(specification=spec.name, target_quarter=target, horizon=horizon,
                                    lag_mode=mode, factor=j+1, variable=variable, block=BLOCK_BY_KEY[variable], loading=loading))
                            self.factors.extend(dict(specification=spec.name, target_quarter=target, horizon=horizon,
                                lag_mode=mode, factor=j+1, month=t, value=v) for t, v in factors[j].items())
                    factors, diag = self.states[stem]
                except (ValueError, np.linalg.LinAlgError, KeyError) as exc:
                    failure = str(exc)
                    LOG.warning('%s %s %s %s failed: %s', spec.name, target, horizon, mode, failure[:180])
                    self.diagnostics.append(dict(specification=spec.name, target_quarter=target, horizon=horizon,
                                                 lag_mode=mode, status='FAILED', failure=failure))
                for kind in bridges:
                    name = spec.name if bridges == ('A',) and aggregation == 'mean' and target not in HOLDOUT else f'{spec.name}__BRIDGE_{kind}_{aggregation}'
                    prediction = np.nan
                    reason = failure
                    if not failure:
                        try:
                            prediction, bdiag = bridge(factors, available, target, origin, kind, aggregation)
                            for quarter, row in available.frame.iterrows():
                                self.gdp_usage.append(dict(model=name, target_quarter=target, horizon=horizon, lag_mode=mode,
                                    origin=origin, GDP_quarter=quarter, publication_date=row.publication_date,
                                    value=row.value, source_url=row.source_url, sha256=row.sha256))
                        except (ValueError, KeyError, np.linalg.LinAlgError) as exc:
                            reason = str(exc)
                    self.forecasts.append(dict(model=name, target_quarter=target, horizon=horizon, lag_mode=mode,
                        timing_rule='STRICT', forecast_origin_date=origin, prediction=prediction, actual=actual,
                        outcome_release_date=release, failure=reason,
                        evaluation_group='HOLDOUT' if target in HOLDOUT else 'DEVELOPMENT',
                        information_class='PREDICTOR_RELEASE_LAG_PSEUDO_REAL_TIME_PARTIAL_VERIFIED_GDP_VINTAGES'))
            LOG.info('%s %s %s complete', spec.name, target, horizon)
        self.flush()

    def flush(self):
        for name, records in [('information_set_audit', self.audit), ('factor_loadings', self.loadings),
                               ('factor_series', self.factors), ('factor_diagnostics', self.diagnostics),
                               ('standardization', self.scales), ('GDP_training_vintage_usage', self.gdp_usage),
                               ('model_definitions', self.definitions)]:
            save(name, pd.DataFrame(records))


def pairwise(forecasts, candidate):
    frames = []
    base = forecasts.loc[forecasts.model.eq(candidate)]
    for name in forecasts.model.unique():
        other = forecasts.loc[forecasts.model.eq(name)]
        keys = base.dropna(subset=['prediction', 'actual'])[KEYS].merge(
            other.dropna(subset=['prediction', 'actual'])[KEYS], on=KEYS, validate='one_to_one')
        both = forecasts.loc[forecasts.model.isin([candidate, name])].merge(keys, on=KEYS, validate='many_to_one')
        if len(both):
            metric = scores(both, 'PAIRWISE_COMMON_WITH_FINAL')
            metric['comparison'] = name
            frames.append(metric)
    return pd.concat(frames, ignore_index=True)


def combinations(forecasts, candidate):
    one = forecasts.loc[forecasts.model.eq(candidate)]
    two = forecasts.loc[forecasts.model.eq('UMIDAS_USD')]
    matched = one.merge(two[KEYS + ['prediction']], on=KEYS, suffixes=('', '_umidas'), validate='one_to_one').dropna(subset=['prediction', 'prediction_umidas', 'actual'])
    dev = matched.loc[matched.evaluation_group.eq('DEVELOPMENT') & matched.lag_mode.eq('standard')]
    delta = dev.prediction - dev.prediction_umidas
    denom = float((delta**2).sum())
    weight = float(np.clip(((dev.actual - dev.prediction_umidas) * delta).sum() / denom, 0., 1.)) if denom > 0 else .5
    # Weight is calculated before the final holdout is forecast/evaluated.
    combos = []
    for w, label in [(0.25, 'FIXED_25_DFM'), (.5, 'FIXED_50_DFM'), (.75, 'FIXED_75_DFM'), (weight, 'DEVELOPMENT_WEIGHT_DFM')]:
        f = matched.drop(columns=['prediction_umidas']).copy()
        f['prediction'] = w * matched.prediction + (1-w) * matched.prediction_umidas
        f['model'] = label
        f['dfm_weight'] = w
        combos.append(f)
    return pd.concat(combos, ignore_index=True), weight


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.FileHandler(OUT / 'phase6c_pipeline.log', mode='w', encoding='utf-8'), logging.StreamHandler()])
    before = inventory(ROOT)
    save_json('protected_before', before)
    protocol = dict(status='DEVELOPMENT_STARTED', research_only=True, holdout_quarters=HOLDOUT,
        selection_cutoff=str(FREEZE_DATE.date()), primary_mode='standard', timing_rule='STRICT',
        primary_target='FIRST_RELEASE', selection_metric='pooled_RMSE_on_identical_development_origins',
        minimum_common_origins=9, factor_order_candidates=[1, 2], factors=[1, 2, 3],
        idiosyncratic_errors='diagonal_white_noise', factor_dynamics='independent_AR_blocks',
        GDP_bridge_minimum='max(12, 3 * coefficient_count)',
        holdout_previously_evaluated_by_prior_phases=True,
        holdout_claim='Selection quarantine in Phase6C; not previously unseen to the research programme',
        blocked_components=['Pure sample-length effect for identical old panel: no 2019 observations',
                            'Full real-time predictor vintage study: archived historical predictor values unavailable'],
        GDP_unresolved_policy='Exclude unknown value vintages; never use date fallback as evidence for revised GDP values',
        sequencing=['DFM0', 'DFM1', 'DFM2_blocks', 'DFM3_ragged', 'factors_and_AR_order', 'freeze_factors',
                    'bridges', 'freeze_final_and_combination_weight', 'robustness_development_only', 'holdout_once'])
    save_json('protocol', protocol)
    dataset = load_dataset(ROOT)
    panel, audit = build_audit(ROOT, dataset, OUT, save)
    vintages = frozen_module('phase6c_verified_vintages', 'scripts/research/phase6b2/vintages.py')
    events = pd.read_csv(ROOT / 'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    targets = pd.read_csv(ROOT / 'results/research/phase6b2/phase6b2_gdp_vintage_registry.csv').set_index('quarter')
    frozen = pd.read_csv(ROOT / 'results/research/phase6b2/phase6b2_forecasts.csv')
    frozen = frozen.loc[frozen.timing_rule.eq('STRICT')].copy()
    frozen['actual'] = frozen.actual_first_release
    frozen['outcome_release_date'] = frozen.target_quarter.map(targets.first_release_date)
    frozen['evaluation_group'] = np.where(frozen.target_quarter.isin(HOLDOUT), 'HOLDOUT', 'DEVELOPMENT')
    frozen['model'] = frozen.model.replace({'DFM_A': 'DFM-0', 'DFM_B': 'PHASE6B2_DFM_B', 'COMBO_A': 'PHASE6B2_COMBO_A', 'COMBO_B': 'PHASE6B2_COMBO_B'})
    # DFM-0 exact saved clean path, never re-estimated with altered data/definitions.
    save('DFM0_identity_audit', frozen.loc[frozen.model.eq('DFM-0'), KEYS + ['prediction']].assign(saved_path_identity=True))
    dev = [(str(q), h) for q in pd.period_range('2022Q1', '2025Q2', freq='Q')
           if str(q) in targets.index for h in ('H1', 'H2', 'H3')]
    # Extend historical origins using the SAME clean benchmark kernels and
    # verified vintage accessor. No frozen benchmark outputs are overwritten.
    sys.path.append(str(ROOT / 'scripts/research/phase6b2'))
    benchmark_kernel = frozen_module('phase6c_clean_benchmark_kernel', 'scripts/research/phase6b2/run.py')
    extra = []
    existing = set(zip(frozen.target_quarter, frozen.horizon, frozen.lag_mode))
    for target, horizon in dev:
        origin = horizon_month_end(target, horizon)
        available = vintages.available_gdp_vintage_as_of(events, origin, target=target)
        for mode in ('standard', 'conservative'):
            if (target, horizon, mode) in existing:
                continue
            predictions = benchmark_kernel.benchmarks(dataset, available, target, horizon, mode)
            for name, (prediction, failure) in predictions.items():
                extra.append(dict(model=name, target_quarter=target, horizon=horizon, lag_mode=mode,
                    timing_rule='STRICT', forecast_origin_date=origin, prediction=prediction, failure=failure,
                    actual=targets.loc[target, 'first_release_value'],
                    outcome_release_date=targets.loc[target, 'first_release_date'], evaluation_group='DEVELOPMENT'))
    frozen = pd.concat([frozen, pd.DataFrame(extra)], ignore_index=True)
    holdout = [(q, h) for q in HOLDOUT for h in ('H1', 'H2', 'H3')]
    eligible = audit.loc[audit.eligible_for_ragged_panel, 'variable'].tolist()
    core = tuple(audit.loc[audit.eligible_for_long_core, 'variable'])
    # One representative industrial series; sector components are ablations, not duplicates.
    balanced_keys = [k for k in eligible if k not in ('manufacturing', 'mining', 'electricity_gas', 'wholesale_trade')]
    exp = Experiment(panel, dataset.release_lag_days, events, targets, vintages)
    selections = []
    base = Spec('DFM-1', core)
    exp.evaluate(base, dev)
    # Controlled sample-length comparison with the SAME recovered long-core
    # variables; it is diagnostic and never enters specification selection.
    exp.evaluate(replace(base, name='DFM-1_SHORT_HISTORY_CONTROL', start='2021-01-31'), dev)
    block_specs = [replace(base, name='DFM-2_CORE', balanced=True)]
    for block in ('PRODUCTION', 'DOMESTIC_DEMAND', 'PRICES', 'EXTERNAL', 'FINANCIAL', 'PAYMENTS'):
        addition = tuple(k for k in balanced_keys if BLOCK_BY_KEY[k] == block and k not in core)
        if addition:
            block_specs.append(replace(base, name='DFM-2_PLUS_' + block, fields=core + addition, balanced=True))
    block_specs.append(Spec('DFM-2_COMBINED', tuple(balanced_keys), balanced=True))
    for spec in block_specs:
        exp.evaluate(spec, dev)
    best2, table = select(pd.DataFrame(exp.forecasts), [s.name for s in block_specs])
    selections.append(table.assign(stage='BLOCK_SELECTION'))
    structure2 = next(s for s in block_specs if s.name == best2)
    protocol['selected_DFM2'] = best2
    ragged = replace(structure2, name='DFM-3', balanced=False)
    exp.evaluate(ragged, dev)
    # Full eligible ragged panel is a prespecified block addition, not a variable search.
    full_ragged = Spec('DFM-3_COMBINED', tuple(balanced_keys))
    exp.evaluate(full_ragged, dev)
    structure_name, table = select(pd.DataFrame(exp.forecasts), [best2, 'DFM-3', 'DFM-3_COMBINED'])
    selections.append(table.assign(stage='INFORMATION_STRUCTURE'))
    structure = {best2: structure2, 'DFM-3': ragged, 'DFM-3_COMBINED': full_ragged}[structure_name]
    protocol['selected_information_structure'] = structure_name
    factor_specs = [replace(structure, name=f'DFM-4_R{r}_P{p}', factors=r, order=p)
                    for r in (1, 2, 3) for p in (1, 2)]
    for spec in factor_specs:
        exp.evaluate(spec, dev)
    best4, table = select(pd.DataFrame(exp.forecasts), [s.name for s in factor_specs])
    selections.append(table.assign(stage='FACTOR_AND_AR_ORDER'))
    selected = next(s for s in factor_specs if s.name == best4)
    protocol.update(status='FACTOR_STRUCTURE_FROZEN', selected_factor_specification=asdict(selected),
                    development_origins=dev, long_core=core, ragged_panel=full_ragged.fields,
                    holdout_forecasts_evaluated=False)
    save_json('protocol', protocol)
    # Only after factor structure selection may bridges be compared.
    exp.evaluate(selected, dev, bridges=('A', 'B', 'C'))
    exp.evaluate(selected, dev, bridges=('A', 'B', 'C'), aggregation='end')
    bridge_names = [f'{selected.name}__BRIDGE_{b}_{a}' for a in ('mean', 'end') for b in ('A', 'B', 'C')]
    final, table = select(pd.DataFrame(exp.forecasts), bridge_names)
    selections.append(table.assign(stage='BRIDGE_SELECTION'))
    bridge_kind, aggregation = final.split('__BRIDGE_')[1].split('_')
    # Duplicate A rows can arise from selection and bridge evaluation; prefer the
    # explicitly named bridge rows. All origins are uniquely keyed downstream.
    research = pd.DataFrame(exp.forecasts).drop_duplicates(['model'] + KEYS, keep='first')
    joined_dev = pd.concat([research, frozen.loc[frozen.evaluation_group.eq('DEVELOPMENT')]], ignore_index=True)
    _, weight = combinations(joined_dev, final)
    protocol.update(status='FINAL_SPECIFICATION_FROZEN_BEFORE_HOLDOUT', final_model=final,
        selected_bridge=bridge_kind, selected_aggregation=aggregation, frozen_combination_DFM_weight=weight,
        specification_freeze_recorded_at=datetime.now(timezone.utc).isoformat(),
        specification_sha256=sha(OUT / 'phase6c_model_definitions.csv'))
    save_json('protocol', protocol)
    save_json('selection_freeze', protocol)
    save('factor_selection', pd.concat(selections, ignore_index=True))
    # Robustness is development-only and cannot change the frozen specification.
    robustness = [replace(selected, name='ROBUST_START_2020', start='2020-01-31'),
                  replace(selected, name='ROBUST_WINSOR_1_99', winsor=True)]
    for block in sorted(set(BLOCK_BY_KEY[k] for k in selected.fields)):
        fields = tuple(k for k in selected.fields if BLOCK_BY_KEY[k] != block)
        if len(fields) > selected.factors:
            robustness.append(replace(selected, name='ABLATE_' + block, fields=fields))
    for key, label in [('gold_price', 'GOLD'), ('russia_ipi', 'RUSSIA'), ('usd_uzs', 'USD'), ('rub_uzs', 'RUB')]:
        fields = tuple(k for k in selected.fields if k != key)
        if fields != selected.fields and len(fields) > selected.factors:
            robustness.append(replace(selected, name='ROBUST_NO_' + label, fields=fields))
    no_fx = tuple(k for k in selected.fields if k not in ('usd_uzs', 'rub_uzs'))
    if no_fx != selected.fields and len(no_fx) > selected.factors:
        robustness.append(replace(selected, name='ROBUST_NO_FX', fields=no_fx))
    for spec in robustness:
        exp.evaluate(spec, dev, bridges=(bridge_kind,), aggregation=aggregation, modes=('standard',))
    # ONE final challenger holdout pass. No model selection calls below this line.
    exp.evaluate(selected, holdout, bridges=(bridge_kind,), aggregation=aggregation)
    research = pd.DataFrame(exp.forecasts).drop_duplicates(['model'] + KEYS, keep='first')
    all_forecasts = pd.concat([research, frozen], ignore_index=True)
    combo, check_weight = combinations(all_forecasts, final)
    assert abs(weight - check_weight) < 1e-12
    forecasts = pd.concat([all_forecasts, combo], ignore_index=True)
    if forecasts.duplicated(['model'] + KEYS).any():
        raise AssertionError('Duplicate forecasts')
    save('forecasts', forecasts)
    full_scores = scores(forecasts)
    save('development_metrics', full_scores.loc[full_scores.evaluation_group.eq('DEVELOPMENT')])
    save('holdout_metrics', full_scores.loc[full_scores.evaluation_group.eq('HOLDOUT')])
    save('horizon_metrics', full_scores)
    save('matched_metrics', pairwise(forecasts, final))
    errors = forecasts.copy()
    errors['error'] = errors.actual - errors.prediction
    errors['absolute_error'] = errors.error.abs()
    errors['squared_error'] = errors.error**2
    save('quarter_level_errors', errors)
    save('combination_metrics', full_scores.loc[full_scores.model.isin(combo.model.unique())])
    rob_names = [s.name for s in robustness]
    robust_scores = full_scores.loc[full_scores.model.str.startswith(tuple(rob_names))] if rob_names else pd.DataFrame()
    save('robustness', robust_scores)
    save('block_ablation', robust_scores.loc[robust_scores.model.str.startswith('ABLATE_')])
    from report import report
    checks = assert_protected(ROOT, before)
    report(OUT, protocol, audit, forecasts, full_scores, checks)
    protocol.update(status='RESEARCH_COMPLETE_WITH_DOCUMENTED_LIMITATIONS', holdout_forecasts_evaluated=True,
                    recommendation='RESEARCH_ONLY')
    save_json('protocol', protocol)
    save_json('protected_after', checks)
    save_json('run_manifest', dict(status=protocol['status'], recommendation='RESEARCH_ONLY',
        python=platform.python_version(), pandas=pd.__version__, numpy=np.__version__, statsmodels=statsmodels.__version__,
        completed_at=datetime.now(timezone.utc).isoformat(), protected=checks,
        failed_origin_records=sum(d.get('status') == 'FAILED' for d in exp.diagnostics),
        inputs={p: sha(ROOT / p) for p in ['data/master/v1_monthly.parquet', 'data/master/gdp_quarterly.parquet',
               'registry/uzbekistan_nowcasting_v1.2_registry.xlsx', 'results/research/phase6b2/phase6b2_gdp_revision_history.csv']},
        outputs={p.name: sha(p) for p in OUT.glob('*.csv')}))
    LOG.info('PHASE 6C finished: %s, r=%s, bridge=%s; protected changes=NO', final, selected.factors, bridge_kind)


if __name__ == '__main__':
    main()
