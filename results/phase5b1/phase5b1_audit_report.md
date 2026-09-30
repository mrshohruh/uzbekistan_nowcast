# Phase 5B.1 — Production hardening patch for the Phase 5B nowcast

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

- Target: **2026Q3**
- Operational stage: **H2**
- As-of date / cutoff: `2026-09-30` / `2026-09-30`
- Point nowcast: **7.6239786596%**
- Phase 5B reference headline: **7.6239786596%**
- Absolute difference: **0.00e+00**
- Phase 5B numerically reproduced: **True**

## Reproducibility

- Git commit: `becfd93f67b59e19cecdcfbb264913dc11d198e7`
- Git branch: `main`
- Working tree dirty at run: **True**
- Dirty paths recorded: **17**
- Diff SHA-256 (only when tree dirty): `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Production files hashed: **25** of
  25 inventory entries
- Code hash inventory: `results/phase5b1/phase5b1_code_hash_inventory.csv`

Publication readiness is stricter than analytical run success. This run's
publication policy result:

- **publication_ready**: False
- **code_reproducibility_complete**: False

Publication blockers:

- working_tree_dirty: git working tree contains uncommitted or untracked files; commit or stash before an official publication run

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

- **ar1**: model_input_data_not_all_green=False, system_data_gate_has_warnings=True, flags=`system_data_gate_has_warnings`
- **ar2**: model_input_data_not_all_green=False, system_data_gate_has_warnings=True, flags=`system_data_gate_has_warnings`
- **umidas_usd_uzs_mom_dlog**: model_input_data_not_all_green=True, system_data_gate_has_warnings=True, flags=`system_data_gate_has_warnings|model_input_data_not_all_green`
- **ensemble_ar2_umidas_usd**: model_input_data_not_all_green=True, system_data_gate_has_warnings=True, flags=`system_data_gate_has_warnings|model_input_data_not_all_green`

Russia IPI remains a system warning (`system_data_gate_has_warnings=True`)
but no production model consumes it, so it does not appear in any model's
`model_input_data_not_all_green` flag.

## Uncertainty presentation

Point: 7.6240%. Empirical 50% error range:
7.7598%–8.3017%.
Empirical 80% error range:
7.4095%–8.3955%.
Historical H2 RMSE: 0.7798 pp.
Historical H2 bias (actual minus forecast):
+0.3217 pp.

Empirical forecast-error range based on historical H2 actual-minus-forecast errors. Because historical H2 forecasts have been biased downward (mean actual minus forecast = +0.322 pp), the empirical range is not necessarily centered on the current point estimate. This is not a conventional confidence interval.

## Revision decomposition

- Previous headline: 8.2998789602%
- Current headline: 7.6239786596%
- Total revision: -0.6759003007 pp
- New-data effect: +0.0000000000 pp
- Data-revision effect: +0.0000000000 pp
- Stage/specification effect: -0.6759003007 pp
- Model-selection effect: +0.0000000000 pp
- Weight effect: +0.0000000000 pp
- Residual: +0.00e+00 pp
- Residual within 1e-10 tolerance: **True**

## Preservation

Original Phase 4, Phase 5A, and Phase 5B artifacts were hashed before and
after this run and confirmed byte-for-byte unchanged. No prior artifact was
overwritten, and no prior artifact was rewritten "to look cleaner".

**PHASE 5B ARTIFACTS WERE NOT MODIFIED.**
