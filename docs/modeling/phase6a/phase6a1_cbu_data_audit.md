# Phase 6A.1 — CBU MIDAS Data Audit

## 1. Objective

Read-only Phase 6A.1 audit of existing database suitability for the supplied CBU MIDAS architecture. No model estimated, no collection performed, no production or shadow gate changed. Production remains 0.5 × AR(2) + 0.5 × USD/UZS U-MIDAS(3).

## 2. CBU framework being replicated

Eight conceptual indicators in Supply, Consumption, Payments, External and Labour; proposed later comparisons include AR(1), quarterly aggregation, Almon MIDAS, U-MIDAS, MIDAS-GETS and MIDAS-GETSIS. This taxonomy comes from the user request. The original paper is absent from repository evidence, so exact original units, search terms and sample cannot be confirmed. No inference of original physical versus nominal measures is presented as verified.

## 3. CBU-to-current-database crosswalk

| cbu_block | cbu_indicator | candidate_variable_key | mapping_status | recommended_role |
| --- | --- | --- | --- | --- |
| Supply | Industrial production | industrial_production | CLOSE_MATCH | CORE_CBU_REPLICATION |
| Supply | Construction | construction | AVAILABLE_BUT_SHORT | CORE_CBU_REPLICATION |
| Supply | Services output |  | MISSING | EXCLUDE_FROM_6A2 |
| Consumption | Retail trade | retail_trade | AVAILABLE_BUT_SHORT | CORE_CBU_REPLICATION |
| Payments | Receipts from trade and paid services | pos_turnover | ALTERNATIVE_PROXY | CBU_PROXY_EXTENSION |
| Payments | Receipts from trade and paid services | instant_payments | ALTERNATIVE_PROXY | OPTIONAL_EXTENSION |
| Payments | Receipts from trade and paid services | interbank_payments | ALTERNATIVE_PROXY | EXCLUDE_FROM_6A2 |
| External | Exports excluding gold | exports_non_gold | ALTERNATIVE_PROXY | CBU_PROXY_EXTENSION |
| External | Imports | imports_total | AVAILABLE_BUT_SHORT | CORE_CBU_REPLICATION |
| Labour | Job-search activity / queries |  | MISSING | EXCLUDE_FROM_6A2 |

Exactly one primary status per candidate. For headline counts the three Payments alternatives collapse to POS, the closest alternative. AVAILABLE_BUT_SHORT overrides conceptual exactness when 2018+ coverage fails. Strict EXACT_MATCH count is zero because original paper definitions are unverified.

## 4. Supply block

Industrial production is national current-price output (SIAT 590), not proven physical volume: 80 clean months, January 2020–August 2026. Construction has 56 clean months, January 2022–August 2026. Services output is absent. CPI services measures prices, wholesale measures distribution turnover, and neither establishes services output. Industry exceeds registry/Phase5C July endpoint by one current vintage month. Prior extension audit flags classification/reporting-universe changes in pre-2019 industry.

## 5. Consumption block

Retail turnover (SIAT 2699) has 68 clean months, January 2021–August 2026; unit conversion from million sums to billion UZS is preserved. It measures nominal spending rather than consumption volume. Older bulletin definitions differ in catering coverage; no splice authorized.

## 6. Payments / trade-service receipts block

Exact classified bank receipts are absent. POS is the economically closest alternative because merchant card payments buy goods/services, but cash and non-card receipts are excluded. Fast payments include business transfers without matched end-use; interbank settlements are broader still. Stored clean counts are POS=20, fast=15, interbank=7. These are sparse histories, not continuous series from their registry starts. Raw POS/interbank begin December 2018 despite registry January 2018 claims. Adoption, channel migration and schema changes must be evaluated. Archive publication dates are proxies, not demonstrated historical first releases.

## 7. External block

Imports directly represent nominal USD imports; non-gold exports subtract gold-dominated Other goods rather than pure gold. Both have 56 clean months from January 2022. Non-gold exports is an ALTERNATIVE_PROXY, with inherited source revisions and release lag. Exact gold exclusion is a high-priority definition gap. Do not silently replace the registry with HS71, which also is not automatically pure gold.

## 8. Labour block

No search activity exists in the registry, master or source contracts. Reproducible reconstruction from an official/public historical source is NOT ESTABLISHED. No original search terms, provider, geography, normalization, extraction timestamp or frozen snapshots are stored. A public search service might be a candidate only after the original study is obtained and its protocol verified; official vacancies/job-seeker registrations are a distinct alternative concept. MISSING is used rather than declaring impossibility (NOT_REPRODUCIBLE).

## 9. Data coverage and release-lag assessment

| candidate_variable_key | actual_panel_start | actual_panel_end | nonmissing_observations | missing_share | internal_missing_months | max_internal_gap_months | typical_release_lag_days |
| --- | --- | --- | --- | --- | --- | --- | --- |
| industrial_production | 2020-01-31 | 2026-08-31 | 80 | 0.23809523809523808 | 0 | 0 | 33.0 |
| construction | 2022-01-31 | 2026-08-31 | 56 | 0.4666666666666667 | 0 | 0 | 27.0 |
|  |  |  | 0 | 1.0 | 0 | 0 |  |
| retail_trade | 2021-01-31 | 2026-08-31 | 68 | 0.3523809523809524 | 0 | 0 | 24.0 |
| pos_turnover | 2020-01-31 | 2026-06-30 | 20 | 0.8095238095238095 | 58 | 36 | 18.0 |
| instant_payments | 2022-01-31 | 2026-06-30 | 15 | 0.8571428571428571 | 39 | 34 | 18.0 |
| interbank_payments | 2019-12-31 | 2025-09-30 | 7 | 0.9333333333333333 | 63 | 60 | 18.0 |
| exports_non_gold | 2022-01-31 | 2026-08-31 | 56 | 0.4666666666666667 | 0 | 0 | 26.0 |
| imports_total | 2022-01-31 | 2026-08-31 | 56 | 0.4666666666666667 | 0 | 0 | 26.0 |
|  |  |  | 0 | 1.0 | 0 | 0 |  |

Counts use 105 months, January 2018–September 2026; unavailable months and unpopulated trailing months count as missing. The 802-row union begins 1960 and ends October 2026; union missingness is separately reported and is not the replication metric. Internal gaps count only between first and last populated clean months. Raw versus clean dates are separate: YoY needs 12 months. GDP has 34 quarters, 2018Q1–2026Q2, with no interpolation.

H1/H2/H3 are quarter month ends. Release admission uses reference-month end + registry lag; conservative mode adds 15 days, with zero-lag sources at least three days. Crosswalk records exact standard/conservative 2026Q3 cutoffs and actual latest observations. Positive monthly lags usually imply no current-quarter month at H1, one at H2 and two at H3; actual sparse series can be older. This is approximate pseudo-real-time, not historical availability evidence.

Stored processed monthly flows and 12-month log growth were recomputed without changing data; numerical results compared to the master. Derived non-gold flow was checked against both de-cumulated parents. Detailed audit includes flags, selectors, retrieval spans and verification results. Current dataset-update timestamps cannot date past first releases.

## 10. Phase 5C evidence for CBU-related variables

The diagnostic CSV preserves each available model/horizon/lag-mode/evidence-class matched relative RMSE, frozen gate, stability and forecast count. No pooled score replaces matched comparisons.

| variable_key | observed_months_since_2018 | missingness_since_2018 | eligibility | eligibility_reason |
| --- | --- | --- | --- | --- |
| construction | 56 | 0.4666666666666667 | ELIGIBLE_SECONDARY | usable_but_short_proxy_or_ragged_history |
| exports_non_gold | 56 | 0.4666666666666667 | ELIGIBLE_SECONDARY | usable_but_short_proxy_or_ragged_history |
| imports_total | 56 | 0.4666666666666667 | ELIGIBLE_SECONDARY | usable_but_short_proxy_or_ragged_history |
| industrial_production | 79 | 0.2476190476190476 | ELIGIBLE_SECONDARY | usable_but_short_proxy_or_ragged_history |
| instant_payments | 15 | 0.8571428571428572 | DIAGNOSTIC_ONLY | short_or_failed_release_history |
| interbank_payments | 7 | 0.9333333333333332 | DIAGNOSTIC_ONLY | short_or_failed_release_history |
| pos_turnover | 20 | 0.8095238095238095 | DIAGNOSTIC_ONLY | short_or_failed_release_history |
| retail_trade | 68 | 0.3523809523809523 | ELIGIBLE_SECONDARY | usable_but_short_proxy_or_ragged_history |

Construction l3 shows pooled matched relative RMSE 0.735504 with just 3 forecasts, UNSTABLE and REJECT. This is insufficient evidence of reliable predictive value. Payments are DIAGNOSTIC_ONLY explicitly because of short/failed release history; activity and trade are ELIGIBLE_SECONDARY for short/proxy/ragged history. Coverage and instability can explain screening disadvantage, but their causal effect and latent predictive quality cannot be inferred. Frozen Phase5C industrial count is 79 versus current 80; preserve both. No REJECT becomes eligible for Phase5D.


Frozen univariate gate evidence (best pooled matched relative RMSE per candidate; descriptive only):

| Variable | Model | Matched relative RMSE | Forecast count | Stability | Gate |
| --- | --- | --- | --- | --- | --- |
| industrial_production | challenger_umidas_ind_prod_yoy_log_l1 | 3.275367 | 28 | UNSTABLE | RETAIN_FOR_RESEARCH |
| construction | challenger_umidas_construction_yoy_log_l3 | 0.735504 | 3 | UNSTABLE | REJECT |
| retail_trade | challenger_umidas_retail_yoy_log_l1 | 2.294423 | 17 | UNSTABLE | REJECT |
| pos_turnover | Not estimated | unavailable | unavailable | unavailable | NOT_ESTIMATED |
| instant_payments | Not estimated | unavailable | unavailable | unavailable | NOT_ESTIMATED |
| interbank_payments | Not estimated | unavailable | unavailable | unavailable | NOT_ESTIMATED |
| exports_non_gold | challenger_umidas_exports_non_gold_yoy_log_l3 | 1.551574 | 3 | UNSTABLE | REJECT |
| imports_total | challenger_umidas_imports_total_yoy_log_l3 | 0.741168 | 3 | UNSTABLE | REJECT |

## 11. Missing indicators

Services output, exact classified trade/paid-services receipts and job-search activity are missing. Exact non-gold exports is also missing despite an available proxy. Sparse payment archives and pre-2020/2021 comparable activity/trade histories are coverage gaps.

## 12. Proposed data extensions

| indicator | priority | expected_historical_coverage | collection_plan |
| --- | --- | --- | --- |
| services_output | HIGH_PRIORITY | Desired 2017 onward for 2018 YoY; unverified | Identify exact national selector and CBU definition before collection; do not use CPI services. |
| trade_paid_services_receipts | HIGH_PRIORITY | Desired 2017 onward; unverified | Locate original CBU study definition and receipt classification; POS is a limited proxy. |
| job_search_activity | HIGH_PRIORITY | Desired 2018 onward; unverified | Establish source/terms and fixed retrieval protocol; an official job-vacancy series would be a different concept. |
| pos_turnover | HIGH_PRIORITY | Registry claims 2018 onward; stored raw begins 2018-12; clean sparse | Fill archive gaps, verify schema/unit changes and January resets; retain cashless-adoption break. |
| exports_non_gold | HIGH_PRIORITY | Current parents start 2021; desired 2017 onward unverified | Replace conceptual ambiguity only through deliberate registry amendment; HS71 is not automatically pure gold. |
| construction;retail_trade;imports_total;industrial_production | MEDIUM_PRIORITY | Current raw starts 2019/2020/2021; desired pre-2018 unverified | Prior extension audit flags industrial classification and retail coverage breaks; no automatic splicing. |
| instant_payments | MEDIUM_PRIORITY | 2021 onward only; cannot cover 2018 system prehistory | Fill gaps for a later-sample extension, preserve adoption trends. |
| interbank_payments | LOW_PRIORITY | Registry 2018 onward; very sparse clean history | Weak receipt correspondence; inspect archive/schema transitions before collection. |

All source candidates are repository-grounded landing pages, not verified new endpoints. Unknown coverage, release lag and vintage availability remain unknown. Obtain the original paper and exact indicator definitions first; preserve official source priority, immutable raw files and source vintages during a later authorized collection phase.

## 13. Recommended Phase 6A.2 variable universe

Conditional core: industrial_production, construction, retail_trade, imports_total. Conditional proxy extensions: exports_non_gold and POS after archive repair. Optional later-sample extension: instant_payments. Exclude uncollected services/job-search and interbank from current 6A.2 inputs. GDP stays quarterly. Dense existing core has 56 common months, January 2022–August 2026; this is not a sufficient claim of usable forecast origins after training. No audited CBU candidate provides a continuous clean 2018/2019–2026 backtest. Construction/trade force 2022; retail 2021; payment proxies additionally impose large holes rather than merely a later start. A full CBU replication is not ready.

## 14. Risks and limitations

Supply is strongest by breadth (two mapped activity concepts, longest industry history); Consumption has highest joint populated coverage (68/105), followed by Supply candidates (56/105) and External (56/105). Labour is weakest (zero); Payments weakest populated block. Different definitions of strength are explicitly separated. Services absence means Supply is incomplete. Short quarterly target, nominal effects, latest-vintage revisions, missing true release histories, proxy contamination and payment adoption limit replication. Repository historical-extension claims are existing evidence, not newly verified external facts.

- pos_turnover: 58 internal missing clean months
- instant_payments: 39 internal missing clean months
- interbank_payments: 63 internal missing clean months
- Ingestion settings V1.1 differ from research loader V1.2; authoritative audit registry resolved from load_dataset signature.
- Industrial current master ends August 2026; frozen Phase5C and registry end July 2026.
- Panel union ends October 2026, beyond audit date; evaluation window capped at September 2026.
- CBU framework supplied by user; original 2023 study not present/independently verified.
- Historical source update dates and archive-date proxies are not first-release vintages.
- Candidate collection sources are unverified landing pages, not fabricated dataset endpoints.

## 15. Final Phase 6A.1 conclusion

Four of eight concepts have direct repository counterparts, subject to nominal/volume and short-history qualifications; none is a strict independently confirmed paper EXACT_MATCH. Two additional concepts have proxies; services and labour are missing. Three exact concepts are AVAILABLE_BUT_SHORT. No audited candidate fully supports a continuous 2018/2019–2026 clean backtest. Collect/verify high-priority services, classified receipts, original search protocol, exact gold exclusion and POS gaps before full Phase6A.2. Frozen gates remain industrial RETAIN_FOR_RESEARCH; construction, retail, imports and non-gold exports REJECT; payment candidates NOT_ESTIMATED. Production and Phase5D hashes must remain unchanged. Next action: **COLLECT_MISSING_HIGH_PRIORITY_DATA_FIRST**. No automatic estimation.

Verification: unchanged full repository pytest suite **PASSED** (exit 0). Sandbox attempts had Windows temporary-directory ACL errors; the full suite passed outside the sandbox. All 132 protected artifacts and 303 source-input hashes are unchanged. All transformation/master consistency checks passed. Test temporary directories removed. No reusable audit code retained, so no new unit tests required.
