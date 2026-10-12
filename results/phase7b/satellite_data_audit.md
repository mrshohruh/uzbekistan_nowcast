# Satellite data audit

SOURCE_METADATA_UNVERIFIED; historical satellite vintages unverified. CSV supplied by colleague; no substitute downloaded.

Coverage contract: True. 152 chronological months, 2014-01–2026-08. Nonmissing counts: {'radiance': 152, 'NDVI': 152, 'EVI': 152, 'NO2': 99}. NO2 begins 2018-06; earlier missing values remain null. Numeric parsing rejects malformed cells and infinities; duplicate months fail. Range investigation flags: 0. NDVI/EVI working screening interval [-1,1] is provisional until products and units are confirmed. NO2 units remain unknown; no unsupported physical upper bound imposed.

NDVI/EVI correlation: 0.976620, computed on aligned nonmissing months. EVI is tested separately.

Radiance jumps flagged using a descriptive six-MAD threshold: 1. These full-sample audit thresholds are never used for model fitting. Values are retained. Annual means around 2016–2017: {2015: 0.31342742116666666, 2016: 0.27995969625, 2017: 0.4894820243333333, 2018: 0.4278454015}. Changes can reflect processing, cloud/snow contamination or economic activity; no causal or sensor-change claim is established. Review flagged months against product documentation.

Monthly climatology and annual means describe seasonality/trends in satellite_seasonality.csv and satellite_annual_means.csv; seasonal patterns must not be interpreted as GDP changes. Correlation matrix, descriptive statistics and all observation-level flags are preserved. Sensor processing discontinuities cannot be verified without product versions.

Needed from colleague: sensor/product identifiers and versions, units/scales, polygon and geographic weighting, cloud/snow masks and quality filters, compositing and aggregation code, calibration changes (particularly 2016–2017), extraction date, original source links, revision history and historical first-publication dates.

Additional diagnostics: satellite_trend_diagnostics.csv records per-month linear trend slopes, time correlations and calendar-month mean ranges in unverified original measurement units. satellite_break_diagnostics.csv records changes in annual means without declaring sensor breaks. Radiance mean rises approximately 74.84% from 2016 to 2017; that discontinuity requires product and processing verification. No observations were corrected or deleted.
