# Phase 6G.5 — M2/CPI redundancy and final DFM selection

## Executive summary

Retain the unchanged M0. CPI-only has the best common-span RMSE, but this advantage disappears against the unchanged full-history M0 on exactly the same scoring origins. Only six quarters (18 horizon forecasts), four post-development quarters, and unverified historical predictor value vintages are available. No challenger establishes sufficient incremental out-of-sample value for promotion.

## Evaluation contract

All five models share the frozen target, origins, STRICT GDP vintage gate, predictor availability rules, training-only scaling, one DynamicFactorMQ factor, AR(2), one-sided filtering, and bridge B. STRICT_COMMON_SPAN refits all models on identical monthly training dates. NATIVE_MATCHED_ORIGINS preserves each legitimate estimation history on identical scoring origins; M0 remains the actual benchmark. FULL_AVAILABLE is reported separately and cannot establish superiority. Bias = actual minus forecast. The current information set is the archived Phase6E cutoff, not a fresh October 6 download. COMMON current M0 fails the unchanged convergence gate; its missing estimate and missing differences stay null. The five current comparison estimates use native training histories and the same archived current information set.

## Model comparison scorecard

| model | specification | common_sample_pooled_rmse | full_available_rmse | full_available_n | native_matched_rmse | post_development_rmse | mae | bias | n_matched_origins | n_independent_quarters | H1_rmse | H2_rmse | H3_rmse | within_quarter_revision_std | nowcast_2026q3 | forecast_stability | factor_interpretability | m2_cpi_redundancy_assessment | decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0_CURRENT_M2 | Current M0 | 1.118430 | 0.487529 | 44 | 0.633364 | 1.132615 | 1.053906 | 1.053906 | 18 | 6 | 1.108932 | 1.118711 | 1.127570 | 0.032542 | 8.301153 | See error dispersion and horizon revisions; only six scored quarters | One-sided common factor; signs aligned to M0; descriptive units | Low CPI pairwise correlation; real money = nominal money minus inflation exactly | RETAIN_M0 |
| M1_CPI_ONLY | CPI only | 0.923321 | 0.923321 | 18 | 0.923321 | 0.952786 | 0.867418 | 0.867418 | 18 | 6 | 0.975059 | 0.934722 | 0.856225 | 0.124732 | 8.215914 | See error dispersion and horizon revisions; only six scored quarters | One-sided common factor; signs aligned to M0; descriptive units | Low CPI pairwise correlation; real money = nominal money minus inflation exactly | REJECT |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | 0.953824 | 0.953824 | 18 | 0.953824 | 0.973573 | 0.900741 | 0.900741 | 18 | 6 | 0.997505 | 0.962727 | 0.898601 | 0.123917 | 8.212569 | See error dispersion and horizon revisions; only six scored quarters | One-sided common factor; signs aligned to M0; descriptive units | Low CPI pairwise correlation; real money = nominal money minus inflation exactly | REJECT |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | 0.960822 | 0.960822 | 18 | 0.960822 | 0.992191 | 0.879681 | 0.879681 | 18 | 6 | 0.983812 | 0.964187 | 0.933807 | 0.058890 | 8.218520 | See error dispersion and horizon revisions; only six scored quarters | One-sided common factor; signs aligned to M0; descriptive units | Low CPI pairwise correlation; real money = nominal money minus inflation exactly | REJECT |
| M4_REAL_M2_ONLY | Real M2 only | 1.090065 | 1.090065 | 18 | 1.090065 | 1.073884 | 1.017761 | 1.017761 | 18 | 6 | 1.078804 | 1.088328 | 1.102929 | 0.040402 | 8.166406 | See error dispersion and horizon revisions; only six scored quarters | One-sided common factor; signs aligned to M0; descriptive units | Low CPI pairwise correlation; real money = nominal money minus inflation exactly | REJECT |

## H1/H2/H3 RMSE comparison

| model | label | sample | horizon | n | rmse | mae | bias |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M0_CURRENT_M2 | Current M0 | FULL_AVAILABLE | H1 | 14 | 0.504859 | 0.423510 | 0.397213 |
| M0_CURRENT_M2 | Current M0 | FULL_AVAILABLE | H2 | 15 | 0.482322 | 0.413124 | 0.379993 |
| M0_CURRENT_M2 | Current M0 | FULL_AVAILABLE | H3 | 15 | 0.476113 | 0.396710 | 0.356835 |
| M0_CURRENT_M2 | Current M0 | FULL_AVAILABLE | POOLED | 44 | 0.487529 | 0.410833 | 0.377577 |
| M0_CURRENT_M2 | Current M0 | STRICT_COMMON_SPAN | H1 | 6 | 1.108932 | 1.040764 | 1.040764 |
| M0_CURRENT_M2 | Current M0 | STRICT_COMMON_SPAN | H2 | 6 | 1.118711 | 1.055215 | 1.055215 |
| M0_CURRENT_M2 | Current M0 | STRICT_COMMON_SPAN | H3 | 6 | 1.127570 | 1.065739 | 1.065739 |
| M0_CURRENT_M2 | Current M0 | STRICT_COMMON_SPAN | POOLED | 18 | 1.118430 | 1.053906 | 1.053906 |
| M0_CURRENT_M2 | Current M0 | NATIVE_MATCHED_ORIGINS | H1 | 6 | 0.643809 | 0.543313 | 0.543313 |
| M0_CURRENT_M2 | Current M0 | NATIVE_MATCHED_ORIGINS | H2 | 6 | 0.629045 | 0.537160 | 0.537160 |
| M0_CURRENT_M2 | Current M0 | NATIVE_MATCHED_ORIGINS | H3 | 6 | 0.627107 | 0.530423 | 0.530423 |
| M0_CURRENT_M2 | Current M0 | NATIVE_MATCHED_ORIGINS | POOLED | 18 | 0.633364 | 0.536965 | 0.536965 |
| M1_CPI_ONLY | CPI only | FULL_AVAILABLE | H1 | 6 | 0.975059 | 0.931897 | 0.931897 |
| M1_CPI_ONLY | CPI only | FULL_AVAILABLE | H2 | 6 | 0.934722 | 0.890760 | 0.890760 |
| M1_CPI_ONLY | CPI only | FULL_AVAILABLE | H3 | 6 | 0.856225 | 0.779598 | 0.779598 |
| M1_CPI_ONLY | CPI only | FULL_AVAILABLE | POOLED | 18 | 0.923321 | 0.867418 | 0.867418 |
| M1_CPI_ONLY | CPI only | STRICT_COMMON_SPAN | H1 | 6 | 0.975059 | 0.931897 | 0.931897 |
| M1_CPI_ONLY | CPI only | STRICT_COMMON_SPAN | H2 | 6 | 0.934722 | 0.890760 | 0.890760 |
| M1_CPI_ONLY | CPI only | STRICT_COMMON_SPAN | H3 | 6 | 0.856225 | 0.779598 | 0.779598 |
| M1_CPI_ONLY | CPI only | STRICT_COMMON_SPAN | POOLED | 18 | 0.923321 | 0.867418 | 0.867418 |
| M1_CPI_ONLY | CPI only | NATIVE_MATCHED_ORIGINS | H1 | 6 | 0.975059 | 0.931897 | 0.931897 |
| M1_CPI_ONLY | CPI only | NATIVE_MATCHED_ORIGINS | H2 | 6 | 0.934722 | 0.890760 | 0.890760 |
| M1_CPI_ONLY | CPI only | NATIVE_MATCHED_ORIGINS | H3 | 6 | 0.856225 | 0.779598 | 0.779598 |
| M1_CPI_ONLY | CPI only | NATIVE_MATCHED_ORIGINS | POOLED | 18 | 0.923321 | 0.867418 | 0.867418 |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | FULL_AVAILABLE | H1 | 6 | 0.997505 | 0.957164 | 0.957164 |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | FULL_AVAILABLE | H2 | 6 | 0.962727 | 0.920346 | 0.920346 |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | FULL_AVAILABLE | H3 | 6 | 0.898601 | 0.824712 | 0.824712 |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | FULL_AVAILABLE | POOLED | 18 | 0.953824 | 0.900741 | 0.900741 |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | STRICT_COMMON_SPAN | H1 | 6 | 0.997505 | 0.957164 | 0.957164 |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | STRICT_COMMON_SPAN | H2 | 6 | 0.962727 | 0.920346 | 0.920346 |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | STRICT_COMMON_SPAN | H3 | 6 | 0.898601 | 0.824712 | 0.824712 |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | STRICT_COMMON_SPAN | POOLED | 18 | 0.953824 | 0.900741 | 0.900741 |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | NATIVE_MATCHED_ORIGINS | H1 | 6 | 0.997505 | 0.957164 | 0.957164 |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | NATIVE_MATCHED_ORIGINS | H2 | 6 | 0.962727 | 0.920346 | 0.920346 |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | NATIVE_MATCHED_ORIGINS | H3 | 6 | 0.898601 | 0.824712 | 0.824712 |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | NATIVE_MATCHED_ORIGINS | POOLED | 18 | 0.953824 | 0.900741 | 0.900741 |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | FULL_AVAILABLE | H1 | 6 | 0.983812 | 0.899798 | 0.899798 |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | FULL_AVAILABLE | H2 | 6 | 0.964187 | 0.885504 | 0.885504 |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | FULL_AVAILABLE | H3 | 6 | 0.933807 | 0.853742 | 0.853742 |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | FULL_AVAILABLE | POOLED | 18 | 0.960822 | 0.879681 | 0.879681 |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | STRICT_COMMON_SPAN | H1 | 6 | 0.983812 | 0.899798 | 0.899798 |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | STRICT_COMMON_SPAN | H2 | 6 | 0.964187 | 0.885504 | 0.885504 |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | STRICT_COMMON_SPAN | H3 | 6 | 0.933807 | 0.853742 | 0.853742 |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | STRICT_COMMON_SPAN | POOLED | 18 | 0.960822 | 0.879681 | 0.879681 |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | NATIVE_MATCHED_ORIGINS | H1 | 6 | 0.983812 | 0.899798 | 0.899798 |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | NATIVE_MATCHED_ORIGINS | H2 | 6 | 0.964187 | 0.885504 | 0.885504 |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | NATIVE_MATCHED_ORIGINS | H3 | 6 | 0.933807 | 0.853742 | 0.853742 |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | NATIVE_MATCHED_ORIGINS | POOLED | 18 | 0.960822 | 0.879681 | 0.879681 |
| M4_REAL_M2_ONLY | Real M2 only | FULL_AVAILABLE | H1 | 6 | 1.078804 | 1.004802 | 1.004802 |
| M4_REAL_M2_ONLY | Real M2 only | FULL_AVAILABLE | H2 | 6 | 1.088328 | 1.018711 | 1.018711 |
| M4_REAL_M2_ONLY | Real M2 only | FULL_AVAILABLE | H3 | 6 | 1.102929 | 1.029769 | 1.029769 |
| M4_REAL_M2_ONLY | Real M2 only | FULL_AVAILABLE | POOLED | 18 | 1.090065 | 1.017761 | 1.017761 |
| M4_REAL_M2_ONLY | Real M2 only | STRICT_COMMON_SPAN | H1 | 6 | 1.078804 | 1.004802 | 1.004802 |
| M4_REAL_M2_ONLY | Real M2 only | STRICT_COMMON_SPAN | H2 | 6 | 1.088328 | 1.018711 | 1.018711 |
| M4_REAL_M2_ONLY | Real M2 only | STRICT_COMMON_SPAN | H3 | 6 | 1.102929 | 1.029769 | 1.029769 |
| M4_REAL_M2_ONLY | Real M2 only | STRICT_COMMON_SPAN | POOLED | 18 | 1.090065 | 1.017761 | 1.017761 |
| M4_REAL_M2_ONLY | Real M2 only | NATIVE_MATCHED_ORIGINS | H1 | 6 | 1.078804 | 1.004802 | 1.004802 |
| M4_REAL_M2_ONLY | Real M2 only | NATIVE_MATCHED_ORIGINS | H2 | 6 | 1.088328 | 1.018711 | 1.018711 |
| M4_REAL_M2_ONLY | Real M2 only | NATIVE_MATCHED_ORIGINS | H3 | 6 | 1.102929 | 1.029769 | 1.029769 |
| M4_REAL_M2_ONLY | Real M2 only | NATIVE_MATCHED_ORIGINS | POOLED | 18 | 1.090065 | 1.017761 | 1.017761 |

## Common-sample RMSE comparison

| model | specification | common_sample_pooled_rmse | full_available_rmse | full_available_n | native_matched_rmse | post_development_rmse | mae | bias | n_matched_origins | n_independent_quarters |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0_CURRENT_M2 | Current M0 | 1.118430 | 0.487529 | 44 | 0.633364 | 1.132615 | 1.053906 | 1.053906 | 18 | 6 |
| M1_CPI_ONLY | CPI only | 0.923321 | 0.923321 | 18 | 0.923321 | 0.952786 | 0.867418 | 0.867418 | 18 | 6 |
| M2_NOMINAL_M2_PLUS_CPI | Nominal M2 + CPI | 0.953824 | 0.953824 | 18 | 0.953824 | 0.973573 | 0.900741 | 0.900741 | 18 | 6 |
| M3_REAL_M2_PLUS_CPI | Real M2 + CPI | 0.960822 | 0.960822 | 18 | 0.960822 | 0.992191 | 0.879681 | 0.879681 | 18 | 6 |
| M4_REAL_M2_ONLY | Real M2 only | 1.090065 | 1.090065 | 18 | 1.090065 | 1.073884 | 1.017761 | 1.017761 | 18 | 6 |

## Current 2026Q3 nowcasts

| sample | model | target_quarter | horizon | forecast_origin | nowcast_2026q3 | information_cutoff | stage_cutoff | latest_m2 | latest_cpi | latest_real_m2 | status | difference_vs_M0 | label | factor_signal | factor_signal_unit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | 8.301153 | 2026-10-05 16:54:48.927036 | 2026-09-30 00:00:00 | 2026-08 | nan | 2026-08 | RESEARCH_ONLY | 0.000000 | Current M0 | 1.364026 | training-factor standard deviations; descriptive, not GDP pp |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | 8.215914 | 2026-10-05 16:54:48.927036 | 2026-09-30 00:00:00 | nan | 2026-08 | 2026-08 | RESEARCH_ONLY | -0.085239 | CPI only | -1.883718 | training-factor standard deviations; descriptive, not GDP pp |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | 8.212569 | 2026-10-05 16:54:48.927036 | 2026-09-30 00:00:00 | 2026-08 | 2026-08 | 2026-08 | RESEARCH_ONLY | -0.088584 | Nominal M2 + CPI | -1.880650 | training-factor standard deviations; descriptive, not GDP pp |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | 8.218520 | 2026-10-05 16:54:48.927036 | 2026-09-30 00:00:00 | 2026-08 | 2026-08 | 2026-08 | RESEARCH_ONLY | -0.082633 | Real M2 + CPI | -1.886735 | training-factor standard deviations; descriptive, not GDP pp |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | 8.166406 | 2026-10-05 16:54:48.927036 | 2026-09-30 00:00:00 | 2026-08 | 2026-08 | 2026-08 | RESEARCH_ONLY | -0.134747 | Real M2 only | 1.306330 | training-factor standard deviations; descriptive, not GDP pp |
| COMMON | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | 8.215914 | 2026-10-05 16:54:48.927036 | 2026-09-30 00:00:00 | nan | 2026-08 | 2026-08 | RESEARCH_ONLY | nan | CPI only | -1.883718 | training-factor standard deviations; descriptive, not GDP pp |
| COMMON | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | 8.212569 | 2026-10-05 16:54:48.927036 | 2026-09-30 00:00:00 | 2026-08 | 2026-08 | 2026-08 | RESEARCH_ONLY | nan | Nominal M2 + CPI | -1.880650 | training-factor standard deviations; descriptive, not GDP pp |
| COMMON | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | 8.218520 | 2026-10-05 16:54:48.927036 | 2026-09-30 00:00:00 | 2026-08 | 2026-08 | 2026-08 | RESEARCH_ONLY | nan | Real M2 + CPI | -1.886735 | training-factor standard deviations; descriptive, not GDP pp |
| COMMON | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | 8.166406 | 2026-10-05 16:54:48.927036 | 2026-09-30 00:00:00 | 2026-08 | 2026-08 | 2026-08 | RESEARCH_ONLY | nan | Real M2 only | 1.306330 | training-factor standard deviations; descriptive, not GDP pp |

## M2/CPI correlation diagnostics

| variable_a | variable_b | N | start | end | pearson | spearman |
| --- | --- | --- | --- | --- | --- | --- |
| nominal_m2 | cpi | 56 | 2022-01-31 00:00:00 | 2026-08-31 00:00:00 | 0.041058 | -0.031169 |
| nominal_m2 | real_m2 | 56 | 2022-01-31 00:00:00 | 2026-08-31 00:00:00 | 0.971670 | 0.953110 |
| cpi | real_m2 | 56 | 2022-01-31 00:00:00 | 2026-08-31 00:00:00 | -0.196248 | -0.255229 |

## VIF diagnostics

| specification | variable | N | vif | diagnostic_only |
| --- | --- | --- | --- | --- |
| nominal_m2 + cpi | nominal_m2 | 56 | 1.001689 | True |
| nominal_m2 + cpi | cpi | 56 | 1.001689 | True |
| real_m2 + cpi | real_m2 | 56 | 1.040056 | True |
| real_m2 + cpi | cpi | 56 | 1.040056 | True |
| nominal_m2 + real_m2 | nominal_m2 | 56 | 17.902625 | True |
| nominal_m2 + real_m2 | real_m2 | 56 | 17.902625 | True |
| nominal_m2 + cpi + real_m2 | nominal_m2 | 56 | inf | True |
| nominal_m2 + cpi + real_m2 | cpi | 56 | inf | True |
| nominal_m2 + cpi + real_m2 | real_m2 | 56 | inf | True |

## DFM factor signals — descriptive standardized units

| sample | model | target_quarter | horizon | forecast_origin | variable | months | descriptive_signal | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | industrial_production | 1 | 0.050184 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | ppi | 2 | 0.031179 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | usd_uzs | 3 | 0.151426 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | rub_uzs | 3 | -0.035020 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | gold_price | 2 | 0.003506 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2 | 0.726074 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | fx_reserves_ex_gold | 2 | -0.079747 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | pos_turnover | 0 | nan | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | industrial_production | 1 | -0.133683 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | ppi | 2 | -0.020261 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | usd_uzs | 3 | -0.069417 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | rub_uzs | 3 | 0.014664 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | gold_price | 2 | -0.005534 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | fx_reserves_ex_gold | 2 | 0.022401 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | pos_turnover | 0 | nan | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2 | -1.176504 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | industrial_production | 1 | -0.129544 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | ppi | 2 | -0.019424 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | usd_uzs | 3 | -0.066715 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | rub_uzs | 3 | 0.013992 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | gold_price | 2 | -0.005345 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2 | 0.065184 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | fx_reserves_ex_gold | 2 | 0.020995 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | pos_turnover | 0 | nan | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2 | -1.138091 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | industrial_production | 1 | -0.119089 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | ppi | 2 | -0.018246 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | usd_uzs | 3 | -0.062339 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | rub_uzs | 3 | 0.013245 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | gold_price | 2 | -0.004922 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2 | -0.092218 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | fx_reserves_ex_gold | 2 | 0.020767 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | pos_turnover | 0 | nan | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | cpi | 2 | -1.049255 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | industrial_production | 1 | -0.040706 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | ppi | 2 | 0.068471 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | usd_uzs | 3 | 0.187525 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | rub_uzs | 3 | -0.060108 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | gold_price | 2 | -0.001492 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | m2 | 2 | 0.798906 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | fx_reserves_ex_gold | 2 | -0.314703 | loading times quarterly mean z; not additive GDP contribution |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | pos_turnover | 0 | nan | loading times quarterly mean z; not additive GDP contribution |

## Factor-loading comparison

| sample | model | target_quarter | horizon | forecast_origin | current | variable | factor | loading | abs_loading | rank | loading_sign | correlation_with_factor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | industrial_production | 1 | 0.077893 | 0.077893 | 4 | 1 | 0.135392 |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | ppi | 1 | -0.041512 | 0.041512 | 6 | -1 | -0.076962 |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | usd_uzs | 1 | -0.165815 | 0.165815 | 3 | -1 | -0.310640 |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | rub_uzs | 1 | 0.036923 | 0.036923 | 7 | 1 | 0.079467 |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | gold_price | 1 | 0.016334 | 0.016334 | 8 | 1 | 0.027666 |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | m2 | 1 | 0.519784 | 0.519784 | 1 | 1 | 0.996040 |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | fx_reserves_ex_gold | 1 | 0.057998 | 0.057998 | 5 | 1 | 0.101613 |
| NATIVE | M0_CURRENT_M2 | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | pos_turnover | 1 | 0.335507 | 0.335507 | 2 | 1 | 0.627665 |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | industrial_production | 1 | -0.298819 | 0.298819 | 3 | -1 | -0.474405 |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | ppi | 1 | 0.022742 | 0.022742 | 6 | 1 | 0.032749 |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | usd_uzs | 1 | 0.085659 | 0.085659 | 4 | 1 | 0.133110 |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | rub_uzs | 1 | -0.019227 | 0.019227 | 8 | -1 | -0.042941 |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | gold_price | 1 | -0.040980 | 0.040980 | 5 | -1 | -0.068246 |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | fx_reserves_ex_gold | 1 | -0.021052 | 0.021052 | 7 | -1 | -0.030624 |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | pos_turnover | 1 | 0.387153 | 0.387153 | 2 | 1 | 0.624489 |
| NATIVE | M1_CPI_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | cpi | 1 | 0.625836 | 0.625836 | 1 | 1 | 0.998051 |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | industrial_production | 1 | -0.289567 | 0.289567 | 3 | -1 | -0.475175 |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | ppi | 1 | 0.021802 | 0.021802 | 7 | 1 | 0.032341 |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | usd_uzs | 1 | 0.082325 | 0.082325 | 4 | 1 | 0.132062 |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | rub_uzs | 1 | -0.018346 | 0.018346 | 9 | -1 | -0.042647 |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | gold_price | 1 | -0.039579 | 0.039579 | 6 | -1 | -0.068246 |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | m2 | 1 | 0.069471 | 0.069471 | 5 | 1 | 0.113458 |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | fx_reserves_ex_gold | 1 | -0.019730 | 0.019730 | 8 | -1 | -0.029587 |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | pos_turnover | 1 | 0.374673 | 0.374673 | 2 | 1 | 0.624668 |
| NATIVE | M2_NOMINAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | cpi | 1 | 0.605403 | 0.605403 | 1 | 1 | 0.997966 |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | industrial_production | 1 | -0.266198 | 0.266198 | 3 | -1 | -0.473968 |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | ppi | 1 | 0.020481 | 0.020481 | 7 | 1 | 0.032988 |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | usd_uzs | 1 | 0.076926 | 0.076926 | 4 | 1 | 0.133986 |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | rub_uzs | 1 | -0.017366 | 0.017366 | 9 | -1 | -0.043355 |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | gold_price | 1 | -0.036444 | 0.036444 | 6 | -1 | -0.068101 |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | real_m2 | 1 | -0.067340 | 0.067340 | 5 | -1 | -0.121438 |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | fx_reserves_ex_gold | 1 | -0.019516 | 0.019516 | 8 | -1 | -0.031889 |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | pos_turnover | 1 | 0.345673 | 0.345673 | 2 | 1 | 0.624717 |
| NATIVE | M3_REAL_M2_PLUS_CPI | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | cpi | 1 | 0.558147 | 0.558147 | 1 | 1 | 0.998017 |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | industrial_production | 1 | -0.090990 | 0.090990 | 5 | -1 | -0.172120 |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | ppi | 1 | -0.076855 | 0.076855 | 7 | -1 | -0.129653 |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | usd_uzs | 1 | -0.231405 | 0.231405 | 4 | -1 | -0.393967 |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | rub_uzs | 1 | 0.078809 | 0.078809 | 6 | 1 | 0.144919 |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | gold_price | 1 | -0.011049 | 0.011049 | 8 | -1 | -0.027748 |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | real_m2 | 1 | 0.583381 | 0.583381 | 1 | 1 | 0.995399 |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | fx_reserves_ex_gold | 1 | 0.295749 | 0.295749 | 2 | 1 | 0.478038 |
| NATIVE | M4_REAL_M2_ONLY | 2026Q3 | H3 | 2026-10-05 16:54:48.927036 | True | pos_turnover | 1 | 0.246943 | 0.246943 | 3 | 1 | 0.483998 |

## Factor path correlations

| sample | target_quarter | horizon | current | model_a | model_b | N | correlation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NATIVE | 2026Q3 | H3 | True | M0_CURRENT_M2 | M1_CPI_ONLY | 57 | 0.029624 |
| NATIVE | 2026Q3 | H3 | True | M0_CURRENT_M2 | M2_NOMINAL_M2_PLUS_CPI | 57 | 0.032036 |
| NATIVE | 2026Q3 | H3 | True | M0_CURRENT_M2 | M3_REAL_M2_PLUS_CPI | 57 | 0.027261 |
| NATIVE | 2026Q3 | H3 | True | M0_CURRENT_M2 | M4_REAL_M2_ONLY | 57 | 0.971807 |
| NATIVE | 2026Q3 | H3 | True | M1_CPI_ONLY | M2_NOMINAL_M2_PLUS_CPI | 57 | 0.999996 |
| NATIVE | 2026Q3 | H3 | True | M1_CPI_ONLY | M3_REAL_M2_PLUS_CPI | 57 | 0.999997 |
| NATIVE | 2026Q3 | H3 | True | M1_CPI_ONLY | M4_REAL_M2_ONLY | 57 | -0.205163 |
| NATIVE | 2026Q3 | H3 | True | M2_NOMINAL_M2_PLUS_CPI | M3_REAL_M2_PLUS_CPI | 57 | 0.999988 |
| NATIVE | 2026Q3 | H3 | True | M2_NOMINAL_M2_PLUS_CPI | M4_REAL_M2_ONLY | 57 | -0.202802 |
| NATIVE | 2026Q3 | H3 | True | M3_REAL_M2_PLUS_CPI | M4_REAL_M2_ONLY | 57 | -0.207478 |

## Factor and bridge fit

| model | matched_fits | mean_factor_variance_explained | mean_bridge_fit_rmse | mean_bridge_r2 |
| --- | --- | --- | --- | --- |
| M0_CURRENT_M2 | 18 | 0.236078 | 0.643613 | 0.250500 |
| M1_CPI_ONLY | 18 | 0.226237 | 0.616663 | 0.298439 |
| M2_NOMINAL_M2_PLUS_CPI | 18 | 0.253494 | 0.617514 | 0.297522 |
| M3_REAL_M2_PLUS_CPI | 18 | 0.246312 | 0.635798 | 0.264914 |
| M4_REAL_M2_ONLY | 18 | 0.239837 | 0.640595 | 0.255231 |

## Incremental information / ablation

| comparison | before | after | delta_common_sample_pooled_rmse | delta_mae | delta_bias | delta_mean_factor_variance_explained | delta_mean_bridge_fit_rmse | delta_mean_bridge_r2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CPI conditional on nominal M2 | M0_CURRENT_M2 | M2_NOMINAL_M2_PLUS_CPI | -0.164606 | -0.153165 | -0.153165 | 0.017416 | -0.026099 | 0.047021 |
| CPI conditional on real M2 | M4_REAL_M2_ONLY | M3_REAL_M2_PLUS_CPI | -0.129243 | -0.138079 | -0.138079 | 0.006475 | -0.004797 | 0.009683 |
| nominal M2 conditional on CPI | M1_CPI_ONLY | M2_NOMINAL_M2_PLUS_CPI | 0.030503 | 0.033322 | 0.033322 | 0.027257 | 0.000851 | -0.000917 |
| real M2 conditional on CPI | M1_CPI_ONLY | M3_REAL_M2_PLUS_CPI | 0.037501 | 0.012263 | 0.012263 | 0.020075 | 0.019135 | -0.033525 |

## Information-content interpretation

CPI is not largely duplicated by nominal M2: their Pearson correlation is about 0.041; nominal and real M2 are highly correlated (about 0.972). Adding nominal M2 to CPI raises common-span RMSE by 0.0305 pp (3.30%); adding real M2 raises it by 0.0375 pp (4.06%). Adding CPI to nominal or real M2 improves common-span performance, but does not beat the unchanged native M0 on matched origins. The current native CPI-containing factor paths correlate above 0.9999 with one another, but only about 0.03 with native M0 over overlapping months. Real-M2-only correlates about 0.972 with M0. CPI therefore materially changes the estimated common factor; adding money to CPI contributes little extra factor-path variation. These native comparisons also reflect estimation-history differences; COMMON path correlations are saved separately. This is evidence of changed factor structure, not demonstrated incremental GDP forecasting value. REJECT means reject promotion on this evidence, not permanently exclude a variable. Every challenger improves all three horizons against common-span M0, but none beats the unchanged native benchmark. Only six scored quarters limit robustness; the best short-span model has 3.8 times the M0 short-span horizon-revision volatility.

## Rolling 24-month correlations

| date | variable_a | variable_b | pearson_24m | spearman_24m | window_months |
| --- | --- | --- | --- | --- | --- |
| 2025-09-30 00:00:00 | nominal_m2 | cpi | 0.414800 | 0.234783 | 24 |
| 2025-10-31 00:00:00 | nominal_m2 | cpi | 0.334785 | 0.186087 | 24 |
| 2025-11-30 00:00:00 | nominal_m2 | cpi | 0.202410 | 0.038261 | 24 |
| 2025-12-31 00:00:00 | nominal_m2 | cpi | 0.051546 | -0.111304 | 24 |
| 2026-01-31 00:00:00 | nominal_m2 | cpi | -0.137648 | -0.289565 | 24 |
| 2026-02-28 00:00:00 | nominal_m2 | cpi | -0.313543 | -0.453043 | 24 |
| 2026-03-31 00:00:00 | nominal_m2 | cpi | -0.522003 | -0.609565 | 24 |
| 2026-04-30 00:00:00 | nominal_m2 | cpi | -0.742107 | -0.737391 | 24 |
| 2026-05-31 00:00:00 | nominal_m2 | cpi | -0.733532 | -0.732174 | 24 |
| 2026-06-30 00:00:00 | nominal_m2 | cpi | -0.720698 | -0.718261 | 24 |
| 2026-07-31 00:00:00 | nominal_m2 | cpi | -0.716560 | -0.700870 | 24 |
| 2026-08-31 00:00:00 | nominal_m2 | cpi | -0.709129 | -0.673043 | 24 |
| 2025-09-30 00:00:00 | nominal_m2 | real_m2 | 0.992083 | 0.952174 | 24 |
| 2025-10-31 00:00:00 | nominal_m2 | real_m2 | 0.989753 | 0.925217 | 24 |
| 2025-11-30 00:00:00 | nominal_m2 | real_m2 | 0.985443 | 0.923478 | 24 |
| 2025-12-31 00:00:00 | nominal_m2 | real_m2 | 0.981095 | 0.923478 | 24 |
| 2026-01-31 00:00:00 | nominal_m2 | real_m2 | 0.977519 | 0.923478 | 24 |
| 2026-02-28 00:00:00 | nominal_m2 | real_m2 | 0.975818 | 0.923478 | 24 |
| 2026-03-31 00:00:00 | nominal_m2 | real_m2 | 0.978743 | 0.923478 | 24 |
| 2026-04-30 00:00:00 | nominal_m2 | real_m2 | 0.984086 | 0.922609 | 24 |
| 2026-05-31 00:00:00 | nominal_m2 | real_m2 | 0.979089 | 0.920000 | 24 |
| 2026-06-30 00:00:00 | nominal_m2 | real_m2 | 0.975535 | 0.917391 | 24 |
| 2026-07-31 00:00:00 | nominal_m2 | real_m2 | 0.973556 | 0.913913 | 24 |
| 2026-08-31 00:00:00 | nominal_m2 | real_m2 | 0.963018 | 0.913913 | 24 |
| 2025-09-30 00:00:00 | cpi | real_m2 | 0.297247 | 0.101739 | 24 |
| 2025-10-31 00:00:00 | cpi | real_m2 | 0.196802 | -0.008696 | 24 |
| 2025-11-30 00:00:00 | cpi | real_m2 | 0.032979 | -0.153913 | 24 |
| 2025-12-31 00:00:00 | cpi | real_m2 | -0.142698 | -0.286957 | 24 |
| 2026-01-31 00:00:00 | cpi | real_m2 | -0.343393 | -0.453913 | 24 |
| 2026-02-28 00:00:00 | cpi | real_m2 | -0.513525 | -0.606087 | 24 |
| 2026-03-31 00:00:00 | cpi | real_m2 | -0.685837 | -0.755652 | 24 |
| 2026-04-30 00:00:00 | cpi | real_m2 | -0.849400 | -0.874783 | 24 |
| 2026-05-31 00:00:00 | cpi | real_m2 | -0.856455 | -0.875652 | 24 |
| 2026-06-30 00:00:00 | cpi | real_m2 | -0.855473 | -0.867826 | 24 |
| 2026-07-31 00:00:00 | cpi | real_m2 | -0.856961 | -0.860000 | 24 |
| 2026-08-31 00:00:00 | cpi | real_m2 | -0.872878 | -0.834783 | 24 |

## Forecast stability

| model | error_std | max_abs_error | within_quarter_revision_std | within_quarter_mean_abs_revision | quarter_to_quarter_forecast_change_std | quarter_to_quarter_change_n | quarters_beating_m0 | share_quarters_beating_m0 | m0_win_comparison | quarters_beating_umidas | share_quarters_beating_umidas | umidas_quarters | pre_development_rmse | post_development_rmse | worst_H1_absolute_error | worst_H2_absolute_error | worst_H3_absolute_error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0_CURRENT_M2 | 0.385244 | 1.628902 | 0.032542 | 0.022908 | 0.324723 | 15 | 0 | 0.000000 | COMMON refit M0; native benchmark performance reported separately | 0 | 0.000000 | 6 | 1.089507 | 1.132615 | 1.628902 | 1.600637 | 1.597869 |
| M1_CPI_ONLY | 0.325570 | 1.428481 | 0.124732 | 0.095398 | 0.260903 | 15 | 5 | 0.833333 | COMMON refit M0; native benchmark performance reported separately | 1 | 0.166667 | 6 | 0.861374 | 0.952786 | 1.428481 | 1.369597 | 1.342037 |
| M2_NOMINAL_M2_PLUS_CPI | 0.322859 | 1.444131 | 0.123917 | 0.088580 | 0.262816 | 15 | 5 | 0.833333 | COMMON refit M0; native benchmark performance reported separately | 1 | 0.166667 | 6 | 0.913046 | 0.973573 | 1.444131 | 1.387979 | 1.361088 |
| M3_REAL_M2_PLUS_CPI | 0.397648 | 1.566400 | 0.058890 | 0.048372 | 0.374183 | 15 | 6 | 1.000000 | COMMON refit M0; native benchmark performance reported separately | 1 | 0.166667 | 6 | 0.894790 | 0.992191 | 1.566400 | 1.524746 | 1.524771 |
| M4_REAL_M2_ONLY | 0.401709 | 1.553802 | 0.040402 | 0.029670 | 0.327435 | 15 | 3 | 0.500000 | COMMON refit M0; native benchmark performance reported separately | 0 | 0.000000 | 6 | 1.121727 | 1.073884 | 1.553802 | 1.509640 | 1.510919 |

## Selection robustness flags

| model | horizons_improving_vs_common_m0 | one_horizon_only | few_quarters | shorter_estimation_history_than_native_m0 | revision_volatility_more_than_twice_m0 | beats_unchanged_m0_on_matched_origins | common_span_rmse_improvement_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M0_CURRENT_M2 | 0 | False | True | False | False | False | 0.000000 |
| M1_CPI_ONLY | 3 | False | True | True | True | False | 17.444878 |
| M2_NOMINAL_M2_PLUS_CPI | 3 | False | True | True | True | False | 14.717565 |
| M3_REAL_M2_PLUS_CPI | 3 | False | True | True | False | False | 14.091911 |
| M4_REAL_M2_ONLY | 3 | False | True | True | False | False | 2.536132 |

## Historical matched forecasts

| target_quarter | horizon | sample | model | forecast_origin | actual | prediction |
| --- | --- | --- | --- | --- | --- | --- |
| 2025Q1 | H1 | COMMON | M0_CURRENT_M2 | 2025-01-31 00:00:00 | 6.800000 | 5.962173 |
| 2025Q1 | H1 | COMMON | M1_CPI_ONLY | 2025-01-31 00:00:00 | 6.800000 | 6.213437 |
| 2025Q1 | H1 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2025-01-31 00:00:00 | 6.800000 | 6.170545 |
| 2025Q1 | H1 | COMMON | M3_REAL_M2_PLUS_CPI | 2025-01-31 00:00:00 | 6.800000 | 6.190353 |
| 2025Q1 | H1 | COMMON | M4_REAL_M2_ONLY | 2025-01-31 00:00:00 | 6.800000 | 5.930414 |
| 2025Q1 | H2 | COMMON | M0_CURRENT_M2 | 2025-02-28 00:00:00 | 6.800000 | 5.919018 |
| 2025Q1 | H2 | COMMON | M1_CPI_ONLY | 2025-02-28 00:00:00 | 6.800000 | 6.164245 |
| 2025Q1 | H2 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2025-02-28 00:00:00 | 6.800000 | 6.123376 |
| 2025Q1 | H2 | COMMON | M3_REAL_M2_PLUS_CPI | 2025-02-28 00:00:00 | 6.800000 | 6.140357 |
| 2025Q1 | H2 | COMMON | M4_REAL_M2_ONLY | 2025-02-28 00:00:00 | 6.800000 | 5.879144 |
| 2025Q1 | H3 | COMMON | M0_CURRENT_M2 | 2025-03-31 00:00:00 | 6.800000 | 5.841386 |
| 2025Q1 | H3 | COMMON | M1_CPI_ONLY | 2025-03-31 00:00:00 | 6.800000 | 6.130801 |
| 2025Q1 | H3 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2025-03-31 00:00:00 | 6.800000 | 6.072600 |
| 2025Q1 | H3 | COMMON | M3_REAL_M2_PLUS_CPI | 2025-03-31 00:00:00 | 6.800000 | 6.093635 |
| 2025Q1 | H3 | COMMON | M4_REAL_M2_ONLY | 2025-03-31 00:00:00 | 6.800000 | 5.791133 |
| 2025Q2 | H1 | COMMON | M0_CURRENT_M2 | 2025-04-30 00:00:00 | 7.200000 | 5.986457 |
| 2025Q2 | H1 | COMMON | M1_CPI_ONLY | 2025-04-30 00:00:00 | 7.200000 | 6.062453 |
| 2025Q2 | H1 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2025-04-30 00:00:00 | 7.200000 | 6.032496 |
| 2025Q2 | H1 | COMMON | M3_REAL_M2_PLUS_CPI | 2025-04-30 00:00:00 | 7.200000 | 6.041864 |
| 2025Q2 | H1 | COMMON | M4_REAL_M2_ONLY | 2025-04-30 00:00:00 | 7.200000 | 5.975271 |
| 2025Q2 | H2 | COMMON | M0_CURRENT_M2 | 2025-05-31 00:00:00 | 7.200000 | 5.922444 |
| 2025Q2 | H2 | COMMON | M1_CPI_ONLY | 2025-05-31 00:00:00 | 7.200000 | 6.129571 |
| 2025Q2 | H2 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2025-05-31 00:00:00 | 7.200000 | 6.073897 |
| 2025Q2 | H2 | COMMON | M3_REAL_M2_PLUS_CPI | 2025-05-31 00:00:00 | 7.200000 | 6.092139 |
| 2025Q2 | H2 | COMMON | M4_REAL_M2_ONLY | 2025-05-31 00:00:00 | 7.200000 | 5.902497 |
| 2025Q2 | H3 | COMMON | M0_CURRENT_M2 | 2025-06-30 00:00:00 | 7.200000 | 5.927092 |
| 2025Q2 | H3 | COMMON | M1_CPI_ONLY | 2025-06-30 00:00:00 | 7.200000 | 6.296736 |
| 2025Q2 | H3 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2025-06-30 00:00:00 | 7.200000 | 6.206221 |
| 2025Q2 | H3 | COMMON | M3_REAL_M2_PLUS_CPI | 2025-06-30 00:00:00 | 7.200000 | 6.235887 |
| 2025Q2 | H3 | COMMON | M4_REAL_M2_ONLY | 2025-06-30 00:00:00 | 7.200000 | 5.879323 |
| 2025Q3 | H1 | COMMON | M0_CURRENT_M2 | 2025-07-31 00:00:00 | 7.600000 | 6.354862 |
| 2025Q3 | H1 | COMMON | M1_CPI_ONLY | 2025-07-31 00:00:00 | 7.600000 | 6.617589 |
| 2025Q3 | H1 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2025-07-31 00:00:00 | 7.600000 | 6.605518 |
| 2025Q3 | H1 | COMMON | M3_REAL_M2_PLUS_CPI | 2025-07-31 00:00:00 | 7.600000 | 6.615528 |
| 2025Q3 | H1 | COMMON | M4_REAL_M2_ONLY | 2025-07-31 00:00:00 | 7.600000 | 6.356198 |
| 2025Q3 | H2 | COMMON | M0_CURRENT_M2 | 2025-08-31 00:00:00 | 7.600000 | 6.364975 |
| 2025Q3 | H2 | COMMON | M1_CPI_ONLY | 2025-08-31 00:00:00 | 7.600000 | 6.584739 |
| 2025Q3 | H2 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2025-08-31 00:00:00 | 7.600000 | 6.569337 |
| 2025Q3 | H2 | COMMON | M3_REAL_M2_PLUS_CPI | 2025-08-31 00:00:00 | 7.600000 | 6.576961 |
| 2025Q3 | H2 | COMMON | M4_REAL_M2_ONLY | 2025-08-31 00:00:00 | 7.600000 | 6.363563 |
| 2025Q3 | H3 | COMMON | M0_CURRENT_M2 | 2025-09-30 00:00:00 | 7.600000 | 6.368056 |
| 2025Q3 | H3 | COMMON | M1_CPI_ONLY | 2025-09-30 00:00:00 | 7.600000 | 6.617118 |
| 2025Q3 | H3 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2025-09-30 00:00:00 | 7.600000 | 6.582251 |
| 2025Q3 | H3 | COMMON | M3_REAL_M2_PLUS_CPI | 2025-09-30 00:00:00 | 7.600000 | 6.594067 |
| 2025Q3 | H3 | COMMON | M4_REAL_M2_ONLY | 2025-09-30 00:00:00 | 7.600000 | 6.365888 |
| 2025Q4 | H1 | COMMON | M0_CURRENT_M2 | 2025-10-31 00:00:00 | 7.700000 | 6.785528 |
| 2025Q4 | H1 | COMMON | M1_CPI_ONLY | 2025-10-31 00:00:00 | 7.700000 | 6.980670 |
| 2025Q4 | H1 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2025-10-31 00:00:00 | 7.700000 | 6.937183 |
| 2025Q4 | H1 | COMMON | M3_REAL_M2_PLUS_CPI | 2025-10-31 00:00:00 | 7.700000 | 6.949905 |
| 2025Q4 | H1 | COMMON | M4_REAL_M2_ONLY | 2025-10-31 00:00:00 | 7.700000 | 6.887470 |
| 2025Q4 | H2 | COMMON | M0_CURRENT_M2 | 2025-11-30 00:00:00 | 7.700000 | 6.786941 |
| 2025Q4 | H2 | COMMON | M1_CPI_ONLY | 2025-11-30 00:00:00 | 7.700000 | 7.076280 |
| 2025Q4 | H2 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2025-11-30 00:00:00 | 7.700000 | 7.034481 |
| 2025Q4 | H2 | COMMON | M3_REAL_M2_PLUS_CPI | 2025-11-30 00:00:00 | 7.700000 | 7.049055 |
| 2025Q4 | H2 | COMMON | M4_REAL_M2_ONLY | 2025-11-30 00:00:00 | 7.700000 | 6.892946 |
| 2025Q4 | H3 | COMMON | M0_CURRENT_M2 | 2025-12-31 00:00:00 | 7.700000 | 6.778692 |
| 2025Q4 | H3 | COMMON | M1_CPI_ONLY | 2025-12-31 00:00:00 | 7.700000 | 7.131659 |
| 2025Q4 | H3 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2025-12-31 00:00:00 | 7.700000 | 7.075813 |
| 2025Q4 | H3 | COMMON | M3_REAL_M2_PLUS_CPI | 2025-12-31 00:00:00 | 7.700000 | 7.093923 |
| 2025Q4 | H3 | COMMON | M4_REAL_M2_ONLY | 2025-12-31 00:00:00 | 7.700000 | 6.901657 |
| 2026Q1 | H1 | COMMON | M0_CURRENT_M2 | 2026-01-31 00:00:00 | 8.700000 | 7.071098 |
| 2026Q1 | H1 | COMMON | M1_CPI_ONLY | 2026-01-31 00:00:00 | 8.700000 | 7.271519 |
| 2026Q1 | H1 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2026-01-31 00:00:00 | 8.700000 | 7.255869 |
| 2026Q1 | H1 | COMMON | M3_REAL_M2_PLUS_CPI | 2026-01-31 00:00:00 | 8.700000 | 7.133600 |
| 2026Q1 | H1 | COMMON | M4_REAL_M2_ONLY | 2026-01-31 00:00:00 | 8.700000 | 7.146198 |
| 2026Q1 | H2 | COMMON | M0_CURRENT_M2 | 2026-02-28 00:00:00 | 8.700000 | 7.099363 |
| 2026Q1 | H2 | COMMON | M1_CPI_ONLY | 2026-02-28 00:00:00 | 8.700000 | 7.330403 |
| 2026Q1 | H2 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2026-02-28 00:00:00 | 8.700000 | 7.312021 |
| 2026Q1 | H2 | COMMON | M3_REAL_M2_PLUS_CPI | 2026-02-28 00:00:00 | 8.700000 | 7.175254 |
| 2026Q1 | H2 | COMMON | M4_REAL_M2_ONLY | 2026-02-28 00:00:00 | 8.700000 | 7.190360 |
| 2026Q1 | H3 | COMMON | M0_CURRENT_M2 | 2026-03-31 00:00:00 | 8.700000 | 7.102131 |
| 2026Q1 | H3 | COMMON | M1_CPI_ONLY | 2026-03-31 00:00:00 | 8.700000 | 7.357963 |
| 2026Q1 | H3 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2026-03-31 00:00:00 | 8.700000 | 7.338912 |
| 2026Q1 | H3 | COMMON | M3_REAL_M2_PLUS_CPI | 2026-03-31 00:00:00 | 8.700000 | 7.175229 |
| 2026Q1 | H3 | COMMON | M4_REAL_M2_ONLY | 2026-03-31 00:00:00 | 8.700000 | 7.189081 |
| 2026Q2 | H1 | COMMON | M0_CURRENT_M2 | 2026-04-30 00:00:00 | 8.500000 | 8.095295 |
| 2026Q2 | H1 | COMMON | M1_CPI_ONLY | 2026-04-30 00:00:00 | 8.500000 | 7.762949 |
| 2026Q2 | H1 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2026-04-30 00:00:00 | 8.500000 | 7.755403 |
| 2026Q2 | H1 | COMMON | M3_REAL_M2_PLUS_CPI | 2026-04-30 00:00:00 | 8.500000 | 8.169961 |
| 2026Q2 | H1 | COMMON | M4_REAL_M2_ONLY | 2026-04-30 00:00:00 | 8.500000 | 8.175636 |
| 2026Q2 | H2 | COMMON | M0_CURRENT_M2 | 2026-05-31 00:00:00 | 8.500000 | 8.075970 |
| 2026Q2 | H2 | COMMON | M1_CPI_ONLY | 2026-05-31 00:00:00 | 8.500000 | 7.870200 |
| 2026Q2 | H2 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2026-05-31 00:00:00 | 8.500000 | 7.864813 |
| 2026Q2 | H2 | COMMON | M3_REAL_M2_PLUS_CPI | 2026-05-31 00:00:00 | 8.500000 | 8.153209 |
| 2026Q2 | H2 | COMMON | M4_REAL_M2_ONLY | 2026-05-31 00:00:00 | 8.500000 | 8.159224 |
| 2026Q2 | H3 | COMMON | M0_CURRENT_M2 | 2026-06-30 00:00:00 | 8.500000 | 8.088209 |
| 2026Q2 | H3 | COMMON | M1_CPI_ONLY | 2026-06-30 00:00:00 | 8.500000 | 8.288137 |
| 2026Q2 | H3 | COMMON | M2_NOMINAL_M2_PLUS_CPI | 2026-06-30 00:00:00 | 8.500000 | 8.275929 |
| 2026Q2 | H3 | COMMON | M3_REAL_M2_PLUS_CPI | 2026-06-30 00:00:00 | 8.500000 | 8.184806 |
| 2026Q2 | H3 | COMMON | M4_REAL_M2_ONLY | 2026-06-30 00:00:00 | 8.500000 | 8.194307 |

## Interpretation and limitations

VIF is descriptive only and is not an automatic rejection criterion in a factor model. Correlation does not imply a multicollinearity problem in a DFM; high correlation does not prove a variable must be removed. The three-way VIF is infinite because real M2 YoY = nominal M2 YoY minus CPI YoY exactly; no tested model contains all three. Factor variance explained is the mean training squared correlation with the filtered factor, a descriptive projection measure, not a PCA eigenvalue or structural GDP contribution. GDP bridge fit is descriptive; in-sample R² does not determine selection. Loading signs are arbitrary and aligned within each origin. Within-quarter revisions compare H1/H2/H3 for the same target; quarter-to-quarter forecast changes also reflect different GDP targets and are not same-target revisions. The inherited post-development sample has already been inspected. Formal independent holdout evidence is unavailable. No release dates or vintage values were invented.

## Testing and preservation

Full relevant suite: 245 passed, 2 failed, 0 errors. All 14 dedicated Phase6G.5 checks pass. The two legacy failures are Phase6B.2 test_protected_artifacts_unchanged and Phase6C test_protected_inventory_and_saved_metrics: their older inventory hashes differ from the newer repository state. The flagged current dashboard, master data, and processed gold payload match the task-start hashes. All 943 current protected files are unchanged. Full estimator reruns reproduce the scientific artifacts exactly. See phase6g5_tests.xml, phase6g5_test_results.json and phase6g5_validation.json for explicit status.

## Final recommendation

Retain the unchanged M0. CPI-only has the best common-span RMSE, but this advantage disappears against the unchanged full-history M0 on exactly the same scoring origins. Only six quarters (18 horizon forecasts), four post-development quarters, and unverified historical predictor value vintages are available. No challenger establishes sufficient incremental out-of-sample value for promotion.

Production unchanged; no automatic promotion. All outputs are isolated research artifacts.

PHASE6G5_RETAIN_M0
