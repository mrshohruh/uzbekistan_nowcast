# Phase 5D prospective shadow protocol

PHASE 5D — PROSPECTIVE SHADOW EVALUATION
NOT AN OFFICIAL MODEL REPLACEMENT

This protocol is immutable. Production is 0.5 × AR(2) + 0.5 × USD/UZS
U-MIDAS(3); no specification, transformation, lag or production artifact changes.
The exact inherited 2026Q3 H2 production value is 7.6239786595896035%.

Cohort selection uses only Phase 5C: include all shadow gates, then fill a small
research cohort with acceptable stability, >=51/54 development observations,
no fragile-influence warning, and an operational inherited forecast. REJECT
is binding. Frozen model definitions, component weights and source hashes are
in phase5d_frozen_challenger_cohort.json. Combination weights are held fixed
at their Phase 5C terminal values; no new outcomes can tune them. Missing
components make a forecast unavailable; weights are never renormalized later.

Evidence classes: DEVELOPMENT_PSEUDO_OOS and HISTORICAL_POST_DEVELOPMENT_TEST
remain historical. LIVE_PROSPECTIVE_SHADOW_PENDING is not accuracy evidence.
LIVE_PROSPECTIVE_REALIZED requires a frozen spec, a pre-release written
forecast, a stored cutoff, an auditable information set and an official outcome.
Start 2026Q3; there is no ending-quarter limit. Inherited H2 forecasts retain
Phase 5C manifest timestamps (run-level provenance, not invented row timestamps).
H1/H3 were not recorded and remain unavailable. They cannot be reconstructed.

H1/H2/H3 mean one/two/three contiguous release-eligible target-quarter USD
monthly aggregates, as in the frozen operational policy. Calendar progression
alone does not advance horizons. Standard registry lags and conservative
standard+15 days (zero-lag daily: 3 days) are inherited. Retrieval timestamps
bound actual availability; lag assumptions alone cannot admit future vintages.
Future forecasts are generated at invocation time, never backdated, from archived
master snapshots with observation retrieval/release eligibility. Unknown source
release dates remain null. Information records include hashes, latest available
months, code commit, registry assumptions and publication cutoff.

Primary GDP convention: FIRST_OBSERVED_OFFICIAL_AFTER_FREEZE. True historical
first releases cannot be reconstructed reliably from existing SIAT snapshots
(their release field is a dataset update timestamp). Preserve first observed
official release and subsequent revised values separately. Never relabel the
first observed value as a proven first publication. Source date evidence and an
archived official raw payload are required for realization registration. Unknown
or ambiguous release timing blocks primary prospective scoring. Freeze precedes
release except inherited 2026Q3, whose specifications and forecasts were frozen
in Phase 5C; if release predated Phase 5D, explicit contemporaneous evidence of
Phase 5C eligibility is required and automated registration refuses it.

Primary forecast convention: first written operational forecast per
quarter/model/horizon/lag mode. Missing forecasts remain missing. All later
vintages are retained but cannot displace the primary forecast.
Errors are forecast minus actual. Matched model/production observations alone
determine RMSE, MAE, bias, median/worst absolute error, relative metrics and
deltas. Report every horizon and pooled H1–H3 separately by lag mode.
Coverage denominator is all realized quarters × requested horizons; missing
records count as unavailable. Failure rate is failed / attempted (excludes
not-yet-available horizons). Revision sizes mean absolute H1→H2/H2→H3/H1→H3
changes, distinct from GDP data revisions.

Quantity stages: 0 NOT_YET_EVALUABLE; 1–3 INSUFFICIENT_PROSPECTIVE_EVIDENCE;
4–5 EARLY_PROSPECTIVE_EVIDENCE; 6–7 MODERATE_PROSPECTIVE_EVIDENCE;
8+ MATURE_PROSPECTIVE_EVIDENCE. No stage promotes a challenger.
At >=4 matched quarters, drop each quarter and require every relative RMSE <1
for ROBUST_PROSPECTIVE_IMPROVEMENT; otherwise flag fragile improvement.
Review eligibility requires >=4 matched quarters, pooled relative RMSE <1,
all horizons covered with >=4 matched quarters and relative RMSE <=1.05,
relative MAE <=1.02, |bias| <=0.5 percentage points, coverage >=90% of
production and >=80% absolute, failure rate <=5%, mean absolute forecast
revision <=max(0.5,1.5×production), robust influence, consistent conservative
lag results (relative RMSE <1, horizon deterioration <=0.05), and reproducible
specifications. Missing evidence fails a check. Four/five-quarter eligibility
is EARLY only; serious replacement decisions should wait 6–8 quarters and
require separate explicit authorization. PRODUCTION_MODEL is forbidden for
challengers. Single-quarter winner labels are descriptive only.

Limitations: Phase 5C historical outcomes are not pristine holdout evidence;
combination robustness under conservative lags was not tested in Phase 5C,
so inherited combinations remain research shadows and cannot pass that gate
until genuine prospective evidence accumulates. All three research candidates
share components and are correlated. No inference of significance from tiny N.
The immutable JSON ledger is authoritative; CSV/Parquet and dashboard are
derived mirrors. Hashes of old phases, frozen specs/protocol, ledgers and
information snapshots are checked on every run. No automatic source repair.

Frozen challengers: combination_equal_weight, combination_inverse_past_rmse, combination_nonnegative_past_stack
