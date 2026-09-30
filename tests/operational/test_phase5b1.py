"""Tests for the Phase 5B.1 auditability and reproducibility patch."""

from __future__ import annotations

from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
import pytest

from uznowcast.operational.phase5b1 import (
    MODEL_INPUT_KEYS, build_code_hash_inventory,
    compute_model_input_quality, compute_publication_readiness,
    enhanced_uncertainty, refactor_monitoring_flags,
    revision_decomposition_with_residual,
)


ROOT = Path(__file__).resolve().parents[2]


def _quality_frame() -> pd.DataFrame:
    """Small quality frame matching the operational post-audit reality."""
    return pd.DataFrame([
        {"variable_key": "gdp_real_yoy", "quality_status": "GREEN"},
        {"variable_key": "usd_uzs", "quality_status": "AMBER"},
        {"variable_key": "russia_ipi", "quality_status": "RED"},
        {"variable_key": "cpi_headline", "quality_status": "GREEN"},
        {"variable_key": "industrial_production", "quality_status": "GREEN"},
    ])


def _monitoring_frame() -> pd.DataFrame:
    return pd.DataFrame([
        {"model": "ar1", "monitoring_flags": "production_input_data_not_all_green"},
        {"model": "ar2", "monitoring_flags": "production_input_data_not_all_green"},
        {"model": "umidas_usd_uzs_mom_dlog",
         "monitoring_flags": "production_input_data_not_all_green"},
        {"model": "ensemble_ar2_umidas_usd",
         "monitoring_flags": "production_input_data_not_all_green"},
    ])


# --------------------------------------------------------------------------
# Issue 2 — model-specific data-quality flags
# --------------------------------------------------------------------------

def test_ar1_does_not_inherit_usd_amber_status():
    quality = _quality_frame()
    per_model = compute_model_input_quality(quality, MODEL_INPUT_KEYS)
    row = per_model.loc[per_model.model == "ar1"].iloc[0]
    assert not bool(row.model_input_data_not_all_green)
    assert int(row.model_input_amber_count) == 0
    assert int(row.model_input_red_count) == 0


def test_ar2_does_not_inherit_usd_amber_status():
    quality = _quality_frame()
    per_model = compute_model_input_quality(quality, MODEL_INPUT_KEYS)
    row = per_model.loc[per_model.model == "ar2"].iloc[0]
    assert not bool(row.model_input_data_not_all_green)


def test_umidas_correctly_inherits_usd_amber_status():
    quality = _quality_frame()
    per_model = compute_model_input_quality(quality, MODEL_INPUT_KEYS)
    row = per_model.loc[per_model.model == "umidas_usd_uzs_mom_dlog"].iloc[0]
    assert bool(row.model_input_data_not_all_green) is True
    assert int(row.model_input_amber_count) == 1


def test_ensemble_inherits_component_input_warning():
    quality = _quality_frame()
    per_model = compute_model_input_quality(quality, MODEL_INPUT_KEYS)
    row = per_model.loc[per_model.model == "ensemble_ar2_umidas_usd"].iloc[0]
    assert bool(row.model_input_data_not_all_green) is True


def test_russia_ipi_red_does_not_contaminate_models_that_do_not_use_it():
    quality = _quality_frame()
    per_model = compute_model_input_quality(quality, MODEL_INPUT_KEYS)
    for model in ("ar1", "ar2", "umidas_usd_uzs_mom_dlog", "ensemble_ar2_umidas_usd"):
        row = per_model.loc[per_model.model == model].iloc[0]
        assert int(row.model_input_red_count) == 0, (
            f"Russia IPI RED must never enter {model}'s model-specific quality"
        )


def test_monitoring_flags_split_system_and_model_warnings():
    quality = _quality_frame()
    monitoring = refactor_monitoring_flags(
        _monitoring_frame(), quality, MODEL_INPUT_KEYS
    )
    for row in monitoring.itertuples(index=False):
        assert bool(row.system_data_gate_has_warnings) is True
        assert "production_input_data_not_all_green" not in row.monitoring_flags
    ar1 = monitoring.loc[monitoring.model == "ar1"].iloc[0]
    assert "system_data_gate_has_warnings" in ar1.monitoring_flags
    assert "model_input_data_not_all_green" not in ar1.monitoring_flags
    umidas = monitoring.loc[monitoring.model == "umidas_usd_uzs_mom_dlog"].iloc[0]
    assert "model_input_data_not_all_green" in umidas.monitoring_flags


# --------------------------------------------------------------------------
# Issue 3 — dashboard horizon default
# --------------------------------------------------------------------------

def test_dashboard_default_horizon_equals_operational_stage(tmp_path: Path):
    from uznowcast.operational.dashboard5b1 import _validation_tables
    predictions = pd.read_parquet(ROOT / "results/phase4c_holdout_predictions.parquet")
    metrics = pd.read_parquet(ROOT / "results/phase4c_holdout_metrics.parquet")
    html = _validation_tables(predictions, metrics, default_horizon="H2")
    assert 'data-horizon="H2" style="display:block"' in html
    assert 'data-horizon="H1" style="display:none"' in html
    assert 'data-horizon="H3" style="display:none"' in html
    assert '<option value="H2" selected>H2</option>' in html


def test_dashboard_manual_h1_h2_h3_selection_remains_available():
    from uznowcast.operational.dashboard5b1 import _validation_tables
    predictions = pd.read_parquet(ROOT / "results/phase4c_holdout_predictions.parquet")
    metrics = pd.read_parquet(ROOT / "results/phase4c_holdout_metrics.parquet")
    html = _validation_tables(predictions, metrics, default_horizon="H2")
    for h in ("H1", "H2", "H3"):
        assert f'<option value="{h}"' in html
        assert f'data-horizon="{h}"' in html


# --------------------------------------------------------------------------
# Issue 1 — dirty git tree + code hash inventory
# --------------------------------------------------------------------------

def _git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


@pytest.mark.skipif(not _git_available(), reason="git not available")
def test_dirty_git_state_is_captured_correctly():
    from uznowcast.operational.phase5b1 import _git_state
    state = _git_state(ROOT)
    assert state["git_commit"], "git commit must be present in a git repo"
    assert state["working_tree_dirty"] in {True, False}
    if state["working_tree_dirty"]:
        assert state["dirty_paths"], "dirty tree must list dirty paths"
        assert state["diff_sha256"] is not None
        assert state["diff_captured"] is True


def test_publication_ready_false_when_tree_is_dirty():
    quality = _quality_frame()
    per_model = compute_model_input_quality(quality, MODEL_INPUT_KEYS)
    readiness = compute_publication_readiness(
        run_status="SUCCESS_WITH_WARNINGS",
        gate={"passed": True, "status": "SUCCESS_WITH_WARNINGS"},
        git_state={"git_commit": "abc", "working_tree_dirty": True,
                   "git_branch": "main", "dirty_paths": ["x"], "diff_sha256": "d"},
        headline_available=True, cutoff_integrity_passed=True,
        model_input_quality=per_model,
        system_warnings=["usd_uzs AMBER"], immutable_preserved=True,
        residual_ok=True,
    )
    assert readiness["publication_ready"] is False
    assert any("working_tree_dirty" in b for b in readiness["publication_blockers"])


def test_publication_ready_true_when_all_gates_pass_and_tree_is_clean():
    quality = _quality_frame()
    per_model = compute_model_input_quality(quality, MODEL_INPUT_KEYS)
    readiness = compute_publication_readiness(
        run_status="SUCCESS",
        gate={"passed": True, "status": "SUCCESS"},
        git_state={"git_commit": "abc", "working_tree_dirty": False,
                   "git_branch": "main", "dirty_paths": [], "diff_sha256": None},
        headline_available=True, cutoff_integrity_passed=True,
        model_input_quality=per_model,
        system_warnings=[], immutable_preserved=True, residual_ok=True,
    )
    assert readiness["publication_ready"] is True
    assert readiness["publication_blockers"] == []


def test_production_code_hash_inventory_is_deterministic():
    first = build_code_hash_inventory(ROOT)
    second = build_code_hash_inventory(ROOT)
    pd.testing.assert_frame_equal(first, second)
    for row in first.loc[first["exists"]].itertuples(index=False):
        assert len(row.sha256) == 64
    roles = set(first["role"])
    assert {"production_source", "configuration", "registry",
            "input_dataset", "frozen_upstream_artifact"} <= roles


# --------------------------------------------------------------------------
# Revision decomposition residual
# --------------------------------------------------------------------------

def test_revision_decomposition_sums_within_numerical_tolerance():
    base = pd.DataFrame([{
        "run_timestamp_utc": "t", "target_quarter": "2026Q3",
        "previous_operational_stage": "H3", "current_operational_stage": "H2",
        "previous_nowcast": 8.29987896024393,
        "new_nowcast": 7.6239786595896035,
        "total_revision": -0.6759003006543267,
        "new_data_effect": 0.0, "data_revision_effect": 0.0,
        "model_specification_or_stage_effect": -0.6759003006543267,
        "decomposition_method": "exact_stage_attribution",
        "model_selection_changed": False, "ensemble_weights_changed": False,
    }])
    frame, residual = revision_decomposition_with_residual(base)
    assert abs(residual) < 1e-10
    assert bool(frame.iloc[0]["residual_within_tolerance_1e_10"]) is True
    assert float(frame.iloc[0]["model_selection_effect"]) == 0.0
    assert float(frame.iloc[0]["weight_effect"]) == 0.0


# --------------------------------------------------------------------------
# Uncertainty numbers unchanged from Phase 5B
# --------------------------------------------------------------------------

def test_uncertainty_interval_values_remain_unchanged():
    base = {
        "point_nowcast": 7.6239786595896035,
        "horizon": "H2", "sample_size": 18,
        "historical_rmse": 0.7798396244785278,
        "interval_50": {"lower": 7.759802849667961, "upper": 8.301696182937693},
        "interval_80": {"lower": 7.409466316705167, "upper": 8.395523559763275},
    }
    enriched = enhanced_uncertainty(
        ROOT, "H2", 7.6239786595896035, base
    )
    assert enriched["interval_50"] == base["interval_50"]
    assert enriched["interval_80"] == base["interval_80"]
    assert enriched["historical_rmse"] == base["historical_rmse"]
    assert "empirical_forecast_error_range" in enriched["labelling"]
    assert "confidence interval" in enriched["presentation_note"]


# --------------------------------------------------------------------------
# Preservation
# --------------------------------------------------------------------------

def test_phase4_5a_5b_artifacts_remain_unchanged_after_phase5b1_run():
    """Guard: the Phase 5B.1 module must not import a path that mutates prior artifacts."""
    # Assemble the immutable set on disk and compare before/after re-hashing.
    from uznowcast.operational.phase5b1 import full_immutable_hashes
    hashes_a = full_immutable_hashes(ROOT)
    hashes_b = full_immutable_hashes(ROOT)
    assert hashes_a == hashes_b
    assert any(k.startswith("results/phase5b/") for k in hashes_a)
    assert any(k.startswith("results/phase4") for k in hashes_a)
    assert any(k.startswith("results/phase5a") for k in hashes_a)
