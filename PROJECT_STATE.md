# Uzbekistan GDP Nowcasting — Project State

**Current date:** 2026-09-30

**Current production target:** 2026Q3

**Operational stage:** H2

**Current nowcast:** 7.6239786595896035%

**Latest official GDP:** 2026Q2 = 8.5% YoY

**Frozen production model:** 0.5 × AR(2) + 0.5 × USD/UZS U-MIDAS(3)

**Frozen through:** Phase 5B.1

**Current production status:** controlled operational reruns supported

**Publication readiness:** depends on a clean Git/code state at run time
(the Phase 5B.1 gate blocks official publication when the working tree is
dirty).

**Frozen historical phases:**

- Phase 4A
- Phase 4A.1
- Phase 4B
- Phase 4C
- Phase 5A
- Phase 5B
- Phase 5B.1

**Next development phase:** Phase 5C — Challenger Model Development

**Critical rule:** Phase 5C challengers must not modify the frozen Phase 5B.1
production baseline. Any challenger work writes to `results/challengers/` and
`dashboard/challengers/` and must leave Phase 4A → Phase 5B.1 artifacts
byte-for-byte unchanged.

## Canonical paths

| What | Path |
|---|---|
| Current production nowcast (JSON) | `results/production/current_nowcast.json` |
| Current production nowcast (CSV/Parquet) | `results/production/current_nowcast.{csv,parquet}` |
| Current run manifest | `results/production/run_manifest.json` |
| Current production readiness | `results/production/production_readiness.json` |
| Current data quality | `results/production/data_quality.csv` |
| Current data status | `results/production/data_status.csv` |
| Current model monitoring | `results/production/model_monitoring.csv` |
| Current revision decomposition | `results/production/revision_decomposition.csv` |
| Current model input quality | `results/production/model_input_quality.csv` |
| Current code hash inventory | `results/production/code_hash_inventory.csv` |
| Current audit report | `results/production/audit_report.md` |
| Current dashboard | `dashboard/current/uzbekistan_nowcast.html` |
| Registry (authoritative) | `registry/uzbekistan_nowcasting_v1.2_registry.xlsx` |
| Model policy / freeze | `results/phase4b_candidate_freeze.json` |
| Frozen validation definition | `results/frozen_validation_definition.json` |
| Historical archive index | `results/archive/README.md` + `results/phase5b2/archive_index.csv` |
| Tests | `tests/` |
| Phase 5B.2 cleanup evidence | `results/phase5b2/` |

The `results/production/` and `dashboard/current/` directories are **copies**
of the Phase 5B.1 headline artifacts. The originals under
`results/phase5b1/` and `dashboard/phase5b1_uzbekistan_nowcast.html` remain
the authoritative immutable evidence. See
`docs/modeling/phase5b2_repository_cleanup.md` for details.
