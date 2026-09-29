# CODEX_START_PROMPT.md

Use the following prompt as the first substantial task in VS Code Codex.

---

Read `AGENTS.md` and `PROJECT_SPEC.md` completely before making changes.

We are building the Uzbekistan Nowcasting Database. The authoritative registry is `registry/uzbekistan_nowcasting_v1_registry.xlsx`.

Implement **Phase 2A only**. Do not build forecasting models and do not expand to all V1 series yet.

Your goals are:

1. Create the Python project/package skeleton specified in the project documents.
2. Implement a robust registry loader. Note that the `V1 Registry` sheet's real headers are on row 4.
3. Add registry validation for unique variable keys, mandatory source/config fields, automation status and transformations.
4. Implement immutable raw-data storage with retrieval timestamps, SHA-256 checksums, source URL and schema fingerprint.
5. Implement the official-source downloader/parser needed for:
   - `gdp_real_yoy`
   - `industrial_production`
   - `usd_uzs`
6. Implement transformations:
   - GDP published convention → `gdp_real_yoy_pct`;
   - SIAT YTD de-cumulation within calendar year;
   - industrial-production YoY log growth;
   - CBU daily FX `Rate / Nominal`;
   - daily FX → monthly mean;
   - monthly FX `100 * Δln`.
7. Preserve raw values as well as transformed values.
8. Add structured download/provenance logs.
9. Add pytest unit tests using frozen local fixtures; unit tests must not call the network.
10. Produce:
    - `data/processed/gdp_real_yoy.parquet`
    - `data/processed/industrial_production.parquet`
    - `data/processed/usd_uzs.parquet`
    - `data/master/pilot_monthly.parquet`
    - `data/master/pilot_monthly.xlsx`
    - `data/master/gdp_quarterly.parquet`
    - `data/master/gdp_quarterly.xlsx`
    - metadata/download/vintage logs
    - a validation summary
11. Run the tests and the pilot pipeline.
12. Summarize exactly what succeeded, what failed, actual historical coverage obtained, any source schema discrepancies, and any registry amendments you recommend.

Important constraints:
- Use official sources specified in the registry.
- Never fabricate an ID, URL, value, unit, release date or historical observation.
- Do not silently substitute another series.
- GDP must remain quarterly.
- Never de-cumulate across December → January.
- De-cumulate YTD data before growth calculations.
- Do not overwrite previous raw vintages.
- If a provider's live schema differs from the registry, preserve evidence, fail visibly where needed, and explain the discrepancy before changing the conceptual series.
- Do not write any nowcasting model yet.

Begin by inspecting the registry and showing a concise implementation plan, then implement it.
