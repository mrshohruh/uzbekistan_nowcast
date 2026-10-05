"""Reconstruct reports and controlled development diagnostics, never select models.

This command makes no holdout forecasts and does not alter the selection freeze.
"""
from dataclasses import replace
import json

import numpy as np
import pandas as pd

from run import (ROOT, OUT, Experiment, frozen_module, save, pairwise, scores,
                 load_dataset, Spec, assert_protected, sha)
from report import report


def main():
    protocol = json.loads((OUT / 'phase6c_protocol.json').read_text())
    freeze = sha(OUT / 'phase6c_selection_freeze.json')
    before = json.loads((OUT / 'phase6c_protected_before.json').read_text())
    forecasts = pd.read_csv(OUT / 'phase6c_forecasts.csv')
    files = ['information_set_audit', 'factor_loadings', 'factor_series', 'factor_diagnostics',
             'standardization', 'GDP_training_vintage_usage', 'model_definitions']
    originals = {n: pd.read_csv(OUT / f'phase6c_{n}.csv') for n in files}
    final = protocol['final_model']
    # Handle saved names from an early runner version without changing values.
    base = protocol['selected_factor_specification']['name']
    mask = forecasts.model.eq(base) & forecasts.evaluation_group.eq('HOLDOUT')
    forecasts.loc[mask, 'model'] = final
    dataset = load_dataset(ROOT)
    from audit import build_audit
    # Metadata correction only; reconstructed approved values must be identical.
    stored_panel = pd.read_csv(OUT / 'phase6c_research_monthly_panel.csv', index_col='date', parse_dates=True)
    rebuilt_panel, _ = build_audit(ROOT, dataset, OUT, save)
    pd.testing.assert_frame_equal(stored_panel, rebuilt_panel, check_names=False, check_freq=False, rtol=1e-12)
    panel = pd.read_csv(OUT / 'phase6c_research_monthly_panel.csv', index_col='date', parse_dates=True)
    events = pd.read_csv(ROOT / 'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    targets = pd.read_csv(ROOT / 'results/research/phase6b2/phase6b2_gdp_vintage_registry.csv').set_index('quarter')
    vintage = frozen_module('phase6c_finalize_vintage', 'scripts/research/phase6b2/vintages.py')
    exp = Experiment(panel, dataset.release_lag_days, events, targets, vintage)
    control = Spec('DFM-1_SHORT_HISTORY_CONTROL', tuple(protocol['long_core']), start='2021-01-31')
    if control.name not in forecasts.model.unique():
        exp.evaluate(control, protocol['development_origins'])
    selected = Spec(**{**protocol['selected_factor_specification'], 'fields': tuple(protocol['selected_factor_specification']['fields'])})
    no_fx = tuple(k for k in selected.fields if k not in ('usd_uzs', 'rub_uzs'))
    if no_fx != selected.fields and len(no_fx)>selected.factors and not forecasts.model.str.startswith('ROBUST_NO_FX').any():
        exp.evaluate(replace(selected, name='ROBUST_NO_FX', fields=no_fx), protocol['development_origins'],
                     bridges=(protocol['selected_bridge'],), aggregation=protocol['selected_aggregation'], modes=('standard',))
    if exp.forecasts:
        forecasts = pd.concat([forecasts, pd.DataFrame(exp.forecasts)], ignore_index=True)
        for name in files:
            saved = pd.read_csv(OUT / f'phase6c_{name}.csv')
            save(name, pd.concat([originals[name], saved], ignore_index=True).drop_duplicates())
    definitions = pd.read_csv(OUT / 'phase6c_model_definitions.csv')
    definitions['experiment_stage'] = np.where(definitions.bridges.str.contains(','), 'DFM-5_BRIDGE_COMPARISON',
                                              definitions.name.str.extract(r'(DFM-[0-4])', expand=False).fillna('ROBUSTNESS'))
    save('model_definitions', definitions)
    save('forecasts', forecasts)
    metrics = scores(forecasts)
    save('horizon_metrics', metrics)
    save('development_metrics', metrics.loc[metrics.evaluation_group.eq('DEVELOPMENT')])
    save('holdout_metrics', metrics.loc[metrics.evaluation_group.eq('HOLDOUT')])
    save('matched_metrics', pairwise(forecasts, final))
    errors = forecasts.assign(error=forecasts.actual-forecasts.prediction)
    save('quarter_level_errors', errors.assign(absolute_error=errors.error.abs(), squared_error=errors.error**2))
    robust = metrics.loc[metrics.model.str.startswith(('ROBUST_', 'ABLATE_'))]
    save('robustness', robust)
    save('block_ablation', robust.loc[robust.model.str.startswith('ABLATE_')])
    selection = pd.read_csv(OUT / 'phase6c_factor_selection.csv')
    block_choice = selection.loc[selection.stage.eq('BLOCK_SELECTION') & selection.horizon.eq('ALL')].sort_values(['rmse','model']).iloc[0].model
    protocol['selected_DFM2'] = block_choice
    # Sequential comparisons use pairwise identical origins and preserve both
    # full-available and matched scores in separate artifacts.
    stages = []
    for left, right, label in [('DFM-0', 'DFM-1', 'OLD_VS_LONG_CORE_COMPOSITION_CONFOUNDED'),
        ('DFM-1_SHORT_HISTORY_CONTROL', 'DFM-1', 'CONTROLLED_CORE_SAMPLE_LENGTH'),
        ('DFM-1', block_choice, 'BALANCED_BLOCK_DESIGN'), (block_choice, 'DFM-3', 'IDENTICAL_FIELDS_RAGGED_HISTORY')]:
        a = forecasts.loc[forecasts.model.eq(left)].dropna(subset=['prediction', 'actual'])
        b = forecasts.loc[forecasts.model.eq(right)].dropna(subset=['prediction', 'actual'])
        keys = a[KEYS].merge(b[KEYS], on=KEYS, validate='one_to_one')
        f = forecasts.loc[forecasts.model.isin([left,right])].merge(keys, on=KEYS, validate='many_to_one')
        if len(f):
            stages.append(scores(f, 'SEQUENTIAL_PAIRWISE_MATCHED').assign(experiment=label))
    save('sequential_matched_metrics', pd.concat(stages, ignore_index=True))
    checks = assert_protected(ROOT, before)
    report(OUT, protocol, pd.read_csv(OUT / 'phase6c_predictor_audit.csv'), forecasts, metrics, checks)
    assert sha(OUT / 'phase6c_selection_freeze.json') == freeze
    manifest_path = OUT / 'phase6c_run_manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else dict(
        status='RESEARCH_COMPLETE_WITH_DOCUMENTED_LIMITATIONS', recommendation='RESEARCH_ONLY', protected=checks,
        inputs={p: sha(ROOT / p) for p in ['data/master/v1_monthly.parquet', 'data/master/gdp_quarterly.parquet',
                'registry/uzbekistan_nowcasting_v1.2_registry.xlsx', 'results/research/phase6b2/phase6b2_gdp_revision_history.csv']})
    manifest['development_diagnostics_added_after_freeze_without_reselection'] = ['same_core_short_history', 'exclude_both_FX']
    manifest['selection_freeze_unchanged'] = True
    manifest['inputs'].update({p: sha(ROOT / p) for p in [
        'data/research/phase6a2/cbu_midas_monthly_panel.csv',
        'results/research/phase6a2/phase6a2_provenance.csv',
        'results/research/phase6b2/phase6b2_gdp_vintage_registry.csv',
        'results/research/phase6b2/phase6b2_forecasts.csv']})
    manifest['estimation_policy'] = dict(maxiter=500, EM_relative_likelihood_tolerance=1e-5,
        maximum_transition_spectral_radius=.9999, minimum_monthly_history=36,
        minimum_observations_per_predictor=12, missing_measurements='Kalman likelihood; not imputed observations')
    manifest['outputs'] = {p.name: sha(p) for p in OUT.glob('*.csv')}
    (OUT / 'phase6c_run_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    protocol.update(status='RESEARCH_COMPLETE_WITH_DOCUMENTED_LIMITATIONS', holdout_forecasts_evaluated=True,
                    recommendation='RESEARCH_ONLY')
    (OUT / 'phase6c_protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    (OUT / 'phase6c_protected_after.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')


if __name__ == '__main__':
    from kernel import KEYS
    main()
