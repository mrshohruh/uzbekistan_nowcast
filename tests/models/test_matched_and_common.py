"""Matched-quarter benchmarks and common-sample comparison tables."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from uznowcast.models.matched import (
    common_sample_metrics, horizon_delta_report, lag_mode_delta, matched_metrics,
)


def _predictions_frame():
    return pd.DataFrame([
        # AR(1) has all four quarters at both horizons/modes
        dict(model='ar1', tier='none', horizon='H1', lag_mode='standard',
             target_quarter='2020-Q1', prediction=5.0, actual=6.0, error=1.0),
        dict(model='ar1', tier='none', horizon='H1', lag_mode='standard',
             target_quarter='2020-Q2', prediction=6.0, actual=5.0, error=-1.0),
        dict(model='ar1', tier='none', horizon='H1', lag_mode='standard',
             target_quarter='2020-Q3', prediction=5.5, actual=7.5, error=2.0),
        dict(model='ar1', tier='none', horizon='H1', lag_mode='standard',
             target_quarter='2020-Q4', prediction=6.0, actual=6.0, error=0.0),
        # Bridge only predicted the last two quarters
        dict(model='bridge_x', tier='B', horizon='H1', lag_mode='standard',
             target_quarter='2020-Q1', prediction=np.nan, actual=6.0, error=np.nan,
             failure='bridge training frame is empty after dropping NaNs'),
        dict(model='bridge_x', tier='B', horizon='H1', lag_mode='standard',
             target_quarter='2020-Q2', prediction=np.nan, actual=5.0, error=np.nan,
             failure='bridge training frame is empty after dropping NaNs'),
        dict(model='bridge_x', tier='B', horizon='H1', lag_mode='standard',
             target_quarter='2020-Q3', prediction=6.0, actual=7.5, error=1.5),
        dict(model='bridge_x', tier='B', horizon='H1', lag_mode='standard',
             target_quarter='2020-Q4', prediction=6.5, actual=6.0, error=-0.5),
    ])


def test_matched_metrics_uses_challenger_quarters():
    frame = _predictions_frame()
    matched = matched_metrics(frame)
    bridge = matched.loc[matched['model'] == 'bridge_x'].iloc[0]
    assert bridge['n_matched_forecasts'] == 2
    assert bridge['comparison_first_quarter'] == '2020-Q3'
    assert bridge['comparison_last_quarter'] == '2020-Q4'
    # AR(1) matched RMSE must be computed only on 2020-Q3/Q4 errors.
    expected_ar_rmse = np.sqrt(((2.0 ** 2) + (0.0 ** 2)) / 2)
    assert bridge['matched_ar1_rmse'] == pytest.approx(expected_ar_rmse)
    challenger_rmse = np.sqrt(((1.5 ** 2) + (0.5 ** 2)) / 2)
    assert bridge['challenger_rmse'] == pytest.approx(challenger_rmse)
    assert bridge['matched_relative_rmse'] == pytest.approx(
        challenger_rmse / expected_ar_rmse)


def test_matched_metrics_ar1_row_is_trivially_relative_one():
    frame = _predictions_frame()
    matched = matched_metrics(frame)
    ar_row = matched.loc[matched['model'] == 'ar1'].iloc[0]
    assert ar_row['matched_relative_rmse'] == pytest.approx(1.0)
    assert ar_row['matched_relative_mae'] == pytest.approx(1.0)


def test_matched_quarter_arrays_identical():
    """Regression guard: the challenger and its matched AR(1) benchmark must
    be computed over the exact same target-quarter list, per Phase 4A.1 §4.
    """
    frame = _predictions_frame()
    bridge_quarters = frame.loc[(frame['model'] == 'bridge_x')
                                 & frame['prediction'].notna(),
                                 'target_quarter'].tolist()
    matched = matched_metrics(frame)
    row = matched.loc[matched['model'] == 'bridge_x'].iloc[0]
    # The comparison span in the metrics row must equal the challenger's
    # min/max valid quarters exactly.
    assert row['comparison_first_quarter'] == min(bridge_quarters)
    assert row['comparison_last_quarter'] == max(bridge_quarters)


def test_common_sample_metrics_uses_intersection():
    frame = _predictions_frame()
    common = common_sample_metrics(frame, {'AR_vs_TierB': ['ar1', 'bridge_x']})
    ar1 = common.loc[common['model'] == 'ar1'].iloc[0]
    bridge = common.loc[common['model'] == 'bridge_x'].iloc[0]
    # Both models must be evaluated on the 2-quarter intersection.
    assert ar1['n_common'] == 2 == bridge['n_common']
    assert ar1['common_first_quarter'] == '2020-Q3'
    assert bridge['common_first_quarter'] == '2020-Q3'
    # AR(1) RMSE on the common sample = sqrt((2^2 + 0^2)/2) = sqrt(2)
    assert ar1['rmse'] == pytest.approx(np.sqrt(2.0))
    # Bridge RMSE on the same two quarters = sqrt((1.5^2 + 0.5^2)/2) = sqrt(1.25)
    assert bridge['rmse'] == pytest.approx(np.sqrt(1.25))
    # Relative-to-AR(1) is exactly bridge_rmse / ar1_rmse on the intersection.
    assert bridge['rmse_relative_to_ar1'] == pytest.approx(bridge['rmse'] / ar1['rmse'])


def test_horizon_delta_report_counts_disagreements():
    frame = pd.DataFrame([
        dict(model='m', tier='B', horizon='H1', lag_mode='standard',
             target_quarter='2020-Q1', prediction=5.0),
        dict(model='m', tier='B', horizon='H2', lag_mode='standard',
             target_quarter='2020-Q1', prediction=5.0),
        dict(model='m', tier='B', horizon='H3', lag_mode='standard',
             target_quarter='2020-Q1', prediction=5.5),
        dict(model='m', tier='B', horizon='H1', lag_mode='standard',
             target_quarter='2020-Q2', prediction=4.0),
        dict(model='m', tier='B', horizon='H2', lag_mode='standard',
             target_quarter='2020-Q2', prediction=4.2),
        dict(model='m', tier='B', horizon='H3', lag_mode='standard',
             target_quarter='2020-Q2', prediction=4.4),
    ])
    report = horizon_delta_report(frame)
    row = report.iloc[0]
    assert row['n_H1_and_H2'] == 2
    assert row['share_H1_ne_H2'] == pytest.approx(0.5)
    assert row['share_H2_ne_H3'] == pytest.approx(1.0)
    assert row['share_H1_ne_H3'] == pytest.approx(1.0)


def test_lag_mode_delta_computes_forecasts_lost():
    matched = pd.DataFrame([
        dict(model='m', tier='B', horizon='H1', lag_mode='standard',
             challenger_rmse=1.0, challenger_mae=0.5, challenger_bias=0.0,
             n_matched_forecasts=10),
        dict(model='m', tier='B', horizon='H1', lag_mode='conservative',
             challenger_rmse=1.3, challenger_mae=0.7, challenger_bias=0.0,
             n_matched_forecasts=7),
    ])
    delta = lag_mode_delta(matched)
    row = delta.iloc[0]
    assert row['delta_rmse'] == pytest.approx(0.3)
    assert row['forecasts_lost_under_conservative'] == 3
