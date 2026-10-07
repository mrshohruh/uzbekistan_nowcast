import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.statespace.dynamic_factor_mq import DynamicFactorMQ
from uznowcast.models.dfm import Spec,mask,standardize,training_panel,estimate,quarterly,bridge

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

def test_monthly_factor_aggregation_preserves_quarters():
    x = pd.DataFrame({0: [1., 2., 3., 4., 5.]}, index=pd.date_range('2024-01-31', periods=5, freq='ME'))
    assert quarterly(x).index.tolist() == [pd.Period('2024Q1')]
    assert quarterly(x).iloc[0, 0] == 2.
    assert quarterly(x, 'end').iloc[0, 0] == 3.

def test_missing_lag_fails_instead_of_guessing():
    x = panel()
    with pytest.raises(ValueError, match='undocumented_release_lag'):
        mask(x, Spec('test', tuple(x.columns)), '2024Q1', 'H1', {}, 'standard')
