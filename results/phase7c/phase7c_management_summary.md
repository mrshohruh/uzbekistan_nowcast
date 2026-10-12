# Management summary — PHASE7C_NO_INCREMENTAL_IMPROVEMENT

We considered retail, construction, imports and an export residual to widen the model's coverage of consumption, investment and trade. None was active; all four were stored in the database. Retail complements POS payments, construction complements industrial activity, imports describe demand for equipment and inputs, and the residual aims to reduce gold shipment volatility.

Official data are traceable through archived payload checksums and retrieval records. Retail begins 2020; other raw series begin 2021, ending August 2026. Growth transformations lose the first twelve months. Nominal values remain sensitive to prices; CPI-adjusted retail is approximate. Historical first-release vintages are unavailable, so reporting delays are assumptions and results are retrospective.

DFM and fixed 50/50 comparisons below use matched forecast origins. Short balanced histories restrict inference. Early/recent, leave-one-quarter-out, quarter-level bootstrap, history controls and lag sensitivities are preserved; even a lowest observed RMSE is not proof of superiority. Retain the three validated nominal series as research hypotheses; do not accept production inclusion from this short experiment. Reject primary export-proxy testing until the negative parent flow and category definition are resolved. Production C0 remains 8.180901340616275%.

Retail trade turnover: On 24 origins / 8 GDP quarters (2024Q1–2026Q1), DFM RMSE gain is -0.1480 pp and fixed-combination RMSE gain is -0.0351 pp (positive means improvement). Quarter-level mean squared-error gain interval [-0.3946, -0.0231] pp². Sensitivities: LAG_PLUS_15D: -0.1486 pp; LAG_PLUS_30D: -0.1486 pp; TRAINING_ONLY_WINSOR_1_99: -0.1487 pp. On 22 converged identical-history-control origins, the DFM RMSE gain is -0.0101 pp; this separates history truncation from added information.
Construction works: On 18 origins / 6 GDP quarters (2025Q1–2026Q2), DFM RMSE gain is -0.4734 pp and fixed-combination RMSE gain is -0.1794 pp (positive means improvement). Quarter-level mean squared-error gain interval [-1.1191, -0.4814] pp². Sensitivities: LAG_PLUS_15D: -0.4690 pp; LAG_PLUS_30D: -0.4690 pp; TRAINING_ONLY_WINSOR_1_99: -0.4571 pp. On 18 converged identical-history-control origins, the DFM RMSE gain is +0.0116 pp; this separates history truncation from added information.
Total imports: On 18 origins / 6 GDP quarters (2025Q1–2026Q2), DFM RMSE gain is -0.4841 pp and fixed-combination RMSE gain is -0.1805 pp (positive means improvement). Quarter-level mean squared-error gain interval [-1.1399, -0.5066] pp². Sensitivities: LAG_PLUS_15D: -0.4839 pp; LAG_PLUS_30D: -0.4839 pp; TRAINING_ONLY_WINSOR_1_99: -0.4839 pp. On 18 converged identical-history-control origins, the DFM RMSE gain is +0.0010 pp; this separates history truncation from added information.
NON_GOLD_EXPORT_PROXY: Primary experiment excluded; empirical incremental value remains unknown.

```text
      comparison            model  n_quarters     rmse      mae
              R1               M0           8 0.591581 0.524502
              R1               R1           8 0.739609 0.623326
              R2               M0           6 0.633364 0.536965
              R2               R2           6 1.106799 1.039932
              R3               M0           6 0.633364 0.536965
              R3               R3           6 1.117425 1.053000
  R1_REAL_APPROX               M0           6 0.633364 0.536965
  R1_REAL_APPROX   R1_REAL_APPROX           6 1.122879 1.058667
            C_R1               C0           8 0.516991 0.431285
            C_R1             C_R1           8 0.552043 0.431895
            C_R2               C0           6 0.554264 0.443690
            C_R2             C_R2           6 0.733683 0.601470
            C_R3               C0           6 0.554264 0.443690
            C_R3             C_R3           6 0.734750 0.604090
C_R1_REAL_APPROX               C0           6 0.554264 0.443690
C_R1_REAL_APPROX C_R1_REAL_APPROX           6 0.736999 0.606127
```

Individual economic and empirical rationales are in phase7c_indicator_passports.md. Decisions: {'retail_trade': 'NO_INCREMENTAL_VALUE', 'construction': 'NO_INCREMENTAL_VALUE', 'imports_total': 'NO_INCREMENTAL_VALUE', 'exports_non_gold': 'DATA_NOT_VALIDATED'}.
