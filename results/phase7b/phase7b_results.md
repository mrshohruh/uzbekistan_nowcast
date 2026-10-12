# Phase 7B satellite research

**PHASE7B_SATELLITE_INCONCLUSIVE**

RESEARCH ONLY · SOURCE_METADATA_UNVERIFIED · VINTAGE UNVERIFIED. Production remains exactly 8.180901340616275%.

Input has 152 months (2014-01–2026-08), 152 radiance/NDVI/EVI observations and 99 NO2 observations beginning 2018-06. Units, products, geographic weighting, processing, sensor changes and historical publication vintages remain unverified. See satellite_data_audit.md and quality flags. Raw CSV archived by SHA256 84da96be4f18c2a2654b9d082b869b84e7c9917bcb1b67a8589a923d76e24aa8. No September 2026 observations or 2026Q3 GDP outcome were used.

Transformations: positive-pair 100 log YoY for radiance/NO2; calendar-aligned year-ago differences for NDVI/EVI. R1 uses seasonally differenced radiance levels, R2 strictly backward expanding NDVI seasonal anomalies (three prior same-month observations), R3 training-only 1/99% radiance-growth winsorization. Training-only standardization in unchanged DFM kernel. No missing measurement becomes zero.

Estimation uses production DynamicFactorMQ EM MLE, one factor, AR(2), filtered states, balanced starting history, and unchanged lagged-GDP mean-factor bridge. No architecture or combination-weight changes. S4/S5 require independently estimable components at the same origin. Failures are explicit in phase7b_failures.csv; no failed model is assigned a chart value. NO2 transforms begin June 2019 and can shorten the balanced training history. Other satellite history predates the production panel but the production start remains January 2019. Phase 6G extended origins were investigated through the current consolidated strict historical forecast artifact; 45 frozen U0 origins are reused, and M0/U0 independently reproduced. No new earlier origins are invented beyond the approved frozen archive. All three 2022Q4 origins are excluded because frozen M0 fails its unchanged factor-transition stability check; phase7b_origin_exclusions.csv preserves the reasons. The U0 archive has 48 origins, but only 45 can be compared with M0/C0.

GDP controls remain STRICT and assert publication before the origin and target exclusion using existing gdp_vintages.csv. Economic predictors retain repository release-lag assumptions. Satellite evaluation is REVISED_DATA_EXPLORATORY at zero-month delay; sensitivities assume availability at reference-month end plus one/two/three calendar months. These are hypothetical schedules, not historical releases. Even delayed evaluations use revised satellite values and are not verified real-time accuracy estimates.

Common samples are intersections on origin, quarter, horizon and scenario, with identical actuals; phase7b_strict_common_metrics.csv additionally places M0/U0/C0, S1/S2/S3 and C1/C2/C3 on a single identical cohort in each delay scenario; each model is refit at each origin. Full-available scores are separately reported and cannot be compared directly with restricted challenger scores. phase7b_full_history_baseline.csv additionally reports the full frozen M0/U0 archives and their combination intersection, including separate holdout/development scores; these archived-history metrics can cover different origin sets. Differences in balanced histories are evaluated with the supplementary M0_NO2_HISTORY_CONTROL beginning June 2019, using identical production functions; phase7b_sample_length_metrics.csv contrasts S3/S5 on the same origins and shortened history. Bias is actual minus prediction; R² is 1-SSE/SST; OOS R² compares same-origin errors against archived AR(1). GDP remains cumulative YTD real YoY percent and quarterly.

Best exploratory DFM by matched RMSE change: {'scenario': 'REVISED_DATA_EXPLORATORY', 'model': 'S6', 'delta_rmse': -0.009268060729583028, 'n_quarters': 15, 'n_origins': 45}. Best exploratory 50/50 combination by matched RMSE change: {'scenario': 'REVISED_DATA_EXPLORATORY', 'model': 'C6', 'delta_rmse': -0.004847149656996563, 'n_quarters': 15, 'n_origins': 45}. These are descriptive selections among multiple tests, not confirmatory evidence.

Vegetation measures show small exploratory gains, whereas nighttime-lights and NO2 log growth do not improve their matched pooled baselines. The best combination C6 reduces RMSE by 0.004847 pp (45 matched origins, 15 quarters). This is a descriptive selection across multiple specifications. Temporal robustness for the selected combination: model                                  C0        C6
scenario                 subset                    
ASSUMED_LAG_1M           EARLY   0.315348  0.292594
                         RECENT  0.486668  0.490904
ASSUMED_LAG_2M           EARLY   0.315348  0.292627
                         RECENT  0.486668  0.490770
ASSUMED_LAG_3M           EARLY   0.315348  0.341613
                         RECENT  0.486668  0.490674
REVISED_DATA_EXPLORATORY EARLY   0.315348  0.292754
                         RECENT  0.486668  0.491282. A pooled gain that reverses in recent history does not establish robust incremental information. The selected EVI combination also reverses its pooled gain under the three-month assumed delay; one/two-month gains are small.

Development/holdout scores are separately preserved in phase7b_evaluation_group_metrics.csv; four holdout quarters alone cannot establish robust model superiority.

Matched accuracy:

```text
                scenario comparison  sample model  n_origins  n_quarters     rmse      mae     bias  r_squared  oos_r_squared_ar1 first_quarter last_quarter
          ASSUMED_LAG_1M         S1 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
          ASSUMED_LAG_1M         S1 MATCHED    S1         45          15 0.506132 0.424181 0.335119   0.734068           0.094638        2022Q3       2026Q2
          ASSUMED_LAG_1M         S2 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
          ASSUMED_LAG_1M         S2 MATCHED    S2         45          15 0.476175 0.399355 0.366685   0.764616           0.198639        2022Q3       2026Q2
          ASSUMED_LAG_1M         S3 MATCHED    M0         36          12 0.519197 0.441001 0.438886   0.673913           0.213956        2022Q3       2026Q2
          ASSUMED_LAG_1M         S3 MATCHED    S3         36          12 0.542931 0.459825 0.451979   0.643418           0.140448        2022Q3       2026Q2
          ASSUMED_LAG_1M         S4 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
          ASSUMED_LAG_1M         S4 MATCHED    S4         45          15 0.476534 0.401568 0.362017   0.764261           0.197430        2022Q3       2026Q2
          ASSUMED_LAG_1M         S5 MATCHED    M0         36          12 0.519197 0.441001 0.438886   0.673913           0.213956        2022Q3       2026Q2
          ASSUMED_LAG_1M         S5 MATCHED    S5         36          12 0.607024 0.488288 0.472078   0.554260          -0.074469        2022Q3       2026Q2
          ASSUMED_LAG_1M         S6 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
          ASSUMED_LAG_1M         S6 MATCHED    S6         45          15 0.474297 0.397635 0.364551   0.766469           0.204949        2022Q3       2026Q2
          ASSUMED_LAG_1M         C1 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
          ASSUMED_LAG_1M         C1 MATCHED    C1         45          15 0.430568 0.341575 0.215226   0.807546           0.344794        2022Q3       2026Q2
          ASSUMED_LAG_1M         C2 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
          ASSUMED_LAG_1M         C2 MATCHED    C2         45          15 0.410952 0.321060 0.231009   0.824682           0.403133        2022Q3       2026Q2
          ASSUMED_LAG_1M         C3 MATCHED    C0         36          12 0.440612 0.348153 0.280692   0.765154           0.433896        2022Q3       2026Q2
          ASSUMED_LAG_1M         C3 MATCHED    C3         36          12 0.453190 0.364298 0.287238   0.751555           0.401116        2022Q3       2026Q2
          ASSUMED_LAG_1M         C4 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
          ASSUMED_LAG_1M         C4 MATCHED    C4         45          15 0.411854 0.321490 0.228676   0.823912           0.400510        2022Q3       2026Q2
          ASSUMED_LAG_1M         C5 MATCHED    C0         36          12 0.440612 0.348153 0.280692   0.765154           0.433896        2022Q3       2026Q2
          ASSUMED_LAG_1M         C5 MATCHED    C5         36          12 0.487600 0.379840 0.297287   0.712394           0.306717        2022Q3       2026Q2
          ASSUMED_LAG_1M         C6 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
          ASSUMED_LAG_1M         C6 MATCHED    C6         45          15 0.410461 0.320990 0.229942   0.825101           0.404558        2022Q3       2026Q2
          ASSUMED_LAG_2M         S1 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
          ASSUMED_LAG_2M         S1 MATCHED    S1         45          15 0.505844 0.423357 0.338995   0.734370           0.095667        2022Q3       2026Q2
          ASSUMED_LAG_2M         S2 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
          ASSUMED_LAG_2M         S2 MATCHED    S2         45          15 0.476215 0.399617 0.367383   0.764576           0.198504        2022Q3       2026Q2
          ASSUMED_LAG_2M         S3 MATCHED    M0         36          12 0.519197 0.441001 0.438886   0.673913           0.213956        2022Q3       2026Q2
          ASSUMED_LAG_2M         S3 MATCHED    S3         36          12 0.542909 0.458861 0.450210   0.643447           0.140518        2022Q3       2026Q2
          ASSUMED_LAG_2M         S4 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
          ASSUMED_LAG_2M         S4 MATCHED    S4         45          15 0.477128 0.401683 0.367346   0.763673           0.195427        2022Q3       2026Q2
          ASSUMED_LAG_2M         S5 MATCHED    M0         36          12 0.519197 0.441001 0.438886   0.673913           0.213956        2022Q3       2026Q2
          ASSUMED_LAG_2M         S5 MATCHED    S5         36          12 0.600741 0.484828 0.473564   0.563439          -0.052343        2022Q3       2026Q2
          ASSUMED_LAG_2M         S6 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
          ASSUMED_LAG_2M         S6 MATCHED    S6         45          15 0.474120 0.397591 0.364762   0.766643           0.205541        2022Q3       2026Q2
          ASSUMED_LAG_2M         C1 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
          ASSUMED_LAG_2M         C1 MATCHED    C1         45          15 0.429746 0.341214 0.217164   0.808280           0.347292        2022Q3       2026Q2
          ASSUMED_LAG_2M         C2 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
          ASSUMED_LAG_2M         C2 MATCHED    C2         45          15 0.410820 0.320885 0.231359   0.824795           0.403516        2022Q3       2026Q2
          ASSUMED_LAG_2M         C3 MATCHED    C0         36          12 0.440612 0.348153 0.280692   0.765154           0.433896        2022Q3       2026Q2
          ASSUMED_LAG_2M         C3 MATCHED    C3         36          12 0.453696 0.365329 0.286354   0.751000           0.399777        2022Q3       2026Q2
          ASSUMED_LAG_2M         C4 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
          ASSUMED_LAG_2M         C4 MATCHED    C4         45          15 0.410932 0.320650 0.231340   0.824700           0.403193        2022Q3       2026Q2
          ASSUMED_LAG_2M         C5 MATCHED    C0         36          12 0.440612 0.348153 0.280692   0.765154           0.433896        2022Q3       2026Q2
          ASSUMED_LAG_2M         C5 MATCHED    C5         36          12 0.483964 0.377075 0.298031   0.716668           0.317019        2022Q3       2026Q2
          ASSUMED_LAG_2M         C6 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
          ASSUMED_LAG_2M         C6 MATCHED    C6         45          15 0.410387 0.320982 0.230048   0.825164           0.404775        2022Q3       2026Q2
          ASSUMED_LAG_3M         S1 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
          ASSUMED_LAG_3M         S1 MATCHED    S1         45          15 0.478602 0.403219 0.370280   0.762210           0.190449        2022Q3       2026Q2
          ASSUMED_LAG_3M         S2 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
          ASSUMED_LAG_3M         S2 MATCHED    S2         45          15 0.478904 0.402612 0.370803   0.761911           0.189429        2022Q3       2026Q2
          ASSUMED_LAG_3M         S3 MATCHED    M0         36          12 0.519197 0.441001 0.438886   0.673913           0.213956        2022Q3       2026Q2
          ASSUMED_LAG_3M         S3 MATCHED    S3         36          12 0.543061 0.456685 0.448383   0.643247           0.140037        2022Q3       2026Q2
          ASSUMED_LAG_3M         S4 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
          ASSUMED_LAG_3M         S4 MATCHED    S4         45          15 0.479284 0.403154 0.371432   0.761533           0.188141        2022Q3       2026Q2
          ASSUMED_LAG_3M         S5 MATCHED    M0         34          12 0.454138 0.398706 0.396468   0.703376           0.198956        2022Q3       2026Q2
          ASSUMED_LAG_3M         S5 MATCHED    S5         34          12 0.505069 0.423353 0.414394   0.633112           0.009206        2022Q3       2026Q2
          ASSUMED_LAG_3M         S6 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
          ASSUMED_LAG_3M         S6 MATCHED    S6         45          15 0.502299 0.417504 0.335094   0.738080           0.108298        2022Q3       2026Q2
          ASSUMED_LAG_3M         C1 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
          ASSUMED_LAG_3M         C1 MATCHED    C1         45          15 0.412682 0.323867 0.232807   0.823203           0.398096        2022Q3       2026Q2
          ASSUMED_LAG_3M         C2 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
          ASSUMED_LAG_3M         C2 MATCHED    C2         45          15 0.412171 0.321642 0.233069   0.823640           0.399586        2022Q3       2026Q2
          ASSUMED_LAG_3M         C3 MATCHED    C0         36          12 0.440612 0.348153 0.280692   0.765154           0.433896        2022Q3       2026Q2
          ASSUMED_LAG_3M         C3 MATCHED    C3         36          12 0.454302 0.366645 0.285440   0.750334           0.398173        2022Q3       2026Q2
          ASSUMED_LAG_3M         C4 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
          ASSUMED_LAG_3M         C4 MATCHED    C4         45          15 0.411869 0.321121 0.233383   0.823899           0.400466        2022Q3       2026Q2
          ASSUMED_LAG_3M         C5 MATCHED    C0         34          12 0.346075 0.297623 0.226194   0.827745           0.534819        2022Q3       2026Q2
          ASSUMED_LAG_3M         C5 MATCHED    C5         34          12 0.372947 0.320210 0.235157   0.799956           0.459774        2022Q3       2026Q2
          ASSUMED_LAG_3M         C6 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
          ASSUMED_LAG_3M         C6 MATCHED    C6         45          15 0.427628 0.338239 0.215214   0.810165           0.353710        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S1 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S1 MATCHED    S1         45          15 0.518763 0.425969 0.326779   0.720629           0.048884        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S2 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S2 MATCHED    S2         45          15 0.477047 0.399694 0.366697   0.763753           0.195701        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S3 MATCHED    M0         36          12 0.519197 0.441001 0.438886   0.673913           0.213956        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S3 MATCHED    S3         36          12 0.542715 0.459451 0.452454   0.643702           0.141133        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S4 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S4 MATCHED    S4         45          15 0.475254 0.394502 0.355701   0.765526           0.201736        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S5 MATCHED    M0         36          12 0.519197 0.441001 0.438886   0.673913           0.213956        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S5 MATCHED    S5         36          12 0.605879 0.485253 0.463874   0.555940          -0.070420        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S6 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S6 MATCHED    S6         45          15 0.475015 0.398065 0.364625   0.765761           0.202538        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R1 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R1 MATCHED    R1         45          15 0.477621 0.398665 0.361466   0.763184           0.193764        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R2 MATCHED    M0         42          14 0.497267 0.423139 0.390112   0.744123           0.109517        2023Q1       2026Q2
REVISED_DATA_EXPLORATORY         R2 MATCHED    R2         42          14 0.514663 0.438133 0.403576   0.725906           0.046121        2023Q1       2026Q2
REVISED_DATA_EXPLORATORY         R3 MATCHED    M0         45          15 0.484283 0.408579 0.376063   0.756532           0.171116        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R3 MATCHED    R3         45          15 0.518785 0.425945 0.328782   0.720605           0.048805        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C1 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C1 MATCHED    C1         45          15 0.436004 0.345895 0.211057   0.802656           0.328144        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C2 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C2 MATCHED    C2         45          15 0.411301 0.321072 0.231015   0.824385           0.402120        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C3 MATCHED    C0         36          12 0.440612 0.348153 0.280692   0.765154           0.433896        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C3 MATCHED    C3         36          12 0.452945 0.363896 0.287475   0.751823           0.401762        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C4 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C4 MATCHED    C4         45          15 0.412838 0.324187 0.225518   0.823069           0.397642        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C5 MATCHED    C0         36          12 0.440612 0.348153 0.280692   0.765154           0.433896        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C5 MATCHED    C5         36          12 0.488029 0.383442 0.293186   0.711889           0.305499        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C6 MATCHED    C0         45          15 0.415602 0.327206 0.235699   0.820692           0.389549        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C6 MATCHED    C6         45          15 0.410755 0.321058 0.229979   0.824850           0.403705        2022Q3       2026Q2
```

Horizon metrics:

```text
                scenario comparison model horizon  n_origins  n_quarters     rmse      mae     bias  r_squared  oos_r_squared_ar1 first_quarter last_quarter
REVISED_DATA_EXPLORATORY         S1    M0      H1         15          15 0.494240 0.415904 0.391361   0.746418           0.136682        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S1    M0      H2         15          15 0.482322 0.413124 0.379993   0.758500           0.177816        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S1    M0      H3         15          15 0.476113 0.396710 0.356835   0.764678           0.198849        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S1    S1      H1         15          15 0.595973 0.479811 0.276874   0.631280          -0.255302        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S1    S1      H2         15          15 0.474535 0.393463 0.358750   0.766235           0.204149        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S1    S1      H3         15          15 0.476423 0.404631 0.344714   0.764371           0.197804        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S2    M0      H1         15          15 0.494240 0.415904 0.391361   0.746418           0.136682        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S2    M0      H2         15          15 0.482322 0.413124 0.379993   0.758500           0.177816        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S2    M0      H3         15          15 0.476113 0.396710 0.356835   0.764678           0.198849        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S2    S2      H1         15          15 0.484657 0.403956 0.378282   0.756156           0.169837        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S2    S2      H2         15          15 0.475140 0.404554 0.371002   0.765639           0.202120        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S2    S2      H3         15          15 0.471245 0.390571 0.350805   0.769465           0.215146        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S3    M0      H1         12          12 0.529735 0.453852 0.453852   0.660542           0.181725        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S3    M0      H2         12          12 0.517018 0.445537 0.445537   0.676644           0.220540        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S3    M0      H3         12          12 0.510657 0.423614 0.417271   0.684552           0.239603        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S3    S3      H1         12          12 0.555033 0.467671 0.467671   0.627345           0.101704        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S3    S3      H2         12          12 0.538112 0.459006 0.459006   0.649720           0.155639        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S3    S3      H3         12          12 0.534782 0.451677 0.430684   0.654042           0.166057        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S4    M0      H1         15          15 0.494240 0.415904 0.391361   0.746418           0.136682        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S4    M0      H2         15          15 0.482322 0.413124 0.379993   0.758500           0.177816        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S4    M0      H3         15          15 0.476113 0.396710 0.356835   0.764678           0.198849        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S4    S4      H1         15          15 0.481641 0.395892 0.371088   0.759181           0.180135        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S4    S4      H2         15          15 0.470544 0.387894 0.354517   0.770151           0.217481        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S4    S4      H3         15          15 0.473508 0.399719 0.341499   0.767246           0.207592        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S5    M0      H1         12          12 0.529735 0.453852 0.453852   0.660542           0.181725        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S5    M0      H2         12          12 0.517018 0.445537 0.445537   0.676644           0.220540        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S5    M0      H3         12          12 0.510657 0.423614 0.417271   0.684552           0.239603        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S5    S5      H1         12          12 0.610569 0.482527 0.478754   0.549039          -0.087055        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S5    S5      H2         12          12 0.612021 0.486237 0.469280   0.546892          -0.092232        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S5    S5      H3         12          12 0.594898 0.486994 0.443588   0.571890          -0.031971        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S6    M0      H1         15          15 0.494240 0.415904 0.391361   0.746418           0.136682        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S6    M0      H2         15          15 0.482322 0.413124 0.379993   0.758500           0.177816        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S6    M0      H3         15          15 0.476113 0.396710 0.356835   0.764678           0.198849        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S6    S6      H1         15          15 0.482046 0.401661 0.375867   0.758776           0.178756        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S6    S6      H2         15          15 0.473208 0.402669 0.368964   0.767540           0.208593        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S6    S6      H3         15          15 0.469706 0.389864 0.349044   0.770969           0.220266        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R1    M0      H1         15          15 0.494240 0.415904 0.391361   0.746418           0.136682        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R1    M0      H2         15          15 0.482322 0.413124 0.379993   0.758500           0.177816        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R1    M0      H3         15          15 0.476113 0.396710 0.356835   0.764678           0.198849        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R1    R1      H1         15          15 0.482590 0.399370 0.376413   0.758232           0.176903        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R1    R1      H2         15          15 0.474499 0.393764 0.361383   0.766270           0.204271        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R1    R1      H3         15          15 0.475735 0.402860 0.346600   0.765051           0.200119        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R2    M0      H1         14          14 0.504859 0.423510 0.397213   0.736250           0.082118        2023Q1       2026Q2
REVISED_DATA_EXPLORATORY         R2    M0      H2         14          14 0.494134 0.423579 0.388082   0.747336           0.120700        2023Q1       2026Q2
REVISED_DATA_EXPLORATORY         R2    M0      H3         14          14 0.492718 0.422328 0.385042   0.748782           0.125732        2023Q1       2026Q2
REVISED_DATA_EXPLORATORY         R2    R2      H1         14          14 0.533819 0.452104 0.424489   0.705123          -0.026207        2023Q1       2026Q2
REVISED_DATA_EXPLORATORY         R2    R2      H2         14          14 0.507546 0.433807 0.396786   0.733435           0.072322        2023Q1       2026Q2
REVISED_DATA_EXPLORATORY         R2    R2      H3         14          14 0.502065 0.428488 0.389454   0.739160           0.092247        2023Q1       2026Q2
REVISED_DATA_EXPLORATORY         R3    M0      H1         15          15 0.494240 0.415904 0.391361   0.746418           0.136682        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R3    M0      H2         15          15 0.482322 0.413124 0.379993   0.758500           0.177816        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R3    M0      H3         15          15 0.476113 0.396710 0.356835   0.764678           0.198849        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R3    R3      H1         15          15 0.596944 0.480230 0.276171   0.630078          -0.259394        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R3    R3      H2         15          15 0.474572 0.395830 0.363039   0.766198           0.204025        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         R3    R3      H3         15          15 0.475240 0.401776 0.347136   0.765540           0.201784        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C1    C0      H1         15          15 0.465939 0.377163 0.292258   0.774627           0.232721        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C1    C0      H2         15          15 0.460713 0.352299 0.290871   0.779654           0.249836        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C1    C0      H3         15          15 0.298027 0.252157 0.123966   0.907795           0.686089        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C1    C1      H1         15          15 0.517462 0.429063 0.235014   0.722029           0.053650        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C1    C1      H2         15          15 0.460345 0.352727 0.280250   0.780007           0.251036        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C1    C1      H3         15          15 0.301023 0.255894 0.117906   0.905932           0.679746        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C2    C0      H1         15          15 0.465939 0.377163 0.292258   0.774627           0.232721        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C2    C0      H2         15          15 0.460713 0.352299 0.290871   0.779654           0.249836        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C2    C0      H3         15          15 0.298027 0.252157 0.123966   0.907795           0.686089        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C2    C2      H1         15          15 0.459097 0.368154 0.285718   0.781197           0.255089        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C2    C2      H2         15          15 0.458307 0.347085 0.286376   0.781950           0.257652        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C2    C2      H3         15          15 0.294431 0.247976 0.120952   0.910006           0.693618        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C3    C0      H1         12          12 0.493151 0.402925 0.343105   0.705809           0.290845        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C3    C0      H2         12          12 0.495603 0.384755 0.348575   0.702876           0.283774        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C3    C0      H3         12          12 0.305938 0.256778 0.150396   0.886776           0.727071        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C3    C3      H1         12          12 0.508406 0.425627 0.350015   0.687326           0.246291        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C3    C3      H2         12          12 0.502109 0.391633 0.355309   0.695024           0.264845        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C3    C3      H3         12          12 0.323864 0.274429 0.157102   0.873120           0.694151        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C4    C0      H1         15          15 0.465939 0.377163 0.292258   0.774627           0.232721        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C4    C0      H2         15          15 0.460713 0.352299 0.290871   0.779654           0.249836        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C4    C0      H3         15          15 0.298027 0.252157 0.123966   0.907795           0.686089        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C4    C4      H1         15          15 0.460493 0.372067 0.282121   0.779865           0.250552        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C4    C4      H2         15          15 0.458711 0.348129 0.278133   0.781565           0.256343        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C4    C4      H3         15          15 0.298054 0.252366 0.116298   0.907778           0.686033        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C5    C0      H1         12          12 0.493151 0.402925 0.343105   0.705809           0.290845        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C5    C0      H2         12          12 0.495603 0.384755 0.348575   0.702876           0.283774        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C5    C0      H3         12          12 0.305938 0.256778 0.150396   0.886776           0.727071        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C5    C5      H1         12          12 0.540472 0.442653 0.355556   0.646641           0.148218        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C5    C5      H2         12          12 0.546108 0.417843 0.360446   0.639233           0.130360        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C5    C5      H3         12          12 0.352381 0.289829 0.163555   0.849792           0.637918        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C6    C0      H1         15          15 0.465939 0.377163 0.292258   0.774627           0.232721        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C6    C0      H2         15          15 0.460713 0.352299 0.290871   0.779654           0.249836        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C6    C0      H3         15          15 0.298027 0.252157 0.123966   0.907795           0.686089        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C6    C6      H1         15          15 0.458626 0.368747 0.284511   0.781646           0.256617        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C6    C6      H2         15          15 0.457622 0.346490 0.285357   0.782601           0.259868        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         C6    C6      H3         15          15 0.293944 0.247935 0.120071   0.910304           0.694631        2022Q3       2026Q2
```

Lag sensitivity and accuracy differences:

```text
                scenario model  delta_rmse  n_quarters  n_origins
          ASSUMED_LAG_1M    C1    0.014965          15         45
          ASSUMED_LAG_1M    C2   -0.004650          15         45
          ASSUMED_LAG_1M    C3    0.012577          12         36
          ASSUMED_LAG_1M    C4   -0.003748          15         45
          ASSUMED_LAG_1M    C5    0.046988          12         36
          ASSUMED_LAG_1M    C6   -0.005141          15         45
          ASSUMED_LAG_1M    S1    0.021848          15         45
          ASSUMED_LAG_1M    S2   -0.008108          15         45
          ASSUMED_LAG_1M    S3    0.023734          12         36
          ASSUMED_LAG_1M    S4   -0.007749          15         45
          ASSUMED_LAG_1M    S5    0.087827          12         36
          ASSUMED_LAG_1M    S6   -0.009986          15         45
          ASSUMED_LAG_2M    C1    0.014144          15         45
          ASSUMED_LAG_2M    C2   -0.004782          15         45
          ASSUMED_LAG_2M    C3    0.013084          12         36
          ASSUMED_LAG_2M    C4   -0.004671          15         45
          ASSUMED_LAG_2M    C5    0.043352          12         36
          ASSUMED_LAG_2M    C6   -0.005216          15         45
          ASSUMED_LAG_2M    S1    0.021561          15         45
          ASSUMED_LAG_2M    S2   -0.008068          15         45
          ASSUMED_LAG_2M    S3    0.023712          12         36
          ASSUMED_LAG_2M    S4   -0.007155          15         45
          ASSUMED_LAG_2M    S5    0.081544          12         36
          ASSUMED_LAG_2M    S6   -0.010163          15         45
          ASSUMED_LAG_3M    C1   -0.002920          15         45
          ASSUMED_LAG_3M    C2   -0.003431          15         45
          ASSUMED_LAG_3M    C3    0.013689          12         36
          ASSUMED_LAG_3M    C4   -0.003733          15         45
          ASSUMED_LAG_3M    C5    0.026872          12         34
          ASSUMED_LAG_3M    C6    0.012026          15         45
          ASSUMED_LAG_3M    S1   -0.005681          15         45
          ASSUMED_LAG_3M    S2   -0.005380          15         45
          ASSUMED_LAG_3M    S3    0.023864          12         36
          ASSUMED_LAG_3M    S4   -0.004999          15         45
          ASSUMED_LAG_3M    S5    0.050932          12         34
          ASSUMED_LAG_3M    S6    0.018016          15         45
REVISED_DATA_EXPLORATORY    C1    0.020402          15         45
REVISED_DATA_EXPLORATORY    C2   -0.004301          15         45
REVISED_DATA_EXPLORATORY    C3    0.012333          12         36
REVISED_DATA_EXPLORATORY    C4   -0.002764          15         45
REVISED_DATA_EXPLORATORY    C5    0.047416          12         36
REVISED_DATA_EXPLORATORY    C6   -0.004847          15         45
REVISED_DATA_EXPLORATORY    R1   -0.006662          15         45
REVISED_DATA_EXPLORATORY    R2    0.017397          14         42
REVISED_DATA_EXPLORATORY    R3    0.034502          15         45
REVISED_DATA_EXPLORATORY    S1    0.034480          15         45
REVISED_DATA_EXPLORATORY    S2   -0.007236          15         45
REVISED_DATA_EXPLORATORY    S3    0.023518          12         36
REVISED_DATA_EXPLORATORY    S4   -0.009029          15         45
REVISED_DATA_EXPLORATORY    S5    0.086682          12         36
REVISED_DATA_EXPLORATORY    S6   -0.009268          15         45
```

Robustness: early/recent halves and leave-one-quarter-out **scoring exclusions** are in phase7b_robustness.csv. These remove each target quarter from evaluation, not from expanding-window training. Alternative-transform models R1/R2 and outlier sensitivity R3 use the same architecture; no tuning against current GDP. Factor stability uses sign-aligned filtered-factor correlations and descriptive factor differences on aligned histories. Exploratory absolute factor correlations (minimum/mean across fits):             min      mean
model                    
R1     0.993242  0.999082
R2     0.803782  0.974979
R3     0.973503  0.998771
S1     0.973501  0.998691
S2     0.983427  0.996502
S3     0.990483  0.997221
S4     0.982815  0.996472
S5     0.192732  0.934667
S6     0.984402  0.996936. Matched NO2-history controls:                 scenario comparison                  model  n_origins  n_quarters     rmse      mae     bias  r_squared  oos_r_squared_ar1 first_quarter last_quarter
REVISED_DATA_EXPLORATORY         S3                     S3         33          11 0.524512 0.436416 0.428782   0.657242           0.246018        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S3 M0_NO2_HISTORY_CONTROL         33          11 0.531669 0.441977 0.434332   0.647825           0.225302        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S5                     S5         33          11 0.598419 0.467318 0.443996   0.553844           0.018567        2022Q3       2026Q2
REVISED_DATA_EXPLORATORY         S5 M0_NO2_HISTORY_CONTROL         33          11 0.531669 0.441977 0.434332   0.647825           0.225302        2022Q3       2026Q2. S3 conclusions depend on whether the original or shortened-history baseline is used; this is a material sample-length confound. Loadings and loading times standardized measurements are descriptive signals, never direct GDP percentage-point contributions or causal effects. Economic-predictor correlations include aligned-pair counts; redundancy and correlations alone cannot establish incremental prediction.

The conservative classification requires at least 12 matched quarters, combination improvement at all four delays and every LOQO/temporal subset. Primary combinations worsening on adequate exploratory samples imply no improvement; mixed, short or unstable evidence is inconclusive. No significance claim is made. Provenance and release verification are still mandatory before any operational consideration.

Current research predictions (frozen cutoff 2026-10-05; null indicates model failure):

```text
model                 scenario  prediction  failure
   M0 REVISED_DATA_EXPLORATORY    8.301153      NaN
   U0 REVISED_DATA_EXPLORATORY    8.060650      NaN
   C0 REVISED_DATA_EXPLORATORY    8.180901      NaN
   S1 REVISED_DATA_EXPLORATORY    8.303192      NaN
   C1 REVISED_DATA_EXPLORATORY    8.181921      NaN
   S2 REVISED_DATA_EXPLORATORY    8.300477      NaN
   C2 REVISED_DATA_EXPLORATORY    8.180563      NaN
   S3 REVISED_DATA_EXPLORATORY    8.314607      NaN
   C3 REVISED_DATA_EXPLORATORY    8.187628      NaN
   S4 REVISED_DATA_EXPLORATORY    8.302387      NaN
   C4 REVISED_DATA_EXPLORATORY    8.181519      NaN
   S5 REVISED_DATA_EXPLORATORY    8.317020      NaN
   C5 REVISED_DATA_EXPLORATORY    8.188835      NaN
   S6 REVISED_DATA_EXPLORATORY    8.300763      NaN
   C6 REVISED_DATA_EXPLORATORY    8.180706      NaN
   R1 REVISED_DATA_EXPLORATORY    8.302890      NaN
   R2 REVISED_DATA_EXPLORATORY    8.300328      NaN
   R3 REVISED_DATA_EXPLORATORY    8.303300      NaN
   M0           ASSUMED_LAG_1M    8.301153      NaN
   U0           ASSUMED_LAG_1M    8.060650      NaN
   C0           ASSUMED_LAG_1M    8.180901      NaN
   S1           ASSUMED_LAG_1M    8.303192      NaN
   C1           ASSUMED_LAG_1M    8.181921      NaN
   S2           ASSUMED_LAG_1M    8.300477      NaN
   C2           ASSUMED_LAG_1M    8.180563      NaN
   S3           ASSUMED_LAG_1M    8.314607      NaN
   C3           ASSUMED_LAG_1M    8.187628      NaN
   S4           ASSUMED_LAG_1M    8.302387      NaN
   C4           ASSUMED_LAG_1M    8.181519      NaN
   S5           ASSUMED_LAG_1M    8.317020      NaN
   C5           ASSUMED_LAG_1M    8.188835      NaN
   M0           ASSUMED_LAG_2M    8.301153      NaN
   U0           ASSUMED_LAG_2M    8.060650      NaN
   C0           ASSUMED_LAG_2M    8.180901      NaN
   S1           ASSUMED_LAG_2M    8.302136      NaN
   C1           ASSUMED_LAG_2M    8.181393      NaN
   S2           ASSUMED_LAG_2M    8.299651      NaN
   C2           ASSUMED_LAG_2M    8.180150      NaN
   S3           ASSUMED_LAG_2M    8.314486      NaN
   C3           ASSUMED_LAG_2M    8.187568      NaN
   S4           ASSUMED_LAG_2M    8.300506      NaN
   C4           ASSUMED_LAG_2M    8.180578      NaN
   S5           ASSUMED_LAG_2M    8.315664      NaN
   C5           ASSUMED_LAG_2M    8.188157      NaN
   M0           ASSUMED_LAG_3M    8.301153      NaN
   U0           ASSUMED_LAG_3M    8.060650      NaN
   C0           ASSUMED_LAG_3M    8.180901      NaN
   S1           ASSUMED_LAG_3M    8.301287      NaN
   C1           ASSUMED_LAG_3M    8.180968      NaN
   S2           ASSUMED_LAG_3M    8.299092      NaN
   C2           ASSUMED_LAG_3M    8.179871      NaN
   S3           ASSUMED_LAG_3M    8.314614      NaN
   C3           ASSUMED_LAG_3M    8.187632      NaN
   S4           ASSUMED_LAG_3M    8.299098      NaN
   C4           ASSUMED_LAG_3M    8.179874      NaN
   S5           ASSUMED_LAG_3M    8.314787      NaN
   C5           ASSUMED_LAG_3M    8.187719      NaN
   S6           ASSUMED_LAG_1M    8.300763      NaN
   C6           ASSUMED_LAG_1M    8.180706      NaN
   S6           ASSUMED_LAG_2M    8.300077      NaN
   C6           ASSUMED_LAG_2M    8.180363      NaN
   S6           ASSUMED_LAG_3M    8.299598      NaN
   C6           ASSUMED_LAG_3M    8.180124      NaN
```

Production independently recomputed: {'dfm': {'recomputed': 8.301152885464585, 'frozen': 8.301152885464585, 'error': 0.0}, 'umidas': {'recomputed': 8.060649795767965, 'frozen': 8.060649795767965, 'error': 0.0}, 'final': {'recomputed': 8.180901340616275, 'frozen': 8.180901340616275, 'error': 0.0}}. Protected existing artifacts verified unchanged: 24929 files. Tests are recorded separately in phase7b_tests.log/xml. The legacy whole-repository hash test is excluded because it predates authorized research artifacts; production seal tests and the independent protection audit remain active. Offline reproduce: `.venv/Scripts/python.exe -m scripts.phase7b.run`. Dashboard: C:\Users\Sh.Nishonqulov\Desktop\uzbekistan_nowcast_codex_starter\results\phase7b\phase7b_satellite_comparison.html.

Metadata needed: exact sensor products and versions, units/scaling, geography and weights, quality/cloud/snow masks, monthly compositing code, processing changes around 2016–2017, extraction timestamp, source links, reproducible scripts, first-publication dates and revisions. No experimental model promoted.

Final validation: 78 selected offline tests passed, zero failures/errors. Headless Edge rendered ten SVG charts and successfully switched S3 / H2 / assumed three-month delay. Two independent S1 refits reproduced identical predictions, loadings and factor paths. Production M0/U0/C0 reproduced with exact float equality; 24,929 pre-existing protected scientific files passed the independent integrity audit.
