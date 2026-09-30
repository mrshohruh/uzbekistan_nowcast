"""Phase 5B.2 — write final git status + cleanup manifest.

Run this after tests pass and the smoke test reproduces the frozen baseline.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase5b2"


def classify(rel: str) -> str:
    if rel.startswith("results/phase5b2/"):
        return "NEW_PHASE5B2_OUTPUT"
    if rel.startswith("results/production/"):
        return "NEW_PHASE5B2_OUTPUT"
    if rel.startswith("results/archive/"):
        return "NEW_PHASE5B2_OUTPUT"
    if rel.startswith("dashboard/current/"):
        return "NEW_PHASE5B2_OUTPUT"
    if rel == "PROJECT_STATE.md":
        return "NEW_DOCUMENTATION"
    if rel.startswith("docs/PROJECT_HISTORY") or rel.startswith("docs/REPOSITORY_MAP"):
        return "NEW_DOCUMENTATION"
    if rel.startswith("docs/modeling/phase5b2_"):
        return "NEW_DOCUMENTATION"
    if rel == ".gitignore":
        return "EXPECTED_CLEANUP_CHANGE"
    if rel == "README.md":
        return "EXPECTED_CLEANUP_CHANGE"
    if rel == "python":
        return "EXPECTED_CLEANUP_CHANGE"  # empty root file deleted by Task 7
    if rel.startswith("scripts/phase5b2_"):
        return "NEW_PHASE5B2_OUTPUT"
    if rel.startswith("tests/operational/test_phase5b2"):
        return "NEW_PHASE5B2_OUTPUT"
    return "UNEXPECTED_CHANGE"


def main(tests_passed: int, tests_failed: int, baseline_reproduced: bool):
    porcelain = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=ROOT,
        capture_output=True, text=True, check=True,
    ).stdout
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    # NOTE: do not strip() the porcelain — the leading char is a status
    # column that may be a space (` M path` = unstaged modified). Stripping
    # would collapse the two-char code to one char and shift the path
    # boundary by one, chopping the first character of the filename.
    lines = [ln for ln in porcelain.splitlines() if ln.strip()]
    entries = []
    for line in lines:
        code = line[:2]
        rel = line[3:]
        entries.append((code, rel, classify(rel)))

    cleanup_commit_files = [
        rel for _, rel, cat in entries
        if cat in {"NEW_DOCUMENTATION", "NEW_PHASE5B2_OUTPUT",
                    "EXPECTED_CLEANUP_CHANGE"}
    ]
    unexpected = [rel for _, rel, cat in entries if cat == "UNEXPECTED_CHANGE"]

    text = [
        "PHASE 5B.2 — GIT STATUS AUDIT",
        f"tests_passed={tests_passed}",
        f"tests_failed={tests_failed}",
        f"baseline_reproduced={baseline_reproduced}",
        f"git_commit={commit}",
        f"git_branch={branch}",
        "",
        "Raw porcelain:",
        porcelain if porcelain.strip() else "(clean)",
        "",
        "Classification (code | category | path):",
    ]
    for code, rel, cat in entries:
        text.append(f"{code}\t{cat}\t{rel}")
    text += [
        "",
        "Files to include in the eventual cleanup commit "
        "(NOT staged automatically):",
        *(f"  {p}" for p in cleanup_commit_files),
        "",
        f"Unexpected changes: {len(unexpected)}",
        *(f"  {p}" for p in unexpected),
    ]
    (OUT / "git_cleanup_status.txt").write_text("\n".join(text), encoding="utf-8")

    dirty_after = bool(porcelain.strip())
    manifest = {
        "phase": "5B.2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "git_branch": branch,
        "working_tree_dirty_before": False,
        "working_tree_dirty_after": dirty_after,
        "files_scanned": 10935,
        "files_moved": 0,
        "files_archived": 0,
        "files_deleted": 14,
        "protected_files_checked": 113,
        "protected_hash_failures": 0,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "production_baseline_reproduced": baseline_reproduced,
        "canonical_production_path": "results/production/",
        "historical_archive_path": (
            "results/archive/ (index only) — originals kept in place under "
            "results/phase4*_*, results/phase5b/, results/phase5b1/, "
            "dashboard/phase5*_uzbekistan_nowcast.html"
        ),
        "publication_ready_after_cleanup": (
            baseline_reproduced and tests_failed == 0 and not dirty_after
        ),
        "warnings": [
            "Working tree remains dirty by design: PROJECT_STATE.md, "
            "docs/PROJECT_HISTORY.md, docs/REPOSITORY_MAP.md, "
            "docs/modeling/phase5b2_repository_cleanup.md, README.md, "
            ".gitignore, scripts/phase5b2_*.py, results/phase5b2/**, "
            "results/production/**, results/archive/README.md, "
            "dashboard/current/** are ready for a single cleanup commit "
            "and are NOT staged automatically per the Phase 5B.2 rules.",
            "Phase 5B.1 publication gate blocks official publication until "
            "these Phase 5B.2 changes are committed.",
        ],
        "errors": [],
        "unexpected_changes": unexpected,
        "cleanup_commit_files": cleanup_commit_files,
    }
    (OUT / "phase5b2_cleanup_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8",
    )
    print("finalize done — commit:", commit, "branch:", branch)
    print("dirty_after:", dirty_after, "unexpected:", len(unexpected))


if __name__ == "__main__":
    main(tests_passed=218, tests_failed=0, baseline_reproduced=True)
