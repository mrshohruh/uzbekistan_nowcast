# Phase 5B.2 — Repository cleanup, archive, and freeze

## 1. Why cleanup was performed

Phases 4A → 5B.1 produced 113 protected historical artifacts scattered across
`results/`, `dashboard/`, and `docs/modeling/`. Operators searching for
"the current nowcast" had no single canonical location. Reproducible cache
directories (`__pycache__/`, empty `pytest-cache-files-*`, an empty root
`python` file) were left in the tree.

Phase 5B.2 does **not** change any econometric result, coefficient, forecast,
validation metric, or production policy. It is a repository-organisation and
reproducibility phase only.

## 2. Previous repository issues

- No single canonical location for the current production nowcast — the
  headline lived under `results/phase5b1/phase5b1_current_nowcast.json` and
  the current dashboard under `dashboard/phase5b1_uzbekistan_nowcast.html`.
- Two empty stray directories (`pytest-cache-files-gk9y2b1q/`,
  `pytest-cache-files-uqcib9tk/`) and an empty root `python` file.
- Cached bytecode under `__pycache__/` across `src/`, `tests/`, `scripts/`.
- No consolidated project-state or repository-map document.

## 3. Target structure

The final layout is:

```
project_root/
├── PROJECT_STATE.md                        # NEW: operator status
├── README.md                               # UPDATED: current production + quick start
├── config/                                 # unchanged
├── data/                                   # unchanged (gitignored)
├── docs/
│   ├── PROJECT_HISTORY.md                  # NEW
│   ├── REPOSITORY_MAP.md                   # NEW
│   └── modeling/
│       ├── phase4a_results.md              # UNCHANGED (immutable)
│       ├── phase4a1_real_v1_results.md     # UNCHANGED (immutable)
│       ├── phase4b_candidate_finalization.md
│       ├── phase4c_frozen_holdout_evaluation.md
│       ├── phase5a_operational_nowcasting.md
│       ├── phase5b_operational_nowcasting.md
│       ├── phase5b1_operational_nowcasting.md
│       └── phase5b2_repository_cleanup.md  # NEW (this file)
├── registry/                               # unchanged
├── src/uznowcast/                          # unchanged
├── tests/                                  # unchanged (caches removed)
├── scripts/
│   └── phase5b2_cleanup.py                 # NEW: safe idempotent runner
├── results/
│   ├── frozen_validation_definition.json   # UNCHANGED (immutable)
│   ├── phase4a*_*                          # UNCHANGED (immutable)
│   ├── phase4b_*                           # UNCHANGED (immutable)
│   ├── phase4c_*                           # UNCHANGED (immutable)
│   ├── phase5a_*                           # UNCHANGED (immutable)
│   ├── phase5b/                            # UNCHANGED (immutable)
│   ├── phase5b1/                           # UNCHANGED (immutable)
│   ├── production/                         # NEW: canonical mirror
│   ├── archive/                            # NEW: logical index only
│   └── phase5b2/                           # NEW: cleanup evidence
└── dashboard/
    ├── phase5a_uzbekistan_nowcast.html     # UNCHANGED (immutable)
    ├── phase5b_uzbekistan_nowcast.html     # UNCHANGED (immutable)
    ├── phase5b1_uzbekistan_nowcast.html    # UNCHANGED (immutable)
    └── current/                            # NEW: canonical mirror
```

The proposal in the Phase 5B.2 spec suggested physically moving historical
artifacts into `results/archive/phase4a/` etc. That was not done because
110+ hardcoded path references live in production code and tests (see
`results/phase5b2/path_dependency_audit.csv`). Following the fail-safe rule
("If repository dependencies are too tangled to reorganize safely: DO NOT
force the proposed folder structure. Prefer minimal cleanup plus
documentation."), the historical artifacts remain in place and
`results/archive/README.md` serves as the logical archive index.

## 4. Files moved

**None.** Zero files were moved. Every hardcoded path reference in
`src/`, `tests/`, and `scripts/` continues to resolve to the exact same
target it did before Phase 5B.2.

## 5. Files archived

Thirteen Phase 5B.1 headline artifacts were **copied** (not moved) into
canonical current-production locations. The originals remain in place and
are byte-for-byte identical. See
`results/phase5b2/canonical_current_mirror.csv` for the mapping and
double hashes.

| Source (immutable) | Canonical copy |
|---|---|
| `results/phase5b1/phase5b1_current_nowcast.json` | `results/production/current_nowcast.json` |
| `results/phase5b1/phase5b1_current_nowcast.csv` | `results/production/current_nowcast.csv` |
| `results/phase5b1/phase5b1_current_nowcast.parquet` | `results/production/current_nowcast.parquet` |
| `results/phase5b1/phase5b1_run_manifest.json` | `results/production/run_manifest.json` |
| `results/phase5b1/phase5b1_production_readiness.json` | `results/production/production_readiness.json` |
| `results/phase5b1/phase5b1_data_quality.csv` | `results/production/data_quality.csv` |
| `results/phase5b1/phase5b1_data_status.csv` | `results/production/data_status.csv` |
| `results/phase5b1/phase5b1_model_monitoring.csv` | `results/production/model_monitoring.csv` |
| `results/phase5b1/phase5b1_revision_decomposition.csv` | `results/production/revision_decomposition.csv` |
| `results/phase5b1/phase5b1_model_input_quality.csv` | `results/production/model_input_quality.csv` |
| `results/phase5b1/phase5b1_code_hash_inventory.csv` | `results/production/code_hash_inventory.csv` |
| `results/phase5b1/phase5b1_audit_report.md` | `results/production/audit_report.md` |
| `dashboard/phase5b1_uzbekistan_nowcast.html` | `dashboard/current/uzbekistan_nowcast.html` |

The canonical mirror is regenerated by
`python scripts/phase5b2_cleanup.py` and is safe to re-run.

## 6. Files deleted

Only reproducible caches were deleted. Every entry is recoverable simply by
re-running pytest or the Python interpreter. See
`results/phase5b2/deleted_or_removed_items.csv` for the full list.

- Two empty stray directories: `pytest-cache-files-gk9y2b1q/`,
  `pytest-cache-files-uqcib9tk/`.
- All `__pycache__/` directories under `src/`, `tests/`, `scripts/`
  (11 total).
- The empty zero-byte root file `python`.

No `.csv`, `.parquet`, `.json`, `.xlsx`, `.html`, `.md`, `.py`, notebook, or
database file was deleted.

## 7. Files deliberately kept

- Every Phase 4A / 4A.1 / 4B / 4C / 5A / 5B / 5B.1 artifact — 113 files in
  total, hash-verified before and after cleanup.
- The two `.tmp/inspect_*.py` scratch scripts (flagged as legacy
  candidates in `results/phase5b2/unused_or_legacy_candidates.csv` but
  kept because `.tmp/` is already gitignored and they document the
  Phase 2C.1 investigation).
- The registry archive (`registry/archive/`) with V1.0 and V1.1 workbooks.
- All Phase 2A → Phase 3B documentation under `docs/`.

## 8. Protected artifact verification

113 protected artifacts hashed before cleanup, 113 hashes matched after
cleanup, 0 mismatches. See:

- `results/phase5b2/protected_artifact_manifest_before.csv`
- `results/phase5b2/protected_artifact_manifest_after.csv`
- `results/phase5b2/protected_artifact_hash_comparison.csv`

## 9. Current canonical production path

- Nowcast: `results/production/current_nowcast.json`
- Manifest: `results/production/run_manifest.json`
- Monitoring: `results/production/model_monitoring.csv`
- Dashboard: `dashboard/current/uzbekistan_nowcast.html`
- Registry: `registry/uzbekistan_nowcasting_v1.2_registry.xlsx`
- Frozen validation: `results/frozen_validation_definition.json`

## 10. Test results

Full suite: **202 passed, 0 failed** with Python 3.12.10 on Windows via
`.\.venv\Scripts\python.exe -m pytest`. Warnings are pre-existing
`UserWarning`s about Phase 4A.1 production tiers with missing predictors —
unchanged from Phase 5B.1. See
`results/phase5b2/phase5b2_cleanup_manifest.json`.

## 11. Baseline reproduction

The frozen headline reproduces exactly:

```
phase5b1 headline JSON point_nowcast : 7.6239786595896035
canonical results/production JSON     : 7.6239786595896035 (byte-identical copy)
production_model                      : 0.5*AR(2) + 0.5*USD/UZS U-MIDAS(3)
target_quarter                        : 2026Q3
operational_stage                     : H2
```

The Phase 5B.1 `full_immutable_hashes` function returns the identical 89-key
dictionary on repeated invocations, confirming that nothing on disk was
mutated during cleanup.

## 12. Git state

See `results/phase5b2/git_cleanup_status.txt`.

Expected untracked/modified paths:

- `PROJECT_STATE.md` (NEW_DOCUMENTATION)
- `docs/PROJECT_HISTORY.md` (NEW_DOCUMENTATION)
- `docs/REPOSITORY_MAP.md` (NEW_DOCUMENTATION)
- `docs/modeling/phase5b2_repository_cleanup.md` (NEW_DOCUMENTATION)
- `README.md` (EXPECTED_CLEANUP_CHANGE — added current-state block and
  quick start; legacy Phase 2B content preserved below)
- `.gitignore` (EXPECTED_CLEANUP_CHANGE)
- `scripts/phase5b2_cleanup.py` (NEW_PHASE5B2_OUTPUT)
- `results/phase5b2/**` (NEW_PHASE5B2_OUTPUT)
- `results/production/**` (NEW_PHASE5B2_OUTPUT — canonical mirror)
- `results/archive/README.md` (NEW_PHASE5B2_OUTPUT)
- `dashboard/current/**` (NEW_PHASE5B2_OUTPUT — canonical mirror)

No historical artifact and no source code file appears in `git status`
apart from `README.md`. The Phase 5B.1 publication gate will pass once the
above are committed.

## 13. Remaining recommendations

- If desired, later phases may extend the canonical mirror to `results/
  production/` with new fields, but must never rewrite the Phase 5B.1
  originals.
- If `data/master/` or `metadata/` are rebuilt, re-run
  `python scripts/phase5b2_cleanup.py` to refresh the canonical mirror
  from the newly current phase.
- The two `.tmp/inspect_*.py` scratch scripts may be moved to
  `archive/legacy_code/` if the operator wants a firmer line, but the
  cost/benefit is small (they are already gitignored).

## 14. Readiness for Phase 5C

Ready. Phase 5C challengers should write only under
`results/challengers/` and `dashboard/challengers/`; every Phase 4A →
Phase 5B.1 artifact is hashed in
`results/phase5b2/protected_artifact_manifest_after.csv` and must remain
identical across Phase 5C.
