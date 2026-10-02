# Phase 2C results

## 1. Implementation summary

Registry V1.1 (2026-09-29) drove all 29 V1 attempts. GDP remains quarterly; the monthly panel is ragged and contains no imputation or interpolation. The build status is `partial_with_failures` with 28 automated series and 1 unresolved series.

## 2. Test results

The completion test command and final count are recorded after the final offline replay. Pipeline validation status: `partial_with_failures`.

## 3. Actual coverage of all 29 variables

| variable_key | first_raw_observation | first_usable_transformed_observation | last_observation | observations | current_status | warnings |
| --- | --- | --- | --- | --- | --- | --- |
| gdp_real_yoy | 2018-03-31 | 2018-03-31 | 2026-06-30 | 34 | automated |  |
| industrial_production | 2019-01-31 | 2020-01-31 | 2026-08-31 | 92 | automated | extreme_log_change; missing_growth_input |
| manufacturing | 2019-01-31 | 2020-01-31 | 2026-08-31 | 92 | automated | extreme_log_change; missing_growth_input |
| mining | 2019-01-31 | 2020-01-31 | 2026-08-31 | 92 | automated | extreme_log_change; missing_growth_input |
| electricity_gas | 2019-01-31 | 2020-01-31 | 2026-08-31 | 92 | automated | extreme_log_change; extreme_monthly_increment; missing_growth_input |
| construction | 2021-01-31 | 2022-01-31 | 2026-08-31 | 68 | automated | extreme_log_change; extreme_monthly_increment; missing_growth_input |
| retail_trade | 2020-01-31 | 2021-01-31 | 2026-08-31 | 80 | automated | extreme_log_change; extreme_monthly_increment; missing_growth_input |
| wholesale_trade | 2020-01-31 | 2021-01-31 | 2026-08-31 | 80 | automated | extreme_log_change; extreme_monthly_increment; missing_growth_input; nonpositive_growth_input; nonpositive_monthly_flow |
| cpi_headline | 2021-01-31 | 2021-01-31 | 2026-08-31 | 68 | automated |  |
| cpi_food | 2021-01-31 | 2021-01-31 | 2026-08-31 | 68 | automated |  |
| cpi_services | 2021-01-31 | 2021-01-31 | 2026-08-31 | 68 | automated |  |
| ppi | 2013-01-31 | 2013-01-31 | 2026-08-31 | 164 | automated |  |
| exports_total | 2021-01-31 | 2022-01-31 | 2026-08-31 | 68 | automated | extreme_log_change; missing_growth_input |
| exports_non_gold | 2021-01-31 | 2022-01-31 | 2026-08-31 | 68 | automated | extreme_log_change; extreme_monthly_increment; missing_growth_input; nonpositive_monthly_flow |
| imports_total | 2021-01-31 | 2022-01-31 | 2026-08-31 | 68 | automated | extreme_log_change; missing_growth_input |
| gold_exports_proxy | 2021-01-31 | 2021-01-31 | 2026-08-31 | 68 | automated | extreme_monthly_increment; nonpositive_monthly_flow |
| usd_uzs | 2013-01-31 | 2013-02-28 | 2026-10-31 | 166 | automated | extreme_log_change; missing_growth_input; partial_month |
| rub_uzs | 2013-01-31 | 2013-02-28 | 2026-10-31 | 166 | automated | extreme_log_change; missing_growth_input; partial_month |
| gold_price | 1960-01-31 | 1960-02-29 | 2026-08-31 | 800 | automated | missing_growth_input |
| russia_ipi |  |  |  | 0 | unresolved | SSLError: HTTPSConnectionPool(host='rosstat.gov.ru', port=443): Max retries exceeded with url: /enterprise_industrial (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)'))) |
| m2 | 2013-01-31 | 2014-01-31 | 2026-08-31 | 164 | automated | missing_growth_input |
| household_deposits | 2022-07-31 | 2023-07-31 | 2026-06-30 | 28 | automated | missing_growth_input |
| corporate_deposits | 2022-07-31 | 2023-07-31 | 2026-06-30 | 28 | automated | missing_growth_input |
| household_credit | 2022-07-31 | 2023-07-31 | 2026-06-30 | 28 | automated | missing_growth_input |
| corporate_credit | 2022-07-31 | 2023-07-31 | 2026-06-30 | 28 | automated | missing_growth_input |
| fx_reserves_ex_gold | 2013-01-31 | 2014-01-31 | 2026-08-31 | 164 | automated | missing_growth_input |
| pos_turnover | 2018-12-31 | 2020-01-31 | 2026-06-30 | 58 | automated | extreme_log_change; missing_growth_input; missing_previous_month; nonpositive_monthly_flow |
| instant_payments | 2021-01-31 | 2022-01-31 | 2026-06-30 | 39 | automated | extreme_log_change; missing_growth_input |
| interbank_payments | 2018-12-31 | 2019-12-31 | 2025-11-30 | 31 | automated | extreme_log_change; missing_growth_input |

## 4. Variables successfully automated

gdp_real_yoy, industrial_production, manufacturing, mining, electricity_gas, construction, retail_trade, wholesale_trade, cpi_headline, cpi_food, cpi_services, ppi, exports_total, imports_total, gold_exports_proxy, usd_uzs, rub_uzs, gold_price, m2, household_deposits, corporate_deposits, household_credit, corporate_credit, fx_reserves_ex_gold, pos_turnover, instant_payments, interbank_payments, exports_non_gold.

## 5. Variables requiring archive spiders

household_deposits, corporate_deposits, household_credit, corporate_credit, pos_turnover, instant_payments, interbank_payments.

## 6. External-series status

gold_price: automated, russia_ipi: SSLError: HTTPSConnectionPool(host='rosstat.gov.ru', port=443): Max retries exceeded with url: /enterprise_industrial (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)'))).

## 7. Derived-series status

exports_non_gold: automated.

## 8. Missingness analysis

The union panel spans 1960-01-31 to 2026-10-31. Threshold dates: {"25": "2019-12-31", "50": "2021-01-31", "75": "2022-01-31", "90": "2025-09-30"}. Missingness is preserved, not filled.

## 9. Ragged-edge analysis

At 2026-10-31, 0 of 28 predictors are usable. Missing: industrial_production, manufacturing, mining, electricity_gas, construction, retail_trade, wholesale_trade, cpi_headline, cpi_food, cpi_services, ppi, exports_total, exports_non_gold, imports_total, gold_exports_proxy, usd_uzs, rub_uzs, gold_price, russia_ipi, m2, household_deposits, corporate_deposits, household_credit, corporate_credit, fx_reserves_ex_gold, pos_turnover, instant_payments, interbank_payments.

## 10. Structural breaks

Registry-caveat screening identifies: cpi_headline, cpi_food, cpi_services, ppi, usd_uzs, rub_uzs, russia_ipi, instant_payments.

## 11. Outlier summary

All quality flags remain in processed data. Existing industrial-production outliers are unchanged; no outlier was removed. See `metadata/industrial_production_outliers.parquet` and the per-variable warning column above.

## 12. Revision behavior

5 revision records are stored in `metadata/revisions.parquet`. Parser/schema changes are classified separately by the revision utility.

## 13. Release-date availability

| variable_key | classification | source_release_dates_observed |
| --- | --- | --- |
| gdp_real_yoy | current release/update timestamp only | 102 |
| industrial_production | current release/update timestamp only | 274 |
| manufacturing | current release/update timestamp only | 183 |
| mining | current release/update timestamp only | 183 |
| electricity_gas | current release/update timestamp only | 183 |
| construction | current release/update timestamp only | 136 |
| retail_trade | current release/update timestamp only | 160 |
| wholesale_trade | current release/update timestamp only | 160 |
| cpi_headline | current release/update timestamp only | 136 |
| cpi_food | current release/update timestamp only | 136 |
| cpi_services | current release/update timestamp only | 136 |
| ppi | current release/update timestamp only | 328 |
| exports_total | current release/update timestamp only | 136 |
| exports_non_gold | current release/update timestamp only | 136 |
| imports_total | current release/update timestamp only | 136 |
| gold_exports_proxy | current release/update timestamp only | 136 |
| usd_uzs | retrieval timestamp only | 0 |
| rub_uzs | retrieval timestamp only | 0 |
| gold_price | current release/update timestamp only | 1600 |
| russia_ipi | no reliable historical release timing | 0 |
| m2 | current release/update timestamp only | 328 |
| household_deposits | archive-date proxy available | 56 |
| corporate_deposits | archive-date proxy available | 56 |
| household_credit | archive-date proxy available | 56 |
| corporate_credit | archive-date proxy available | 56 |
| fx_reserves_ex_gold | current release/update timestamp only | 328 |
| pos_turnover | archive-date proxy available | 116 |
| instant_payments | archive-date proxy available | 78 |
| interbank_payments | archive-date proxy available | 62 |

## 14. Master dataset dimensions

`v1_monthly`: 802 rows × 29 columns. `v1_observations_long`: 13359 rows × 20 columns. GDP is separate in `gdp_quarterly`.

## 15. Source discrepancies

12 confirmed discrepancies are listed in `docs/phase2c_registry_recommendations.md`; none silently changed V1.1.

## 16. Registry recommendations

See `docs/phase2c_registry_recommendations.md`. Changes require explicit approval for a later registry version.

## 17. Unresolved risks

{
  "russia_ipi": "SSLError: HTTPSConnectionPool(host='rosstat.gov.ru', port=443): Max retries exceeded with url: /enterprise_industrial (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)')))"
}

Historical release timing is incomplete for current-snapshot sources. Archive dates are not treated as fabricated first-release dates. External-source TLS/schema availability remains an operational risk.

## 18. Recommended Phase 3 steps

Approve or reject the Phase 2C registry recommendations; schedule periodic source/replay checks; accumulate genuine vintages and release histories; and define pseudo-real-time information-set tests. Forecasting should begin only after those governance decisions.
