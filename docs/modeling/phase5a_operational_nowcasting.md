# Phase 5A — First operational Uzbekistan GDP nowcast

## Operational result

- Run timestamp (UTC): `2026-09-30T06:00:13.385637Z`
- As-of date: `2026-09-30`
- Automatically detected target: **2026Q3**
- Automatically detected information stage: **H3**
- Latest legitimately known GDP: **2026Q2**, 8.5% YoY
- Headline fixed 50/50 ensemble: **8.300%**
- AR(1): 8.037%
- AR(2): 7.334%
- USD/UZS U-MIDAS(3): 9.266%
- Monthly information cutoff: `2026-09-30`
- Latest usable monthly reference period: `2026-08-31`

2026Q3 is the calendar quarter containing 2026-09-30 and is the first quarter at or after the latest GDP outcome legitimately available under the 31-day registry timing assumption (2026Q2). The monthly panel contributes 36 release-eligible target-quarter records through 2026-08-31.

H3 is the latest existing Phase 4 horizon cutoff on or before 2026-09-30 (2026-09-30).

## Frozen production policy

Phase 5A starts a post-validation operational period. The headline remains exactly
`0.5 × AR(2) + 0.5 × USD/UZS U-MIDAS(3)`. AR(1), AR(2), and standalone U-MIDAS
are comparison models. No model, predictor, lag, transformation, release convention,
or weight was selected from the current-quarter result. Standard registry release
lags are the production convention; conservative lags remain a sensitivity diagnostic.

## Real-time information and leakage controls

The quarterly training window contains every GDP outcome whose assumed release date
(quarter end plus the registry's 31-day lag) is no later than the as-of date, and then
explicitly removes the target and every later quarter. Each monthly master cell is
eligible only when its reference month-end plus its variable-specific registry lag is
no later than the as-of date. Missing cells remain missing.

Leakage checks: target_quarter_gdp_absent_from_training=passed, later_gdp_absent_from_training=passed, monthly_values_released_after_as_of_absent=passed.

The cell-level evidence is in `results/phase5a_data_status.csv` and `.parquet`, including
the source, expected/assumed availability date, availability flag, model-use flag, and
exclusion reason for every predictor-month record.

## Availability at the run date

- Registered monthly indicators: 28
- Currently usable indicators: 27
- Indicators with observations awaiting assumed release: 0
- Missing/unavailable indicators: 1

“Currently usable” means at least one non-missing value is legitimately available; it
does not mean the latest calendar-month row is populated. In particular, the existence
of a September master row does not make a September observation available.

## Indicative uncertainty

7.717% to 8.883%. This is the point forecast plus/minus the 0.582755 percentage-point RMSE across 14 matching Phase 4B expanding-window development forecasts. It is an indicative historical forecast-error range, not a formal confidence interval.

The four Phase 4C holdout outcomes are not used to estimate this range.

## Validation and revision history

The dashboard reads the untouched Phase 4C prediction and metric artifacts. H3 is the
default management view, while H1 and H2 remain selectable. The revision-history files
contain the initial live run and clearly labelled Phase 4C H1→H2→H3 demonstrations;
historical validation revisions are never presented as live operational revisions.

## Reproducibility

- Monthly master SHA-256: `78a7c51b97247d3ccbd72cbcb03b89f6f52f0f091201956bba85c0373856ba7c`
- Quarterly master SHA-256: `36793699e48de74ecfe31eeb7eb8f23cf3eb6f2ab9ca929cdd4bb240c1bdfbac`
- Registry SHA-256: `0659713cea0fea42c3823a3be26dd116ba15f2b292f269ba5f7e1c7b99abbb33`
- Release-lag mode: `standard`
- Estimation: expanding window
- Model architecture: Phase 4B freeze, unchanged through Phase 4C and Phase 5A

The complete run manifest is `results/phase5a_run_manifest.json`. The dashboard is
`dashboard/phase5a_uzbekistan_nowcast.html` and is self-contained.

## Limitations

- Phase 4C contains only four validation quarters, so its ranking is initial evidence.
- Release availability is a frozen registry-lag approximation where historical first-release
  timestamps are unavailable; it is not a reconstructed official release archive.
- The only monthly signal in the production U-MIDAS is USD/UZS dynamics. The prototype
  does not claim sector contributions or causal effects.
- The uncertainty range is a historical error yardstick, not a probability statement.

**PHASE 4C VALIDATION ARTIFACTS WERE NOT MODIFIED.**

**THE CURRENT NOWCAST USES ONLY INFORMATION AVAILABLE AS OF THE SPECIFIED AS-OF DATE.**
