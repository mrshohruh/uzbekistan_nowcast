# Automated nowcast update

Status: **NO_INFORMATION_CHANGE**

1. Run date/time: 2026-10-05T11:26:09.620042+00:00 (CHECK_ONLY). Cutoff: 2026-10-05T11:28:04.848518+00:00.

2. Target quarter: 2026Q3.

3. Horizon/stage: H3 / POST_H3_LATE_INITIALIZATION.

4. Source checks: {"industrial_production": "SOURCE_UNAVAILABLE", "ppi": "SOURCE_UNAVAILABLE", "usd_uzs": "SOURCE_UNAVAILABLE", "rub_uzs": "SOURCE_UNAVAILABLE", "gold_price": "SOURCE_UNAVAILABLE", "m2": "SOURCE_UNAVAILABLE", "fx_reserves_ex_gold": "SOURCE_UNAVAILABLE", "pos_turnover": "SOURCE_UNAVAILABLE", "gdp_real_yoy": "SOURCE_UNAVAILABLE"}

5. New observations: 0; see data_changes.csv (candidate-only in dry/check mode).

6. Accepted historical revisions: 0; previous values and provenance retained in versioned backups and observations_long.

7. Failed sources: ['industrial_production', 'ppi', 'usd_uzs', 'rub_uzs', 'gold_price', 'm2', 'fx_reserves_ex_gold', 'pos_turnover', 'gdp_real_yoy']

8. Stale/missing indicators:

             variable latest_usable_month  months_stale classification
industrial_production             2026-07             0          AMBER
                  ppi             2026-08             0          AMBER
              usd_uzs             2026-09             0          AMBER
              rub_uzs             2026-09             0          AMBER
           gold_price             2026-08             0          AMBER
                   m2             2026-08             0          AMBER
  fx_reserves_ex_gold             2026-08             0          AMBER
         pos_turnover             2024-12            48            RED
         gdp_real_yoy              2026Q2             0          AMBER

9. Current masters changed: monthly=False, quarterly=False. Candidate changes: {'monthly': False, 'quarterly': False}.

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
                AR1           8.114253          8.114253 0.000000e+00 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:28:04.848518+00:00 Descriptive changed inputs only; no causal decomposition
                AR2           7.457305          7.457305 8.881784e-16 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:28:04.848518+00:00 Descriptive changed inputs only; no causal decomposition
         UMIDAS_USD           8.060650          8.060650 0.000000e+00 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:28:04.848518+00:00 Descriptive changed inputs only; no causal decomposition
PRODUCTION_ENSEMBLE           7.758977          7.758977 0.000000e+00 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:28:04.848518+00:00 Descriptive changed inputs only; no causal decomposition
        PHASE6C_DFM           8.301153          8.301153 0.000000e+00 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:28:04.848518+00:00 Descriptive changed inputs only; no causal decomposition
        COMBO_50_50           8.180901          8.180901 0.000000e+00 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:28:04.848518+00:00 Descriptive changed inputs only; no causal decomposition
   COMBO_DEV_WEIGHT           8.191455          8.191455 0.000000e+00 2026-10-05T06:28:16.244132+00:00 2026-10-05T11:28:04.848518+00:00 Descriptive changed inputs only; no causal decomposition

Changed inputs are descriptive, not an exact causal decomposition.

13. GDP value detected but unverified: False. Verified realization registered: False. API update dates are never first releases.

14. Scoring occurred in the current monitor: False. Only the existing Phase 6D documented-first-release scoring policy is used; no model retuning.

15. Governance: INITIALIZED; no automatic model promotion.

16. Operator warnings: ["industrial_production: SOURCE_UNAVAILABLE", "ppi: SOURCE_UNAVAILABLE", "usd_uzs: SOURCE_UNAVAILABLE", "rub_uzs: SOURCE_UNAVAILABLE", "gold_price: SOURCE_UNAVAILABLE", "m2: SOURCE_UNAVAILABLE", "fx_reserves_ex_gold: SOURCE_UNAVAILABLE", "pos_turnover: SOURCE_UNAVAILABLE", "gdp_real_yoy: SOURCE_UNAVAILABLE", "Unknown releases remain null; lag is planning metadata", "Unknown releases remain null; lag is planning metadata", "Unknown releases remain null; lag is planning metadata", "Unknown releases remain null; lag is planning metadata", "Unknown releases remain null; lag is planning metadata", "Unknown releases remain null; lag is planning metadata", "Unknown releases remain null; lag is planning metadata", "POS scope after December 2024 withheld; never filled", "Unknown releases remain null; lag is planning metadata"]