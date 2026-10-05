"""Repeat one actual development fit; no holdout rerun or model reselection."""
import json

import numpy as np
import pandas as pd

from run import ROOT, OUT, load_dataset, frozen_module, sha
from kernel import Spec, mask, training_panel, standardize, estimate, bridge
from uznowcast.models.data import horizon_month_end, quarter_start, quarter_end
from audit import assert_protected


def main():
    protocol = json.loads((OUT / 'phase6c_selection_freeze.json').read_text())
    s = protocol['selected_factor_specification']
    spec = Spec(**{**s, 'fields': tuple(s['fields'])})
    origin_table = pd.read_csv(OUT / 'phase6c_forecasts.csv')
    origin_table = origin_table.loc[origin_table.model.eq(protocol['final_model']) & origin_table.evaluation_group.eq('DEVELOPMENT') &
                                   origin_table.horizon.eq('H3') & origin_table.lag_mode.eq('standard') & origin_table.prediction.notna()]
    target = origin_table.target_quarter.max()
    original = origin_table.loc[origin_table.target_quarter.eq(target)].iloc[0].prediction
    dataset = load_dataset(ROOT)
    panel = pd.read_csv(OUT / 'phase6c_research_monthly_panel.csv', index_col='date', parse_dates=True)
    x, _ = mask(panel, spec, target, 'H3', dataset.release_lag_days, 'standard')
    end = quarter_start(target) - pd.Timedelta(days=1)
    x, _ = training_panel(x, end, spec.balanced)
    z, _, _ = standardize(x, end, spec.winsor)
    z = z.reindex(pd.date_range(z.index.min(), quarter_end(target), freq='ME'))
    factors, loadings, diagnostics = estimate(z.loc[:end], z, spec)
    saved = pd.read_csv(OUT / 'phase6c_factor_series.csv')
    saved = saved.loc[saved.specification.eq(spec.name) & saved.target_quarter.eq(target) & saved.horizon.eq('H3') & saved.lag_mode.eq('standard')]
    states = saved.pivot(index='month', columns='factor', values='value').to_numpy()
    maximum_factor_difference = float(np.max(abs(states - factors.to_numpy())))
    events = pd.read_csv(ROOT / 'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    vintage = frozen_module('phase6c_verify_vintage', 'scripts/research/phase6b2/vintages.py')
    origin = horizon_month_end(target, 'H3')
    available = vintage.available_gdp_vintage_as_of(events, origin, target=target)
    prediction, _ = bridge(factors, available, target, origin, protocol['selected_bridge'], protocol['selected_aggregation'])
    delta = float(abs(prediction - original))
    assert maximum_factor_difference < 1e-8
    assert delta < 1e-8
    checks = assert_protected(ROOT, json.loads((OUT / 'phase6c_protected_before.json').read_text()))
    result = dict(target_quarter=target, horizon='H3', lag_mode='standard', maximum_factor_difference=maximum_factor_difference,
                  maximum_forecast_difference=delta, tolerance=1e-8, deterministic=True, protected=checks,
                  holdout_reevaluated=False, selection_freeze_sha256=sha(OUT / 'phase6c_selection_freeze.json'))
    (OUT / 'phase6c_determinism_checks.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
