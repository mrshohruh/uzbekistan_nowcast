"""Modelling-time preprocessing that never rewrites the database.

Standardization statistics and any robust-treatment thresholds are learned
strictly from the training-window slice and then applied to the entire
frame. This is called at every expanding-window step, so nothing about the
target quarter enters the transformation.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Standardizer:
    """Column-wise (mean, std) computed on the training slice only."""

    means: pd.Series
    stds: pd.Series

    @classmethod
    def fit(cls, training_slice: pd.DataFrame) -> 'Standardizer':
        means = training_slice.mean(axis=0, skipna=True)
        stds = training_slice.std(axis=0, ddof=0, skipna=True)
        # Guard against divide-by-zero on constant columns.
        stds = stds.mask(stds == 0, 1.0)
        stds = stds.fillna(1.0)
        return cls(means=means, stds=stds)

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        return frame.subtract(self.means, axis=1).divide(self.stds, axis=1)


def robust_flag_mask(frame: pd.DataFrame, quality_column: str | None) -> pd.DataFrame:
    """Return a bool mask where an existing database quality flag says
    the observation is documented as extreme.

    The mask NEVER modifies the database observation. It is used solely to
    let a robustness variant (variant B in
    ``docs/phase4a_results.md`` §11) mark the observation as missing in a
    parallel run.
    """
    if quality_column is None or quality_column not in frame.columns:
        return pd.DataFrame(False, index=frame.index, columns=frame.columns)
    flags = frame[quality_column].fillna('').astype(str)
    extreme = flags.str.contains('extreme_log_change|nonpositive|impossible_negative',
                                  regex=True)
    return pd.DataFrame({column: extreme for column in frame.columns})


def apply_robust_variant(frame: pd.DataFrame, mask: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``frame`` where masked cells are NaN (variant B)."""
    if mask.shape != frame.shape:
        raise ValueError('robust mask shape mismatch')
    out = frame.copy()
    out = out.mask(mask, np.nan)
    return out


def training_slice(monthly: pd.DataFrame, train_quarters: tuple[str, ...]) -> pd.DataFrame:
    """Restrict a monthly panel to months strictly inside the training set.

    A month belongs to the training slice if its calendar quarter appears
    in ``train_quarters`` OR if it precedes the earliest training quarter.
    This lets standardization use the long left-hand history of long-run
    series (e.g. PPI back to 2013) while still forbidding any future
    information.
    """
    if not train_quarters:
        return monthly.iloc[:0].copy()
    train_end_quarter = max(train_quarters)
    year, q = int(train_end_quarter[:4]), int(train_end_quarter[-1])
    end_month = 3 * q
    cutoff = pd.Timestamp(year=year, month=end_month, day=1) + pd.offsets.MonthEnd(0)
    return monthly.loc[monthly.index <= cutoff.normalize()].copy()
