# Phase 7C indicator passports

## Retail trade turnover

1. Indicator: Retail trade turnover.
2. Provider: National Statistics Committee / SIAT. [Official source](https://siat.stat.uz/data/2699/?lang=en). 
3. Definition/unit: national current-price turnover/works in billion UZS. Retail source million sums scaled by 0.001. Export residual is a derived proxy, never official non-gold exports.
4. Coverage: raw 2020-01 to 2026-08; usable growth 2021-01 to 2026-08 (68 months).
5. Mechanism: Consumption-related demand and trade services value added.
6. Interpretation: production and expenditure channels; sales/works values are not directly GDP value added.
7. Expected relationship: expansion often accompanies GDP growth; factor loading sign is unrestricted.
8. Sign changes: Nominal sales also reflect inflation, imported goods and changes in formal coverage. Remittances can support demand without equivalent domestic production.
9. Uzbekistan relevance: household demand, remittance-supported spending and domestic distribution. These are economic hypotheses, not quantified structural estimates.
10. Overlap: POS turnover already measures payment-mediated demand; overlap can limit incremental information.
11. Primary transformation: within-year de-cumulation then 100 ln(flow_t/flow_t-12), strictly positive pairs. CPI sensitivity subtracts trailing twelve monthly CPI log changes; approximate purchasing-power adjustment, not retail volume.
12. Availability: assumed 24 days after reference month end; +15/+30-day sensitivities. Stored latest source update is not historical first publication. Current frozen-cutoff candidate data were retrieved before 2026-10-05.
13. Risks: Nominal sales also reflect inflation, imported goods and changes in formal coverage. Remittances can support demand without equivalent domestic production. Revised history and annual reconciliation can change prior monthly flows; de-cumulation magnifies revisions. Historical analysis is RETROSPECTIVE_EXPLORATORY.
14. Incremental evidence:

```text
model  n_origins  n_quarters     rmse      mae     bias  r_squared  oos_r_squared_ar1
   M0         24           8 0.591581 0.524502 0.524502   0.409337           0.175423
   R1         24           8 0.739609 0.623326 0.528695   0.076757          -0.288864

On 24 origins / 8 GDP quarters (2024Q1–2026Q1), DFM RMSE gain is -0.1480 pp and fixed-combination RMSE gain is -0.0351 pp (positive means improvement). Quarter-level mean squared-error gain interval [-0.3946, -0.0231] pp². Sensitivities: LAG_PLUS_15D: -0.1486 pp; LAG_PLUS_30D: -0.1486 pp; TRAINING_ONLY_WINSOR_1_99: -0.1487 pp. On 22 converged identical-history-control origins, the DFM RMSE gain is -0.0101 pp; this separates history truncation from added information.
```

15. Decision: **NO_INCREMENTAL_VALUE**. Reject this addition in the tested specification because matched DFM and combined accuracy deteriorate. Economic relevance remains plausible; short revised histories and convergence failures limit broader conclusions.

Management explanation: Consumption-related demand and trade services value added. Nominal sales also reflect inflation, imported goods and changes in formal coverage. Remittances can support demand without equivalent domestic production. Forecasting evidence is distinct from theoretical plausibility. Correlation and loading signals describe association, not causal effects or GDP percentage-point contributions.

## Construction works

1. Indicator: Construction works.
2. Provider: National Statistics Committee / SIAT. [Official source](https://siat.stat.uz/data/2403/?lang=en). 
3. Definition/unit: national current-price turnover/works in billion UZS. Retail source million sums scaled by 0.001. Export residual is a derived proxy, never official non-gold exports.
4. Coverage: raw 2021-01 to 2026-08; usable growth 2022-01 to 2026-08 (56 months).
5. Mechanism: Construction value added and investment-related activity.
6. Interpretation: production and expenditure channels; sales/works values are not directly GDP value added.
7. Expected relationship: expansion often accompanies GDP growth; factor loading sign is unrestricted.
8. Sign changes: Project timing, input costs and imported materials can separate nominal works from real domestic value added.
9. Uzbekistan relevance: infrastructure and building investment. These are economic hypotheses, not quantified structural estimates.
10. Overlap: Industrial production and M2 can already capture materials demand and credit conditions.
11. Primary transformation: within-year de-cumulation then 100 ln(flow_t/flow_t-12), strictly positive pairs. No construction-specific deflator validated; no headline-CPI construction deflation.
12. Availability: assumed 27 days after reference month end; +15/+30-day sensitivities. Stored latest source update is not historical first publication. Current frozen-cutoff candidate data were retrieved before 2026-10-05.
13. Risks: Project timing, input costs and imported materials can separate nominal works from real domestic value added. Revised history and annual reconciliation can change prior monthly flows; de-cumulation magnifies revisions. Historical analysis is RETROSPECTIVE_EXPLORATORY.
14. Incremental evidence:

```text
model  n_origins  n_quarters     rmse      mae     bias  r_squared  oos_r_squared_ar1
   M0         18           6 0.633364 0.536965 0.536965   0.106902           0.249661
   R2         18           6 1.106799 1.039932 1.039932  -1.727280          -1.291332

On 18 origins / 6 GDP quarters (2025Q1–2026Q2), DFM RMSE gain is -0.4734 pp and fixed-combination RMSE gain is -0.1794 pp (positive means improvement). Quarter-level mean squared-error gain interval [-1.1191, -0.4814] pp². Sensitivities: LAG_PLUS_15D: -0.4690 pp; LAG_PLUS_30D: -0.4690 pp; TRAINING_ONLY_WINSOR_1_99: -0.4571 pp. On 18 converged identical-history-control origins, the DFM RMSE gain is +0.0116 pp; this separates history truncation from added information.
```

15. Decision: **NO_INCREMENTAL_VALUE**. Reject this addition in the tested specification because matched DFM and combined accuracy deteriorate. Economic relevance remains plausible; short revised histories and convergence failures limit broader conclusions.

Management explanation: Construction value added and investment-related activity. Project timing, input costs and imported materials can separate nominal works from real domestic value added. Forecasting evidence is distinct from theoretical plausibility. Correlation and loading signals describe association, not causal effects or GDP percentage-point contributions.

## Total imports

1. Indicator: Total imports.
2. Provider: National Statistics Committee / SIAT. [Official source](https://siat.stat.uz/data/1162/?lang=en). 
3. Definition/unit: national USD-valued trade flow in million USD. Retail source million sums scaled by 0.001. Export residual is a derived proxy, never official non-gold exports.
4. Coverage: raw 2021-01 to 2026-08; usable growth 2022-01 to 2026-08 (56 months).
5. Mechanism: Intermediate inputs, capital investment and household demand.
6. Interpretation: external trade and domestic demand channels; sales/works values are not directly GDP value added.
7. Expected relationship: expansion often accompanies GDP growth; factor loading sign is unrestricted.
8. Sign changes: Imports subtract from expenditure GDP but may accompany domestic expansion; USD prices, exchange rates and substitution can reverse association. This is value growth, not volume growth.
9. Uzbekistan relevance: imported equipment and intermediate-input dependence. These are economic hypotheses, not quantified structural estimates.
10. Overlap: FX, industrial production and M2 overlap with financing and input-demand channels.
11. Primary transformation: within-year de-cumulation then 100 ln(flow_t/flow_t-12), strictly positive pairs. Nominal USD-value growth.
12. Availability: assumed 26 days after reference month end; +15/+30-day sensitivities. Stored latest source update is not historical first publication. Current frozen-cutoff candidate data were retrieved before 2026-10-05.
13. Risks: Imports subtract from expenditure GDP but may accompany domestic expansion; USD prices, exchange rates and substitution can reverse association. This is value growth, not volume growth. Revised history and annual reconciliation can change prior monthly flows; de-cumulation magnifies revisions. Historical analysis is RETROSPECTIVE_EXPLORATORY.
14. Incremental evidence:

```text
model  n_origins  n_quarters     rmse      mae     bias  r_squared  oos_r_squared_ar1
   M0         18           6 0.633364 0.536965 0.536965   0.106902           0.249661
   R3         18           6 1.117425 1.053000 1.053000  -1.779899          -1.335539

On 18 origins / 6 GDP quarters (2025Q1–2026Q2), DFM RMSE gain is -0.4841 pp and fixed-combination RMSE gain is -0.1805 pp (positive means improvement). Quarter-level mean squared-error gain interval [-1.1399, -0.5066] pp². Sensitivities: LAG_PLUS_15D: -0.4839 pp; LAG_PLUS_30D: -0.4839 pp; TRAINING_ONLY_WINSOR_1_99: -0.4839 pp. On 18 converged identical-history-control origins, the DFM RMSE gain is +0.0010 pp; this separates history truncation from added information.
```

15. Decision: **NO_INCREMENTAL_VALUE**. Reject this addition in the tested specification because matched DFM and combined accuracy deteriorate. Economic relevance remains plausible; short revised histories and convergence failures limit broader conclusions.

Management explanation: Intermediate inputs, capital investment and household demand. Imports subtract from expenditure GDP but may accompany domestic expansion; USD prices, exchange rates and substitution can reverse association. This is value growth, not volume growth. Forecasting evidence is distinct from theoretical plausibility. Correlation and loading signals describe association, not causal effects or GDP percentage-point contributions.

## NON_GOLD_EXPORT_PROXY

1. Indicator: NON_GOLD_EXPORT_PROXY.
2. Provider: National Statistics Committee / SIAT. [Official source](https://siat.stat.uz/data/1103/?lang=en). [Other goods parent](https://siat.stat.uz/data/3082/?lang=en).
3. Definition/unit: national USD-valued trade flow in million USD. Retail source million sums scaled by 0.001. Export residual is a derived proxy, never official non-gold exports.
4. Coverage: raw 2021-01 to 2026-08; usable growth 2022-01 to 2026-08 (56 months).
5. Mechanism: Foreign demand and non-gold tradable activity, approximated by total exports less Other goods.
6. Interpretation: external trade and domestic demand channels; sales/works values are not directly GDP value added.
7. Expected relationship: expansion often accompanies GDP growth; factor loading sign is unrestricted.
8. Sign changes: Other goods is not verified as exact gold; one negative monthly parent increment prevents primary validation. Gold shipment timing and services revisions can distort the residual.
9. Uzbekistan relevance: gold-related shipment volatility in external trade. These are economic hypotheses, not quantified structural estimates.
10. Overlap: Gold price and exchange rates already capture external conditions.
11. Primary transformation: within-year de-cumulation then 100 ln(flow_t/flow_t-12), strictly positive pairs. Both export parents de-cumulated before subtraction.
12. Availability: assumed 26 days after reference month end; +15/+30-day sensitivities. Stored latest source update is not historical first publication. Current frozen-cutoff candidate data were retrieved before 2026-10-05.
13. Risks: Other goods is not verified as exact gold; one negative monthly parent increment prevents primary validation. Gold shipment timing and services revisions can distort the residual. Revised history and annual reconciliation can change prior monthly flows; de-cumulation magnifies revisions. Historical analysis is RETROSPECTIVE_EXPLORATORY.
14. Incremental evidence:

```text
Not estimated: parent-flow validation failed.
```

15. Decision: **DATA_NOT_VALIDATED**. Resolve the negative parent increment and validate category compatibility before primary testing.

Management explanation: Foreign demand and non-gold tradable activity, approximated by total exports less Other goods. Other goods is not verified as exact gold; one negative monthly parent increment prevents primary validation. Gold shipment timing and services revisions can distort the residual. Forecasting evidence is distinct from theoretical plausibility. Correlation and loading signals describe association, not causal effects or GDP percentage-point contributions.
