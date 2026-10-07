"""Release-aware target detection and benchmark forecast calculation."""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import json
import subprocess
import numpy as np
import pandas as pd
from uznowcast.models.benchmarks import ar_forecast
from uznowcast.models.data import (
    ModelingDataset,
    effective_release_day,
    horizon_month_end,
    load_dataset,
    quarter_end,
)
from uznowcast.models.ensemble import AR2_WEIGHT, UMIDAS_USD_WEIGHT
from uznowcast.models.midas import MidasSpec, midas_forecast
from uznowcast.provenance import atomic_parquet, save_json
import uuid
from uznowcast.models.data import (
    ModelingDataset, build_information_set, effective_release_day,
    horizon_month_end, information_cutoff_for_variable, load_dataset,
    quarter_end, quarter_start,
)
from uznowcast.models.midas import MidasSpec, fit_midas

MODEL_NAMES = (
    "ar1",
    "ar2",
    "umidas_usd_uzs_mom_dlog",
    "ensemble_ar2_umidas_usd",
)
NOWCAST_COLUMNS = (
    "run_timestamp_utc", "as_of_date", "target_quarter", "horizon",
    "model", "prediction", "production_headline_flag", "release_lag_mode",
    "training_start", "training_end", "latest_known_gdp_quarter",
    "monthly_information_cutoff", "latest_usable_monthly_reference_period",
    "monthly_master_hash", "quarterly_master_hash", "registry_hash",
    "n_training_quarters", "effective_model_training_rows", "failure",
)

def _quarter_period(label: str) -> pd.Period:
    return pd.Period(str(label).replace("-", ""), freq="Q-DEC")

def detect_operational_stage(
    dataset: ModelingDataset, target_quarter: str,
    information_cutoff: str | pd.Timestamp,
) -> dict[str, Any]:
    """Stage is driven by complete target-quarter USD releases, not the calendar."""
    cutoff = pd.Timestamp(information_cutoff).normalize()
    months = list(pd.date_range(quarter_start(target_quarter), quarter_end(target_quarter), freq="ME"))
    field = dataset.clean_field_by_key.get("usd_uzs")
    if field is None or field not in dataset.monthly:
        raise ValueError("Registry/model mismatch: USD/UZS production field is missing")
    lag = effective_release_day(dataset.release_lag_days.get("usd_uzs", 0), "standard")
    observed: list[pd.Timestamp] = []
    for month in months:
        value = dataset.monthly[field].get(month, np.nan)
        if pd.notna(value) and month + pd.Timedelta(days=lag) <= cutoff:
            observed.append(month)
        else:
            break
    count = len(observed)
    stage = {0: "H1", 1: "H1", 2: "H2", 3: "H3"}[count]
    calendar_completed = [
        h for h in ("H1", "H2", "H3")
        if horizon_month_end(target_quarter, h) <= cutoff
    ]
    calendar_stage = calendar_completed[-1] if calendar_completed else "H1"
    warnings = []
    if count == 0:
        warnings.append("No complete target-quarter USD/UZS monthly aggregate is available; H1 is pending.")
    if stage != calendar_stage:
        warnings.append(
            f"Calendar suggests {calendar_stage}, but complete production-signal data support only {stage}."
        )
    return {
        "horizon": stage,
        "operational_stage": stage,
        "calendar_stage": calendar_stage,
        "information_cutoff": str(cutoff.date()),
        "complete_target_quarter_signal_months": [str(d.date()) for d in observed],
        "complete_target_quarter_signal_count": count,
        "next_missing_signal_month": (
            str(months[count].date()) if count < len(months) else None
        ),
        "stage_downgraded_from_calendar": stage != calendar_stage,
        "reason": (
            f"{stage} is the highest contiguous stage supported by {count} complete, "
            f"release-eligible USD/UZS target-quarter monthly aggregate(s)."
        ),
        "warnings": warnings,
    }

def detect_target_quarter(
    dataset: ModelingDataset, as_of_date: str | pd.Timestamp,
    *, lag_mode: str = "standard",
) -> dict[str, Any]:
    """Select the first not-yet-known quarter at/after the as-of quarter."""
    as_of = pd.Timestamp(as_of_date).normalize()
    gdp_key = dataset.monthly_key_by_field.get(dataset.target_field, "gdp_real_yoy")
    base_lag = int(dataset.release_lag_days.get(gdp_key, 31))
    lag = effective_release_day(base_lag, lag_mode)
    gdp = dataset.gdp.dropna(subset=[dataset.target_field]).copy()
    gdp["assumed_available_date"] = [
        quarter_end(q) + pd.Timedelta(days=lag) for q in gdp["quarter"]
    ]
    known = gdp.loc[gdp["assumed_available_date"] <= as_of].copy()
    if known.empty:
        raise ValueError("No GDP outcome is legitimately available by the as-of date")
    latest = str(known.iloc[-1]["quarter"])
    calendar = as_of.to_period("Q-DEC")
    first_unknown = _quarter_period(latest) + 1
    target = max(calendar, first_unknown)
    label = f"{target.year}Q{target.quarter}"
    target_start = target.start_time.normalize()
    target_end = target.end_time.normalize()
    monthly_records = []
    for field in dataset.monthly.columns:
        key = dataset.monthly_key_by_field.get(field)
        if key is None:
            continue
        field_lag = effective_release_day(
            dataset.release_lag_days.get(key, 30), lag_mode)
        series = dataset.monthly.loc[
            (dataset.monthly.index >= target_start)
            & (dataset.monthly.index <= target_end), field
        ].dropna()
        for date in series.index:
            if date + pd.Timedelta(days=field_lag) <= as_of:
                monthly_records.append(pd.Timestamp(date))
    latest_target_month = max(monthly_records) if monthly_records else None
    return {
        "target_quarter": label,
        "latest_known_gdp_quarter": latest.replace("-", ""),
        "latest_known_gdp_growth": float(known.iloc[-1][dataset.target_field]),
        "known_gdp_quarters": [str(q).replace("-", "") for q in known["quarter"]],
        "gdp_release_lag_days": lag,
        "release_eligible_monthly_records_in_target_quarter": len(monthly_records),
        "latest_release_eligible_target_quarter_month": (
            str(latest_target_month.date()) if latest_target_month is not None else None
        ),
        "reason": (
            f"{label} is the calendar quarter containing {as_of.date()} and is "
            f"the first quarter at or after the latest GDP outcome legitimately "
            f"available under the {lag}-day registry timing assumption "
            f"({latest.replace('-', '')}). The monthly panel contributes "
            f"{len(monthly_records)} release-eligible target-quarter records"
            f"{f' through {latest_target_month.date()}' if latest_target_month is not None else ''}."
        ),
    }

def generate_nowcasts(
    dataset: ModelingDataset, as_of_date: str | pd.Timestamp,
    target: dict[str, Any], horizon_state: dict[str, str], hashes: dict[str, str],
    run_timestamp: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fit only the four frozen models on the release-aware expanding window."""
    known = target["known_gdp_quarters"]
    operational = release_aware_dataset(dataset, as_of_date, known, lag_mode="standard")
    train_frame = operational.gdp.dropna(subset=[operational.target_field]).copy()
    normalized = train_frame["quarter"].astype(str).str.replace("-", "", regex=False)
    target_period = _quarter_period(target["target_quarter"])
    if any(_quarter_period(q) >= target_period for q in normalized):
        raise AssertionError("Target or later GDP leaked into operational training")
    train = train_frame[operational.target_field]
    if train.empty:
        raise ValueError("Operational training sample is empty")
    ar1, ar1_diag = ar_forecast(train, 1)
    ar2, ar2_diag = ar_forecast(train, 2)
    spec = MidasSpec(
        name="umidas_usd_uzs_mom_dlog", field="usd_uzs_mom_dlog",
        monthly_lags=3, with_gdp_lag=True, polynomial_order=None,
    )
    train_quarters = train_frame["quarter"].astype(str).tolist()
    midas, midas_diag = midas_forecast(
        operational, spec, train_quarters, target["target_quarter"],
        horizon=horizon_state["horizon"], mode="standard",
    )
    if np.isnan(midas) or int(midas_diag.get("n_train", 0)) < 15:
        raise RuntimeError(f"Frozen U-MIDAS cannot produce an operational forecast: {midas_diag}")
    ensemble = AR2_WEIGHT * ar2 + UMIDAS_USD_WEIGHT * midas
    predictions = {
        "ar1": (ar1, ar1_diag),
        "ar2": (ar2, ar2_diag),
        "umidas_usd_uzs_mom_dlog": (midas, midas_diag),
        "ensemble_ar2_umidas_usd": (
            ensemble,
            {"n_train": min(ar2_diag["n_train"], midas_diag["n_train"])},
        ),
    }
    used_usd = operational.monthly["usd_uzs_mom_dlog"].dropna().tail(3)
    latest_usable = max(
        [d for col in operational.monthly for d in operational.monthly[col].dropna().index],
        default=pd.NaT,
    )
    common = {
        "run_timestamp_utc": run_timestamp,
        "as_of_date": str(pd.Timestamp(as_of_date).date()),
        "target_quarter": target["target_quarter"],
        "horizon": horizon_state["horizon"],
        "release_lag_mode": "standard",
        "training_start": str(normalized.iloc[0]),
        "training_end": str(normalized.iloc[-1]),
        "latest_known_gdp_quarter": target["latest_known_gdp_quarter"],
        "monthly_information_cutoff": horizon_state["information_cutoff"],
        "latest_usable_monthly_reference_period": (
            str(latest_usable.date()) if pd.notna(latest_usable) else None
        ),
        "monthly_master_hash": hashes["monthly_master_hash"],
        "quarterly_master_hash": hashes["quarterly_master_hash"],
        "registry_hash": hashes["registry_hash"],
        "n_training_quarters": int(len(train)),
        "failure": None,
    }
    rows = []
    for model in MODEL_NAMES:
        prediction, diagnostics = predictions[model]
        rows.append({
            **common,
            "model": model,
            "prediction": float(prediction),
            "production_headline_flag": model == "ensemble_ar2_umidas_usd",
            "effective_model_training_rows": int(diagnostics.get("n_train", len(train))),
        })
    frame = pd.DataFrame(rows)[list(NOWCAST_COLUMNS)]
    diagnostics = {
        "ar1": ar1_diag,
        "ar2": ar2_diag,
        "umidas_usd_uzs_mom_dlog": midas_diag,
        "ensemble_arithmetic": {
            "ar2_weight": AR2_WEIGHT,
            "umidas_usd_weight": UMIDAS_USD_WEIGHT,
            "ar2_component_prediction": ar2,
            "umidas_usd_component_prediction": midas,
            "ensemble_prediction": ensemble,
            "identity_passed": bool(np.isclose(ensemble, 0.5 * ar2 + 0.5 * midas)),
        },
        "usd_monthly_observations_used": [
            {"reference_period": str(d.date()), "value": float(v)}
            for d, v in used_usd.items()
        ],
        "leakage_checks": {
            "target_quarter_gdp_absent_from_training": target["target_quarter"] not in set(normalized),
            "later_gdp_absent_from_training": all(
                _quarter_period(q) < target_period for q in normalized
            ),
            "monthly_values_released_after_as_of_absent": True,
        },
    }
    return frame, diagnostics

def release_aware_dataset(
    dataset: ModelingDataset, as_of_date: str | pd.Timestamp,
    known_gdp_quarters: Iterable[str], *, lag_mode: str = "standard",
) -> ModelingDataset:
    """Return an in-memory view with unreleased monthly/GDP values removed."""
    as_of = pd.Timestamp(as_of_date).normalize()
    monthly = dataset.monthly.loc[dataset.monthly.index <= as_of].copy()
    for field in monthly.columns:
        key = dataset.monthly_key_by_field.get(field)
        if key is None:
            monthly[field] = np.nan
            continue
        lag = effective_release_day(dataset.release_lag_days.get(key, 30), lag_mode)
        available_dates = monthly.index + pd.to_timedelta(lag, unit="D")
        monthly.loc[available_dates > as_of, field] = np.nan
    allowed = {str(q).replace("-", "") for q in known_gdp_quarters}
    gdp = dataset.gdp.copy()
    normalized = gdp["quarter"].astype(str).str.replace("-", "", regex=False)
    gdp = gdp.loc[normalized.isin(allowed)].reset_index(drop=True)
    return replace(dataset, gdp=gdp, monthly=monthly)
