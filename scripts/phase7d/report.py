"""Offline HTML with embedded result data; no services, CDN or build tool."""
import json
from pathlib import Path
import pandas as pd
from scripts.operations.prospective.common import safe


METHODOLOGY = """# Phase 7D methodology

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
"""


def report(inputs,metrics,horizons,forecasts,signals,loadings,contributions,availability,robustness,nowcast,manifest,frozen,out: Path):
    forecasts=forecasts.copy()
    forecasts['error']=forecasts.actual-forecasts.prediction
    forecasts['absolute_error']=forecasts.error.abs()
    forecasts.to_csv(out/'phase7d_forecasts.csv',index=False,float_format='%.17g')
    availability=availability.copy()
    availability['frequency']=availability.original_label.map(inputs.inventory.set_index('original_label').frequency)
    availability.to_csv(out/'phase7d_origin_availability.csv',index=False,float_format='%.17g')
    (out/'phase7d_methodology.md').write_text(METHODOLOGY,encoding='utf8')
    primary=metrics.loc[metrics['sample'].eq('MATCHED_ALL')]
    hold=metrics.loc[metrics['sample'].eq('MATCHED_HOLDOUT')]
    fields=['model','rmse','bias','mae','r2','r2_os_ar1','n_forecasts','n_quarters','evaluation_start','evaluation_end']
    def markdown(f):
        def value(v):return '—' if pd.isna(v) else f'{v:.6f}' if isinstance(v,float) else str(v)
        return '| '+' | '.join(f.columns)+' |\n| '+' | '.join(['---']*len(f.columns))+' |\n'+'\n'.join('| '+' | '.join(value(v) for v in row)+' |' for row in f.itertuples(index=False,name=None))
    selected=nowcast['model']
    chosen=hold.loc[hold.model.eq(selected)].iloc[0];production=hold.loc[hold.model.eq('COMBO_50_50')].iloc[0]
    improvement=100*(1-chosen.rmse/production.rmse) if production.rmse>0 else None
    text=f"""# Phase 7D results — KEEP_PRODUCTION

Audited **91 monthly + 5 quarterly = 96 predictors** and one separate quarterly
GDP target. D1/D2/D3/D4 retain all 96 declared predictors. All 96 are estimable
at the current origin; short histories are explicitly unidentifiable at earlier
origins, then enter without truncating older series. GDP never enters the
monthly predictor panel. See origin_availability for each column at each origin.

All 30 GDP values exactly match the repository's official cumulative YTD
target after index minus 100. Source column definitions are otherwise partly
inferred from labels and patterns. Zero PPI indices are raw preserved / clean
null; reserve swings and genuine structural gaps remain visible.

## Exact matched latest-revised-target evaluation

{markdown(primary[fields])}

These metrics are newly recalculated on common origins and latest-revised GDP,
not the frozen production metrics. All legacy kernels were rerun read-only.
Forecast counts include overlapping H1/H2/H3; distinct quarters are shown.
Failures and all generated forecasts remain in the CSVs.

## Final holdout, excluded from model selection

{markdown(hold[fields])}

Selected experiment: **{selected}**, {nowcast['factor_count']} common factors,
chosen using development RMSE through 2025Q2. Holdout RMSE change versus matched
production is {improvement:.3f}% improvement (a negative value means worse).
This short retrospective sample cannot establish genuine statistical superiority.
Decision: **KEEP_PRODUCTION**, no automatic promotion.

## Experimental current target

2026Q3 experimental cumulative real YTD GDP YoY: **{nowcast['prediction']:.8f}%**.
Calendar cutoff: **{nowcast['cutoff']}**, H3 after quarter-end.
Source missing September predictors: {nowcast['missing_september_source_count']};
missing after release assumptions / transforms:
{nowcast['missing_september_after_release_and_transform_count']}.
Current release/vintage class: **{nowcast['information_class']}**.
Cutoff matches the production calendar date but lacks workbook release and
retrieval evidence; it does not reproduce the sealed legacy information set.
Indicative historical-error reference band:
{nowcast['historical_error_reference_lower']:.4f}% to
{nowcast['historical_error_reference_upper']:.4f}% — not a calibrated interval.

Frozen production remains **COMBO_50_50 = 8.180901340616275%**.
Original frozen metrics are in phase7d_frozen_production_metrics.csv and the
dashboard's separate historical-reference section. Their original holdout
RMSE is 0.5825277229410664 pp; it must not be confused with re-scored values.

## Audit and limitations

Raw workbook SHA256: {manifest['workbook_sha256']}.
Immutable workbook archive: input/{manifest['workbook_sha256']}.xlsx.
Pipeline hashes {manifest['protected_file_count']} prior files and verifies
unchanged bytes at completion; the manifest records the actual verification.
No production scientific output or forecast is overwritten.

The uploaded workbook lacks individual source URLs, release calendars and
retrieval dates. CPI label discrepancy and enterprise-count semantics require
source-owner clarification. Real GDP is compared with nominal activity and
income predictors; seasonal structure, correlated idiosyncratic errors, short
quarterly histories and revisions remain limitations. The estimator is a
two-step missing-data PCA / AR(2) Kalman DFM, not full dynamic MLE.
Fixed ridge penalties and minimum-history thresholds are documented.

The dashboard embeds generated data and SVG interactions with no server or CDN.
Horizon metrics, quarter-cluster uncertainty, group ablations, outlier / lag /
pandemic sensitivities, group factor energies and prequential band coverage
are auditable in accompanying CSVs. Tests and browser checks are reported
in phase7d_validation.json and phase7d_browser_validation.json after execution.

Reproduce: `.venv\\Scripts\\python.exe -m scripts.phase7d.run`.
Run tests: `.venv\\Scripts\\python.exe -m scripts.phase7d.test_runner`.
"""
    (out/'phase7d_results.md').write_text(text,encoding='utf8')
    payload=dict(models=primary.model.tolist(),metrics=metrics.to_dict('records'),horizons=horizons.to_dict('records'),
        forecasts=forecasts.to_dict('records'),signals=signals.loc[signals.evaluation_group.eq('CURRENT')].to_dict('records'),
        loadings=loadings.loc[loadings.evaluation_group.eq('CURRENT')].to_dict('records'),
        contributions=contributions.loc[contributions.date.ge('2026-07-01')].to_dict('records'),inventory=inputs.inventory.to_dict('records'),
        transformations=inputs.transformations.to_dict('records'),availability=availability.loc[availability.evaluation_group.eq('CURRENT')].to_dict('records'),
        robustness=robustness.to_dict('records'),nowcast=nowcast,manifest=manifest,
        frozen=frozen.to_dict('records'),audit=inputs.audit,methodology=METHODOLOGY)
    # Avoid circular HTML / manifest checksum claims inside the HTML itself.
    payload['manifest']={k:v for k,v in manifest.items() if k not in ('output_sha256','code_sha256')}
    encoded=json.dumps(safe(payload),ensure_ascii=False,allow_nan=False).replace('</','<\\/')
    template=(Path(__file__).parent/'dashboard.html').read_text(encoding='utf8')
    (out/'phase7d_dfm_dashboard.html').write_text(template.replace('__PAYLOAD__',encoded),encoding='utf8')
