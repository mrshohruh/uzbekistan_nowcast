# Phase 2A implementation and live-run results

Completed on 29 September 2026 using the supplied, unchanged registry. Only GDP,
industrial production and USD/UZS were ingested. No forecasting code or Phase 2B
downloaders were added.

## Result

- Full build: **passed with documented warnings**; no final source/download/schema failures.
- Offline unit and integration tests: **49 passed**. Tests explicitly prohibit network calls.
- Dependency check: **no broken requirements**.
- Offline replay: **passed**. All eight processed/master output tables matched exactly,
  including the two Excel tables; all **3,665 raw archive files/sidecars** were unchanged;
  the **2,242 retained observation-vintage rows** did not multiply or change.
- Original full build: `61bb825a7c6541439faac1c9742da432`.
- Verified replay: `8751d743c0c24806a4f08f5c412365f7`, completed at
  `2026-09-29T06:00:30.694961+00:00`.

The commands are documented in [README](../README.md). Detailed machine-readable
evidence is in `metadata/validation_summary.json`, `metadata/replay_verification.json`
and the immutable reports under `metadata/runs/`.

## Actual coverage

| Series/output | Raw/level coverage | Observations | Usable clean coverage |
|---|---|---:|---|
| GDP | 2018 Q1–2026 Q2 | 34 quarters | All 34 quarters; published index minus 100 |
| Industrial production | January 2019–July 2026 | 91 monthly YTD/flow observations | January 2020–July 2026; 79 YoY log-growth values |
| USD/UZS activation dates | 2013-01-01–2026-09-29 | 1,823 distinct dated rates | Normalized rate retained for every date |
| USD/UZS monthly | January 2013–September 2026 | 165 monthly means | February 2013–August 2026; 163 monthly log changes |

There are no missing quarters in GDP or missing calendar months in either monthly
series over these spans. FX calendar-day gaps remain explicit and are expected with
weekly historical releases, weekends and holidays; no rates were forward-filled.

The monthly master has **165 unique calendar-month rows** and exactly:

```text
date
ind_prod_yoy_log
usd_uzs_mom_dlog
```

The separate GDP master has **34 quarterly rows**, `gdp_real_yoy_pct`, and provenance
metadata. GDP is absent from the monthly master. Unavailable predictor history remains null.

## Warnings and interpretation limits

1. The first 12 industrial months have no YoY comparator. All seven complete years,
   2019–2025, reconcile exactly: monthly flows sum to December YTD. No non-positive
   industrial monthly flows were found.
2. Industrial log-growth warnings exceed the configured 50-point threshold:
   September 2024 **73.264590** and July 2026 **59.742029**. Their source-derived values
   are preserved, without smoothing or arbitrary corrections.
3. September 2017 FX log change is **66.574460**, flagged as extreme. The registry
   already notes the 2017 FX liberalization break. The value is preserved.
4. September 2026 FX is an incomplete month through the 29th. Its observed mean and
   daily rates are retained; the clean monthly change is null. January 2013 also has
   no preceding monthly comparator within the requested archive window.
5. SIAT update timestamps describe the retrieved dataset edition, not each period's
   original release. CBU activation dates are not asserted to be releases. Unknown
   release dates remain null; historical first-release information sets have not been
   reconstructed. The as-of utility conservatively gates on retrieval too.
6. Industrial production is a current-price UZS value series, not a volume index.
   GDP uses the published quarterly convention unchanged. Standalone-quarter versus
   YTD growth semantics should be clarified with the provider before modelling.

The revision ledger contains one **transformed-value** change for June 2026 FX: an
initial short-window smoke build lacked May, while the full history supplies that lag.
This is not presented as a provider revision. No changed raw source values were detected
between the initial and verification SIAT downloads. Old vintages remain retained.

## Source/schema findings and amendments proposed

No source substitution or registry amendment was made. The observed SIAT machine
endpoints return descriptors requiring a second download of the linked `file`.
The national GDP row is code `1700`; the industrial total is code `B, C, D, E`.
CBU's dated endpoint is a snapshot with an activation date, not a bulk history response.

Recommended clarifications are machine-readable SIAT selectors, explicit descriptor
routing and update-date semantics, confirmed GDP period semantics, explicit unique-
activation-date FX averaging/incomplete-month handling, and alignment of example field
names in project documents with the workbook. Details and official-source links are
in [source findings](source_findings.md).

## Delivered artifacts and operational limits

All requested processed Parquet files, both Parquet/Excel master pairs, immutable raw
payloads, download/vintage/release/schema metadata, structured pipeline logs and
validation summaries exist. The daily FX file is an additional diagnostic output.

Initial sandbox network/temp-directory restrictions were resolved using approved
execution outside the sandbox. An intentionally uncached offline smoke end date failed
visibly before the successful runs; its failure report remains archived. Development
and bootstrap logging is retained separately as `logs/bootstrap_and_development.log`.
These are not outstanding source failures.

Run one build writer at a time. Use `--refresh` to collect revised source vintages;
ordinary cached reruns do not discover changes at existing URLs. Back up raw payloads
and metadata together. Review the documented economic interpretation issues before
authorizing Phase 2B or a modelling phase.
