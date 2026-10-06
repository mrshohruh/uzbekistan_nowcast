"""Phase 5B.2 — canonical current-production layout and hash preservation."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PROD_DIR = ROOT / "results" / "production"
DASH_DIR = ROOT / "dashboard" / "current"
FROZEN_5B1_DIR = ROOT / "results" / "phase5b1"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


CANONICAL_MIRROR = {
    "current_nowcast.json": "phase5b1_current_nowcast.json",
    "current_nowcast.csv": "phase5b1_current_nowcast.csv",
    "current_nowcast.parquet": "phase5b1_current_nowcast.parquet",
    "run_manifest.json": "phase5b1_run_manifest.json",
    "production_readiness.json": "phase5b1_production_readiness.json",
    "data_quality.csv": "phase5b1_data_quality.csv",
    "data_status.csv": "phase5b1_data_status.csv",
    "model_monitoring.csv": "phase5b1_model_monitoring.csv",
    "revision_decomposition.csv": "phase5b1_revision_decomposition.csv",
    "model_input_quality.csv": "phase5b1_model_input_quality.csv",
    "code_hash_inventory.csv": "phase5b1_code_hash_inventory.csv",
    "audit_report.md": "phase5b1_audit_report.md",
}


@pytest.mark.parametrize("canonical_name,source_name",
                         list(CANONICAL_MIRROR.items()))
def test_canonical_current_files_are_byte_identical_mirrors_of_phase5b1(
    canonical_name: str, source_name: str
):
    canonical = PROD_DIR / canonical_name
    source = FROZEN_5B1_DIR / source_name
    assert canonical.exists(), f"missing canonical mirror: {canonical}"
    assert source.exists(), f"missing frozen source: {source}"
    assert _sha256(canonical) == _sha256(source)


def test_canonical_dashboard_mirrors_phase5b1_dashboard():
    canonical = DASH_DIR / "uzbekistan_nowcast.html"
    source = ROOT / "dashboard" / "phase5b1_uzbekistan_nowcast.html"
    assert canonical.exists()
    assert source.exists()
    pointer=ROOT/'results/operations/current_production.json'
    if pointer.exists():
        active=json.loads(pointer.read_text(encoding='utf8'))
        policy=json.loads((ROOT/active['policy']).read_text(encoding='utf8'))
        assert policy['model']=='COMBO_50_50' and policy['status']=='PHASE6E_PROMOTED'
        assert _sha256(canonical)==_sha256(ROOT/active['dashboard'])
        # The original Phase 5B.1 default remains byte-identical and reproducible.
        assert _sha256(ROOT/'results/phase6e/legacy_current_dashboard.html')==_sha256(source)
    else:
        assert _sha256(canonical) == _sha256(source)


def test_canonical_headline_matches_frozen_baseline():
    data = json.loads(
        (PROD_DIR / "current_nowcast.json").read_text(encoding="utf-8")
    )
    assert data["point_nowcast"] == 7.6239786595896035
    assert data["target"]["target_quarter"] == "2026Q3"
    assert data["operational_stage"]["operational_stage"] == "H2"
    assert data["production_model"] == "0.5*AR(2) + 0.5*USD/UZS U-MIDAS(3)"


def test_project_state_document_exists_and_matches_frozen_headline():
    text = (ROOT / "PROJECT_STATE.md").read_text(encoding="utf-8")
    assert "7.6239786595896035" in text
    assert "2026Q3" in text
    assert "H2" in text
    assert "Phase 5B.1" in text


def test_protected_artifact_hash_comparison_is_all_match():
    csv_path = ROOT / "results" / "phase5b2" / \
        "protected_artifact_hash_comparison.csv"
    assert csv_path.exists()
    with csv_path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "expected at least one protected artifact"
    for row in rows:
        assert row["hash_match"] == "TRUE", (
            f"hash mismatch on {row['artifact']}: "
            f"before={row['sha256_before']} after={row['sha256_after']}"
        )
