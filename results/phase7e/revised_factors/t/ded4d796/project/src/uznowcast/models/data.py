"""Read-only loaders for the V1.2 GDP target and monthly predictor panel.

Every function in this module treats the master files as immutable inputs.
Nothing here writes back into ``data/master/`` or ``metadata/``. Missing
values from the database are preserved as ``NaN`` rather than filled.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
import re

import numpy as np
import pandas as pd

from uznowcast.registry import Registry, load_registry


DEFAULT_MASTER_DIR = 'data/master'


# The Phase 3B tier assignment is authoritative; see
# docs/model_readiness_tiers.md.
TIER_A: tuple[str, ...] = (
    'ppi', 'usd_uzs', 'rub_uzs', 'gold_price', 'm2', 'fx_reserves_ex_gold',
)
TIER_B_ADDITIONAL: tuple[str, ...] = (
    'industrial_production', 'manufacturing', 'mining', 'electricity_gas',
    'retail_trade', 'wholesale_trade',
)
TIER_C_ADDITIONAL: tuple[str, ...] = (
    'construction', 'cpi_headline', 'cpi_food', 'cpi_services',
    'exports_total', 'exports_non_gold', 'imports_total', 'gold_exports_proxy',
)
EXPERIMENTAL_KEYS: tuple[str, ...] = (
    'household_deposits', 'corporate_deposits', 'household_credit',
    'corporate_credit', 'pos_turnover', 'instant_payments', 'interbank_payments',
)
EXCLUDED_KEYS: tuple[str, ...] = ('russia_ipi',)


def tier_variables(tier: str) -> tuple[str, ...]:
    """Return the variable keys for a Phase 4A predictor tier.

    ``tier`` is one of ``A``, ``B``, ``C``, ``experimental``. The tier
    definitions are taken from ``docs/model_readiness_tiers.md``.
    """
    if tier == 'A':
        return TIER_A
    if tier == 'B':
        return TIER_A + TIER_B_ADDITIONAL
    if tier == 'C':
        return TIER_A + TIER_B_ADDITIONAL + TIER_C_ADDITIONAL
    if tier == 'experimental':
        return EXPERIMENTAL_KEYS
    raise ValueError(f'Unknown tier: {tier!r}')


@dataclass(frozen=True)
class ModelingDataset:
    """Bundle of read-only inputs Phase 4A models operate against."""

    gdp: pd.DataFrame           # columns: quarter, gdp_real_yoy_pct
    monthly: pd.DataFrame       # index=month-end date, columns=clean_model_field
    registry: Registry
    release_lag_days: dict[str, int]      # variable_key → registry lag
    clean_field_by_key: dict[str, str]
    monthly_key_by_field: dict[str, str]
    target_field: str = 'gdp_real_yoy_pct'

    def variable_keys(self) -> tuple[str, ...]:
        return tuple(self.clean_field_by_key)

    def predictor_fields(self, tier: str) -> list[str]:
        want = set(tier_variables(tier))
        return [self.clean_field_by_key[key] for key in tier_variables(tier)
                if key in want and key in self.clean_field_by_key
                and self.clean_field_by_key[key] in self.monthly.columns]


def _read_gdp(gdp_path: Path, target_field: str) -> pd.DataFrame:
    frame = pd.read_parquet(gdp_path)
    if target_field not in frame.columns:
        raise ValueError(f'GDP master missing {target_field}; columns: {list(frame.columns)}')
    if 'quarter' not in frame.columns:
        raise ValueError('GDP master missing quarter column')
    result = frame[['quarter', target_field]].copy()
    result['quarter'] = result['quarter'].astype(str)
    if result['quarter'].duplicated().any():
        raise ValueError('GDP master has duplicate quarters')
    result = result.sort_values('quarter').reset_index(drop=True)
    return result


def _read_monthly(monthly_path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(monthly_path)
    if 'date' not in frame.columns:
        raise ValueError('Monthly master missing date column')
    frame = frame.copy()
    frame['date'] = pd.to_datetime(frame['date'])
    frame = frame.sort_values('date').set_index('date')
    if frame.index.has_duplicates:
        raise ValueError('Monthly master has duplicate dates')
    # Drop non-predictor auxiliary columns emitted by build_monthly.
    auxiliary = {c for c in frame.columns if c.endswith('_quality_flag') or c.endswith('_is_complete')}
    return frame.drop(columns=list(auxiliary))


def load_dataset(root: Path, *, master_dir: str = DEFAULT_MASTER_DIR,
                 registry_relative: str = 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx',
                 monthly_name: str = 'v1_monthly.parquet',
                 gdp_name: str = 'gdp_quarterly.parquet',
                 target_field: str = 'gdp_real_yoy_pct') -> ModelingDataset:
    """Read the read-only frozen V1.2 master datasets."""
    root = Path(root).resolve()
    registry_path = root / registry_relative
    registry = load_registry(registry_path)
    gdp = _read_gdp(root / master_dir / gdp_name, target_field)
    monthly = _read_monthly(root / master_dir / monthly_name)
    clean_field_by_key = {row['variable_key']: row['clean_model_field']
                          for row in registry.scope('v1')}
    monthly_key_by_field = {v: k for k, v in clean_field_by_key.items()}
    release_lag_days = {row['variable_key']: int(row['typical_publication_lag_days'])
                        for row in registry.scope('v1')
                        if row.get('typical_publication_lag_days') is not None}
    return ModelingDataset(
        gdp=gdp, monthly=monthly, registry=registry,
        release_lag_days=release_lag_days,
        clean_field_by_key=clean_field_by_key,
        monthly_key_by_field=monthly_key_by_field,
        target_field=target_field)


# --- Nowcast horizons ---------------------------------------------------------

QUARTER_PATTERN = re.compile(r'(\d{4})-Q([1-4])$|(\d{4})Q([1-4])$')


def quarter_start(quarter: str) -> pd.Timestamp:
    match = QUARTER_PATTERN.match(quarter)
    if not match:
        raise ValueError(f'Bad quarter label: {quarter!r}')
    year = int(match.group(1) or match.group(3))
    q = int(match.group(2) or match.group(4))
    month = 3 * (q - 1) + 1
    return pd.Timestamp(year=year, month=month, day=1)


def quarter_end(quarter: str) -> pd.Timestamp:
    start = quarter_start(quarter)
    return (start + pd.offsets.MonthEnd(3)).normalize()


def horizon_month_end(quarter: str, horizon: str) -> pd.Timestamp:
    """Calendar-month end for horizon H1/H2/H3 within the target quarter."""
    horizons = {'H1': 1, 'H2': 2, 'H3': 3}
    if horizon not in horizons:
        raise ValueError(f'Unknown horizon: {horizon!r}')
    offset = horizons[horizon] - 1
    start = quarter_start(quarter)
    month_first = (start + pd.offsets.MonthBegin(offset)).normalize()
    return (month_first + pd.offsets.MonthEnd(0)).normalize()


LAG_MODES = ('standard', 'conservative')


def effective_release_day(base_lag: int, mode: str) -> int:
    """Return the assumed publication lag under the requested mode.

    ``standard`` uses the registry's typical lag verbatim. ``conservative``
    adds a 15-day safety cushion and bumps zero-lag daily sources to 3 days.
    Neither mode fabricates a first-release date; both are documented as
    approximate pseudo-real-time assumptions.
    """
    if mode not in LAG_MODES:
        raise ValueError(f'Unknown lag mode: {mode!r}')
    if mode == 'standard':
        return max(int(base_lag), 0)
    return max(int(base_lag) + 15, 3)


def information_cutoff_for_variable(origin: pd.Timestamp, variable_key: str,
                                     release_lag_days: dict[str, int],
                                     mode: str = 'standard') -> pd.Timestamp:
    """Latest reference month whose value would be available by ``origin``.

    A monthly statistic for reference-month ``m`` is assumed released on
    the last day of ``m`` plus its typical publication lag. The latest
    releasable month at ``origin`` therefore satisfies
    ``end_of_month + lag_days <= origin``. Under the standard assumption
    the Phase 4A framework does **not** claim that a statistic was known
    on its reference-month end date; it uses the registry's Typical
    publication lag (days). Under conservative mode the lag is padded by
    15 days.
    """
    lag = effective_release_day(release_lag_days.get(variable_key, 30), mode)
    # Candidate release date is (end of ref-month) + lag; we want the
    # latest ref-month whose release ≤ origin.
    candidate_end = origin - pd.Timedelta(days=lag)
    # candidate_end may fall mid-month; step back to that month's end.
    return (candidate_end.to_period('M').to_timestamp('M').normalize()
            if candidate_end.day == candidate_end.days_in_month
            else (candidate_end.to_period('M') - 1).to_timestamp('M').normalize())


def build_information_set(dataset: ModelingDataset, quarter: str, horizon: str,
                          fields: Sequence[str], *, mode: str = 'standard') -> pd.DataFrame:
    """Return the monthly panel visible at the horizon's information origin.

    For every requested field, ``NaN`` any month beyond the latest release
    permitted by that variable's release lag. Also ``NaN`` any month after
    the horizon's own calendar cutoff. The returned frame is the input to
    every model at that quarter/horizon.
    """
    origin = horizon_month_end(quarter, horizon)
    panel = dataset.monthly.copy()
    panel = panel.loc[panel.index <= origin]
    for field in fields:
        key = dataset.monthly_key_by_field.get(field)
        if key is None:
            continue
        cutoff = information_cutoff_for_variable(origin, key, dataset.release_lag_days, mode)
        panel.loc[panel.index > cutoff, field] = np.nan
    return panel[list(fields)]


def gdp_available_at(dataset: ModelingDataset, quarter: str, horizon: str,
                     *, gdp_lag_days: int | None = None,
                     mode: str = 'standard') -> pd.DataFrame:
    """Return GDP rows released by the horizon's information origin.

    GDP has no documented first-release history in V1.2 (see the release
    audit). This function conservatively assumes a documented typical GDP
    publication lag (default 30 days after quarter end) and drops any
    quarter whose implied release would post after the origin. That mirrors
    the same look-ahead-bias guard used on monthly predictors.
    """
    origin = horizon_month_end(quarter, horizon)
    lag = effective_release_day(gdp_lag_days if gdp_lag_days is not None else 30, mode)
    keep = []
    for _, row in dataset.gdp.iterrows():
        end = quarter_end(row['quarter'])
        release = end + pd.Timedelta(days=lag)
        if release <= origin:
            keep.append(row)
    if not keep:
        return dataset.gdp.iloc[:0].copy()
    frame = pd.DataFrame(keep).reset_index(drop=True)
    return frame


def usable_target_quarters(dataset: ModelingDataset) -> list[str]:
    """List of quarters for which a target value exists in the GDP master."""
    frame = dataset.gdp.dropna(subset=[dataset.target_field])
    return frame['quarter'].tolist()
