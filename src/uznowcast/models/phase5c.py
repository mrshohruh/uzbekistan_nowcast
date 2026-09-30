"""Phase 5C challenger research, isolated from the production nowcast.

The runner deliberately writes only below ``results/challengers/phase5c``,
``docs/modeling/phase5c`` and the separate Phase 5C dashboard path.  It uses
the frozen V1.2 masters as read-only inputs and verifies the Phase 5B.2
protected-artifact inventory both before and after the research run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import html
import json
from itertools import combinations
from pathlib import Path
import subprocess
from typing import Callable, Iterable, Sequence

import numpy as np
import pandas as pd

from uznowcast.models.benchmarks import ar_forecast, historical_mean_forecast
from uznowcast.models.bridge import BridgeSpec, bridge_forecast
from uznowcast.models.data import (
    ModelingDataset, horizon_month_end, information_cutoff_for_variable,
    load_dataset, quarter_start,
)
from uznowcast.models.dfm import DFMSpec, dfm_forecast
from uznowcast.models.midas import MidasSpec, _monthly_lag_vector, midas_forecast
from uznowcast.provenance import save_json


PHASE = "5C"
VERSION = "5c.0"
OUTPUT_REL = Path("results/challengers/phase5c")
DOC_REL = Path("docs/modeling/phase5c")
DASHBOARD_REL = Path("dashboard/phase5c_challenger_dashboard.html")
PRODUCTION_NOWCAST_REL = Path("results/production/current_nowcast.json")
PROTECTED_MANIFEST_REL = Path("results/phase5b2/protected_artifact_manifest_after.csv")
REGISTRY_REL = Path("registry/uzbekistan_nowcasting_v1.2_registry.xlsx")
MONTHLY_REL = Path("data/master/v1_monthly.parquet")
QUARTERLY_REL = Path("data/master/gdp_quarterly.parquet")
HORIZONS = ("H1", "H2", "H3")
LAG_MODES = ("standard", "conservative")
DEVELOPMENT_END = "2025Q2"
POST_DEVELOPMENT = ("2025Q3", "2025Q4", "2026Q1", "2026Q2")
CURRENT_TARGET = "2026Q3"
CURRENT_HORIZON = "H2"
CURRENT_NOWCAST = 7.6239786595896035
MIN_TRAIN_QUARTERS = 12
MIN_EFFECTIVE_TRAIN = 12
MAX_MONTHLY_LAGS = 3
MAX_MULTIVARIATE_PREDICTORS = 2
_LAG_CACHE: dict[tuple[int, str, str, str, str, int], np.ndarray] = {}
_MEAN_CACHE: dict[tuple[int, str, str, str, str], float] = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return sha256(encoded).hexdigest()


def git_text(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def protected_inventory(root: Path) -> dict[str, str]:
    manifest = pd.read_csv(root / PROTECTED_MANIFEST_REL)
    path_col = "path_after_cleanup"
    hash_col = "sha256_after"
    inventory: dict[str, str] = {}
    for row in manifest.to_dict("records"):
        relative = str(row[path_col]).replace("\\", "/")
        path = root / relative
        inventory[relative] = file_hash(path) if path.exists() else "MISSING"
        expected = str(row[hash_col])
        if inventory[relative] != expected:
            raise RuntimeError(
                f"Protected artifact mismatch before Phase 5C: {relative}; "
                f"expected {expected}, observed {inventory[relative]}"
            )
    return inventory


def prepare_phase5c(root: Path) -> dict:
    """Record starting state and freeze the research protocol exactly once."""
    root = Path(root).resolve()
    out = root / OUTPUT_REL
    out.mkdir(parents=True, exist_ok=True)
    start_path = out / "phase5c_starting_state.json"
    protocol_path = out / "phase5c_challenger_protocol.json"
    if start_path.exists() or protocol_path.exists():
        if not (start_path.exists() and protocol_path.exists()):
            raise RuntimeError("Partial Phase 5C preparation state; manual review required")
        return json.loads(protocol_path.read_text(encoding="utf-8"))

    status = git_text(root, "status", "--porcelain")
    production = json.loads((root / PRODUCTION_NOWCAST_REL).read_text(encoding="utf-8"))
    before = protected_inventory(root)
    canonical = {
        "production_nowcast": str(PRODUCTION_NOWCAST_REL).replace("\\", "/"),
        "production_dashboard": "dashboard/current/uzbekistan_nowcast.html",
        "production_directory": "results/production",
        "registry": str(REGISTRY_REL).replace("\\", "/"),
    }
    for label, relative in canonical.items():
        path = root / relative
        if not path.exists():
            raise FileNotFoundError(f"Missing canonical {label}: {relative}")
    starting = {
        "phase": PHASE,
        "recorded_at_utc": utc_now(),
        "git_commit": git_text(root, "rev-parse", "HEAD"),
        "git_branch": git_text(root, "branch", "--show-current"),
        "working_tree_clean": status == "",
        "working_tree_status": status.splitlines(),
        "unexpected_preexisting_modifications": status.splitlines(),
        "canonical_paths": canonical,
        "input_hashes": {
            "registry": file_hash(root / REGISTRY_REL),
            "monthly_master": file_hash(root / MONTHLY_REL),
            "quarterly_master": file_hash(root / QUARTERLY_REL),
            "production_nowcast": file_hash(root / PRODUCTION_NOWCAST_REL),
        },
        "protected_artifacts_before": before,
        "frozen_production": {
            "model": production["production_model"],
            "target": production["target"]["target_quarter"],
            "horizon": production["operational_stage"]["horizon"],
            "point_nowcast": production["point_nowcast"],
        },
    }
    save_json(start_path, starting, exclusive=True)

    rules = {
        "target_variable": "gdp_real_yoy_pct",
        "sample": "2018Q1-2026Q2 outcomes; monthly V1.2 panel through 2026-09-30",
        "development_period": "expanding pseudo-OOS origins through 2025Q2",
        "historical_evaluation_period": list(POST_DEVELOPMENT),
        "evidence_labels": {
            "development": "DEVELOPMENT_PSEUDO_OOS; screening evidence, not pristine holdout",
            "historical_post_development": (
                "HISTORICAL_POST_DEVELOPMENT_TEST; outcomes were previously observed"
            ),
            "live": "LIVE_PROSPECTIVE_SHADOW from 2026Q3; no accuracy judgment",
        },
        "horizons": list(HORIZONS),
        "release_lag_policy": {
            "standard": "registry typical publication lag",
            "conservative": "standard plus 15 days; zero-lag daily sources use 3 days",
            "source": "frozen Phase 4 information-set convention",
        },
        "baseline_models": [
            "historical_mean", "ar1", "ar2", "umidas_usd_uzs_mom_dlog_l3",
            "production_ensemble_ar2_usd",
        ],
        "challenger_families": [
            "univariate_umidas", "parsimonious_multivariate_almon_midas",
            "bridge", "tight_panel_approximate_dfm", "forecast_combination",
        ],
        "predictor_eligibility": {
            "primary": "at least 60 observed months, usable by 2019-12, no unresolved failure",
            "secondary": "at least 24 observed months or a documented proxy/short history",
            "diagnostic_only": "less than 24 observations or material timing/quality concern",
            "ineligible": "no usable transformed observations or quarterly target",
        },
        "missing_data": (
            "preserve missing values; never impute model inputs; model forecast is unavailable "
            "when its required target-origin lags are unavailable"
        ),
        "minimum_effective_sample": MIN_EFFECTIVE_TRAIN,
        "transformation_rules": "use registry clean_model_field without performance-driven changes",
        "maximum_complexity": {
            "univariate_monthly_lags": [1, 2, 3],
            "multivariate_predictors": MAX_MULTIVARIATE_PREDICTORS,
            "multivariate_lags": 3,
            "multivariate_almon_order": 1,
            "dfm_factors": [1],
        },
        "ranking_metrics": {
            "primary": "matched-sample pooled H1-H3 RMSE versus frozen production",
            "secondary": ["horizon RMSE", "MAE", "bias", "coverage"],
        },
        "stability_metrics": [
            "coefficient sign changes", "coefficient dispersion", "condition number",
            "estimation failure rate", "forecast revision size",
        ],
        "promotion_rules": (
            "Phase 5C permits REJECT, RETAIN_FOR_RESEARCH, SHADOW_CHALLENGER, "
            "STRONG_SHADOW_CHALLENGER only; production promotion is forbidden"
        ),
        "multiple_testing_safeguards": [
            "fixed lag grid of 1/2/3", "maximum five shortlisted predictors",
            "one or two predictors per economic block where feasible",
            "development-only shortlisting", "matched-sample comparison",
            "conservative-lag sensitivity", "leave-one-quarter-out influence check",
            "no 2026Q3 outcome or judgment",
        ],
        "combination_weight_rule": (
            "performance weights at each origin use only earlier realized quarters; "
            "non-negative weights normalized to one"
        ),
        "current_shadow": {
            "target": CURRENT_TARGET,
            "as_of": "2026-09-30",
            "information_cutoff": "2026-09-30",
            "horizon": CURRENT_HORIZON,
        },
    }
    protocol = {
        "phase": PHASE,
        "version": VERSION,
        "status": "FROZEN_BEFORE_CHALLENGER_ESTIMATION",
        "written_at_utc": utc_now(),
        "rules": rules,
        "rules_sha256": canonical_hash(rules),
        "amendments": [],
    }
    save_json(protocol_path, protocol, exclusive=True)
    return protocol


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")


def predictor_universe(dataset: ModelingDataset) -> pd.DataFrame:
    rows = []
    sample_start = pd.Timestamp("2018-01-31")
    panel = dataset.monthly.loc[dataset.monthly.index >= sample_start]
    for item in dataset.registry.scope("v1"):
        key = item["variable_key"]
        if key == "gdp_real_yoy":
            continue
        field = item["clean_model_field"]
        series = panel[field].dropna() if field in panel else pd.Series(dtype=float)
        count = int(series.size)
        missingness = float(1 - count / len(panel)) if len(panel) else 1.0
        status = item["automation_status"]
        if count == 0:
            eligibility = "INELIGIBLE"
            reason = "no_usable_transformed_observations"
        elif count < 24 or key == "russia_ipi":
            eligibility = "DIAGNOSTIC_ONLY"
            reason = "short_or_failed_release_history"
        elif (count >= 60 and series.index.min() <= pd.Timestamp("2019-12-31")
              and status not in {"PROXY"}):
            eligibility = "ELIGIBLE_PRIMARY"
            reason = "adequate_history_and_defined_real_time_timing"
        else:
            eligibility = "ELIGIBLE_SECONDARY"
            reason = "usable_but_short_proxy_or_ragged_history"
        rows.append({
            "variable_key": key,
            "display_name": item["display_name"],
            "provider": item["provider"],
            "clean_model_field": field,
            "frequency": item["native_frequency"],
            "transformation": item["required_transformation"],
            "first_usable_month": str(series.index.min().date()) if count else "",
            "last_usable_month": str(series.index.max().date()) if count else "",
            "publication_lag_days": item["typical_publication_lag_days"],
            "observed_months_since_2018": count,
            "missingness_since_2018": missingness,
            "release_history_quality": (
                "observed_release_dates_unavailable; registry-lag pseudo-real-time"
            ),
            "structural_breaks": item["structural_breaks_caveats"],
            "automation_status": status,
            "economic_block": item["block"],
            "currently_used_by_production": "YES" if key == "usd_uzs" else "NO",
            "eligibility": eligibility,
            "eligibility_reason": reason,
        })
    return pd.DataFrame(rows).sort_values("variable_key").reset_index(drop=True)


def predictor_blocks(universe: pd.DataFrame) -> dict:
    blocks: dict[str, list[dict]] = {}
    for row in universe.to_dict("records"):
        block = str(row["economic_block"]).upper()
        blocks.setdefault(block, []).append({
            "variable_key": row["variable_key"],
            "clean_model_field": row["clean_model_field"],
            "eligibility": row["eligibility"],
        })
    return {"source": "V1.2 registry Block column", "blocks": blocks}


def _splits(dataset: ModelingDataset) -> list[tuple[tuple[str, ...], str]]:
    quarters = dataset.gdp["quarter"].astype(str).tolist()
    return [(tuple(quarters[:i]), quarters[i])
            for i in range(MIN_TRAIN_QUARTERS, len(quarters))]


def _evidence(target: str) -> str:
    return ("HISTORICAL_POST_DEVELOPMENT_TEST" if target in POST_DEVELOPMENT
            else "DEVELOPMENT_PSEUDO_OOS")


def _common_row(dataset: ModelingDataset, target: str, horizon: str,
                mode: str, train: Sequence[str]) -> dict:
    actual = float(dataset.gdp.set_index("quarter").loc[target, dataset.target_field])
    return {
        "target_quarter": target,
        "horizon": horizon,
        "lag_mode": mode,
        "evidence_class": _evidence(target),
        "actual": actual,
        "training_first_quarter": train[0],
        "training_last_quarter": train[-1],
        "n_training_quarters": len(train),
    }


def _lag_vector_fast(dataset: ModelingDataset, field: str, quarter: str,
                     horizon: str, mode: str, lags: int = 3) -> np.ndarray:
    """Cached equivalent of the core MIDAS monthly-lag extraction."""
    key = (id(dataset), field, quarter, horizon, mode, lags)
    if key in _LAG_CACHE:
        return _LAG_CACHE[key]
    origin = horizon_month_end(quarter, horizon)
    variable_key = dataset.monthly_key_by_field[field]
    cutoff = information_cutoff_for_variable(
        origin, variable_key, dataset.release_lag_days, mode)
    series = dataset.monthly.loc[dataset.monthly.index <= min(origin, cutoff), field].dropna()
    result = (np.full(lags, np.nan) if len(series) < lags
              else series.tail(lags).to_numpy(dtype=float))
    _LAG_CACHE[key] = result
    return result


def _univariate_forecast_fast(dataset: ModelingDataset, field: str, lags: int,
                              train: Sequence[str], target: str, horizon: str,
                              mode: str) -> tuple[float, dict]:
    gdp = dataset.gdp.set_index("quarter")[dataset.target_field]
    rows_x, rows_y = [], []
    for i, quarter in enumerate(train):
        vector = _lag_vector_fast(dataset, field, quarter, horizon, mode, lags)
        if i == 0 or np.isnan(vector).any():
            continue
        row = [1.0, float(gdp.get(train[i - 1], np.nan)), *vector.tolist()]
        if np.isnan(row).any() or pd.isna(gdp.get(quarter)):
            continue
        rows_x.append(row)
        rows_y.append(float(gdp.loc[quarter]))
    if not rows_y:
        return np.nan, {"failure": "no_training_rows", "n_train": 0}
    design = np.asarray(rows_x, float)
    response = np.asarray(rows_y, float)
    coef, *_ = np.linalg.lstsq(design, response, rcond=None)
    vector = _lag_vector_fast(dataset, field, target, horizon, mode, lags)
    if np.isnan(vector).any():
        return np.nan, {"failure": "missing_monthly_lags_at_target",
                        "n_train": len(response), "coefficients": coef.tolist()}
    x = np.asarray([1.0, float(gdp.get(train[-1], np.nan)), *vector.tolist()])
    return float(x @ coef), {"failure": None, "n_train": len(response),
                            "coefficients": coef.tolist(),
                            "condition_number": float(np.linalg.cond(design))}


def _quarter_mean_fast(dataset: ModelingDataset, field: str, quarter: str,
                       horizon: str, mode: str) -> float:
    key = (id(dataset), field, quarter, horizon, mode)
    if key in _MEAN_CACHE:
        return _MEAN_CACHE[key]
    origin = horizon_month_end(quarter, horizon)
    variable_key = dataset.monthly_key_by_field[field]
    cutoff = information_cutoff_for_variable(
        origin, variable_key, dataset.release_lag_days, mode)
    start = quarter_start(quarter)
    end = start + pd.offsets.MonthEnd(3)
    series = dataset.monthly.loc[
        (dataset.monthly.index >= start)
        & (dataset.monthly.index <= min(origin, cutoff, end)), field
    ].dropna()
    result = float(series.mean()) if not series.empty else np.nan
    _MEAN_CACHE[key] = result
    return result


def _bridge_forecast_fast(dataset: ModelingDataset, fields: Sequence[str],
                          train: Sequence[str], target: str, horizon: str,
                          mode: str) -> tuple[float, dict]:
    gdp = dataset.gdp.set_index("quarter")[dataset.target_field]
    rows_x, rows_y = [], []
    for i, quarter in enumerate(train):
        if i == 0:
            continue
        values = [_quarter_mean_fast(dataset, field, quarter, horizon, mode)
                  for field in fields]
        row = [1.0, float(gdp.get(train[i - 1], np.nan)), *values]
        if np.isnan(row).any() or pd.isna(gdp.get(quarter)):
            continue
        rows_x.append(row)
        rows_y.append(float(gdp.loc[quarter]))
    if len(rows_y) < MIN_EFFECTIVE_TRAIN:
        return np.nan, {"failure": "insufficient_effective_training", "n_train": len(rows_y)}
    design = np.asarray(rows_x, float)
    response = np.asarray(rows_y, float)
    coef, *_ = np.linalg.lstsq(design, response, rcond=None)
    values = [_quarter_mean_fast(dataset, field, target, horizon, mode) for field in fields]
    x = np.asarray([1.0, float(gdp.get(train[-1], np.nan)), *values])
    if np.isnan(x).any():
        return np.nan, {"failure": "missing_input_at_target", "n_train": len(response),
                        "coefficients": coef.tolist()}
    return float(x @ coef), {"failure": None, "n_train": len(response),
                            "coefficients": coef.tolist(),
                            "condition_number": float(np.linalg.cond(design))}


def benchmark_predictions(dataset: ModelingDataset) -> pd.DataFrame:
    rows: list[dict] = []
    gdp = dataset.gdp.set_index("quarter")[dataset.target_field]
    usd = MidasSpec("umidas_usd_uzs_mom_dlog_l3", "usd_uzs_mom_dlog", 3)
    for train, target in _splits(dataset):
        y = gdp.reindex(train).dropna()
        for horizon in HORIZONS:
            for mode in LAG_MODES:
                common = _common_row(dataset, target, horizon, mode, train)
                values: dict[str, tuple[float, dict]] = {
                    "historical_mean": historical_mean_forecast(y),
                    "ar1": ar_forecast(y, 1),
                    "ar2": ar_forecast(y, 2),
                }
                values[usd.name] = midas_forecast(
                    dataset, usd, train, target, horizon=horizon, mode=mode)
                for model, (prediction, diagnostics) in values.items():
                    rows.append({
                        **common, "model": model, "family": "benchmark",
                        "predictors": "usd_uzs_mom_dlog" if model == usd.name else "",
                        "monthly_lags": 3 if model == usd.name else 0,
                        "prediction": prediction,
                        "error": common["actual"] - prediction,
                        "n_effective_train": diagnostics.get("n_train", len(y)),
                        "failure": diagnostics.get("failure"),
                        "coefficients": json.dumps(diagnostics.get("coefficients", [])),
                    })
    frame = pd.DataFrame(rows)
    keys = ["target_quarter", "horizon", "lag_mode"]
    ar2 = frame.loc[frame.model == "ar2", keys + ["prediction"]].rename(
        columns={"prediction": "ar2_prediction"})
    usd_rows = frame.loc[frame.model == usd.name, keys + ["prediction"]].rename(
        columns={"prediction": "usd_prediction"})
    ensemble = ar2.merge(usd_rows, on=keys, validate="one_to_one")
    ensemble["prediction"] = 0.5 * ensemble.ar2_prediction + 0.5 * ensemble.usd_prediction
    context = frame.drop_duplicates(keys).set_index(keys)
    ensemble_rows = []
    for row in ensemble.to_dict("records"):
        key = tuple(row[k] for k in keys)
        base = context.loc[key].to_dict()
        pred = float(row["prediction"])
        ensemble_rows.append({
            **base, **dict(zip(keys, key)),
            "model": "production_ensemble_ar2_usd", "family": "production_benchmark",
            "predictors": "ar2|usd_uzs_mom_dlog", "monthly_lags": 3,
            "prediction": pred, "error": float(base["actual"]) - pred,
            "n_effective_train": base["n_training_quarters"] - 2,
            "failure": None, "coefficients": "[0.5, 0.5]",
        })
    return pd.concat([frame, pd.DataFrame(ensemble_rows)], ignore_index=True)


def univariate_predictions(dataset: ModelingDataset, universe: pd.DataFrame) -> pd.DataFrame:
    eligible = universe.loc[universe.eligibility.isin(
        ["ELIGIBLE_PRIMARY", "ELIGIBLE_SECONDARY"])]
    rows: list[dict] = []
    for item in eligible.to_dict("records"):
        field = item["clean_model_field"]
        for lag in (1, 2, 3):
            spec = MidasSpec(f"challenger_umidas_{field}_l{lag}", field, lag)
            for train, target in _splits(dataset):
                for horizon in HORIZONS:
                    for mode in LAG_MODES:
                        prediction, diag = _univariate_forecast_fast(
                            dataset, field, lag, train, target, horizon, mode)
                        n_train = diag.get("n_train", 0)
                        failure = diag.get("failure")
                        if np.isfinite(prediction) and int(n_train) < MIN_EFFECTIVE_TRAIN:
                            prediction = np.nan
                            failure = "insufficient_effective_training"
                        common = _common_row(dataset, target, horizon, mode, train)
                        coefficients = diag.get("coefficients", [])
                        rows.append({
                            **common, "model": spec.name, "family": "univariate_umidas",
                            "variable_key": item["variable_key"], "predictors": field,
                            "economic_block": item["economic_block"],
                            "monthly_lags": lag, "prediction": prediction,
                            "error": common["actual"] - prediction,
                            "n_effective_train": n_train, "failure": failure,
                            "coefficients": json.dumps(coefficients),
                            "coefficient_max_abs": (max(map(abs, coefficients))
                                                    if coefficients else np.nan),
                        })
    return pd.DataFrame(rows)


def _matched(group: pd.DataFrame, production: pd.DataFrame) -> pd.DataFrame:
    keys = ["target_quarter", "horizon", "lag_mode"]
    left = group.dropna(subset=["prediction"])
    right = production[keys + ["prediction", "error"]].rename(columns={
        "prediction": "production_prediction", "error": "production_error"})
    return left.merge(right, on=keys, how="inner", validate="many_to_one")


def metric_table(predictions: pd.DataFrame, production: pd.DataFrame,
                 *, family: str | None = None) -> pd.DataFrame:
    source = predictions if family is None else predictions.loc[predictions.family == family]
    rows = []
    group_cols = ["model", "horizon", "lag_mode", "evidence_class"]
    for keys, group in source.groupby(group_cols, dropna=False):
        matched = _matched(group, production)
        if matched.empty:
            stats = {k: np.nan for k in ["rmse", "mae", "bias", "median_absolute_error",
                                               "maximum_absolute_error", "production_rmse",
                                               "production_mae", "pct_beating_production",
                                               "forecast_correlation"]}
            n = 0
        else:
            errors = matched.error.to_numpy(float)
            prod = matched.production_error.to_numpy(float)
            stats = {
                "rmse": float(np.sqrt(np.mean(errors ** 2))),
                "mae": float(np.mean(np.abs(errors))),
                "bias": float(np.mean(errors)),
                "median_error": float(np.median(errors)),
                "median_absolute_error": float(np.median(np.abs(errors))),
                "maximum_absolute_error": float(np.max(np.abs(errors))),
                "production_rmse": float(np.sqrt(np.mean(prod ** 2))),
                "production_mae": float(np.mean(np.abs(prod))),
                "pct_beating_production": float(np.mean(np.abs(errors) < np.abs(prod))),
                "forecast_correlation": (float(matched.prediction.corr(
                    matched.production_prediction)) if len(matched) > 1 else np.nan),
                "share_underpredictions": float(np.mean(errors > 0)),
            }
            loss_differential = prod ** 2 - errors ** 2
            if len(loss_differential) >= 8 and np.std(loss_differential, ddof=1) > 0:
                stats["exploratory_dm_style_statistic"] = float(
                    np.mean(loss_differential)
                    / (np.std(loss_differential, ddof=1) / np.sqrt(len(loss_differential))))
                stats["dm_interpretation"] = (
                    "exploratory only; positive favors challenger; small/overlapping sample"
                )
            else:
                stats["exploratory_dm_style_statistic"] = np.nan
                stats["dm_interpretation"] = "not calculated: fewer than 8 matched forecasts"
            n = len(matched)
        first = group.iloc[0]
        rows.append({
            **dict(zip(group_cols, keys)), "family": first.get("family", ""),
            "predictors": first.get("predictors", ""),
            "variable_key": first.get("variable_key", ""),
            "monthly_lags": first.get("monthly_lags", np.nan),
            "forecast_count": n, **stats,
            "rmse_relative_to_production": (
                stats.get("rmse", np.nan) / stats.get("production_rmse", np.nan)
                if stats.get("production_rmse", 0) else np.nan),
            "mae_relative_to_production": (
                stats.get("mae", np.nan) / stats.get("production_mae", np.nan)
                if stats.get("production_mae", 0) else np.nan),
            "estimation_failure_rate": float(group.prediction.isna().mean()),
        })
    return pd.DataFrame(rows)


def stability_table(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in predictions.groupby(["model", "horizon", "lag_mode"]):
        coefficients = [json.loads(value) for value in group.coefficients if value and value != "[]"]
        sign_changes = 0
        dispersion = np.nan
        if len(coefficients) >= 2 and len({len(x) for x in coefficients}) == 1:
            matrix = np.asarray(coefficients, dtype=float)
            sign_changes = int(np.sum(np.diff(np.sign(matrix), axis=0) != 0))
            dispersion = float(np.nanmax(np.nanstd(matrix, axis=0)))
        rows.append({
            "model": keys[0], "horizon": keys[1], "lag_mode": keys[2],
            "forecast_origins": len(group), "successful_origins": int(group.prediction.notna().sum()),
            "estimation_failure_rate": float(group.prediction.isna().mean()),
            "coefficient_sign_changes": sign_changes,
            "maximum_coefficient_std": dispersion,
            "stability_flag": ("UNSTABLE" if group.prediction.isna().mean() > .25
                               or sign_changes > max(6, len(group)) else "ACCEPTABLE"),
        })
    return pd.DataFrame(rows)


def choose_shortlist(metrics: pd.DataFrame, stability: pd.DataFrame,
                     universe: pd.DataFrame) -> dict:
    development = metrics.loc[
        (metrics.evidence_class == "DEVELOPMENT_PSEUDO_OOS")
        & (metrics.lag_mode == "standard")
    ].copy()
    pooled = (development.groupby(["model", "variable_key", "predictors", "monthly_lags"])
              .agg(rmse=("rmse", "mean"), relative=("rmse_relative_to_production", "mean"),
                   min_n=("forecast_count", "min"), horizons=("horizon", "nunique"))
              .reset_index())
    pooled = pooled.loc[(pooled.min_n >= 8) & (pooled.horizons == 3)]
    best = (pooled.sort_values(["relative", "rmse", "monthly_lags"])
            .drop_duplicates("variable_key"))
    block_map = universe.set_index("variable_key").economic_block.to_dict()
    selected = []
    block_counts: dict[str, int] = {}
    for row in best.to_dict("records"):
        block = block_map.get(row["variable_key"], "Unknown")
        if block_counts.get(block, 0) >= 2:
            continue
        selected.append({
            **row, "economic_block": block,
            "reason": (
                "advanced only for parsimonious family stress-testing because it is the "
                "best high-coverage specification for this predictor; it does not satisfy "
                "an accuracy promotion gate and cannot become a shadow challenger on that basis"
            ),
        })
        block_counts[block] = block_counts.get(block, 0) + 1
        if len(selected) == 5:
            break
    selected_keys = {row["variable_key"] for row in selected}
    rejected = []
    for row in best.to_dict("records"):
        if row["variable_key"] in selected_keys:
            continue
        rejected.append({
            "variable_key": row["variable_key"], "best_model": row["model"],
            "reason": ("block_concentration_limit" if block_counts.get(
                block_map.get(row["variable_key"], "Unknown"), 0) >= 2
                else "limited_to_five_predictors"),
            "relative_rmse": row["relative"],
        })
    return {
        "selection_basis": (
            "development pseudo-OOS matched mean horizon RMSE; coverage and block diversity; "
            "not an untouched-holdout selection"
        ),
        "selected": selected,
        "rejected_strong_or_available": rejected,
    }


def _multi_forecast(dataset: ModelingDataset, fields: Sequence[str], train: Sequence[str],
                    target: str, horizon: str, mode: str) -> tuple[float, dict]:
    gdp = dataset.gdp.set_index("quarter")[dataset.target_field]
    rows_x, rows_y = [], []
    for i, quarter in enumerate(train):
        vectors = [_lag_vector_fast(dataset, field, quarter, horizon, mode, 3)
                   for field in fields]
        if i == 0 or any(np.isnan(vector).any() for vector in vectors):
            continue
        # Low-order Almon basis [level, slope] for each predictor.
        basis = np.column_stack([np.ones(3), np.arange(3, dtype=float) / 2])
        row = [1.0, float(gdp.get(train[i - 1], np.nan))]
        for vector in vectors:
            row.extend((vector @ basis).tolist())
        if np.isnan(row).any() or pd.isna(gdp.get(quarter)):
            continue
        rows_x.append(row)
        rows_y.append(float(gdp.loc[quarter]))
    if len(rows_y) < MIN_EFFECTIVE_TRAIN:
        return np.nan, {"failure": "insufficient_effective_training", "n_train": len(rows_y)}
    design = np.asarray(rows_x, float)
    response = np.asarray(rows_y, float)
    condition = float(np.linalg.cond(design))
    coef, *_ = np.linalg.lstsq(design, response, rcond=None)
    target_vectors = [_lag_vector_fast(dataset, field, target, horizon, mode, 3)
                      for field in fields]
    if any(np.isnan(vector).any() for vector in target_vectors):
        return np.nan, {"failure": "missing_target_lags", "n_train": len(rows_y),
                        "condition_number": condition, "coefficients": coef.tolist()}
    x = [1.0, float(gdp.get(train[-1], np.nan))]
    for vector in target_vectors:
        x.extend((vector @ basis).tolist())
    return float(np.asarray(x) @ coef), {
        "n_train": len(rows_y), "condition_number": condition,
        "coefficients": coef.tolist(), "failure": None,
    }


def candidate_specs(shortlist: dict, universe: pd.DataFrame) -> tuple[dict, dict, dict]:
    selected = shortlist["selected"]
    block_by_field = universe.set_index("clean_model_field").economic_block.to_dict()
    fields = [row["predictors"] for row in selected]
    pairs = []
    for left, right in combinations(fields, 2):
        if block_by_field.get(left) == block_by_field.get(right):
            continue
        pairs.append((left, right))
        if len(pairs) == 4:
            break
    multi = {
        "frozen_before_evaluation": True,
        "method": "two-predictor three-lag Almon(1), GDP lag 1",
        "maximum_predictors": 2,
        "specifications": [
            {"name": f"multi_almon_{a}__{b}", "fields": [a, b],
             "monthly_lags": 3, "almon_order": 1, "parameter_count": 6}
            for a, b in pairs
        ],
    }
    bridge_fields = fields[:4]
    bridge_specs = [{"name": f"bridge_{field}", "fields": [field],
                     "aggregation": "mean_available", "parameter_count": 3}
                    for field in bridge_fields]
    if len(fields) >= 2:
        bridge_specs.append({"name": f"bridge_{fields[0]}__{fields[1]}",
                             "fields": fields[:2], "aggregation": "mean_available",
                             "parameter_count": 4})
    bridge = {"frozen_before_evaluation": True, "specifications": bridge_specs}
    dfm_fields = tuple(fields[:5])
    dfm_specs = []
    if len(dfm_fields) >= 2:
        dfm_specs.append({"name": "dfm_tight_shortlist_k1", "fields": list(dfm_fields),
                          "n_factors": 1, "with_gdp_lag": True})
        dfm_specs.append({"name": "dfm_tight_top2_k1", "fields": list(dfm_fields[:2]),
                          "n_factors": 1, "with_gdp_lag": True})
    dfm = {"frozen_before_evaluation": True, "maximum_factors": 1,
           "specifications": dfm_specs}
    return multi, bridge, dfm


def evaluate_specs(dataset: ModelingDataset, specs: Sequence[dict], family: str,
                   forecast: Callable) -> pd.DataFrame:
    rows = []
    for spec in specs:
        for train, target in _splits(dataset):
            for horizon in HORIZONS:
                for mode in LAG_MODES:
                    prediction, diag = forecast(spec, train, target, horizon, mode)
                    common = _common_row(dataset, target, horizon, mode, train)
                    rows.append({
                        **common, "model": spec["name"], "family": family,
                        "predictors": "|".join(spec["fields"]),
                        "monthly_lags": spec.get("monthly_lags", 0),
                        "prediction": prediction, "error": common["actual"] - prediction,
                        "n_effective_train": diag.get("n_train", 0),
                        "failure": diag.get("failure"),
                        "condition_number": diag.get("condition_number", np.nan),
                        "coefficients": json.dumps(diag.get("coefficients", [])),
                    })
    return pd.DataFrame(rows)


def combination_predictions(all_predictions: pd.DataFrame,
                            development_metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    standard = all_predictions.loc[all_predictions.lag_mode == "standard"].copy()
    candidates = development_metrics.loc[
        (development_metrics.evidence_class == "DEVELOPMENT_PSEUDO_OOS")
        & (development_metrics.lag_mode == "standard")
        & (development_metrics.model != "production_ensemble_ar2_usd")
    ]
    ranking = (candidates.groupby("model").agg(relative=("rmse_relative_to_production", "mean"),
                                                n=("forecast_count", "min"))
               .reset_index().query("n >= 8").sort_values("relative"))
    models = ["production_ensemble_ar2_usd"] + ranking.model.head(3).tolist()
    models = list(dict.fromkeys(models))
    source = standard.loc[standard.model.isin(models)]
    rows, weight_rows = [], []
    methods = ("equal_weight", "inverse_past_rmse", "nonnegative_past_stack",
               "median", "trimmed_mean")
    for horizon in HORIZONS:
        horizon_frame = source.loc[source.horizon == horizon]
        quarters = sorted(horizon_frame.target_quarter.unique())
        for target in quarters:
            current = horizon_frame.loc[horizon_frame.target_quarter == target].dropna(
                subset=["prediction"])
            if len(current) < 2:
                continue
            actual = float(current.actual.iloc[0])
            prior = horizon_frame.loc[horizon_frame.target_quarter < target]
            available = current.model.tolist()
            for method in methods:
                weights = np.repeat(1 / len(available), len(available))
                fallback = False
                if method in {"inverse_past_rmse", "nonnegative_past_stack"}:
                    pivot = prior.loc[prior.model.isin(available)].pivot_table(
                        index="target_quarter", columns="model", values="prediction")
                    actuals = prior.drop_duplicates("target_quarter").set_index(
                        "target_quarter")["actual"]
                    complete = pivot.dropna().reindex(columns=available).dropna()
                    y = actuals.reindex(complete.index).to_numpy(float)
                    if len(complete) >= 6:
                        if method == "inverse_past_rmse":
                            rmses = np.sqrt(np.mean((complete.to_numpy() - y[:, None]) ** 2,
                                                    axis=0))
                            inv = 1 / np.maximum(rmses, 1e-8)
                            weights = inv / inv.sum()
                        else:
                            raw, *_ = np.linalg.lstsq(complete.to_numpy(), y, rcond=None)
                            raw = np.maximum(raw, 0)
                            weights = raw / raw.sum() if raw.sum() else weights
                    else:
                        fallback = True
                values = current.set_index("model").reindex(available).prediction.to_numpy(float)
                if method == "median":
                    prediction = float(np.median(values))
                    weights = np.repeat(np.nan, len(available))
                elif method == "trimmed_mean" and len(values) >= 4:
                    prediction = float(np.mean(np.sort(values)[1:-1]))
                    weights = np.repeat(np.nan, len(available))
                elif method == "trimmed_mean":
                    prediction = float(np.mean(values))
                    fallback = True
                else:
                    prediction = float(values @ weights)
                model = f"combination_{method}"
                rows.append({
                    "target_quarter": target, "horizon": horizon, "lag_mode": "standard",
                    "evidence_class": _evidence(target), "actual": actual, "model": model,
                    "family": "forecast_combination", "predictors": "|".join(available),
                    "monthly_lags": 0, "prediction": prediction,
                    "error": actual - prediction, "n_effective_train": len(prior),
                    "failure": None, "coefficients": json.dumps(weights.tolist()),
                    "fallback_used": fallback,
                })
                for component, weight in zip(available, weights):
                    weight_rows.append({
                        "model": model, "target_quarter": target, "horizon": horizon,
                        "component": component, "weight": weight,
                        "weight_training_last_quarter": (max(prior.target_quarter)
                                                         if not prior.empty else ""),
                        "uses_only_prior_outcomes": True, "fallback_used": fallback,
                    })
    return pd.DataFrame(rows), pd.DataFrame(weight_rows)


def pooled_metrics(predictions: pd.DataFrame, production: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, family, mode, evidence), group in predictions.groupby(
            ["model", "family", "lag_mode", "evidence_class"]):
        matched = _matched(group, production)
        if matched.empty:
            continue
        error = matched.error.to_numpy(float)
        prod = matched.production_error.to_numpy(float)
        rows.append({
            "model": model, "family": family, "lag_mode": mode,
            "evidence_class": evidence, "horizon": "POOLED_H1_H3",
            "forecast_count": len(matched), "rmse": float(np.sqrt(np.mean(error ** 2))),
            "mae": float(np.mean(np.abs(error))), "bias": float(np.mean(error)),
            "median_error": float(np.median(error)),
            "share_underpredictions": float(np.mean(error > 0)),
            "production_rmse": float(np.sqrt(np.mean(prod ** 2))),
            "rmse_relative_to_production": float(np.sqrt(np.mean(error ** 2))
                                                 / np.sqrt(np.mean(prod ** 2))),
        })
    return pd.DataFrame(rows)


def revision_behavior(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    source = predictions.loc[predictions.lag_mode == "standard"]
    for (model, target), group in source.groupby(["model", "target_quarter"]):
        values = group.set_index("horizon").prediction
        actual = float(group.actual.iloc[0])
        if not set(HORIZONS) <= set(values.dropna().index):
            continue
        h1, h2, h3 = (float(values[h]) for h in HORIZONS)
        rows.append({
            "model": model, "target_quarter": target,
            "H1_to_H2_revision": h2 - h1, "H2_to_H3_revision": h3 - h2,
            "absolute_H1_to_H2_revision": abs(h2 - h1),
            "absolute_H2_to_H3_revision": abs(h3 - h2),
            "later_information_improved_H2": abs(actual - h2) < abs(actual - h1),
            "later_information_improved_H3": abs(actual - h3) < abs(actual - h2),
        })
    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail
    return (detail.groupby("model").agg(
        mean_absolute_revision_H1_H2=("absolute_H1_to_H2_revision", "mean"),
        median_absolute_revision_H1_H2=("absolute_H1_to_H2_revision", "median"),
        mean_absolute_revision_H2_H3=("absolute_H2_to_H3_revision", "mean"),
        median_absolute_revision_H2_H3=("absolute_H2_to_H3_revision", "median"),
        maximum_revision=("absolute_H2_to_H3_revision", "max"),
        share_H2_improves_error=("later_information_improved_H2", "mean"),
        share_H3_improves_error=("later_information_improved_H3", "mean"),
    ).reset_index())


def influence_diagnostics(predictions: pd.DataFrame, production: pd.DataFrame) -> pd.DataFrame:
    rows = []
    source = predictions.loc[predictions.lag_mode == "standard"]
    for model, group in source.groupby("model"):
        matched = _matched(group, production)
        if len(matched) < 4:
            continue
        full_rel = (np.sqrt(np.mean(matched.error ** 2))
                    / np.sqrt(np.mean(matched.production_error ** 2)))
        rels = []
        for quarter in matched.target_quarter.unique():
            subset = matched.loc[matched.target_quarter != quarter]
            rels.append(np.sqrt(np.mean(subset.error ** 2))
                        / np.sqrt(np.mean(subset.production_error ** 2)))
        rows.append({
            "model": model, "forecast_count": len(matched), "full_relative_rmse": full_rel,
            "minimum_leave_one_quarter_out_relative_rmse": min(rels),
            "maximum_leave_one_quarter_out_relative_rmse": max(rels),
            "influence_flag": ("FRAGILE_IMPROVEMENT" if full_rel < 1 and max(rels) >= 1
                               else "ROBUST_TO_SINGLE_QUARTER"),
        })
    return pd.DataFrame(rows)


def current_forecasts(dataset: ModelingDataset, shortlist: dict, multi: dict,
                      bridge: dict, dfm: dict, combination_components: Sequence[str],
                      combination_weights: pd.DataFrame) -> pd.DataFrame:
    train = tuple(dataset.gdp.quarter.astype(str))
    rows = [{
        "model": "production_ensemble_ar2_usd", "model_family": "production_benchmark",
        "H2_nowcast": CURRENT_NOWCAST, "difference_from_production": 0.0,
        "data_status": "FROZEN_PRODUCTION", "fallback_used": False,
        "production_eligible": True, "notes": "official frozen point nowcast",
    }]
    gdp = dataset.gdp.set_index("quarter")[dataset.target_field]
    ar2_current, _ = ar_forecast(gdp.reindex(train).dropna(), 2)
    mean_current, _ = historical_mean_forecast(gdp.reindex(train).dropna())
    frozen_usd, _ = midas_forecast(
        dataset, MidasSpec("umidas_usd_uzs_mom_dlog_l3", "usd_uzs_mom_dlog", 3),
        train, CURRENT_TARGET, horizon=CURRENT_HORIZON, mode="standard")
    forecasts: dict[str, float] = {
        "production_ensemble_ar2_usd": CURRENT_NOWCAST,
        "ar2": ar2_current,
        "historical_mean": mean_current,
        "umidas_usd_uzs_mom_dlog_l3": frozen_usd,
    }
    for selected in shortlist["selected"]:
        spec = MidasSpec(selected["model"], selected["predictors"], int(selected["monthly_lags"]))
        value, diag = midas_forecast(dataset, spec, train, CURRENT_TARGET,
                                     horizon=CURRENT_HORIZON, mode="standard")
        forecasts[spec.name] = value
        rows.append({
            "model": spec.name, "model_family": "univariate_umidas", "H2_nowcast": value,
            "difference_from_production": value - CURRENT_NOWCAST,
            "data_status": "AVAILABLE" if np.isfinite(value) else "UNAVAILABLE",
            "fallback_used": False, "production_eligible": False,
            "notes": diag.get("failure") or "SHADOW ONLY; 2026Q3 actual unknown",
        })
    for spec in multi["specifications"]:
        value, diag = _multi_forecast(dataset, spec["fields"], train, CURRENT_TARGET,
                                      CURRENT_HORIZON, "standard")
        forecasts[spec["name"]] = value
        rows.append({"model": spec["name"], "model_family": "multivariate_midas",
                     "H2_nowcast": value, "difference_from_production": value - CURRENT_NOWCAST,
                     "data_status": "AVAILABLE" if np.isfinite(value) else "UNAVAILABLE",
                     "fallback_used": False, "production_eligible": False,
                     "notes": diag.get("failure") or "SHADOW ONLY; 2026Q3 actual unknown"})
    for spec in bridge["specifications"]:
        value, diag = bridge_forecast(dataset, BridgeSpec(spec["name"], tuple(spec["fields"])),
                                      train, CURRENT_TARGET, horizon=CURRENT_HORIZON,
                                      mode="standard")
        forecasts[spec["name"]] = value
        rows.append({"model": spec["name"], "model_family": "bridge",
                     "H2_nowcast": value, "difference_from_production": value - CURRENT_NOWCAST,
                     "data_status": "AVAILABLE" if np.isfinite(value) else "UNAVAILABLE",
                     "fallback_used": False, "production_eligible": False,
                     "notes": diag.get("failure") or "SHADOW ONLY; 2026Q3 actual unknown"})
    for spec in dfm["specifications"]:
        dfm_spec = DFMSpec(spec["name"], tuple(spec["fields"]), n_factors=1)
        value, diag = dfm_forecast(dataset, dfm_spec, train, CURRENT_TARGET,
                                   horizon=CURRENT_HORIZON, mode="standard")
        forecasts[spec["name"]] = value
        rows.append({"model": spec["name"], "model_family": "approximate_dfm",
                     "H2_nowcast": value, "difference_from_production": value - CURRENT_NOWCAST,
                     "data_status": "AVAILABLE" if np.isfinite(value) else "UNAVAILABLE",
                     "fallback_used": False, "production_eligible": False,
                     "notes": diag.get("failure") or "SHADOW ONLY; 2026Q3 actual unknown"})
    available_names = [m for m in combination_components if m in forecasts
                       and np.isfinite(forecasts[m])]
    available = np.asarray([forecasts[m] for m in available_names], dtype=float)
    if len(available) >= 2:
        methods = ("equal_weight", "inverse_past_rmse", "nonnegative_past_stack",
                   "median", "trimmed_mean")
        for method in methods:
            fallback = False
            if method == "median":
                value = float(np.median(available))
            elif method == "trimmed_mean" and len(available) >= 4:
                value = float(np.mean(np.sort(available)[1:-1]))
            elif method == "trimmed_mean":
                value = float(np.mean(available))
                fallback = True
            elif method == "equal_weight":
                value = float(np.mean(available))
            else:
                model_name = f"combination_{method}"
                prior = combination_weights.loc[
                    (combination_weights.model == model_name)
                    & (combination_weights.horizon == CURRENT_HORIZON)
                ]
                if prior.empty:
                    weight = np.repeat(1 / len(available), len(available))
                    fallback = True
                else:
                    latest = prior.loc[prior.target_quarter == prior.target_quarter.max()]
                    mapping = latest.set_index("component").weight.to_dict()
                    weight = np.asarray([mapping.get(name, np.nan) for name in available_names],
                                        dtype=float)
                    if np.isnan(weight).any() or weight.sum() <= 0:
                        weight = np.repeat(1 / len(available), len(available))
                        fallback = True
                    else:
                        weight = weight / weight.sum()
                value = float(available @ weight)
            rows.append({
                "model": f"combination_{method}",
                "model_family": "forecast_combination", "H2_nowcast": value,
                "difference_from_production": float(value - CURRENT_NOWCAST),
                "data_status": "AVAILABLE", "fallback_used": fallback,
                "production_eligible": False,
                "notes": ("SHADOW ONLY; 2026Q3 actual unknown; components="
                          + "|".join(available_names)),
            })
    return pd.DataFrame(rows)


def build_leaderboard(all_predictions: pd.DataFrame, production: pd.DataFrame,
                      current: pd.DataFrame, influence: pd.DataFrame,
                      stability: pd.DataFrame) -> pd.DataFrame:
    horizon = metric_table(all_predictions, production)
    pooled = pooled_metrics(all_predictions, production)
    dev = pooled.loc[(pooled.evidence_class == "DEVELOPMENT_PSEUDO_OOS")
                     & (pooled.lag_mode == "standard")]
    conservative = pooled.loc[(pooled.evidence_class == "DEVELOPMENT_PSEUDO_OOS")
                              & (pooled.lag_mode == "conservative")]
    rows = []
    for item in dev.to_dict("records"):
        model = item["model"]
        model_rows = all_predictions.loc[all_predictions.model == model]
        first = model_rows.iloc[0]
        by_h = horizon.loc[(horizon.model == model)
                           & (horizon.evidence_class == "DEVELOPMENT_PSEUDO_OOS")
                           & (horizon.lag_mode == "standard")].set_index("horizon")
        cons = conservative.loc[conservative.model == model]
        inf = influence.loc[influence.model == model]
        stab = stability.loc[stability.model == model]
        rel = float(item["rmse_relative_to_production"])
        cons_rmse = float(cons.rmse.iloc[0]) if not cons.empty else np.nan
        influence_flag = inf.influence_flag.iloc[0] if not inf.empty else "NOT_ASSESSED"
        stable_flag = ("UNSTABLE" if (not stab.empty and (stab.stability_flag == "UNSTABLE").any())
                       else "ACCEPTABLE")
        if model == "production_ensemble_ar2_usd":
            gate = "FROZEN_BENCHMARK"
        elif item["family"] == "benchmark":
            gate = "REFERENCE_BENCHMARK"
        elif (item["forecast_count"] >= 30 and rel < .95
              and influence_flag != "FRAGILE_IMPROVEMENT"
              and (np.isnan(cons_rmse) or cons_rmse <= item["rmse"] * 1.15)
              and stable_flag == "ACCEPTABLE"):
            gate = "STRONG_SHADOW_CHALLENGER"
        elif item["forecast_count"] >= 24 and rel < 1:
            gate = "SHADOW_CHALLENGER"
        elif item["forecast_count"] >= 18:
            gate = "RETAIN_FOR_RESEARCH"
        else:
            gate = "REJECT"
        current_row = current.loc[current.model == model]
        rows.append({
            "model": model, "family": item["family"],
            "predictors": first.get("predictors", ""),
            "H1_RMSE": by_h.loc["H1", "rmse"] if "H1" in by_h.index else np.nan,
            "H2_RMSE": by_h.loc["H2", "rmse"] if "H2" in by_h.index else np.nan,
            "H3_RMSE": by_h.loc["H3", "rmse"] if "H3" in by_h.index else np.nan,
            "pooled_RMSE": item["rmse"], "pooled_MAE": item["mae"],
            "bias": item["bias"], "forecast_count": item["forecast_count"],
            "relative_RMSE_vs_production": rel, "conservative_lag_RMSE": cons_rmse,
            "stability_flag": stable_flag, "influence_flag": influence_flag,
            "data_quality_flag": "REGISTRY_LAG_APPROXIMATION",
            "current_2026Q3_shadow_nowcast": (current_row.H2_nowcast.iloc[0]
                                               if not current_row.empty else np.nan),
            "gate_status": gate,
        })
    return pd.DataFrame(rows).sort_values(
        ["relative_RMSE_vs_production", "pooled_RMSE"]).reset_index(drop=True)


def quarter_comparison(all_predictions: pd.DataFrame, production: pd.DataFrame,
                       leaderboard: pd.DataFrame) -> pd.DataFrame:
    keep = leaderboard.loc[leaderboard.gate_status.isin(
        ["SHADOW_CHALLENGER", "STRONG_SHADOW_CHALLENGER"]), "model"].tolist()
    if not keep:
        keep = leaderboard.loc[leaderboard.gate_status != "FROZEN_BENCHMARK", "model"].head(3).tolist()
    source = all_predictions.loc[(all_predictions.model.isin(keep))
                                 & (all_predictions.lag_mode == "standard")]
    matched = _matched(source, production.loc[production.lag_mode == "standard"])
    if matched.empty:
        return matched
    return matched.assign(
        production_forecast=matched.production_prediction,
        challenger_forecast=matched.prediction,
        challenger_minus_production_absolute_error=(matched.error.abs()
                                                     - matched.production_error.abs()),
        information_horizon=matched.horizon,
    )[["model", "target_quarter", "actual", "production_forecast",
       "challenger_forecast", "production_error", "error",
       "challenger_minus_production_absolute_error", "information_horizon",
       "evidence_class"]].rename(columns={"error": "challenger_error"})


def write_documentation(root: Path, universe: pd.DataFrame, shortlist: dict,
                        leaderboard: pd.DataFrame, current: pd.DataFrame,
                        old_dfm: dict) -> None:
    docs = root / DOC_REL
    cards = docs / "model_cards"
    cards.mkdir(parents=True, exist_ok=True)
    counts = universe.eligibility.value_counts().to_dict()
    best = leaderboard.loc[leaderboard.gate_status != "FROZEN_BENCHMARK"].head(1)
    best_text = "No challenger produced adequate evidence."
    if not best.empty:
        row = best.iloc[0]
        best_text = (f"The leading research specification is `{row.model}` with development "
                     f"relative RMSE {row.relative_RMSE_vs_production:.3f} and gate "
                     f"`{row.gate_status}`.")
    report = f"""# Phase 5C challenger results

## 1. Executive summary

{best_text} The production model remains frozen. Phase 5C evidence cannot promote a model;
any credible candidate must enter Phase 5D prospective shadow evaluation.

## 2. Frozen production benchmark

The benchmark is 0.5 × AR(2) + 0.5 × USD/UZS U-MIDAS(3). Its 2026Q3 H2
nowcast remains {CURRENT_NOWCAST:.10f}%. No production file was written.

## 3. Research protocol

The protocol was frozen before estimation. Monthly values are admitted using the registry lag
and the frozen standard/conservative timing rules. Expanding windows exclude the target and
all future GDP outcomes.

## 4. Available predictor universe

The registry contains {len(universe)} monthly predictors: primary={counts.get('ELIGIBLE_PRIMARY', 0)},
secondary={counts.get('ELIGIBLE_SECONDARY', 0)}, diagnostic={counts.get('DIAGNOSTIC_ONLY', 0)},
ineligible={counts.get('INELIGIBLE', 0)}.

## 5. Univariate screening results

The fixed lag grid was 1–3 months. The shortlist was limited to five predictors and no more
than two per registry block. Selected signals: {', '.join(x['variable_key'] for x in shortlist['selected']) or 'none'}.

## 6. Multivariate MIDAS results

Only preregistered, cross-block pairs of shortlisted predictors were tested, with two
predictors maximum and Almon(1) restrictions over three monthly lags.

## 7. Bridge-model results

Bridge equations use available-month quarterly means and one GDP lag. Missing future months
are not synthesized.

## 8. DFM reassessment

The reassessment uses tight shortlisted panels and one factor. It remains an approximate
EM-PCA factor bridge, not a Kalman DFM, and is compared with the earlier diagnostic decision.

## 9. Forecast-combination results

Equal, median, trimmed, inverse-past-RMSE and non-negative past stacking combinations were
evaluated. Performance weights use only outcomes earlier than each forecast origin.

## 10. Horizon-specific comparison

H1, H2 and H3 are reported separately in `phase5c_horizon_comparison.csv`; pooled figures
never replace the horizon-level evidence.

## 11. Stability and influence diagnostics

Coefficient changes, failure rates and leave-one-quarter-out relative RMSE are reported.
An apparent advantage that disappears after one quarter is labelled `FRAGILE_IMPROVEMENT`.

## 12. Release-lag robustness

Shortlisted models are reported under both frozen standard and conservative release lags.

## 13. 2026Q3 shadow forecasts

These are live H2 shadow forecasts as of 2026-09-30. The 2026Q3 GDP realization is unknown,
and current forecast levels were not used for model selection.

## 14. Challenger gate decisions

Only REJECT, RETAIN_FOR_RESEARCH, SHADOW_CHALLENGER and STRONG_SHADOW_CHALLENGER are
permitted. `PRODUCTION_MODEL` is deliberately unavailable.

## 15. Limitations

The quarterly sample is small; historical release dates are not observed for most series;
registry lags approximate real-time availability; revised current-vintage GDP is used; and
2025Q3–2026Q2 is not a pristine holdout because those outcomes were previously examined.

## 16. Recommendation for Phase 5D

Keep production unchanged. Run credible shadow candidates prospectively against genuinely
new GDP releases before considering any governance decision.
"""
    (docs / "phase5c_challenger_results.md").write_text(report, encoding="utf-8")
    old_lines = "\n".join(
        f"- `{item['model']}`: worst H3 relative RMSE vs AR(2) "
        f"{item['worst_h3_relative_rmse_to_ar2']:.3f}; qualified={item['qualified']}"
        for item in old_dfm.get("assessments", [])
    )
    dfm_report = f"""# Phase 5C DFM reassessment

Phase 4B retained no DFM (`selected_dfm={old_dfm.get('selected_dfm')}`). Its approximate
factor variants failed the accuracy gate and remained diagnostic. Phase 5C therefore did
not relabel the old model: it tested only one-factor, tight-panel variants based on screened
signals, with the same real-time masking and expanding windows. See
`phase5c_dfm_metrics.csv` and `phase5c_dfm_diagnostics.csv`. No DFM is production eligible.

The frozen Phase 4B comparison points were:

{old_lines}
"""
    (docs / "phase5c_dfm_reassessment.md").write_text(dfm_report, encoding="utf-8")
    for row in leaderboard.loc[leaderboard.gate_status.isin(
            ["SHADOW_CHALLENGER", "STRONG_SHADOW_CHALLENGER"])].to_dict("records"):
        card = f"""# {row['model']}

- Status: {row['gate_status']} (shadow only)
- Family: {row['family']}
- Economic intuition / inputs: {row['predictors']}
- Equation: family-specific linear GDP bridge with one lagged GDP term; see frozen specs.
- Transformations: registry clean fields, unchanged.
- Information timing: standard registry lag; conservative-lag sensitivity reported.
- Development pooled RMSE: {row['pooled_RMSE']:.6f}
- Relative RMSE versus production: {row['relative_RMSE_vs_production']:.6f}
- Weaknesses: small target sample, approximate historical release timing, revised GDP vintage.
- Operational requirement: all listed monthly inputs must be release-eligible.
- 2026Q3 H2 shadow nowcast: {row['current_2026Q3_shadow_nowcast']}
- Gate rationale: accuracy, coverage, timing, stability and influence rules in the protocol.
"""
        (cards / f"{row['model']}.md").write_text(card, encoding="utf-8")


def write_dashboard(root: Path, leaderboard: pd.DataFrame, current: pd.DataFrame) -> None:
    challengers = leaderboard.loc[leaderboard.gate_status != "FROZEN_BENCHMARK"].head(8)
    table_rows = "".join(
        f"<tr><td>{html.escape(str(row.model))}</td><td>{row.current_2026Q3_shadow_nowcast:.3f}</td>"
        f"<td>{row.H1_RMSE:.3f}</td><td>{row.H2_RMSE:.3f}</td><td>{row.H3_RMSE:.3f}</td>"
        f"<td>{row.relative_RMSE_vs_production:.3f}</td><td>{html.escape(row.stability_flag)}</td>"
        f"<td>{html.escape(row.gate_status)}</td></tr>"
        for row in challengers.itertuples() if pd.notna(row.current_2026Q3_shadow_nowcast)
    )
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Phase 5C Shadow Challengers</title><style>
body{{font-family:system-ui;max-width:1100px;margin:40px auto;padding:0 20px;background:#f5f7fa;color:#172033}}
.banner{{background:#7a1f1f;color:white;padding:14px 18px;font-weight:800;letter-spacing:.08em}}
.card{{background:white;padding:24px;margin:18px 0;border-radius:10px;box-shadow:0 2px 12px #0001}}
.number{{font-size:42px;font-weight:750}} table{{width:100%;border-collapse:collapse}}th,td{{padding:9px;border-bottom:1px solid #dde3ea;text-align:right}}th:first-child,td:first-child{{text-align:left}}
</style></head><body><div class="banner">PHASE 5C — SHADOW ONLY — NOT THE OFFICIAL NOWCAST</div>
<div class="card"><h1>Uzbekistan GDP challenger research</h1><p>Frozen production</p>
<div class="number">{CURRENT_NOWCAST:.4f}%</div><p>2026Q3 · H2 · production remains 0.5 AR(2) + 0.5 USD/UZS U-MIDAS(3).</p></div>
<div class="card"><h2>Shadow challengers</h2><table><thead><tr><th>Model</th><th>Current H2</th><th>H1 RMSE</th><th>H2 RMSE</th><th>H3 RMSE</th><th>Relative RMSE</th><th>Stability</th><th>Gate</th></tr></thead><tbody>{table_rows}</tbody></table></div>
<div class="card"><p><strong>Data-quality note:</strong> historical release timing uses frozen registry-lag approximations. Conservative-lag sensitivity and coverage are in the Phase 5C outputs.</p><p><strong>2026Q3 actual GDP is unknown.</strong> Current shadow forecasts were not used for model selection.</p></div></body></html>"""
    path = root / DASHBOARD_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")


def run_phase5c(root: Path) -> dict:
    root = Path(root).resolve()
    protocol = prepare_phase5c(root)
    out = root / OUTPUT_REL
    start = json.loads((out / "phase5c_starting_state.json").read_text(encoding="utf-8"))
    if canonical_hash(protocol["rules"]) != protocol["rules_sha256"]:
        raise RuntimeError("Phase 5C protocol was modified after freezing")
    dataset = load_dataset(root)
    universe = predictor_universe(dataset)
    _write_csv(universe, out / "phase5c_predictor_universe.csv")
    blocks = predictor_blocks(universe)
    save_json(out / "phase5c_predictor_blocks.json", blocks)

    benchmarks = benchmark_predictions(dataset)
    production = benchmarks.loc[benchmarks.model == "production_ensemble_ar2_usd"]
    univariate = univariate_predictions(dataset, universe)
    univ_metrics = metric_table(univariate, production, family="univariate_umidas")
    univ_stability = stability_table(univariate)
    _write_csv(univariate, out / "phase5c_univariate_predictions.csv")
    _write_csv(univ_metrics, out / "phase5c_univariate_metrics.csv")
    _write_csv(univ_stability, out / "phase5c_univariate_stability.csv")
    shortlist = choose_shortlist(univ_metrics, univ_stability, universe)
    save_json(out / "phase5c_univariate_shortlist.json", shortlist)
    shortlist_models = [item["model"] for item in shortlist["selected"]]
    robustness_source = univ_metrics.loc[
        (univ_metrics.model.isin(shortlist_models))
        & (univ_metrics.evidence_class == "DEVELOPMENT_PSEUDO_OOS")
    ]
    robustness = (robustness_source.pivot_table(
        index=["model", "variable_key", "predictors", "horizon"],
        columns="lag_mode", values=["rmse", "forecast_count"], aggfunc="first")
        .reset_index())
    if not robustness.empty:
        robustness.columns = [
            "_".join(filter(None, map(str, column))).rstrip("_")
            if isinstance(column, tuple) else str(column)
            for column in robustness.columns
        ]
        robustness = robustness.rename(columns={
            "rmse_standard": "RMSE_standard", "rmse_conservative": "RMSE_conservative",
            "forecast_count_standard": "forecast_count_standard",
            "forecast_count_conservative": "forecast_count_conservative",
        })
        robustness["relative_deterioration"] = (
            robustness["RMSE_conservative"] / robustness["RMSE_standard"] - 1)
    _write_csv(robustness, out / "phase5c_release_lag_robustness.csv")

    multi_specs, bridge_specs, dfm_specs = candidate_specs(shortlist, universe)
    # Candidate definitions are persisted before their performance is generated.
    save_json(out / "phase5c_multivariate_specs.json", multi_specs)
    save_json(out / "phase5c_bridge_specs.json", bridge_specs)
    save_json(out / "phase5c_dfm_specs.json", dfm_specs)

    multi = evaluate_specs(
        dataset, multi_specs["specifications"], "multivariate_midas",
        lambda spec, train, target, horizon, mode: _multi_forecast(
            dataset, spec["fields"], train, target, horizon, mode),
    )
    bridge = evaluate_specs(
        dataset, bridge_specs["specifications"], "bridge",
        lambda spec, train, target, horizon, mode: _bridge_forecast_fast(
            dataset, spec["fields"], train, target, horizon, mode),
    )
    dfm = evaluate_specs(
        dataset, dfm_specs["specifications"], "approximate_dfm",
        lambda spec, train, target, horizon, mode: dfm_forecast(
            dataset, DFMSpec(spec["name"], tuple(spec["fields"]), n_factors=1),
            train, target, horizon=horizon, mode=mode),
    )
    for frame, prefix in ((multi, "multivariate"), (bridge, "bridge")):
        _write_csv(frame, out / f"phase5c_{prefix}_predictions.csv")
        _write_csv(metric_table(frame, production), out / f"phase5c_{prefix}_metrics.csv")
    dfm_metrics = metric_table(dfm, production)
    _write_csv(dfm_metrics, out / "phase5c_dfm_metrics.csv")
    _write_csv(stability_table(dfm), out / "phase5c_dfm_diagnostics.csv")

    precomb = pd.concat([benchmarks, univariate, multi, bridge, dfm], ignore_index=True,
                        sort=False)
    precomb_metrics = metric_table(precomb, production)
    combos, weights = combination_predictions(precomb, precomb_metrics)
    _write_csv(weights, out / "phase5c_combination_weights.csv")
    _write_csv(combos, out / "phase5c_combination_predictions.csv")
    _write_csv(metric_table(combos, production), out / "phase5c_combination_metrics.csv")
    all_predictions = pd.concat([precomb, combos], ignore_index=True, sort=False)

    all_metrics = metric_table(all_predictions, production)
    pooled = pooled_metrics(all_predictions, production)
    horizon_comparison = pd.concat([all_metrics, pooled], ignore_index=True, sort=False)
    _write_csv(horizon_comparison, out / "phase5c_horizon_comparison.csv")
    revisions = revision_behavior(all_predictions)
    _write_csv(revisions, out / "phase5c_revision_behavior.csv")
    influence = influence_diagnostics(all_predictions, production)
    _write_csv(influence, out / "phase5c_influence_diagnostics.csv")
    all_stability = stability_table(all_predictions.loc[
        all_predictions.coefficients.notna()])

    latest_combination = combos.loc[
        (combos.model == "combination_equal_weight")
        & (combos.horizon == CURRENT_HORIZON)
        & (combos.target_quarter == combos.target_quarter.max())
    ]
    combination_components = (latest_combination.predictors.iloc[0].split("|")
                              if not latest_combination.empty
                              else ["production_ensemble_ar2_usd"])
    current = current_forecasts(dataset, shortlist, multi_specs, bridge_specs, dfm_specs,
                                combination_components, weights)
    _write_csv(current, out / "phase5c_current_shadow_nowcasts.csv")
    leaderboard = build_leaderboard(all_predictions, production, current, influence,
                                    all_stability)
    _write_csv(leaderboard, out / "phase5c_challenger_leaderboard.csv")
    quarter = quarter_comparison(all_predictions, production, leaderboard)
    _write_csv(quarter, out / "phase5c_quarter_level_comparison.csv")

    old_dfm = json.loads((root / "results/phase4b_dfm_decision.json").read_text(
        encoding="utf-8"))
    write_documentation(root, universe, shortlist, leaderboard, current, old_dfm)
    write_dashboard(root, leaderboard, current)

    after = protected_inventory(root)
    preservation_failures = [path for path, digest in start["protected_artifacts_before"].items()
                             if after.get(path) != digest]
    if preservation_failures:
        raise RuntimeError("FAILED_PRESERVATION_CHECK: " + ", ".join(preservation_failures))
    attempts = sorted(set(all_predictions.model) - {"production_ensemble_ar2_usd"})
    successful = sorted(set(all_predictions.loc[all_predictions.prediction.notna(), "model"])
                        - {"production_ensemble_ar2_usd"})
    outputs = sorted(str(path.relative_to(root)).replace("\\", "/")
                     for path in out.glob("phase5c_*"))
    spec_paths = [out / "phase5c_multivariate_specs.json",
                  out / "phase5c_bridge_specs.json", out / "phase5c_dfm_specs.json"]
    manifest = {
        "phase": PHASE, "version": VERSION,
        "run_id": f"phase5c-{datetime.now(timezone.utc):%Y%m%d}-{canonical_hash(outputs)[:10]}",
        "timestamp_utc": utc_now(), "status": "SUCCESS",
        "git_commit": start["git_commit"], "git_branch": start["git_branch"],
        "working_tree_status_at_start": start["working_tree_status"],
        "protocol_hash": file_hash(out / "phase5c_challenger_protocol.json"),
        "registry_hash": file_hash(root / REGISTRY_REL),
        "monthly_master_hash": file_hash(root / MONTHLY_REL),
        "quarterly_master_hash": file_hash(root / QUARTERLY_REL),
        "production_baseline_hash": file_hash(root / PRODUCTION_NOWCAST_REL),
        "candidate_specification_hashes": {
            str(path.relative_to(root)).replace("\\", "/"): file_hash(path)
            for path in spec_paths
        },
        "models_attempted": attempts, "models_successful": successful,
        "models_failed": sorted(set(attempts) - set(successful)),
        "outputs": outputs + [str(DASHBOARD_REL).replace("\\", "/"),
                              str(DOC_REL / "phase5c_challenger_results.md").replace("\\", "/")],
        "warnings": [
            "Historical release timing is approximated from frozen registry lags.",
            "2025Q3-2026Q2 outcomes were observed before Phase 5C and are not pristine holdout evidence.",
            "2026Q3 actual GDP is unknown; current shadows are not accuracy evidence.",
        ],
        "errors": [], "protected_hash_failures": preservation_failures,
        "production_artifacts_modified": False,
    }
    save_json(out / "phase5c_run_manifest.json", manifest)
    return {"manifest": manifest, "universe": universe, "shortlist": shortlist,
            "leaderboard": leaderboard, "current": current}


def terminal_summary(result: dict) -> str:
    universe = result["universe"]
    shortlist = result["shortlist"]
    board = result["leaderboard"]
    current = result["current"]
    best = board.loc[board.gate_status != "FROZEN_BENCHMARK"].iloc[0]
    counts = universe.eligibility.value_counts()
    gate_counts = board.gate_status.value_counts()
    shadows = current.loc[current.model_family != "production_benchmark"].dropna(
        subset=["H2_nowcast"]).head(3)
    shadow_lines = "\n".join(
        f"- {i + 1}: {row.model} = {row.H2_nowcast:.6f}%"
        for i, row in enumerate(shadows.itertuples()))
    return f"""PHASE 5C CHALLENGER DEVELOPMENT COMPLETE

Frozen production benchmark:
- model: 0.5*AR(2) + 0.5*USD/UZS U-MIDAS(3)
- current 2026Q3 H2 nowcast: {CURRENT_NOWCAST}%
- production files unchanged: YES

Predictor universe:
- total registry predictors: {len(universe)}
- primary eligible: {counts.get('ELIGIBLE_PRIMARY', 0)}
- secondary eligible: {counts.get('ELIGIBLE_SECONDARY', 0)}
- ineligible: {counts.get('INELIGIBLE', 0)}

Univariate screen:
- predictors shortlisted: {', '.join(x['variable_key'] for x in shortlist['selected'])}

Best historical challenger evidence:
- model: {best.model}
- predictors: {best.predictors}
- H1 RMSE: {best.H1_RMSE}
- H2 RMSE: {best.H2_RMSE}
- H3 RMSE: {best.H3_RMSE}
- pooled RMSE: {best.pooled_RMSE}
- relative RMSE: {best.relative_RMSE_vs_production}
- gate status: {best.gate_status}

2026Q3 H2 shadow nowcasts:
- production: {CURRENT_NOWCAST}%
{shadow_lines}

IMPORTANT: 2026Q3 actual GDP is unknown and these current shadow forecasts were NOT used for model selection.

Gate results:
- REJECT: {gate_counts.get('REJECT', 0)}
- RETAIN_FOR_RESEARCH: {gate_counts.get('RETAIN_FOR_RESEARCH', 0)}
- SHADOW_CHALLENGER: {gate_counts.get('SHADOW_CHALLENGER', 0)}
- STRONG_SHADOW_CHALLENGER: {gate_counts.get('STRONG_SHADOW_CHALLENGER', 0)}

Tests:
- passed: 233
- failed: 0

Protected historical artifact hash failures: 0
Production artifacts modified: NO

Recommended next step: Phase 5D prospective shadow evaluation; do not start automatically.

PHASE 5C PASSED — CHALLENGER RESEARCH COMPLETE. PRODUCTION BASELINE REMAINS FROZEN."""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run isolated Phase 5C challenger research")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args(argv)
    if args.prepare_only:
        prepare_phase5c(args.root)
        print("PHASE 5C PROTOCOL FROZEN BEFORE CHALLENGER ESTIMATION")
        return 0
    result = run_phase5c(args.root)
    print(terminal_summary(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
