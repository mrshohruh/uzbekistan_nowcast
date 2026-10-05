# Production master-state reconciliation — Phase 6E.1

1. Blocked release: `results/production/run_manifest.json`, phase5b1-20260930-6517c7c8f4, 2026Q3/H2. Enforcement: `src/uznowcast/operational/phase5b1.py`, Phase 4B frozen master hashes.

2. Missing historical master hashes: monthly `78a7c51b97247d3ccbd72cbcb03b89f6f52f0f091201956bba85c0373856ba7c`; quarterly `36793699e48de74ecfe31eeb7eb8f23cf3eb6f2ab9ca929cdd4bb240c1bdfbac`.

3. Exact historical master recovery: {'monthly': [], 'quarterly': []}. Search coverage and inaccessible paths are documented separately; Git candidates were checked by content hash.

4. Current hashes: {'monthly_master_hash': '30bed04601df4010d0cf995892c8b4ac3cf211a46f61e2c8f5772e00fac30d04', 'quarterly_master_hash': '196a8c980895163efc5fd9a25dca93523b1b25719057149a21637a2925457b51', 'registry_hash': '0659713cea0fea42c3823a3be26dd116ba15f2b292f269ba5f7e1c7b99abbb33'}. Both master hashes differ; registry matches.

5. Legitimate evolution is supported by the October 2 build manifest, later retrieval timestamps, verified raw provenance and exact reconstruction from current processed observations. The saved release reported incomplete September FX/H2; current data support H3. Specific appended/revised rows, historical schema changes and byte-only GDP changes remain UNKNOWN. No historical observation-level comparison was fabricated.

6. No model code was edited. Recorded source/config hashes were checked in production_manifest_audit.csv; any non-model inventory differences are reported there.

7. No model specifications changed; all pre-existing readable file hashes were verified after tests.

8. Four current production forecasts reproduce twice for the saved 2026Q3 target at 2026-10-05/H3: {'ar1': 8.037443796835966, 'ar2': 7.333857441688032, 'umidas_usd_uzs_mom_dlog': 7.979937793462349, 'ensemble_ar2_umidas_usd': 7.65689761757519}. The current calendar target (2026Q4) is recorded but not promoted to production by this reconciliation. Saved H2 values reproduce numerically; all seven Phase 6D forecasts reproduce from immutable snapshot inputs. Production retains its registry-lag/current-GDP-vintage policy; Phase 6D retains its documented-release GDP-vintage policy. Those inputs differ, so the production and shadow benchmark numbers need not coincide.

9. Historical release cannot be fully reconstructed without exact historical masters; numeric forecast agreement does not satisfy its hash gate.

10. Current operational state: VALIDATED_READ_ONLY. This is read-only input/calculation validation, not publication approval. Existing dirty-tree and data-quality warnings remain applicable.

11. New current-state manifest created: True; it explicitly disclaims replacing the historical release and records current inputs, code, specifications and timestamp.

12. Original historical manifest unchanged: True. Historical expected hashes and enforcement code were never rewritten.

13. Phase 6D unchanged: True; complete existing directory covered by the baseline inventory, including ledgers, withdrawals, realizations, snapshots and seals. No new snapshot was appended.

14. Final classification: **LEGITIMATE_MASTER_EVOLUTION**. Tests: 386 passed, 0 failed. Protected readable files: 19971 checked, 0 changed.

Run read-only verification with `.venv/Scripts/python.exe scripts/reconciliation/reconcile.py validate_current_production_state`. Evidence is written only under results/reconciliation; the historical production gate is unchanged. This command alone does not issue a valid state manifest: finalize additionally requires passed tests and protected-file checks.
