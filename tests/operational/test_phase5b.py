from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from uznowcast.models.data import ModelingDataset
from uznowcast.operational.phase5b import (
    CURRENT_REQUIRED_FIELDS, build_data_quality, build_data_status,
    build_information_set_audit, build_model_input_audit,
    detect_operational_stage, phase5b_policy, production_gate,
    revision_outputs, validate_current_payload,
)
from tests.models.conftest import make_gdp_frame, make_monthly_panel, make_registry_stub


def hardened_dataset() -> ModelingDataset:
    gdp = make_gdp_frame(n_quarters=34)
    monthly = make_monthly_panel(
        n_months=105, fields=("usd_uzs_mom_dlog", "other_field")
    )
    monthly.loc[pd.Timestamp("2026-09-30"), "usd_uzs_mom_dlog"] = np.nan
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


def _target() -> dict:
    return {
        "target_quarter": "2026Q3", "latest_known_gdp_quarter": "2026Q2",
        "latest_known_gdp_growth": 8.5,
        "known_gdp_quarters": [q.replace("-", "") for q in make_gdp_frame(2018, 34)["quarter"]],
    }


def test_stage_detection_uses_actual_complete_signal_not_calendar():
    state = detect_operational_stage(hardened_dataset(), "2026Q3", "2026-09-30")
    assert state["calendar_stage"] == "H3"
    assert state["horizon"] == "H2"
    assert state["next_missing_signal_month"] == "2026-09-30"


def test_stage_detection_reaches_h3_when_third_month_exists():
    dataset = hardened_dataset()
    dataset.monthly.loc[pd.Timestamp("2026-09-30"), "usd_uzs_mom_dlog"] = 0.25
    assert detect_operational_stage(dataset, "2026Q3", "2026-09-30")["horizon"] == "H3"


def test_missing_value_classification_distinguishes_structural_lag(tmp_path: Path):
    dataset = hardened_dataset()
    state = detect_operational_stage(dataset, "2026Q3", "2026-09-30")
    status = build_data_status(tmp_path, dataset, "2026-09-30", "2026Q3", state)
    september_other = status.loc[
        (status.variable_key == "other") & (status.reference_period == "2026-09-30")
    ].iloc[0]
    assert september_other.missing_value_classification == "structural_publication_lag"


def test_partial_required_month_is_deliberately_excluded(tmp_path: Path):
    dataset = hardened_dataset()
    processed = tmp_path / "data/processed"
    processed.mkdir(parents=True)
    pd.DataFrame({
        "reference_date": [pd.Timestamp("2026-09-30")],
        "quality_flag": ["partial_month"],
    }).to_parquet(processed / "usd_uzs.parquet")
    state = detect_operational_stage(dataset, "2026Q3", "2026-09-30")
    status = build_data_status(tmp_path, dataset, "2026-09-30", "2026Q3", state)
    row = status.loc[
        (status.variable_key == "usd_uzs") & (status.reference_period == "2026-09-30")
    ].iloc[0]
    assert row.missing_value_classification == "deliberately_excluded_observation"
    assert not row.fallback_used


def test_data_quality_gate_allows_amber_required_series(tmp_path: Path):
    dataset = hardened_dataset()
    quality = build_data_quality(tmp_path, dataset, "2026Q3", "2026-09-30")
    state = detect_operational_stage(dataset, "2026Q3", "2026-09-30")
    frozen = {"primary_candidate_models": list((
        "ar1", "ar2", "umidas_usd_uzs_mom_dlog", "ensemble_ar2_umidas_usd"
    ))}
    gate = production_gate(dataset, quality, state, frozen)
    assert gate["passed"]
    assert gate["status"] in {"SUCCESS", "SUCCESS_WITH_WARNINGS"}


def test_data_quality_gate_rejects_red_required_series(tmp_path: Path):
    dataset = hardened_dataset()
    quality = build_data_quality(tmp_path, dataset, "2026Q3", "2026-09-30")
    quality.loc[quality.variable_key == "usd_uzs", ["quality_status", "gate_passed"]] = ["RED", False]
    state = detect_operational_stage(dataset, "2026Q3", "2026-09-30")
    frozen = {"primary_candidate_models": [
        "ar1", "ar2", "umidas_usd_uzs_mom_dlog", "ensemble_ar2_umidas_usd"
    ]}
    gate = production_gate(dataset, quality, state, frozen)
    assert not gate["passed"]
    assert gate["status"] == "FAILED_DATA_GATE"


def test_information_set_cutoff_enforced():
    dataset = hardened_dataset()
    state = detect_operational_stage(dataset, "2026Q3", "2026-09-30")
    audit = build_information_set_audit(Path("."), dataset, _target(), state)
    assert audit.cutoff_check_passed.all()
    assert (pd.to_datetime(audit.loc[audit.variable_key == "usd_uzs", "assumed_available_date"])
            <= pd.to_datetime(audit.loc[audit.variable_key == "usd_uzs", "forecast_origin"])).all()


def test_model_input_audit_labels_exact_variables():
    models = ["ar1", "ar2", "umidas_usd_uzs_mom_dlog", "ensemble_ar2_umidas_usd"]
    nowcasts = pd.DataFrame({
        "model": models, "prediction": [7.0, 7.1, 8.0, 7.55],
        "effective_model_training_rows": [33, 32, 20, 20],
    }).set_index("model", drop=False)
    diagnostics = {"usd_monthly_observations_used": [
        {"reference_period": "2026-06-30", "value": 1.0},
        {"reference_period": "2026-07-31", "value": 2.0},
        {"reference_period": "2026-08-31", "value": 3.0},
    ]}
    audit = build_model_input_audit(
        nowcasts.reset_index(drop=True), diagnostics, _target(),
        {"horizon": "H2"}, {"passed": True},
    )
    usd = audit.loc[audit.variable == "usd_uzs_mom_dlog"].iloc[0]
    assert usd.lags_used == "last 3 available monthly observations"
    assert "2026-08-31" in usd.exact_latest_monthly_observations
    assert not usd.fallback_used


def test_revision_decomposition_attributes_same_input_change_to_stage(tmp_path: Path):
    (tmp_path / "results").mkdir()
    previous_predictions = [{"model": m, "prediction": p} for m, p in {
        "ar1": 7.0, "ar2": 7.1, "umidas_usd_uzs_mom_dlog": 8.0,
        "ensemble_ar2_umidas_usd": 7.55,
    }.items()]
    (tmp_path / "results/phase5a_current_nowcast.json").write_text(
        __import__("json").dumps({
            "predictions": previous_predictions,
            "run": {"horizon_detection": {"horizon": "H3"}},
        }), encoding="utf-8")
    hashes = {"monthly_master_hash": "m", "quarterly_master_hash": "q", "registry_hash": "r"}
    (tmp_path / "results/phase5a_run_manifest.json").write_text(
        __import__("json").dumps({"input_hashes": hashes}), encoding="utf-8")
    nowcasts = pd.DataFrame({
        "model": [p["model"] for p in previous_predictions],
        "prediction": [7.0, 7.1, 8.2, 7.65],
        "as_of_date": ["2026-09-30"] * 4,
        "target_quarter": ["2026Q3"] * 4,
        "horizon": ["H2"] * 4,
        "production_headline_flag": [False, False, False, True],
    })
    decomposition, history = revision_outputs(
        tmp_path, nowcasts, "t", _target(), {"horizon": "H2"}, hashes
    )
    assert decomposition.iloc[0].new_data_effect == 0
    assert decomposition.iloc[0].data_revision_effect == 0
    assert np.isclose(decomposition.iloc[0].model_specification_or_stage_effect, 0.1)
    assert len(history) == 4


def test_production_policy_retains_frozen_model_and_weights():
    policy = phase5b_policy("t")
    assert policy["headline_model"] == "ensemble_ar2_umidas_usd"
    assert policy["ensemble_weights"] == {"ar2": 0.5, "umidas_usd_uzs_mom_dlog": 0.5}
    assert policy["model_selection"] == "unchanged from Phase 5A; no automatic switching"


def test_current_json_schema_validator():
    payload = {field: None for field in CURRENT_REQUIRED_FIELDS}
    payload["status"] = "SUCCESS"
    validate_current_payload(payload)
    del payload["target"]
    with pytest.raises(ValueError, match="missing fields"):
        validate_current_payload(payload)
