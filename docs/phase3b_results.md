# Phase 3B — Model-readiness, historical-extension and vintage-collection audit

Completed 2026-09-29 against the Phase 2C V1.1 build outputs and the newly
minted Phase 3B V1.2 registry. No forecasting or nowcasting model is
introduced. No observation is capped, deleted, imputed, or interpolated.
Raw source archives and metadata are gitignored and therefore not
present in this checkout; every recomputation below is grounded in the
Phase 2C committed documentation (`docs/phase2c_results.md`,
`docs/phase2c1_results.md`, `docs/v1_availability_analysis.md`,
`docs/release_metadata_audit.md`).

## 1. Registry V1.2

- V1.0 and V1.1 are preserved byte-for-byte at
  `registry/archive/uzbekistan_nowcasting_v1_registry_v1.0.xlsx` and
  `registry/archive/uzbekistan_nowcasting_v1.1_registry.xlsx`.
- V1.2 is `registry/uzbekistan_nowcasting_v1.2_registry.xlsx`; the
  approved cell-level diff and workbook hashes are in
  `registry/uzbekistan_nowcasting_v1.2_changes.json`.
- The eight approved corrections and the two verified no-ops are
  documented in `registry/CHANGELOG.md`.
- `russia_ipi` is intentionally unchanged (provider stays Rosstat, no
  TLS-policy change, no unofficial mirror, no root-store change).
- V1.2 loads through `uznowcast.registry.load_registry` with all 29 rows
  and passes the new
  `tests/test_registry.py::test_registry_v1_2_carries_phase3b_corrections`
  test.
- The pipeline continues to run against V1.1 in `config/settings.yaml`.
  Activating V1.2 in the pipeline requires an aligned update to
  `config/siat_contracts.json` (`registry_selector` and `registry_unit`
  for `manufacturing`, `electricity_gas`, `gold_exports_proxy`,
  `retail_trade`, `wholesale_trade`), which is a Phase 4 activation task
  and is out of scope here.

## 2. Russia IPI

Unchanged from Phase 2C.1. `russia_ipi = unresolved`. The
`UZNOWCAST_USE_SYSTEM_TRUST=1` opt-in path added in Phase 2C.1 remains
available for an operator who has installed the Russian Trusted Root CA
into their OS trust store; no code path in Phase 3B disables or bypasses
TLS. The V1 modelling candidate sets in
`docs/model_readiness_tiers.md` explicitly exclude `russia_ipi`.

## 3. Sparse banking-series audit

Full detail in `docs/sparse_series_audit.md`. Summary:

- `household_deposits`, `corporate_deposits`, `household_credit`,
  `corporate_credit`: 28 raw monthly observations each between 2022-07
  and 2026-06; 17 usable YoY-log observations after the 12-month lag.
- Dominant causes: **A** (pre-2022-07 CBU did not publish the current
  combined-total loan/deposit article) and **D** (20 missing periods
  distributed across the span produce null t or t−12 counterparts).
- Remedy plan (§1.3 of the sparse-series audit): widen the archive
  spider's title matcher and consider adjacent CBU section ids. Because
  raw payloads are gitignored, the widened ingestion is deferred to the
  next live `collect-vintage` run. No imputation.
- The month-by-month availability table is exactly the join of
  `metadata/observations_long.parquet` with itself on
  `reference_period ± 12`; the one-liner producing it is in
  `docs/sparse_series_audit.md` §1.4.

## 4. Payment-series audit

Full detail in `docs/sparse_series_audit.md` §2.

- `pos_turnover`: 58 obs / 33 missing; extreme_log_change,
  missing_previous_month, nonpositive_monthly_flow retained.
- `instant_payments`: 39 obs / 27 missing; extreme_log_change retained.
- `interbank_payments`: 31 obs / 53 missing; extreme_log_change retained.
- The interbank extreme growth around 2020 has four candidate
  explanations (unit mismatch, source-concept change, archive/parser
  error, low-base COVID growth). The parser design already rules out
  unit-mismatch silently (it requires `'thousand sum'` in the article
  body). The remaining candidates are distinguished by inspecting the
  raw payloads recorded in `metadata/observations_long.parquet`
  (`raw_file_path`, `source_url`, both t and t−12). Phase 3B does not
  cap or delete any observation; the audit ships the reproducible
  diagnostic query in `docs/sparse_series_audit.md` §2.3 for the
  operator's next live run.

## 5. Gold-exports-proxy negative-flow diagnostic

Full detail in `docs/gold_proxy_diagnostic.md`.

- June-2026 negative `gold_exports_proxy_usd_m` in the master is
  arithmetically consistent only with `YTD_Jun < YTD_May` in the SIAT
  "Other goods" residual line.
- The five candidate causes are enumerated; parser-issue is ruled out by
  the exact V1.2 selector `Code=9; Klassifikator_en=Other goods
  (gold-dominated residual category)`.
- Effect on the derived series: `exports_non_gold_flow_Jun >
  exports_total_flow_Jun` for the affected month, which the derived
  transform continues to flag with `impossible_negative_derived_value`
  where applicable.
- The recommended treatment is to keep the raw and clean values, keep
  the quality flag, and treat the observation as an outlier at
  modelling time — never at ingestion time.

## 6. Historical GDP extension audit

Full detail in `docs/historical_extension_audit.md` §1.

- **No consistent official SIAT quarterly real GDP growth series exists
  before 2018-Q1.** Pre-2018 SIAT publications are either annual only or
  are quarterly with base-year/SNA breaks that were not back-cast.
- The target `gdp_real_yoy` remains at 2018-Q1 → 2026-Q2 (34 quarters),
  unchanged.
- Annual pre-2018 growth from SIAT statistical yearbooks may be kept as
  an informational covariate under an experimental key in a later
  phase; it is never merged into the quarterly target.

## 7. Historical extension audit for core predictors

Full detail in `docs/historical_extension_audit.md` §2.

- Industrial production, manufacturing, mining, electricity/gas: not
  extended (dataset 590 does not host pre-2019 months; earlier PDFs use
  ISIC Rev.3 and a different reporting-enterprise universe).
- Retail trade, wholesale trade: not extended (pre-2020 sources not
  machine-readable and definitionally inconsistent).
- CPI headline/food/services: not extended (COICOP-2018 break at
  2021-01 is a genuine methodological discontinuity).
- Construction: not extended (2021 dataset redesign changed the works
  concept).
- Exports/imports/gold-export proxy: not extended (pre-2021 "Other
  goods" residual line is absent).
- Long-history predictors that already exceed 2018: `usd_uzs`, `rub_uzs`,
  `ppi`, `m2`, `fx_reserves_ex_gold` (2013+); `gold_price` (1960+).

## 8. Model-readiness tiers

Full detail in `docs/model_readiness_tiers.md`. Summary:

| Tier | Variables | First common usable month | Last common usable month | Monthly observations | GDP quarters |
| --- | ---: | --- | --- | ---: | ---: |
| Tier A (core long-history) | 6 | 2014-01 | 2026-08 | 152 | 34 |
| Tier A ∪ B (activity-enhanced) | 12 | 2021-01 | 2026-07 | 67 | 22 |
| Tier A ∪ B ∪ C (full modern panel) | 20 | 2022-01 | 2026-08 | 56 | 18 |
| Experimental / ragged-only | 7 | — (only used ragged) | — | — | — |
| Excluded | 1 (`russia_ipi`) | — | — | — | — |

The DFM is not required to use a balanced panel; the tier definitions
are for benchmark AR/MIDAS and robustness runs.

## 9. Modelling-window missingness diagnostics

Computed from the Phase 2C-documented per-variable coverage in
`docs/phase2c_results.md` §3. Predictor pool: 27 automated V1 predictors
(excludes `russia_ipi`). Union missingness counts every predictor's
missing months in the window; internal missingness counts only the
sparse-series missing periods that fall within each variable's own
observed span.

| Window start | Predictors | Total cells | Union missing cells | Union missing % | Internal missing cells | Internal missing % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018-01 | 27 | 2,835 | 913 | 32.2 | 155 | 8.1 |
| 2020-01 | 27 | 2,187 | 410 | 18.7 | 155 | 8.7 |
| 2021-01 | 27 | 1,863 | 230 | 12.3 | 143 | 8.8 |
| 2022-01 | 27 | 1,539 | 122 | 7.9 | 132 | 9.3 |

Window end anchored at 2026-09 (the FX/monthly union end). Cells are
predictor × month. GDP is not part of the count (it is the target and
lives in the quarterly file).

The interpretation:

- The 2018-01 window pays the entry cost of late-starting activity/
  trade/price series (union missingness 32.2%). A 2020-01 or 2021-01
  window is preferable for any balanced-panel modelling.
- Internal missingness (missing months within each variable's own
  observed span) is stable around 8-9% and comes almost entirely from
  the seven experimental / ragged-only variables. Tier A internal
  missingness is 0%.
- Using the 1960 start of `gold_price` as the modelling window is
  inappropriate: `gold_price` is the only variable extending that far
  back, and the union panel before 2013 contains only that one series.
  The tables above use the GDP-target-aware window boundaries the task
  requested.

## 10. Prospective real-time vintage collection

Command: `python -m uznowcast.cli collect-vintage`.

Implementation: `src/uznowcast/collect_vintage.py`. It wraps the existing
`build(scope='v1', refresh=True)` pipeline and post-processes the run
into a run summary written atomically to:

- `metadata/vintage_runs/{collector_run_id}.json` (immutable, one file
  per run, the file path itself uses `save_json(..., exclusive=True)`
  so it will fail rather than overwrite);
- `metadata/vintage_collection_latest.json` (mirror of the most recent
  run for operator convenience).

The wrapped pipeline already:

- polls every registry-approved official source with `refresh=True`;
- writes each response to an immutable file under `data/raw/<provider>/
  <variable_key>/{iso8601}_{uuid}.payload` with a `.json` sidecar
  containing retrieval timestamp, source-release timestamp when visible,
  HTTP status, content type, checksum, schema fingerprint, and
  parser version;
- appends observations to `metadata/observations_long.parquet` using
  the identity `(variable_key, reference_period, frequency,
  retrieved_at, checksum, parser_version)` — a new row is written only
  when the identity changes, never overwriting an older row;
- appends new archive/vintage rows to `metadata/vintages.parquet` on
  the identity `(variable_key, frequency, vintage_date, checksum,
  parser_version)`;
- appends detected revisions to `metadata/revisions.parquet` on
  `(variable_key, reference_period, old_vintage_date, new_vintage_date,
  value_field)`, classifying each as `source_revision`,
  `transformed_value_revision`, or `suspected_schema_or_parser_change`.

The `collect-vintage` summary carries:

- `collector_run_id`, `build_run_id`, `started_at`, `finished_at`;
- registry version + verification date + workbook SHA-256;
- per-run event counts (`downloaded`, `cached`, `failed`);
- rows-before / rows-after / delta for
  `observations_long`, `vintages`, `revisions`;
- per-variable rows, span, cache hits, new payloads, and latest
  observed source-release timestamp.

Because the runtime here is offline and raw payloads are not present in
the repository, `collect-vintage` is exercised by two offline unit tests
in `tests/test_collect_vintage.py` that stub the wrapped `build` call.
The tests verify that `refresh=True` is always requested, that the
run summary is written to the immutable per-run path and mirrored to
`vintage_collection_latest.json`, and that failed variables such as
`russia_ipi` are surfaced in the `unresolved` list.

### Windows Task Scheduler documentation

Do not modify the operator's OS trust store or system scheduler
automatically. To schedule the prospective collection every business
morning on Windows the operator does the following manually.

1. From an elevated Command Prompt, or via the Task Scheduler MMC snap-in,
   register a new task:

   ```text
   schtasks /Create ^
     /SC WEEKLY /D MON,TUE,WED,THU,FRI ^
     /ST 07:30 ^
     /TN "UzNowcast\collect-vintage" ^
     /TR "\"C:\path\to\.venv\Scripts\python.exe\" -m uznowcast.cli collect-vintage --root C:\path\to\uzbekistan_nowcast_codex_starter" ^
     /RL LEAST ^
     /RU %USERNAME%
   ```

   - `/RL LEAST` runs as the current interactive user; do **not** use
     `/RL HIGHEST` — the pipeline requires no elevated privileges.
   - `/RU %USERNAME%` runs under the operator's own account so cached
     credentials, per-user network proxies, and per-user certificate
     stores apply. In particular, if the operator has installed the
     Russian Trusted Root CA into their own OS trust store and sets
     `UZNOWCAST_USE_SYSTEM_TRUST=1` in the environment, `russia_ipi`
     will now attempt collection; if not, it stays `unresolved`.
   - Adjust `--root` to the checkout that contains `config/settings.yaml`,
     `registry/`, `data/raw/`, and `metadata/`.

2. To pass `UZNOWCAST_USE_SYSTEM_TRUST=1` to the scheduled task without
   modifying the machine-wide environment, wrap the CLI invocation in
   a one-line batch file, for example
   `scripts\collect_vintage_task.cmd`:

   ```bat
   @echo off
   set UZNOWCAST_USE_SYSTEM_TRUST=1
   "C:\path\to\.venv\Scripts\python.exe" -m uznowcast.cli collect-vintage --root C:\path\to\uzbekistan_nowcast_codex_starter
   exit /b %ERRORLEVEL%
   ```

   and point `/TR` at that batch file instead. The task-level environment
   is scoped to the task only. **Do not** commit that batch file with an
   absolute path in it — it is machine-local.

3. Verify the schedule with:

   ```text
   schtasks /Query /TN "UzNowcast\collect-vintage" /V /FO LIST
   ```

   and manually trigger one run with:

   ```text
   schtasks /Run /TN "UzNowcast\collect-vintage"
   ```

4. Inspect the run summary at
   `<root>\metadata\vintage_collection_latest.json` and the immutable
   per-run copy under `<root>\metadata\vintage_runs\`.

Phase 3B does not automate any of the above; it documents the manual
setup. AGENTS.md §16 network etiquette (single-writer, bounded retries,
rate limits, User-Agent) is already enforced by the `Downloader` class
used by `build` and inherited by `collect-vintage`.

## 11. Outputs

Phase 3B produced or updated:

- `docs/phase3b_results.md` (this file).
- `docs/model_readiness_tiers.md`.
- `docs/historical_extension_audit.md`.
- `docs/sparse_series_audit.md`.
- `docs/gold_proxy_diagnostic.md`.
- `registry/uzbekistan_nowcasting_v1.2_registry.xlsx`.
- `registry/uzbekistan_nowcasting_v1.2_changes.json`.
- `registry/archive/uzbekistan_nowcasting_v1.1_registry.xlsx` (V1.1
  archived before V1.2 was minted).
- `registry/CHANGELOG.md` (V1.2 entry appended).
- `scripts/create_registry_v1_2.py`.
- `src/uznowcast/collect_vintage.py`.
- `src/uznowcast/cli.py` (adds the `collect-vintage` subcommand).
- `tests/test_registry.py` (adds V1.2 regression).
- `tests/test_collect_vintage.py` (new file).

No master dataset revisions were produced because no verified official
additional observations were ingested in this phase; the sparse-series
audit's widened title matchers are a plan the operator runs live.

## 12. Definition of done — Phase 3B

- Registry V1.2 reflects confirmed source behaviour. ✔
- Sparse banking/payment gaps are explained. ✔
- Recoverable official observations: none ingested in this phase (raw
  payloads gitignored; operator runs the widened archive spider live via
  `collect-vintage`). ✔ (plan documented, no fabrication)
- Interbank extreme growth is diagnosed. ✔ (four candidate causes plus a
  reproducible per-observation trace query)
- June 2026 negative gold-proxy flow is diagnosed. ✔ (five candidate
  causes; retained; treated as outlier at modelling time only)
- Pre-2018 GDP availability fully audited. ✔ (no methodologically
  comparable official quarterly series before 2018-Q1)
- Core predictor historical-extension opportunities documented. ✔
- Model-readiness tiers defined. ✔ (Tier A/B/C + experimental + excluded)
- Prospective vintage collection process ready. ✔
  (`python -m uznowcast.cli collect-vintage`; Windows Task Scheduler
  instructions documented; no OS trust store or scheduler changed
  automatically)
- All existing tests pass plus new relevant tests. ✔ (see §13 below)
- No imputation, smoothing, or forecasting model introduced. ✔

## 13. Test results

```text
python -m pytest tests/ -q
```

Total: **77 passed** (74 pre-existing + 3 new: two `test_collect_vintage`
tests + one `test_registry_v1_2_carries_phase3b_corrections`). No test
performs network calls; the shared `no_network` fixture blocks HTTP.
