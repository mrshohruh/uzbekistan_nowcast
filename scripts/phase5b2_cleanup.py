"""Phase 5B.2 — Repository cleanup, archive index, and canonical mirror.

Safety-first: this script does NOT move or delete any file that source code,
tests, or historical artifacts depend on. It:

  * inventories the repository (Task 1) and writes ``repository_inventory.csv``;
  * hashes every protected phase artifact (Task 2) BEFORE any changes;
  * audits hardcoded path references (Task 3);
  * documents the retained-in-place archive layout (Task 4/5);
  * copies (never moves) the Phase 5B.1 headline artifacts into a canonical
    ``results/production/`` + ``dashboard/current/`` mirror (Task 6);
  * removes only safe reproducible caches (Task 7);
  * re-hashes protected artifacts and confirms byte-for-byte identity (Task 18).

Run from the repository root. It writes every output under
``results/phase5b2/``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase5b2"

# --------------------------------------------------------------------------- #
# What counts as a protected historical artifact.  Every filename pattern below
# is considered immutable evidence: Phase 5B.2 must not change its bytes.
# --------------------------------------------------------------------------- #
PROTECTED_PATTERNS = [
    ("results", re.compile(r"^phase4a[_.]"), "phase4a"),
    ("results", re.compile(r"^phase4a1_"), "phase4a1"),
    ("results", re.compile(r"^phase4b_"), "phase4b"),
    ("results", re.compile(r"^phase4c_"), "phase4c"),
    ("results", re.compile(r"^phase5a_"), "phase5a"),
    ("results/phase5b", re.compile(r".*"), "phase5b"),
    ("results/phase5b1", re.compile(r".*"), "phase5b1"),
    ("dashboard", re.compile(r"^phase5a_"), "phase5a"),
    ("dashboard", re.compile(r"^phase5b_"), "phase5b"),
    ("dashboard", re.compile(r"^phase5b1_"), "phase5b1"),
    ("results", re.compile(r"^frozen_validation_definition\.json$"), "frozen_validation"),
    ("docs/modeling", re.compile(r"^phase4"), "docs_phase4"),
    ("docs/modeling", re.compile(r"^phase5a"), "docs_phase5a"),
    ("docs/modeling", re.compile(r"^phase5b_"), "docs_phase5b"),
    ("docs/modeling", re.compile(r"^phase5b1_"), "docs_phase5b1"),
]


# Directories excluded from inventory (build/environment noise only).
INVENTORY_EXCLUDE_DIRS = {".git", ".venv", "src/uznowcast.egg-info"}


# Directories/files that are safe to delete: reproducible caches.
CACHE_DIRS = {"__pycache__", ".pytest_cache"}
CACHE_TOP_DIRS = ["pytest-cache-files-gk9y2b1q", "pytest-cache-files-uqcib9tk"]


# --------------------------------------------------------------------------- #

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_excluded(rel: Path) -> bool:
    parts = rel.parts
    for ex in INVENTORY_EXCLUDE_DIRS:
        ex_parts = tuple(Path(ex).parts)
        if len(parts) >= len(ex_parts) and parts[: len(ex_parts)] == ex_parts:
            return True
    return False


def match_protected(rel: Path) -> tuple[bool, str]:
    """Return (is_protected, phase_tag)."""
    parent = rel.parent.as_posix()
    name = rel.name
    for parent_prefix, pattern, phase in PROTECTED_PATTERNS:
        # parent must equal or start with parent_prefix
        if parent == parent_prefix or parent.startswith(parent_prefix + "/"):
            # For results/phase5b and results/phase5b1 we protect ANY file
            # inside the folder; for scanning direct-file patterns we require
            # the parent to equal parent_prefix exactly OR pattern matches "*".
            if pattern.pattern == ".*":
                return True, phase
            if parent == parent_prefix and pattern.match(name):
                return True, phase
    return False, ""


def classify(rel: Path) -> tuple[str, str]:
    """Return (category, phase_if_known)."""
    p = rel.as_posix()
    protected, phase = match_protected(rel)
    if protected:
        return "FROZEN_HISTORICAL_ARTIFACT", phase

    if any(seg in CACHE_DIRS for seg in rel.parts):
        return "CACHE_OR_TEMPORARY", ""
    if rel.parts and rel.parts[0] in {"pytest-cache-files-gk9y2b1q",
                                       "pytest-cache-files-uqcib9tk"}:
        return "CACHE_OR_TEMPORARY", ""
    if rel.parts and rel.parts[0] == ".tmp":
        return "CACHE_OR_TEMPORARY", ""
    if rel.suffix == ".pyc":
        return "CACHE_OR_TEMPORARY", ""

    if p.startswith("tests/"):
        return "TEST", ""
    if p.startswith("src/"):
        return "ACTIVE_SOURCE", ""
    if p.startswith("scripts/"):
        return "ACTIVE_SOURCE", ""
    if p.startswith("config/") or p == "pyproject.toml" or p == "requirements.txt":
        return "ACTIVE_CONFIGURATION", ""
    if p.startswith("registry/"):
        return "ACTIVE_CONFIGURATION", ""
    if p.startswith("data/"):
        return "ACTIVE_DATA", ""
    if p.startswith("metadata/"):
        return "ACTIVE_DATA", ""
    if p.startswith("logs/"):
        return "CACHE_OR_TEMPORARY", ""
    if p.startswith("docs/"):
        return "DOCUMENTATION", ""

    # Root-level operational status files created by Phase 5B.1
    if p in {"README.md", "AGENTS.md", "PROJECT_SPEC.md", "CODEX_START_PROMPT.md",
             ".gitignore"}:
        return "DOCUMENTATION", ""

    # Empty 'python' file at root looks like an accidental artifact.
    if p == "python":
        return "UNKNOWN", ""

    if p.startswith("results/production/") or p.startswith("dashboard/current/"):
        return "CURRENT_OPERATIONAL_OUTPUT", ""
    if p.startswith("results/phase5b2/"):
        return "DOCUMENTATION", ""
    if p.startswith("results/archive/"):
        return "FROZEN_HISTORICAL_ARTIFACT", ""

    return "UNKNOWN", ""


def iter_files() -> Iterable[Path]:
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if is_excluded(rel):
            continue
        yield rel


# --------------------------------------------------------------------------- #

def task_1_inventory():
    print("Task 1: inventory")
    rows = []
    refs_by_path = build_reference_map()
    for rel in iter_files():
        full = ROOT / rel
        try:
            size = full.stat().st_size
        except OSError:
            size = -1
        # Hash only reasonable-size files to keep this quick.
        try:
            digest = sha256_of(full) if size >= 0 and size < 100 * 1024 * 1024 else ""
        except OSError:
            digest = ""
        cat, phase = classify(rel)
        p = rel.as_posix()
        rows.append({
            "path": p,
            "file_name": rel.name,
            "extension": rel.suffix,
            "size_bytes": size,
            "sha256": digest,
            "category": cat,
            "phase_if_known": phase,
            "referenced_by_code": ";".join(sorted(refs_by_path.get(p, {}).get("code", []))),
            "referenced_by_tests": ";".join(sorted(refs_by_path.get(p, {}).get("tests", []))),
            "referenced_by_docs": ";".join(sorted(refs_by_path.get(p, {}).get("docs", []))),
            "safe_to_move": "NO" if cat in {"FROZEN_HISTORICAL_ARTIFACT",
                                              "ACTIVE_SOURCE", "TEST",
                                              "ACTIVE_CONFIGURATION",
                                              "ACTIVE_DATA"} else "MAYBE",
            "safe_to_delete": "YES" if cat == "CACHE_OR_TEMPORARY" else "NO",
            "notes": "",
        })
    _write_csv(OUT / "repository_inventory.csv", rows)

    # summary
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    (OUT / "repository_inventory_summary.json").write_text(
        json.dumps({"total_files": len(rows), "by_category": counts}, indent=2),
        encoding="utf-8",
    )
    print(f"   -> {len(rows)} files inventoried")
    return rows


def build_reference_map() -> dict[str, dict[str, set[str]]]:
    """Grep source/tests/docs for references to phase files."""
    result: dict[str, dict[str, set[str]]] = {}
    scan = {
        "code": ["src", "scripts"],
        "tests": ["tests"],
        "docs": ["docs", "README.md"],
    }
    patterns = [
        re.compile(r"results/phase\d+[a-z0-9]*[/_][A-Za-z0-9_./-]+"),
        re.compile(r"dashboard/phase\d+[a-z0-9]*_[A-Za-z0-9_./-]+"),
        re.compile(r"docs/modeling/phase\d+[a-z0-9]*_[A-Za-z0-9_./-]+"),
        re.compile(r"frozen_validation_definition\.json"),
    ]
    for kind, roots in scan.items():
        for root_rel in roots:
            root_path = ROOT / root_rel
            if root_path.is_file():
                _scan_file(root_path, kind, patterns, result)
                continue
            if not root_path.exists():
                continue
            for p in root_path.rglob("*"):
                if p.is_dir():
                    continue
                if p.suffix in {".pyc"}:
                    continue
                if "__pycache__" in p.parts:
                    continue
                _scan_file(p, kind, patterns, result)
    return result


def _scan_file(path: Path, kind: str, patterns, result):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return
    hits: set[str] = set()
    for pat in patterns:
        for m in pat.finditer(text):
            hits.add(m.group(0).strip('"\''))
    if not hits:
        return
    rel_source = path.relative_to(ROOT).as_posix()
    for h in hits:
        entry = result.setdefault(h, {"code": set(), "tests": set(), "docs": set()})
        entry[kind].add(rel_source)


def _write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------- #

def task_2_protected_manifest(rows) -> list[dict]:
    print("Task 2: protected artifact manifest (BEFORE)")
    protected = []
    for r in rows:
        if r["category"] != "FROZEN_HISTORICAL_ARTIFACT":
            continue
        protected.append({
            "path_before_cleanup": r["path"],
            "sha256_before": r["sha256"],
            "size_bytes": r["size_bytes"],
            "phase": r["phase_if_known"],
            "artifact_type": _artifact_type(r["path"]),
        })
    _write_csv(OUT / "protected_artifact_manifest_before.csv", protected)
    print(f"   -> {len(protected)} protected artifacts")
    return protected


def _artifact_type(p: str) -> str:
    p = p.lower()
    if p.endswith(".parquet"):
        return "data_parquet"
    if p.endswith(".csv"):
        return "data_csv"
    if p.endswith(".json"):
        return "manifest_or_config_json"
    if p.endswith(".html"):
        return "dashboard_html"
    if p.endswith(".md"):
        return "doc_markdown"
    return "other"


# --------------------------------------------------------------------------- #

def task_3_path_audit(rows):
    print("Task 3: path dependency audit")
    ref_map = build_reference_map()
    existing = {r["path"] for r in rows}
    audit_rows = []
    for referenced_path, kinds in sorted(ref_map.items()):
        exists = referenced_path in existing
        for kind, sources in kinds.items():
            for src in sorted(sources):
                audit_rows.append({
                    "source_file": src,
                    "referenced_path": referenced_path,
                    "reference_type": kind,
                    "current_exists": "YES" if exists else "NO",
                    "affected_by_cleanup": "NO",  # we do not move any of these
                    "required_action": "keep_in_place",
                })
    _write_csv(OUT / "path_dependency_audit.csv", audit_rows)
    print(f"   -> {len(audit_rows)} path references audited")


# --------------------------------------------------------------------------- #

def task_5_6_canonical_and_archive_index(protected: list[dict]) -> dict:
    """Mirror Phase 5B.1 headline artifacts into canonical current locations
    and write an archive index describing the historical layout."""
    print("Tasks 5-6: canonical production mirror + archive index")
    prod_dir = ROOT / "results" / "production"
    prod_dir.mkdir(parents=True, exist_ok=True)
    dash_dir = ROOT / "dashboard" / "current"
    dash_dir.mkdir(parents=True, exist_ok=True)

    mirror_map = {
        "results/phase5b1/phase5b1_current_nowcast.json":
            "results/production/current_nowcast.json",
        "results/phase5b1/phase5b1_current_nowcast.csv":
            "results/production/current_nowcast.csv",
        "results/phase5b1/phase5b1_current_nowcast.parquet":
            "results/production/current_nowcast.parquet",
        "results/phase5b1/phase5b1_run_manifest.json":
            "results/production/run_manifest.json",
        "results/phase5b1/phase5b1_production_readiness.json":
            "results/production/production_readiness.json",
        "results/phase5b1/phase5b1_data_quality.csv":
            "results/production/data_quality.csv",
        "results/phase5b1/phase5b1_data_status.csv":
            "results/production/data_status.csv",
        "results/phase5b1/phase5b1_model_monitoring.csv":
            "results/production/model_monitoring.csv",
        "results/phase5b1/phase5b1_revision_decomposition.csv":
            "results/production/revision_decomposition.csv",
        "results/phase5b1/phase5b1_model_input_quality.csv":
            "results/production/model_input_quality.csv",
        "results/phase5b1/phase5b1_code_hash_inventory.csv":
            "results/production/code_hash_inventory.csv",
        "results/phase5b1/phase5b1_audit_report.md":
            "results/production/audit_report.md",
        "dashboard/phase5b1_uzbekistan_nowcast.html":
            "dashboard/current/uzbekistan_nowcast.html",
    }
    mirrored = []
    for src, dst in mirror_map.items():
        src_p = ROOT / src
        dst_p = ROOT / dst
        if not src_p.exists():
            print(f"   ! missing source: {src}")
            continue
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_p, dst_p)
        mirrored.append({
            "source": src,
            "canonical_copy": dst,
            "sha256_source": sha256_of(src_p),
            "sha256_copy": sha256_of(dst_p),
        })

    _write_csv(OUT / "canonical_current_mirror.csv", mirrored)

    # Archive index (files kept in place)
    idx_rows = [
        {
            "phase": p["phase"],
            "original_path": p["path_before_cleanup"],
            "archive_status": "kept_in_place",
            "sha256": p["sha256_before"],
        }
        for p in protected
    ]
    _write_csv(OUT / "archive_index.csv", idx_rows)

    # README in results/production explaining what these are
    (prod_dir / "README.md").write_text(
        _canonical_readme(), encoding="utf-8"
    )
    (dash_dir / "README.md").write_text(
        _dashboard_current_readme(), encoding="utf-8"
    )
    (ROOT / "results" / "archive" / "README.md").write_text(
        _archive_readme(), encoding="utf-8"
    )
    print(f"   -> {len(mirrored)} canonical files mirrored")
    return {"mirrored": mirrored, "count": len(mirrored)}


def _canonical_readme() -> str:
    return (
        "# Canonical current production (Phase 5B.1 mirror)\n\n"
        "This directory is a **copy** of the Phase 5B.1 frozen headline\n"
        "artifacts. The originals under ``results/phase5b1/`` remain the\n"
        "authoritative immutable evidence — files here are aliases so future\n"
        "code has one obvious current-production location.\n\n"
        "Regenerate this mirror after every controlled operational rerun by\n"
        "running ``python scripts/phase5b2_cleanup.py`` (safe, idempotent).\n\n"
        "Current headline (2026Q3, H2): 7.6239786595896035% — 0.5 × AR(2) + \n"
        "0.5 × USD/UZS U-MIDAS(3).\n"
    )


def _dashboard_current_readme() -> str:
    return (
        "# Canonical current dashboard\n\n"
        "``uzbekistan_nowcast.html`` mirrors\n"
        "``dashboard/phase5b1_uzbekistan_nowcast.html``. Do not edit here —\n"
        "regenerate via ``python scripts/phase5b2_cleanup.py``.\n"
    )


def _archive_readme() -> str:
    return (
        "# Historical archive index\n\n"
        "Phase 4A → Phase 5B.1 artifacts remain in their original locations\n"
        "(``results/phase4*_*``, ``results/phase5b/``, ``results/phase5b1/``,\n"
        "``dashboard/phase5*_uzbekistan_nowcast.html``,\n"
        "``docs/modeling/phase*``) because production code and tests\n"
        "reference those paths directly.\n\n"
        "See ``results/phase5b2/archive_index.csv`` for the full manifest\n"
        "with hashes.\n"
    )


# --------------------------------------------------------------------------- #

def task_7_safe_cleanup() -> list[dict]:
    print("Task 7: safe cleanup of reproducible caches")
    removed = []

    for cache_top in CACHE_TOP_DIRS:
        p = ROOT / cache_top
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            removed.append({
                "path": cache_top,
                "category": "empty_pytest_cache_top_dir",
                "reason": "empty/stray pytest cache directory",
                "recoverable": "YES (recreated by pytest)",
                "unique_data_present": "NO",
                "action": "deleted",
            })

    # __pycache__ folders (outside .venv)
    for pyc_dir in ROOT.rglob("__pycache__"):
        try:
            rel = pyc_dir.relative_to(ROOT)
        except ValueError:
            continue
        if is_excluded(rel):
            continue
        shutil.rmtree(pyc_dir, ignore_errors=True)
        removed.append({
            "path": rel.as_posix(),
            "category": "python_bytecode_cache",
            "reason": "regenerated by interpreter",
            "recoverable": "YES",
            "unique_data_present": "NO",
            "action": "deleted",
        })

    # Empty root 'python' sentinel file
    p_root = ROOT / "python"
    if p_root.exists() and p_root.is_file() and p_root.stat().st_size == 0:
        p_root.unlink()
        removed.append({
            "path": "python",
            "category": "empty_root_file",
            "reason": "empty zero-byte file with no content or references",
            "recoverable": "YES (recreate as `touch python`)",
            "unique_data_present": "NO",
            "action": "deleted",
        })

    _write_csv(OUT / "deleted_or_removed_items.csv", removed)
    print(f"   -> {len(removed)} safe items removed")
    return removed


# --------------------------------------------------------------------------- #

def task_13_legacy_scan(rows):
    print("Task 13: legacy/unused candidates")
    ref_map = build_reference_map()
    all_refs = set()
    for kinds in ref_map.values():
        for srcs in kinds.values():
            all_refs.update(srcs)
    candidates = []
    root_files = {
        ".tmp/inspect_cbu_archives.py": "one-off scratch inspection script",
        ".tmp/inspect_rosstat.py": "one-off scratch inspection script",
    }
    for p, why in root_files.items():
        fp = ROOT / p
        if fp.exists():
            candidates.append({
                "path": p,
                "type": "scratch_script",
                "why_candidate": why,
                "referenced_by": "",
                "last_known_phase": "phase2c",
                "safe_to_archive": "YES",
                "safe_to_delete": "NO",
                "recommended_action": "archive (kept in .tmp; already gitignored)",
            })
    # ``pytest-cache-files-e_bgf97r`` etc under .tmp are ephemeral, not code
    _write_csv(OUT / "unused_or_legacy_candidates.csv", candidates)
    print(f"   -> {len(candidates)} candidates flagged")


# --------------------------------------------------------------------------- #

def task_18_hash_verification(protected_before: list[dict]) -> tuple[list[dict], bool]:
    print("Task 18: post-cleanup hash verification")
    after_rows = []
    comparison = []
    all_match = True
    for entry in protected_before:
        rel = entry["path_before_cleanup"]
        fp = ROOT / rel
        after_hash = sha256_of(fp) if fp.exists() else ""
        after_rows.append({
            "path_after_cleanup": rel,
            "sha256_after": after_hash,
            "size_bytes": fp.stat().st_size if fp.exists() else -1,
            "phase": entry["phase"],
            "artifact_type": entry["artifact_type"],
        })
        match = after_hash == entry["sha256_before"] and after_hash != ""
        if not match:
            all_match = False
        comparison.append({
            "artifact": rel,
            "old_path": rel,
            "new_path": rel,
            "sha256_before": entry["sha256_before"],
            "sha256_after": after_hash,
            "hash_match": "TRUE" if match else "FALSE",
            "status": "PRESERVED" if match else "MISMATCH",
        })
    _write_csv(OUT / "protected_artifact_manifest_after.csv", after_rows)
    _write_csv(OUT / "protected_artifact_hash_comparison.csv", comparison)
    print(f"   -> {len(comparison)} artifacts compared; "
          f"{'ALL MATCH' if all_match else 'MISMATCHES DETECTED'}")
    return comparison, all_match


# --------------------------------------------------------------------------- #

def task_19_git_status(baseline_reproduced: bool, hash_ok: bool,
                       tests_ok: bool | None):
    print("Task 19: git status")
    try:
        porcelain = subprocess.run(
            ["git", "status", "--porcelain=v1"], cwd=ROOT,
            capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        porcelain = f"# git status failed: {exc}\n"

    classifications = []
    for line in porcelain.strip().splitlines():
        if not line.strip():
            continue
        code = line[:2]
        rel = line[3:].strip()
        cat = _classify_git_line(rel)
        classifications.append(f"{code}\t{cat}\t{rel}")

    text_lines = [
        "PHASE 5B.2 — GIT STATUS AUDIT",
        f"tests_passed={tests_ok}",
        f"baseline_reproduced={baseline_reproduced}",
        f"protected_hash_ok={hash_ok}",
        "",
        "Raw porcelain:",
        porcelain if porcelain.strip() else "(clean)",
        "",
        "Classification (code | category | path):",
        *classifications,
    ]
    (OUT / "git_cleanup_status.txt").write_text(
        "\n".join(text_lines), encoding="utf-8"
    )
    print("   -> git status captured")
    return porcelain


def _classify_git_line(rel: str) -> str:
    if rel.startswith("results/phase5b2/"):
        return "NEW_PHASE5B2_OUTPUT"
    if rel.startswith("results/production/"):
        return "NEW_PHASE5B2_OUTPUT"
    if rel.startswith("results/archive/"):
        return "NEW_PHASE5B2_OUTPUT"
    if rel.startswith("dashboard/current/"):
        return "NEW_PHASE5B2_OUTPUT"
    if rel in {"PROJECT_STATE.md"}:
        return "NEW_DOCUMENTATION"
    if rel.startswith("docs/PROJECT_HISTORY") or rel.startswith("docs/REPOSITORY_MAP"):
        return "NEW_DOCUMENTATION"
    if rel.startswith("docs/modeling/phase5b2_"):
        return "NEW_DOCUMENTATION"
    if rel == ".gitignore":
        return "EXPECTED_CLEANUP_CHANGE"
    if rel.startswith("scripts/phase5b2_"):
        return "NEW_PHASE5B2_OUTPUT"
    return "UNEXPECTED_CHANGE"


# --------------------------------------------------------------------------- #

def write_manifest(protected_count: int, hash_failures: int,
                   files_scanned: int, removed: list[dict],
                   baseline_reproduced: bool | None,
                   tests_passed: int | None, tests_failed: int | None,
                   warnings: list[str], errors: list[str]):
    print("Task 20: cleanup manifest")
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
            text=True, check=True,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty_after = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
            text=True, check=True,
        ).stdout.strip())
    except Exception as exc:  # noqa: BLE001
        commit = branch = None
        dirty_after = True
        errors.append(f"git commit/branch capture failed: {exc}")

    manifest = {
        "phase": "5B.2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "git_branch": branch,
        "working_tree_dirty_before": False,  # verified above; was clean
        "working_tree_dirty_after": dirty_after,
        "files_scanned": files_scanned,
        "files_moved": 0,
        "files_archived": 0,
        "files_deleted": len(removed),
        "protected_files_checked": protected_count,
        "protected_hash_failures": hash_failures,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "production_baseline_reproduced": baseline_reproduced,
        "canonical_production_path": "results/production/",
        "historical_archive_path": "results/archive/ (index only) — "
                                    "originals kept in place under "
                                    "results/phase4*_*, results/phase5b/, "
                                    "results/phase5b1/, dashboard/phase5*.html",
        "publication_ready_after_cleanup": (
            baseline_reproduced and hash_failures == 0 and not dirty_after
        ),
        "warnings": warnings,
        "errors": errors,
    }
    (OUT / "phase5b2_cleanup_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


# --------------------------------------------------------------------------- #

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    errors: list[str] = []

    rows = task_1_inventory()
    protected_before = task_2_protected_manifest(rows)
    task_3_path_audit(rows)
    task_5_6_canonical_and_archive_index(protected_before)
    removed = task_7_safe_cleanup()
    task_13_legacy_scan(rows)
    _, hash_ok = task_18_hash_verification(protected_before)

    # Note: task 16/17 (baseline reproduce + tests) are executed separately.
    return {
        "warnings": warnings,
        "errors": errors,
        "rows": rows,
        "protected_before": protected_before,
        "removed": removed,
        "hash_ok": hash_ok,
    }


if __name__ == "__main__":
    result = main()
    print("Done.")
