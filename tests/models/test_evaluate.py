import numpy as np
import pandas as pd
import pytest

from uznowcast.models.evaluate import evaluate, summarize_predictions


def test_evaluate_produces_predictions_and_metrics(synthetic_dataset):
    result = evaluate(synthetic_dataset, horizons=('H3',), lag_modes=('standard',),
                       min_train=12, tiers=('B',))
    assert result['first_evaluation_quarter'] is not None
    predictions = result['predictions']
    assert predictions, 'evaluate should produce at least one prediction row'
    df = pd.DataFrame(predictions)
    for column in ('model', 'tier', 'horizon', 'lag_mode', 'target_quarter',
                    'prediction', 'actual', 'error'):
        assert column in df.columns
    # No prediction row should peek at future observations: any row whose
    # target quarter is later than the max training quarter in that split's
    # AR(1) benchmark must be strictly after every training quarter.
    ar1_rows = df.loc[df.model == 'ar1']
    for _, row in ar1_rows.iterrows():
        assert row['target_quarter'] > result['windows'][
            [w['target_quarter'] for w in result['windows']].index(row['target_quarter'])]['first_train_quarter']


def test_summarize_predictions_adds_relative_metrics(synthetic_dataset):
    result = evaluate(synthetic_dataset, horizons=('H1',), lag_modes=('standard',),
                       min_train=12, tiers=('B',))
    metrics = summarize_predictions(result['predictions'])
    ar1_row = metrics.loc[metrics.model == 'ar1'].iloc[0]
    assert ar1_row['rmse_relative_to_ar1'] == pytest.approx(1.0)
    assert ar1_row['mae_relative_to_ar1'] == pytest.approx(1.0)


def test_evaluate_reproducible(synthetic_dataset):
    r1 = evaluate(synthetic_dataset, horizons=('H2',), lag_modes=('standard',),
                   min_train=12, tiers=('B',))
    r2 = evaluate(synthetic_dataset, horizons=('H2',), lag_modes=('standard',),
                   min_train=12, tiers=('B',))
    preds1 = pd.DataFrame(r1['predictions']).sort_values(['model', 'target_quarter']).reset_index(drop=True)
    preds2 = pd.DataFrame(r2['predictions']).sort_values(['model', 'target_quarter']).reset_index(drop=True)
    pd.testing.assert_frame_equal(preds1, preds2)
