# Revised Phase 7E factors — research experiment

Research experiment only. Production COMBO_50_50 remains **8.180901340616275%**; no promotion. Original Phase 7E outputs, master datasets and registry are preserved.

The target is **2026Q3 cumulative real year-to-date GDP YoY**, not standalone-quarter growth. The unchanged research cutoff is **2026-10-05**. H1/H2/H3 are target-quarter month ends.

**Information limit:** predictor release dates and historical vintages are absent from the original research workbook. The unchanged assumed-lag gate is respected, and GDP training uses STRICT observed publication vintages with target GDP excluded. This is PSEUDO_REAL_TIME_NOT_VINTAGE_VERIFIED; authentic predictor release restrictions cannot be verified from these inputs. No missing release date is invented. Revised-data and vintage uncertainty remains.

Each factor, its training standardization, missing-data PCA, AR(2), one-sided filter, hierarchical projection and GDP bridge is refitted inside each archived origin. No fit is shared across origins. Target-quarter data never train factor parameters. All transformations, minimum-history thresholds, penalties, weighting formula, quarterly covariate rules, GDP actuals and windows are unchanged. Family weights are recomputed by the original formula on the retained measurement set.

Both original F5 sign anchors are excluded. Retained broad money M2 fixes the revised F5 positive orientation in full and core fits. This changes the sign convention only; tests verify sign-invariant predictions and contributions. No indicator is added, replaced or moved. E3 remains the original two-stage hierarchical approximation, with F5 as reference block; E3 variable loadings here are first-stage measurement loadings.

Bias is **actual minus prediction**, consistent with the original Phase 7E convention. Negative bias means overprediction. R² is 1−SSE/SST, not squared correlation; out-of-sample R² uses matched AR1 and unchanged COMBO_50_50 benchmark errors. COMBO research scores use the archived comparable GDP actuals; they are distinct from frozen production first-release metrics.

## Factor membership

| factor | interpretation | original_count | revised_count | original_core_count | revised_core_count |
| --- | --- | --- | --- | --- | --- |
| F1 | Industrial activity | 29 | 28 | 3 | 3 |
| F2 | Services activity | 14 | 14 | 4 | 4 |
| F3 | Domestic demand | 5 | 5 | 3 | 3 |
| F4 | External conditions | 5 | 5 | 3 | 3 |
| F5 | Prices and monetary conditions | 38 | 36 | 4 | 2 |

Deliberate exclusions retained in the inventory:

- F1: Industrial production — Industrial production (billion UZS) [M]. Aggregate overlaps industrial components; deliberately excluded.
- F5: CPI — Cumulative index (index, %) [M]. Headline overlaps retained CPI categories; deliberately excluded.
- F5: PPI — Composite index (index, %) [M]. Composite overlaps retained PPI categories; deliberately excluded.

E1 retains F1–F4 (52 monthly indicators); E2/E3 retain F1–F5 (88); E4 adds its unchanged five quarterly covariates. The original 17-variable economic core becomes **15 variables**: F1=3, F2=4, F3=3, F4=3, F5=2. Aggregate industry was already absent from the core.

## 2026Q3 research nowcasts

| model | original_prediction | revised_prediction | nowcast_change_pp |
| --- | --- | --- | --- |
| E1 | 8.860393 | 8.789903 | -0.070490 |
| E2 | 8.849506 | 8.783592 | -0.065914 |
| E3 | 8.656072 | 8.608215 | -0.047856 |
| E4 | 8.546187 | 8.483709 | -0.062478 |
| ECONOMIC_CORE | 8.913026 | 8.677255 | -0.235771 |

## Identical-origin evaluation

### MATCHED_ALL

| model | original_rmse | revised_rmse | revised_mae | revised_bias | revised_r2 | revised_r2_os_ar1 | revised_r2_os_combo_50_50 | revised_n_forecasts | revised_n_quarters | performance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E1 | 0.864003 | 0.874444 | 0.771885 | 0.771885 | -0.702380 | -0.430259 | -1.489034 | 18 | 6 | WORSENED |
| E2 | 0.948251 | 0.961531 | 0.874782 | 0.874782 | -1.058348 | -0.729327 | -2.009492 | 18 | 6 | WORSENED |
| E3 | 1.004778 | 1.004430 | 0.902663 | 0.902663 | -1.246115 | -0.887079 | -2.284024 | 18 | 6 | IMPROVED |
| E4 | 0.786225 | 0.794444 | 0.707541 | 0.707541 | -0.405138 | -0.180530 | -1.054439 | 18 | 6 | WORSENED |
| ECONOMIC_CORE | 0.910017 | 0.892853 | 0.796808 | 0.796808 | -0.774813 | -0.491114 | -1.594939 | 18 | 6 | IMPROVED |

### MATCHED_DEVELOPMENT

| model | original_rmse | revised_rmse | revised_mae | revised_bias | revised_r2 | revised_r2_os_ar1 | revised_r2_os_combo_50_50 | revised_n_forecasts | revised_n_quarters | performance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E1 | 0.446272 | 0.443344 | 0.418159 | 0.418159 | -3.913837 | 0.402667 | 0.190966 | 6 | 2 | IMPROVED |
| E2 | 0.570769 | 0.575209 | 0.561204 | 0.561204 | -7.271632 | -0.005512 | -0.361876 | 6 | 2 | WORSENED |
| E3 | 0.586639 | 0.586850 | 0.571760 | 0.571760 | -7.609827 | -0.046624 | -0.417558 | 6 | 2 | WORSENED |
| E4 | 0.465004 | 0.468926 | 0.450981 | 0.450981 | -4.497291 | 0.331741 | 0.094903 | 6 | 2 | WORSENED |
| ECONOMIC_CORE | 0.484942 | 0.457080 | 0.448999 | 0.448999 | -4.223053 | 0.365078 | 0.140055 | 6 | 2 | IMPROVED |

### MATCHED_HOLDOUT

| model | original_rmse | revised_rmse | revised_mae | revised_bias | revised_r2 | revised_r2_os_ar1 | revised_r2_os_combo_50_50 | revised_n_forecasts | revised_n_quarters | performance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E1 | 1.010035 | 1.024061 | 0.948749 | 0.948749 | -3.522702 | -0.645250 | -2.090429 | 12 | 4 | WORSENED |
| E2 | 1.088982 | 1.105160 | 1.031571 | 1.031571 | -4.267405 | -0.916155 | -2.599295 | 12 | 4 | WORSENED |
| E3 | 1.158575 | 1.158069 | 1.068115 | 1.068115 | -4.783820 | -1.104014 | -2.952169 | 12 | 4 | IMPROVED |
| E4 | 0.905048 | 0.914749 | 0.835821 | 0.835821 | -2.608693 | -0.312755 | -1.465873 | 12 | 4 | WORSENED |
| ECONOMIC_CORE | 1.060477 | 1.044662 | 0.970713 | 0.970713 | -3.706499 | -0.712111 | -2.216020 | 12 | 4 | IMPROVED |

All rows compare original and revised models on identical common successful origins and identical latest-revised GDP actuals. The primary holdout remains 2025Q3–2026Q2 (four target quarters, 12 forecasts). Improvement means lower matched RMSE; it is descriptive evidence on a small, previously examined holdout, not proof of forecast superiority.

## Forecast performance by horizon

| model | horizon | original_rmse | revised_rmse | original_mae | revised_mae | original_bias | revised_bias | original_r2 | revised_r2 | revised_n_forecasts | performance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E1 | H1 | 1.000014 | 0.998581 | 0.954207 | 0.955178 | 0.954207 | 0.955178 | -3.312785 | -3.300438 | 4 | IMPROVED |
| E2 | H1 | 1.068753 | 1.071260 | 1.021135 | 1.026485 | 1.021135 | 1.026485 | -3.926068 | -3.949206 | 4 | WORSENED |
| E3 | H1 | 1.107337 | 1.101192 | 1.049218 | 1.043931 | 1.049218 | 1.043931 | -4.288177 | -4.229644 | 4 | IMPROVED |
| E4 | H1 | 0.827144 | 0.826355 | 0.762111 | 0.764721 | 0.762111 | 0.764721 | -1.950589 | -1.944959 | 4 | IMPROVED |
| ECONOMIC_CORE | H1 | 1.095943 | 1.091449 | 1.039197 | 1.038637 | 1.039197 | 1.038637 | -4.179905 | -4.137510 | 4 | IMPROVED |
| E1 | H2 | 0.928055 | 0.938147 | 0.880772 | 0.894959 | 0.880772 | 0.894959 | -2.714439 | -2.795666 | 4 | WORSENED |
| E2 | H2 | 1.002243 | 1.014760 | 0.957136 | 0.974042 | 0.957136 | 0.974042 | -3.332034 | -3.440921 | 4 | WORSENED |
| E3 | H2 | 1.074345 | 1.070004 | 1.019106 | 1.017069 | 1.019106 | 1.017069 | -3.977757 | -3.937606 | 4 | IMPROVED |
| E4 | H2 | 0.869992 | 0.877743 | 0.816725 | 0.827274 | 0.816725 | 0.827274 | -2.264201 | -2.322621 | 4 | WORSENED |
| ECONOMIC_CORE | H2 | 1.011244 | 0.988498 | 0.945181 | 0.934007 | 0.945181 | 0.934007 | -3.410198 | -3.214028 | 4 | IMPROVED |
| E1 | H3 | 1.095080 | 1.126419 | 0.962382 | 0.996110 | 0.962382 | 0.996110 | -4.171757 | -4.472003 | 4 | WORSENED |
| E2 | H3 | 1.187822 | 1.219345 | 1.059070 | 1.094186 | 1.059070 | 1.094186 | -5.084836 | -5.412088 | 4 | WORSENED |
| E3 | H3 | 1.283150 | 1.290674 | 1.134189 | 1.143345 | 1.134189 | 1.143345 | -6.100699 | -6.184210 | 4 | WORSENED |
| E4 | H3 | 1.008107 | 1.028106 | 0.893748 | 0.915468 | 0.893748 | 0.915468 | -3.382878 | -3.558499 | 4 | WORSENED |
| ECONOMIC_CORE | H3 | 1.072442 | 1.051461 | 0.954196 | 0.939496 | 0.954196 | 0.939496 | -3.960139 | -3.767959 | 4 | IMPROVED |

## Economic interpretation

F1–F4 retain their original economic meaning; F1 now omits the redundant total while preserving all components. Full F5 retains detailed consumer and producer price indices, money and rates. Its interpretation remains price/monetary co-movement, with heterogeneous loadings rather than a causal inflation shock. The core F5 now contains only M2 and the lending rate, so it represents liquidity and financing conditions and has **no direct inflation measurement**. The original F5 number and broad economic label remain, with this narrower core meaning explicitly disclosed. Other caveats persist: nominal industrial/demand series, overlapping detailed components and short services history.

| model | factor | n_declared | n_estimable | anchor | mean_pairwise_correlation | positive_loading_share | effective_loading_count | observed_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E1 | F1 | 28 | 28 | Industrial production — Manufacturing industry (billion UZS) [M] | 0.128607 | 0.964286 | 15.174638 | 0.990385 |
| E1 | F2 | 14 | 14 | Rendered market services — Transport activities (% of previous year) [M] | 0.224888 | 0.857143 | 8.710570 | 1.000000 |
| E1 | F3 | 5 | 5 | Retail trade volume (million UZS) [M] | 0.051140 | 0.600000 | 3.053025 | 0.809091 |
| E1 | F4 | 5 | 5 | Export volume (million USD) [M] | 0.159403 | 0.800000 | 2.566176 | 0.842697 |
| E2 | F1 | 28 | 28 | Industrial production — Manufacturing industry (billion UZS) [M] | 0.128607 | 0.964286 | 15.174638 | 0.990385 |
| E2 | F2 | 14 | 14 | Rendered market services — Transport activities (% of previous year) [M] | 0.224888 | 0.857143 | 8.710570 | 1.000000 |
| E2 | F3 | 5 | 5 | Retail trade volume (million UZS) [M] | 0.051140 | 0.600000 | 3.053025 | 0.809091 |
| E2 | F4 | 5 | 5 | Export volume (million USD) [M] | 0.159403 | 0.800000 | 2.566176 | 0.842697 |
| E2 | F5 | 36 | 36 | M2 — Broad money liabilities (billion UZS) [M] | 0.056151 | 0.361111 | 3.145552 | 0.874074 |
| E3 | F1 | 28 | 28 | Industrial production — Manufacturing industry (billion UZS) [M] | 0.128607 | 0.964286 | 15.174638 | 0.990385 |
| E3 | F2 | 14 | 14 | Rendered market services — Transport activities (% of previous year) [M] | 0.224888 | 0.857143 | 8.710570 | 1.000000 |
| E3 | F3 | 5 | 5 | Retail trade volume (million UZS) [M] | 0.051140 | 0.600000 | 3.053025 | 0.809091 |
| E3 | F4 | 5 | 5 | Export volume (million USD) [M] | 0.159403 | 0.800000 | 2.566176 | 0.842697 |
| E3 | F5 | 36 | 36 | M2 — Broad money liabilities (billion UZS) [M] | 0.056151 | 0.361111 | 3.145552 | 0.874074 |
| E4 | F1 | 28 | 28 | Industrial production — Manufacturing industry (billion UZS) [M] | 0.128607 | 0.964286 | 15.174638 | 0.990385 |
| E4 | F2 | 14 | 14 | Rendered market services — Transport activities (% of previous year) [M] | 0.224888 | 0.857143 | 8.710570 | 1.000000 |
| E4 | F3 | 5 | 5 | Retail trade volume (million UZS) [M] | 0.051140 | 0.600000 | 3.053025 | 0.809091 |
| E4 | F4 | 5 | 5 | Export volume (million USD) [M] | 0.159403 | 0.800000 | 2.566176 | 0.842697 |
| E4 | F5 | 36 | 36 | M2 — Broad money liabilities (billion UZS) [M] | 0.056151 | 0.361111 | 3.145552 | 0.874074 |
| ECONOMIC_CORE | F1 | 3 | 3 | Industrial production — Manufacturing industry (billion UZS) [M] | 0.138807 | 1.000000 | 2.375630 | 1.000000 |
| ECONOMIC_CORE | F2 | 4 | 4 | Rendered market services — Transport activities (% of previous year) [M] | -0.031142 | 0.750000 | 1.504597 | 1.000000 |
| ECONOMIC_CORE | F3 | 3 | 3 | Retail trade volume (million UZS) [M] | 0.113654 | 1.000000 | 1.938538 | 0.924242 |
| ECONOMIC_CORE | F4 | 3 | 3 | Export volume (million USD) [M] | 0.123840 | 1.000000 | 1.101229 | 1.000000 |
| ECONOMIC_CORE | F5 | 2 | 2 | M2 — Broad money liabilities (billion UZS) [M] | 0.259442 | 1.000000 | 1.977860 | 1.000000 |

## Current GDP attribution

Contributions are standardized bridge coefficient × signal, in GDP percentage points. Include intercept, available GDP lag and E4 covariates to reconcile totals. They are statistical attribution, not causal sector GDP contributions.

| model | component | value |
| --- | --- | --- |
| E1 | Intercept | 6.642248 |
| E1 | F1 | 0.727095 |
| E1 | F2 | 0.611175 |
| E1 | F3 | 0.002676 |
| E1 | F4 | -0.019141 |
| E1 | AVAILABLE_GDP_LAG | 0.825850 |
| E2 | Intercept | 6.646585 |
| E2 | F1 | 0.729611 |
| E2 | F2 | 0.654016 |
| E2 | F3 | 0.002498 |
| E2 | F4 | -0.019252 |
| E2 | F5 | -0.100913 |
| E2 | AVAILABLE_GDP_LAG | 0.871047 |
| E3 | Intercept | 6.646552 |
| E3 | GLOBAL | 0.087382 |
| E3 | F1_RESIDUAL | 0.350255 |
| E3 | F2_RESIDUAL | 0.541842 |
| E3 | F3_RESIDUAL | 0.115286 |
| E3 | F4_RESIDUAL | -0.029112 |
| E3 | AVAILABLE_GDP_LAG | 0.896010 |
| E4 | Intercept | 6.652584 |
| E4 | F1 | 0.443044 |
| E4 | F2 | 0.378856 |
| E4 | F3 | 0.003370 |
| E4 | F4 | -0.017174 |
| E4 | F5 | -0.144698 |
| E4 | AVAILABLE_GDP_LAG | 0.941408 |
| E4 | Remittance — Secondary income, credits (million USD)  | 0.049153 |
| E4 | Average Nominal Wages (UZS)  | -0.021578 |
| E4 | Investments in fixed assets (%)  | 0.021071 |
| E4 | Investment financed through FDI (million UZS) | 0.095732 |
| E4 | Total income of the population (billion UZS) | 0.081941 |
| ECONOMIC_CORE | Intercept | 6.600069 |
| ECONOMIC_CORE | F1 | 0.909301 |
| ECONOMIC_CORE | F2 | 0.464539 |
| ECONOMIC_CORE | F3 | 0.004460 |
| ECONOMIC_CORE | F4 | -0.057731 |
| ECONOMIC_CORE | F5 | 0.119539 |
| ECONOMIC_CORE | AVAILABLE_GDP_LAG | 0.637079 |

## Failures and validation

345 revised forecast attempts failed visibly, predominantly early origins without enough services history. All 95 successful original model/origin fits were recomputed; max archive discrepancy 0 pp. Contribution reconciliation error: 2.66e-15 pp. Failed forecasts are excluded symmetrically by origin matching, never filled. See revised_phase7e_failures.csv and validation.json for executed tests, browser checks and protection hashes.

## Reproduction

```powershell
.venv/Scripts/python.exe -B -m scripts.phase7e.revised_factors.run
.venv/Scripts/python.exe -B -m scripts.phase7e.revised_factors.validate
```

## Exact retained variables (full blocks and core)

### F1 — Industrial activity

- Industrial production — Mining and quarrying (billion UZS) [M] **[core]**
- Industrial production — Manufacturing industry (billion UZS) [M] **[core]**
- Industrial production — Electricity, gas, steam and air conditioning (billion UZS) [M] **[core]**
- Industrial production — Water supply; sewerage, waste collection and disposal (billion UZS) [M]
- Industrial production — Manufacturing of food products (billion UZS) [M]
- Industrial production — Manufacture of beverages (billion UZS) [M]
- Industrial production — Manufacture of tobacco products (billion UZS) [M]
- Industrial production — Manufacture of textiles (billion UZS) [M]
- Industrial production — Manufacture of wearing apparel (billion UZS) [M]
- Industrial production — Manufacture of leather and related products (billion UZS) [M]
- Industrial production — Manufacture of wooden and cork products, (except furniture), products made of straw and plaiting materials (billion UZS) [M]
- Industrial production — Manufacture of paper and paper products (billion UZS) [M]
- Industrial production — Printing and Playback of Recorded Materials (billion UZS) [M]
- Industrial production — Manufacture of chemical products (billion UZS) [M]
- Industrial production — Manufacture of coke and refined petroleum products (billion UZS) [M]
- Industrial production — Manufacture of basic pharmaceutical products and preparations (billion UZS) [M]
- Industrial production — Manufacture of rubber and plastic products (billion UZS) [M]
- Industrial production — Manufacture of other non-metallic mineral products (billion UZS) [M]
- Industrial production — Metallurgical industry (billion UZS) [M]
- Industrial production — Manufacture of fabricated metal products, except machinery and equipment (billion UZS) [M]
- Industrial production — Manufacture of computers, electronic and optical products (billion UZS) [M]
- Industrial production — Manufacture of electrical equipment (billion UZS) [M]
- Industrial production — Manafacture of machinery and equipment,not elsewhere classified (billion UZS) [M]
- Industrial production — Manufacture of motor vehicles, trailers and semi-trailers (billion UZS) [M]
- Industrial production — Manufacture of other transport equipment (billion UZS) [M]
- Industrial production — Furniture manufacture (billion UZS) [M]
- Industrial production — Manufacture of other finished products (billion UZS) [M]
- Industrial production — Repair and installation of machinery and equipment (billion UZS) [M]

### F2 — Services activity

- Rendered market services — Trade (% of previous year) [M]
- Rendered market services — Information and communication (% of previous year) [M] **[core]**
- Rendered market services — Transport activities (% of previous year) [M] **[core]**
- Rendered market services — of which: motor transport (% of previous year) [M]
- Rendered market services — Accommodation and food service activities (% of previous year) [M] **[core]**
- Rendered market services — Financial activities (% of previous year) [M] **[core]**
- Rendered market services — Real estate activities (% of previous year) [M]
- Rendered market services — Architectural and engineering activities, technical testing and analysis (% of previous year) [M]
- Rendered market services — Renting and leasing (% of previous year) [M]
- Rendered market services — Education (% of previous year) [M]
- Rendered market services — Human health activities (% of previous year) [M]
- Rendered market services — Repair of computers and household goods (% of previous year) [M]
- Rendered market services — Personal (% of previous year) [M]
- Rendered market services — Other services (% of previous year) [M]

### F3 — Domestic demand

- Construction works (billion UZS) [M] **[core]**
- Retail trade volume (million UZS) [M] **[core]**
- Wholesale trade volume (million UZS) [M] **[core]**
- Small business entities (units) [M]
- Operating enterprises (units) [M]

### F4 — External conditions

- Export volume (million USD) [M] **[core]**
- Import volume (million USD) [M] **[core]**
- Gold (USD/troy oz) [M] **[core]**
- International reserves — Foreign currency reserves (in convertible foreign currencies) (million USD) [M]
- International reserves — Gold (million USD) [M]

### F5 — Prices and monetary conditions

- CPI — Food products (index, %) [M]
- CPI — Non-food products (index, %) [M]
- CPI — Services (index, %) [M]
- CPI — Food and non-alcoholic drinks (index, %) [M]
- CPI — Alcoholic drinks, tobacco products (index, %) [M]
- CPI — Clothes and footwear (index, %) [M]
- CPI — Housing services, water, electricity, gas and other fuels (index, %) [M]
- CPI — Household items, appliances and routine home maintenance (index, %) [M]
- CPI — Health care (index, %) [M]
- CPI — Transport (index, %) [M]
- CPI — Information and communication (index, %) [M]
- CPI — Recreation, sports and culture (index, %) [M]
- CPI — Services in the field of education (index, %) [M]
- CPI — Restaurants and hotel services (index, %) [M]
- CPI — Insurance and financial services (index, %) [M]
- CPI — Household goods and services, social protection and miscellaneous goods and services (index, %) [M]
- PPI — Mining and quarrying (index, %) [M]
- PPI — Manufacturing industry (index, %) [M]
- PPI — Electricity, gas, steam and air conditioning (index, %) [M]
- PPI — Water supply; sewerage, waste collection and disposal (index, %) [M]
- PPI — Manufacturing of food products (index, %) [M]
- PPI — Manufacture of beverages (index, %) [M]
- PPI — Manufacture of textiles (index, %) [M]
- PPI — Manufacture of chemical products (index, %) [M]
- PPI — Manufacture of coke and refined petroleum products (index, %) [M]
- PPI — Manufacture of other non-metallic mineral products (index, %) [M]
- PPI — Metallurgical industry (index, %) [M]
- PPI — Manufacture of fabricated metal products, except machinery and equipment (index, %) [M]
- PPI — Manufacture of electrical equipment (index, %) [M]
- PPI — Manufacture of motor vehicles, trailers and semi-trailers (index, %) [M]
- PPI — Mining of metal ores (index, %) [M]
- M2 — Broad money liabilities (billion UZS) [M] **[core]**
- Interest rates — Time deposits of individuals (annual %) [M]
- Interest rates — Time deposits of legal entities (annual %) [M]
- Interest rates — Loans extended to individuals (annual %) [M]
- Interest rates — Loans extended to legal entities (annual %) [M] **[core]**


## Executed validation

Full suite: 351 tests; initially 349 passed and 2 failed. The two pre-existing staged operations tests exceeded legacy Windows path lengths in the experiment’s deeper temporary directory. Targeted rerun with shorter fixture paths: 2 checks, 0 failures and 0 errors. Final status: 351 passed, 0 failures, 0 errors, 0 skips. All 22 new scientific checks passed in the initial full suite. Complete numerical replay: passed; all CSVs and initial dashboard HTML byte-identical. Browser validation found and corrected case-sensitive indicator search. After this UI-only fix, dashboard reporting replay is byte-identical and every numerical CSV hash is unchanged. Offline Edge controls: passed; Edge requires an unrestricted launch because restricted Windows IPC prevented startup. All 334 protected prior files verified unchanged after tests and browser validation. Predictor historical vintages remain unverified.
