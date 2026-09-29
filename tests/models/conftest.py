"""Synthetic dataset builders for Phase 4A model tests.

The tests never touch live sources or the frozen master parquets. They
construct small pandas frames that mimic the ``ModelingDataset`` shape:

- ``gdp`` — quarterly frame with columns ``quarter`` and ``gdp_real_yoy_pct``.
- ``monthly`` — monthly index (calendar month-end) × predictor columns.
- ``registry`` — minimal stand-in with ``rows`` and ``clean_field_by_key``.

That is enough to exercise the leakage guards, the horizon information sets,
the expanding-window splits, and every model family without a filesystem.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Iterable

import numpy as np
import pandas as pd
import pytest

from uznowcast.models.data import ModelingDataset


def _quarter_labels(start_year: int, n: int) -> list[str]:
    labels = []
    year, q = start_year, 1
    for _ in range(n):
        labels.append(f'{year}-Q{q}')
        q += 1
        if q > 4:
            q, year = 1, year + 1
    return labels


def make_gdp_frame(start_year: int = 2018, n_quarters: int = 34, seed: int = 20260929) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    quarters = _quarter_labels(start_year, n_quarters)
    values = 5.0 + rng.normal(0.0, 1.0, size=n_quarters)
    return pd.DataFrame(dict(quarter=quarters, gdp_real_yoy_pct=values))


def make_monthly_panel(start_year: int = 2018, n_months: int = 102,
                       fields: Iterable[str] = ('field_a', 'field_b', 'field_c'),
                       seed: int = 20260929, missing: dict[str, int] | None = None
                       ) -> pd.DataFrame:
    """Build a synthetic monthly panel with month-end dates."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp(year=start_year, month=1, day=1)
    dates = pd.date_range(start=start + pd.offsets.MonthEnd(0), periods=n_months, freq='ME')
    fields = list(fields)
    frame = pd.DataFrame(rng.normal(0, 1, size=(n_months, len(fields))),
                          index=dates, columns=fields)
    if missing:
        for column, tail in missing.items():
            if column in frame:
                frame.iloc[-tail:, frame.columns.get_loc(column)] = np.nan
    frame.index.name = 'date'
    return frame


def make_registry_stub(clean_field_by_key: dict[str, str],
                       release_lag_days: dict[str, int] | None = None):
    release_lag_days = release_lag_days or {key: 30 for key in clean_field_by_key}
    rows = {key: dict(variable_key=key, clean_model_field=field,
                      typical_publication_lag_days=release_lag_days[key],
                      provider='synthetic', native_frequency='Monthly')
            for key, field in clean_field_by_key.items()}
    return SimpleNamespace(rows=rows, scope=lambda name: list(rows.values()),
                            version='V1.2', verification_date='2026-09-29')


@pytest.fixture
def synthetic_dataset():
    gdp = make_gdp_frame()
    monthly = make_monthly_panel(fields=('ind_prod_yoy_log', 'cpi_headline_mom_log',
                                          'm2_yoy_log'))
    clean = {'industrial_production': 'ind_prod_yoy_log',
             'cpi_headline': 'cpi_headline_mom_log',
             'm2': 'm2_yoy_log'}
    registry = make_registry_stub(clean, release_lag_days={
        'industrial_production': 30, 'cpi_headline': 5, 'm2': 25,
    })
    return ModelingDataset(
        gdp=gdp, monthly=monthly, registry=registry,
        release_lag_days={'industrial_production': 30, 'cpi_headline': 5, 'm2': 25},
        clean_field_by_key=clean,
        monthly_key_by_field={v: k for k, v in clean.items()},
    )
