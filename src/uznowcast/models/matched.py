"""Matched-quarter and common-sample metric tables for Phase 4A.1.

Both address a specific comparison bug in Phase 4A: the ``relative_to_ar1``
metrics compared each challenger's RMSE to the AR(1) RMSE computed over
the AR(1)'s own (full) evaluation sample, even when the challenger only
produced predictions on a subset of those quarters. That inflated or
deflated relative rankings depending on which quarters each challenger
happened to fail on.

Matched-quarter metrics recompute the AR(1) benchmark on the exact
quarters where the challenger has a valid prediction. Common-sample
tables identify the intersection of quarters across a whole group of
models and report metrics on that intersection so early-starting models
do not appear artificially better by starting later.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from uznowcast.models.metrics import summarize


def valid_target_quarters(frame: pd.DataFrame) -> pd.Index:
    """Quarters where the frame carries a non-null prediction AND actual."""
    mask = frame['prediction'].notna() & frame['actual'].notna()
    return pd.Index(frame.loc[mask, 'target_quarter'].unique(), name='target_quarter')


def matched_metrics(predictions: pd.DataFrame,
                    *, benchmark: str = 'ar1') -> pd.DataFrame:
    """One row per (model, tier, horizon, lag_mode) with matched-AR(1) metrics.

    The AR(1) rows are matched against themselves (which trivially yields
    ``matched_relative_rmse = 1.0``) so downstream code can filter without
    a special case.
    """
    if predictions.empty:
        return predictions.copy()
    frame = predictions.copy()
    frame['error_abs'] = frame['error'].abs()
    rows: list[dict] = []
    grouped = frame.groupby(['model', 'tier', 'horizon', 'lag_mode'], dropna=False)
    for (model, tier, horizon, lag_mode), group in grouped:
        challenger_valid = group.loc[group['prediction'].notna() & group['actual'].notna()]
        if challenger_valid.empty:
            challenger_stats = summarize([])
            comparison_first = comparison_last = None
        else:
            errors = challenger_valid['error'].tolist()
            challenger_stats = summarize(errors)
            comparison_first = str(challenger_valid['target_quarter'].min())
            comparison_last = str(challenger_valid['target_quarter'].max())
        matched = _benchmark_on_quarters(frame, benchmark, horizon, lag_mode,
                                          challenger_valid['target_quarter'])
        rows.append(dict(
            model=model, tier=tier, horizon=horizon, lag_mode=lag_mode,
            n_matched_forecasts=int(len(challenger_valid)),
            comparison_first_quarter=comparison_first,
            comparison_last_quarter=comparison_last,
            challenger_rmse=challenger_stats['rmse'],
            challenger_mae=challenger_stats['mae'],
            challenger_bias=challenger_stats['bias'],
            matched_ar1_rmse=matched['rmse'],
            matched_ar1_mae=matched['mae'],
            matched_ar1_bias=matched['bias'],
            matched_relative_rmse=(_ratio(challenger_stats['rmse'], matched['rmse'])),
            matched_relative_mae=(_ratio(challenger_stats['mae'], matched['mae'])),
        ))
    return pd.DataFrame(rows)


def _benchmark_on_quarters(frame: pd.DataFrame, benchmark: str, horizon: str,
                           lag_mode: str, quarters: pd.Series) -> dict:
    if len(quarters) == 0:
        return summarize([])
    bench_rows = frame.loc[(frame['model'] == benchmark) &
                            (frame['horizon'] == horizon) &
                            (frame['lag_mode'] == lag_mode) &
                            (frame['target_quarter'].isin(quarters.tolist()))]
    matched = bench_rows.loc[bench_rows['prediction'].notna() & bench_rows['actual'].notna()]
    return summarize(matched['error'].tolist())


def _ratio(num: float, den: float) -> float:
    if den is None or den == 0.0 or np.isnan(den) or num is None or np.isnan(num):
        return float('nan')
    return float(num / den)


def common_sample_metrics(predictions: pd.DataFrame,
                          model_groups: dict[str, list[str]]) -> pd.DataFrame:
    """Metrics on the intersection of quarters where every model in a group
    has a valid prediction.

    ``model_groups`` maps a group label to the sequence of model names
    (e.g. ``{'AR_vs_TierA_bridges': ['ar1', 'bridge_ppi_...', ...]}``).
    Groups with an empty intersection emit one row per member with
    ``n_common == 0``.
    """
    if predictions.empty:
        return predictions.copy().iloc[:0]
    rows: list[dict] = []
    for horizon in sorted(predictions['horizon'].dropna().unique()):
        for lag_mode in sorted(predictions['lag_mode'].dropna().unique()):
            slab = predictions.loc[(predictions['horizon'] == horizon)
                                    & (predictions['lag_mode'] == lag_mode)]
            for group_label, members in model_groups.items():
                members = [m for m in members if m in set(slab['model'])]
                if not members:
                    continue
                quarter_sets = []
                for member in members:
                    member_valid = slab.loc[(slab['model'] == member)
                                             & slab['prediction'].notna()
                                             & slab['actual'].notna(),
                                             'target_quarter']
                    quarter_sets.append(set(member_valid.tolist()))
                intersection = set.intersection(*quarter_sets) if quarter_sets else set()
                for member in members:
                    member_rows = slab.loc[(slab['model'] == member)
                                            & slab['target_quarter'].isin(intersection)]
                    stats = summarize(member_rows['error'].tolist())
                    rows.append(dict(
                        group=group_label, model=member,
                        horizon=horizon, lag_mode=lag_mode,
                        n_common=len(intersection),
                        common_first_quarter=(min(intersection) if intersection else None),
                        common_last_quarter=(max(intersection) if intersection else None),
                        rmse=stats['rmse'], mae=stats['mae'], bias=stats['bias'],
                    ))
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    # Attach relative-to-AR(1) inside the same group + horizon + lag_mode.
    frame['rmse_relative_to_ar1'] = float('nan')
    frame['mae_relative_to_ar1'] = float('nan')
    for keys, block in frame.groupby(['group', 'horizon', 'lag_mode']):
        ar1 = block.loc[block['model'] == 'ar1']
        if ar1.empty:
            continue
        rmse_bench = float(ar1['rmse'].iloc[0])
        mae_bench = float(ar1['mae'].iloc[0])
        mask = ((frame['group'] == keys[0]) & (frame['horizon'] == keys[1])
                 & (frame['lag_mode'] == keys[2]))
        frame.loc[mask, 'rmse_relative_to_ar1'] = frame.loc[mask, 'rmse'] / rmse_bench
        frame.loc[mask, 'mae_relative_to_ar1'] = frame.loc[mask, 'mae'] / mae_bench
    return frame


# --- Horizon sanity ----------------------------------------------------------


def horizon_delta_report(predictions: pd.DataFrame) -> pd.DataFrame:
    """Per-model share of forecasts where H1/H2/H3 predictions differ.

    Reports one row per (model, tier, lag_mode) with three shares.
    Benchmark models (``historical_mean``, ``ar1``, ``ar2``) are expected
    to be identical across horizons; that expectation is verified by the
    generated columns.
    """
    if predictions.empty:
        return predictions.copy().iloc[:0]
    rows: list[dict] = []
    for (model, tier, lag_mode), group in predictions.groupby(
            ['model', 'tier', 'lag_mode'], dropna=False):
        pivoted = group.pivot_table(index='target_quarter', columns='horizon',
                                     values='prediction', aggfunc='first')
        share = {}
        for a, b in (('H1', 'H2'), ('H2', 'H3'), ('H1', 'H3')):
            if a in pivoted.columns and b in pivoted.columns:
                mask = pivoted[a].notna() & pivoted[b].notna()
                if mask.any():
                    diff = pivoted.loc[mask, a] != pivoted.loc[mask, b]
                    share[f'share_{a}_ne_{b}'] = float(diff.mean())
                    share[f'n_{a}_and_{b}'] = int(mask.sum())
                else:
                    share[f'share_{a}_ne_{b}'] = float('nan')
                    share[f'n_{a}_and_{b}'] = 0
            else:
                share[f'share_{a}_ne_{b}'] = float('nan')
                share[f'n_{a}_and_{b}'] = 0
        rows.append(dict(model=model, tier=tier, lag_mode=lag_mode, **share))
    return pd.DataFrame(rows)


# --- Lag-mode sensitivity ----------------------------------------------------


def lag_mode_delta(matched: pd.DataFrame) -> pd.DataFrame:
    """Standard vs conservative comparison on matched-AR(1) metrics."""
    if matched.empty:
        return matched.copy().iloc[:0]
    frame = matched.copy()
    rows: list[dict] = []
    for (model, tier, horizon), block in frame.groupby(['model', 'tier', 'horizon'],
                                                        dropna=False):
        std = block.loc[block['lag_mode'] == 'standard']
        con = block.loc[block['lag_mode'] == 'conservative']
        if std.empty or con.empty:
            continue
        rows.append(dict(
            model=model, tier=tier, horizon=horizon,
            standard_rmse=float(std['challenger_rmse'].iloc[0]),
            conservative_rmse=float(con['challenger_rmse'].iloc[0]),
            delta_rmse=(float(con['challenger_rmse'].iloc[0])
                        - float(std['challenger_rmse'].iloc[0])),
            standard_mae=float(std['challenger_mae'].iloc[0]),
            conservative_mae=float(con['challenger_mae'].iloc[0]),
            delta_mae=(float(con['challenger_mae'].iloc[0])
                       - float(std['challenger_mae'].iloc[0])),
            n_standard=int(std['n_matched_forecasts'].iloc[0]),
            n_conservative=int(con['n_matched_forecasts'].iloc[0]),
            forecasts_lost_under_conservative=(int(std['n_matched_forecasts'].iloc[0])
                                                - int(con['n_matched_forecasts'].iloc[0])),
        ))
    return pd.DataFrame(rows)
