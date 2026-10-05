# Existing DFM and information-set audit

The production `src/uznowcast/models/dfm.py` is an approximate EM-PCA model, with no Kalman transition, one factor by default, training-only scaling and a quarterly mean factor plus lagged GDP bridge. It is not modified.

The clean Phase 6B.2 comparison uses the immutable Phase 6B DOMESTIC_3 state-space kernel: industrial production, construction and retail published growth from the separately validated CBU research panel; one VAR(1) factor, diagonal white-noise idiosyncratic errors, training-only scaling, missing-observation Kalman filtering, no smoothed factors in forecasts. It starts January 2021. DFM-0 is its saved STRICT Bridge A path; Bridge B remains a separate benchmark.

Monthly horizons and standard/conservative lags come verbatim from models.data. GDP uses Phase 6B.2 documented publication events and strict same-day exclusion. Unresolved GDP value vintages remain excluded; the 46-day Phase 6B.1 fallback is a date assumption, not evidence for a historical value. No current-master GDP values are substituted into undocumented vintage gaps.

Phase 6C uses the frozen registry master plus explicitly identified approved Phase 6A.2 recoveries. Industrial, retail and construction use published real growth, consistently with DFM-0, rather than silently calling them nominal de-cumulated registry flow growth. These research deviations are recorded per variable; no registry or canonical master is changed. Published industrial growth begins January 2019, retail January 2020 and construction January 2021. POS is retained only through its verified December 2024 scope boundary. Longer history of the identical three-variable domestic panel is still blocked by construction coverage. DFM-1 therefore changes composition as well as history.

All predictor coverage and eligibility decisions use data through June 2025. Sparse banking/payments are not silently backfilled. Exact historical predictor revision vintages are unavailable, so the study is explicitly release-lag pseudo-real-time with verified partial GDP vintages, not full real-time evidence.
