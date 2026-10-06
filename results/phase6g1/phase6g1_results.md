# Phase 6G.1 — M2 dominance audit



Research only. Phase 6E production and its dashboard remain unchanged. No challenger is promoted. This is availability-aware pseudo-real-time, not fully vintage-real-time; predictor revision-value leakage remains unresolved.

## Exact reconstruction and signal meaning



The dashboard quarterly M2 signal is exactly reproducible: **0.726073786411**, with current absolute signal share **67.407878027%** and absolute loading share **41.524057459%**. The latest-month signal is 0.657006558411; it is a different quantity. Phase 6E DFM/U-MIDAS/ensemble, Phase 6F M2-L2 and both Phase 6G extended benchmark RMSEs are refitted and checked before challenger interpretation.

| Month | Raw M2 (billion UZS) | YoY log value | Training mean | Training SD | z | Loading |
|---|---:|---:|---:|---:|---:|---:|
| 2026-07 | 434511.157141744 | 31.937271539 | 20.635954291 | 7.387675190 | 1.529752860 | 0.519783970 |
| 2026-08 | 437719.635821015 | 29.973970336 | 20.635954291 | 7.387675190 | 1.263999270 | 0.519783970 |



Training-only mean 20.635954290500, SD 7.387675190245; target-quarter mean z 1.396876064639; sign-aligned loading 0.519783969953. Two released Q3 M2 observations (July/August), arithmetic mean aggregation: mean(z_Jul,z_Aug) × loading = 0.726073786411. Latest transformed August value is 29.973970335589.

The signal denominator is 1.077134910139, from exactly ["industrial_production", "ppi", "usd_uzs", "rub_uzs", "gold_price", "m2", "fx_reserves_ex_gold"]. POS has no Q3 signal and remains null. Loading share instead includes all eight estimated loadings, including POS. Loading share = |loading_i|/Σ|loading_j|. Signal share = |mean released-quarter z_i × loading_i|/Σ|available signals_j|.

Neither share is a GDP contribution. The bridge has a valid additive intercept/factor/GDP-lag design, but an individual loading × current z is not the filtered factor’s full historical/state contribution. No per-indicator GDP contribution is fabricated; **0.726 is not +0.726 pp GDP**.

## Coverage and source audit



| Indicator | Latest usable month | Q3 months | Missing months | Q3 mean z | Loading | Signal | Share % |
|---|---|---:|---:|---:|---:|---:|---:|
| industrial_production | 2026-07 | 1 | 2 | 0.644266 | 0.077893 | 0.050184 | 4.659 |
| ppi | 2026-08 | 2 | 1 | -0.751073 | -0.041512 | 0.031179 | 2.895 |
| usd_uzs | 2026-09 | 3 | 0 | -0.913228 | -0.165815 | 0.151426 | 14.058 |
| rub_uzs | 2026-09 | 3 | 0 | -0.948450 | 0.036923 | -0.035020 | 3.251 |
| gold_price | 2026-08 | 2 | 1 | 0.214617 | 0.016334 | 0.003506 | 0.325 |
| m2 | 2026-08 | 2 | 1 | 1.396876 | 0.519784 | 0.726074 | 67.408 |
| fx_reserves_ex_gold | 2026-08 | 2 | 1 | -1.374990 | 0.057998 | -0.079747 | 7.404 |
| pos_turnover | 2024-12 | 0 | 3 | Unavailable | 0.335507 | Unavailable | Unavailable |



POS stops at 2024-12 because the frozen Phase 6D input adapter explicitly rejects post-2024-12 records and requires scope verification. Newer CBU POS/BC/ATM archive records exist through 2026-06 in metadata; they are not verified as comparable POS-only production inputs. Some newer clean values also have missing-flow/extreme-change flags. This is an intentional scope guard, not a silently abandoned updater. No replacement is made.

August industrial production exists in the approved official SIAT 577 archive: raw physical-volume index 108.0, clean growth 8.0. Its assumed release date is Aug31 + 33 days = Oct3, after the frozen nominal H3 Sep30 cutoff. The Oct5 late-init production snapshot retains the H3 mask, so July is correctly its latest usable month. This is not an August ingestion omission. The approved comparison contains no September real-index observation; repository absence does not prove live official publication delay.

The dashboard bars renderer uses a zero-width visual bar for a null signal but labels it Unavailable and excludes it from the numerical denominator. That is not an observed zero. DFM input cells remain NaN; EM likelihood and filtered Kalman states handle missing observations. A stale POS history can affect estimated loadings/dynamics without providing a current Q3 measurement.

## Historical dominance and standardization



| Statistic | N | Mean | Median | SD | Min | Max | p25 | p75 | p90 | Current | Current percentile |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| m2_signal_share_pct | 30 | 52.0332 | 56.3517 | 24.2762 | 11.0710 | 88.8028 | 34.3909 | 71.0317 | 78.1996 | 67.4079 | 66.67 |
| m2_loading_share_pct | 44 | 38.7862 | 40.0693 | 7.3441 | 13.0310 | 48.2081 | 35.1982 | 43.3063 | 45.7142 | 41.5241 | 52.27 |
| m2_zscore | 30 | 0.8260 | 1.1341 | 1.0566 | -1.0715 | 2.8163 | -0.1445 | 1.5118 | 1.8646 | 1.3969 | 63.33 |
| signal_HHI | 44 | 0.5432 | 0.5002 | 0.2257 | 0.2194 | 0.9979 | 0.3511 | 0.6713 | 0.9023 | 0.4837 | 45.45 |
| m2_signal_share_pct_H3_ONLY | 15 | 50.7946 | 62.9148 | 24.7171 | 11.0710 | 79.7561 | 34.1248 | 72.0476 | 77.8108 | 67.4079 | 73.33 |
| latest_M2_zscore | 44 | 0.7731 | 1.1000 | 1.0554 | -1.2994 | 3.1958 | -0.2062 | 1.5013 | 1.7293 | 1.2640 | 61.36 |



Current M2 share is classified NORMAL_RANGE: percentile 66.67 across observed historical signals; horizon-matched H3 percentile 73.33. Descriptive labels use the empirical p75/p90, not a forecasting threshold. M2 is the largest signal at 22/44 origins (50.00%). Share is defined at 30 of the 44 origins; missing Q3 M2 signals remain null, not zero.

Historical average signal HHI 0.543246; current HHI 0.483703; current percentile 45.45.

M2 share exceeds 40% at 19/30 observed-share origins (63.33%), or 43.18% of all 44 candidate origins. Thresholds are descriptive only.

M2 share exceeds 50% at 18/30 observed-share origins (60.00%), or 40.91% of all 44 candidate origins. Thresholds are descriptive only.

M2 share exceeds 60% at 14/30 observed-share origins (46.67%), or 31.82% of all 44 candidate origins. Thresholds are descriptive only.

Latest-observation training z: current 1.263999; 2 historical |z|>2, 1 |z|>3. Quarterly mean z is 1.396876. The current M2 observation is not an extreme |z|>2 event; its large loading and uneven observed-signal denominator must be distinguished from an extreme raw monetary-growth observation. No clipping/winsorization occurs.



## Ragged edge and POS denominator



available_indicator_count: N=30; correlation -0.527575.

available_target_quarter_month_count: N=30; correlation -0.185285.

AT_LEAST_MEDIAN_COVERAGE: N=24; mean M2 share 46.790408%.

BELOW_MEDIAN_COVERAGE: N=6; mean M2 share 73.004311%.

These associations exclude unavailable M2 signals and are descriptive; horizon and monetary era are confounded. They do not establish that ragged-edge missingness primarily causes M2 dominance. The current missing POS contribution cannot be identified without a valid released current POS observation.

For historical charts with both observed M2 and POS signals, removing only the observed POS term from the denominator increases M2 share by mean 11.537548 pp, maximum 25.776618 pp. This shows denominator sensitivity; it does not assign that historical POS value to 2026Q3 or estimate a current causal effect.



## Forecast tests — extended sample has priority



| Sample | Model | N | H1 RMSE | H2 RMSE | H3 RMSE | Pooled RMSE | Δ vs matched benchmark |
|---|---|---:|---:|---:|---:|---:|---:|
| EXTENDED_PRINCIPAL_COMMON | D0 | 36 | 0.504728 | 0.491772 | 0.491739 | 0.496117 | 0.000000 |
| EXTENDED_PRINCIPAL_COMMON | D1 | 36 | 0.692792 | 0.682866 | 1.288836 | 0.932267 | 0.436149 |
| EXTENDED_PRINCIPAL_COMMON | D2 | 36 | 0.537920 | 0.508618 | 0.499623 | 0.515646 | 0.019529 |
| EXTENDED_PRINCIPAL_COMMON | E0 | 36 | 0.488022 | 0.491058 | 0.327233 | 0.442111 | 0.000000 |
| EXTENDED_PRINCIPAL_COMMON | E1 | 36 | 0.565913 | 0.578492 | 0.632891 | 0.593145 | 0.151034 |
| EXTENDED_PRINCIPAL_COMMON | E2 | 36 | 0.496494 | 0.493452 | 0.344506 | 0.450439 | 0.008328 |
| ORIGINAL_HOLDOUT_PRINCIPAL_COMMON | D0 | 6 | 0.835787 | 0.805619 | 0.807322 | 0.816360 | 0.000000 |
| ORIGINAL_HOLDOUT_PRINCIPAL_COMMON | D1 | 6 | 1.058902 | 1.095215 | 1.009502 | 1.055125 | 0.238765 |
| ORIGINAL_HOLDOUT_PRINCIPAL_COMMON | D2 | 6 | 0.799453 | 0.764442 | 0.746419 | 0.770420 | -0.045940 |
| ORIGINAL_HOLDOUT_PRINCIPAL_COMMON | E0 | 6 | 0.840000 | 0.879397 | 0.461342 | 0.750949 | 0.000000 |
| ORIGINAL_HOLDOUT_PRINCIPAL_COMMON | E1 | 6 | 0.955621 | 1.023428 | 0.565160 | 0.871784 | 0.120834 |
| ORIGINAL_HOLDOUT_PRINCIPAL_COMMON | E2 | 6 | 0.814187 | 0.855553 | 0.425616 | 0.724803 | -0.026146 |
| ORIGINAL_HOLDOUT_REFERENCE_12 | D0 | 12 | 0.690729 | 0.673486 | 0.670942 | 0.678442 | 0.000000 |
| ORIGINAL_HOLDOUT_REFERENCE_12 | D2 | 12 | 0.633445 | 0.608262 | 0.597139 | 0.613137 | -0.065306 |
| ORIGINAL_HOLDOUT_REFERENCE_12 | E0 | 12 | 0.671930 | 0.677106 | 0.328716 | 0.582528 | 0.000000 |
| ORIGINAL_HOLDOUT_REFERENCE_12 | E2 | 12 | 0.646056 | 0.652769 | 0.302546 | 0.558280 | -0.024247 |
| PHASE6G_REFERENCE_44 | D0 | 44 | 0.504859 | 0.482322 | 0.476113 | 0.487529 | 0.000000 |
| PHASE6G_REFERENCE_44 | D2 | 44 | 0.520924 | 0.559129 | 0.504724 | 0.528928 | 0.041399 |
| PHASE6G_REFERENCE_44 | E0 | 44 | 0.482015 | 0.460713 | 0.298027 | 0.420197 | 0.000000 |
| PHASE6G_REFERENCE_44 | E2 | 44 | 0.485639 | 0.488267 | 0.338725 | 0.442075 | 0.021878 |
| REAL_M2_PAIRWISE_COMMON | D0 | 18 | 0.643809 | 0.629045 | 0.627107 | 0.633364 | 0.000000 |
| REAL_M2_PAIRWISE_COMMON | D3 | 18 | 1.086138 | 1.095956 | 1.111407 | 1.097883 | 0.464519 |
| REAL_M2_PAIRWISE_COMMON | E0 | 18 | 0.622295 | 0.640033 | 0.353175 | 0.554264 | 0.000000 |
| REAL_M2_PAIRWISE_COMMON | E3 | 18 | 0.807621 | 0.835169 | 0.477290 | 0.725159 | 0.170895 |



D0/D1/D2 and E0/E1/E2 share identical principal origins. Challenger failures are excluded from all principal comparison models. The original 12-origin holdout is reported separately. Full pairwise and real-M2 comparisons use exact matched benchmark origins; no unequal-sample RMSE difference supports a conclusion.

D1 fails the original unchanged convergence/stability gate at eight Phase 6G origins: 2022Q3 H2/H3 and all six 2025Q3/2025Q4 horizons. Consequently the principal D0/D1/D2 comparison has 36 extended origins and only six common original-holdout origins. The full 44-origin D0/D2 Phase 6G reference and original 12-origin D0/D2 holdout reference are retained in separate rows. Missing D1 forecasts are never filled or treated as numerical errors to score. Failure coverage is itself a limitation of the no-M2 challenger.

D3 uses existing official SIAT monthly CPI: real M2 YoY log = nominal M2 YoY log − Σ of twelve consecutive monthly 100 ln(CPI_index/100) values. Each parent is publication-masked before transformation, and gaps invalidate a twelve-month sum. CPI begins January 2021; YoY inflation first exists December 2021, materially reducing D3’s balanced training history. D3 is therefore assessed on a separate reduced common sample rather than shrinking the main 44-origin question. Both baseline and real-M2 scores on that reduced sample are reported. CPI’s 2026 methodology change and revised-snapshot limitation remain.

Earlier/later eras use the pre-existing 2025Q3 development/holdout boundary, not a searched break date. Earlier results overlap specification development and are retrospective robustness, not independent prospective validation. Bias is actual minus forecast; OOS R² = 1 − SSE_challenger/SSE_matched_baseline, positive improvement, negative worse.

## Loadings, factors and bridge



D0: current factor correlation with D0 1.000000, factor SD 1.871131, empirical persistence 0.962035, fitted AR(2) (1.354396, -0.399762), range [-2.612640, 3.303506], sign alignment 1. Largest loading m2 (41.52%); largest observed quarterly signal m2 (67.41%).

D1: current factor correlation with D0 0.036612, factor SD 1.633749, empirical persistence 0.844871, fitted AR(2) (0.992735, -0.168173), range [-3.710353, 3.416882], sign alignment 1. Largest loading fx_reserves_ex_gold (43.09%); largest observed quarterly signal fx_reserves_ex_gold (72.32%).

D2: current factor correlation with D0 0.906796, factor SD 1.791046, empirical persistence 0.962303, fitted AR(2) (1.405649, -0.450348), range [-2.415026, 3.195065], sign alignment 1. Largest loading m2 (47.02%); largest observed quarterly signal m2 (78.93%).

D3: current factor correlation with D0 0.972320, factor SD 1.667480, empirical persistence 0.948543, fitted AR(2) (1.292760, -0.341263), range [-3.336428, 2.627388], sign alignment 1. Largest loading m2 (36.16%); largest observed quarterly signal m2 (54.23%).

Sign-aligned loadings are summarized with mean/median/SD/min/max, current loading and mean absolute share. Drivers retain their fitted factor orientation, so forecasts and within-model absolute shares do not change under diagnostic alignment. D1 cannot contain M2; it uses seven predictors and the unchanged one-factor AR(2) system. No M2 is added separately to the bridge. Removing one predictor can transfer dominance rather than guarantee balance; compare D1’s concentration and variable shares with D0.

For D2, latest_period records the underlying source M2 month; latest_factor_cell_period records its two-month-later assignment in the factor design. Thus the lag does not create a new dated M2 observation. Monthly counts refer to occupied factor-design cells in the target quarter.

industrial_production: current absolute loading share D0 6.223% → D1 13.061%. POS remains without Q3 observations in both models.

pos_turnover: current absolute loading share D0 26.803% → D1 17.713%. POS remains without Q3 observations in both models.

usd_uzs: current absolute loading share D0 13.246% → D1 6.258%. POS remains without Q3 observations in both models.

rub_uzs: current absolute loading share D0 2.950% → D1 5.372%. POS remains without Q3 observations in both models.

Current D0 bridge: intercept=1.409154 (SE 0.791688), factor=0.106812 (SE 0.142576), GDP_lag1=0.778789 (SE 0.127336); condition 20.9486, max non-intercept VIF 1.1538, DW 0.9054, leverage max 0.3119, Cook max 0.3090. SEs are descriptive in the small quarterly sample.

Current D1 bridge: intercept=1.302977 (SE 0.808300), factor=-0.059468 (SE 0.181230), GDP_lag1=0.796684 (SE 0.130196); condition 21.2454, max non-intercept VIF 1.1863, DW 0.9132, leverage max 0.3151, Cook max 0.3277. SEs are descriptive in the small quarterly sample.

Current D2 bridge: intercept=1.445837 (SE 0.794219), factor=0.156659 (SE 0.151955), GDP_lag1=0.769566 (SE 0.127382); condition 20.5896, max non-intercept VIF 1.1364, DW 0.9141, leverage max 0.3146, Cook max 0.2994. SEs are descriptive in the small quarterly sample.

Current D3 bridge: intercept=2.563110 (SE 1.312809), factor=0.159798 (SE 0.121229), GDP_lag1=0.617599 (SE 0.195027); condition 46.2033, max non-intercept VIF 1.0269, DW 0.5872, leverage max 0.3719, Cook max 0.9214. SEs are descriptive in the small quarterly sample.

D1 leave-one-quarter-out: all exclusions improve=False; ΔRMSE range 0.172528 to 0.481326.

E1 leave-one-quarter-out: all exclusions improve=False; ΔRMSE range 0.065522 to 0.175494.

D2 leave-one-quarter-out: all exclusions improve=False; ΔRMSE range -0.007676 to 0.044242.

E2 leave-one-quarter-out: all exclusions improve=False; ΔRMSE range -0.003025 to 0.020611.

D3 leave-one-quarter-out: all exclusions improve=False; ΔRMSE range 0.411786 to 0.525853.

E3 leave-one-quarter-out: all exclusions improve=False; ΔRMSE range 0.150733 to 0.192547.



Training-period correlations of nominal M2 and M2-L2 with each other input are in phase6g1_m2_correlations.csv. They assess duplicated associations, not causality. Factor comparisons and bridge diagnostics provide conditional evidence; neither identifies a causal monetary effect.

## Current nowcasts and decision



| Model | DFM nowcast | Fixed 50/50 ensemble | Δ ensemble vs production |
|---|---:|---:|---:|
| D0 | 8.301152885 | 8.180901341 | 0.000000000 |
| D2 | 8.413700639 | 8.237175217 | 0.056273877 |
| D1 | 8.213181627 | 8.136915711 | -0.043985629 |
| D3 | 8.161792633 | 8.111221214 | -0.069680126 |



Current estimates use the exact archived Oct5 Phase 6E information identity and fixed H3 mask. No refresh or promotion is performed. No missing POS signal is filled with zero or historical values. A large descriptive share alone cannot establish either usefulness or harm; matched extended-history performance, era stability and coverage must carry the model conclusion.

Diagnosis: M2_DOMINANT_BUT_USEFUL. Recommendation: KEEP_CURRENT_DFM_AND_MONITOR_M2. Keep nominal M2 under monitoring; no direct production promotion or M2-L2 promotion follows this audit. Historical value vintages and comparable modern POS scope remain unresolved.

Reproduce: `.venv/Scripts/python.exe -m scripts.phase6g1.run`. Exact numerical rerun, test and protected-hash evidence are attached separately after completed validation.

Validation completed: 173 offline tests passed, 27 numerical CSV artifacts identical across two complete reruns, and 680 protected files unchanged. Publication-mask checks passed; historical predictor-value vintage leakage remains unresolved. See phase6g1_validation.json and phase6g1_determinism.json.

M2 DIAGNOSIS:
M2_DOMINANT_BUT_USEFUL

MODEL RECOMMENDATION:
KEEP_CURRENT_DFM_AND_MONITOR_M2
