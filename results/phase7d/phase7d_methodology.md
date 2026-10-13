# Phase 7D methodology

This research does not alter the frozen COMBO_50_50 model, weights, forecasts,
registry, masters or prior scientific artifacts. Every original predictor label
is retained. The content-addressed workbook under input/ preserves raw bytes;
raw sheet CSVs and cell-level transformations preserve original values.

## GDP and transformations

GDP is the quarterly **official cumulative YTD real YoY growth** target, not
standalone-quarter growth. Subtract 100 from the published volume index;
all 30 workbook target values agree with the official repository master.
GDP is never a monthly predictor, interpolated or de-cumulated as a ratio.
The official definition is corroborated by the [national GDP release](https://stat.uz/img/press-relizlar/analitics-of-gdp_eng_p72885.pdf).

Monthly nominal industrial output, construction, retail, wholesale, USD trade
and provisionally newly created small-business counts are YTD flows. January is
the raw value; other months subtract the immediately previous calendar month
within the same year. Missing predecessors stay missing. Then calculate
100 ln(flow_t/flow_t-12), only for positive operands. These nominal series do
not become real industrial volume measures merely through de-cumulation.

CPI and PPI are previous-month=100: use 100 ln(index/100), never log differences
of these reported ratios as if they were price levels. The misleading CPI
"Cumulative" label is contradicted by monthly patterns and official 2021 values:
January 101.00, February 100.64, March 100.84. See the [official CPI report](https://stat.uz/images/uploads/reliz2021/press-reliz-narx_31_03_2023_eng.pdf)
and [SIAT PPI 1581](https://siat.stat.uz/data/1581/?lang=en).
Zero PPI indices are preserved as raw zero and marked invalid; their log
transformation is null. Existing services YoY indices and fixed-investment
growth indices subtract 100; growth ratios cannot be de-cumulated.

M2 and operating-entity stocks use log YoY growth. Gold and foreign-currency /
gold reserve stocks use monthly log changes. Reserve swings remain visible.
Interest rates stay in annual percentage rate levels, subsequently standardized.
Quarter-specific secondary income credits and published nominal wage averages
use log YoY growth. Secondary income credits are not an exact remittance
measure. Wage averages are never de-cumulated. Nominal FDI investment and
population income are interpreted as YTD flows, de-cumulated quarterly before
log YoY growth. Some definitions are inferred from labels and resets; neither
units nor original source/vintage metadata are independently verified for
each uploaded column. The enterprise interpretation is explicitly provisional.

The transformation audit contains every predictor-period, including nulls,
raw values, intermediate flows, clean values, source cells and quality flags.
Outlier counts and annual-mean shifts are full-sample descriptive audits only;
they never determine production transforms or forecast-origin scaling.

## Estimator and identification

D1, D2 and D3 are one-, two-, and three-common-factor two-step monthly DFMs.
D4 uses two group-balanced common factors, not a claimed independently fitted
hierarchical model. Monthly groups are industry, domestic demand, consumer
prices, producer prices, external trade, services, enterprises and financial.
Quarterly groups also cover wages, household income and investment.
Every group and column remains represented in the main experiment.

At each origin fit missing-data PCA on the expanding monthly panel ending
before the target quarter. For a rank-k matrix F L', minimize observed weighted
squared reconstruction error plus twice a fixed nuclear-norm penalty (lambda=2)
on the rank-k reconstruction. Missing cells initialize at the standardized
neutral prior and alternate between the preceding regularized rank-k
reconstruction and the rank-k SVD of the completed matrix with singular values
shrunk by 2. Original observed cells are fixed. Penalizing the reconstructed
matrix bounds weakly identified missing-history blocks. This generalized
missing-data PCA has nonincreasing penalized objective; stopping uses relative
penalized-objective improvement <1e-6 after 20 iterations
or relative completion change <1e-6, with a 1,000 iteration cap. Report the
convergence flag and objective, including any capped approximate solutions.
Missing internal reconstructions are latent estimates, never saved as source
observations. No global interpolation, backwards fill of observed inputs or
full-sample factor estimate is used.

For D4 give each active group equal total squared weight: w_j=1/sqrt(N_group).
This weights PCA and inflates the Kalman measurement variance by N_group;
large industrial/price groups cannot gain precision simply through membership
count. D1-D3 use w_j=1. Measurement errors are diagonal with an estimated
training residual variance floored at 0.15 standardized squared units, limiting
near-duplicate variables' precision. Remaining correlated measurement errors
are a model limitation; group energy shares reveal domination.

Fit each factor's AR(2) by ridge OLS (penalty 1). If companion eigenvalues exceed
0.98, repeatedly multiply both AR coefficients by 0.95 and record stabilization.
Estimate innovation variance from training residuals. Apply the Gaussian
Kalman filter to released observed cells with the fitted loading matrix and
diagonal noise; missing measurements cause state prediction without an update.
Predict remaining target-quarter months with the transition equation. Only
one-sided filtered factors feed the bridge. Scale factors by their training
filtered mean and standard deviation; orient each so its largest absolute
training loading is positive. Factors can rotate across fits: numbered factors
are within-fit signals, not stable structural shocks.

This is a two-step PCA / Kalman estimator, **not** full dynamic EM maximum
likelihood and not identical to the production statsmodels EM estimator.
The two-step design is motivated by [Doz, Giannone and Reichlin](https://cepr.org/publications/dp6043)
and the [ECB factor-model paper](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp674.pdf).
Missing-data completion is an implementation extension with reported finite
sample approximation limitations; no asymptotic guarantee is asserted here.

Columns with fewer than six observed training values or constant training
variance remain in the inventory and each origin's audit, with unavailable
loadings and an explicit NOT_IDENTIFIABLE status. They enter automatically
when training observations permit. Late services do not truncate other series
to 2024. No high-correlation screening is used.

## Mixed-frequency GDP bridge

The quarterly target uses the mean of three monthly filtered/projected factors,
lagged released GDP, and all five quarterly explanatory covariates. Avoid an
unrestricted 96-variable quarterly GDP regression. The bridge has ridge
penalty 10 for standardized slopes, 20 for covariate missingness indicators,
and an unpenalized intercept. Fixed penalties are declared in advance and never
tuned to the holdout. Quarterly covariate scaling uses bridge training rows
only, at least four nonmissing rows, with a neutral standardized Gaussian
prior and explicit missing indicator for unavailable values.

For each target q the quarterly design requests q-1, release-gated at the
original H1/H2/H3 origin for that training row. Use a realized q-1 only if
available. Otherwise project q-1 using an adjacent-pair AR(1) fitted solely to
earlier released history, shrinking its coefficient and documenting the
projection; short histories remain unavailable. Target-quarter realized
quarterly predictors never enter. The origin audit identifies every released,
projected, or unidentifiable quarterly bridge value and coefficient.
No quarterly predictor is repeated across unreleased monthly observations.

## Historical information and comparisons

Preserve repository horizons: H1, H2, H3 are month-end 1, 2, 3 of the target
quarter. Expanding-window origins follow the existing historical schedule.
GDP training uses the repository's strict, documented historical GDP vintage
kernel, publication before the origin, and strictly earlier target quarters.
Experimental GDP bridge starts at the workbook's 2019 target coverage.
Legacy kernels retain their original training histories, transformation,
factor/lag specifications and GDP boundary; they are rerun read-only at each
exact same forecast origin. Score **all** predictions against the workbook's
latest-revised cumulative real YTD GDP, explicitly different from original
frozen first-release metrics. Report frozen production metrics separately.
Legacy predictor inputs differ from the new workbook because model designs
are preserved; comparison measures their implemented forecast procedures,
not the isolated effect of predictor count alone.

Monthly / quarterly availability is reference-period end plus the documented
assumed calendar-day lag in the dictionary. Monthly lags: activity, trade,
services, entities and rates 30 days; CPI 5; PPI 20; M2 25; reserves 15; gold 0.
Quarterly lags: credits 90; wages 30; investment and population income 45.
These are research **assumptions**, not invented provider release dates.
Current workbook cells and historical predictor revisions cannot be vintage
verified. Label results PSEUDO_REAL_TIME_NOT_VINTAGE_VERIFIED. Do not infer
actual releases from typical lags. Current cutoff can match production's date
without matching its sealed economic information set.

The main leaderboard is the strict intersection of successful forecasts for
all nine specifications. Verify origin, quarter, horizon and actual value
equality. DEVELOPMENT ends 2025Q2, HOLDOUT is 2025Q3-2026Q2. Select the DFM
specification with lowest development RMSE only. Factor-count comparison uses
identical origins. Failures and origins outside this intersection remain in
forecasts and failure audit; do not hide them.

## Metrics, uncertainty and robustness

Errors are actual minus predicted, in GDP percentage points. Report RMSE, MAE,
mean error, median/max absolute error, sample R2=1-SSE/SST, out-of-sample
R2=1-SSE_model/SSE_AR1 and versus an expanding released historical mean,
RMSE improvement versus each model, forecasts, distinct quarters, dates and
H1/H2/H3 scores. R2 is null when sample is too small or denominator zero;
negative R2 means worse squared error than its stated mean/benchmark,
not negative explanatory power. The mean benchmark uses training information,
whereas conventional evaluation R2 centers on the evaluation actual mean.

Use quarter-cluster resampling of mean squared-error gain, keeping H1/H2/H3
together (4,000 deterministic draws). With only four holdout quarter clusters,
these intervals are descriptive, not reliable evidence of superiority.
Quarter-mean errors provide lag-1/lag-2 autocorrelation and early/recent bias.
Past-error bands use the 90th absolute-error quantile from at least eight
previous distinct quarters at the same horizon; later errors never calibrate
earlier bands. Coverage is descriptive, not a nominal guarantee.
Current +/-1.96 holdout RMSE is only a historical-error reference band,
not a calibrated 95% prediction interval.

Robustness re-estimates one-factor and grouped DFMs on the same origin schedule
with training-only 1/99% winsorization, exclusion of services, exclusion of
2020/2021 training factor and GDP observations, +15-day lags, and each group
ablation. Main all-variable results remain intact. Variant failures, changed
predictor counts and the exact paired evaluation counts are reported. Compare
balanced/unbalanced factors and inspect group loading-energy domination.
Loading times standardized observation is a measurement signal in standardized
units, not an additive GDP contribution or causal effect.

Phase 7D is retrospective research. The historical holdout has already been
examined in earlier repository research; it is not an untouched prospective
experiment. Do not auto-promote. KEEP_PRODUCTION remains the operational
decision until source definitions, vintages and prospective results support a
separate promotion review.
