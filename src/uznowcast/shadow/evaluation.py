"""Matched prospective scoring. No estimates, screening or production writes."""
from __future__ import annotations

import numpy as np
import pandas as pd

PRODUCTION = 'production_ensemble_ar2_usd'
HORIZONS = ('H1', 'H2', 'H3')


def evidence_status(n: int) -> str:
    if n == 0:
        return 'NOT_YET_EVALUABLE'
    if n < 4:
        return 'INSUFFICIENT_PROSPECTIVE_EVIDENCE'
    if n < 6:
        return 'EARLY_PROSPECTIVE_EVIDENCE'
    if n < 8:
        return 'MODERATE_PROSPECTIVE_EVIDENCE'
    return 'MATURE_PROSPECTIVE_EVIDENCE'


def matched_metrics(frame: pd.DataFrame) -> dict:
    paired = frame.dropna(subset=['forecast', 'production_forecast', 'actual'])
    if paired.empty:
        return dict(matched_n=0, rmse=np.nan, production_rmse=np.nan,
                    relative_rmse=np.nan, mae=np.nan, production_mae=np.nan,
                    relative_mae=np.nan, bias=np.nan, median_abs_error=np.nan,
                    worst_abs_error=np.nan, delta_RMSE=np.nan, delta_MAE=np.nan,
                    percentage_improvement=np.nan, quarters_better_than_production=0,
                    quarters_worse_than_production=0)
    e = paired.forecast - paired.actual
    p = paired.production_forecast - paired.actual
    rmse, prmse = float(np.sqrt((e**2).mean())), float(np.sqrt((p**2).mean()))
    mae, pmae = float(e.abs().mean()), float(p.abs().mean())
    relative = rmse / prmse if prmse > 0 else np.nan
    return dict(matched_n=len(paired), rmse=rmse, production_rmse=prmse,
                relative_rmse=relative, mae=mae, production_mae=pmae,
                relative_mae=mae/pmae if pmae > 0 else np.nan, bias=float(e.mean()),
                median_abs_error=float(e.abs().median()), worst_abs_error=float(e.abs().max()),
                delta_RMSE=rmse-prmse, delta_MAE=mae-pmae,
                percentage_improvement=100*(1-relative),
                quarters_better_than_production=int((e.abs()<p.abs()).groupby(paired.target_quarter).all().sum()),
                quarters_worse_than_production=int((e.abs()>p.abs()).groupby(paired.target_quarter).any().sum()))


def influence(frame: pd.DataFrame) -> dict:
    paired = frame.dropna(subset=['forecast', 'production_forecast', 'actual'])
    quarters = sorted(paired.target_quarter.unique())
    if len(quarters) < 4:
        return dict(influence_flag='INSUFFICIENT_PROSPECTIVE_EVIDENCE', minimum_relative_rmse=np.nan,
                    maximum_relative_rmse=np.nan, dropped_quarter_results={})
    ratios = {q: matched_metrics(paired[paired.target_quarter != q])['relative_rmse'] for q in quarters}
    values = list(ratios.values())
    robust = all(np.isfinite(v) and v < 1 for v in values)
    return dict(influence_flag='ROBUST_PROSPECTIVE_IMPROVEMENT' if robust else 'FRAGILE_PROSPECTIVE_IMPROVEMENT',
                minimum_relative_rmse=min(values), maximum_relative_rmse=max(values),
                dropped_quarter_results=ratios)


def governance(n: int, pooled: dict, checks: dict) -> str:
    """Missing operational evidence blocks eligibility, never implies success."""
    if n < 4:
        return 'INSUFFICIENT_PROSPECTIVE_EVIDENCE'
    ratio = pooled.get('relative_rmse', np.nan)
    if not np.isfinite(ratio):
        return 'MIXED'
    if ratio >= 1:
        return 'UNDERPERFORMING'
    required = ('influence', 'horizons', 'mae', 'bias', 'coverage', 'failures',
                'revisions', 'lag_consistency', 'reproducible')
    if all(checks.get(key) is True for key in required):
        return 'GOVERNANCE_REVIEW_ELIGIBLE'
    return 'PROMISING_SHADOW'


def quarter_scores(forecasts: pd.DataFrame, realizations: pd.DataFrame) -> pd.DataFrame:
    columns = ['target_quarter','horizon','model','release_lag_mode','actual','forecast','error',
               'absolute_error','squared_error','production_forecast','production_absolute_error',
               'challenger_minus_production_abs_error','winner_for_that_observation']
    if forecasts.empty or realizations.empty:
        return pd.DataFrame(columns=columns)
    eligible = realizations[realizations.evidence_class == 'LIVE_PROSPECTIVE_REALIZED']
    f = forecasts.merge(eligible[['target_quarter','release_date','first_observed_value']], on='target_quarter')
    f = f[(pd.to_datetime(f.forecast_timestamp_utc, utc=True) < pd.to_datetime(f.release_date, utc=True))
          & (pd.to_datetime(f.information_cutoff, utc=True) < pd.to_datetime(f.release_date, utc=True))]
    # First operational vintage at each horizon is primary; later vintages remain in storage.
    keys = ['target_quarter','horizon','release_lag_mode']
    f = f.sort_values('forecast_timestamp_utc').drop_duplicates(keys+['model'], keep='first')
    f = f.rename(columns={'forecast_value':'forecast','first_observed_value':'actual'})
    p = f[f.model == PRODUCTION][keys+['forecast']].rename(columns={'forecast':'production_forecast'})
    f = f.merge(p, on=keys, how='left', validate='many_to_one')
    f['error'] = f.forecast-f.actual
    f['absolute_error'] = f.error.abs()
    f['squared_error'] = f.error**2
    f['production_absolute_error'] = (f.production_forecast-f.actual).abs()
    f['challenger_minus_production_abs_error'] = f.absolute_error-f.production_absolute_error
    f['winner_for_that_observation'] = np.select(
        [f.challenger_minus_production_abs_error < 0, f.challenger_minus_production_abs_error > 0,
         f.challenger_minus_production_abs_error == 0], ['challenger','production','tie'], default='unavailable')
    return f[columns]
