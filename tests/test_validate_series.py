import numpy as np
import pandas as pd
import pytest

from uznowcast.validation.observations import _parse_registry_period, validate_series


def test_parse_plain_monthly_token():
    assert _parse_registry_period('2021-M01', 'M') == pd.Period('2021-01', freq='M')


def test_parse_monthly_token_with_annotation():
    got = _parse_registry_period('2022-M10 (verified same-schema archive)', 'M')
    assert got == pd.Period('2022-10', freq='M')


def test_parse_monthly_token_release_family_suffix():
    got = _parse_registry_period('2026-M08 release family', 'M')
    assert got == pd.Period('2026-08', freq='M')


def test_parse_quarterly_token_with_annotation():
    got = _parse_registry_period('2026-Q2 (preliminary)', 'Q')
    assert got == pd.Period('2026Q2', freq='Q')


def test_parse_rejects_ambiguous_native_freq():
    with pytest.raises(ValueError):
        _parse_registry_period('2026-Q2', 'M')


def _frame(months, raw, monthly_flow, freq='M'):
    dates = pd.to_datetime(months)
    return pd.DataFrame({
        'reference_period': [d.strftime('%Y-%m') for d in dates],
        'reference_date': dates,
        'frequency': freq,
        'raw_value': raw,
        'clean_value': [np.nan] * len(dates),
        'monthly_flow': monthly_flow,
        'quality_flag': [''] * len(dates),
    })


def _row(**overrides):
    row = dict(
        variable_key='dummy',
        native_frequency='Monthly',
        verified_start='2024-M01',
        verified_end='current',
        structural_breaks_caveats='',
    )
    row.update(overrides)
    return row


def test_reconciliation_skipped_when_raw_equals_monthly_flow():
    months = [f'2024-{m:02d}-{28 if m == 2 else 30}' for m in range(1, 13)]
    values = list(range(10, 22))
    frame = _frame(months, values, values)
    result = validate_series(frame, _row())
    assert result['annual_reconciliation'] == []


def test_reconciliation_enforced_when_ytd_and_flow_diverge():
    months = [f'2024-{m:02d}-{28 if m == 2 else 30}' for m in range(1, 13)]
    flows = [10] * 12
    ytd = list(np.cumsum(flows))
    frame = _frame(months, ytd, flows)
    result = validate_series(frame, _row())
    assert result['annual_reconciliation'] and result['annual_reconciliation'][0]['passed']


def test_reconciliation_reports_broken_ytd():
    months = [f'2024-{m:02d}-{28 if m == 2 else 30}' for m in range(1, 13)]
    flows = [10] * 12
    ytd = list(np.cumsum(flows))
    ytd[-1] += 5  # break December-YTD reconciliation
    frame = _frame(months, ytd, flows)
    with pytest.raises(ValueError, match='reconcile'):
        validate_series(frame, _row())
