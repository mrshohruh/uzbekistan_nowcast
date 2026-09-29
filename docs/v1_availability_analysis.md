# V1 availability and ragged-edge analysis

| Variable | First raw observation | First usable transformed observation | Last observation | Frequency | Missing periods | Current status | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Real GDP growth (quarterly) | 2018-03-31 | 2018-03-31 | 2026-06-30 | Quarterly | 0 | automated |  |
| Industrial production | 2019-01-31 | 2020-01-31 | 2026-07-31 | Monthly | 0 | automated | extreme_log_change; missing_growth_input |
| Manufacturing output | 2019-01-31 | 2020-01-31 | 2026-07-31 | Monthly | 0 | automated | extreme_log_change; missing_growth_input |
| Mining and quarrying output | 2019-01-31 | 2020-01-31 | 2026-07-31 | Monthly | 0 | automated | extreme_log_change; missing_growth_input |
| Electricity, gas, steam and air-conditioning supply | 2019-01-31 | 2020-01-31 | 2026-07-31 | Monthly | 0 | automated | extreme_log_change; extreme_monthly_increment; missing_growth_input |
| Construction works | 2021-01-31 | 2022-01-31 | 2026-08-31 | Monthly | 0 | automated | extreme_log_change; extreme_monthly_increment; missing_growth_input |
| Retail trade turnover | 2020-01-31 | 2021-01-31 | 2026-08-31 | Monthly | 0 | automated | extreme_log_change; extreme_monthly_increment; missing_growth_input |
| Wholesale trade turnover | 2020-01-31 | 2021-01-31 | 2026-08-31 | Monthly | 0 | automated | extreme_log_change; extreme_monthly_increment; missing_growth_input; nonpositive_growth_input; nonpositive_monthly_flow |
| Headline CPI | 2021-01-31 | 2021-01-31 | 2026-08-31 | Monthly | 0 | automated |  |
| Food CPI | 2021-01-31 | 2021-01-31 | 2026-08-31 | Monthly | 0 | automated |  |
| Services CPI | 2021-01-31 | 2021-01-31 | 2026-08-31 | Monthly | 0 | automated |  |
| Producer Price Index | 2013-01-31 | 2013-01-31 | 2026-08-31 | Monthly | 0 | automated |  |
| Total exports | 2021-01-31 | 2022-01-31 | 2026-08-31 | Monthly | 0 | automated | extreme_log_change; missing_growth_input |
| Non-gold exports (derived) | 2021-01-31 | 2022-01-31 | 2026-08-31 | Monthly | 0 | automated | extreme_log_change; extreme_monthly_increment; missing_growth_input; nonpositive_monthly_flow |
| Total imports | 2021-01-31 | 2022-01-31 | 2026-08-31 | Monthly | 0 | automated | extreme_log_change; missing_growth_input |
| Gold / precious-metals export proxy | 2021-01-31 | 2021-01-31 | 2026-08-31 | Monthly | 0 | automated | extreme_monthly_increment; nonpositive_monthly_flow |
| USD/UZS official exchange rate | 2013-01-31 | 2013-02-28 | 2026-09-30 | Daily | 0 | automated | extreme_log_change; missing_growth_input; partial_month |
| RUB/UZS official exchange rate | 2013-01-31 | 2013-02-28 | 2026-09-30 | Daily | 0 | automated | extreme_log_change; missing_growth_input; partial_month |
| World gold price | 1960-01-31 | 1960-02-29 | 2026-08-31 | Monthly | 0 | automated | missing_growth_input |
| Russia industrial production index |  |  |  | Monthly | 0 | unresolved | ValueError: Offline cache missing: https://rosstat.gov.ru/enterprise_industrial |
| Broad money (M2 / broad money liabilities) | 2013-01-31 | 2014-01-31 | 2026-08-31 | Monthly | 0 | automated | missing_growth_input |
| Household deposits | 2022-07-31 | 2023-07-31 | 2026-06-30 | Monthly | 20 | automated | missing_growth_input |
| Corporate/legal-entity deposits | 2022-07-31 | 2023-07-31 | 2026-06-30 | Monthly | 20 | automated | missing_growth_input |
| Household/individual credit | 2022-07-31 | 2023-07-31 | 2026-06-30 | Monthly | 20 | automated | missing_growth_input |
| Corporate/legal-entity credit | 2022-07-31 | 2023-07-31 | 2026-06-30 | Monthly | 20 | automated | missing_growth_input |
| Foreign-currency reserves excluding monetary gold | 2013-01-31 | 2014-01-31 | 2026-08-31 | Monthly | 0 | automated | missing_growth_input |
| POS-terminal payment turnover | 2018-12-31 | 2020-01-31 | 2026-06-30 | Monthly archive / current JSON snapshot | 33 | automated | extreme_log_change; missing_growth_input; missing_previous_month; nonpositive_monthly_flow |
| Central Bank instant/fast payment-system turnover | 2021-01-31 | 2022-01-31 | 2026-06-30 | Monthly | 27 | automated | extreme_log_change; missing_growth_input |
| Interbank Payment System turnover | 2018-12-31 | 2019-12-31 | 2025-11-30 | Monthly | 53 | automated | extreme_log_change; missing_growth_input |

## Coverage thresholds

| Predictor share | First month |
| --- | --- |
| 25% | 2019-12-31 |
| 50% | 2021-01-31 |
| 75% | 2022-01-31 |
| 90% | 2025-09-30 |

## Predictors available by calendar year

| year | peak_predictors | predictors_at_year_end_or_latest |
| --- | --- | --- |
| 1960 | 1 | 1 |
| 1961 | 1 | 1 |
| 1962 | 1 | 1 |
| 1963 | 1 | 1 |
| 1964 | 1 | 1 |
| 1965 | 1 | 1 |
| 1966 | 1 | 1 |
| 1967 | 1 | 1 |
| 1968 | 1 | 1 |
| 1969 | 1 | 1 |
| 1970 | 1 | 1 |
| 1971 | 1 | 1 |
| 1972 | 1 | 1 |
| 1973 | 1 | 1 |
| 1974 | 1 | 1 |
| 1975 | 1 | 1 |
| 1976 | 1 | 1 |
| 1977 | 1 | 1 |
| 1978 | 1 | 1 |
| 1979 | 1 | 1 |
| 1980 | 1 | 1 |
| 1981 | 1 | 1 |
| 1982 | 1 | 1 |
| 1983 | 1 | 1 |
| 1984 | 1 | 1 |
| 1985 | 1 | 1 |
| 1986 | 1 | 1 |
| 1987 | 1 | 1 |
| 1988 | 1 | 1 |
| 1989 | 1 | 1 |
| 1990 | 1 | 1 |
| 1991 | 1 | 1 |
| 1992 | 1 | 1 |
| 1993 | 1 | 1 |
| 1994 | 1 | 1 |
| 1995 | 1 | 1 |
| 1996 | 1 | 1 |
| 1997 | 1 | 1 |
| 1998 | 1 | 1 |
| 1999 | 1 | 1 |
| 2000 | 1 | 1 |
| 2001 | 1 | 1 |
| 2002 | 1 | 1 |
| 2003 | 1 | 1 |
| 2004 | 1 | 1 |
| 2005 | 1 | 1 |
| 2006 | 1 | 1 |
| 2007 | 1 | 1 |
| 2008 | 1 | 1 |
| 2009 | 1 | 1 |
| 2010 | 1 | 1 |
| 2011 | 1 | 1 |
| 2012 | 1 | 1 |
| 2013 | 4 | 4 |
| 2014 | 6 | 6 |
| 2015 | 6 | 6 |
| 2016 | 6 | 6 |
| 2017 | 6 | 6 |
| 2018 | 6 | 6 |
| 2019 | 7 | 7 |
| 2020 | 12 | 11 |
| 2021 | 17 | 17 |
| 2022 | 22 | 20 |
| 2023 | 24 | 20 |
| 2024 | 24 | 20 |
| 2025 | 26 | 21 |
| 2026 | 26 | 0 |

## Latest-month ragged edge

Latest union month: 2026-09-30. 0 of 28 predictors have usable transformed values.

Available: .

Missing: industrial_production, manufacturing, mining, electricity_gas, construction, retail_trade, wholesale_trade, cpi_headline, cpi_food, cpi_services, ppi, exports_total, exports_non_gold, imports_total, gold_exports_proxy, usd_uzs, rub_uzs, gold_price, russia_ipi, m2, household_deposits, corporate_deposits, household_credit, corporate_credit, fx_reserves_ex_gold, pos_turnover, instant_payments, interbank_payments.

Unusually short histories (<36 raw observations): russia_ipi, household_deposits, corporate_deposits, household_credit, corporate_credit, interbank_payments.
