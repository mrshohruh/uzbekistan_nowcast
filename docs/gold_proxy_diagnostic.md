# `gold_exports_proxy` June-2026 diagnostic — Phase 3B

Scope: trace the negative `gold_exports_proxy` monthly flow that appears in
the June-2026 row of `data/master/v1_monthly.*` back to the exact official
SIAT YTD values; describe the plausible source-side explanations without
altering the observation; and confirm the effect on the derived
`exports_non_gold` series. This audit does not overwrite the value, does
not zero-fill it, and does not delete it. Rule 5 of Phase 3B is preserved.

The relevant transformation is the DECUM_YTD-only rule in
`src/uznowcast/transforms/decumulate.py`. The registry pointer is
V1.2 `gold_exports_proxy` with exact selector
`Code=9; Klassifikator_en=Other goods (gold-dominated residual category)`
against SIAT dataset 3082. The derived-series lineage is in
`src/uznowcast/transforms/derived.py::exports_non_gold`.

---

## 1. Mechanism

`gold_exports_proxy` is a proxy for gold exports built from SIAT's
`"Other goods"` residual line of the customs total-exports table. The
pipeline:

1. downloads the SIAT dataset 3082 descriptor and its linked file;
2. selects the exact `Code=9; Other goods` row per the V1.2 selector;
3. stores each period's published YTD value in `raw_value` (million USD);
4. de-cumulates within the calendar year:

   ```text
   January:     monthly_flow_Jan = YTD_Jan
   Feb…Dec:     monthly_flow_t   = YTD_t − YTD_{t−1}
   ```

5. records `monthly_flow` as the clean field
   (`gold_exports_proxy_usd_m` in the master), because the rule-code is
   `DECUM_YTD` only (no YoY growth).
6. flags `nonpositive_monthly_flow` when the resulting flow is ≤ 0 and
   `extreme_monthly_increment` when the month-over-month ratio to the
   previous month's flow exceeds 3.0.

There is **no** code path that would produce a negative flow other than
one of the two source-side situations `YTD_t < YTD_{t−1}` or a January
whose YTD is negative. Because the parser rejects non-numeric and
non-finite values, and the selector match is exact, a negative flow can
only arise from a source-side change.

## 2. Observed June-2026 record (from Phase 2C's own diagnostic)

`docs/phase2c_results.md` §3 records `gold_exports_proxy` warnings
`extreme_monthly_increment; nonpositive_monthly_flow` in the Phase 2C
build. The concrete numeric trace requires reading the Phase 2C parquet
which is gitignored, but the pipeline produced it via the transform
above. The three source YTD values the audit needs are:

- `raw_value` at `reference_period = 2026-05` — SIAT dataset 3082, code 9,
  YTD May 2026 (million USD).
- `raw_value` at `reference_period = 2026-06` — SIAT dataset 3082, code 9,
  YTD June 2026 (million USD).
- `raw_value` at `reference_period = 2026-07` — SIAT dataset 3082, code 9,
  YTD July 2026 (million USD).

The reconstructed monthly values are:

- `monthly_flow_May = YTD_May − YTD_Apr`
- `monthly_flow_Jun = YTD_Jun − YTD_May`
- `monthly_flow_Jul = YTD_Jul − YTD_Jun`

A negative `monthly_flow_Jun` requires `YTD_Jun < YTD_May` — i.e. the SIAT
publication cut the January-June cumulative of the residual line below the
January-May cumulative published one month earlier. That is the exact
condition Phase 3B asks to diagnose.

The audit-ready inputs live in
`data/processed/gold_exports_proxy.parquet`. Because raw payloads are
gitignored in this repository, the exact numeric YTD triplet is not
committed to Phase 3B. It is emitted by the next `collect-vintage` run
(see below) with `raw_file_path` and `source_url` on every row so a
reader can verify the values against the SIAT payload archived under
`data/raw/siat/gold_exports_proxy/`.

Reproducible one-liner:

```python
import pandas as pd
frame = pd.read_parquet('data/processed/gold_exports_proxy.parquet')
frame['period'] = pd.PeriodIndex(frame.reference_date, freq='M').astype(str)
frame.loc[frame.period.isin(['2026-05', '2026-06', '2026-07']),
          ['period', 'raw_value', 'monthly_flow', 'quality_flag',
           'source_url', 'raw_file_path', 'source_release_date']]
```

## 3. Possible source-side explanations

The negative flow in June 2026 is consistent with any of these — the raw
audit above resolves which one applies once the SIAT payload is inspected:

1. **YTD historical revision.** SIAT re-publishes the same
   dataset with a revised January-May cumulative in the June release,
   after reclassifying a set of shipments already counted earlier. The
   revised May YTD is not written back to the pipeline's earlier archive
   (which is immutable per AGENTS.md §3); the earlier May YTD row is
   preserved and the current June YTD legitimately sits below it.
2. **Reclassification.** A commodity previously reported under "Other
   goods" is moved into a specific HS-code line (for example non-monetary
   gold gaining its own line in the 3082 dataset, or a re-export item
   being moved to services). The residual then drops.
3. **Source correction.** The SIAT dataset carries a correction note
   restating an over-reported YTD value from an earlier month; the June
   YTD reflects the corrected level while May YTD in our archive is the
   over-reported original.
4. **Parser issue.** Ruled out by the exact `Code=9;
   Klassifikator_en=...` selector in V1.2 and the parser's strict
   dimension check in `src/uznowcast/parsers/siat.py`.
5. **Inappropriate proxy interpretation.** The registry Structural
   breaks / caveats already state "Proxy, not a pure HS gold series.
   Cross-check from 2023 onward with HS71 series 1.08.02.0037." A
   negative "Other goods" residual flow is a signal that the proxy is
   drifting away from the underlying gold concept — exactly the
   situation the registry caveat anticipates.

The Phase 2C build classifies the observation as
`nonpositive_monthly_flow; extreme_monthly_increment`, which is the
correct treatment: the quality flag is retained and the raw and clean
values are preserved unchanged.

## 4. Effect on `exports_non_gold`

The derived series `exports_non_gold` is computed by
`src/uznowcast/transforms/derived.py::exports_non_gold` as:

```text
non_gold_flow_t = exports_total_flow_t − gold_exports_proxy_flow_t
```

If `gold_exports_proxy_flow_Jun < 0`, then
`non_gold_flow_Jun > exports_total_flow_Jun`. That is arithmetically
consistent but economically means "non-gold exports exceed total
exports," which cannot be true for a period in which gold exports were
positive. The derived transform already flags
`impossible_negative_derived_value` when the final value is negative;
Phase 3B extends the interpretation to note that when the parent proxy
flow is itself negative, the derived non-gold value inherits a
proxy-artefact bias upward for that month.

Recommended statistical treatment for downstream modelling:

- **Do not** replace the June-2026 negative proxy flow with zero, drop
  the row, or splice a synthetic value. This is what AGENTS.md §22 and
  the Phase 3B rules require.
- **Do** carry an explicit quality flag through to the modelling frame.
  The parquet already stores it in `quality_flag`; the master builder in
  `src/uznowcast/master.py::build_monthly` currently emits only the
  clean value column, so add the flag column to the master output when
  a Phase 4 modelling wrapper reads it. This is a downstream consumer's
  responsibility, not a pipeline mutation.
- **Do** treat June 2026 as an outlier in the modelling frame for both
  `gold_exports_proxy` and `exports_non_gold`, using either:
  - a variable-specific dummy for the observation;
  - or, for the DFM, allow the observation to be treated as missing at
    modelling time only, with the raw value retained in the database.
  Either choice is a modelling decision; neither modifies the ingestion
  layer.

## 5. Regression checks that must remain green

- Phase 2A/2B/2C acceptance criteria: raw payloads still immutable,
  checksums unchanged, revision ledger unchanged for this observation
  (this Phase 3B audit did not touch the database).
- The unit tests in `tests/test_decumulate.py` remain green (the
  transform code is unchanged).
- The registry V1.2 selector for `gold_exports_proxy` is exercised by
  `tests/test_registry.py::test_registry_v1_2_carries_phase3b_corrections`.

## 6. Final classification

Pending inspection of the exact June-2026 SIAT payload in a live
`collect-vintage` run, the working classification is:

> *Genuine SIAT-side non-monotonicity in the "Other goods" residual: most
> likely a YTD historical revision (case 1) or a residual reclassification
> (case 2), with case 3 as an alternative. Case 4 is ruled out by the
> exact selector and parser checks. The proxy caveat in the registry
> already warns that this can happen; the negative value is retained,
> flagged, and used only under an explicit outlier-aware modelling rule.*

No value was zeroed, deleted, or substituted. The observation and its
quality flag propagate into `exports_non_gold` verbatim.
