"""Render the final report and required terminal summary from audited outputs."""
import json,re,sys
from pathlib import Path
import pandas as pd
from recovery import ROOT,OUT,sha
from build import protection,KEYS

def value(v):return 'NONE' if pd.isna(v) else str(v)

def main():
 sys.stdout.reconfigure(encoding='utf-8')
 status=pd.read_csv(OUT/'phase6a2_collection_status.csv').set_index('variable_key')
 common=pd.read_csv(OUT/'phase6a2_common_sample_audit.csv').set_index('sample')
 manifest=json.loads((OUT/'phase6a2_run_manifest.json').read_text())
 failures=json.loads((OUT/'stat_parse_failures.json').read_text(encoding='utf-8'))
 raw=(OUT/'repository_tests.txt').read_bytes();testtext=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
 match=re.search(r'(\d+) passed(?:, (\d+) failed)?',testtext)
 if not match:raise ValueError('Repository test result missing')
 passed=int(match.group(1));failed=int(match.group(2) or 0)
 if failed:raise ValueError('Repository tests failed')
 raw=(OUT/'research_tests.txt').read_bytes();researchtext=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
 if not re.search(r'15 passed',researchtext) or re.search(r'\d+ failed',researchtext):raise ValueError('Final research test result is not 15 passed / zero failed')
 counts={stage:sum(r['stage']==stage for r in failures) for stage in ['download','parse']}
 labels=['Industrial production','Construction','Services output','Retail trade','Trade and paid-services receipts','POS turnover','Exports excluding gold','Imports','Job-search activity']
 coverage='| Indicator | Classification | Published observations | Coverage | Missing on 2018-01–2026-08 grid |\n|---|---|---:|---|---:|\n'
 for key,label in zip(KEYS,labels):
  r=status.loc[key];coverage+=f'| {label} | {r.classification} | {r.observation_count} | {value(r.start_month)}–{value(r.end_month)} | {r.missing_month_count} |\n'
 samples='| Set | Common span | Joint months | Longest continuous block | Missing on 104-month grid | Complete GDP quarters | Conditional calendar forecast quarters |\n|---|---|---:|---|---:|---:|---:|\n'
 for name,r in common.iterrows():samples+=f'| {name} | {value(r.common_start)}–{value(r.common_end)} | {r.common_month_count} | {value(r.longest_continuous_start)}–{value(r.longest_continuous_end)} ({r.continuous_months}) | {r.missing_months} | {r.quarterly_gdp_reference_count} | {r.potential_quarterly_forecast_origin_count_after_12_training_quarters} |\n'
 paper='https://cbu.uz/upload/iblock/3d6/6kbvfiumraqdb4ejh0qrzkc6y4pbr3vi/MIDAS_WP.pdf'
 report=f'''# Phase 6A.2 — Public data recovery and CBU dataset reconstruction

Decision: **COLLECT_MORE_DATA**. A separate research panel and every required audit output were created. Full original-paper replication is **NOT READY**. A 2018–2026 backtest is **PARTIAL**: substantial public history is recoverable, but the defensible CORE-4 portion starts in January 2021. No forecasting model was implemented or estimated.

## Original paper and definition contract

The official [CBU working paper]({paper}) was located and archived, together with its [publication page](https://cbu.uz/ru/research/economic/2525870/) and [publication index](https://cbu.uz/ru/research/economic/). Its Russian title is *Краткосрочное прогнозирование ВВП с помощью MIDAS-модели*. Author: **Ruslan Yakovlev**, Monetary Policy Department. The index dates publication to **30 November 2023**; the landing page's June 2025 update is not the publication date. The exact stated monthly sample is **January 2018–October 2023**.

Pages 5–6 identify industrial production, construction, services, retail, trade/paid-services receipts, exports without gold, imports and monthly job-search queries. The paper describes the displayed data as **real cumulative year-on-year growth**. This differs from the repository's nominal de-cumulated monthly log-growth predictors. Published physical-volume/growth indices are therefore preserved directly, with index minus 100 stored as percentage-point growth; those indices are never de-cumulated.

The target is real GDP growth, with the Q4 exercise interpreted as annual GDP growth. The exact construction of standalone quarterly versus YTD GDP is not specified; the existing quarterly GDP target was neither changed nor converted to monthly frequency. Named comparisons are AR(1), arithmetic mean of three months, Almon MIDAS, U-MIDAS, MIDAS-GETS and MIDAS-GETSIS. Empirical lag counts, precise deflators, underlying selector IDs, search basket, normalization and aggregation rules remain **NOT_SPECIFIED_IN_ORIGINAL_PAPER**. None was invented. The definition CSV records these omissions explicitly.

## Recovered coverage

{coverage}

Counts refer to the retained published measurement: real published growth for activity, nominal YTD levels for imports/POS/no-gold exports, and direct nominal monthly receipts. These are **not counts of comparable transformed predictors or historical first releases**. Missing counts use a fixed 104-month January 2018–August 2026 grid; the coverage CSV also reports internal gaps and longest continuous blocks.

### Services

Official 2018–2023 Statistics Agency monthly service releases provide national market-services values and comparable-price growth. SIAT **3215** supplies national nominal market-services levels and **3216** physical-volume growth for January 2024–August 2026. Exact selector: **Code=1700 AND Klassifikator_en=Republic of Uzbekistan**. This is services output, not services CPI.

All **104 months** were recovered. The March 2019 PDF has overlaid text/column extraction; its national volume and growth were cross-checked against the explicit national headline and table. Nominal YTD units are billion soums; real growth uses previous-year=100. Monthly releases describe January-to-report-month accumulated volumes. The paper is closer to the real comparable-price growth concept than nominal turnover. SIAT metadata states that informal/hidden-economy survey activity is included from **September 2024**. A complete calendar grid does not establish comparable cross-regime growth. The panel includes an explicit services regime field and separate nominal levels. Negative YTD increments and the September boundary are withheld from nominal monthly-flow transformations. Most historical PDF months use different retrospective snapshots, so adjacent nominal flows are withheld rather than mixing revisions. Published real growth remains usable as a separately documented candidate.

### POS history and revisions

The 94 inspected monthly archive releases alone had gaps. Official **2018 and 2019 annual bulletins** and **Table 6.4 in the March 2026 XLSX bulletin** fill the historical gaps. Their amount column is in **billion UZS**, converted by **×1000** to the monthly payment archive's **million UZS**. Table 6.4 explicitly says **since the beginning of the year**. First-of-month as-of dates describe transactions through the preceding month, so 1 April describes January–March, not April. Stocks of terminals/cards are never treated as transaction flows.

The raw archive also contains 2017 observations; the main panel starts in January 2018. POS levels are complete through **July 2026**, with August unresolved. A single internally consistent bulletin vintage is preferred within each historical year. The 2024 December YTD amount in the December 2024 bulletin differs from the revised March 2026 bulletin and monthly archive. Both raw vintages remain intact; the selected amount is audited in the overlap CSV. January resets, duplicate sources, annual totals, extreme changes and source differences are recorded.

The December 2025 Uzbek payment article labels its January–December turnover **POS (E-POS)**. Equivalence to the earlier reporting universe and the actual start date are unresolved. January 2025 is a conservative marker for the reported YTD window, **not an invented launch date**. Post-2024 POS YoY transformations are withheld pending scope verification. April–July 2026 YTD snapshots are retained, but monthly differences are withheld where a single internally consistent vintage is unavailable. POS is an optional proxy and is not an original-paper conceptual variable.

### Trade and paid-services receipts

Official CBU cash-circulation reviews, monetary-policy decisions and bulletin annexes were searched. The [2022 annual review](https://cbu.uz/ru/press_center/reviews/847782/) confirms the identity **259.0 trillion UZS total = 162.7 cash + 96.3 classified terminal receipts**. This differs from total POS turnover. It is annual evidence only and is never interpolated into months.

The [September 2020 policy decision](https://cbu.uz/ru/press_center/news/403913/) explicitly reports monthly receipts of **12.6 trillion UZS in June 2020** and **11.1 trillion in July 2020**. These two direct observations are retained. Its rounded August growth statement is not converted into an exact level. A full downloadable exact monthly total/components series and the paper's real deflator were not identified. Charts without exact recoverable labels are not digitized into invented observations. This remains the principal numeric-series collection gap.

### Exports excluding gold

Monthly official foreign-trade PDFs were archived through August 2026. Where a national total and an explicitly labelled **non-monetary gold, excluding gold ores and concentrates** row coexist, the research reconstruction is **total goods-and-services exports minus that row**, in million USD. Direct published “exports without gold” totals provide another candidate and a cross-check. This is separate from the unchanged registry `exports_non_gold` proxy. **Other goods and HS71 are never subtracted as gold.** Monetary-gold flows are not added to merchandise exports without official evidence.

The latest August 2026 release gives total exports **22,866.9 million USD**, non-monetary gold **2,803.8**, and the reconstruction **20,063.1**. Its separate headline about merchandise exports excluding gold is a **goods-only** concept and is not used as a goods-and-services cross-check. The table also says precious metals other than non-monetary gold are classified as non-ferrous metals; the effective methodology-change date is not supplied.

Five releases have conflicting direct no-gold and subtraction amounts: **March, April, November and December 2024, and January 2025**. Both versions are preserved under distinct mismatch-candidate keys and excluded from `exports_ex_gold_exact`. Older rows labelled only “Gold” remain scope-unknown candidates. The retained exact-scope nominal YTD reconstruction has **62 observations**, with genuine gaps. Its key denotes the verified excluded commodity scope, **not exact replication of the paper's real transformed predictor**. Different PDF vintages are not de-cumulated together; consequently most monthly-flow/log-growth cells remain missing. Further consistent-vintage annex recovery is required.

### Industrial production, construction, retail and imports

SIAT **577** supplies physical-volume industrial growth from January 2019, **2406** construction growth from January 2021, and **2700** retail growth from January 2020, all through August 2026. SIAT **556** is explicitly large-enterprise output, so it is retained as a separate candidate and rejected as an automatic national all-enterprise substitute. Archived 2018 industry and 2018–2020 construction/retail headlines are retained under distinct historical growth/nominal keys. Their real-volume/reporting-universe equivalence to revised SIAT remains unresolved; they are not silently spliced.

SIAT **2414** extends nominal imports to January 2020–August 2026. It is goods **and services**, not goods-only imports, and its USD YTD values allow within-vintage calendar-year de-cumulation. Strictly positive monthly flows allow separate percentage and log YoY growth from January 2021. Older official releases include tourism-survey recalculations of 2017/first-half 2018 and remain separate candidates. The December 2019 foreign-economic-activity annex was also recovered from the quarterly archive; annual/quarterly observations were not manufactured into monthly history. The original paper's real trade deflator is unspecified.

### Job-search methodology

The archived official [Q4 2025 CBU labour-market review](https://cbu.uz/upload/iblock/6d1/ztibodg8w0rorc8xp2dsn4xln5k0r6l1/Labor-Market-review-full-review_-_2_-_2_.pdf) identifies Google Trends as the source for its job-search index. Neither it nor the original paper discloses exact words/topics, Uzbek/Russian basket, geography protocol, category, search type, normalization or aggregation. Classification is **PUBLIC_SOURCE_CONFIRMED_QUERY_SPEC_UNKNOWN**. No unsupported keyword basket was downloaded or labelled a replication. That review also notes changing search behaviour toward apps/social networks in 2024–2025, requiring caution even if a protocol is later obtained.

## Common samples and forecast-origin limits

{samples}

CORE-4 has **68 continuous published-observation months**. CORE plus services has the same calendar coverage, but its longest block before crossing the documented services break is **January 2021–August 2024: 44 months**. CORE plus services plus exact-scope no-gold exports has a longest block of **33 months**, June 2021–February 2024. Full original and the seven-variable numeric set have zero joint complete months because the receipts months predate the retained construction history; removing job search alone does not solve that gap.

The GDP table has 34 quarterly observations, 2018Q1–2026Q2. Conditional calendar-origin counts require **12 consecutive complete training quarters** immediately before a complete target quarter. CORE-4/CORE plus services have 22 aligned quarterly references and an upper bound of **10 forecast quarters / 30 H1–H3 calendar origins** under an unspecified future availability design. The gold subset has **zero** origins under that consecutive-training requirement. These are calendar feasibility counts, not model results or certified usable backtest origins. **Historical first-release-verified origin count is zero; actual usable historical-origin count is undetermined.** No typical registry lag was presented as a first-release date. Real trade/receipt transformation and cumulative GDP target mapping must be resolved before a defensible paper comparison.

## Storage, provenance and validation

The separate panel is `data/research/phase6a2/cbu_midas_monthly_panel.csv` and `.parquet`, with one unique row per month and explicit real-growth, nominal YTD, raw-level, monthly-flow, percentage/log-growth, historical-candidate and registry-proxy columns. GDP is absent. No interpolation or missing-value filling occurs. The human-readable coverage matrix is `results/research/phase6a2/phase6a2_coverage_matrix.html`, with a matching CSV and month-by-indicator status audit. Duplicate-source cells reflect preserved overlapping releases, not duplicate panel dates; break cells are explicit boundaries.

The source inventory verifies **{manifest['raw_source_count']} source-file checksums**, including reused repository raw files. Every newly archived raw file maps to a verified source URL. Exact selectors, reference month, unit, cumulative definition, parser version/envelope, hash and retrieval timestamp are retained. Explicit printed release dates identify the observed publication vintage, not the first release of its historical observations. Source update dates, retrieval dates and publication dates remain separate. Unknown dates and assumed release lags are null.

An early concurrent collector logging race left 14 source records without their original log metadata. Those URL/retrieval records were recovered from exact SHA256 URL hashes, collector manifests and immutable timestamped filenames. Original unavailable HTTP headers remain null. New collectors write separate process logs. The limitation is recorded in the run manifest; no status or header was invented.

Statistics archive failures remain visible: **{counts['download']} download/read failures** (including dead links and malformed PDF streams) and **{counts['parse']} strict-selection/reference-period failures**. The failure JSON gives each source and stage. A file linked under 2018 describing 2017 is rejected rather than relabelled. Unmatched source tables remain archived for further recovery.

Quality outputs include raw duplicate/overlap comparisons, source-unit checks, expected YTD monotonicity, January resets, missing predecessor detection, positivity checks and extreme-change warnings. De-cumulation only uses adjacent months in the same year with the same unit and raw vintage. December-to-January subtraction is impossible. Algebraic reconciliation is recorded for accepted differences; incomplete/mixed-vintage years are not certified as annual reconciliations. The offline fixture tests cover exact national selection, overlaid PDFs, current-year gold columns, import/export gold separation, conflicting totals, calendar gaps and vintage/unit safeguards.

**Repository tests: {passed} passed, {failed} failed, 4 existing warnings. Research recovery tests: 15 passed, 0 failed.** No network calls occur in those new tests. Tests use isolated research temporary paths. Commands and pinned isolated reader requirements are in `scripts/research/phase6a2/README.md`.

**Protected verification: {len(manifest['protected_before'])} files unchanged; zero hash failures.** Production, Phase 5D prospective records, Phase 5C frozen gates/evidence, historical Phase 5 forecasts, canonical master, metadata and Phase 6A.1 inputs were not modified. No registry amendment, model estimation or promotion occurred.

## Next action

**COLLECT_MORE_DATA**. First recover the complete cash plus classified trade/service terminal-receipt history and internally consistent historical gold-export monthly annexes. Reconcile 2018–2020 real-activity candidates and the services/POS definition changes. Obtain an official job-query protocol and clarify the paper's real trade/receipt deflators and GDP target convention. The current panel is a documented research collection, not a silently substituted production dataset or a certified full-replication backtest.
'''
 path=ROOT/'docs/modeling/phase6a/phase6a2_data_recovery_report.md';path.write_text(report,encoding='utf-8')
 protection(manifest)
 manifest['test_results']={'repository':{'passed':passed,'failed':failed,'warnings':4},'research':{'passed':15,'failed':0}}
 manifest['protected_after']=protection(manifest)
 artifacts=[p for p in OUT.glob('phase6a2_*') if p.is_file() and p.name!='phase6a2_run_manifest.json' and not p.name.startswith('phase6a2_fetch_log')]
 artifacts+=[path,ROOT/'data/research/phase6a2/cbu_midas_monthly_panel.csv',ROOT/'data/research/phase6a2/cbu_midas_monthly_panel.parquet']
 artifacts+=list((ROOT/'scripts/research/phase6a2').glob('*.py'))
 manifest['output_hashes']={p.relative_to(ROOT).as_posix():sha(p) for p in artifacts}
 (OUT/'phase6a2_run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 lines=['PHASE 6A.2 COMPLETE','','Original CBU MIDAS paper:','FOUND','','Original paper sample:','2018-01 – 2023-10','']
 for key,label in zip(KEYS,labels):
  r=status.loc[key];lines.extend([label+':',r.classification,f'Coverage: {value(r.start_month)} – {value(r.end_month)}'])
  if key!='job_search_index':lines.append(f'Missing months: {r.missing_month_count}')
  else:lines.extend(['Exact CBU query specification:','NOT FOUND'])
  lines.append('')
 for name,label in [('FULL_ORIGINAL_CBU_INDICATOR_SET','Full CBU common sample'),('CORE_NUMERIC_OFFICIAL_DATA_SET','Core official-data common sample')]:
  r=common.loc[name];lines.extend([label+':',f'{value(r.common_start)} – {value(r.common_end)}',f'Continuous months: {r.continuous_months}',''])
 lines.extend(['2018–2026 backtest:','PARTIAL','','Full CBU replication:','NOT READY','','Research panel created:','YES','','Production modified:','NO','','Phase 5D modified:','NO','','Protected hash failures:','0','','Repository tests:','PASSED',f'Tests passed: {passed}',f'Tests failed: {failed}','','Next action:','COLLECT_MORE_DATA'])
 summary='\n'.join(lines);(OUT/'phase6a2_terminal_summary.txt').write_text(summary,encoding='utf-8');print(summary)

if __name__=='__main__':main()
