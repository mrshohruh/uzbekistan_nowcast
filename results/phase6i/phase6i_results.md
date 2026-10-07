PHASE 6I CLASSIFICATION: PHASE6I_KEEP_U0

Current production U-MIDAS:
U0: intercept + latest released GDP lag + three released USD/UZS monthly log changes (oldest first).

Best research challenger:
U2: usd_uzs + m2 (provisional RMSE leader; not a promotion).

Common-sample pooled RMSE:
U0 = 0.686149040
U1 = 1.048734345
U2 = 0.839503039
U3 = 1.170220315
U4 = 1.455931450
U5 = 1.653018181
U6 = 2.439758719

Best H1 model: U1
Best H2 model: U0
Best H3 model: U0

Current 2026Q3 research nowcasts:
U0 = 8.060649796%
U1 = 8.818617811%
U2 = 7.805608972%
U3 = 7.522179662%
U4 = 7.613261269%
U5 = 8.179379753%
U6 = 7.030954968%

Production changed:
NO

Production remains 8.180901340616275% = 50% DFM + 50% U-MIDAS. Current U0 is 8.060649795767965%.

This is evidence generation only. The primary ranking uses identical HOLDOUT origins across U0–U6. Development and combined development/holdout results are supplementary, not independent validation. Only four holdout quarters are available, with three dependent horizons per quarter. A lower RMSE here is insufficient evidence for promotion. The largest model estimates 14 parameters from a short quarterly history; N/K below 3 is flagged as weak degrees of freedom. Proceed with U0 as the frozen benchmark and the lowest common-holdout RMSE challenger as a provisional candidate for prospective evaluation. Do not promote or tune lag lengths on this holdout. Every challenger has worse common-holdout pooled RMSE than U0. Retain U0; the best challenger is a comparator for further research, not a preferred production specification.

IP beyond FX (U0 → U1): matched pooled ΔRMSE +0.362585 pp, ΔMAE +0.271065 pp; improves RMSE in 1/3 horizons. Improved origins 5/12. Total SSE gain -7.548519; top two quarter gains -0.613673. Interpret concentration cautiously.
M2 after FX + IP (U1 → U4): matched pooled ΔRMSE +0.407197 pp, ΔMAE +0.288480 pp; improves RMSE in 1/3 horizons. Improved origins 4/12. Total SSE gain -12.238712; top two quarter gains 0.252184. Interpret concentration cautiously.
Retail after FX + IP + M2 (U4 → U6): matched pooled ΔRMSE +0.983827 pp, ΔMAE +0.853089 pp; improves RMSE in 0/3 horizons. Improved origins 3/12. Total SSE gain -45.992235; top two quarter gains -0.118884. Interpret concentration cautiously.
M2 alone (U0 → U2): matched pooled ΔRMSE +0.153354 pp, ΔMAE +0.152454 pp; improves RMSE in 0/3 horizons. Improved origins 2/12. Total SSE gain -2.807578; top two quarter gains -0.291790. Interpret concentration cautiously.
Retail alone (U0 → U3): matched pooled ΔRMSE +0.484071 pp, ΔMAE +0.345256 pp; improves RMSE in 0/3 horizons. Improved origins 3/12. Total SSE gain -10.783381; top two quarter gains -0.705474. Interpret concentration cautiously.

55 coefficient/horizon groups change sign across successful origins. 0 predictor pairs have absolute monthly correlation >= 0.9. Full coefficient ranges and condition numbers are supplied in the coefficient and forecast CSVs. No causal interpretation is assigned to individual coefficients.

Production U-MIDAS audit

Target: published cumulative year-to-date real GDP YoY percent, volume index minus 100; GDP remains quarterly. This is not standalone-quarter GDP growth.

USD/UZS: Rate/Nominal, monthly mean, then 100 × change in log monthly mean; positive means UZS depreciation.

Design: intercept + one GDP lag + three monthly USD/UZS values, oldest to newest. Each predictor addition contributes three coefficients. U0 has K=5; U1/U2/U3 K=8; U4/U5 K=11; U6 K=14. OLS uses numpy.linalg.lstsq with rcond=None; classical conditional OLS standard errors are supplementary, not robust inference.

Lag alignment: last three nonmissing observations available at each quarter/horizon, NOT necessarily the three months in that quarter. Internal missing months are skipped exactly as in production; no filling or extrapolation. If fewer than three values exist, that training row is omitted or the target forecast fails. GDP lag follows the preceding available training quarter; target GDP lag is the latest strictly released quarter. This reproduces the production convention rather than silently changing it.

H1/H2/H3: end of first/second/third calendar month in target quarter. Each variable is masked by reference month end + registry typical lag <= nominal horizon origin. For current post-H3 initialization, actual retrieval/release gating uses the frozen snapshot cutoff, followed by the unchanged nominal H3 mask.

Training: expanding history of verified GDP vintages strictly available before forecast origin; no current/future target GDP. Every historical training predictor vector is reconstructed at its own same-horizon nominal origin. Minimum 15 complete quarterly rows. No lag search, feature scaling, ridge penalty or variable selection.

Historical evaluation: exact existing standard-lag STRICT GDP-vintage origins and stored scoring actuals, split into DEVELOPMENT and HOLDOUT. U0 is independently checked against both the production function and every frozen historical prediction. The current production scoring sample comprises 12 origins across four holdout quarters; this study also supplies the 36 development origins.

Historical predictors lack complete verified release vintages. Latest revised canonical master values are masked using the existing approved registry-lag pseudo-real-time convention. Typical lags are assumptions, not observed release dates; no dates or vintages are fabricated. This is not a full real-time backtest. Current added predictors are separately gated by observed retrieval and known release timestamp.

IP deliberately uses canonical ind_prod_yoy_log, not the approved Phase6A2 recovered real-activity percent-growth series used by DFM. These are different concepts; registry and production are unchanged. Retail uses retail_yoy_log (not retail_trade_yoy_log); M2 is nominal EOP stock YoY log growth, never real M2. All values are already approved transformed pipeline fields, not newly defined series.

Bias = actual minus forecast, in GDP percentage points. Correlations are pairwise complete monthly transformed inputs, with overlap counts; they are descriptive and never used for fitting or selection. Rank, raw design condition number, coefficient signs, ranges and standard deviations are supplied; condition numbers depend on units and the intercept. Standard errors are null when residual degrees of freedom or full rank are unavailable. Strong correlations alone do not disqualify a model.

Registry transformation contract

variable,field,transformation,lag_days
usd_uzs,usd_uzs_mom_dlog,Normalize Rate/Nominal; aggregate daily observations to monthly mean; model transform = 100*Δln(monthly_mean). Positive = UZS depreciation.,0
industrial_production,ind_prod_yoy_log,De-cumulate within calendar year; then 100*ln(monthly_flow_t/monthly_flow_t-12). Flag non-positive flows.,33
m2,m2_yoy_log,Use EOP level; model transform = 100*ln(level_t/level_t-12).,25
retail_trade,retail_yoy_log,De-cumulate within calendar year; then 100*ln(monthly_flow_t/monthly_flow_t-12).,24

Coverage and sample limits

sample,evaluation_group,models,n_common,first_origin,last_origin
maximum_available,HOLDOUT,U0 + U1 + U2 + U3 + U4 + U5 + U6,12,2025-07-31 00:00:00,2026-06-30 00:00:00
strict_common,HOLDOUT,U0 + U1 + U2 + U3 + U4 + U5 + U6,12,2025-07-31 00:00:00,2026-06-30 00:00:00
sequence_common,HOLDOUT,U0 + U1 + U4 + U6,12,2025-07-31 00:00:00,2026-06-30 00:00:00
U0_vs_U1,HOLDOUT,U0 + U1,12,2025-07-31 00:00:00,2026-06-30 00:00:00
U0_vs_U2,HOLDOUT,U0 + U2,12,2025-07-31 00:00:00,2026-06-30 00:00:00
U0_vs_U3,HOLDOUT,U0 + U3,12,2025-07-31 00:00:00,2026-06-30 00:00:00
U0_vs_U4,HOLDOUT,U0 + U4,12,2025-07-31 00:00:00,2026-06-30 00:00:00
U0_vs_U5,HOLDOUT,U0 + U5,12,2025-07-31 00:00:00,2026-06-30 00:00:00
U0_vs_U6,HOLDOUT,U0 + U6,12,2025-07-31 00:00:00,2026-06-30 00:00:00
IP_increment,HOLDOUT,U0 + U1,12,2025-07-31 00:00:00,2026-06-30 00:00:00
M2_increment,HOLDOUT,U1 + U4,12,2025-07-31 00:00:00,2026-06-30 00:00:00
Retail_increment,HOLDOUT,U4 + U6,12,2025-07-31 00:00:00,2026-06-30 00:00:00
maximum_available,DEVELOPMENT,U0 + U1 + U2 + U3 + U4 + U5 + U6,6,2025-01-31 00:00:00,2025-06-30 00:00:00
strict_common,DEVELOPMENT,U0 + U1 + U2 + U3 + U4 + U5 + U6,6,2025-01-31 00:00:00,2025-06-30 00:00:00
sequence_common,DEVELOPMENT,U0 + U1 + U4 + U6,6,2025-01-31 00:00:00,2025-06-30 00:00:00
U0_vs_U1,DEVELOPMENT,U0 + U1,17,2024-02-29 00:00:00,2025-06-30 00:00:00
U0_vs_U2,DEVELOPMENT,U0 + U2,36,2022-07-31 00:00:00,2025-06-30 00:00:00
U0_vs_U3,DEVELOPMENT,U0 + U3,6,2025-01-31 00:00:00,2025-06-30 00:00:00
U0_vs_U4,DEVELOPMENT,U0 + U4,17,2024-02-29 00:00:00,2025-06-30 00:00:00
U0_vs_U5,DEVELOPMENT,U0 + U5,6,2025-01-31 00:00:00,2025-06-30 00:00:00
U0_vs_U6,DEVELOPMENT,U0 + U6,6,2025-01-31 00:00:00,2025-06-30 00:00:00
IP_increment,DEVELOPMENT,U0 + U1,17,2024-02-29 00:00:00,2025-06-30 00:00:00
M2_increment,DEVELOPMENT,U1 + U4,17,2024-02-29 00:00:00,2025-06-30 00:00:00
Retail_increment,DEVELOPMENT,U4 + U6,6,2025-01-31 00:00:00,2025-06-30 00:00:00
maximum_available,ALL,U0 + U1 + U2 + U3 + U4 + U5 + U6,18,2025-01-31 00:00:00,2026-06-30 00:00:00
strict_common,ALL,U0 + U1 + U2 + U3 + U4 + U5 + U6,18,2025-01-31 00:00:00,2026-06-30 00:00:00
sequence_common,ALL,U0 + U1 + U4 + U6,18,2025-01-31 00:00:00,2026-06-30 00:00:00
U0_vs_U1,ALL,U0 + U1,29,2024-02-29 00:00:00,2026-06-30 00:00:00
U0_vs_U2,ALL,U0 + U2,48,2022-07-31 00:00:00,2026-06-30 00:00:00
U0_vs_U3,ALL,U0 + U3,18,2025-01-31 00:00:00,2026-06-30 00:00:00
U0_vs_U4,ALL,U0 + U4,29,2024-02-29 00:00:00,2026-06-30 00:00:00
U0_vs_U5,ALL,U0 + U5,18,2025-01-31 00:00:00,2026-06-30 00:00:00
U0_vs_U6,ALL,U0 + U6,18,2025-01-31 00:00:00,2026-06-30 00:00:00
IP_increment,ALL,U0 + U1,29,2024-02-29 00:00:00,2026-06-30 00:00:00
M2_increment,ALL,U1 + U4,29,2024-02-29 00:00:00,2026-06-30 00:00:00
Retail_increment,ALL,U4 + U6,18,2025-01-31 00:00:00,2026-06-30 00:00:00

Parsimony and numerical diagnostics

model,n_train_min,n_train_max,n_over_k_min,weak_fits,condition_max,rank_min
U0,15,31,3.0,0,22.455267216713363,5.0
U1,8,25,1.0,27,246.5651567982858,8.0
U2,15,31,1.875,27,232.21563572290466,8.0
U3,5,21,0.625,19,299.16166577056833,8.0
U4,8,25,0.7272727272727273,30,517.0527320228839,11.0
U5,5,21,0.45454545454545453,19,524.6624876269165,11.0
U6,5,21,0.35714285714285715,19,1888.9453874838046,14.0

Reproducibility

Run `.venv/Scripts/python.exe -m scripts.phase6i.run`. No network or production writer is invoked. The manifest records full before/after SHA256 inventories, code hashes, frozen snapshot and output hashes. Tests and deterministic rerun checks are recorded in phase6i_validation.json.
