# Phase 6D shadow monitor

Status: PHASE6D_INITIALIZED. Governance: INITIALIZED; 0 realized prospective quarters. No production promotion.

First prospective target: 2026Q3. Current target: 2026Q3, H3, POST_H3_LATE_INITIALIZATION. Latest official GDP: 2026Q2. Actual forecast timestamps are retained; late snapshots do not establish on-time H3 evidence.

No verified first-release outcome is registered for pending forecasts. No pending forecast errors, metrics, rankings or superiority claims are calculated. POS is scope-verified only through December 2024 and remains missing thereafter.

              model  forecast     forecast_status
                AR1  8.114253 PENDING_REALIZATION
                AR2  7.457305 PENDING_REALIZATION
         UMIDAS_USD  8.060650 PENDING_REALIZATION
PRODUCTION_ENSEMBLE  7.758977 PENDING_REALIZATION
        PHASE6C_DFM  8.301153 PENDING_REALIZATION
        COMBO_50_50  8.180901 PENDING_REALIZATION
   COMBO_DEV_WEIGHT  8.191455 PENDING_REALIZATION

Run again using `.venv/Scripts/python.exe scripts/research/phase6d/monitor.py`. Archive a dated official first-release document with `--archive-source URL`; submit reviewed evidence using `--realization evidence.json`. Required fields follow sources.register_realization; source receipt, checksum, dated first-publication basis and extraction evidence must match. Mutable SIAT update dates cannot substitute for first publication. Future qualifying snapshots append to the ledger; scores are derived separately.

Governance: 0 INITIALIZED; 1 EARLY_EVIDENCE; 2 INSUFFICIENT_EVIDENCE; 3 PRELIMINARY_REVIEW; 4+ GOVERNANCE_REVIEW_ELIGIBLE. Review eligibility never promotes a model automatically.

Frozen DFM, U-MIDAS and combination weights changed: NO. Protected production artifacts changed: NO (hash verification). All seven forecasts generated successfully. Development weights: DFM 0.5438822544881572; U-MIDAS 0.4561177455118428.

Data status:

             variable latest_usable_month expected_month  stale_months latest_observation expected_latest_observation  release_lag  months_stale  missing_recent       source_status                                                     historical_vintage_status                                             current_vintage_hash            model_usage_status                              warning status                                                        note
industrial_production          2026-07-31     2026-09-30             2         2026-07-31                  2026-09-30           33             2               2 AVAILABLE_WITH_GAPS LATEST_RETRIEVED_RESEARCH_HISTORY; NOT COMPLETE HISTORICAL REAL-TIME VINTAGES 07d79d4e2f25b524b50a1e45b25f453375395d73bdab478e30b4f797a9140d3c FROZEN_INCLUDED_NO_IMPUTATION Missing release dates remain unknown  AMBER Observed retrieval gated; unknown release dates remain null
                  ppi          2026-08-31     2026-09-30             1         2026-08-31                  2026-09-30           15             1               1 AVAILABLE_WITH_GAPS LATEST_RETRIEVED_RESEARCH_HISTORY; NOT COMPLETE HISTORICAL REAL-TIME VINTAGES 6aca447dfdcba486bc6ed6a8fe0356d1a0062411b675c97d0659b5e428f79456 FROZEN_INCLUDED_NO_IMPUTATION Missing release dates remain unknown  AMBER Observed retrieval gated; unknown release dates remain null
              usd_uzs          2026-09-30     2026-09-30             0         2026-09-30                  2026-09-30            0             0               0 AVAILABLE_WITH_GAPS LATEST_RETRIEVED_RESEARCH_HISTORY; NOT COMPLETE HISTORICAL REAL-TIME VINTAGES 66afdd214a59bcf63b50141c86f1f9ba4288dd825ea06ff981a09108eda1dd41 FROZEN_INCLUDED_NO_IMPUTATION Missing release dates remain unknown  GREEN Observed retrieval gated; unknown release dates remain null
              rub_uzs          2026-09-30     2026-09-30             0         2026-09-30                  2026-09-30            0             0               0 AVAILABLE_WITH_GAPS LATEST_RETRIEVED_RESEARCH_HISTORY; NOT COMPLETE HISTORICAL REAL-TIME VINTAGES 190f50ae379bf61851773a5f7b0600494ce942e364da72835c8cfd2fc4f3874a FROZEN_INCLUDED_NO_IMPUTATION Missing release dates remain unknown  GREEN Observed retrieval gated; unknown release dates remain null
           gold_price          2026-08-31     2026-09-30             1         2026-08-31                  2026-09-30            7             1               1 AVAILABLE_WITH_GAPS LATEST_RETRIEVED_RESEARCH_HISTORY; NOT COMPLETE HISTORICAL REAL-TIME VINTAGES 45c0abb713a289010bc9e7cf43693658319e8553d5decef3cb772f0ce0a53230 FROZEN_INCLUDED_NO_IMPUTATION Missing release dates remain unknown  AMBER Observed retrieval gated; unknown release dates remain null
                   m2          2026-08-31     2026-09-30             1         2026-08-31                  2026-09-30           25             1               1 AVAILABLE_WITH_GAPS LATEST_RETRIEVED_RESEARCH_HISTORY; NOT COMPLETE HISTORICAL REAL-TIME VINTAGES e01e22c2d2a720034749e4a7dd9cbbe76d14f1415a0474df344948115492365e FROZEN_INCLUDED_NO_IMPUTATION Missing release dates remain unknown  AMBER Observed retrieval gated; unknown release dates remain null
  fx_reserves_ex_gold          2026-08-31     2026-09-30             1         2026-08-31                  2026-09-30            7             1               1 AVAILABLE_WITH_GAPS LATEST_RETRIEVED_RESEARCH_HISTORY; NOT COMPLETE HISTORICAL REAL-TIME VINTAGES 71cce1322b28c93c28bed659dd952e6647f98390fffc56f8396ea78575cf2e44 FROZEN_INCLUDED_NO_IMPUTATION Missing release dates remain unknown  AMBER Observed retrieval gated; unknown release dates remain null
         pos_turnover          2024-12-31     2026-09-30            21         2024-12-31                  2026-09-30           18            21               3 AVAILABLE_WITH_GAPS LATEST_RETRIEVED_RESEARCH_HISTORY; NOT COMPLETE HISTORICAL REAL-TIME VINTAGES 7e9fc4b244a9f79871d0fe6326b205a24ce1291cb1f2462ae8753fe2bc55ce92 FROZEN_INCLUDED_NO_IMPUTATION              Scope-limited stale POS    RED     Verified scope ends December 2024; later cells excluded

Initialization correction: pre-2019 USD benchmark history was restored. Original snapshot rows remain immutable but are excluded from scoring through withdrawal records. Corrected snapshot is current. No frozen specification changed.

Tests: 304 passed; 0 failed.

Prospective scorecard:

REALIZATION_PENDING. No performance conclusion can yet be made.

Promotion review must assess matched performance versus production, concentration in one quarter, horizon failures, bias, reproducibility, leakage, operational failure rate and data reliability. No automatic decision or weight re-estimation.

The next on-time horizon opportunity is 2026Q4 H1 on October 31, 2026. If Q3 GDP is still unavailable then, the frozen prior-GDP gate will record model failures rather than substitute an unobserved GDP value. No July/August/September forecasts were backdated.
