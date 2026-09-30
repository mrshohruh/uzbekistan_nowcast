"""Phase 4B candidate-freeze and holdout-isolation regression tests."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from uznowcast.models.dfm import DFMSpec
from uznowcast.models.ensemble import (
    AR2_WEIGHT, UMIDAS_USD_WEIGHT, fixed_ar2_usd_ensemble,
)
from uznowcast.models.phase4b import (
    EXPECTED_HOLDOUT, _candidate_freeze_payload, _read_development_gdp,
    development_metrics, write_phase4b_results,
)


def _prediction(model: str, quarter: str, prediction: float, actual: float,
                *, horizon: str = 'H3', lag_mode: str = 'standard') -> dict:
    return dict(
        model=model, tier='none', horizon=horizon, lag_mode=lag_mode,
        target_quarter=quarter, n_train=15, prediction=prediction,
        actual=actual, error=actual - prediction, failure=None,
        candidate_role='primary',
    )


def test_fixed_equal_weight_ensemble_calculation_and_weight():
    frame = pd.DataFrame([
        _prediction('ar2', '2024Q1', 4.0, 6.0),
        _prediction('umidas_usd_uzs_mom_dlog', '2024Q1', 8.0, 6.0),
    ])
    result = fixed_ar2_usd_ensemble(frame).iloc[0]
    assert AR2_WEIGHT == 0.5
    assert UMIDAS_USD_WEIGHT == 0.5
    assert result['prediction'] == pytest.approx(6.0)
    assert result['ensemble_weight_ar2'] == pytest.approx(0.5)
    assert result['ensemble_weight_umidas_usd'] == pytest.approx(0.5)


def test_development_metrics_matches_both_ar1_and_ar2():
    frame = pd.DataFrame([
        _prediction('ar1', '2024Q1', 4.0, 5.0),
        _prediction('ar1', '2024Q2', 4.0, 6.0),
        _prediction('ar1', '2024Q3', 4.0, 7.0),
        _prediction('ar2', '2024Q1', 4.5, 5.0),
        _prediction('ar2', '2024Q2', 5.0, 6.0),
        _prediction('ar2', '2024Q3', 5.5, 7.0),
        _prediction('challenger', '2024Q2', 5.5, 6.0),
        _prediction('challenger', '2024Q3', 6.0, 7.0),
    ])
    row = development_metrics(frame).loc[
        lambda x: x['model'] == 'challenger'].iloc[0]
    assert row['N'] == 2
    assert row['matched_ar1_rmse'] == pytest.approx(np.sqrt((2 ** 2 + 3 ** 2) / 2))
    assert row['matched_ar2_rmse'] == pytest.approx(np.sqrt((1 ** 2 + 1.5 ** 2) / 2))


def test_development_gdp_reader_never_reads_holdout_outcomes(monkeypatch):
    development = ('2025Q1', '2025Q2')
    quarters = list(development + EXPECTED_HOLDOUT)
    calls: list[dict] = []

    def audited_read(*args, **kwargs):
        calls.append(dict(kwargs))
        if kwargs['columns'] == ['quarter']:
            return pd.DataFrame({'quarter': quarters})
        assert kwargs['filters'] == [('quarter', 'in', list(development))]
        # The reader exposes only development values. Frozen sentinel values
        # never enter the returned frame.
        return pd.DataFrame({
            'quarter': list(development),
            'gdp_real_yoy_pct': [5.0, 6.0],
        })

    monkeypatch.setattr(pd, 'read_parquet', audited_read)
    result = _read_development_gdp(
        Path('gdp.parquet'), development_quarters=development,
        holdout_quarters=EXPECTED_HOLDOUT)
    assert result['quarter'].tolist() == list(development)
    assert result['gdp_real_yoy_pct'].tolist() == [5.0, 6.0]
    assert calls[0]['columns'] == ['quarter']
    assert calls[1]['columns'] == ['quarter', 'gdp_real_yoy_pct']
    assert calls[1]['filters'] == [('quarter', 'in', list(development))]


def _minimal_results() -> dict:
    frozen = {
        'development_quarters': ['2025Q1', '2025Q2'],
        'holdout_quarters': list(EXPECTED_HOLDOUT),
        'master_fingerprint': {
            'monthly_sha256': 'm', 'quarterly_sha256': 'q',
            'registry_sha256': 'r',
        },
    }
    empty = pd.DataFrame()
    spec = DFMSpec(name='dfm_tierA_k1', fields=('a', 'b'))
    return {
        'frozen': frozen,
        'specs': (spec,),
        'predictions': empty,
        'development_metrics': empty,
        'horizon_updates': empty,
        'ensemble_diagnostics': empty,
        'dfm_diagnostics': empty,
        'dfm_field_resolution': empty,
        'dfm_factor_loadings': empty,
        'dfm_tolerance_sensitivity': empty,
        'dfm_decision': {'selected_dfm': None, 'gate': {}, 'assessments': []},
    }


def test_candidate_freeze_declares_unopened_holdout():
    payload = _candidate_freeze_payload(_minimal_results())
    assert payload['holdout_outcomes_used'] is False
    assert payload['holdout_quarters'] == list(EXPECTED_HOLDOUT)
    assert payload['development_period_endpoint'] == '2025Q2'
    assert payload['primary_candidate_models'] == [
        'ar1', 'ar2', 'umidas_usd_uzs_mom_dlog',
        'ensemble_ar2_umidas_usd',
    ]


def test_candidate_freeze_is_the_last_selection_artifact_written(monkeypatch):
    from uznowcast.models import phase4b
    events: list[str] = []

    def record_table(frame, path):
        events.append(path.name)

    def record_json(path, payload):
        events.append(path.name)

    monkeypatch.setattr(phase4b, '_write_table', record_table)
    monkeypatch.setattr(phase4b, 'save_json', record_json)
    write_phase4b_results(Path.cwd(), _minimal_results())
    assert events[-1] == 'phase4b_candidate_freeze.json'
