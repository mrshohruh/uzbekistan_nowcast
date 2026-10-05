"""No network calls. Test the research boundary and reconstruct saved evidence."""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.statespace.dynamic_factor_mq import DynamicFactorMQ

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(Path(__file__).parent))
from kernel import (Spec, mask, standardize, training_panel, estimate, scores, select,
                    development_only, quarterly, bridge, KEYS)
from audit import assert_protected


def panel():
    rng = np.random.default_rng(611)
    x = pd.DataFrame(rng.normal(size=(90, 5)), index=pd.date_range('2019-01-31', periods=90, freq='ME'), columns=list('abcde'))
    x.loc[:'2020-12-31', 'e'] = np.nan
    x.loc['2022-03-31', 'a'] = np.nan
    return x


def test_future_observations_and_unreleased_values_do_not_change_mask_or_scaling():
    x = panel(); spec = Spec('test', tuple(x.columns)); lags = dict.fromkeys(x.columns, 30)
    a, audit = mask(x, spec, '2024Q1', 'H1', lags, 'standard')
    y = x.copy(); y.loc['2024-01-31':] = 1e12
    b, _ = mask(y, spec, '2024Q1', 'H1', lags, 'standard')
    pd.testing.assert_frame_equal(a, b)
    za, ma, sa = standardize(a, pd.Timestamp('2023-12-31'))
    zb, mb, sb = standardize(b, pd.Timestamp('2023-12-31'))
    pd.testing.assert_frame_equal(za, zb)
    pd.testing.assert_series_equal(ma, mb); pd.testing.assert_series_equal(sa, sb)
    assert all(r['latest_usable_observation'] <= r['cutoff'] <= r['origin'] for r in audit)


def test_later_starting_variable_does_not_truncate_ragged_sample():
    x = panel()
    frame, train = training_panel(x, pd.Timestamp('2023-12-31'), False)
    assert len(train) == 60 and frame.index.min() == pd.Timestamp('2019-01-31')
    assert train['e'].iloc[:24].isna().all()
    _, balanced = training_panel(x, pd.Timestamp('2023-12-31'), True)
    assert len(balanced) == 36
    assert pd.isna(balanced.loc['2022-03-31', 'a'])


@pytest.mark.parametrize('r', [1, 2, 3])
@pytest.mark.parametrize('order', [1, 2])
def test_state_dimensions_and_arbitrary_missing_filter(r, order):
    x = panel(); z, _, _ = standardize(x, pd.Timestamp('2023-12-31'))
    model = DynamicFactorMQ(z, factors=r, factor_orders=order, standardize=False, idiosyncratic_ar1=False)
    assert model.k_states == r * order
    result = model.filter(model.start_params)
    assert result.factors.filtered.shape == (len(z), r)
    assert np.isfinite(result.factors.filtered.to_numpy()).all()
    assert np.isnan(model.endog[:24, -1]).all()
    assert model.nobs == 90


def test_future_data_cannot_change_historical_factors():
    x = panel(); spec = Spec('test', tuple(x.columns)); lags = dict.fromkeys(x.columns, 30)
    a, _ = mask(x, spec, '2024Q1', 'H1', lags, 'standard')
    y = x.copy(); y.loc['2024-01-31':] = -1e9
    b, _ = mask(y, spec, '2024Q1', 'H1', lags, 'standard')
    za, _, _ = standardize(a, pd.Timestamp('2023-12-31'))
    zb, _, _ = standardize(b, pd.Timestamp('2023-12-31'))
    m = DynamicFactorMQ(za, factors=2, standardize=False, idiosyncratic_ar1=False)
    states1 = m.filter(m.start_params).factors.filtered
    states2 = m.clone(zb).filter(m.start_params).factors.filtered
    pd.testing.assert_frame_equal(states1, states2)


def test_em_rerun_is_deterministic():
    rng = np.random.default_rng(32)
    f = np.zeros(100)
    for i in range(1, 100):
        f[i] = .65*f[i-1] + rng.normal()
    x = pd.DataFrame(f[:, None]*np.array([1., .7, -.5, .8]) + rng.normal(scale=.5, size=(100,4)),
                     index=pd.date_range('2019-01-31', periods=100, freq='ME'), columns=list('abcd'))
    x.loc[:'2020-12-31', 'd'] = np.nan
    z, _, _ = standardize(x, pd.Timestamp('2026-12-31'))
    a, la, da = estimate(z, z, Spec('test', tuple(x.columns)))
    b, lb, db = estimate(z, z, Spec('test', tuple(x.columns)))
    np.testing.assert_allclose(a, b, atol=1e-10)
    np.testing.assert_allclose(la, lb, atol=1e-10)
    assert da['n_training_months'] == 100


def forecast_fixture():
    rows = []
    for model, error in [('good', .1), ('bad', 1.)]:
        for q in pd.period_range('2023Q1', '2026Q2', freq='Q'):
            for h in ('H1', 'H2', 'H3'):
                rows.append(dict(model=model, target_quarter=str(q), horizon=h, lag_mode='standard', timing_rule='STRICT',
                    prediction=6+error, actual=6., evaluation_group='HOLDOUT' if str(q)>='2025Q3' else 'DEVELOPMENT'))
    return pd.DataFrame(rows)


def test_holdout_cannot_change_selection():
    x = forecast_fixture()
    first, _ = select(x, ['good', 'bad'])
    x.loc[x.target_quarter.ge('2025Q3') & x.model.eq('good'), 'prediction'] = 1e9
    x.loc[x.target_quarter.ge('2025Q3'), 'actual'] = -1e9
    second, _ = select(x, ['good', 'bad'])
    assert first == second == 'good'
    assert development_only(x).target_quarter.lt('2025Q3').all()


def test_development_outcomes_released_after_freeze_are_excluded():
    x = forecast_fixture()
    x['outcome_release_date'] = '2025-08-15'
    assert development_only(x).empty


def test_monthly_factor_aggregation_preserves_quarters():
    x = pd.DataFrame({0: [1., 2., 3., 4., 5.]}, index=pd.date_range('2024-01-31', periods=5, freq='ME'))
    assert quarterly(x).index.tolist() == [pd.Period('2024Q1')]
    assert quarterly(x).iloc[0, 0] == 2.
    assert quarterly(x, 'end').iloc[0, 0] == 3.


def test_missing_lag_fails_instead_of_guessing():
    x = panel()
    with pytest.raises(ValueError, match='undocumented_release_lag'):
        mask(x, Spec('test', tuple(x.columns)), '2024Q1', 'H1', {}, 'standard')


def test_gdp_accessor_excludes_same_day_future_and_unverified_values():
    spec = importlib.util.spec_from_file_location('phase6c_test_vintage', ROOT / 'scripts/research/phase6b2/vintages.py')
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    events = pd.read_csv(ROOT / 'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    available = module.available_gdp_vintage_as_of(events, pd.Timestamp('2025-07-28'), target='2025Q3')
    assert '2025Q2' not in available.frame.index
    assert available.frame.index.to_series().lt('2025Q3').all()
    assert pd.to_datetime(available.frame.publication_date).lt(pd.Timestamp('2025-07-28')).all()


def test_protected_inventory_and_saved_metrics():
    out = ROOT / 'results/phase6c'
    before = json.loads((out / 'phase6c_protected_before.json').read_text())
    assert_protected(ROOT, before)
    if not (out / 'phase6c_forecasts.csv').exists():
        pytest.skip('Full research run has not finished')
    forecasts = pd.read_csv(out / 'phase6c_forecasts.csv')
    assert not forecasts.duplicated(['model'] + KEYS).any()
    calculated = scores(forecasts)
    saved = pd.read_csv(out / 'phase6c_horizon_metrics.csv')
    columns = ['model', 'lag_mode', 'timing_rule', 'evaluation_group', 'horizon']
    joined = calculated.merge(saved, on=columns, suffixes=('_new', '_saved'), validate='one_to_one')
    for metric in ['rmse', 'mae', 'bias', 'median_absolute_error', 'n']:
        np.testing.assert_allclose(joined[metric+'_new'], joined[metric+'_saved'], atol=1e-10, equal_nan=True)
    matched = pd.read_csv(out / 'phase6c_matched_metrics.csv')
    final = json.loads((out / 'phase6c_selection_freeze.json').read_text())['final_model']
    for comparison in matched.comparison.unique():
        a = forecasts.loc[forecasts.model.eq(final)].dropna(subset=['prediction', 'actual'])
        b = forecasts.loc[forecasts.model.eq(comparison)].dropna(subset=['prediction', 'actual'])
        keys = a[KEYS].merge(b[KEYS], on=KEYS, validate='one_to_one')
        subset = forecasts.loc[forecasts.model.isin([final, comparison])].merge(keys, on=KEYS)
        rebuilt = scores(subset, 'PAIRWISE_COMMON_WITH_FINAL')
        saved_pair = matched.loc[matched.comparison.eq(comparison)]
        joined = rebuilt.merge(saved_pair, on=columns, suffixes=('_new', '_saved'), validate='one_to_one')
        np.testing.assert_allclose(joined.rmse_new, joined.rmse_saved, atol=1e-10, equal_nan=True)


def test_saved_information_and_gdp_boundaries():
    out = ROOT / 'results/phase6c'
    information = pd.read_csv(out / 'phase6c_information_set_audit.csv')
    assert (information.latest_usable_observation.isna() | pd.to_datetime(information.latest_usable_observation).le(pd.to_datetime(information.cutoff))).all()
    assert pd.to_datetime(information.cutoff).le(pd.to_datetime(information.origin)).all()
    usage = pd.read_csv(out / 'phase6c_GDP_training_vintage_usage.csv')
    assert usage.GDP_quarter.lt(usage.target_quarter).all()
    assert pd.to_datetime(usage.publication_date).lt(pd.to_datetime(usage.origin)).all()


def test_frozen_dfm0_and_benchmarks_have_identical_saved_predictions():
    out = ROOT / 'results/phase6c'
    if not (out / 'phase6c_forecasts.csv').exists():
        pytest.skip('Full research run has not finished')
    original = pd.read_csv(ROOT / 'results/research/phase6b2/phase6b2_forecasts.csv')
    original = original.loc[original.timing_rule.eq('STRICT')].copy()
    original['model'] = original.model.replace({'DFM_A':'DFM-0','DFM_B':'PHASE6B2_DFM_B',
                                                'COMBO_A':'PHASE6B2_COMBO_A','COMBO_B':'PHASE6B2_COMBO_B'})
    saved = pd.read_csv(out / 'phase6c_forecasts.csv')
    joined = original.merge(saved, on=['model'] + KEYS, suffixes=('_old','_new'), validate='one_to_one')
    assert len(joined) == len(original)
    np.testing.assert_allclose(joined.prediction_old, joined.prediction_new, rtol=0, atol=1e-12, equal_nan=True)


def test_recovered_pos_scope_and_research_labels():
    out = ROOT / 'results/phase6c'
    data = pd.read_csv(out / 'phase6c_research_monthly_panel.csv', index_col='date', parse_dates=True)
    assert data.loc['2025-01-31':, 'pos_turnover'].isna().all()
    assert data.loc['2019-01-31':'2024-12-31', 'pos_turnover'].notna().all()
    audit = pd.read_csv(out / 'phase6c_predictor_audit.csv').set_index('variable')
    assert 'research-only deviation' in audit.loc['industrial_production','transformation']


def test_factor_bridge_freeze_is_development_only():
    out = ROOT / 'results/phase6c'
    if not (out / 'phase6c_selection_freeze.json').exists():
        pytest.skip('Selection has not finished')
    protocol = json.loads((out / 'phase6c_selection_freeze.json').read_text())
    assert not protocol['holdout_forecasts_evaluated']
    assert all(q<'2025Q3' for q,h in protocol['development_origins'])
    selection = pd.read_csv(out / 'phase6c_factor_selection.csv')
    assert selection.evaluation_group.eq('DEVELOPMENT').all()
    assert protocol['selected_factor_specification']['factors'] in (1,2,3)
