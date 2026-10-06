# Phase 6G.3 — GDP target audit and nominal challenger

PHASE6G3_TARGET_DEFINITION_ISSUE_FOUND

**Production remains unchanged.** The current real target is cumulative-period YTD real GDP YoY growth reported at quarter ends. It is not standalone-quarter real GDP YoY. All 34 SIAT-to-processed-to-master observations reconcile. This is a period-definition limitation, not an arithmetic/parser bug or an unauthorized registry correction.

| Model / target | N | H1 RMSE | H2 RMSE | H3 RMSE | Pooled RMSE | Target SD | Normalized RMSE | 2026Q3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ACCEPTED_REAL_DFM | 42 | 0.504859 | 0.494134 | 0.492718 | 0.497267 | 1.020154 | 0.487443 | 8.301153 |
| NOMINAL_STANDALONE_LOG | 42 | 2.445852 | 2.409512 | 2.415391 | 2.423637 | 1.843858 | 1.314438 | 19.086701 |
| REAL_SHARED_BRIDGE | 42 | 0.586938 | 0.567039 | 0.564737 | 0.572992 | 1.020154 | 0.561672 | 8.314553 |

## A. Real-GDP lineage and definition

[Official SIAT real GDP growth dataset 3698](https://siat.stat.uz/data/3698/?lang=en), indicator **1.01.01.0059**, exact national selector `Code=1700`, `Klassifikator_en=Republic of Uzbekistan`. The registry routes the official descriptor to its linked archived JSON. The parser validates dimensions, code, unit and quarterly frequency; `gdp_target` subtracts 100; the result is stored in processed GDP and the separate quarterly master.

The archived dated national reports explicitly say January–March, January–June, January–September and January–December. Their real growth chart values match the cumulative-period convention recorded in Phase 6B.2. SIAT’s quarterly frequency is a reporting frequency; it does not make Q2–Q4 standalone-quarter observations. Q1 is both the first quarter and the first YTD period.

`gdp_target_audit.csv` inspects 34 quarters from 2018Q1 through 2026Q2, retaining raw index, source definition, model/current-master target, exact transformation, first-release evidence where verified, current revised status, retrieval/update dates and checksums. 10 first-release dates remain unresolved. Dataset update timestamps are never used as those first releases.

Historical model training does not simply use the current master: the existing strict accessor selects latest documented official growth vintages available before each origin. Frozen historical actuals are retained exactly. Origin-specific training values and the raw/master lineage are therefore separate parts of the audit.

**Finding:** implementation conforms to the existing index-minus-100 registry rule. The conceptual issue is calling this a standalone-quarter GDP growth target, or interpreting its forecast that way. This cumulative convention was already documented in Phase 6B.2; Phase 6G.3 verifies it across the full series. The classification records this semantic issue, without claiming a newly introduced production bug.

Proposed clarification for deliberate future registry review: explicitly name/describe the target as cumulative YTD real GDP YoY at quarterly reporting frequency. Recover official standalone-quarter real volume levels or appropriate weights before constructing a standalone-real target. Never de-cumulate real growth percentages or subtract Q1 growth from H1 growth.

## B–C. Nominal levels, validation and growth

[Official SIAT nominal GDP dataset 3695](https://siat.stat.uz/data/3695/?lang=en), indicator **1.01.01.0056**, production method, current prices, national currency **billion UZS**. The quarterly table is cumulative within the calendar year. Descriptor and payload bytes are immutable in this phase’s raw directory with URL, retrieval time, status, checksum, parser version and schema fingerprint.

The standalone flow is Q1=cumulative Q1, Q2=H1−Q1, Q3=9M−H1, Q4=FY−9M, strictly within year. Both cumulative and standalone values are retained. Missing prior quarters produce missing flow; no filling occurs. Growth is `100*(ln(standalone_t)-ln(standalone_t-4))`; conventional `100*(standalone_t/standalone_t-4-1)` is separately retained. The growth percentage itself is never logarithmized.

The revised SIAT dataset has 34 levels and 30 usable standalone YoY log targets. No standalone value is nonpositive. Complete-year standalone sums are independently checked against [official annual SIAT dataset 544](https://siat.stat.uz/data/544/?lang=en), indicator 1.01.01.0001. All complete 2018–2025 years pass; 2026 is incomplete and has no annual test. The first four growth values are missing because a prior-year standalone quarter is absent.

Revisions are preserved in `nominal_cumulative_vintage_events.csv` and `nominal_growth_vintage_history.csv`. The latest SIAT snapshot is used for descriptive/current-series validation only; its revised values never receive historical release dates.

## D. Controlled experiment and information sets

The accepted factor extractor is reused exactly: the same eight predictors and transformations, economic M2 lag zero, one DynamicFactorMQ factor, AR(2), no idiosyncratic AR(1), EM maxiter 500/tolerance 1e−5, training-only scaling, balanced start and ragged-edge release masks. Filtered factor paths and loadings are identical for both target bridges by construction. The accepted real bridge is independently reproduced against every frozen historical/current prediction to tolerance 1e−7.

Nominal targets are derived only from dated official publication events. At each historical origin, every cumulative parent is the latest documented level with publication date strictly earlier than that origin; target/future quarters are excluded. All four required parent values and publication dates/checksums/URLs are recorded. Revisions to a cumulative parent also revise derived standalone levels and growth. No registry lag substitutes for an unknown release date.

The archive is partial. Early nominal 2018Q1/Q2 publication values are absent; derived growth begins only once its published parents are known. A dated FY2023 article reports **1,066.6 trillion UZS**, converted to **1,066,600 billion UZS**, with 100-billion reporting precision explicitly flagged. It is a rounded published value, never presented as an exact SIAT vintage. The reviewed extraction ledger is tied to checksummed official PDFs/HTML.

Cumulative parents from different dated releases may reflect different revision vintages. That is the information actually available under this partial archive, not a coherent complete provider snapshot. Mixed vintages and rounded parents are flagged. GDP methodological/non-observed-economy revisions can create unusually large derived quarterly changes; interpret these as a limitation rather than proof of economic acceleration.

Both controlled bridges use intercept + quarterly mean accepted factor + their own target’s GDP-growth(q−1). Their training quarter set is the **same intersection** of documented real and nominal target histories, inside the unchanged estimation window. `REAL_SHARED_BRIDGE` controls for the reduced nominal data coverage. `ACCEPTED_REAL_DFM` retains its original full real bridge for reference. This additional common-target restriction is necessary for a fair experiment and is explicitly not identical to the full accepted real training sample.

All 44 accepted historical origins are attempted. 42 origins form the exact three-model common evaluation sample. 2 historical/current controlled-origin failures are retained in `model_failures.csv`; insufficient nominal history is never silently replaced. The minimum bridge training requirement remains 12 quarters.

**Identification limit:** the requested real-to-nominal comparison also changes cumulative real growth to standalone nominal growth, and ordinary percentage growth to log growth. It therefore does not isolate inflation alone. Cumulative nominal and log-real YTD diagnostics are supplied to separate period definitions descriptively, without redesigning the DFM.

## E. Forecast performance and scale

Normalized RMSE is 0.561672 for the real shared bridge and 1.314438 for nominal standalone growth. Nominal appears worse on this scale-adjusted measure; raw percentage-point RMSEs across the two targets are not evidence of inherent target superiority.

Target SD uses unique target quarters within each horizon/sample. Forecast volatility is the sample SD of origin predictions. MAE, actual-minus-forecast bias, forecast correlation, forecast R² relative to that target’s realized sample mean and OOS R² relative to the released GDP-growth(q−1) naive forecast are in `horizon_metrics.csv`. These are within-target measures; forecast correlation or in-sample associations alone do not establish useful nowcast accuracy.

Nominal evaluation actuals are **first documented derived** standalone-growth values from the dated archive, not certified exhaustive first-release nominal targets. Real actuals are exactly those of the existing clean evaluation. Largest misses by model are in `largest_historical_misses.csv`; actual publication and parent provenance are separately stored.

## F. Real activity versus inflation information

The accepted factor has M2, PPI, USD/UZS, RUB/UZS, gold prices, industrial production, ex-gold reserves and verified-scope POS turnover. CPI, retail, wholesale, exports and imports are supplementary economic diagnostics only; their DFM loading is unavailable because they do not enter the accepted factor. Nominal/real GDP enter the quarterly bridge, not the factor panel. No missing loading is invented.

Correlations use quarter means with all three observed months and preserve gaps. CPI/PPI YoY log inflation is the sum of 12 monthly log changes, requiring all 12 observations. `target_diagnostics.csv` compares each predictor with standalone nominal growth, cumulative nominal log growth, real YTD growth and an implicit YTD price-growth component.

The implicit price component is the difference between nominal YTD log growth and real YTD log growth on the latest revised series; it is a descriptive decomposition, not a separately recovered official vintage deflator. Ex-post factor regressions on real growth, price growth and both quantify associations only. They cannot prove that inflation causes forecast performance.

## Current 2026Q3 research estimates

REAL_SHARED_BRIDGE: 8.314552665, real cumulative YTD YoY percent; RESEARCH_ONLY_PARTIAL_DOCUMENTED_TARGET_VINTAGES.

NOMINAL_STANDALONE_LOG: 19.086701401, nominal standalone YoY log percent; RESEARCH_ONLY_PARTIAL_DOCUMENTED_TARGET_VINTAGES.

ACCEPTED_REAL_DFM: 8.301152885, real cumulative YTD YoY percent; UNCHANGED_PRODUCTION_REFERENCE.

U_MIDAS: 8.060649796, real cumulative YTD YoY percent; UNCHANGED_PRODUCTION_REFERENCE.

COMBO_50_50: 8.180901341, real cumulative YTD YoY percent; UNCHANGED_PRODUCTION_REFERENCE.

The nominal nowcast is a nominal standalone-quarter YoY log growth forecast. It cannot be subtracted from the real cumulative growth forecast and interpreted as a revision or price effect. Production DFM, U-MIDAS and COMBO_50_50 numbers are preserved.

## Conclusion and reproduction

The real target construction is arithmetically consistent and registry-compliant, with a confirmed cumulative-period interpretation. The nominal dataset validates, and a controlled partial-archive challenger is estimable on the matched subset. Period-definition differences, incomplete nominal release history and mixed parent revisions prevent a clean price-basis-only superiority claim. No production promotion or target alteration is authorized by these results.

Run `.venv/Scripts/python.exe -m scripts.phase6g3.run`; test `.venv/Scripts/python.exe -m scripts.phase6g3.tests`. Re-runs reuse checksummed archived nominal SIAT downloads. All authoring is confined to scripts/phase6g3 and results/phase6g3. Before/after protected hashes and test summaries are stored in this phase.

Ex-post factor associations: REAL_ONLY R²=0.095210, N=30.0; PRICE_ONLY R²=0.022876, N=30.0; BOTH R²=0.107522, N=30.0.

| Indicator | Corr. nominal standalone log YoY | Corr. real YTD log YoY | Corr. implicit YTD price growth |
|---|---:|---:|---:|
| m2 | -0.014935 | 0.297977 | 0.159979 |
| cpi | 0.241085 | -0.361011 | 0.158506 |
| ppi | 0.408001 | 0.098133 | 0.350124 |
| retail | -0.164258 | 0.479345 | -0.299136 |
| wholesale | -0.372100 | -0.044672 | -0.364635 |
| exports | 0.026031 | -0.290075 | 0.222074 |
| imports | -0.047290 | 0.009476 | -0.283093 |
| usd_uzs | 0.013366 | -0.261361 | -0.054183 |
| rub_uzs | 0.269037 | -0.050747 | 0.277510 |
| industrial_production | 0.314460 | 0.746969 | 0.143746 |
| accepted_filtered_factor | -0.016321 | 0.308561 | 0.151250 |

The nominal model is weaker on normalized RMSE, so these results do not support an inflation-driven nominal accuracy advantage. PPI and CPI do contain price information, while industrial production shows a stronger real-growth association. The accepted factor’s price-only association is weak compared with real-only association; both together add little explanatory power in this ex-post diagnostic. Interpretation remains descriptive and sensitive to target revisions/period definitions.

Failed origins: [{'target_quarter': '2022Q3', 'horizon': 'H2', 'current': False, 'error': 'Insufficient identical nominal/real bridge history: 10 quarters, minimum 12'}, {'target_quarter': '2022Q3', 'horizon': 'H3', 'current': False, 'error': 'Insufficient identical nominal/real bridge history: 10 quarters, minimum 12'}]

## Verification evidence

Test results: {'errors': 0, 'exit_code': 1, 'failures': 1, 'skipped': 0, 'tests': 179}. Full output: tests.log and tests.xml.

The unchanged legacy Phase 6B.2 protection test compares today’s repository to its old phase-specific freeze and fails. Its discrepancies overlap files already different in the Phase 6G.3 starting inventory: ['dashboard/current/uzbekistan_nowcast.html', 'data/master/v1_monthly.parquet', 'data/master/v1_monthly.xlsx', 'data/processed/gold_price.parquet']. Earlier phase tests/artifacts were not modified to hide this result. The Phase 6G.3 baseline protection check passes.

Final new Phase 6G.3 suite: {'errors': 0, 'exit_code': 0, 'failures': 0, 'skipped': 0, 'tests': 7}.

Accepted current factor loadings (identical for both targets)

| Indicator | Loading |
|---|---:|
| industrial_production | 0.077893 |
| ppi | -0.041512 |
| usd_uzs | -0.165815 |
| rub_uzs | 0.036923 |
| gold_price | 0.016334 |
| m2 | 0.519784 |
| fx_reserves_ex_gold | 0.057998 |
| pos_turnover | 0.335507 |

Latest-revised nominal standalone versus real cumulative log YoY correlation: 0.342622, N=30. Different reporting-period coverage limits interpretation.

Nominal current log forecast 19.086701% corresponds to conventional YoY growth 21.029849%.

The protection inventory is supplemented with historical Phase 6B.2 paths omitted by the inherited Phase 6G.2 inventory. These supplemental hashes were captured during the audit; they are kept separately from the immutable Phase 6G.3 start snapshot. This phase’s production/model/data writers are never invoked.

1033 current-baseline protected artifact hashes match. No production or prior research artifact is changed.
