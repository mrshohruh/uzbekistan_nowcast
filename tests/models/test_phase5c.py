"""Phase 5C governance, timing, and reproducibility guardrails."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd

from uznowcast.models.data import (
    effective_release_day, horizon_month_end, information_cutoff_for_variable,
    load_dataset,
)
from uznowcast.models.phase5c import (
    CURRENT_TARGET, MAX_MONTHLY_LAGS, MAX_MULTIVARIATE_PREDICTORS,
    OUTPUT_REL, PRODUCTION_NOWCAST_REL, _matched,
)
from uznowcast.registry import load_registry


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / OUTPUT_REL


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _json(name: str) -> dict:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_production_baseline_remains_unchanged():
    start = _json("phase5c_starting_state.json")
    assert _hash(ROOT / PRODUCTION_NOWCAST_REL) == start["input_hashes"]["production_nowcast"]
    current = json.loads((ROOT / PRODUCTION_NOWCAST_REL).read_text(encoding="utf-8"))
    assert current["point_nowcast"] == 7.6239786595896035


def test_phase4_through_phase5b2_immutable_hashes_unchanged():
    start = _json("phase5c_starting_state.json")
    failures = [relative for relative, expected in start["protected_artifacts_before"].items()
                if _hash(ROOT / relative) != expected]
    assert failures == []


def test_no_observation_enters_before_availability():
    dataset = load_dataset(ROOT)
    origin = horizon_month_end("2025Q1", "H1")
    cutoff = information_cutoff_for_variable(
        origin, "industrial_production", dataset.release_lag_days, "standard")
    assert cutoff < origin
    assert cutoff + pd.Timedelta(days=dataset.release_lag_days["industrial_production"]) <= origin


def test_predictor_transformations_match_registry():
    universe = pd.read_csv(OUT / "phase5c_predictor_universe.csv")
    registry = load_registry(ROOT / "registry/uzbekistan_nowcasting_v1.2_registry.xlsx")
    expected = {row["variable_key"]: row["required_transformation"]
                for row in registry.scope("v1") if row["variable_key"] != "gdp_real_yoy"}
    assert universe.set_index("variable_key").transformation.to_dict() == expected


def test_historical_forecasts_use_expanding_windows():
    predictions = pd.read_csv(OUT / "phase5c_univariate_predictions.csv")
    assert (predictions.training_last_quarter < predictions.target_quarter).all()
    counts = (predictions.drop_duplicates(["model", "target_quarter", "horizon", "lag_mode"])
              .sort_values("target_quarter").groupby(["model", "horizon", "lag_mode"])
              .n_training_quarters.apply(lambda x: x.is_monotonic_increasing))
    assert counts.all()


def test_future_gdp_never_enters_estimation():
    predictions = pd.read_csv(OUT / "phase5c_multivariate_predictions.csv")
    assert not predictions.empty
    assert (predictions.training_last_quarter < predictions.target_quarter).all()
    assert (predictions.training_first_quarter <= predictions.training_last_quarter).all()


def test_matched_sample_metrics_use_identical_quarters():
    candidate = pd.DataFrame({
        "target_quarter": ["2024Q1", "2024Q2"], "horizon": ["H1", "H1"],
        "lag_mode": ["standard", "standard"], "prediction": [1.0, np.nan],
    })
    production = pd.DataFrame({
        "target_quarter": ["2024Q1", "2024Q2"], "horizon": ["H1", "H1"],
        "lag_mode": ["standard", "standard"], "prediction": [1.2, 1.3],
        "error": [.2, .3],
    })
    matched = _matched(candidate, production)
    assert matched.target_quarter.tolist() == ["2024Q1"]


def test_candidate_lag_lengths_obey_protocol():
    protocol = _json("phase5c_challenger_protocol.json")
    predictions = pd.read_csv(OUT / "phase5c_univariate_predictions.csv")
    assert set(predictions.monthly_lags.unique()) <= {1, 2, 3}
    assert predictions.monthly_lags.max() == MAX_MONTHLY_LAGS
    assert protocol["rules"]["maximum_complexity"]["univariate_monthly_lags"] == [1, 2, 3]


def test_multivariate_models_obey_predictor_limit():
    specs = _json("phase5c_multivariate_specs.json")
    assert specs["maximum_predictors"] == MAX_MULTIVARIATE_PREDICTORS
    assert all(len(spec["fields"]) <= MAX_MULTIVARIATE_PREDICTORS
               for spec in specs["specifications"])


def test_performance_weights_use_past_data_only():
    weights = pd.read_csv(OUT / "phase5c_combination_weights.csv")
    assert weights.uses_only_prior_outcomes.astype(bool).all()
    populated = weights.weight_training_last_quarter.notna()
    assert (weights.loc[populated, "weight_training_last_quarter"]
            < weights.loc[populated, "target_quarter"]).all()


def test_current_2026q3_gdp_is_never_assumed():
    quarterly = pd.read_parquet(ROOT / "data/master/gdp_quarterly.parquet")
    shadows = pd.read_csv(OUT / "phase5c_current_shadow_nowcasts.csv")
    assert CURRENT_TARGET not in set(quarterly.quarter.astype(str))
    assert shadows.production_eligible.sum() == 1
    assert shadows.loc[~shadows.production_eligible, "notes"].str.contains(
        "actual unknown", case=False, na=False).all()


def test_phase5c_cannot_modify_production_outputs():
    manifest = _json("phase5c_run_manifest.json")
    assert manifest["production_artifacts_modified"] is False
    assert all(not path.startswith("results/production/") for path in manifest["outputs"])


def test_challenger_dashboard_clearly_marks_shadow_forecasts():
    page = (ROOT / "dashboard/phase5c_challenger_dashboard.html").read_text(encoding="utf-8")
    assert "SHADOW ONLY" in page
    assert "NOT THE OFFICIAL NOWCAST" in page
    assert "2026Q3 actual GDP is unknown" in page


def test_leaderboard_metrics_reproduce_from_predictions():
    leaderboard = pd.read_csv(OUT / "phase5c_challenger_leaderboard.csv")
    best = leaderboard.loc[leaderboard.family == "univariate_umidas"].iloc[0]
    predictions = pd.read_csv(OUT / "phase5c_univariate_predictions.csv")
    candidate = predictions.loc[
        (predictions.model == best.model)
        & (predictions.lag_mode == "standard")
        & (predictions.evidence_class == "DEVELOPMENT_PSEUDO_OOS")
    ].dropna(subset=["prediction"])
    reproduced = float(np.sqrt(np.mean(candidate.error.to_numpy(float) ** 2)))
    assert np.isclose(reproduced, best.pooled_RMSE)


def test_conservative_lag_uses_frozen_rule():
    assert effective_release_day(0, "conservative") == 15
    assert effective_release_day(24, "conservative") == 39
    protocol = _json("phase5c_challenger_protocol.json")
    assert "plus 15 days" in protocol["rules"]["release_lag_policy"]["conservative"]
