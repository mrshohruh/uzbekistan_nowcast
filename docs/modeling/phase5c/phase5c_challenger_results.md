# Phase 5C challenger results

## 1. Executive summary

The leading research specification is `challenger_umidas_gold_exports_proxy_usd_m_l1` with development relative RMSE 0.607 and gate `REJECT`. The production model remains frozen. Phase 5C evidence cannot promote a model;
any credible candidate must enter Phase 5D prospective shadow evaluation.

## 2. Frozen production benchmark

The benchmark is 0.5 × AR(2) + 0.5 × USD/UZS U-MIDAS(3). Its 2026Q3 H2
nowcast remains 7.6239786596%. No production file was written.

## 3. Research protocol

The protocol was frozen before estimation. Monthly values are admitted using the registry lag
and the frozen standard/conservative timing rules. Expanding windows exclude the target and
all future GDP outcomes.

## 4. Available predictor universe

The registry contains 28 monthly predictors: primary=6,
secondary=14, diagnostic=7,
ineligible=1.

## 5. Univariate screening results

The fixed lag grid was 1–3 months. The shortlist was limited to five predictors and no more
than two per registry block. Selected signals: usd_uzs, ppi, m2, rub_uzs, fx_reserves_ex_gold.

## 6. Multivariate MIDAS results

Only preregistered, cross-block pairs of shortlisted predictors were tested, with two
predictors maximum and Almon(1) restrictions over three monthly lags.

## 7. Bridge-model results

Bridge equations use available-month quarterly means and one GDP lag. Missing future months
are not synthesized.

## 8. DFM reassessment

The reassessment uses tight shortlisted panels and one factor. It remains an approximate
EM-PCA factor bridge, not a Kalman DFM, and is compared with the earlier diagnostic decision.

## 9. Forecast-combination results

Equal, median, trimmed, inverse-past-RMSE and non-negative past stacking combinations were
evaluated. Performance weights use only outcomes earlier than each forecast origin.

## 10. Horizon-specific comparison

H1, H2 and H3 are reported separately in `phase5c_horizon_comparison.csv`; pooled figures
never replace the horizon-level evidence.

## 11. Stability and influence diagnostics

Coefficient changes, failure rates and leave-one-quarter-out relative RMSE are reported.
An apparent advantage that disappears after one quarter is labelled `FRAGILE_IMPROVEMENT`.

## 12. Release-lag robustness

Shortlisted models are reported under both frozen standard and conservative release lags.

## 13. 2026Q3 shadow forecasts

These are live H2 shadow forecasts as of 2026-09-30. The 2026Q3 GDP realization is unknown,
and current forecast levels were not used for model selection.

## 14. Challenger gate decisions

Only REJECT, RETAIN_FOR_RESEARCH, SHADOW_CHALLENGER and STRONG_SHADOW_CHALLENGER are
permitted. `PRODUCTION_MODEL` is deliberately unavailable.

## 15. Limitations

The quarterly sample is small; historical release dates are not observed for most series;
registry lags approximate real-time availability; revised current-vintage GDP is used; and
2025Q3–2026Q2 is not a pristine holdout because those outcomes were previously examined.

## 16. Recommendation for Phase 5D

Keep production unchanged. Run credible shadow candidates prospectively against genuinely
new GDP releases before considering any governance decision.
