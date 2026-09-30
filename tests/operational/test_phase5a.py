from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

from uznowcast.models.data import ModelingDataset
from uznowcast.operational.dashboard import render_dashboard
from uznowcast.operational.phase5a import (
    NOWCAST_COLUMNS, REVISION_COLUMNS, build_data_status,
    build_revision_history, detect_horizon, detect_target_quarter,
    file_sha256, generate_nowcasts, phase4_artifact_hashes,
    release_aware_dataset,
)
from tests.models.conftest import make_gdp_frame, make_monthly_panel, make_registry_stub


def operational_dataset() -> ModelingDataset:
    gdp = make_gdp_frame(n_quarters=34)
    monthly = make_monthly_panel(n_months=105, fields=("usd_uzs_mom_dlog", "other_field"))
    clean = {
        "gdp_real_yoy": "gdp_real_yoy_pct",
        "usd_uzs": "usd_uzs_mom_dlog",
        "other": "other_field",
    }
    registry = make_registry_stub(clean, {
        "gdp_real_yoy": 31, "usd_uzs": 0, "other": 30,
    })
    for key, row in registry.rows.items():
        row.update(display_name=key, human_source_url="https://example.test/source")
    return ModelingDataset(
        gdp=gdp, monthly=monthly, registry=registry,
        release_lag_days={"gdp_real_yoy": 31, "usd_uzs": 0, "other": 30},
        clean_field_by_key=clean,
        monthly_key_by_field={v: k for k, v in clean.items()},
    )


def forecast_inputs():
    dataset = operational_dataset()
    target = detect_target_quarter(dataset, "2026-09-30")
    horizon = detect_horizon(target["target_quarter"], "2026-09-30")
    hashes = {
        "monthly_master_hash": "m", "quarterly_master_hash": "q", "registry_hash": "r"
    }
    return dataset, target, horizon, hashes


def test_target_quarter_detection_uses_release_aware_gdp():
    dataset = operational_dataset()
    result = detect_target_quarter(dataset, "2026-09-30")
    assert result["target_quarter"] == "2026Q3"
    assert result["latest_known_gdp_quarter"] == "2026Q2"


def test_horizon_detection_uses_existing_cutoffs_between_month_ends():
    assert detect_horizon("2026Q3", "2026-08-15")["horizon"] == "H1"
    assert detect_horizon("2026Q3", "2026-09-15")["horizon"] == "H2"
    assert detect_horizon("2026Q3", "2026-09-30")["horizon"] == "H3"


def test_release_aware_view_excludes_target_quarter_gdp():
    dataset, target, _, _ = forecast_inputs()
    view = release_aware_dataset(dataset, "2026-09-30", target["known_gdp_quarters"])
    labels = set(view.gdp["quarter"].str.replace("-", "", regex=False))
    assert "2026Q3" not in labels


def test_release_aware_view_excludes_all_later_gdp():
    dataset, target, _, _ = forecast_inputs()
    extra = pd.DataFrame({"quarter": ["2026-Q3", "2026-Q4"], "gdp_real_yoy_pct": [99.0, 100.0]})
    dataset = ModelingDataset(**{**dataset.__dict__, "gdp": pd.concat([dataset.gdp, extra])})
    view = release_aware_dataset(dataset, "2026-09-30", target["known_gdp_quarters"])
    assert view.gdp["gdp_real_yoy_pct"].max() < 99


def test_monthly_value_released_after_as_of_is_masked():
    dataset = operational_dataset()
    dataset.monthly.loc[pd.Timestamp("2026-09-30"), "other_field"] = 123.0
    view = release_aware_dataset(dataset, "2026-09-30", ["2026Q2"])
    assert np.isnan(view.monthly.loc[pd.Timestamp("2026-09-30"), "other_field"])


def test_exact_fifty_fifty_ensemble_arithmetic():
    dataset, target, horizon, hashes = forecast_inputs()
    frame, diagnostics = generate_nowcasts(
        dataset, "2026-09-30", target, horizon, hashes, "2026-09-30T00:00:00Z"
    )
    values = frame.set_index("model")["prediction"]
    expected = 0.5 * values["ar2"] + 0.5 * values["umidas_usd_uzs_mom_dlog"]
    assert values["ensemble_ar2_umidas_usd"] == expected
    assert diagnostics["ensemble_arithmetic"]["identity_passed"]


def test_hash_helper_records_exact_sha256(tmp_path: Path):
    path = tmp_path / "input.bin"
    path.write_bytes(b"phase5a")
    assert file_sha256(path) == sha256(b"phase5a").hexdigest()


def test_current_nowcast_schema_and_leakage_flags():
    dataset, target, horizon, hashes = forecast_inputs()
    frame, diagnostics = generate_nowcasts(
        dataset, "2026-09-30", target, horizon, hashes, "2026-09-30T00:00:00Z"
    )
    assert tuple(frame.columns) == NOWCAST_COLUMNS
    assert set(frame["model"]) == {
        "ar1", "ar2", "umidas_usd_uzs_mom_dlog", "ensemble_ar2_umidas_usd"
    }
    assert all(diagnostics["leakage_checks"].values())


def _write_phase4_dashboard_fixtures(root: Path) -> None:
    results = root / "results"
    results.mkdir(parents=True, exist_ok=True)
    prediction_rows = []
    update_rows = []
    models = ["historical_mean", "ar1", "ar2", "umidas_usd_uzs_mom_dlog", "ensemble_ar2_umidas_usd"]
    quarters = ["2025Q3", "2025Q4", "2026Q1", "2026Q2"]
    for qi, quarter in enumerate(quarters):
        actual = 7.6 + qi * 0.2
        for mi, model in enumerate(models):
            forecasts = []
            for hi, horizon in enumerate(("H1", "H2", "H3")):
                pred = actual - 0.5 + 0.1 * hi + 0.02 * mi
                forecasts.append(pred)
                prediction_rows.append({
                    "model": model, "lag_mode": "standard", "horizon": horizon,
                    "target_quarter": quarter, "prediction": pred, "actual": actual,
                })
            update_rows.append({
                "model": model, "lag_mode": "standard", "target_quarter": quarter,
                "actual": actual, "H1_prediction": forecasts[0],
                "H2_prediction": forecasts[1], "H3_prediction": forecasts[2],
            })
    pd.DataFrame(prediction_rows).to_parquet(results / "phase4c_holdout_predictions.parquet")
    pd.DataFrame(update_rows).to_parquet(results / "phase4c_horizon_updates.parquet")
    metric_rows = []
    for model in models:
        for horizon in ("H1", "H2", "H3", "POOLED_H1_H3"):
            metric_rows.append({
                "model": model, "horizon": horizon, "lag_mode": "standard", "rmse": 0.5,
            })
    pd.DataFrame(metric_rows).to_parquet(results / "phase4c_holdout_metrics.parquet")


def _minimal_nowcasts() -> pd.DataFrame:
    rows = []
    for i, model in enumerate(("ar1", "ar2", "umidas_usd_uzs_mom_dlog", "ensemble_ar2_umidas_usd")):
        rows.append({
            "model": model, "prediction": 7.0 + i / 10,
            "production_headline_flag": model == "ensemble_ar2_umidas_usd",
            "horizon": "H3", "as_of_date": "2026-09-30",
            "target_quarter": "2026Q3",
        })
    return pd.DataFrame(rows)


def test_revision_history_schema(tmp_path: Path):
    _write_phase4_dashboard_fixtures(tmp_path)
    frame = build_revision_history(tmp_path, _minimal_nowcasts(), "2026-09-30T00:00:00Z")
    assert tuple(frame.columns) == REVISION_COLUMNS
    assert {True, False} == set(frame["live_production_flag"])


def test_dashboard_generation_is_self_contained(tmp_path: Path):
    _write_phase4_dashboard_fixtures(tmp_path)
    availability = {
        "registered_indicators": 2, "currently_usable_indicators": 1,
        "awaiting_release_indicators": 0, "missing_unavailable_indicators": 1,
        "latest_usable_monthly_reference_period": "2026-08-31",
        "indicator_summary": [
            {"variable_key": "usd_uzs", "indicator_status": "available", "most_recent_usable_reference_period": "2026-08-31"},
            {"variable_key": "other", "indicator_status": "missing_unavailable", "most_recent_usable_reference_period": None},
        ],
    }
    path = render_dashboard(
        root=tmp_path, nowcasts=_minimal_nowcasts(),
        target={"target_quarter": "2026Q3", "latest_known_gdp_growth": 8.5,
                "latest_known_gdp_quarter": "2026Q2", "reason": "release-aware target"},
        horizon_state={"horizon": "H3", "reason": "third month", "information_cutoff": "2026-09-30"},
        availability=availability,
        uncertainty={"reported": False, "reason": "test"}, data_status=pd.DataFrame(),
    )
    text = path.read_text(encoding="utf-8")
    assert "Uzbekistan Real GDP Nowcast" in text
    assert "https://" not in text
    assert "Frozen validation: 2025Q3–2026Q2" in text


def test_dashboard_does_not_modify_phase4_artifacts(tmp_path: Path):
    _write_phase4_dashboard_fixtures(tmp_path)
    docs = tmp_path / "docs/modeling"
    docs.mkdir(parents=True)
    (docs / "phase4c_frozen_holdout_evaluation.md").write_text("frozen", encoding="utf-8")
    before = phase4_artifact_hashes(tmp_path)
    test_dashboard_generation_is_self_contained(tmp_path)
    assert phase4_artifact_hashes(tmp_path) == before


def test_identical_inputs_reproduce_identical_forecast_values():
    dataset, target, horizon, hashes = forecast_inputs()
    first, _ = generate_nowcasts(dataset, "2026-09-30", target, horizon, hashes, "t1")
    second, _ = generate_nowcasts(dataset, "2026-09-30", target, horizon, hashes, "t2")
    pd.testing.assert_series_equal(first["prediction"], second["prediction"])


def test_data_status_marks_only_release_eligible_values_available():
    dataset = operational_dataset()
    dataset.monthly.loc[pd.Timestamp("2026-09-30"), "other_field"] = 123.0
    status, summary = build_data_status(dataset, "2026-09-30")
    row = status.loc[
        (status["variable_key"] == "other")
        & (status["reference_period"] == "2026-09-30")
    ].iloc[0]
    assert not bool(row["available_as_of"])
    assert row["exclusion_reason"] == "awaiting_assumed_release"
    assert summary["registered_indicators"] == 2
