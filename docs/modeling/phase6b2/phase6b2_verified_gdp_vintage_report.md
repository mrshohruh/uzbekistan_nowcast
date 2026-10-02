# Phase 6B.2 — verified GDP publication and vintage research

**Final classification: PHASE6B2_RELEASE_HISTORY_INCOMPLETE. Research only; no promotion.**

The isolated reconstruction contains all 34 registry quarters, with **24 earliest recovered official first-release dates and values**, and **103 documented publication events**. Ten early first releases remain unresolved. The accessor uses the latest *documented* eligible vintage; it does not certify that every intervening revision has been recovered. These results improve the information boundary but are **not an exhaustive real-time vintage backtest**.

The frozen GDP target remains cumulative year-to-date real YoY growth, with published volume indices converted by subtracting 100. GDP remains quarterly. Monthly panels, release masks, scaling, the one-factor AR(1) DFM with diagonal white-noise errors, the USD U-MIDAS specification and its minimum 15 effective observations, and all 50/50 weights remain unchanged.

## Official evidence and unresolved history

87 archived official source responses have URL, raw file, retrieval time, HTTP status and SHA256 provenance in [source inventory](../../../results/research/phase6b2/phase6b2_gdp_release_sources.csv). Search results were used to locate sources; the ledger uses downloaded official pages and PDFs. Dated landing pages must embed the actual report bytes; similar reports at different URLs are not assumed to be the same vintage. Printed PDF release dates are recorded separately from landing-page dates. Website sidebar timestamps and current SIAT dataset updates are not historical quarter releases.

The requested examples were checked independently. Several earliest recoverable releases precede the supplied summary articles:

| quarter | supplied_example | earliest_verified_publication | first_value | current_master | official_evidence |
| --- | --- | --- | --- | --- | --- |
| 2023Q4 | 2024-01-26 | 2024-01-26 | 6.0000 | 6.3000 | [2023Q4 source](https://stat.uz/en/press-center/news-of-committee/50023-skol-ko-sostavil-valovoj-vnutrennij-produkt-respubliki-uzbekistan-za-2023-god) |
| 2024Q1 | 2024-04-30 | 2024-04-25 | 6.2000 | 6.4000 | [2024Q1 source](https://stat.uz/img/02_-vvp_press-reliz-2024-yanvar-mart_eng_p68893.pdf) |
| 2024Q2 | 2024-07-24 | 2024-07-24 | 6.4000 | 6.6000 | [2024Q2 source](https://stat.uz/en/press-center/news-of-committee/55357-2024-yilning-yanvar-iyun-oylarida-o-zbekiston-respulikasi-yaimi-qanchani-tashkil-etdi-3) |
| 2024Q3 | 2024-10-25 | 2024-10-25 | 6.6000 | 6.6000 | [2024Q3 source](https://stat.uz/img/press-relizlar/yalpi-ichki-mahsulot_25_10_2024_ang_p80808.pdf) |
| 2024Q4 | 2025-01-27 | 2025-01-24 | 6.5000 | 6.7000 | [2024Q4 source](https://stat.uz/img/03_-vvp_press-reliz-2024_ang_p76737.pdf) |
| 2025Q2 | 2025-07-28 | 2025-07-28 | 7.2000 | 7.2000 | [2025Q2 source](https://stat.uz/img/press-relizlar/analitika-vvp_eng_p13982.pdf) |
| 2025Q3 | 2025-10-27 | 2025-10-27 | 7.6000 | 7.6000 | [2025Q3 source](https://stat.uz/en/press-center/news-of-committee/64794-zbekiston-yalpi-ichki-ma-suloti-azhmi-7-6-foizga-sdi-4) |
| 2025Q4 | 2026-01-26 | 2026-01-26 | 7.7000 | 7.7000 | [2025Q4 source](https://stat.uz/img/news/analitika-vvp_eng_p32560.pdf) |
| 2026Q1 | 2026-04-27 | 2026-04-27 | 8.7000 | 8.7000 | [2026Q1 source](https://stat.uz/img/news/analitika-vvp_eng_p57021.pdf) |
| 2026Q2 | 2026-07-31 | 2026-07-30 | 8.5000 | 8.5000 | [2026Q2 source](https://stat.uz/img/press-relizlar/analitika-vvp_eng_p39366.pdf) |

The unresolved first releases are **2018Q1–2019Q4 and 2020Q1–2020Q2**. Official annual catalogues contain several undated preliminary reports, but neither their filenames, PDF creation metadata, current upload dates nor typical lags prove historical publication. The catalogue's 2018 Q2 GDP link returns HTTP 404; the failed response is archived. These quarters retain null first-release fields, not invented dates or current-master first values. Later dated reports provide usable historical values for many of them. **2018Q1 and 2018Q2 have no eligible documented vintage in the evaluation origins and are excluded from training.**

Revision coverage is also partial: old quarters are republished in later quarterly reports, but the dates on which every intervening revision first became public are not established. Publication-event dates therefore mean “this value is verifiably published by this date,” not “this is the exact original revision date.” The accessor never uses a later document early. It can retain an older documented value where a missing intermediate revision may have existed.

The 2024 Q1 report prints historical chart labels for 2020 and 2021 in an order inconsistent with the preceding report. Both observations remain in the evidence ledger as **SOURCE_CHART_ORDER_SUSPECT** and are excluded from the accessor; they are neither silently swapped nor treated as verified usable revisions. Previous documented vintages remain available. This is another reason the archive cannot support a complete-history classification.

## Timing and vintage access

The frozen forecast origin is the month-end calendar date at 00:00 Asia/Tashkent. Known official clock times must strictly precede that cutoff. Date-only releases on that date are SAME_DAY_TIME_UNKNOWN: STRICT excludes them and PERMISSIVE_END_OF_DAY includes them. Both rules were run independently of accuracy. There are **0 same-day unknown records** in the 60 evaluated origins; consequently both timing-rule forecasts are identical. The earlier April 25, 2024 release removes the apparent April 30 same-day issue.

Of Phase 6B.1's 20 excluded H1 records (10 quarters × 2 monthly-lag modes), **20 are restored**, **0 are genuinely unavailable**, and **0 have same-day ambiguity**, using the recovered official prior-quarter dates. Counts do not imply that the ten unresolved early releases were verified.

The [accessor](../../../scripts/research/phase6b2/vintages.py) excludes target and future quarters, selects the latest eligible documented event, preserves publication URL/checksum/value provenance, rejects duplicate events and rejects substituted revised values. Unknown dated evidence is never filled from the master. [Training vintage usage](../../../results/research/phase6b2/phase6b2_GDP_training_vintage_usage.csv) records every returned GDP observation at each origin.

**16 of the 24 verified first-release observations differ from the current master.** Across the origin training sets, **25 distinct GDP quarters** have documented available values differing from the master. **4 of the 10 distinct immediate prior-quarter GDP values** differ:

| prior_quarter | prior_GDP_first_release_value | prior_GDP_vintage_value | prior_GDP_current_value | changed |
| --- | --- | --- | --- | --- |
| 2023Q4 | 6.0000 | 6.0000 | 6.3000 | True |
| 2024Q1 | 6.2000 | 6.2000 | 6.4000 | True |
| 2024Q2 | 6.4000 | 6.4000 | 6.6000 | True |
| 2024Q3 | 6.6000 | 6.6000 | 6.6000 | False |
| 2024Q4 | 6.5000 | 6.5000 | 6.7000 | True |
| 2025Q1 | 6.8000 | 6.8000 | 6.8000 | False |
| 2025Q2 | 7.2000 | 7.2000 | 7.2000 | False |
| 2025Q3 | 7.6000 | 7.6000 | 7.6000 | False |
| 2025Q4 | 7.7000 | 7.7000 | 7.7000 | False |
| 2026Q1 | 8.7000 | 8.7000 | 8.7000 | False |

## Matched accuracy: primary first-release targets

Every model has 30 matched origins per monthly-lag mode and timing rule: 10 H1, 10 H2 and 10 H3. Development comprises 2024Q1–2025Q2 (18 origins); the historical post-development test comprises 2025Q3–2026Q2 (12 origins). Both lag modes together give 60 matched origins per timing rule. There are eight forecasts at each origin. Rules are sensitivities, not extra independent observations.

The primary diagnostic is FIRST_RELEASE; LATEST_REVISED is a separate secondary diagnostic. Errors and bias are actual minus forecast. The following standard-lag, strict-rule table uses identical origins for all models:

| model | n_forecasts_pooled | rmse_pooled | mae_pooled | bias_pooled | n_forecasts_post | rmse_post | mae_post | bias_post |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| COMBO_B | 30 | 0.4875 | 0.3552 | 0.2803 | 12 | 0.6846 | 0.5327 | 0.4851 |
| DFM_B | 30 | 0.6471 | 0.4969 | 0.3972 | 12 | 0.9241 | 0.8509 | 0.8509 |
| PRODUCTION_ENSEMBLE | 30 | 0.5469 | 0.4222 | 0.3772 | 12 | 0.7006 | 0.4908 | 0.4357 |
| UMIDAS_USD | 30 | 0.5694 | 0.4356 | 0.1634 | 12 | 0.6861 | 0.5585 | 0.1194 |

The combination beats U-MIDAS and the production ensemble in the pooled documented-vintage sample. Standalone DFM B does **not** beat U-MIDAS pooled or post-development. It does beat U-MIDAS on these development subsets:

| evaluation_group | horizon | n_forecasts_dfm | rmse_dfm | rmse_usd |
| --- | --- | --- | --- | --- |
| DEVELOPMENT_PSEUDO_OOS | H1 | 6 | 0.2801 | 0.3748 |
| DEVELOPMENT_PSEUDO_OOS | H2 | 6 | 0.3129 | 0.4358 |
| DEVELOPMENT_PSEUDO_OOS | H3 | 6 | 0.4572 | 0.5906 |
| DEVELOPMENT_PSEUDO_OOS | ALL | 18 | 0.3584 | 0.4758 |
| DEVELOPMENT_PSEUDO_OOS | H2_H3 | 12 | 0.3918 | 0.5190 |

These are matched *documented-vintage* comparisons. No sample can be certified as using the exhaustive actual GDP vintage history while the identified gaps remain.

The four post-development quarters weaken the combination result: its all-horizon RMSE is 0.6846 versus U-MIDAS 0.6861, a difference of only about 0.0015. On post-development H2/H3, the combination RMSE is 0.6325 versus U-MIDAS 0.6129, so the combination loses there. Post-development FIRST_RELEASE and LATEST_REVISED scores coincide because these four target growth values are unchanged in the master.

Complete pre-specified combination diagnostics for the primary standard/strict result:

| evaluation_group | horizon | n_forecasts | rmse | mae | bias |
| --- | --- | --- | --- | --- | --- |
| DEVELOPMENT_PSEUDO_OOS | H1 | 6 | 0.2980 | 0.2401 | 0.2401 |
| DEVELOPMENT_PSEUDO_OOS | H2 | 6 | 0.3117 | 0.2510 | 0.2202 |
| DEVELOPMENT_PSEUDO_OOS | H3 | 6 | 0.2550 | 0.2194 | -0.0291 |
| DEVELOPMENT_PSEUDO_OOS | ALL | 18 | 0.2892 | 0.2369 | 0.1437 |
| DEVELOPMENT_PSEUDO_OOS | H2_H3 | 12 | 0.2848 | 0.2352 | 0.0956 |
| HISTORICAL_POST_DEVELOPMENT_TEST | H1 | 4 | 0.7785 | 0.6546 | 0.5663 |
| HISTORICAL_POST_DEVELOPMENT_TEST | H2 | 4 | 0.7750 | 0.6007 | 0.5463 |
| HISTORICAL_POST_DEVELOPMENT_TEST | H3 | 4 | 0.4466 | 0.3428 | 0.3428 |
| HISTORICAL_POST_DEVELOPMENT_TEST | ALL | 12 | 0.6846 | 0.5327 | 0.4851 |
| HISTORICAL_POST_DEVELOPMENT_TEST | H2_H3 | 8 | 0.6325 | 0.4717 | 0.4445 |
| POOLED_RESEARCH_ONLY | H1 | 10 | 0.5438 | 0.4059 | 0.3706 |
| POOLED_RESEARCH_ONLY | H2 | 10 | 0.5464 | 0.3909 | 0.3506 |
| POOLED_RESEARCH_ONLY | H3 | 10 | 0.3447 | 0.2688 | 0.1197 |
| POOLED_RESEARCH_ONLY | ALL | 30 | 0.4875 | 0.3552 | 0.2803 |
| POOLED_RESEARCH_ONLY | H2_H3 | 20 | 0.4568 | 0.3298 | 0.2351 |

## Separate latest-revised targets and prior-phase comparisons

The old 0.4754 Phase 6B.1 standard pooled H2/H3 combination RMSE becomes **0.4727** on the same 20 origins with latest-revised targets and documented GDP training vintages. The primary first-release equivalent is **0.4568**. The approximate numerical improvement survives this partial-archive sensitivity, but neither number establishes a verified complete-history result.

Restoring H1 gives latest-revised all-horizon combination RMSE 0.5072 over 30 origins; the primary first-release score is 0.4875. The frozen original all-horizon combination score was about 0.5054. These 30-origin scores must not be compared with the 20-origin Phase 6B.1 pooled score as if coverage were identical.

For the three-phase numeric comparison below, **every model uses the exact common H2/H3 origins across all three phases**, and latest-revised actuals stay fixed. Historical predictions are read from frozen files and scored only in new Phase 6B.2 comparison outputs; the earlier records are not rewritten. The original and fallback phases are historical references with their original information limitations, not verified-vintage results.

| phase | model | n_forecasts | rmse | mae |
| --- | --- | --- | --- | --- |
| PHASE6B | COMBO_B | 20 | 0.4754 | 0.3533 |
| PHASE6B | DFM_B | 20 | 0.6299 | 0.4639 |
| PHASE6B | PRODUCTION_ENSEMBLE | 20 | 0.5559 | 0.4274 |
| PHASE6B | UMIDAS_USD | 20 | 0.6156 | 0.4874 |
| PHASE6B1 | COMBO_B | 20 | 0.4754 | 0.3533 |
| PHASE6B1 | DFM_B | 20 | 0.6299 | 0.4639 |
| PHASE6B1 | PRODUCTION_ENSEMBLE | 20 | 0.5559 | 0.4274 |
| PHASE6B1 | UMIDAS_USD | 20 | 0.6156 | 0.4874 |
| PHASE6B2 | COMBO_B | 20 | 0.4727 | 0.3606 |
| PHASE6B2 | DFM_B | 20 | 0.6416 | 0.5221 |
| PHASE6B2 | PRODUCTION_ENSEMBLE | 20 | 0.5636 | 0.4540 |
| PHASE6B2 | UMIDAS_USD | 20 | 0.5970 | 0.4728 |

[Forecast-level attribution](../../../results/research/phase6b2/phase6b2_phase6b1_comparison.csv) separates: (1) restoring verified release timing while explicitly retaining the 46-day fallback for unresolved early dates; (2) removing master values on quarters without documented historical support; and (3) replacing remaining master values with eligible published vintages. Counterfactual master-value forecasts are explicitly invalid-value diagnostics and never enter primary metrics. H1 has no fallback forecast, so restoration is reported as availability, not a fabricated numeric difference.

## Complementarity and leave-one-quarter-out checks

DFM B and U-MIDAS forecast-error correlations are:

| evaluation_group | n | dfm_b_umidas_error_correlation |
| --- | --- | --- |
| DEVELOPMENT_PSEUDO_OOS | 18 | -0.1888 |
| HISTORICAL_POST_DEVELOPMENT_TEST | 12 | 0.7120 |
| POOLED_RESEARCH_ONLY | 30 | 0.1401 |

The low pooled correlation is consistent with useful pooled complementarity. The much higher post-development correlation and nearly tied post-development RMSE limit that interpretation.

Leaving out one target quarter, while retaining the fixed model specifications and 50/50 forecasts, the pooled combination beats U-MIDAS in **10/10** omissions and production in **10/10** omissions. For the four-quarter post-development sample, it beats U-MIDAS in **3/4** and production in **3/4** omissions. These are evaluation sensitivities, not refitted model weights. No optimal combination weight was estimated.

| omitted_target_quarter | COMBO_B | DFM_B | PRODUCTION_ENSEMBLE | UMIDAS_USD |
| --- | --- | --- | --- | --- |
| 2024Q1 | 0.5089 | 0.6539 | 0.5677 | 0.5941 |
| 2024Q2 | 0.5059 | 0.6817 | 0.5580 | 0.5782 |
| 2024Q3 | 0.5127 | 0.6775 | 0.5715 | 0.6001 |
| 2024Q4 | 0.5136 | 0.6820 | 0.5734 | 0.5985 |
| 2025Q1 | 0.5011 | 0.6779 | 0.5381 | 0.5784 |
| 2025Q2 | 0.4859 | 0.6555 | 0.5486 | 0.5198 |
| 2025Q3 | 0.4895 | 0.6401 | 0.5540 | 0.5815 |
| 2025Q4 | 0.5121 | 0.6533 | 0.5744 | 0.5446 |
| 2026Q1 | 0.3185 | 0.4742 | 0.3796 | 0.4921 |
| 2026Q2 | 0.4948 | 0.6480 | 0.5745 | 0.5956 |

| omitted_target_quarter | COMBO_B | DFM_B | PRODUCTION_ENSEMBLE | UMIDAS_USD |
| --- | --- | --- | --- | --- |
| 2025Q3 | 0.7426 | 0.9861 | 0.7605 | 0.7494 |
| 2025Q4 | 0.7870 | 1.0116 | 0.8046 | 0.6610 |
| 2026Q1 | 0.3701 | 0.6462 | 0.2996 | 0.5231 |
| 2026Q2 | 0.7530 | 1.0014 | 0.8048 | 0.7818 |

## Verification, reproducibility and governance

All 60 DFM factor paths were re-estimated from the frozen monthly panel and core. Maximum absolute difference from Phase 6B is **4.99e-12**, below 1e-8. A second complete factor computation produced byte-identical factor outputs. Two final identical-input forecast/evidence runs produced byte-identical results for **19 CSV artifacts**.

Final tests: **161 passed, 0 failed** ({'repository_models': 101, 'phase6b': 17, 'phase6b1': 23, 'phase6b2': 20}). Initial test attempts encountered Windows temporary-folder restrictions and the older modules' shared bare `run.py` name; separate final processes resolved these without modifying frozen code. Model-suite fixture warnings about intentionally missing predictors remain expected. Tests cover release/value boundaries, revisions, target/future rejection, strict/permissive and observed-clock behavior, duplicates, exact matching, separate target definitions, factor identity, deterministic reruns, evidence checksums and protection.

All **592 protected files remain byte-identical** to the initial protection baseline. Production, registry, dashboards, Phase 5D, issued forecast history and Phase 4/5/6B/6B.1 artifacts remain unchanged. Only the three isolated Phase 6B.2 paths contain authored outputs.

Offline reproduction from the archived evidence:

```powershell
.venv/Scripts/python.exe scripts/research/phase6b2/factors.py
.venv/Scripts/python.exe scripts/research/phase6b2/run.py
.venv/Scripts/python.exe scripts/research/phase6b2/verify.py
.venv/Scripts/python.exe -m pytest scripts/research/phase6b2/test_vintages.py -q -o addopts='' -p no:cacheprovider --basetemp results/research/phase6b2/test_tmp_new_verified > results/research/phase6b2/phase6b2_new_tests_verified.log 2>&1
.venv/Scripts/python.exe scripts/research/phase6b2/report.py
```

Evidence parsers are pinned in `scripts/research/phase6b2/requirements-research.txt`; exact model and parser environment versions are recorded in the run manifest. Collection is cached, rate-limited and bounded; failed sources remain visible. Tests for Phase 6B, 6B.1 and 6B.2 must run in separate processes because those older research modules use shared bare import names.

Required artifacts: [vintage registry](../../../results/research/phase6b2/phase6b2_gdp_vintage_registry.csv), [source inventory](../../../results/research/phase6b2/phase6b2_gdp_release_sources.csv), [revision events](../../../results/research/phase6b2/phase6b2_gdp_revision_history.csv), [origin audit](../../../results/research/phase6b2/phase6b2_origin_information_audit.csv), [benchmarks](../../../results/research/phase6b2/phase6b2_clean_benchmark_forecasts.csv), [DFM forecasts](../../../results/research/phase6b2/phase6b2_dfm_forecasts.csv), [combinations](../../../results/research/phase6b2/phase6b2_combination_forecasts.csv), [matched forecasts](../../../results/research/phase6b2/phase6b2_matched_forecasts.csv), [metrics](../../../results/research/phase6b2/phase6b2_horizon_metrics.csv), [quarter errors](../../../results/research/phase6b2/phase6b2_quarter_level_errors.csv), [leave-one-quarter-out](../../../results/research/phase6b2/phase6b2_leave_one_quarter_out.csv), [prior-phase comparison](../../../results/research/phase6b2/phase6b2_phase6b1_comparison.csv), and [manifest](../../../results/research/phase6b2/phase6b2_run_manifest.json).

**Stop at Phase 6B.2.** No Phase 6C, model promotion, production change or dashboard replacement was performed. The unresolved early first releases, incomplete intermediate revisions and flagged source ambiguity determine the final RELEASE_HISTORY_INCOMPLETE classification, regardless of favorable pooled RMSE.
