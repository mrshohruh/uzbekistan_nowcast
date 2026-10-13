# Phase 8A.1 — existing sources and collection audit

**Classification: PHASE8A1_PARTIAL.** Audit date: 2026-10-12, Asia/Tashkent. Eight active predictors audited: **READY 0, PARTIAL 7, BLOCKED 1, UNKNOWN 0**. Quarterly GDP is an additional direct dependency, classified PARTIAL and excluded from predictor counts. The source CSV contains nine indicator rows.

READY requires current download/parser verification and unattended admissibility. Historical success alone does not meet that threshold. PARTIAL means an evidenced adapter/local data with unresolved runtime or governance conditions. POS is BLOCKED for a comparable new production extension; it remains in the frozen model.

## Verified production dependencies

`config/production.json` resolves `results/operations/current_production.json`, `results/current/production_policy.json`, `config/model_definitions.json` and registry v1.2. The DFM fields are exactly industrial_production, ppi, usd_uzs, rub_uzs, gold_price, m2, fx_reserves_ex_gold and pos_turnover. They match acquisition ACTIVE and prospective FIELDS. U-MIDAS uses three USD/UZS monthly log changes, an intercept and lagged GDP. The headline is COMBO_50_50 with weights 0.5/0.5; the older AR2/USD PRODUCTION_ENSEMBLE is shadow-only.

`config/settings.yaml` defaults to registry v1.1, whereas active production explicitly pins `registry/uzbekistan_nowcasting_v1.2_registry.xlsx`. Earlier registries and broad bootstrap commands are not silently substituted active specifications. No registry was changed.

## Readiness matrix

| Indicator | Readiness | Raw/local coverage | Local clean latest | Saved model eligible | Archived parser replay |
|---|---|---|---|---|---|
| industrial_production | PARTIAL | 2019-01–2026-08, real recovery | 2026-08, nominal canonical | 2026-07 | PASS, approved real SIAT 577 |
| ppi | PARTIAL | 2013-01–2026-08 | 2026-08 | 2026-08 | PASS |
| usd_uzs | PARTIAL | 2013-01-01–2026-10-01, daily | 2026-09 | 2026-09 | PASS, one daily payload |
| rub_uzs | PARTIAL | 2013-01-01–2026-10-01, daily | 2026-09 | 2026-09 | PASS, one daily payload |
| gold_price | PARTIAL | 1960-01–2026-09 | 2026-09 | 2026-08 | PASS |
| m2 | PARTIAL | 2013-01–2026-08 | 2026-08 | 2026-08 | PASS |
| fx_reserves_ex_gold | PARTIAL | 2013-01–2026-08 | 2026-08 | 2026-08 | PASS |
| pos_turnover | BLOCKED | 2016-12–2026-07, recovery provenance | 2026-06, canonical parsed series | 2024-12 | FAIL, KeyError: 'apreily' |
| gdp_real_yoy | PARTIAL | 2018Q1–2026Q2 | 2026Q2 | 2026Q2 | PASS |

Coverage is measured from retained observations, not inferred from registry Verified start/end. The source CSV records exact units, frequency, source IDs, URLs, selectors, parser/update paths, missing periods, quality flags, retrieval dates and checksums. Raw coverage means observation coverage in retained raw-value columns, daily history or selected recovery provenance; it does not certify a complete archive. Recovery selection does not imply POS scope approval. Saved model eligibility comes from `results/current/data_freshness.csv` at the frozen forecast information set, not a new forecast or today's eligibility calculation.

## Source-to-model trace

Official source → archived raw bytes/sidecar → strict parser → transformations and validation → current processed snapshots and vintage metadata → separate monthly/quarterly masters → retrieval/release-gated inputs and approved recovery overrides → immutable operational input snapshots → production.

The inventory has 126 rows covering existing collection entry points, configuration/contracts/registries, parsers/transforms/validation, operations dependencies, storage and research/maintenance scripts. Operational source updates enter `scripts/operations/run_update.py`, use `acquisition.py`, stage isolated projects, validate candidates and promote with journals/backups. Collection commands were not invoked.

Source families and current adapters:

- SIAT JSON descriptor → returned payload: GDP 3698, PPI 1581, approved real industry 577. Strict parser checks indicator identity, frequency, units and dimensions.
- CBU dated FX JSON: distinct official activation dates; Rate/Nominal; arithmetic monthly mean; monthly log change. No calendar-day filling or end-month substitution.
- CBU official e-GDDS pages → current XLSX links: M2 page 111578, reserves page 111574; exact workbook title, units and selected row checked.
- World Bank commodity-markets page → monthly Pink Sheet XLSX: exact Gold column, USD/troy-ounce unit, monthly price and monthly log change. This is the existing registry-approved external provider.
- CBU payment-system archive: date-filtered listings, article HTML Total row and linked files; reviewed source extracts are required for comparable POS extension.

Exact URLs and archived receipt references appear per CSV row. URL presence alone was not treated as proof of accessibility.

### Industrial-production exception

Registry SIAT 590 / 1.02.01.0021 is current-price nominal YTD output, converted to monthly flows then YoY log growth in the canonical master. Production instead uses the already-approved SIAT 577 / 1.02.01.0004 physical-volume growth index, national Code=1700, minus 100. It is not de-cumulated. `config/industry_source.json` and `acquisition.real_industry_contract` explicitly encode this existing exception.

Production recovery reads `data/current/recovered_monthly.csv` and `predictor_provenance.csv`; accepted future real-industry/POS updates use `data/operations/shadow_observations.parquet`. That overlay file is absent locally at audit time. The recovery contains industry through 2026-08; saved production masks use through July. The source CSV's local clean field refers to the nominal processed file and must not be confused with the real production input. No definition was changed.

### POS and GDP admission

POS recovery provenance extends through 2026-07, but comparable production scope ends 2024-12. Later recovered growth is null/unverified and excluded. The canonical parsed POS series has later cells; those are not an accepted production extension. `config/operations_pos_scope_review.json` is absent. `reviewed_pos` requires checksum-matched official receipts, named reviewer, scope/value confirmations and extracted evidence. Current archive parsing takes the final numeric field from a Total row and points at the first attachment, while retaining the HTML page parent. Positional parsing and page-versus-attachment lineage need explicit tests.

The read-only replay of archived article `https://cbu.uz/en/statistics/paysistem/992617/` failed with `KeyError: 'apreily'` after three checksum-verified receipt reads. This is an actual local parser failure, not a live source failure. Its exact final receipt and error are recorded in the CSV. Generic archive processing collects per-article failures, but production acquisition discards that audit list and can return partial historical success.

GDP remains quarterly, published cumulative YTD real growth (volume index minus 100). The registry's no-de-cumulation growth flag must not be interpreted as standalone-quarter GDP growth. New API periods are detected but withheld until documented first-release evidence exists. `data/current/gdp_vintages.csv`, verified realization records and strict vintage accessors are direct dependencies for GDP lags and target boundaries. SIAT updated_at is a dataset update, not proof of historical first release.

Other V1 predictors are inactive in current production: construction, corporate_credit, corporate_deposits, cpi_food, cpi_headline, cpi_services, electricity_gas, exports_non_gold, exports_total, gold_exports_proxy, household_credit, household_deposits, imports_total, instant_payments, interbank_payments, manufacturing, mining, retail_trade, russia_ipi and wholesale_trade. No readiness claim is made for these. Phase 7 electricity/satellite/economic-coverage scripts and dashboards are research components, not active economic collection dependencies. Historical archives were not enumerated.

## Live checks and limits

Nine small memory-only TLS-verified requests were attempted on 2026-10-12 at approximately 09:00:07–09:00:12 UTC, 14:00 Tashkent. All failed before provider contact: configured proxy 127.0.0.1:9 refused connection, ProxyError / WinError 10061. Requested initial URLs are recorded in the CSV, including explicit USD/RUB 2026-10-12 snapshot dates.

All sources are **LIVE_NOT_TESTED**. Reachability, successful download, live parsing and full live validation are unverified. This environment failure does not establish provider downtime, authentication, CAPTCHA, encoding or TLS failure. No access-control/TLS/proxy bypass or alternate provider was used. One attempt per source sufficed to establish this non-transient local limitation; no archive crawl occurred.

Existing download_log receipts show HTTP 200 downloads on 2026-10-05. A memory-only archived client resolved their exact URLs, verified SHA-256 and replayed current parsers: **8 passed, POS failed**. SIAT descriptor/payload, CBU page/workbook, World Bank page/workbook and one POS article/file were read. FX replay checked one retained daily payload per currency, not full history. Archived byte checks are separate from live verification and successful parsing is separate from admission to production.

## Storage, updates and reproducibility

Raw bytes use exclusive timestamp/UUID files and sidecars with URL, retrieval/update dates, HTTP status, checksum, parser version and schema fingerprint. Operations additionally archive current_updates receipts. Official-host restrictions, User-Agent, rate limiting, content-type checks, timeouts and bounded retries exist. SSL exceptions can enter generic ConnectionError retries. Strict HTML workbook-link/update markup can fail on site changes. PPI normalizes Cyrillic M periods; page resolvers require strict UTF-8 while archive parsing uses replacement decoding. No active adapter requires source secrets.

Current processed snapshot keys are unique periods per series. `metadata/observations_long.parquet` has 13,360 rows with zero duplicates under variable/period/frequency/retrieval/checksum/parser identity. `vintages.parquet` has 8,481 rows with zero duplicates under its append identity. Five revision records exist locally. Changed raw/clean values are compared and vintaged; unchanged candidates keep old provenance and omitted source rows do not delete history. Reruns may intentionally archive new raw receipts without changing economic fingerprints.

Real-industry overlay changes are excluded from the canonical `store_vintages` observation list; backups retain prior datasets, but a unified overlay observation history needs work. Historical first-release predictor vintages remain incomplete. Typical registry lags are not fabricated release dates.

The monthly master has 802 unique rows and unique columns; GDP is absent. Quarterly target has 34 unique quarters. All nine local processed series pass `validate_series` with warnings. CSV records gaps and quality flags; this does not assert each warning is harmless. USD/RUB daily history has 1,825 observations each through 2026-10-01. Monthly means include partial October, with latest clean change September. Validated new daily data are persisted only inside the accepted monthly-period branch, so partial-only/unchanged-month runs can retain raw receipts without updating daily Parquet/vintages. This is a static code finding, not a data-loss experiment.

Staging, concurrency hashes, operational lock, pending-transaction gates, backups, per-file atomic replacement and rollback exist. No pending transaction was found. Multi-file replacement is not filesystem-atomic: readers must honor a committed manifest/lock. Noncritical source failure retains old information; critical USD validation blocks promotion. Archive article errors can be masked. Collection and production publication are separate subprocesses/locks; a later builder failure is not one atomic database/publication rollback. No promotion or fault injection ran.

The saved forecast links input fingerprint `4682b245f25db4ae87b43e80444f62b85e29533b53a3a8038ffb7c90191386e0` and data version `update_20261005_114925_44219a53` to current manifests and immutable prospective snapshots with inputs, provenance and specification hashes. This supports frozen replay, not reconstruction of unobserved historical releases. Saved freshness dates differ from raw dates because of masks; an older operational POS stale count of 48 also differs from the production freshness count of 21 and needs consistent reporting.

## Priorities for Phase 8A.2

The risks CSV contains 14 prioritized findings. The first five are:

1. Documented `--run-nowcast` skips source collection. Define a collection-only entry point and test flag semantics.
2. POS new production extension is scope-blocked; its sampled archived parser also fails on observed month spelling. Review comparable official scope and parser evidence.
3. Recheck exact official sources under the intended Windows task account with permitted working network/TLS.
4. Retain validated FX daily candidates and vintages independently of completed-month admission.
5. Propagate archive article errors/overlaps and report partial success visibly.

Also separate collection from publication, version recovery overlay parents and retain the GDP first-release gate. Test unchanged/revision/partial-source/partial-month/crash/rerun behavior in isolation. The design specifies exactly days 1/11/21 in Asia/Tashkent, no publication-calendar or event-triggered scheduler. Account permissions, root working directory, pinned virtual environment, proxy/CA, runtime limits, lock recovery and exit-code monitoring need validation. No task or clock time was installed. No Phase 8A.2 implementation, new provider, registry expansion, scientific change or forecast was performed.

## Tests and production freeze

**41 existing tests passed; zero failures.** Forty selected tests cover SIAT exact rows/schema failure, FX normalization/duplicates/mean/partial-month/lineage, de-cumulation, prices, master construction, two read-only registry cases, M2 page resolution and production configuration. One additional frozen M2 parser/growth test passed. Commands used `.venv/Scripts/python.exe -B -X utf8 -m pytest -p no:cacheprovider -q` with those explicit test paths. No network in tests; selected tests use no tmp_path mutation. The full maintenance test runner was skipped because it creates data/t files and overwrites an existing repository-cleanup XML report.

Read-only checks: configuration PASS; accepted model seal PASS (81 runtime files); current-version verification PASS; pending transactions zero. No model fit, production reconstruction, cleanup, dependency upgrade or updater ran. Stored current_nowcast.json confirms 2026Q3 **8.180901340616275%**. Arithmetic verification of 0.5×8.301152885464585 + 0.5×8.060649795767965 equals the exact saved reference. Existing policy/configuration and forecast artifacts agree; no nowcast mismatch found. Historical manifest hashes describe their own vintages and are not assumed identical to the accepted current seal.

Mutation verification: **PASS — all 1,957 baseline files across 12 trees retain identical aggregate SHA-256 hashes and file counts**. The baseline covers config, registry, src, scripts, data/processed, data/master, data/current, data/operations, metadata, results/current, results/operations and dashboard. Aggregates hash sorted repository-relative paths and each file's SHA-256, excluding bytecode caches. Git status shows only the new results/phase8a1 directory and no tracked modifications. Protected archives were not enumerated or changed. Git reports access-denied warnings for two pre-existing pytest temporary directories in phase6i/phase7c; they were not accessed. Exactly five new audit files exist; no existing report was overwritten. Production models/configuration, master data, source metadata, forecasts and dashboards remain unchanged.

| Baseline tree | Files | SHA-256 before and after |
|---|---:|---|
| config | 11 | f0a77f9a2abe802349038edd40643d4d5e532fe8b7041108c95a022cbfe744cd |
| registry | 8 | 41792ba318fb4ea8965fe3c0c3d5cf46f11faebdcbed2a7ef7033d2e839942eb |
| src | 48 | 0b950f76b9f8f5e28c5366dfd3233e845b0dab86f53e76b73e3201db9a20b28c |
| scripts | 67 | a764c8f1666ffad5403f37255ecac859bdddcbee40a797c9b47c4a67202c6523 |
| data/processed | 32 | 14c29d561079c2ac87090b1c6b44886001b6c81754b7a793d7979d6ec6de6eff |
| data/master | 10 | 5ca4ceda8f9953858f02ebd34312eff427050a7d63d922b7d9c27cce23d70cfc |
| data/current | 4 | 1d347faa5c2b81c60030af87d7f0d1b4564271f96463e8634fc2c41d3dea4771 |
| data/operations | 1 | eac2e1dfaa28270896da15e2340ad65e8c99f2bef45f2847f5d908d7a77078c5 |
| metadata | 28 | 2f6a8c2199a893931c7c67aabe1a38638b1adaa36ce15b5a64f3988dd3969d98 |
| results/current | 24 | cc8ed00502686315a83b2c3f3f060b5da5c6194d4f640ba1152e0e486f835fb7 |
| results/operations | 1721 | 11e6454be5770544180e6a8b8fcf84d88dc21a7978ce6beaaee1b58c2411d122 |
| dashboard | 3 | d62ec7630f422140d92a75e6b16535aea6f0ad06bfcf2ced6dba742d86fb5e95 |

## Deliverables

- `results/phase8a1/phase8a1_source_audit.csv`
- `results/phase8a1/phase8a1_pipeline_inventory.csv`
- `results/phase8a1/phase8a1_risks.csv`
- `results/phase8a1/phase8a1_automation_design.md`
- `results/phase8a1/phase8a1_results.md`
