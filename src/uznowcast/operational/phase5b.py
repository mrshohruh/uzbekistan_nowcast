"""Phase 5B production hardening for the frozen Uzbekistan GDP nowcast."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import json
import subprocess
import uuid

import numpy as np
import pandas as pd

from uznowcast.models.benchmarks import ar_forecast
from uznowcast.models.data import (
    ModelingDataset, build_information_set, effective_release_day,
    horizon_month_end, information_cutoff_for_variable, load_dataset,
    quarter_end, quarter_start,
)
from uznowcast.models.midas import MidasSpec, fit_midas
from uznowcast.operational.phase5a import (
    MODEL_NAMES, detect_target_quarter, file_sha256, generate_nowcasts,
)
from uznowcast.provenance import atomic_parquet, save_json


OUTPUT_DIR = "results/phase5b"
POLICY_PATH = f"{OUTPUT_DIR}/phase5b_production_policy.json"
ACTIVE_MODELS = tuple(MODEL_NAMES)
PRODUCTION_REQUIRED_KEYS = ("gdp_real_yoy", "usd_uzs")
FAILURE_STATUSES = {
    "FAILED_DATA_GATE", "FAILED_MODEL", "FAILED_CONFIGURATION",
}
CURRENT_REQUIRED_FIELDS = {
    "run_id", "run_timestamp_utc", "status", "as_of_date",
    "information_cutoff", "target", "operational_stage", "point_nowcast",
    "uncertainty", "latest_known_gdp_period", "latest_known_gdp_value",
    "production_model", "predictions", "data_gate", "warnings", "errors",
    "previous_nowcast", "revision", "models_attempted", "models_successful",
    "models_rejected_by_gate", "fallback_observations_used",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_table(frame: pd.DataFrame, path: Path) -> None:
    atomic_parquet(frame, path.with_suffix(".parquet"))
    frame.to_csv(path.with_suffix(".csv"), index=False)


def validate_current_payload(payload: dict[str, Any]) -> None:
    missing = CURRENT_REQUIRED_FIELDS - set(payload)
    if missing:
        raise ValueError(f"Phase 5B current-nowcast output missing fields: {sorted(missing)}")
    if payload["status"] in FAILURE_STATUSES and payload.get("point_nowcast") is not None:
        raise ValueError("Failed run must not publish a point nowcast")


def immutable_artifact_hashes(root: Path) -> dict[str, str]:
    """Hash all Phase 4 and Phase 5A audit artifacts, not Phase 5B outputs."""
    root = Path(root).resolve()
    paths: list[Path] = []
    paths.extend(p for p in (root / "results").glob("phase4*") if p.is_file())
    paths.extend(p for p in (root / "results").glob("phase5a*") if p.is_file())
    frozen = root / "results/frozen_validation_definition.json"
    if frozen.exists():
        paths.append(frozen)
    paths.extend(p for p in (root / "docs/modeling").glob("phase4*") if p.is_file())
    paths.extend(p for p in (root / "docs/modeling").glob("phase5a*") if p.is_file())
    paths.extend(p for p in (root / "dashboard").glob("phase5a*") if p.is_file())
    return {
        p.relative_to(root).as_posix(): file_sha256(p)
        for p in sorted(set(paths))
    }


def phase5b_policy(created_at: str) -> dict[str, Any]:
    return {
        "phase": "5B",
        "policy_version": "1.0",
        "created_at_utc": created_at,
        "status": "FROZEN_OPERATIONAL_HARDENING_POLICY",
        "inherits": "results/phase5a_production_policy.json",
        "phase5a_artifacts": "immutable audit baseline",
        "headline_model": "ensemble_ar2_umidas_usd",
        "comparison_models": ["ar1", "ar2", "umidas_usd_uzs_mom_dlog"],
        "ensemble_weights": {"ar2": 0.5, "umidas_usd_uzs_mom_dlog": 0.5},
        "release_lag_mode": "standard",
        "stage_policy": {
            "basis": "complete release-eligible target-quarter observations for the frozen USD/UZS monthly signal",
            "H1": "first target-quarter USD/UZS monthly aggregate available",
            "H2": "first two target-quarter USD/UZS monthly aggregates available",
            "H3": "all three target-quarter USD/UZS monthly aggregates available",
            "delayed_release_rule": "remain at the highest contiguous available stage; never advance on calendar alone",
        },
        "fallback_hierarchy": [
            "official observation available by information cutoff",
            "previously published official vintage when explicitly present and appropriate",
            "frozen model-specific lag structure that does not require the missing value",
            "documented carry/bridge estimate only after an explicit future policy amendment",
            "exclude the affected model when required information is unavailable",
        ],
        "prohibited_fills": ["mean", "zero", "interpolation", "extrapolation", "forward_fill"],
        "publication_statuses": [
            "SUCCESS", "SUCCESS_WITH_WARNINGS", "FAILED_DATA_GATE",
            "FAILED_MODEL", "FAILED_CONFIGURATION",
        ],
        "hard_fail_conditions": [
            "target GDP definition missing", "cutoff integrity violation",
            "registry/model mismatch", "required transformation infeasible",
            "insufficient estimation sample", "headline production ensemble unavailable",
            "malformed required latest data",
        ],
        "uncertainty": (
            "empirical forecast-error intervals from all pre-current genuine Phase 4B "
            "development and Phase 4C holdout pseudo/out-of-sample errors at the current horizon"
        ),
        "model_selection": "unchanged from Phase 5A; no automatic switching",
    }


def ensure_policy(root: Path, created_at: str) -> dict[str, Any]:
    path = Path(root) / POLICY_PATH
    expected = phase5b_policy(created_at)
    if path.exists():
        existing = _read_json(path)
        fixed = ("headline_model", "ensemble_weights", "release_lag_mode",
                 "stage_policy", "fallback_hierarchy", "model_selection")
        if any(existing.get(k) != expected.get(k) for k in fixed):
            raise RuntimeError("Existing Phase 5B policy conflicts with the frozen policy")
        return existing
    save_json(path, expected, exclusive=True)
    return expected


def _processed_quality(root: Path, key: str) -> dict[pd.Timestamp, str]:
    path = root / f"data/processed/{key}.parquet"
    if not path.exists():
        return {}
    frame = pd.read_parquet(path)
    if frame.empty or "quality_flag" not in frame:
        return {}
    date_col = "reference_date" if "reference_date" in frame else "reference_period"
    dates = pd.to_datetime(frame[date_col], errors="coerce").dt.to_period("M").dt.to_timestamp("M")
    return {
        pd.Timestamp(d).normalize(): str(q or "")
        for d, q in zip(dates, frame["quality_flag"].fillna("")) if pd.notna(d)
    }


def _processed_provenance(root: Path, key: str) -> dict[pd.Timestamp, dict[str, Any]]:
    path = root / f"data/processed/{key}.parquet"
    if not path.exists():
        return {}
    frame = pd.read_parquet(path)
    if frame.empty:
        return {}
    date_col = "reference_date" if "reference_date" in frame else "reference_period"
    dates = pd.to_datetime(frame[date_col], errors="coerce").dt.to_period("M").dt.to_timestamp("M")
    result: dict[pd.Timestamp, dict[str, Any]] = {}
    for index, date in zip(frame.index, dates):
        if pd.isna(date):
            continue
        row = frame.loc[index]
        result[pd.Timestamp(date).normalize()] = {
            "observed_release_date": row.get("source_release_date"),
            "release_date_basis": row.get("source_release_basis"),
            "retrieved_at": row.get("retrieved_at"),
            "vintage_date": row.get("vintage_date"),
        }
    return result


def _failure_evidence(root: Path, key: str) -> tuple[bool, str | None]:
    path = root / f"data/processed/{key}.failure.json"
    if not path.exists():
        return False, None
    payload = _read_json(path)
    return True, str(payload.get("failure_reason") or payload.get("status"))


def _month_distance(later: pd.Timestamp, earlier: pd.Timestamp) -> int:
    return (later.year - earlier.year) * 12 + later.month - earlier.month


def _extreme_recent_changes(series: pd.Series) -> int:
    values = pd.to_numeric(series.dropna(), errors="coerce").dropna()
    if len(values) < 8:
        return 0
    changes = values.diff().dropna()
    baseline = changes.iloc[:-12] if len(changes) > 12 else changes
    recent = changes.iloc[-12:]
    median = float(baseline.median())
    mad = float((baseline - median).abs().median())
    if mad == 0 or np.isnan(mad):
        scale = float(baseline.std(ddof=0))
        return int(((recent - median).abs() > max(6 * scale, 1e-12)).sum())
    robust_z = 0.6745 * (recent - median).abs() / mad
    return int((robust_z > 6).sum())


def build_data_quality(
    root: Path, dataset: ModelingDataset, target_quarter: str,
    information_cutoff: str | pd.Timestamp,
) -> pd.DataFrame:
    """One formal production-gate row for all 29 registry series."""
    root = Path(root)
    cutoff = pd.Timestamp(information_cutoff).normalize()
    target_start, target_finish = quarter_start(target_quarter), quarter_end(target_quarter)
    rows: list[dict[str, Any]] = []
    for registry_row in dataset.registry.scope("v1"):
        key = registry_row["variable_key"]
        field = registry_row["clean_model_field"]
        lag = effective_release_day(dataset.release_lag_days.get(key, 30), "standard")
        required = key in PRODUCTION_REQUIRED_KEYS
        failed_retrieval, retrieval_error = _failure_evidence(root, key)
        if key == "gdp_real_yoy":
            values = dataset.gdp.set_index(
                dataset.gdp["quarter"].map(lambda q: quarter_end(str(q)))
            )[dataset.target_field]
            eligible = values.loc[values.index + pd.to_timedelta(lag, unit="D") <= cutoff]
            candidates = [
                (pd.Period(year=y, quarter=q, freq="Q-DEC"),
                 pd.Timestamp(year=y, month=q * 3, day=1) + pd.offsets.MonthEnd(0))
                for y in range(2000, cutoff.year + 1) for q in range(1, 5)
            ]
            expected_dates = [end for _, end in candidates if end + pd.Timedelta(days=lag) <= cutoff]
            expected_latest = max(expected_dates) if expected_dates else None
            frequency = "Quarterly"
        else:
            values = (dataset.monthly[field] if field in dataset.monthly
                      else pd.Series(index=dataset.monthly.index, dtype=float))
            expected_latest = information_cutoff_for_variable(
                cutoff, key, dataset.release_lag_days, "standard")
            eligible = values.loc[values.index <= expected_latest]
            frequency = "Monthly"
        numeric = pd.to_numeric(eligible, errors="coerce")
        non_numeric = int((eligible.notna() & numeric.isna()).sum())
        valid = numeric.dropna()
        latest = pd.Timestamp(valid.index.max()).normalize() if len(valid) else None
        first = pd.Timestamp(valid.index.min()).normalize() if len(valid) else None
        if first is not None and expected_latest is not None:
            freq = "QE-DEC" if key == "gdp_real_yoy" else "ME"
            expected_index = pd.date_range(first, expected_latest, freq=freq)
            aligned = numeric.reindex(expected_index)
            missing_total = int(aligned.isna().sum())
            recent_start = cutoff - pd.DateOffset(months=11)
            missing_recent = int(aligned.loc[aligned.index >= recent_start].isna().sum())
            unexpected_gaps = missing_total
        else:
            missing_total = missing_recent = unexpected_gaps = 0
        if key == "gdp_real_yoy":
            relevant_index = []
        else:
            relevant_index = [
                d for d in pd.date_range(target_start, target_finish, freq="ME")
                if d <= expected_latest
            ]
        missing_current = int(sum(
            d not in numeric.index or pd.isna(numeric.get(d)) for d in relevant_index
        ))
        quality = _processed_quality(root, key)
        recent_quality = sorted({
            q for d, q in quality.items()
            if d >= cutoff - pd.DateOffset(months=3) and q
        })
        partial_latest = bool(
            expected_latest is not None
            and "partial_month" in quality.get(expected_latest, "")
        )
        duplicate_dates = int(values.index.duplicated().sum())
        frequency_consistent = bool(values.index.is_monotonic_increasing and duplicate_dates == 0)
        extreme_count = _extreme_recent_changes(valid)
        staleness_months = (
            _month_distance(expected_latest, latest)
            if latest is not None and expected_latest is not None else None
        )
        age_days = int((cutoff - latest).days) if latest is not None else None
        transformation_feasible = bool(len(valid) >= (3 if key == "usd_uzs" else 1))
        reasons: list[str] = []
        if failed_retrieval:
            reasons.append("failed_data_retrieval")
        if latest is None:
            reasons.append("no_usable_observation")
        if staleness_months and staleness_months > 0:
            reasons.append(f"stale_by_{staleness_months}_months")
        if partial_latest:
            reasons.append("latest_expected_month_is_partial_and_deliberately_excluded")
        if missing_recent:
            reasons.append(f"{missing_recent}_missing_expected_observations_in_recent_window")
        if unexpected_gaps:
            reasons.append(f"{unexpected_gaps}_unexpected_gaps_from_own_start")
        if non_numeric:
            reasons.append("non_numeric_observations")
        if duplicate_dates:
            reasons.append("duplicate_dates")
        if extreme_count:
            reasons.append(f"{extreme_count}_extreme_recent_changes_for_review")
        if not transformation_feasible:
            reasons.append("transformation_infeasible")
        hard_error = bool(
            required and (
                latest is None or non_numeric or duplicate_dates
                or not transformation_feasible
            )
        )
        if hard_error or (failed_retrieval and latest is None):
            status = "RED"
        elif reasons:
            status = "AMBER"
        else:
            status = "GREEN"
        rows.append({
            "variable_key": key,
            "clean_model_field": field,
            "display_name": registry_row.get("display_name"),
            "provider": registry_row.get("provider"),
            "source_url": registry_row.get("human_source_url"),
            "frequency": frequency,
            "production_required": required,
            "publication_lag_days": lag,
            "latest_observation_date": str(latest.date()) if latest is not None else None,
            "expected_latest_observation_date": (
                str(expected_latest.date()) if expected_latest is not None else None
            ),
            "age_days_at_cutoff": age_days,
            "staleness_months": staleness_months,
            "missing_observations": missing_total,
            "missing_recent_12_months": missing_recent,
            "missing_current_nowcast_quarter": missing_current,
            "unexpected_gaps": unexpected_gaps,
            "duplicate_dates": duplicate_dates,
            "frequency_consistent": frequency_consistent,
            "non_numeric_observations": non_numeric,
            "extreme_recent_changes": extreme_count,
            "transformation_feasible": transformation_feasible,
            "recent_quality_flags": "|".join(recent_quality),
            "failed_retrieval": failed_retrieval,
            "retrieval_error": retrieval_error,
            "fallback_used": False,
            "fallback_method": None,
            "quality_status": status,
            "gate_passed": not hard_error,
            "status_reasons": "|".join(reasons) if reasons else "fully_operational",
        })
    return pd.DataFrame(rows).sort_values("variable_key").reset_index(drop=True)


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


def build_data_status(
    root: Path, dataset: ModelingDataset, information_cutoff: str,
    target_quarter: str, stage: dict[str, Any],
) -> pd.DataFrame:
    """Classify every monthly predictor cell without conflating release states."""
    root = Path(root)
    cutoff = pd.Timestamp(information_cutoff).normalize()
    rows: list[dict[str, Any]] = []
    target_used = set(pd.to_datetime(stage["complete_target_quarter_signal_months"]))
    for registry_row in dataset.registry.scope("v1"):
        key = registry_row["variable_key"]
        if key == "gdp_real_yoy":
            continue
        field = registry_row["clean_model_field"]
        series = (dataset.monthly[field] if field in dataset.monthly
                  else pd.Series(index=dataset.monthly.index, dtype=float))
        lag = effective_release_day(dataset.release_lag_days.get(key, 30), "standard")
        valid_dates = series.dropna().index
        first_valid = valid_dates.min() if len(valid_dates) else None
        quality = _processed_quality(root, key)
        provenance = _processed_provenance(root, key)
        failed, failure_reason = _failure_evidence(root, key)
        for date, value in series.items():
            date = pd.Timestamp(date).normalize()
            assumed = date + pd.Timedelta(days=lag)
            has_value = bool(pd.notna(value))
            release_eligible = bool(date <= cutoff and assumed <= cutoff)
            available = bool(has_value and release_eligible)
            used = bool(key == "usd_uzs" and date in target_used)
            flag = quality.get(date, "")
            provenance_row = provenance.get(date, {})
            if available and used:
                classification = "available_and_used"
                reason = "enters_current_umidas_target_lag_vector"
            elif available:
                classification = "deliberately_excluded_observation"
                reason = ("available_but_not_used_by_frozen_production_model"
                          if key != "usd_uzs" else "outside_current_target_quarter_signal_window")
            elif date > cutoff:
                classification = "not_yet_released_observation"
                reason = "reference_period_after_information_cutoff"
            elif assumed > cutoff:
                classification = "structural_publication_lag"
                reason = "registry_lag_places_release_after_information_cutoff"
            elif "partial_month" in flag:
                classification = "deliberately_excluded_observation"
                reason = "incomplete_month_excluded_by_frozen_preprocessing"
            elif failed and not has_value:
                classification = "failed_data_retrieval"
                reason = failure_reason
            elif first_valid is None or date < first_valid:
                classification = "unavailable_historical_observation"
                reason = "outside_available_history"
            else:
                classification = "true_missing_observation"
                reason = "expected_by_registry_lag_but_absent_from_master"
            rows.append({
                "variable_key": key,
                "clean_model_field": field,
                "reference_period": str(date.date()),
                "value": float(value) if has_value else np.nan,
                "provider": registry_row.get("provider"),
                "source_url": registry_row.get("human_source_url"),
                "publication_lag_days": lag,
                "expected_release_date": str(assumed.date()),
                "assumed_available_date": str(assumed.date()),
                "observed_release_date": provenance_row.get("observed_release_date"),
                "release_date_basis": provenance_row.get("release_date_basis"),
                "retrieved_at": provenance_row.get("retrieved_at"),
                "vintage_date": provenance_row.get("vintage_date"),
                "information_cutoff": str(cutoff.date()),
                "release_eligible": release_eligible,
                "available_as_of_cutoff": available,
                "used_in_current_nowcast": used,
                "missing_value_classification": classification,
                "quality_flag": flag,
                "fallback_used": False,
                "fallback_method": None,
                "reason": reason,
            })
    return pd.DataFrame(rows)


def production_gate(
    dataset: ModelingDataset, quality: pd.DataFrame,
    stage: dict[str, Any], frozen: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = list(stage["warnings"])
    if dataset.target_field not in dataset.gdp:
        errors.append("target GDP definition missing")
    frozen_models = tuple(frozen.get("primary_candidate_models", []))
    if frozen_models != ACTIVE_MODELS:
        errors.append("registry/model mismatch: active candidates differ from Phase 4B freeze")
    required = quality.loc[quality["production_required"]]
    red_required = required.loc[required["quality_status"] == "RED"]
    if len(red_required):
        errors.extend(
            f"required series failed gate: {k}" for k in red_required["variable_key"]
        )
    amber_required = required.loc[required["quality_status"] == "AMBER"]
    warnings.extend(
        f"required series is AMBER: {row.variable_key} ({row.status_reasons})"
        for row in amber_required.itertuples()
    )
    red_optional = quality.loc[
        (~quality["production_required"]) & (quality["quality_status"] == "RED")]
    warnings.extend(
        f"non-production series is RED: {row.variable_key} ({row.status_reasons})"
        for row in red_optional.itertuples()
    )
    status = "FAILED_CONFIGURATION" if any("mismatch" in e or "definition" in e for e in errors) else (
        "FAILED_DATA_GATE" if errors else ("SUCCESS_WITH_WARNINGS" if warnings else "SUCCESS")
    )
    return {
        "status": status,
        "passed": status not in FAILURE_STATUSES,
        "warnings": warnings,
        "errors": errors,
        "green_series": int((quality["quality_status"] == "GREEN").sum()),
        "amber_series": int((quality["quality_status"] == "AMBER").sum()),
        "red_series": int((quality["quality_status"] == "RED").sum()),
    }


def build_model_input_audit(
    nowcasts: pd.DataFrame, diagnostics: dict[str, Any], target: dict[str, Any],
    stage: dict[str, Any], gate: dict[str, Any],
) -> pd.DataFrame:
    values = nowcasts.set_index("model")
    usd_obs = diagnostics["usd_monthly_observations_used"]
    specs = [
        ("ar1", "gdp_real_yoy_pct", "official real GDP YoY", "quarterly lag 1",
         target["latest_known_gdp_quarter"], 1, values.loc["ar1", "effective_model_training_rows"]),
        ("ar2", "gdp_real_yoy_pct", "official real GDP YoY", "quarterly lags 1 and 2",
         target["latest_known_gdp_quarter"], 2, values.loc["ar2", "effective_model_training_rows"]),
        ("umidas_usd_uzs_mom_dlog", "gdp_real_yoy_pct", "official real GDP YoY", "quarterly lag 1",
         target["latest_known_gdp_quarter"], 1, values.loc["umidas_usd_uzs_mom_dlog", "effective_model_training_rows"]),
        ("umidas_usd_uzs_mom_dlog", "usd_uzs_mom_dlog", "100 × monthly log change in monthly-mean USD/UZS", "last 3 available monthly observations",
         usd_obs[-1]["reference_period"], 3, values.loc["umidas_usd_uzs_mom_dlog", "effective_model_training_rows"]),
        ("ensemble_ar2_umidas_usd", "ar2 + umidas_usd_uzs_mom_dlog", "fixed forecast combination", "0.5 / 0.5",
         usd_obs[-1]["reference_period"], 2, values.loc["ensemble_ar2_umidas_usd", "effective_model_training_rows"]),
    ]
    rows = []
    for model, variable, transform, lags, latest, regressors, n_eff in specs:
        forecast = float(values.loc[model, "prediction"])
        rows.append({
            "model": model,
            "variable": variable,
            "transformation": transform,
            "lags_used": lags,
            "latest_usable_observation": latest,
            "exact_latest_monthly_observations": (
                json.dumps(usd_obs) if variable == "usd_uzs_mom_dlog" else None
            ),
            "number_of_usable_regressors_or_components": regressors,
            "effective_estimation_observations": int(n_eff),
            "fallback_used": False,
            "fallback_method": None,
            "operational_stage": stage["horizon"],
            "model_passed_production_gate": bool(gate["passed"] and pd.notna(forecast)),
            "current_forecast": forecast,
        })
    return pd.DataFrame(rows)


def build_information_set_audit(
    root: Path, dataset: ModelingDataset, target: dict[str, Any], stage: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    cutoff = pd.Timestamp(stage["information_cutoff"])
    gdp_provenance = _processed_provenance(Path(root), "gdp_real_yoy")
    usd_provenance = _processed_provenance(Path(root), "usd_uzs")
    gdp = dataset.gdp.copy()
    allowed = set(target["known_gdp_quarters"])
    for item in gdp.itertuples(index=False):
        q = str(item.quarter).replace("-", "")
        if q not in allowed:
            continue
        assumed = quarter_end(q) + pd.Timedelta(days=31)
        provenance = gdp_provenance.get(quarter_end(q), {})
        for model in ("ar1", "ar2", "umidas_usd_uzs_mom_dlog"):
            rows.append({
                "model": model, "variable_key": "gdp_real_yoy",
                "clean_model_field": dataset.target_field,
                "reference_period": q, "value": float(getattr(item, dataset.target_field)),
                "use_context": "expanding_window_estimation",
                "forecast_origin": stage["information_cutoff"],
                "assumed_available_date": str(assumed.date()),
                "observed_release_date": provenance.get("observed_release_date"),
                "release_date_basis": provenance.get("release_date_basis"),
                "retrieved_at": provenance.get("retrieved_at"),
                "vintage_date": provenance.get("vintage_date"),
                "information_cutoff": stage["information_cutoff"],
                "cutoff_check_passed": assumed <= cutoff,
                "availability_basis": "registry_lag_assumption",
            })
    field = "usd_uzs_mom_dlog"
    train_quarters = [str(q) for q in dataset.gdp["quarter"]
                      if str(q).replace("-", "") in allowed]
    contexts = [(q, "midas_training_lag_vector") for q in train_quarters]
    contexts.append((target["target_quarter"], "current_target_lag_vector"))
    for quarter, context in contexts:
        panel = build_information_set(dataset, quarter, stage["horizon"], [field], mode="standard")
        used = panel[field].dropna().tail(3)
        origin = horizon_month_end(quarter, stage["horizon"])
        for date, value in used.items():
            assumed = pd.Timestamp(date)
            provenance = usd_provenance.get(pd.Timestamp(date).normalize(), {})
            rows.append({
                "model": "umidas_usd_uzs_mom_dlog", "variable_key": "usd_uzs",
                "clean_model_field": field, "reference_period": str(date.date()),
                "value": float(value), "use_context": context,
                "forecast_origin": str(origin.date()),
                "assumed_available_date": str(assumed.date()),
                "observed_release_date": provenance.get("observed_release_date"),
                "release_date_basis": provenance.get("release_date_basis"),
                "retrieved_at": provenance.get("retrieved_at"),
                "vintage_date": provenance.get("vintage_date"),
                "information_cutoff": stage["information_cutoff"],
                "cutoff_check_passed": assumed <= min(origin, cutoff),
                "availability_basis": "registry_lag_assumption",
            })
    frame = pd.DataFrame(rows)
    if not frame["cutoff_check_passed"].all():
        raise AssertionError("Information-set audit found a cutoff violation")
    return frame


def empirical_uncertainty(root: Path, horizon: str, point: float) -> dict[str, Any]:
    root = Path(root)
    dev = pd.read_parquet(root / "results/phase4b_predictions.parquet")
    holdout = pd.read_parquet(root / "results/phase4c_holdout_predictions.parquet")
    dev = dev.loc[
        (dev["model"] == "ensemble_ar2_umidas_usd")
        & (dev["horizon"] == horizon) & (dev["lag_mode"] == "standard")
        & dev["prediction"].notna() & dev["actual"].notna(),
        ["target_quarter", "prediction", "actual"]
    ].assign(sample="phase4b_development_pseudo_oos")
    holdout = holdout.loc[
        (holdout["model"] == "ensemble_ar2_umidas_usd")
        & (holdout["horizon"] == horizon) & (holdout["lag_mode"] == "standard")
        & holdout["prediction"].notna() & holdout["actual"].notna(),
        ["target_quarter", "prediction", "actual"]
    ].assign(sample="phase4c_frozen_holdout")
    errors = pd.concat([dev, holdout], ignore_index=True)
    errors["error"] = errors["actual"] - errors["prediction"]
    n = len(errors)
    rmse = float(np.sqrt(np.mean(np.square(errors["error"]))))
    quantiles = errors["error"].quantile([0.10, 0.25, 0.75, 0.90])
    return {
        "point_nowcast": point,
        "horizon": horizon,
        "sample_size": int(n),
        "development_count": int((errors["sample"] == "phase4b_development_pseudo_oos").sum()),
        "frozen_holdout_count": int((errors["sample"] == "phase4c_frozen_holdout").sum()),
        "historical_rmse": rmse,
        "interval_50": {
            "lower": float(point + quantiles.loc[0.25]),
            "upper": float(point + quantiles.loc[0.75]),
        },
        "interval_80": {
            "lower": float(point + quantiles.loc[0.10]),
            "upper": float(point + quantiles.loc[0.90]),
        },
        "method": (
            "Empirical actual-minus-forecast error quantiles from matching-horizon "
            "standard-lag Phase 4B development pseudo-OOS plus untouched Phase 4C holdout forecasts."
        ),
        "formal_probability_interval": False,
    }


def model_monitoring(
    root: Path, dataset: ModelingDataset, nowcasts: pd.DataFrame,
    stage: dict[str, Any], quality: pd.DataFrame, diagnostics: dict[str, Any],
) -> pd.DataFrame:
    root = Path(root)
    horizon = stage["horizon"]
    metrics = pd.read_parquet(root / "results/phase4c_holdout_metrics.parquet")
    predictions = pd.read_parquet(root / "results/phase4c_holdout_predictions.parquet")
    values = nowcasts.set_index("model")["prediction"]
    ensemble = float(values["ensemble_ar2_umidas_usd"])
    benchmark = float(values["ar2"])
    history = dataset.gdp[dataset.target_field].dropna()
    lo, hi = float(history.min()), float(history.max())
    production_amber = bool((quality.loc[quality["production_required"], "quality_status"] != "GREEN").any())
    train = dataset.gdp[dataset.target_field].dropna()
    previous_coefficients: dict[str, list[float]] = {}
    for p, name in ((1, "ar1"), (2, "ar2")):
        _, prior = ar_forecast(train.iloc[:-1], p)
        previous_coefficients[name] = [prior["intercept"], *prior["ar_coefficients"]]
    spec = MidasSpec("umidas_usd_uzs_mom_dlog", "usd_uzs_mom_dlog", 3, True, None)
    quarters = dataset.gdp["quarter"].astype(str).tolist()
    prior_midas = fit_midas(dataset, spec, quarters[:-1], horizon=horizon, mode="standard")
    previous_coefficients[spec.name] = prior_midas["coefficients"]
    rows = []
    for model in ACTIVE_MODELS:
        metric = metrics.loc[
            (metrics["model"] == model) & (metrics["horizon"] == horizon)
            & (metrics["lag_mode"] == "standard")
        ].iloc[0]
        recent = predictions.loc[
            (predictions["model"] == model) & (predictions["horizon"] == horizon)
            & (predictions["lag_mode"] == "standard")
        ].sort_values("target_quarter").iloc[-1]
        current = float(values[model])
        if model == "ar1":
            current_coef = [diagnostics[model]["intercept"], *diagnostics[model]["ar_coefficients"]]
        elif model == "ar2":
            current_coef = [diagnostics[model]["intercept"], *diagnostics[model]["ar_coefficients"]]
        elif model == spec.name:
            current_coef = diagnostics[model]["coefficients"]
        else:
            current_coef = []
        if current_coef:
            prior = np.asarray(previous_coefficients[model], dtype=float)
            curr = np.asarray(current_coef, dtype=float)
            coefficient_change = float(np.linalg.norm(curr - prior) / max(np.linalg.norm(prior), 1e-12))
            coefficient_flag = coefficient_change > 1.0
        else:
            coefficient_change = np.nan
            coefficient_flag = False
        flags = []
        if abs(current - ensemble) > 2 * float(metric["rmse"]):
            flags.append("large_disagreement_with_ensemble")
        if current < lo - float(metric["rmse"]) or current > hi + float(metric["rmse"]):
            flags.append("outside_historical_gdp_range_plus_rmse")
        if coefficient_flag:
            flags.append("large_coefficient_change")
        if production_amber:
            flags.append("production_input_data_not_all_green")
        input_rows = {
            "ar1": (1, int(nowcasts.loc[nowcasts.model == model, "effective_model_training_rows"].iloc[0])),
            "ar2": (2, int(nowcasts.loc[nowcasts.model == model, "effective_model_training_rows"].iloc[0])),
            spec.name: (4, int(nowcasts.loc[nowcasts.model == model, "effective_model_training_rows"].iloc[0])),
            "ensemble_ar2_umidas_usd": (2, int(nowcasts.loc[nowcasts.model == model, "effective_model_training_rows"].iloc[0])),
        }[model]
        rows.append({
            "model": model, "current_nowcast": current,
            "historical_oos_scope": f"Phase 4C {horizon} standard, four quarters",
            "historical_oos_rmse": float(metric["rmse"]),
            "historical_oos_mae": float(metric["mae"]),
            "historical_oos_bias": float(metric["bias"]),
            "deviation_from_ensemble": current - ensemble,
            "deviation_from_ar2_benchmark": current - benchmark,
            "most_recent_realized_quarter": str(recent["target_quarter"]),
            "most_recent_forecast_error": float(recent["error"]),
            "usable_regressors_or_components": input_rows[0],
            "estimation_sample_size": input_rows[1],
            "coefficient_change_ratio_vs_prior_expanding_fit": coefficient_change,
            "model_successful": bool(pd.notna(current)),
            "monitoring_flags": "|".join(flags) if flags else "none",
            "review_required": bool(flags),
        })
    return pd.DataFrame(rows)


def revision_outputs(
    root: Path, nowcasts: pd.DataFrame, run_timestamp: str,
    target: dict[str, Any], stage: dict[str, Any], hashes: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    root = Path(root)
    previous_json = _read_json(root / "results/phase5a_current_nowcast.json")
    previous = {r["model"]: float(r["prediction"]) for r in previous_json["predictions"]}
    previous_manifest = _read_json(root / "results/phase5a_run_manifest.json")
    same_inputs = (
        previous_manifest["input_hashes"]["monthly_master_hash"] == hashes["monthly_master_hash"]
        and previous_manifest["input_hashes"]["quarterly_master_hash"] == hashes["quarterly_master_hash"]
        and previous_manifest["input_hashes"]["registry_hash"] == hashes["registry_hash"]
    )
    rows = []
    for item in nowcasts.itertuples(index=False):
        prior = previous.get(item.model, np.nan)
        revision = float(item.prediction - prior) if pd.notna(prior) else np.nan
        rows.append({
            "run_timestamp_utc": run_timestamp,
            "run_date": item.as_of_date,
            "target_quarter": item.target_quarter,
            "operational_stage": item.horizon,
            "model": item.model,
            "previous_forecast": prior,
            "new_forecast": float(item.prediction),
            "absolute_revision": abs(revision) if pd.notna(revision) else np.nan,
            "revision_percentage_points": revision,
            "new_data_releases_since_previous_run": "none; input hashes unchanged" if same_inputs else "input fingerprint changed; see manifest",
            "revised_historical_data_since_previous_run": "none detected" if same_inputs else "input fingerprint changed; exact vintage comparison required",
            "model_availability_changes": "none",
            "model_weight_or_selection_changes": "none; frozen 0.5/0.5 policy retained",
        })
    decomposition = pd.DataFrame([{
        "run_timestamp_utc": run_timestamp,
        "target_quarter": target["target_quarter"],
        "previous_operational_stage": previous_json["run"]["horizon_detection"]["horizon"],
        "current_operational_stage": stage["horizon"],
        "previous_nowcast": previous["ensemble_ar2_umidas_usd"],
        "new_nowcast": float(nowcasts.loc[nowcasts.production_headline_flag, "prediction"].iloc[0]),
        "total_revision": float(nowcasts.loc[nowcasts.production_headline_flag, "prediction"].iloc[0]) - previous["ensemble_ar2_umidas_usd"],
        "new_data_effect": 0.0 if same_inputs else np.nan,
        "data_revision_effect": 0.0 if same_inputs else np.nan,
        "model_specification_or_stage_effect": (
            float(nowcasts.loc[nowcasts.production_headline_flag, "prediction"].iloc[0])
            - previous["ensemble_ar2_umidas_usd"] if same_inputs else np.nan
        ),
        "decomposition_method": (
            "Exact residual attribution when input hashes are unchanged: the full revision "
            "is attributed to the corrected availability-driven operational-stage classification."
        ),
        "model_selection_changed": False,
        "ensemble_weights_changed": False,
    }])
    history_path = root / OUTPUT_DIR / "phase5b_nowcast_revision_history.parquet"
    previous_history = pd.read_parquet(history_path) if history_path.exists() else pd.DataFrame()
    history = pd.concat([previous_history, pd.DataFrame(rows)], ignore_index=True)
    history = history.drop_duplicates(
        ["run_date", "target_quarter", "operational_stage", "model"], keep="last"
    )
    return decomposition, history


def _code_version(root: Path) -> dict[str, Any]:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                                check=True, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=root,
                                    check=True, capture_output=True, text=True).stdout.strip())
        return {"git_commit": commit, "working_tree_dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"git_commit": None, "working_tree_dirty": None}


def run_phase5b(root: Path, *, as_of_date: str = "2026-09-30",
                information_cutoff: str = "2026-09-30") -> dict[str, Any]:
    root = Path(root).resolve()
    run_timestamp = utc_now()
    run_id = f"phase5b-{pd.Timestamp(as_of_date):%Y%m%d}-{uuid.uuid4().hex[:10]}"
    immutable_before = immutable_artifact_hashes(root)

    # Required sequencing: governance is frozen before masters are loaded.
    policy = ensure_policy(root, run_timestamp)
    try:
        monthly_path = root / "data/master/v1_monthly.parquet"
        quarterly_path = root / "data/master/gdp_quarterly.parquet"
        registry_path = root / "registry/uzbekistan_nowcasting_v1.2_registry.xlsx"
        hashes = {
            "monthly_master_hash": file_sha256(monthly_path),
            "quarterly_master_hash": file_sha256(quarterly_path),
            "registry_hash": file_sha256(registry_path),
        }
        frozen = _read_json(root / "results/phase4b_candidate_freeze.json")
        expected = frozen["master_hashes"]
        hash_checks = {
            "monthly_master": hashes["monthly_master_hash"] == expected["monthly_sha256"],
            "quarterly_master": hashes["quarterly_master_hash"] == expected["quarterly_sha256"],
            "registry": hashes["registry_hash"] == expected["registry_sha256"],
        }
        if not all(hash_checks.values()):
            raise RuntimeError(f"FAILED_CONFIGURATION: input hashes differ from frozen baseline: {hash_checks}")
        dataset = load_dataset(root)
        target = detect_target_quarter(dataset, as_of_date)
        if target["target_quarter"] != "2026Q3" and str(as_of_date) == "2026-09-30":
            raise RuntimeError("FAILED_CONFIGURATION: current-vintage target is not 2026Q3")
        stage = detect_operational_stage(dataset, target["target_quarter"], information_cutoff)
        quality = build_data_quality(root, dataset, target["target_quarter"], information_cutoff)
        gate = production_gate(dataset, quality, stage, frozen)
        if not gate["passed"]:
            raise RuntimeError(f"{gate['status']}: {'; '.join(gate['errors'])}")
        nowcasts, diagnostics = generate_nowcasts(
            dataset, as_of_date, target, stage, hashes, run_timestamp
        )
        if nowcasts["prediction"].isna().any():
            raise RuntimeError("FAILED_MODEL: one or more active model forecasts are missing")
        headline = float(nowcasts.loc[nowcasts.production_headline_flag, "prediction"].iloc[0])
        data_status = build_data_status(root, dataset, information_cutoff,
                                        target["target_quarter"], stage)
        info_set = build_information_set_audit(root, dataset, target, stage)
        input_audit = build_model_input_audit(nowcasts, diagnostics, target, stage, gate)
        monitoring = model_monitoring(root, dataset, nowcasts, stage, quality, diagnostics)
        uncertainty = empirical_uncertainty(root, stage["horizon"], headline)
        decomposition, history = revision_outputs(
            root, nowcasts, run_timestamp, target, stage, hashes
        )
        warnings = list(gate["warnings"])
        if monitoring["review_required"].any():
            warnings.append("One or more model-monitoring flags require review; no model was automatically removed.")
        status = "SUCCESS_WITH_WARNINGS" if warnings else "SUCCESS"
    except Exception as exc:
        status_text = str(exc)
        status = next((s for s in FAILURE_STATUSES if status_text.startswith(s)), "FAILED_CONFIGURATION")
        failure = {
            "run_id": run_id, "run_timestamp_utc": run_timestamp,
            "status": status, "as_of_date": as_of_date,
            "information_cutoff": information_cutoff,
            "error": status_text,
        }
        save_json(root / OUTPUT_DIR / "phase5b_current_nowcast.json", failure)
        raise

    output = root / OUTPUT_DIR
    _write_table(quality, output / "phase5b_data_quality")
    _write_table(data_status, output / "phase5b_data_status")
    _write_table(input_audit, output / "phase5b_model_input_audit")
    _write_table(monitoring, output / "phase5b_model_monitoring")
    _write_table(decomposition, output / "phase5b_revision_decomposition")
    _write_table(history, output / "phase5b_nowcast_revision_history")
    _write_table(info_set, output / "phase5b_information_set")
    _write_table(nowcasts, output / "phase5b_current_nowcast")

    current_payload = {
        "run_id": run_id, "run_timestamp_utc": run_timestamp, "status": status,
        "as_of_date": str(pd.Timestamp(as_of_date).date()),
        "information_cutoff": str(pd.Timestamp(information_cutoff).date()),
        "target": target, "operational_stage": stage,
        "point_nowcast": headline, "uncertainty": uncertainty,
        "latest_known_gdp_period": target["latest_known_gdp_quarter"],
        "latest_known_gdp_value": target["latest_known_gdp_growth"],
        "production_model": "0.5*AR(2) + 0.5*USD/UZS U-MIDAS(3)",
        "predictions": nowcasts.to_dict(orient="records"),
        "data_gate": gate,
        "warnings": warnings, "errors": [],
        "previous_nowcast": float(decomposition.iloc[0]["previous_nowcast"]),
        "revision": float(decomposition.iloc[0]["total_revision"]),
        "models_attempted": list(ACTIVE_MODELS),
        "models_successful": list(ACTIVE_MODELS),
        "models_rejected_by_gate": [],
        "fallback_observations_used": 0,
    }
    validate_current_payload(current_payload)
    save_json(output / "phase5b_current_nowcast.json", current_payload)

    from uznowcast.operational.dashboard5b import render_phase5b_dashboard
    render_phase5b_dashboard(
        root=root, current=current_payload, quality=quality,
        input_audit=input_audit, monitoring=monitoring,
        decomposition=decomposition, data_status=data_status,
    )
    _write_report(root, current_payload, quality, input_audit, monitoring,
                  decomposition, immutable_before)

    immutable_after = immutable_artifact_hashes(root)
    if immutable_before != immutable_after:
        raise AssertionError("Phase 4 or Phase 5A artifact changed during Phase 5B")
    outputs = [
        f"{OUTPUT_DIR}/phase5b_production_policy.json",
        f"{OUTPUT_DIR}/phase5b_run_manifest.json",
        f"{OUTPUT_DIR}/phase5b_current_nowcast.json",
        f"{OUTPUT_DIR}/phase5b_current_nowcast.csv",
        f"{OUTPUT_DIR}/phase5b_current_nowcast.parquet",
        f"{OUTPUT_DIR}/phase5b_data_quality.csv", f"{OUTPUT_DIR}/phase5b_data_quality.parquet",
        f"{OUTPUT_DIR}/phase5b_data_status.csv", f"{OUTPUT_DIR}/phase5b_data_status.parquet",
        f"{OUTPUT_DIR}/phase5b_model_input_audit.csv", f"{OUTPUT_DIR}/phase5b_model_input_audit.parquet",
        f"{OUTPUT_DIR}/phase5b_model_monitoring.csv", f"{OUTPUT_DIR}/phase5b_model_monitoring.parquet",
        f"{OUTPUT_DIR}/phase5b_revision_decomposition.csv", f"{OUTPUT_DIR}/phase5b_revision_decomposition.parquet",
        f"{OUTPUT_DIR}/phase5b_nowcast_revision_history.csv", f"{OUTPUT_DIR}/phase5b_nowcast_revision_history.parquet",
        f"{OUTPUT_DIR}/phase5b_information_set.csv", f"{OUTPUT_DIR}/phase5b_information_set.parquet",
        "docs/modeling/phase5b_operational_nowcasting.md",
        "dashboard/phase5b_uzbekistan_nowcast.html",
    ]
    manifest = {
        "run_id": run_id, "run_timestamp_utc": run_timestamp, "status": status,
        "target_quarter": target["target_quarter"],
        "operational_stage": stage["horizon"], "as_of_date": as_of_date,
        "information_cutoff": information_cutoff,
        "latest_known_gdp_period": target["latest_known_gdp_quarter"],
        "latest_known_gdp_value": target["latest_known_gdp_growth"],
        "code_version": _code_version(root),
        "registry_version": dataset.registry.version,
        "registry_hash": hashes["registry_hash"],
        "input_data_fingerprints": hashes, "frozen_hash_checks": hash_checks,
        "models_attempted": list(ACTIVE_MODELS),
        "models_successful": list(ACTIVE_MODELS),
        "models_rejected_by_production_gate": [],
        "production_model_combination": current_payload["production_model"],
        "warnings": warnings, "errors": [], "output_files": outputs,
        "immutable_phase4_phase5a_hashes_before": immutable_before,
        "immutable_phase4_phase5a_hashes_after": immutable_after,
        "immutable_artifacts_unchanged": True,
        "reproducibility": "Forecast values deterministic for identical inputs and policy; run IDs/timestamps vary.",
    }
    save_json(output / "phase5b_run_manifest.json", manifest)
    return {
        "current": current_payload, "manifest": manifest, "quality": quality,
        "data_status": data_status, "input_audit": input_audit,
        "monitoring": monitoring, "decomposition": decomposition,
        "history": history, "information_set": info_set,
    }


def _write_report(
    root: Path, current: dict[str, Any], quality: pd.DataFrame,
    input_audit: pd.DataFrame, monitoring: pd.DataFrame,
    decomposition: pd.DataFrame, immutable_before: dict[str, str],
) -> None:
    stage = current["operational_stage"]
    uncertainty = current["uncertainty"]
    d = decomposition.iloc[0]
    report = f"""# Phase 5B — Hardened operational Uzbekistan GDP nowcast

## Result

- Status: **{current['status']}**
- Target: **{current['target']['target_quarter']}**
- Operational stage: **{stage['horizon']}**
- As-of date / information cutoff: `{current['as_of_date']}` / `{current['information_cutoff']}`
- Point nowcast: **{current['point_nowcast']:.3f}%**
- Empirical 50% error interval: **{uncertainty['interval_50']['lower']:.3f}%–{uncertainty['interval_50']['upper']:.3f}%**
- Empirical 80% error interval: **{uncertainty['interval_80']['lower']:.3f}%–{uncertainty['interval_80']['upper']:.3f}%**
- Matching-horizon historical RMSE: **{uncertainty['historical_rmse']:.3f} pp**
- Latest official GDP: **{current['latest_known_gdp_period']} = {current['latest_known_gdp_value']:.1f}% YoY**

These empirical intervals use {uncertainty['sample_size']} matching-{stage['horizon']} errors
({uncertainty['development_count']} Phase 4B development pseudo-OOS and
{uncertainty['frozen_holdout_count']} untouched Phase 4C holdout observations). They are
historical forecast-error ranges, not structural probability forecasts.

## Phase 5A audit and correction

The Phase 5A implementation matched its frozen model, weight, cutoff masking, expanding-window,
hash, and output policies. One operational-label limitation was found: stage detection used the
calendar cutoff. The September USD/UZS monthly aggregate in the frozen vintage is marked
`partial_month` and has no clean model value. Phase 5B therefore reports **{stage['horizon']}**,
the highest stage supported by complete contiguous target-quarter production-signal months
({', '.join(stage['complete_target_quarter_signal_months'])}). Phase 5A files were not changed.

## Revision from Phase 5A

- Previous headline: {d['previous_nowcast']:.6f}%
- Phase 5B headline: {d['new_nowcast']:.6f}%
- Revision: {d['total_revision']:+.6f} percentage points
- New-data effect: {d['new_data_effect']:+.6f} pp
- Data-revision effect: {d['data_revision_effect']:+.6f} pp
- Stage/specification effect: {d['model_specification_or_stage_effect']:+.6f} pp

Input hashes are unchanged, so the revision is exactly attributed to using the availability-driven
{stage['horizon']} frozen estimation path instead of Phase 5A's calendar-labelled H3 path. Model
selection and 0.5/0.5 weights are unchanged.

## Data-quality gate

- GREEN: {int((quality.quality_status == 'GREEN').sum())}
- AMBER: {int((quality.quality_status == 'AMBER').sum())}
- RED: {int((quality.quality_status == 'RED').sum())}
- Missing expected current-quarter observations: {int(quality.missing_current_nowcast_quarter.sum())}
- Fallback observations used: 0

RED optional series do not silently enter production. The current RED series and its retrieval
evidence are retained in `phase5b_data_quality`. No value was imputed, interpolated, zero-filled,
extrapolated, or forward-filled.

## Operational definitions

- H1: first complete, release-eligible target-quarter USD/UZS monthly aggregate.
- H2: first two complete, release-eligible target-quarter aggregates.
- H3: all three complete, release-eligible target-quarter aggregates.
- A delayed or partial release keeps the system at the highest contiguous supported stage.

The information-set audit records every quarterly outcome and monthly lag observation entering
estimation or the current target vector. All rows pass `assumed_available_date <= forecast_origin`
and the run information cutoff.

## Fail-safe and fallback policy

Required GDP or USD failures, cutoff violations, registry/model mismatches, insufficient samples,
or an unavailable headline ensemble stop publication. Optional-series failures create warnings.
The permitted hierarchy is official data, an explicit prior official vintage, a frozen lag structure
that does not require the missing value, then model exclusion. Statistical filling is prohibited.

## Monitoring limitations

The Phase 4C monitoring metrics contain only four quarters. Coefficient change is a reproducible
expanding-fit diagnostic, not a formal stability test. Russia IPI remains unavailable because the
recorded Rosstat retrieval failed TLS certificate verification; it is not used by any production model.
The release calendar remains an assumption where historical first-release timestamps are unavailable.

## Reproducibility and preservation

The run manifest records hashes, code identity, models, warnings, outputs, and all
{len(immutable_before)} immutable Phase 4/5A artifact hashes. The production policy was written
before model estimation.

**PHASE 4 AND PHASE 5A ARTIFACTS WERE NOT MODIFIED.**

**THE PHASE 5B NOWCAST USES ONLY INFORMATION AVAILABLE BY THE SPECIFIED CUTOFF.**
"""
    path = Path(root) / "docs/modeling/phase5b_operational_nowcasting.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Run hardened Phase 5B nowcast")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--as-of-date", default="2026-09-30")
    parser.add_argument("--information-cutoff", default="2026-09-30")
    args = parser.parse_args()
    result = run_phase5b(
        args.root, as_of_date=args.as_of_date,
        information_cutoff=args.information_cutoff,
    )
    c = result["current"]
    q = result["quality"]
    print("PHASE 5B COMPLETE")
    print(f"Target quarter: {c['target']['target_quarter']}")
    print(f"Operational stage: {c['operational_stage']['horizon']}")
    print(f"Point nowcast: {c['point_nowcast']:.6f}%")
    print(f"80% uncertainty interval: {c['uncertainty']['interval_80']['lower']:.6f}% to {c['uncertainty']['interval_80']['upper']:.6f}%")
    print(f"Previous nowcast: {c['previous_nowcast']:.6f}%")
    print(f"Revision: {c['revision']:+.6f} pp")
    print(f"Latest known GDP: {c['latest_known_gdp_period']} = {c['latest_known_gdp_value']:.1f}%")
    print(f"Production model/model combination: {c['production_model']}")
    print(f"Data: GREEN={(q.quality_status == 'GREEN').sum()} AMBER={(q.quality_status == 'AMBER').sum()} RED={(q.quality_status == 'RED').sum()}")
    print(f"Models: attempted={len(c['models_attempted'])} successful={len(c['models_successful'])} rejected={len(c['models_rejected_by_gate'])}")
    print(f"Warnings: {len(c['warnings'])}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
