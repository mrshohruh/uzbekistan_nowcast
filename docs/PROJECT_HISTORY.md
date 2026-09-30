# Project history

## Phase 1–3 — Data infrastructure

Registry-driven ingestion, cleaning, and transformation of the Uzbekistan
V1 macroeconomic panel. Established the row-4 registry contract, SIAT/CBU
downloaders and parsers, immutable raw storage with checksums, YTD
de-cumulation, daily→monthly FX aggregation, revision preservation, and a
single monthly master + separate quarterly GDP target. Registry V1.0
graduated to V1.1 (source-URL corrections) and V1.2 (Phase 3B changes,
sparse-series audit, gold-proxy diagnostic, model-readiness tiers).

## Phase 4A — Initial econometric model evaluation

Benchmark GDP nowcasting candidates: AR(p), OLS bridge, U-MIDAS, and a
simple DFM. Established prediction/metrics/loadings artifacts under
`results/phase4a_*.parquet` and the model-spec JSON.

## Phase 4A.1 — Real-data validation

Common-sample and matched-sample metrics on the live V1.2 build, fixture
guard, effective-training safeguards, resolved model-readiness tiers, and
the frozen 4-quarter holdout window. Outputs under `results/phase4a1_*`.

## Phase 4B — Candidate architecture

Frozen candidate menu (`results/phase4b_candidate_freeze.json`), DFM
tolerance and diagnostics, ensemble horizon-update mechanics, and
development-window predictions. Everything prior to Phase 4C's frozen
holdout evaluation is preserved as archived training-window evidence.

## Phase 4C — Frozen holdout evaluation

Ran the Phase 4B candidates on the frozen holdout, produced
`results/phase4c_holdout_predictions.parquet` and
`results/phase4c_holdout_metrics.parquet`, and selected the production
combination on holdout evidence alone.

## Phase 5A — First operational nowcast

First live operational Uzbekistan GDP nowcast. Produced the initial
current-nowcast/run-manifest/production-policy/revision-history artifacts
under `results/phase5a_*`, and the first operator dashboard at
`dashboard/phase5a_uzbekistan_nowcast.html`.

## Phase 5B — Operational hardening

Added data-quality gates, information-set audit, empirical uncertainty
intervals, revision decomposition, model monitoring, and a hardened
operator dashboard. Wrote outputs under `results/phase5b/` and the
`dashboard/phase5b_uzbekistan_nowcast.html` dashboard.

## Phase 5B.1 — Final production hardening

Added deterministic production code-hash inventory, publication-readiness
policy that blocks official publication on a dirty tree, model-specific
data-quality flags (AR does not inherit USD/UZS AMBER), revision
decomposition residual test, and dashboard default-horizon correction to
the operational stage. Wrote outputs under `results/phase5b1/` and
`dashboard/phase5b1_uzbekistan_nowcast.html`. Frozen production baseline
for 2026Q3, H2: **7.6239786595896035%** from 0.5 × AR(2) + 0.5 × USD/UZS
U-MIDAS(3).

## Phase 5B.2 — Repository cleanup and freeze

Repository-organisation phase. Inventoried 10,935 files, hashed the 113
protected Phase 4A → Phase 5B.1 artifacts before and after cleanup (all
identical), audited hardcoded path references, mirrored the Phase 5B.1
headline artifacts into a canonical `results/production/` +
`dashboard/current/` layer, removed only reproducible caches
(`__pycache__/`, empty `pytest-cache-files-*` shells, empty `python`
root file), and produced the `PROJECT_STATE.md`, `REPOSITORY_MAP.md`, and
Phase 5B.2 report. No frozen historical artifact was moved or modified.

## Phase 5C — Challenger model development

Future work. Must write only to `results/challengers/` and
`dashboard/challengers/`. Must not modify Phase 4A → Phase 5B.1 evidence.
Must reuse the frozen `results/frozen_validation_definition.json` and the
frozen holdout protocol from Phase 4C.
