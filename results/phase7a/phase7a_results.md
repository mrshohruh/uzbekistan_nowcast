# Phase 7A electricity research

**PHASE7A_INSUFFICIENT_DATA**

Three directly reported monthly republic consumption observations were collected: June 2026 7707.9 GWh, July 8800 GWh, August 8400 GWh. Target coverage is 3/93 months (90 missing), with zero valid YoY pairs. No national monthly demand history back to 2019 was verified. This is a bounded public-source investigation, not proof that private or unindexed records do not exist.

SIAT 2684 is annual subscriber consumption, code 1.02.02.0019, in million kWh (= GWh), national series 2016-2025. Ten annual observations are archived separately; they are never distributed into months. The metadata note still describes 2023 as preliminary despite newer years, so year-specific revision status is unresolved. Its 2026-09-02 update is a dataset update, not each observation's first release. [Official SIAT](https://siat.stat.uz/data/2684/?lang=en).

The Ministry's [June release](https://gov.uz/oz/minenergy/news/view/190427), [July release](https://gov.uz/oz/minenergy/news/view/208274) and [August release](https://gov.uz/oz/minenergy/news/view/226468) distinguish consumption from generation. The exact system boundary (losses, own use, off-grid scope) remains undocumented in those articles. Publication-heading delays are [9, 19, 28] days. September 2026 consumption was not verified. Pages downloaded on 2026-10-12 do not confirm which numeric vintage existed at their heading dates: VINTAGE_UNVERIFIED.

January reports delivery to consumers; Jan-Mar delivery is 20163 GWh, whereas Jan-Apr republic consumption is 29517 GWh. No equivalence is documented, so April is not de-cumulated across this change. Jan-Aug minus Jan-Jul gives 8500 GWh, while reported August is 8400 GWh: rounding and/or revision compatibility cannot be resolved. Direct monthly figures are retained. Two 2024 household monthly figures and daily demand peaks are excluded. Generation is not substituted. HET annual delivery totals and SIAT subscriber consumption are separate measures.

Ember's full downloaded monthly file has 180933 rows and zero Uzbekistan/UZB rows. Its July 2026 format has Area, ISO 3 code, Date and Electricity source columns. [Ember source](https://ember-energy.org/data/monthly-electricity-data/). HET report PDFs and the national-grid archive index are archived; no complete monthly panel was verified. Local HET homepage/report retrieval failed; the ESG page and PDFs succeeded. Local IEA returned HTTP 403; its browser-readable country page does not establish monthly demand coverage. All retrieval results are in source_registry.csv, including failures.

## Evaluation decision

E1, E2 and C1 are NOT ESTIMABLE. Do not force a DFM with three levels and zero YoY inputs. Matched challenger origins: zero. Short-history M0 comparison, RMSE improvement, LOQO robustness, lag sensitivity, correlations with IP/manufacturing/utilities/M2, incremental factor signals and electricity loadings are all not estimable. No conclusion of no improvement is warranted. Existing baseline scores are copied and explicitly labelled FROZEN_BASELINE_ONLY, not results of an electricity experiment. Primary matched-sample challenger metrics remain null.

The existing one-factor AR(2) DFM with lagged-GDP bridge and U0 implementation were inspected in scripts/production/models.py. GDP remains published cumulative YTD real GDP YoY percent. No GDP release or target was downloaded. Model standardization, U0 predictors/coefficient fitting rules and 50/50 weights are unchanged. A future experiment must use training-only scaling, strict GDP vintages and observed electricity release vintages; an assumed lag belongs only in a separately labelled sensitivity experiment. No sensitivity forecast is generated without usable YoY history.

## Current references and cutoff

Frozen production cutoff 2026-10-05, post-H3 initialization. M0 8.301152885464585%; U0 8.060649795767965%; C0 **8.180901340616275%**. Latest collected consumption: August 2026, heading published 2026-09-28, retrieved 2026-10-12; not admitted as a confirmed historical vintage at the production cutoff. E1/C1 remain null and RESEARCH_ONLY.

Electricity is not suitable for operational use on this evidence. Promotion recommendation: defer until at least multi-year compatible monthly data, definition documentation and release archives are obtained. No production registry entry or protected scientific artifact was changed.

## Reproduction and artifacts

Offline build: `.venv/Scripts/python.exe -m scripts.phase7a.run`. Network collection: `.venv/Scripts/python.exe -m scripts.phase7a.collect`; every run creates a new immutable raw directory. The build validates stored checksums and schemas, and fails if new Ember Uzbekistan coverage requires review.

Production protection and independently recomputed current forecasts are recorded in run_manifest.json; test results are in phase7a_tests.log and phase7a_tests.xml. The local dashboard embeds all scripts and charts without external services.

Validation: 72 selected tests, 0 failures, 0 errors. Windows short-temp runner: `python -m scripts.phase7a.test_runner tests/production tests/models/test_phase6i.py tests/models/test_phase7a.py -k "not test_protected_artifacts_unchanged"`. The legacy whole-repository historical hash test is replaced by this run's 1951-file protection audit and existing seal tests. The initial superseded run had Windows temporary-directory setup errors. Current DFM, U0 and COMBO reproduced with exact float equality. Browser rendering was not verified; the dashboard passed static self-containment/data checks.

Generated artifacts:

- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\data\research\electricity\electricity_consumption_monthly.csv`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\data\research\electricity\electricity_subscriber_consumption_annual.csv`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\data\research\electricity\electricity_transformed_monthly.csv`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7a\electricity_data_audit.csv`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7a\electricity_data_coverage.csv`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7a\electricity_release_evidence.csv`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7a\electricity_separate_candidates.csv`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7a\phase7a_current_nowcasts.csv`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7a\phase7a_electricity_comparison.html`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7a\phase7a_factor_loadings.csv`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7a\phase7a_factor_signals.csv`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7a\phase7a_horizon_metrics.csv`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7a\phase7a_model_comparison.csv`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7a\source_registry.csv`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7a\phase7a_results.md`
- `C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7a\run_manifest.json`
