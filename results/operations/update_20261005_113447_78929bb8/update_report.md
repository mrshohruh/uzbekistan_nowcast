# Automated nowcast update

Status: **UPDATE_SUCCESS_WITH_WARNINGS**

1. Run date/time: 2026-10-05T11:34:47.604005+00:00 (CHECK_ONLY). Cutoff: 2026-10-05T11:40:02.750033+00:00.

2. Target quarter: 2026Q3.

3. Horizon/stage: H3 / POST_H3_LATE_INITIALIZATION.

4. Source checks: {"industrial_production": "UNCHANGED", "ppi": "UNCHANGED", "usd_uzs": "PARTIAL_CURRENT_MONTH", "rub_uzs": "PARTIAL_CURRENT_MONTH", "gold_price": "UPDATED", "m2": "UNCHANGED", "fx_reserves_ex_gold": "UNCHANGED", "pos_turnover": "UNCHANGED", "gdp_real_yoy": "UNCHANGED"}

5. New observations: 1; see data_changes.csv (candidate-only in dry/check mode).

6. Accepted historical revisions: 0; previous values and provenance retained in versioned backups and observations_long.

7. Failed sources: []

8. Stale/missing indicators:

             variable latest_usable_month  months_stale classification
industrial_production             2026-07             0          GREEN
                  ppi             2026-08             0          GREEN
              usd_uzs             2026-09             0          GREEN
              rub_uzs             2026-09             0          GREEN
           gold_price             2026-08             0          GREEN
                   m2             2026-08             0          GREEN
  fx_reserves_ex_gold             2026-08             0          GREEN
         pos_turnover             2024-12            48            RED
         gdp_real_yoy              2026Q2             0          GREEN

9. Current masters changed: monthly=False, quarterly=False. Candidate changes: {'monthly': True, 'quarterly': False}.

10. Phase 6D snapshot appended: False; DUPLICATE_INFORMATION_SET. Existing immutable snapshots and ledger prefix retained.

11. Current frozen shadow forecasts:

              model  forecast
                AR1  8.114253
                AR2  7.457305
         UMIDAS_USD  8.060650
PRODUCTION_ENSEMBLE  7.758977
        PHASE6C_DFM  8.301153
        COMBO_50_50  8.180901
   COMBO_DEV_WEIGHT  8.191455

Separate production current-vintage/registry-lag reproduction:

Empty DataFrame
Columns: []
Index: []

12. Change versus previous same-target snapshot:

              model  previous_forecast  current_forecast     revision      previous_information_cutoff       current_information_cutoff                                              attribution
                AR1           8.114253          8.114253 0.000000e+00 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:40:02.750033+00:00 Descriptive changed inputs only; no causal decomposition
                AR2           7.457305          7.457305 8.881784e-16 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:40:02.750033+00:00 Descriptive changed inputs only; no causal decomposition
         UMIDAS_USD           8.060650          8.060650 0.000000e+00 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:40:02.750033+00:00 Descriptive changed inputs only; no causal decomposition
PRODUCTION_ENSEMBLE           7.758977          7.758977 0.000000e+00 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:40:02.750033+00:00 Descriptive changed inputs only; no causal decomposition
        PHASE6C_DFM           8.301153          8.301153 0.000000e+00 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:40:02.750033+00:00 Descriptive changed inputs only; no causal decomposition
        COMBO_50_50           8.180901          8.180901 0.000000e+00 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:40:02.750033+00:00 Descriptive changed inputs only; no causal decomposition
   COMBO_DEV_WEIGHT           8.191455          8.191455 0.000000e+00 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:40:02.750033+00:00 Descriptive changed inputs only; no causal decomposition

Changed inputs are descriptive, not an exact causal decomposition.

13. GDP value detected but unverified: False. Verified realization registered: False. API update dates are never first releases.

14. Scoring occurred in the current monitor: False. Only the existing Phase 6D documented-first-release scoring policy is used; no model retuning.

15. Governance: INITIALIZED; no automatic model promotion.

16. Operator warnings: ["POS scope after December 2024 withheld; never filled", "Candidate changes validated only; dry/check mode promoted nothing"]