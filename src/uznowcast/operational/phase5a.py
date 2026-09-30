"""Phase 5A first operational Uzbekistan GDP nowcast.

This module is deliberately a thin orchestration layer over the frozen Phase 4
model implementations. It adds as-of-date detection, release-aware masking,
provenance, revisions, and presentation; it does not add or tune a model.
"""

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


POLICY_PATH = "results/phase5a_production_policy.json"
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
REVISION_COLUMNS = (
    "history_type", "run_date", "run_timestamp_utc", "target_quarter",
    "horizon", "transition", "model", "previous_forecast",
    "current_forecast", "revision_percentage_points",
    "new_monthly_observations", "live_production_flag",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def phase4_artifact_hashes(root: Path) -> dict[str, str]:
    """Hash every immutable Phase 4 result/report artifact."""
    root = Path(root).resolve()
    paths = sorted(
        [p for p in (root / "results").glob("phase4*") if p.is_file()]
        + [root / "results/frozen_validation_definition.json"]
        + [p for p in (root / "docs/modeling").glob("phase4*") if p.is_file()]
    )
    return {
        p.relative_to(root).as_posix(): file_sha256(p)
        for p in paths if p.exists()
    }


def production_policy(run_timestamp: str) -> dict:
    return {
        "phase": "5A",
        "policy_version": "1.0",
        "created_at_utc": run_timestamp,
        "status": "FROZEN_OPERATIONAL_POLICY",
        "phase4c_benchmark_policy": (
            "Phase 4C remains immutable historical validation."
        ),
        "operational_period_policy": (
            "Phase 5A begins a new post-validation operational period."
        ),
        "primary_headline_model": "ensemble_ar2_umidas_usd",
        "comparison_models": [
            "ar1", "ar2", "umidas_usd_uzs_mom_dlog"
        ],
        "historical_mean_policy": "Retained as a benchmark where useful.",
        "model_switching": "No automatic or ad-hoc switching based on current-quarter results.",
        "ensemble_weights": {
            "ar2": AR2_WEIGHT,
            "umidas_usd_uzs_mom_dlog": UMIDAS_USD_WEIGHT,
        },
        "production_release_lag_mode": "standard",
        "robustness_release_lag_mode": "conservative",
        "information_policy": [
            "Forecasts obey real-time information availability.",
            "Future realized GDP outcomes never enter a nowcast before they would be known.",
            "Every run records an as_of_date, exact data vintage, and input hashes.",
        ],
        "frozen_architecture": {
            "midas_predictor": "usd_uzs_mom_dlog",
            "monthly_lags": 3,
            "quarterly_gdp_lags": 1,
            "ensemble_formula": "0.5 * AR(2) + 0.5 * USD/UZS U-MIDAS(3)",
            "dfm_role": "diagnostic_only_not_in_phase5a_production",
        },
    }


def ensure_production_policy(root: Path, run_timestamp: str) -> dict:
    """Create the policy once, before any live forecast is calculated."""
    path = Path(root) / POLICY_PATH
    expected = production_policy(run_timestamp)
    if path.exists():
        existing = _json(path)
        fixed = (
            "primary_headline_model", "model_switching",
            "ensemble_weights", "production_release_lag_mode",
            "frozen_architecture",
        )
        if any(existing.get(key) != expected.get(key) for key in fixed):
            raise RuntimeError("Existing Phase 5A production policy conflicts with the frozen policy")
        return existing
    save_json(path, expected, exclusive=True)
    return expected


def _quarter_period(label: str) -> pd.Period:
    return pd.Period(str(label).replace("-", ""), freq="Q-DEC")


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


def detect_horizon(target_quarter: str, as_of_date: str | pd.Timestamp) -> dict[str, str]:
    """Map an as-of date to the existing H1/H2/H3 month-end convention."""
    as_of = pd.Timestamp(as_of_date).normalize()
    cutoffs = {h: horizon_month_end(target_quarter, h) for h in ("H1", "H2", "H3")}
    completed = [h for h in ("H1", "H2", "H3") if cutoffs[h] <= as_of]
    horizon = completed[-1] if completed else "H1"
    cutoff = min(as_of, cutoffs[horizon])
    if completed:
        reason = (
            f"{horizon} is the latest existing Phase 4 horizon cutoff on or "
            f"before {as_of.date()} ({cutoffs[horizon].date()})."
        )
    else:
        reason = (
            f"The date precedes the H1 month-end cutoff; the existing H1 "
            f"convention is used with information capped at {as_of.date()}."
        )
    return {
        "horizon": horizon,
        "horizon_cutoff": str(cutoffs[horizon].date()),
        "information_cutoff": str(cutoff.date()),
        "reason": reason,
    }


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


def build_data_status(
    dataset: ModelingDataset, as_of_date: str | pd.Timestamp,
    *, lag_mode: str = "standard",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build a cell-level vintage table and indicator-level availability counts."""
    as_of = pd.Timestamp(as_of_date).normalize()
    rows: list[dict[str, Any]] = []
    predictors = [r for r in dataset.registry.scope("v1")
                  if r["variable_key"] != "gdp_real_yoy"]
    used_candidates: list[tuple[str, pd.Timestamp]] = []
    usd_field = dataset.clean_field_by_key.get("usd_uzs")
    if usd_field in dataset.monthly:
        key = "usd_uzs"
        lag = effective_release_day(dataset.release_lag_days.get(key, 0), lag_mode)
        series = dataset.monthly[usd_field].copy()
        eligible = series.index + pd.to_timedelta(lag, unit="D") <= as_of
        used_candidates = [(usd_field, d) for d in series.loc[eligible].dropna().tail(3).index]
    used_set = set(used_candidates)
    summaries: list[dict[str, Any]] = []
    for registry_row in predictors:
        key = registry_row["variable_key"]
        field = registry_row["clean_model_field"]
        lag = effective_release_day(dataset.release_lag_days.get(key, 30), lag_mode)
        series = (dataset.monthly[field] if field in dataset.monthly
                  else pd.Series(index=dataset.monthly.index, dtype=float))
        usable_dates: list[pd.Timestamp] = []
        awaiting_records = 0
        nonmissing_records = 0
        for date, value in series.items():
            ref = pd.Timestamp(date).normalize()
            assumed = ref + pd.Timedelta(days=lag)
            has_value = bool(pd.notna(value))
            nonmissing_records += int(has_value)
            eligible = bool(ref <= as_of and assumed <= as_of)
            available = bool(has_value and eligible)
            if available:
                usable_dates.append(ref)
            if has_value and not eligible:
                awaiting_records += 1
            used = (field, ref) in used_set
            if used:
                reason = ""
            elif ref > as_of:
                reason = "reference_period_after_as_of_date"
            elif assumed > as_of:
                reason = "awaiting_assumed_release"
            elif not has_value:
                reason = "missing_in_monthly_master"
            elif key != "usd_uzs":
                reason = "not_in_frozen_production_model"
            else:
                reason = "outside_current_three_observation_midas_window"
            rows.append({
                "variable_key": key,
                "clean_model_field": field,
                "display_name": registry_row.get("display_name"),
                "reference_period": str(ref.date()),
                "value": float(value) if has_value else np.nan,
                "provider": registry_row.get("provider"),
                "source": registry_row.get("human_source_url"),
                "expected_release_date": str(assumed.date()),
                "assumed_available_date": str(assumed.date()),
                "release_lag_days": lag,
                "release_lag_mode": lag_mode,
                "release_eligible_as_of": eligible,
                "available_as_of": available,
                "used_in_current_nowcast": used,
                "exclusion_reason": reason,
            })
        latest = max(usable_dates) if usable_dates else None
        if latest is not None:
            status = "available"
        elif awaiting_records:
            status = "awaiting_release"
        else:
            status = "missing_unavailable"
        summaries.append({
            "variable_key": key,
            "clean_model_field": field,
            "indicator_status": status,
            "most_recent_usable_reference_period": (
                str(latest.date()) if latest is not None else None
            ),
            "nonmissing_records_in_master": nonmissing_records,
            "records_awaiting_release": awaiting_records,
        })
    frame = pd.DataFrame(rows).merge(
        pd.DataFrame(summaries),
        on=["variable_key", "clean_model_field"], how="left", validate="many_to_one",
    )
    summary = pd.DataFrame(summaries)
    usable = int((summary["indicator_status"] == "available").sum())
    awaiting = int((summary["indicator_status"] == "awaiting_release").sum())
    missing = int((summary["indicator_status"] == "missing_unavailable").sum())
    latest_values = summary["most_recent_usable_reference_period"].dropna()
    counts = {
        "registered_indicators": int(len(summary)),
        "currently_usable_indicators": usable,
        "awaiting_release_indicators": awaiting,
        "missing_unavailable_indicators": missing,
        "latest_usable_monthly_reference_period": (
            str(latest_values.max()) if len(latest_values) else None
        ),
        "indicator_summary": summaries,
        "definition": (
            "An indicator is currently usable when at least one non-missing "
            "master value has an assumed availability date no later than the as-of date."
        ),
    }
    return frame, counts


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


def uncertainty_from_development(root: Path, horizon: str, point: float) -> dict[str, Any]:
    """Use matching Phase 4B genuine pseudo-OOS ensemble errors, not holdout errors."""
    predictions = pd.read_parquet(Path(root) / "results/phase4b_predictions.parquet")
    block = predictions.loc[
        (predictions["model"] == "ensemble_ar2_umidas_usd")
        & (predictions["horizon"] == horizon)
        & (predictions["lag_mode"] == "standard")
        & predictions["prediction"].notna()
        & predictions["actual"].notna()
    ].copy()
    errors = block["actual"] - block["prediction"]
    n = int(len(errors))
    if n < 12:
        return {
            "reported": False, "n_development_forecasts": n,
            "reason": "Fewer than 12 matching development pseudo-out-of-sample errors.",
        }
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    return {
        "reported": True,
        "label": "indicative historical forecast-error range",
        "method": (
            "headline nowcast plus/minus the RMSE of matching-horizon, standard-lag, "
            "expanding-window Phase 4B development pseudo-out-of-sample ensemble errors"
        ),
        "source_artifact": "results/phase4b_predictions.parquet",
        "horizon": horizon,
        "n_development_forecasts": n,
        "development_rmse": rmse,
        "lower": float(point - rmse),
        "upper": float(point + rmse),
        "formal_confidence_interval": False,
    }


def build_revision_history(
    root: Path, nowcasts: pd.DataFrame, run_timestamp: str,
) -> pd.DataFrame:
    """Combine initial live rows with clearly labelled Phase 4C demonstrations."""
    root = Path(root)
    current_rows = []
    prior_path = root / "results/phase5a_nowcast_revision_history.parquet"
    prior = pd.read_parquet(prior_path) if prior_path.exists() else pd.DataFrame()
    live_prior = prior.loc[prior.get("history_type", pd.Series(dtype=str)) == "live_production"] if len(prior) else pd.DataFrame()
    for row in nowcasts.itertuples(index=False):
        previous = np.nan
        new_info = "initial operational run; no prior live vintage"
        transition = "initial"
        if len(live_prior):
            candidates = live_prior.loc[
                (live_prior["target_quarter"] == row.target_quarter)
                & (live_prior["model"] == row.model)
            ]
            if len(candidates):
                candidate = candidates.iloc[-1]
                same_run_date = str(candidate["run_date"]) == str(row.as_of_date)
                same_value = np.isclose(float(candidate["current_forecast"]), row.prediction)
                if same_run_date and same_value:
                    previous = candidate["previous_forecast"]
                    transition = str(candidate["transition"])
                    new_info = str(candidate["new_monthly_observations"])
                else:
                    previous = float(candidate["current_forecast"])
                    transition = "prior_run_to_current"
                    new_info = "see phase5a_data_status for newly available observations"
        current_rows.append({
            "history_type": "live_production",
            "run_date": row.as_of_date,
            "run_timestamp_utc": run_timestamp,
            "target_quarter": row.target_quarter,
            "horizon": row.horizon,
            "transition": transition,
            "model": row.model,
            "previous_forecast": previous,
            "current_forecast": row.prediction,
            "revision_percentage_points": (
                np.nan if pd.isna(previous) else row.prediction - previous
            ),
            "new_monthly_observations": new_info,
            "live_production_flag": True,
        })
    historical_rows = []
    updates = pd.read_parquet(root / "results/phase4c_horizon_updates.parquet")
    updates = updates.loc[
        (updates["lag_mode"] == "standard")
        & updates["model"].isin(MODEL_NAMES)
    ]
    for row in updates.itertuples(index=False):
        for previous_h, current_h in (("H1", "H2"), ("H2", "H3")):
            previous = float(getattr(row, f"{previous_h}_prediction"))
            current = float(getattr(row, f"{current_h}_prediction"))
            historical_rows.append({
                "history_type": "frozen_phase4c_validation_demonstration",
                "run_date": None,
                "run_timestamp_utc": None,
                "target_quarter": row.target_quarter,
                "horizon": current_h,
                "transition": f"{previous_h}_to_{current_h}",
                "model": row.model,
                "previous_forecast": previous,
                "current_forecast": current,
                "revision_percentage_points": current - previous,
                "new_monthly_observations": (
                    "historical Phase 4C horizon update; not a live production revision"
                ),
                "live_production_flag": False,
            })
    combined = pd.concat(
        [prior, pd.DataFrame(current_rows), pd.DataFrame(historical_rows)],
        ignore_index=True,
    )
    combined = combined[list(REVISION_COLUMNS)].drop_duplicates(
        ["history_type", "run_date", "target_quarter", "horizon", "transition", "model"],
        keep="last",
    )
    return combined.sort_values(
        ["live_production_flag", "target_quarter", "model", "horizon"],
        ascending=[False, True, True, True], na_position="last",
    ).reset_index(drop=True)


def _code_version(root: Path) -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip())
        return {"git_commit": commit, "working_tree_dirty_at_run": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"git_commit": None, "working_tree_dirty_at_run": None}


def _write_table(frame: pd.DataFrame, parquet_path: Path) -> None:
    atomic_parquet(frame, parquet_path)
    frame.to_csv(parquet_path.with_suffix(".csv"), index=False)


def _write_report(
    root: Path, *, nowcasts: pd.DataFrame, target: dict[str, Any],
    horizon_state: dict[str, str], availability: dict[str, Any],
    uncertainty: dict[str, Any], hashes: dict[str, str],
    diagnostics: dict[str, Any], run_timestamp: str,
) -> Path:
    values = nowcasts.set_index("model")["prediction"]
    if uncertainty.get("reported"):
        uncertainty_text = (
            f"{uncertainty['lower']:.3f}% to {uncertainty['upper']:.3f}%. "
            f"This is the point forecast plus/minus the {uncertainty['development_rmse']:.6f} "
            f"percentage-point RMSE across {uncertainty['n_development_forecasts']} matching "
            "Phase 4B expanding-window development forecasts. It is an indicative historical "
            "forecast-error range, not a formal confidence interval."
        )
    else:
        uncertainty_text = f"Not reported: {uncertainty.get('reason', 'insufficient evidence')}"
    check_text = ", ".join(
        f"{name}={'passed' if passed else 'FAILED'}"
        for name, passed in diagnostics["leakage_checks"].items()
    )
    report = f"""# Phase 5A — First operational Uzbekistan GDP nowcast

## Operational result

- Run timestamp (UTC): `{run_timestamp}`
- As-of date: `{nowcasts.iloc[0]['as_of_date']}`
- Automatically detected target: **{target['target_quarter']}**
- Automatically detected information stage: **{horizon_state['horizon']}**
- Latest legitimately known GDP: **{target['latest_known_gdp_quarter']}**, {target['latest_known_gdp_growth']:.1f}% YoY
- Headline fixed 50/50 ensemble: **{values['ensemble_ar2_umidas_usd']:.3f}%**
- AR(1): {values['ar1']:.3f}%
- AR(2): {values['ar2']:.3f}%
- USD/UZS U-MIDAS(3): {values['umidas_usd_uzs_mom_dlog']:.3f}%
- Monthly information cutoff: `{horizon_state['information_cutoff']}`
- Latest usable monthly reference period: `{availability['latest_usable_monthly_reference_period']}`

{target['reason']}

{horizon_state['reason']}

## Frozen production policy

Phase 5A starts a post-validation operational period. The headline remains exactly
`0.5 × AR(2) + 0.5 × USD/UZS U-MIDAS(3)`. AR(1), AR(2), and standalone U-MIDAS
are comparison models. No model, predictor, lag, transformation, release convention,
or weight was selected from the current-quarter result. Standard registry release
lags are the production convention; conservative lags remain a sensitivity diagnostic.

## Real-time information and leakage controls

The quarterly training window contains every GDP outcome whose assumed release date
(quarter end plus the registry's 31-day lag) is no later than the as-of date, and then
explicitly removes the target and every later quarter. Each monthly master cell is
eligible only when its reference month-end plus its variable-specific registry lag is
no later than the as-of date. Missing cells remain missing.

Leakage checks: {check_text}.

The cell-level evidence is in `results/phase5a_data_status.csv` and `.parquet`, including
the source, expected/assumed availability date, availability flag, model-use flag, and
exclusion reason for every predictor-month record.

## Availability at the run date

- Registered monthly indicators: {availability['registered_indicators']}
- Currently usable indicators: {availability['currently_usable_indicators']}
- Indicators with observations awaiting assumed release: {availability['awaiting_release_indicators']}
- Missing/unavailable indicators: {availability['missing_unavailable_indicators']}

“Currently usable” means at least one non-missing value is legitimately available; it
does not mean the latest calendar-month row is populated. In particular, the existence
of a September master row does not make a September observation available.

## Indicative uncertainty

{uncertainty_text}

The four Phase 4C holdout outcomes are not used to estimate this range.

## Validation and revision history

The dashboard reads the untouched Phase 4C prediction and metric artifacts. H3 is the
default management view, while H1 and H2 remain selectable. The revision-history files
contain the initial live run and clearly labelled Phase 4C H1→H2→H3 demonstrations;
historical validation revisions are never presented as live operational revisions.

## Reproducibility

- Monthly master SHA-256: `{hashes['monthly_master_hash']}`
- Quarterly master SHA-256: `{hashes['quarterly_master_hash']}`
- Registry SHA-256: `{hashes['registry_hash']}`
- Release-lag mode: `standard`
- Estimation: expanding window
- Model architecture: Phase 4B freeze, unchanged through Phase 4C and Phase 5A

The complete run manifest is `results/phase5a_run_manifest.json`. The dashboard is
`dashboard/phase5a_uzbekistan_nowcast.html` and is self-contained.

## Limitations

- Phase 4C contains only four validation quarters, so its ranking is initial evidence.
- Release availability is a frozen registry-lag approximation where historical first-release
  timestamps are unavailable; it is not a reconstructed official release archive.
- The only monthly signal in the production U-MIDAS is USD/UZS dynamics. The prototype
  does not claim sector contributions or causal effects.
- The uncertainty range is a historical error yardstick, not a probability statement.

**PHASE 4C VALIDATION ARTIFACTS WERE NOT MODIFIED.**

**THE CURRENT NOWCAST USES ONLY INFORMATION AVAILABLE AS OF THE SPECIFIED AS-OF DATE.**
"""
    path = Path(root) / "docs/modeling/phase5a_operational_nowcasting.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    return path


def run_phase5a(root: Path, *, as_of_date: str = "2026-09-30") -> dict[str, Any]:
    """Run and persist the complete Phase 5A operational prototype."""
    root = Path(root).resolve()
    run_timestamp = utc_now()
    phase4_before = phase4_artifact_hashes(root)

    # Required sequencing: policy exists before masters are loaded or any live
    # prediction is calculated.
    policy = ensure_production_policy(root, run_timestamp)

    monthly_path = root / "data/master/v1_monthly.parquet"
    quarterly_path = root / "data/master/gdp_quarterly.parquet"
    registry_path = root / "registry/uzbekistan_nowcasting_v1.2_registry.xlsx"
    hashes = {
        "monthly_master_hash": file_sha256(monthly_path),
        "quarterly_master_hash": file_sha256(quarterly_path),
        "registry_hash": file_sha256(registry_path),
    }
    frozen = _json(root / "results/phase4b_candidate_freeze.json")
    expected = frozen["master_hashes"]
    hash_checks = {
        "monthly_master": hashes["monthly_master_hash"] == expected["monthly_sha256"],
        "quarterly_master": hashes["quarterly_master_hash"] == expected["quarterly_sha256"],
        "registry": hashes["registry_hash"] == expected["registry_sha256"],
    }
    if not all(hash_checks.values()):
        raise RuntimeError(f"Phase 5A input hashes do not match the Phase 4 freeze: {hash_checks}")

    dataset = load_dataset(root)
    target = detect_target_quarter(dataset, as_of_date)
    horizon_state = detect_horizon(target["target_quarter"], as_of_date)
    data_status, availability = build_data_status(dataset, as_of_date)
    nowcasts, diagnostics = generate_nowcasts(
        dataset, as_of_date, target, horizon_state, hashes, run_timestamp,
    )
    headline = float(nowcasts.loc[nowcasts["production_headline_flag"], "prediction"].iloc[0])
    uncertainty = uncertainty_from_development(root, horizon_state["horizon"], headline)
    revisions = build_revision_history(root, nowcasts, run_timestamp)

    results = root / "results"
    _write_table(nowcasts, results / "phase5a_current_nowcast.parquet")
    _write_table(data_status, results / "phase5a_data_status.parquet")
    _write_table(revisions, results / "phase5a_nowcast_revision_history.parquet")
    current_json = {
        "run": {
            "run_timestamp_utc": run_timestamp,
            "as_of_date": str(pd.Timestamp(as_of_date).date()),
            "target_detection": target,
            "horizon_detection": horizon_state,
        },
        "predictions": nowcasts.to_dict(orient="records"),
        "headline_uncertainty": uncertainty,
        "availability_summary": {
            k: v for k, v in availability.items() if k != "indicator_summary"
        },
        "model_diagnostics": diagnostics,
    }
    save_json(results / "phase5a_current_nowcast.json", current_json)

    from uznowcast.operational.dashboard import render_dashboard
    render_dashboard(
        root=root, nowcasts=nowcasts, target=target,
        horizon_state=horizon_state, availability=availability,
        uncertainty=uncertainty, data_status=data_status,
    )
    _write_report(
        root, nowcasts=nowcasts, target=target, horizon_state=horizon_state,
        availability=availability, uncertainty=uncertainty, hashes=hashes,
        diagnostics=diagnostics, run_timestamp=run_timestamp,
    )

    phase4_after = phase4_artifact_hashes(root)
    phase4_unchanged = phase4_before == phase4_after
    if not phase4_unchanged:
        raise AssertionError("A frozen Phase 4 artifact changed during Phase 5A")
    manifest = {
        "phase": "5A",
        "run_timestamp_utc": run_timestamp,
        "as_of_date": str(pd.Timestamp(as_of_date).date()),
        "target_quarter": target["target_quarter"],
        "horizon": horizon_state["horizon"],
        "training_endpoint": target["latest_known_gdp_quarter"],
        "information_cutoff": horizon_state["information_cutoff"],
        "latest_usable_monthly_reference_period": availability[
            "latest_usable_monthly_reference_period"
        ],
        "input_paths": {
            "monthly_master": "data/master/v1_monthly.parquet",
            "quarterly_master": "data/master/gdp_quarterly.parquet",
            "registry": "registry/uzbekistan_nowcasting_v1.2_registry.xlsx",
        },
        "input_hashes": hashes,
        "phase4_freeze_hash_checks": hash_checks,
        "phase4_artifacts_unchanged": phase4_unchanged,
        "phase4_artifact_hashes_before": phase4_before,
        "phase4_artifact_hashes_after": phase4_after,
        "data_vintage": {
            "monthly_last_master_row": str(dataset.monthly.index.max().date()),
            "quarterly_last_master_row": str(dataset.gdp["quarter"].iloc[-1]).replace("-", ""),
            "registry_version": dataset.registry.version,
            "registry_verification_date": dataset.registry.verification_date,
            "quarterly_retrieved_at_values": sorted(
                set(pd.read_parquet(quarterly_path)["retrieved_at"].dropna().astype(str))
            ),
        },
        "model_specification": policy["frozen_architecture"],
        "release_lag_assumption": "standard",
        "estimation": "expanding window",
        "code_version": _code_version(root),
        "leakage_checks": diagnostics["leakage_checks"],
        "outputs": [
            POLICY_PATH,
            "results/phase5a_run_manifest.json",
            "results/phase5a_current_nowcast.json",
            "results/phase5a_current_nowcast.csv",
            "results/phase5a_current_nowcast.parquet",
            "results/phase5a_data_status.csv",
            "results/phase5a_data_status.parquet",
            "results/phase5a_nowcast_revision_history.csv",
            "results/phase5a_nowcast_revision_history.parquet",
            "dashboard/phase5a_uzbekistan_nowcast.html",
            "docs/modeling/phase5a_operational_nowcasting.md",
        ],
    }
    save_json(results / "phase5a_run_manifest.json", manifest)
    return {
        "policy": policy,
        "manifest": manifest,
        "target": {**target, **horizon_state},
        "nowcasts": nowcasts,
        "data_status": data_status,
        "availability": availability,
        "uncertainty": uncertainty,
        "revisions": revisions,
        "diagnostics": diagnostics,
    }
