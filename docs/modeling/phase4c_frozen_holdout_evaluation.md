# Phase 4C — Frozen holdout evaluation

Phase 4C evaluates the model architecture frozen in
`results/phase4b_candidate_freeze.json`. No predictor, transformation, lag,
weight, release assumption, preprocessing rule, DFM setting, or model family
was changed after the validation outcomes were opened.

## 1. Protocol and holdout opening

The machine-readable protocol was written at
`2026-09-30T04:57:10.689403Z`, before any frozen GDP outcome was loaded. Its
evaluation-rules SHA-256 is
`2ab62646b6ff046a7c586bb5aa5754ea6af8245ff3d78d2d9a06440613d448f7`.

All required input hashes matched both the Phase 4B candidate freeze and the
frozen-validation definition:

| Input | SHA-256 | Passed |
| --- | --- | --- |
| `v1_monthly.parquet` | `78a7c51b97247d3ccbd72cbcb03b89f6f52f0f091201956bba85c0373856ba7c` | Yes |
| `gdp_quarterly.parquet` | `36793699e48de74ecfe31eeb7eb8f23cf3eb6f2ab9ca929cdd4bb240c1bdfbac` | Yes |
| `uzbekistan_nowcasting_v1.2_registry.xlsx` | `0659713cea0fea42c3823a3be26dd116ba15f2b292f269ba5f7e1c7b99abbb33` | Yes |

The hashes were revalidated immediately before opening. The first holdout GDP
read began at **2026-09-30T04:58:39.398660Z** and completed at
`2026-09-30T04:58:39.607737Z`. The recorded step was
`load_phase4c_dataset:load_dataset quarterly target read`.

The protocol's `post_load_rule_mutations` list is empty.

## 2. Frozen evaluation design

- Holdout: 2025Q3, 2025Q4, 2026Q1, 2026Q2.
- Primary candidates: AR(1), AR(2), USD/UZS U-MIDAS(3), and the fixed 50/50
  AR(2)–USD U-MIDAS ensemble.
- Additional benchmark: expanding historical mean.
- Main accuracy benchmark: AR(2).
- Horizons: H1, H2, H3.
- Primary release assumption: standard.
- Robustness release assumption: conservative.
- Primary metric: RMSE; secondary metrics: MAE and bias.
- Estimation: expanding window. An earlier holdout outcome enters only a later
  holdout origin; the current and future outcomes never enter estimation.
- Comparison: exact matched observations.

All five models produced predictions for all four quarters under every horizon
and lag mode. No DFM was added to the primary tables. The Phase 4B approximate
DFMs remain diagnostic, and no Kalman DFM was implemented or tested.

## 3. Frozen outcomes

| Quarter | Real GDP YoY, % |
| --- | ---: |
| 2025Q3 | 7.6 |
| 2025Q4 | 7.7 |
| 2026Q1 | 8.7 |
| 2026Q2 | 8.5 |

## 4. Primary standard-lag results

### Horizon-specific accuracy

| Horizon | Model | N | RMSE | MAE | Bias | RMSE / matched AR(2) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| H1 | AR(1) | 4 | 0.8340 | 0.7313 | 0.7313 | 0.8448 |
| H1 | Ensemble | 4 | 0.8518 | 0.7138 | 0.5556 | 0.8629 |
| H1 | USD U-MIDAS | 4 | 0.9670 | 0.9125 | 0.3023 | 0.9796 |
| H1 | AR(2) | 4 | 0.9871 | 0.8089 | 0.8089 | 1.0000 |
| H1 | Historical mean | 4 | 2.2092 | 2.1680 | 2.1680 | 2.2380 |
| H2 | AR(1) | 4 | 0.8340 | 0.7313 | 0.7313 | 0.8448 |
| H2 | Ensemble | 4 | 0.8663 | 0.6669 | 0.5603 | 0.8776 |
| H2 | USD U-MIDAS | 4 | 0.9302 | 0.8187 | 0.3118 | 0.9423 |
| H2 | AR(2) | 4 | 0.9871 | 0.8089 | 0.8089 | 1.0000 |
| H2 | Historical mean | 4 | 2.2092 | 2.1680 | 2.1680 | 2.2380 |
| H3 | Ensemble | 4 | 0.5298 | 0.3706 | 0.2837 | 0.5367 |
| H3 | USD U-MIDAS | 4 | 0.5428 | 0.4442 | -0.2416 | 0.5499 |
| H3 | AR(1) | 4 | 0.8340 | 0.7313 | 0.7313 | 0.8448 |
| H3 | AR(2) | 4 | 0.9871 | 0.8089 | 0.8089 | 1.0000 |
| H3 | Historical mean | 4 | 2.2092 | 2.1680 | 2.1680 | 2.2380 |

AR(1) has the lowest RMSE at H1 and H2. The ensemble has the lowest H3 RMSE,
46.3% below matched AR(2). USD U-MIDAS is close behind at H3.

### Pooled H1–H3 standard-lag accuracy

The pooled calculation treats each quarter/horizon forecast as one observation,
for 12 observations per model.

| Model | N | RMSE | MAE | Bias | RMSE / AR(2) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ensemble | 12 | 0.7652 | 0.5837 | 0.4665 | 0.7752 |
| AR(1) | 12 | 0.8340 | 0.7313 | 0.7313 | 0.8448 |
| USD U-MIDAS | 12 | 0.8356 | 0.7251 | 0.1241 | 0.8465 |
| AR(2) | 12 | 0.9871 | 0.8089 | 0.8089 | 1.0000 |
| Historical mean | 12 | 2.2092 | 2.1680 | 2.1680 | 2.2380 |

## 5. Quarter-level standard-lag forecasts and errors

Each model cell is `forecast (actual − forecast)`.

### H1

| Quarter | Actual | Historical mean | AR(1) | AR(2) | USD U-MIDAS | Ensemble |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2025Q3 | 7.6 | 5.867 (1.733) | 6.881 (0.719) | 6.860 (0.740) | 6.726 (0.874) | 6.793 (0.807) |
| 2025Q4 | 7.7 | 5.923 (1.777) | 7.214 (0.486) | 7.112 (0.588) | 8.920 (-1.220) | 8.016 (-0.316) |
| 2026Q1 | 8.7 | 5.978 (2.722) | 7.316 (1.384) | 6.976 (1.724) | 7.550 (1.150) | 7.263 (1.437) |
| 2026Q2 | 8.5 | 6.061 (2.439) | 8.165 (0.335) | 8.316 (0.184) | 8.094 (0.406) | 8.205 (0.295) |

### H2

| Quarter | Actual | Historical mean | AR(1) | AR(2) | USD U-MIDAS | Ensemble |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2025Q3 | 7.6 | 5.867 (1.733) | 6.881 (0.719) | 6.860 (0.740) | 6.825 (0.775) | 6.843 (0.757) |
| 2025Q4 | 7.7 | 5.923 (1.777) | 7.214 (0.486) | 7.112 (0.588) | 8.714 (-1.014) | 7.913 (-0.213) |
| 2026Q1 | 8.7 | 5.978 (2.722) | 7.316 (1.384) | 6.976 (1.724) | 7.353 (1.347) | 7.165 (1.535) |
| 2026Q2 | 8.5 | 6.061 (2.439) | 8.165 (0.335) | 8.316 (0.184) | 8.361 (0.139) | 8.338 (0.162) |

### H3

| Quarter | Actual | Historical mean | AR(1) | AR(2) | USD U-MIDAS | Ensemble |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2025Q3 | 7.6 | 5.867 (1.733) | 6.881 (0.719) | 6.860 (0.740) | 8.036 (-0.436) | 7.448 (0.152) |
| 2025Q4 | 7.7 | 5.923 (1.777) | 7.214 (0.486) | 7.112 (0.588) | 8.635 (-0.935) | 7.874 (-0.174) |
| 2026Q1 | 8.7 | 5.978 (2.722) | 7.316 (1.384) | 6.976 (1.724) | 8.372 (0.328) | 7.674 (1.026) |
| 2026Q2 | 8.5 | 6.061 (2.439) | 8.165 (0.335) | 8.316 (0.184) | 8.423 (0.077) | 8.369 (0.131) |

## 6. Conservative-lag robustness

| Horizon | Best model | Best RMSE | Ensemble RMSE | USD U-MIDAS RMSE | AR(1) RMSE | AR(2) RMSE |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| H1 | USD U-MIDAS | 0.6236 | 0.7999 | 0.6236 | 0.8340 | 0.9871 |
| H2 | AR(1) | 0.8340 | 0.8518 | 0.9670 | 0.8340 | 0.9871 |
| H3 | AR(1) | 0.8340 | 0.8663 | 0.9302 | 0.8340 | 0.9871 |

The release-lag shift moves the USD information sequence by approximately one
horizon: conservative H2 matches standard H1, and conservative H3 matches
standard H2. Relative to standard, conservative ensemble RMSE changes by
-0.0519 at H1, -0.0145 at H2, and +0.3365 at H3.

## 7. Forecast revisions

Benchmark forecasts use only quarterly GDP and therefore do not revise across
H1/H2/H3. Under the standard assumption:

| Model | Mean absolute H1→H2 revision | Mean absolute H2→H3 revision |
| --- | ---: | ---: |
| USD U-MIDAS | 0.1921 | 0.5926 |
| Ensemble | 0.0961 | 0.2963 |
| Historical mean / AR(1) / AR(2) | 0.0000 | 0.0000 |

The largest standard H2→H3 USD revision is 1.2112 percentage points. The fixed
ensemble halves every USD-only revision because its AR(2) component does not
change across horizons.

## 8. Ensemble diagnostics

The ensemble remained exactly 50% AR(2) and 50% USD U-MIDAS for every row.
Component-error correlations under the standard assumption are 0.485 at H1,
0.663 at H2, and 0.444 at H3. Under the conservative assumption they are
0.966, 0.485, and 0.663 respectively. Quarter-level component forecasts and
errors are preserved in `results/phase4c_ensemble_diagnostics`.

## 9. Interpretation and limitation

This holdout contains only four quarters. The tables are a frozen evaluation,
not a new model-selection exercise, and no architecture decision was changed
after observing them. The results show useful late-horizon information in the
USD U-MIDAS signal and diversification from the fixed ensemble, while AR(1)
remains competitive at early horizons. Claims beyond these four observations
would be unwarranted.

## 10. Outputs

- `results/phase4c_evaluation_protocol.json`
- `results/phase4c_holdout_predictions.csv` and `.parquet`
- `results/phase4c_holdout_metrics.csv` and `.parquet`
- `results/phase4c_horizon_updates.csv` and `.parquet`
- `results/phase4c_ensemble_diagnostics.csv` and `.parquet`
- `results/phase4c_model_comparison.csv` and `.parquet`

