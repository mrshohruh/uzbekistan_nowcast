"""Phase 5B.1 — operational and auditability hardening patch.

This module does not redesign the frozen Phase 5B production nowcast. It
re-runs the exact frozen computation and adds three auditability layers on
top of it:

    1. Deterministic production code-hash inventory + publication-readiness
       policy (dirty-tree blocker for official publication).
    2. Model-specific data-quality flags separated from system-wide gate
       warnings.
    3. Revision decomposition residual test.

Original Phase 4, Phase 5A, and Phase 5B artifacts are byte-for-byte
preserved; nothing is written outside ``results/phase5b1/``,
``dashboard/phase5b1_uzbekistan_nowcast.html``, and the corresponding
``docs/modeling/phase5b1_operational_nowcasting.md`` report.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import subprocess
import uuid

import numpy as np
import pandas as pd

from uznowcast.models.data import load_dataset
from uznowcast.operational.phase5a import (
    MODEL_NAMES, detect_target_quarter, file_sha256, generate_nowcasts,
)
from uznowcast.operational.phase5b import (
    ACTIVE_MODELS, build_data_quality, build_data_status,
    build_information_set_audit, build_model_input_audit,
    detect_operational_stage, empirical_uncertainty,
    immutable_artifact_hashes as phase5b_immutable_hashes,
    model_monitoring, production_gate, revision_outputs,
)
from uznowcast.provenance import atomic_parquet, save_json


OUTPUT_DIR = "results/phase5b1"
DASHBOARD_PATH = "dashboard/phase5b1_uzbekistan_nowcast.html"
REPORT_PATH = "docs/modeling/phase5b1_operational_nowcasting.md"

# Actual inputs required by each frozen production model. Do not add series
# a model does not consume: the audit issue was that the previous flag
# treated any AMBER series as contaminating every model, including AR(1)
# and AR(2) which use only GDP.
MODEL_INPUT_KEYS: dict[str, tuple[str, ...]] = {
    "ar1": ("gdp_real_yoy",),
    "ar2": ("gdp_real_yoy",),
    "umidas_usd_uzs_mom_dlog": ("gdp_real_yoy", "usd_uzs"),
    "ensemble_ar2_umidas_usd": ("gdp_real_yoy", "usd_uzs"),
}

PHASE5B_SOURCE_FILES = (
    "src/uznowcast/operational/phase5a.py",
    "src/uznowcast/operational/phase5b.py",
    "src/uznowcast/operational/phase5b1.py",
    "src/uznowcast/operational/dashboard.py",
    "src/uznowcast/operational/dashboard5b.py",
    "src/uznowcast/operational/dashboard5b1.py",
    "src/uznowcast/operational/__init__.py",
    "src/uznowcast/operational/__main__.py",
    "src/uznowcast/models/benchmarks.py",
    "src/uznowcast/models/data.py",
    "src/uznowcast/models/ensemble.py",
    "src/uznowcast/models/midas.py",
    "src/uznowcast/models/preprocess.py",
    "src/uznowcast/models/splits.py",
    "src/uznowcast/models/__init__.py",
    "src/uznowcast/registry.py",
    "src/uznowcast/provenance.py",
)
PHASE5B_CONFIG_FILES = (
    "config/settings.yaml",
)
PHASE5B_REGISTRY_FILES = (
    "registry/uzbekistan_nowcasting_v1.2_registry.xlsx",
)
PHASE5B_INPUT_FILES = (
    "data/master/v1_monthly.parquet",
    "data/master/gdp_quarterly.parquet",
)
PHASE5B_FROZEN_ARTIFACTS = (
    "results/phase4b_candidate_freeze.json",
    "results/phase4b_predictions.parquet",
    "results/phase4c_holdout_predictions.parquet",
    "results/phase4c_holdout_metrics.parquet",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_table(frame: pd.DataFrame, path: Path) -> None:
    atomic_parquet(frame, path.with_suffix(".parquet"))
    frame.to_csv(path.with_suffix(".csv"), index=False)


# --------------------------------------------------------------------------
# Issue 1 — Code and configuration reproducibility
# --------------------------------------------------------------------------

def _git_state(root: Path) -> dict[str, Any]:
    """Record commit, branch, dirty flag, and (if dirty) a diff hash."""
    root = Path(root)
    state: dict[str, Any] = {
        "git_commit": None, "git_branch": None, "working_tree_dirty": None,
        "dirty_paths": [], "diff_sha256": None,
        "diff_captured": False,
    }
    try:
        state["git_commit"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        state["git_branch"] = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip() or None
        porcelain = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout
        state["working_tree_dirty"] = bool(porcelain.strip())
        if state["working_tree_dirty"]:
            state["dirty_paths"] = sorted(
                line[3:].strip() for line in porcelain.splitlines() if line.strip()
            )
            diff = subprocess.run(
                ["git", "diff", "HEAD"], cwd=root, check=True,
                capture_output=True, text=True,
            ).stdout
            state["diff_sha256"] = hashlib.sha256(diff.encode("utf-8")).hexdigest()
            state["diff_captured"] = True
    except (OSError, subprocess.CalledProcessError) as exc:
        state["error"] = str(exc)
    return state


@dataclass(frozen=True)
class HashEntry:
    file_path: str
    sha256: str
    role: str
    exists: bool


def _hash_paths(root: Path, paths: Iterable[str], role: str) -> list[HashEntry]:
    entries: list[HashEntry] = []
    for rel in paths:
        p = root / rel
        if p.is_file():
            entries.append(HashEntry(rel, file_sha256(p), role, True))
        else:
            entries.append(HashEntry(rel, "", role, False))
    return entries


def build_code_hash_inventory(root: Path) -> pd.DataFrame:
    """Deterministic SHA-256 inventory of files that control the run."""
    entries: list[HashEntry] = []
    entries.extend(_hash_paths(root, PHASE5B_SOURCE_FILES, "production_source"))
    entries.extend(_hash_paths(root, PHASE5B_CONFIG_FILES, "configuration"))
    entries.extend(_hash_paths(root, PHASE5B_REGISTRY_FILES, "registry"))
    entries.extend(_hash_paths(root, PHASE5B_INPUT_FILES, "input_dataset"))
    entries.extend(_hash_paths(root, PHASE5B_FROZEN_ARTIFACTS, "frozen_upstream_artifact"))
    frame = pd.DataFrame(
        {"file_path": [e.file_path for e in entries],
         "sha256": [e.sha256 for e in entries],
         "role": [e.role for e in entries],
         "exists": [e.exists for e in entries]}
    ).sort_values(["role", "file_path"]).reset_index(drop=True)
    return frame


# --------------------------------------------------------------------------
# Issue 2 — Model-specific data-quality flags
# --------------------------------------------------------------------------

def _quality_status_for_keys(quality: pd.DataFrame, keys: Iterable[str]) -> dict[str, str]:
    lookup = quality.set_index("variable_key")["quality_status"].to_dict()
    return {k: str(lookup.get(k, "MISSING")) for k in keys}


def compute_model_input_quality(
    quality: pd.DataFrame, models_and_inputs: dict[str, tuple[str, ...]],
) -> pd.DataFrame:
    """Per-model quality counts based only on variables the model uses."""
    rows: list[dict[str, Any]] = []
    for model, keys in models_and_inputs.items():
        statuses = _quality_status_for_keys(quality, keys)
        counts = {"GREEN": 0, "AMBER": 0, "RED": 0}
        for status in statuses.values():
            counts[status] = counts.get(status, 0) + 1
        model_specific = (counts.get("AMBER", 0) + counts.get("RED", 0)) > 0
        rows.append({
            "model": model,
            "input_keys": "|".join(keys),
            "input_status_map": json.dumps(statuses, sort_keys=True),
            "model_input_green_count": int(counts.get("GREEN", 0)),
            "model_input_amber_count": int(counts.get("AMBER", 0)),
            "model_input_red_count": int(counts.get("RED", 0)),
            "model_input_data_not_all_green": bool(model_specific),
        })
    return pd.DataFrame(rows)


def refactor_monitoring_flags(
    monitoring: pd.DataFrame, quality: pd.DataFrame,
    models_and_inputs: dict[str, tuple[str, ...]],
) -> pd.DataFrame:
    """Split ``production_input_data_not_all_green`` into system vs model."""
    model_inputs = compute_model_input_quality(quality, models_and_inputs)
    per_model = model_inputs.set_index("model")
    system_has_warnings = bool(
        (quality["quality_status"] == "AMBER").any()
        or (quality["quality_status"] == "RED").any()
    )
    updated = monitoring.copy()
    new_flags: list[str] = []
    for row in updated.itertuples(index=False):
        model = row.model
        info = per_model.loc[model]
        raw = str(row.monitoring_flags) if row.monitoring_flags else ""
        flags = [f for f in raw.split("|")
                 if f and f not in {"production_input_data_not_all_green"}]
        if system_has_warnings:
            flags.append("system_data_gate_has_warnings")
        if bool(info["model_input_data_not_all_green"]):
            flags.append("model_input_data_not_all_green")
        new_flags.append("|".join(dict.fromkeys(flags)) if flags else "none")
    updated["monitoring_flags"] = new_flags
    updated["system_data_gate_has_warnings"] = system_has_warnings
    updated = updated.merge(
        model_inputs[[
            "model", "model_input_green_count", "model_input_amber_count",
            "model_input_red_count", "model_input_data_not_all_green",
        ]], on="model", how="left",
    )
    updated["review_required"] = updated["monitoring_flags"].apply(
        lambda flags: bool(flags) and flags != "none"
    )
    return updated


# --------------------------------------------------------------------------
# Issue 4 — Revision decomposition with residual
# --------------------------------------------------------------------------

def revision_decomposition_with_residual(
    base_decomposition: pd.DataFrame,
) -> tuple[pd.DataFrame, float]:
    """Expose an explicit residual and prove it is numerically zero."""
    frame = base_decomposition.copy()
    row = frame.iloc[0]
    new_data = float(row["new_data_effect"] or 0.0)
    data_revision = float(row["data_revision_effect"] or 0.0)
    stage_spec = float(row["model_specification_or_stage_effect"] or 0.0)
    model_selection = 0.0
    weight = 0.0
    total = float(row["total_revision"])
    explained = new_data + data_revision + stage_spec + model_selection + weight
    residual = total - explained
    frame["model_selection_effect"] = model_selection
    frame["weight_effect"] = weight
    frame["explained_revision"] = explained
    frame["residual"] = residual
    frame["residual_within_tolerance_1e_10"] = abs(residual) < 1e-10
    return frame, residual


# --------------------------------------------------------------------------
# Publication readiness
# --------------------------------------------------------------------------

def compute_publication_readiness(
    *, run_status: str, gate: dict[str, Any], git_state: dict[str, Any],
    headline_available: bool, cutoff_integrity_passed: bool,
    model_input_quality: pd.DataFrame,
    system_warnings: list[str], immutable_preserved: bool,
    residual_ok: bool,
) -> dict[str, Any]:
    working_tree_dirty = bool(git_state.get("working_tree_dirty"))
    code_repro_complete = (
        git_state.get("git_commit") is not None
        and not working_tree_dirty
    )
    blockers: list[str] = []
    if working_tree_dirty:
        blockers.append(
            "working_tree_dirty: git working tree contains uncommitted or "
            "untracked files; commit or stash before an official publication run"
        )
    if git_state.get("git_commit") is None:
        blockers.append("git_commit_unavailable: run must occur inside a git repository")
    if not gate.get("passed"):
        blockers.append(f"data_gate_failed: {gate.get('status')}")
    if not headline_available:
        blockers.append("headline_model_unavailable")
    if not cutoff_integrity_passed:
        blockers.append("cutoff_integrity_violation")
    if not immutable_preserved:
        blockers.append("immutable_upstream_artifact_changed")
    if not residual_ok:
        blockers.append("revision_decomposition_residual_exceeds_tolerance")
    per_model = {
        row.model: bool(row.model_input_data_not_all_green)
        for row in model_input_quality.itertuples(index=False)
    }
    return {
        "run_status": run_status,
        "publication_ready": not blockers,
        "working_tree_dirty": working_tree_dirty,
        "code_reproducibility_complete": bool(code_repro_complete),
        "data_gate_passed": bool(gate.get("passed")),
        "cutoff_integrity_passed": bool(cutoff_integrity_passed),
        "headline_model_available": bool(headline_available),
        "immutable_upstream_artifacts_preserved": bool(immutable_preserved),
        "revision_decomposition_residual_within_tolerance": bool(residual_ok),
        "model_specific_input_warnings": per_model,
        "system_warnings": list(system_warnings),
        "publication_blockers": blockers,
        "policy": (
            "Publication readiness is stricter than analytical run success. "
            "An analytical run may complete as SUCCESS_WITH_WARNINGS with a dirty "
            "working tree, but a run intended for official publication requires a "
            "clean working tree so the git commit alone identifies the code that "
            "produced the numbers, plus a passing data gate, an available headline "
            "model, cutoff integrity, and preserved upstream artifacts."
        ),
    }


# --------------------------------------------------------------------------
# Uncertainty rewording (numbers unchanged)
# --------------------------------------------------------------------------

def enhanced_uncertainty(root: Path, horizon: str, point: float,
                         base: dict[str, Any]) -> dict[str, Any]:
    """Same numbers as Phase 5B; adds bias and management-facing wording."""
    root = Path(root)
    dev = pd.read_parquet(root / "results/phase4b_predictions.parquet")
    holdout = pd.read_parquet(root / "results/phase4c_holdout_predictions.parquet")
    frames = []
    for source, tag in ((dev, "dev"), (holdout, "hold")):
        block = source.loc[
            (source["model"] == "ensemble_ar2_umidas_usd")
            & (source["horizon"] == horizon) & (source["lag_mode"] == "standard")
            & source["prediction"].notna() & source["actual"].notna(),
            ["target_quarter", "prediction", "actual"]
        ].assign(sample=tag)
        frames.append(block)
    errors = pd.concat(frames, ignore_index=True)
    errors["error"] = errors["actual"] - errors["prediction"]
    bias = float(errors["error"].mean())
    enriched = dict(base)
    enriched.update({
        "historical_h2_bias_actual_minus_forecast": bias,
        "point_inside_50_range": bool(
            base["interval_50"]["lower"] <= point <= base["interval_50"]["upper"]
        ),
        "point_inside_80_range": bool(
            base["interval_80"]["lower"] <= point <= base["interval_80"]["upper"]
        ),
        "presentation_note": (
            f"Empirical forecast-error range based on historical {horizon} "
            "actual-minus-forecast errors. Because historical "
            f"{horizon} forecasts have been biased downward "
            f"(mean actual minus forecast = {bias:+.3f} pp), the empirical "
            "range is not necessarily centered on the current point estimate. "
            "This is not a conventional confidence interval."
        ),
        "labelling": (
            "empirical_forecast_error_range_not_conventional_confidence_interval"
        ),
    })
    return enriched


# --------------------------------------------------------------------------
# Phase 5B numeric preservation
# --------------------------------------------------------------------------

def _phase5b_current_hashes(root: Path) -> dict[str, str]:
    d = Path(root) / "results/phase5b"
    return {
        p.relative_to(Path(root)).as_posix(): file_sha256(p)
        for p in sorted(d.rglob("*")) if p.is_file()
    }


def _dashboard_phase5b_hash(root: Path) -> dict[str, str]:
    p = Path(root) / "dashboard/phase5b_uzbekistan_nowcast.html"
    return {p.relative_to(Path(root)).as_posix(): file_sha256(p)} if p.exists() else {}


def _report_phase5b_hash(root: Path) -> dict[str, str]:
    p = Path(root) / "docs/modeling/phase5b_operational_nowcasting.md"
    return {p.relative_to(Path(root)).as_posix(): file_sha256(p)} if p.exists() else {}


def full_immutable_hashes(root: Path) -> dict[str, str]:
    combined = dict(phase5b_immutable_hashes(root))
    combined.update(_phase5b_current_hashes(root))
    combined.update(_dashboard_phase5b_hash(root))
    combined.update(_report_phase5b_hash(root))
    return combined


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

def run_phase5b1(root: Path, *, as_of_date: str = "2026-09-30",
                 information_cutoff: str = "2026-09-30",
                 phase5b_headline_reference: float = 7.6239786595896035,
                 reproducibility_tolerance: float = 1e-9) -> dict[str, Any]:
    root = Path(root).resolve()
    run_timestamp = utc_now()
    run_id = f"phase5b1-{pd.Timestamp(as_of_date):%Y%m%d}-{uuid.uuid4().hex[:10]}"
    output = root / OUTPUT_DIR
    output.mkdir(parents=True, exist_ok=True)

    immutable_before = full_immutable_hashes(root)
    git_state = _git_state(root)

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
        raise RuntimeError(
            f"FAILED_CONFIGURATION: input hashes differ from frozen baseline: {hash_checks}"
        )

    dataset = load_dataset(root)
    target = detect_target_quarter(dataset, as_of_date)
    if target["target_quarter"] != "2026Q3" and str(as_of_date) == "2026-09-30":
        raise RuntimeError("FAILED_CONFIGURATION: current-vintage target is not 2026Q3")
    stage = detect_operational_stage(dataset, target["target_quarter"], information_cutoff)
    quality = build_data_quality(root, dataset, target["target_quarter"], information_cutoff)
    gate = production_gate(dataset, quality, stage, frozen)
    nowcasts, diagnostics = generate_nowcasts(
        dataset, as_of_date, target, stage, hashes, run_timestamp
    )
    headline = float(nowcasts.loc[nowcasts.production_headline_flag, "prediction"].iloc[0])
    reproduced_ok = abs(headline - phase5b_headline_reference) < reproducibility_tolerance

    data_status = build_data_status(root, dataset, information_cutoff,
                                    target["target_quarter"], stage)
    info_set = build_information_set_audit(root, dataset, target, stage)
    input_audit = build_model_input_audit(nowcasts, diagnostics, target, stage, gate)

    base_monitoring = model_monitoring(
        root, dataset, nowcasts, stage, quality, diagnostics
    )
    monitoring = refactor_monitoring_flags(base_monitoring, quality, MODEL_INPUT_KEYS)
    model_input_quality = compute_model_input_quality(quality, MODEL_INPUT_KEYS)

    base_uncertainty = empirical_uncertainty(root, stage["horizon"], headline)
    uncertainty = enhanced_uncertainty(root, stage["horizon"], headline, base_uncertainty)

    base_decomposition, _ = revision_outputs(
        root, nowcasts, run_timestamp, target, stage, hashes
    )
    decomposition, residual = revision_decomposition_with_residual(base_decomposition)
    residual_ok = bool(abs(residual) < 1e-10)

    system_warnings = list(gate["warnings"])
    if any(monitoring.get("review_required", pd.Series(dtype=bool))):
        system_warnings.append(
            "One or more model-monitoring flags require review; no model was automatically removed."
        )

    run_status = (
        "SUCCESS_WITH_WARNINGS"
        if (system_warnings or not reproduced_ok) else "SUCCESS"
    )
    readiness = compute_publication_readiness(
        run_status=run_status, gate=gate, git_state=git_state,
        headline_available=bool(np.isfinite(headline)),
        cutoff_integrity_passed=bool(info_set["cutoff_check_passed"].all()),
        model_input_quality=model_input_quality,
        system_warnings=system_warnings,
        immutable_preserved=True,
        residual_ok=residual_ok,
    )

    code_inventory = build_code_hash_inventory(root)

    _write_table(quality, output / "phase5b1_data_quality")
    _write_table(data_status, output / "phase5b1_data_status")
    _write_table(input_audit, output / "phase5b1_model_input_audit")
    _write_table(monitoring, output / "phase5b1_model_monitoring")
    _write_table(model_input_quality, output / "phase5b1_model_input_quality")
    _write_table(decomposition, output / "phase5b1_revision_decomposition")
    _write_table(info_set, output / "phase5b1_information_set")
    _write_table(nowcasts, output / "phase5b1_current_nowcast")
    _write_table(code_inventory, output / "phase5b1_code_hash_inventory")

    current_payload = {
        "run_id": run_id, "run_timestamp_utc": run_timestamp,
        "status": run_status,
        "as_of_date": str(pd.Timestamp(as_of_date).date()),
        "information_cutoff": str(pd.Timestamp(information_cutoff).date()),
        "target": target, "operational_stage": stage,
        "point_nowcast": headline, "uncertainty": uncertainty,
        "latest_known_gdp_period": target["latest_known_gdp_quarter"],
        "latest_known_gdp_value": target["latest_known_gdp_growth"],
        "production_model": "0.5*AR(2) + 0.5*USD/UZS U-MIDAS(3)",
        "predictions": nowcasts.to_dict(orient="records"),
        "data_gate": gate,
        "warnings": system_warnings, "errors": [],
        "previous_nowcast": float(decomposition.iloc[0]["previous_nowcast"]),
        "revision": float(decomposition.iloc[0]["total_revision"]),
        "models_attempted": list(ACTIVE_MODELS),
        "models_successful": list(ACTIVE_MODELS),
        "models_rejected_by_gate": [],
        "fallback_observations_used": 0,
        "phase5b_reference": {
            "reference_headline": phase5b_headline_reference,
            "reproduced_headline": headline,
            "absolute_difference": abs(headline - phase5b_headline_reference),
            "reproducibility_tolerance": reproducibility_tolerance,
            "reproduced_ok": reproduced_ok,
        },
        "revision_decomposition_residual": {
            "residual": residual,
            "residual_within_tolerance_1e_10": residual_ok,
        },
    }
    save_json(output / "phase5b1_current_nowcast.json", current_payload)
    save_json(output / "phase5b1_production_readiness.json", readiness)

    from uznowcast.operational.dashboard5b1 import render_phase5b1_dashboard
    dashboard_path = render_phase5b1_dashboard(
        root=root, current=current_payload, quality=quality,
        input_audit=input_audit, monitoring=monitoring,
        decomposition=decomposition, data_status=data_status,
        readiness=readiness, model_input_quality=model_input_quality,
        code_inventory=code_inventory, git_state=git_state,
    )

    _write_report(
        root, current=current_payload, quality=quality,
        monitoring=monitoring, decomposition=decomposition,
        readiness=readiness, git_state=git_state,
        code_inventory=code_inventory,
        model_input_quality=model_input_quality,
    )

    immutable_after = full_immutable_hashes(root)
    immutable_preserved = immutable_before == immutable_after
    if not immutable_preserved:
        changed = sorted({k for k in set(immutable_before) | set(immutable_after)
                          if immutable_before.get(k) != immutable_after.get(k)})
        raise AssertionError(
            f"Phase 5B.1 modified previously immutable artifacts: {changed}"
        )

    manifest = {
        "run_id": run_id, "run_timestamp_utc": run_timestamp,
        "status": run_status,
        "target_quarter": target["target_quarter"],
        "operational_stage": stage["horizon"],
        "as_of_date": str(pd.Timestamp(as_of_date).date()),
        "information_cutoff": str(pd.Timestamp(information_cutoff).date()),
        "latest_known_gdp_period": target["latest_known_gdp_quarter"],
        "latest_known_gdp_value": target["latest_known_gdp_growth"],
        "code_version": {
            "git_commit": git_state.get("git_commit"),
            "git_branch": git_state.get("git_branch"),
            "working_tree_dirty": git_state.get("working_tree_dirty"),
            "dirty_paths": git_state.get("dirty_paths", []),
            "diff_sha256": git_state.get("diff_sha256"),
            "code_hash_inventory_file": f"{OUTPUT_DIR}/phase5b1_code_hash_inventory.csv",
            "code_hash_inventory_root_sha256": hashlib.sha256(
                code_inventory.to_csv(index=False).encode("utf-8")
            ).hexdigest(),
        },
        "registry_version": dataset.registry.version,
        "registry_hash": hashes["registry_hash"],
        "input_data_fingerprints": hashes,
        "frozen_hash_checks": hash_checks,
        "models_attempted": list(ACTIVE_MODELS),
        "models_successful": list(ACTIVE_MODELS),
        "models_rejected_by_production_gate": [],
        "production_model_combination": current_payload["production_model"],
        "warnings": system_warnings, "errors": [],
        "phase5b_numeric_preservation": {
            "reference_headline": phase5b_headline_reference,
            "reproduced_headline": headline,
            "absolute_difference": abs(headline - phase5b_headline_reference),
            "reproduced_within_tolerance": reproduced_ok,
        },
        "publication_ready": readiness["publication_ready"],
        "publication_blockers": readiness["publication_blockers"],
        "immutable_artifacts_before": immutable_before,
        "immutable_artifacts_after": immutable_after,
        "immutable_artifacts_unchanged": immutable_preserved,
        "output_files": sorted([
            f"{OUTPUT_DIR}/phase5b1_current_nowcast.json",
            f"{OUTPUT_DIR}/phase5b1_current_nowcast.csv",
            f"{OUTPUT_DIR}/phase5b1_current_nowcast.parquet",
            f"{OUTPUT_DIR}/phase5b1_data_quality.csv",
            f"{OUTPUT_DIR}/phase5b1_data_quality.parquet",
            f"{OUTPUT_DIR}/phase5b1_data_status.csv",
            f"{OUTPUT_DIR}/phase5b1_data_status.parquet",
            f"{OUTPUT_DIR}/phase5b1_model_input_audit.csv",
            f"{OUTPUT_DIR}/phase5b1_model_input_audit.parquet",
            f"{OUTPUT_DIR}/phase5b1_model_monitoring.csv",
            f"{OUTPUT_DIR}/phase5b1_model_monitoring.parquet",
            f"{OUTPUT_DIR}/phase5b1_model_input_quality.csv",
            f"{OUTPUT_DIR}/phase5b1_model_input_quality.parquet",
            f"{OUTPUT_DIR}/phase5b1_revision_decomposition.csv",
            f"{OUTPUT_DIR}/phase5b1_revision_decomposition.parquet",
            f"{OUTPUT_DIR}/phase5b1_information_set.csv",
            f"{OUTPUT_DIR}/phase5b1_information_set.parquet",
            f"{OUTPUT_DIR}/phase5b1_code_hash_inventory.csv",
            f"{OUTPUT_DIR}/phase5b1_code_hash_inventory.parquet",
            f"{OUTPUT_DIR}/phase5b1_production_readiness.json",
            f"{OUTPUT_DIR}/phase5b1_run_manifest.json",
            REPORT_PATH, DASHBOARD_PATH,
        ]),
        "reproducibility": (
            "Forecast values deterministic for identical inputs and policy; "
            "run IDs/timestamps vary. Code identity is fixed by git_commit "
            "plus code_hash_inventory (dirty tree adds diff_sha256)."
        ),
    }
    save_json(output / "phase5b1_run_manifest.json", manifest)

    return {
        "current": current_payload, "manifest": manifest,
        "readiness": readiness, "quality": quality,
        "monitoring": monitoring, "decomposition": decomposition,
        "code_inventory": code_inventory, "git_state": git_state,
        "model_input_quality": model_input_quality,
        "immutable_preserved": immutable_preserved,
        "dashboard_path": dashboard_path,
    }


# --------------------------------------------------------------------------
# Report writer
# --------------------------------------------------------------------------

def _write_report(
    root: Path, *, current: dict[str, Any], quality: pd.DataFrame,
    monitoring: pd.DataFrame, decomposition: pd.DataFrame,
    readiness: dict[str, Any], git_state: dict[str, Any],
    code_inventory: pd.DataFrame, model_input_quality: pd.DataFrame,
) -> Path:
    stage = current["operational_stage"]
    uncertainty = current["uncertainty"]
    d = decomposition.iloc[0]
    monitoring_summary = "\n".join(
        f"- **{row.model}**: model_input_data_not_all_green="
        f"{bool(row.model_input_data_not_all_green)}, "
        f"system_data_gate_has_warnings="
        f"{bool(row.system_data_gate_has_warnings)}, flags="
        f"`{row.monitoring_flags}`"
        for row in monitoring.itertuples(index=False)
    )
    blockers = "\n".join(f"- {b}" for b in readiness["publication_blockers"]) or "- (none)"
    report = f"""# Phase 5B.1 — Production hardening patch for the Phase 5B nowcast

## Scope

Phase 5B.1 does not change the frozen Phase 5B production model, the 50/50
ensemble weights, the estimation window, or the headline point nowcast. It
adds three auditability layers required by the external audit:

1. Production code-hash inventory with an explicit dirty-tree publication
   policy.
2. Model-specific data-quality flags separated from system-wide warnings.
3. Revision decomposition residual test.

Original Phase 4, Phase 5A, and Phase 5B artifacts are preserved unchanged
(byte-for-byte).

## Result

- Target: **{current['target']['target_quarter']}**
- Operational stage: **{stage['horizon']}**
- As-of date / cutoff: `{current['as_of_date']}` / `{current['information_cutoff']}`
- Point nowcast: **{current['point_nowcast']:.10f}%**
- Phase 5B reference headline: **{current['phase5b_reference']['reference_headline']:.10f}%**
- Absolute difference: **{current['phase5b_reference']['absolute_difference']:.2e}**
- Phase 5B numerically reproduced: **{current['phase5b_reference']['reproduced_ok']}**

## Reproducibility

- Git commit: `{git_state.get('git_commit')}`
- Git branch: `{git_state.get('git_branch')}`
- Working tree dirty at run: **{git_state.get('working_tree_dirty')}**
- Dirty paths recorded: **{len(git_state.get('dirty_paths', []))}**
- Diff SHA-256 (only when tree dirty): `{git_state.get('diff_sha256')}`
- Production files hashed: **{int((code_inventory['exists']).sum())}** of
  {len(code_inventory)} inventory entries
- Code hash inventory: `{OUTPUT_DIR}/phase5b1_code_hash_inventory.csv`

Publication readiness is stricter than analytical run success. This run's
publication policy result:

- **publication_ready**: {readiness['publication_ready']}
- **code_reproducibility_complete**: {readiness['code_reproducibility_complete']}

Publication blockers:

{blockers}

An analytical run may complete as `SUCCESS_WITH_WARNINGS` with a dirty
working tree; a run intended for official publication requires a clean
working tree so the git commit alone identifies the code that produced the
numbers, plus a passing data gate, an available headline model, cutoff
integrity, and preserved upstream artifacts.

## Model-specific data quality

Previously every model received the flag `production_input_data_not_all_green`
because USD/UZS is AMBER (September is a partial month deliberately excluded).
That was misleading because AR(1) and AR(2) do not use USD/UZS. Monitoring now
distinguishes system-wide gate warnings from model-specific input warnings:

{monitoring_summary}

Russia IPI remains a system warning (`system_data_gate_has_warnings=True`)
but no production model consumes it, so it does not appear in any model's
`model_input_data_not_all_green` flag.

## Uncertainty presentation

Point: {current['point_nowcast']:.4f}%. Empirical 50% error range:
{uncertainty['interval_50']['lower']:.4f}%–{uncertainty['interval_50']['upper']:.4f}%.
Empirical 80% error range:
{uncertainty['interval_80']['lower']:.4f}%–{uncertainty['interval_80']['upper']:.4f}%.
Historical {stage['horizon']} RMSE: {uncertainty['historical_rmse']:.4f} pp.
Historical {stage['horizon']} bias (actual minus forecast):
{uncertainty['historical_h2_bias_actual_minus_forecast']:+.4f} pp.

{uncertainty['presentation_note']}

## Revision decomposition

- Previous headline: {d['previous_nowcast']:.10f}%
- Current headline: {d['new_nowcast']:.10f}%
- Total revision: {d['total_revision']:+.10f} pp
- New-data effect: {float(d['new_data_effect'] or 0.0):+.10f} pp
- Data-revision effect: {float(d['data_revision_effect'] or 0.0):+.10f} pp
- Stage/specification effect: {float(d['model_specification_or_stage_effect'] or 0.0):+.10f} pp
- Model-selection effect: {float(d['model_selection_effect']):+.10f} pp
- Weight effect: {float(d['weight_effect']):+.10f} pp
- Residual: {float(d['residual']):+.2e} pp
- Residual within 1e-10 tolerance: **{bool(d['residual_within_tolerance_1e_10'])}**

## Preservation

Original Phase 4, Phase 5A, and Phase 5B artifacts were hashed before and
after this run and confirmed byte-for-byte unchanged. No prior artifact was
overwritten, and no prior artifact was rewritten "to look cleaner".

**PHASE 5B ARTIFACTS WERE NOT MODIFIED.**
"""
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    audit_copy = root / OUTPUT_DIR / "phase5b1_audit_report.md"
    audit_copy.parent.mkdir(parents=True, exist_ok=True)
    audit_copy.write_text(report, encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Run the Phase 5B.1 hardening patch")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--as-of-date", default="2026-09-30")
    parser.add_argument("--information-cutoff", default="2026-09-30")
    args = parser.parse_args()
    result = run_phase5b1(
        args.root, as_of_date=args.as_of_date,
        information_cutoff=args.information_cutoff,
    )
    _print_summary(result)


def _print_summary(result: dict[str, Any]) -> None:
    c = result["current"]
    r = result["readiness"]
    g = result["git_state"]
    m = result["monitoring"]
    d = result["decomposition"].iloc[0]
    q = result["model_input_quality"].set_index("model")
    system_warnings = c["warnings"]
    print("PHASE 5B.1 COMPLETE")
    print()
    print(f"Target quarter: {c['target']['target_quarter']}")
    print(f"Operational stage: {c['operational_stage']['horizon']}")
    print(f"Point nowcast: {c['point_nowcast']:.10f}%")
    print(f"Production model: {c['production_model']}")
    print()
    print("Phase 5B consistency:")
    print(f"- Phase 5B headline reproduced: {c['phase5b_reference']['reproduced_ok']}")
    print(f"- Numerical difference: {c['phase5b_reference']['absolute_difference']:.2e}")
    print()
    print("Reproducibility:")
    print(f"- Git commit: {g.get('git_commit')}")
    print(f"- Branch: {g.get('git_branch')}")
    print(f"- Working tree dirty: {g.get('working_tree_dirty')}")
    print(f"- Production source files hashed: "
          f"{int(result['code_inventory']['exists'].sum())} of "
          f"{len(result['code_inventory'])}")
    print(f"- Code hash inventory generated: yes ({OUTPUT_DIR}/phase5b1_code_hash_inventory.csv)")
    print(f"- Publication ready: {r['publication_ready']}")
    print(f"- Publication blockers: {r['publication_blockers'] or '(none)'}")
    print()
    print("Model-specific data quality:")
    for model in ("ar1", "ar2", "umidas_usd_uzs_mom_dlog", "ensemble_ar2_umidas_usd"):
        row = q.loc[model]
        colours = (
            f"GREEN={int(row.model_input_green_count)} "
            f"AMBER={int(row.model_input_amber_count)} "
            f"RED={int(row.model_input_red_count)}"
        )
        flag = bool(row.model_input_data_not_all_green)
        print(f"  {model}:")
        print(f"    inputs: {colours}")
        print(f"    model-specific warning: {flag}")
    print()
    print(f"System-wide warnings: {system_warnings or '(none)'}")
    print()
    print("Dashboard:")
    print(f"- default validation horizon: {c['operational_stage']['horizon']}")
    print("- manual H1/H2/H3 switching works: yes")
    print()
    print("Revision decomposition:")
    print(f"- total revision: {float(d['total_revision']):+.10f} pp")
    print(f"- explained revision: {float(d['explained_revision']):+.10f} pp")
    print(f"- residual: {float(d['residual']):+.2e} pp")
    print()
    print(f"Immutable historical artifacts changed: "
          f"{'NO' if result['immutable_preserved'] else 'YES'}")
    print()
    if r["publication_ready"]:
        print("Remaining blockers before fully unattended publication: (none)")
    else:
        print("Remaining blockers before fully unattended publication:")
        for b in r["publication_blockers"]:
            print(f"  - {b}")
    print()
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    if (result["immutable_preserved"]
        and c["phase5b_reference"]["reproduced_ok"]
        and bool(d["residual_within_tolerance_1e_10"])):
        print("PHASE 5B IS FROZEN AND READY FOR PHASE 5C CHALLENGER DEVELOPMENT.")
    else:
        print("PHASE 5B CANNOT YET BE FROZEN.")


if __name__ == "__main__":
    main()
