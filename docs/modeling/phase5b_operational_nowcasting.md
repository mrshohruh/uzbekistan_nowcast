# Phase 5B — Hardened operational Uzbekistan GDP nowcast

## Result

- Status: **SUCCESS_WITH_WARNINGS**
- Target: **2026Q3**
- Operational stage: **H2**
- As-of date / information cutoff: `2026-09-30` / `2026-09-30`
- Point nowcast: **7.624%**
- Empirical 50% error interval: **7.760%–8.302%**
- Empirical 80% error interval: **7.409%–8.396%**
- Matching-horizon historical RMSE: **0.780 pp**
- Latest official GDP: **2026Q2 = 8.5% YoY**

These empirical intervals use 18 matching-H2 errors
(14 Phase 4B development pseudo-OOS and
4 untouched Phase 4C holdout observations). They are
historical forecast-error ranges, not structural probability forecasts.

## Phase 5A audit and correction

The Phase 5A implementation matched its frozen model, weight, cutoff masking, expanding-window,
hash, and output policies. One operational-label limitation was found: stage detection used the
calendar cutoff. The September USD/UZS monthly aggregate in the frozen vintage is marked
`partial_month` and has no clean model value. Phase 5B therefore reports **H2**,
the highest stage supported by complete contiguous target-quarter production-signal months
(2026-07-31, 2026-08-31). Phase 5A files were not changed.

## Revision from Phase 5A

- Previous headline: 8.299879%
- Phase 5B headline: 7.623979%
- Revision: -0.675900 percentage points
- New-data effect: +0.000000 pp
- Data-revision effect: +0.000000 pp
- Stage/specification effect: -0.675900 pp

Input hashes are unchanged, so the revision is exactly attributed to using the availability-driven
H2 frozen estimation path instead of Phase 5A's calendar-labelled H3 path. Model
selection and 0.5/0.5 weights are unchanged.

## Data-quality gate

- GREEN: 14
- AMBER: 14
- RED: 1
- Missing expected current-quarter observations: 18
- Fallback observations used: 0

RED optional series do not silently enter production. The current RED series and its retrieval
evidence are retained in `phase5b_data_quality`. No value was imputed, interpolated, zero-filled,
extrapolated, or forward-filled.

## Operational definitions

- H1: first complete, release-eligible target-quarter USD/UZS monthly aggregate.
- H2: first two complete, release-eligible target-quarter aggregates.
- H3: all three complete, release-eligible target-quarter aggregates.
- A delayed or partial release keeps the system at the highest contiguous supported stage.

The information-set audit records every quarterly outcome and monthly lag observation entering
estimation or the current target vector. All rows pass `assumed_available_date <= forecast_origin`
and the run information cutoff.

## Fail-safe and fallback policy

Required GDP or USD failures, cutoff violations, registry/model mismatches, insufficient samples,
or an unavailable headline ensemble stop publication. Optional-series failures create warnings.
The permitted hierarchy is official data, an explicit prior official vintage, a frozen lag structure
that does not require the missing value, then model exclusion. Statistical filling is prohibited.

## Monitoring limitations

The Phase 4C monitoring metrics contain only four quarters. Coefficient change is a reproducible
expanding-fit diagnostic, not a formal stability test. Russia IPI remains unavailable because the
recorded Rosstat retrieval failed TLS certificate verification; it is not used by any production model.
The release calendar remains an assumption where historical first-release timestamps are unavailable.

## Reproducibility and preservation

The run manifest records hashes, code identity, models, warnings, outputs, and all
68 immutable Phase 4/5A artifact hashes. The production policy was written
before model estimation.

**PHASE 4 AND PHASE 5A ARTIFACTS WERE NOT MODIFIED.**

**THE PHASE 5B NOWCAST USES ONLY INFORMATION AVAILABLE BY THE SPECIFIED CUTOFF.**
