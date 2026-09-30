"""Pre-specified Phase 4B forecast combination utilities."""
from __future__ import annotations

import numpy as np
import pandas as pd


ENSEMBLE_NAME = 'ensemble_ar2_umidas_usd'
AR2_WEIGHT = 0.5
UMIDAS_USD_WEIGHT = 0.5


def fixed_ar2_usd_ensemble(predictions: pd.DataFrame) -> pd.DataFrame:
    """Return the frozen 50/50 AR(2) + USD U-MIDAS prediction rows.

    No weight argument is exposed intentionally: Phase 4B pre-specifies
    equal weights and forbids holdout-driven weight optimization.
    """
    keys = ['target_quarter', 'horizon', 'lag_mode']
    ar2 = predictions.loc[predictions['model'] == 'ar2',
                          keys + ['prediction', 'actual', 'n_train']].copy()
    usd = predictions.loc[predictions['model'] == 'umidas_usd_uzs_mom_dlog',
                          keys + ['prediction', 'actual', 'n_train']].copy()
    ar2 = ar2.rename(columns={
        'prediction': 'ar2_component_prediction',
        'actual': 'ar2_actual',
        'n_train': 'ar2_n_train',
    })
    usd = usd.rename(columns={
        'prediction': 'umidas_usd_component_prediction',
        'actual': 'umidas_actual',
        'n_train': 'umidas_n_train',
    })
    merged = ar2.merge(usd, on=keys, how='inner', validate='one_to_one')
    valid = (merged['ar2_component_prediction'].notna()
             & merged['umidas_usd_component_prediction'].notna())
    merged['prediction'] = np.where(
        valid,
        AR2_WEIGHT * merged['ar2_component_prediction']
        + UMIDAS_USD_WEIGHT * merged['umidas_usd_component_prediction'],
        np.nan,
    )
    merged['actual'] = merged['ar2_actual']
    inconsistent = (merged['ar2_actual'].notna() & merged['umidas_actual'].notna()
                    & (merged['ar2_actual'] != merged['umidas_actual']))
    if inconsistent.any():
        raise ValueError('Ensemble components carry inconsistent actual values')
    merged['error'] = merged['actual'] - merged['prediction']
    merged['model'] = ENSEMBLE_NAME
    merged['tier'] = 'A'
    merged['n_train'] = merged[['ar2_n_train', 'umidas_n_train']].min(axis=1)
    merged['failure'] = np.where(valid, None, 'missing_component_prediction')
    merged['candidate_role'] = 'primary'
    merged['ensemble_weight_ar2'] = AR2_WEIGHT
    merged['ensemble_weight_umidas_usd'] = UMIDAS_USD_WEIGHT
    return merged[[
        'model', 'tier', 'horizon', 'lag_mode', 'target_quarter',
        'n_train', 'prediction', 'actual', 'error', 'failure',
        'candidate_role', 'ar2_component_prediction',
        'umidas_usd_component_prediction', 'ensemble_weight_ar2',
        'ensemble_weight_umidas_usd',
    ]]

