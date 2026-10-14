"""Factor-number diagnostics, finite-sample caveats and an offline dashboard."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scripts.phase7f.protection import OUT,ROOT
from scripts.phase7f.panels import MAIN
from scripts.operations.prospective.common import safe


def table(frame,cols):
    def cell(value):
        if isinstance(value,(float,np.floating)):
            if not np.isfinite(value):return 'unavailable'
            return str(int(value)) if value==int(value) else f'{value:.5f}'
        return str(value).replace('|','/').replace('\n',' ')
    return '| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+'\n'.join('| '+' | '.join(cell(v) for v in r)+' |' for r in frame[cols].itertuples(index=False,name=None))+'\n'


def report(summary,curves,spectrum,loads,variables,context):
    primary=summary.loc[summary['sample'].eq('ORIGINAL_COMPLETE')]
    columns=['model','declared_variables','n_variables','n_months','sample_start','sample_end','current_factors','k_max','ICp1','ICp2','ICp3','ER','methods_disagree','hits_search_boundary']
    caps=pd.read_csv(OUT/'phase7f_kmax_sensitivity.csv',float_precision='round_trip')
    methodology='''# Phase 7F methodology

Research-only static factor-number diagnostics. No data download, nowcast update, dynamic factor re-estimation, bridge fitting, RMSE selection or promotion occurs. Production stays COMBO_50_50 = 8.180901340616275% for cumulative real YTD GDP YoY in 2026Q3. Corresponding runs use cutoff 2026-10-05 and estimator training ending 2026-06-30; current-quarter filtering/forecast months are excluded from formal selection.

## Exact inspected implementations

Production uses scripts/production/models.py and src/uznowcast/models/dfm.py: eight fixed columns, one contemporaneous latent factor with AR(2) dynamics, statsmodels DynamicFactorMQ EM maximum likelihood, no idiosyncratic AR(1), filtered states, GDP bridge B with quarterly mean factor and GDP lag. Its 'balanced' flag trims to the latest first observation but still allows interior and trailing missing cells. The original estimator training is 90 months; POS is absent from January 2025 onward. Read the saved transformed historical_panel.csv, apply the unchanged mask/training_panel/standardize functions, and verify its dimensions against the frozen fit. No dynamic estimator is rerun.

Production industrial production is the approved real growth index minus 100, not Phase 7E's nominal flow; PPI is monthly log inflation; USD/UZS and RUB/UZS are normalized monthly-mean log changes; gold is a monthly log price change; M2 and reserves excluding gold are stock log YoY changes; POS is de-cumulated monthly-flow log YoY. Original transformation definitions and bases are exported verbatim.

Phase 7E reads the immutable Phase 7D workbook, verifies its checksum and reuses read_workbook, release_gate and standardize. It transforms nominal YTD production/trade/construction/turnover into monthly flows before log YoY; price indices into monthly log inflation; services indices minus 100; monetary stocks into log YoY; reserves/gold into log monthly changes; rates remain levels. All 91 original monthly columns and five quarterly covariates retain their existing dictionary. No quarterly variable is made into artificial monthly observations. Predictor vintages and individual release dates remain unverified, with the same assumed lag gates.

E1 imposes one separate factor per F1–F4 block. E2 imposes one per F1–F5. E4 has exactly the same monthly measurement panel as E2; its five quarterly covariates affect only the GDP bridge. The 17-variable core also imposes five separate economic factors. These grouped models are not pooled unrestricted DFMs: the E1–E4/core main diagnostic rows test their pooled monthly static span, not the optimum number of separate economic channels. Current counts are documented architecture counts, not assumed statistically selected counts.

E3 first estimates the five block signals, then a single global PCA/AR(2)/Kalman factor from them. It projects blocks on the global signal and uses GLOBAL plus F1–F4 residuals in the bridge; F5 is the reference. Report the pooled 91-variable span AND E3_STAGE2 (five first-stage block signals) AND E3_BRIDGE (global plus four residual signals). Stage rows use existing saved current-origin one-sided factor paths through June 2026; they contain generated regressors, including model estimates for missing measurements. Their selectors are heuristic diagnostics of an estimated signal covariance, not independently observed-series tests, not formally identified hierarchical likelihood tests, and not new causal shocks. No forecasted target-quarter state enters.

## Standardization and balancing

Primary normalization uses each model's existing origin training mean and sample standard deviation (ddof=1). Phase 7E family precision weights are reconstructed exactly within each block: sqrt(N_block/(number_of_families*family_size)); core weights use its own families. Pooled rows retain these within-block weights but do not impose equal total cross-block precision. The stage inputs retain their existing training-standardized scale. Within the chosen complete observed rows, all diagnostic columns are demeaned again as balanced PCA requires zero sample means. This final centering is diagnostic-only; no production standardization is changed. Thus balanced covariances can have different variances from an origin-wide unit-variance panel.

ORIGINAL_COMPLETE: retain all declared columns and only rows with every transformed input genuinely present. Dates may have gaps; gap counts are reported. The cross-sectional static covariance does not require consecutive dates; missingness-related selection, seasonal representation and serial-dependence concerns remain. Constants on an exact balanced window have no covariance information and are explicitly excluded, with effective N updated. Every original variable and month has an audit row, including unavailable samples. No missing value is filled with zero, a mean, a latent reconstruction or interpolation.

COMMON_STRICT: intersection of complete monthly dates across production and E1–E4/core, retaining all their columns. This yields only nine months, below the predeclared minimum 12, so formal recommendations are unavailable. COMMON_CALENDAR_SUBSET: the continuous shared-history calendar (2024 January–December), dropping any variable incomplete within it and any constant. It has identical calendar dates across panels but different explicitly documented columns; it is a weak 12-month sensitivity, not a full-coverage matched test.

LONG_HISTORY_RECTANGLE: choose a fully observed contiguous rectangle with T>=36, N>=2 by maximizing T*N using only the missingness mask. Tie-break by N, T, then earliest start. This drops short/gapped variables openly; it tests a reduced specification, not the full original model. Services have no 36-month history and this variant is unavailable. UNWEIGHTED_ORIGINAL removes only diagnostic measurement weights. BALANCED_RESTANDARDIZED reuses the existing normalization function on the retained observed window, then applies the original weights. These separate sensitivities expose scaling/coverage dependence without overwriting original definitions.

## Published selectors and numerical rules

For centered finite X of dimension T by N, compute unregularized SVD. Eigenvalues lambda_j = s_j²/T, ordered decreasing. PCA rank-k residual V(k) = sum_{j>k} lambda_j / N = SSE/(N*T). Residual degrees of freedom must not replace N*T. Normalized static scores satisfy F'F/T=I; signed loadings equal sqrt(lambda_j) times covariance eigenvectors, with the largest absolute loading oriented positive. Also export loadings divided by original measurement weight, in origin-standardized predictor units. These diagnostic PCA loadings are not the existing dynamic model's coefficients or official GDP contributions.

ICp1(k) = log V(k) + k * (N+T)/(N*T) * log(N*T/(N+T))
ICp2(k) = log V(k) + k * (N+T)/(N*T) * log(min(N,T))
ICp3(k) = log V(k) + k * log(min(N,T))/min(N,T)

Each criterion minimizes over k=0,...,Kmax with the actual retained N,T. ER(k) = lambda_k/lambda_(k+1), maximized over positive k=1,...,Kmax. It cannot select zero here; a positive ER result cannot rule out zero factors. There are no p-values or conventional significance cutoffs. Exact ties favor the smallest count.

Main Kmax = min(10, floor(min(N,T)/2), numerical_rank-1), reserving a substantial residual dimension. Numerical rank uses tolerance max(lambda_1*1e-10,1e-12). Exclude numerical-null denominators and saturated residuals; fail visibly when rank<2 rather than reporting fake positive factors. Predeclared stress searches use requested caps 5/10/15, clipped to min(N,T)-2 and rank-1. A recommendation at the search ceiling is censored evidence, not proof that the ceiling is optimal. For three-variable core blocks the main/stress search contains only k=1 among positive choices: ER=1 is mechanical, not evidence against a second factor. All panels have at least one small dimension below 60; asymptotic consistency is not established for these finite, correlated and often short panels.

Static covariance rank/common components differ from the number of primitive dynamic shocks, dynamic state dimensions, autoregressive lag states and economically imposed blocks. No selector in this phase estimates the number of dynamic shocks. A common static dimension below the block count can suggest redundant global co-movement, while larger counts can reflect within-block heterogeneity, idiosyncratic dependence or over-selection. It cannot alone prove redundant economic channels or causal shocks.

Formulas are verified against [Bai and Ng (2002), equation 9](https://www.columbia.edu/~sn2294/pub/ecta02.pdf). The ordered adjacent-eigenvalue selector is [Ahn and Horenstein (2013)](https://onlinelibrary.wiley.com/doi/10.3982/ECTA8968). These are static selection procedures; neither is a GDP forecast-accuracy rule.
'''
    methodology=methodology.replace('clipped to min(N,T)-2 and rank-1.',
        'clipped to max(1,min(N,T)-2) and rank-1. The two-variable exception retains its sole valid positive candidate; it supplies no meaningful choice among multiple positive counts.')
    (OUT/'phase7f_methodology.md').write_text(methodology,encoding='utf8')
    results='# Phase 7F — optimal DFM factor-number selection\n\nResearch diagnostics completed without changing production. **COMBO_50_50 remains 8.180901340616275% for 2026Q3.** All counts below select static covariance components on balanced subpanels; they are not automatically dynamic DFM shocks, state dimensions or economic block counts.\n\n'
    results+='## Primary full-variable balanced panels\n\n'+table(primary,columns)
    results+='\nAll main recommendations retain original variables, subject to an explicitly recorded constant-column exclusion where necessary. Rows lost to missingness are listed individually. Production has 72 jointly observed months (2019–2024), versus its 90-month missing-data estimator sample; full Phase 7E pools have only 24 jointly complete months, mostly 2024–2026. These different samples do not support a clean cross-model causal ranking.\n\n'
    results+='## Common-calendar and longer-history sensitivity\n\n'+table(summary.loc[summary.model.isin(MAIN) & summary['sample'].isin(['COMMON_STRICT','COMMON_CALENDAR_SUBSET','LONG_HISTORY_RECTANGLE','UNWEIGHTED_ORIGINAL','BALANCED_RESTANDARDIZED'])],['model','sample','n_variables','n_months','sample_start','sample_end','ICp1','ICp2','ICp3','ER','status','failure'])
    results+='\nThe strict common full-coverage sample has nine months and is unavailable under the fixed 12-month minimum. The 12-month common-calendar sensitivity excludes incomplete/constant columns explicitly. Long-history rectangles omit short-history indicators and are reduced specifications. Neither sensitivity is silently treated as the original model.\n\n'
    results+='## Search-cap sensitivity on primary panels\n\n'+table(caps.loc[caps['sample'].eq('ORIGINAL_COMPLETE')],['model','requested_cap','k_max','ICp1','ICp2','ICp3','ER','hits_search_boundary'])
    production=primary.loc[primary.model.eq('PRODUCTION_DFM')].iloc[0]
    results+=f'\n## Interpretation and future evaluation\n\n1. **Production one-factor support:** in its original eight-variable balanced panel, ICp1/ICp2/ICp3/ER recommend {int(production.ICp1)}/{int(production.ICp2)}/{int(production.ICp3)}/{int(production.ER)} respectively. One static component is not selected on that sample. All reach the main ceiling {int(production.k_max)}, so the exact optimal count is unresolved; stress searches and reduced-variable samples must be read alongside it. N=8 is small, and static evidence does not establish a replacement dynamic architecture or better GDP forecasts.\n\n'
    results+='2. **Five Phase 7E economic factors:** no consensus validates exactly five independent static factors. The full E2/E3/E4 monthly pools give IC recommendations 10/6/10 versus ER=2 on 24 complete months, with two criteria at the ceiling. E4 repeats E2 because quarterly bridge variables do not change the monthly measurement panel. E3 stage diagnostics separately examine its global and residual structure; generated-regressor results cannot prove a fully identified hierarchy.\n\n'
    results+='3. **Groups needing further investigation:** industrial activity has ICp1/ICp2=5/4 while ER=1; prices/monetary conditions have ICp1/ICp2=3/3 while ER=1; services IC criteria reach seven while ER=1. Domestic demand and external conditions give IC=2 versus ER=1. These conflicts motivate multi-factor or sub-family sensitivities, not definitive claims that every group requires the largest count. ICp3 is especially ceiling-sensitive here.\n\n'
    results+='4. **Possible redundancy:** low ER counts in pooled panels and in the five generated block signals suggest a small number of dominant shared directions. High IC counts simultaneously suggest remaining heterogeneous covariance or finite-sample over-selection. Economic blocks need not represent statistically independent common factors. Neither result justifies deleting channels or describing redundant causal shocks.\n\n'
    results+='5. **Structures deserving future evaluation:** predeclare alternative static/dynamic dimensions rather than taking an RMSE winner: a two-direction pooled Phase 7E diagnostic motivated by ER, moderate within-industry and within-price sub-family structures motivated by ICp1/ICp2, and production multi-factor sensitivity informed by its full scree/cap results. Revisit short-history services after more observations and test E3 common/residual dependence. Compare interpretation, identification, genuine release availability and prospective forecasting performance in a separately authorized phase. Keep all disagreements and upper-bound hits visible.\n\n'
    results+='6. **Core:** 17-variable core ICp1/ICp2/ICp3/ER=8/6/8/6 in 28 complete months. Narrower labels do not establish a uniquely five-factor static structure. Core block ER counts of one can be mechanical when only one positive candidate is admissible.\n\n'
    results+='## Reproduction — Windows CMD\n\n```cmd\ncd /d C:\\Users\\Sh.Nishonqulov\\Desktop\\uzbekistan_nowcast_codex_starter\n.venv\\Scripts\\python.exe -B -m scripts.phase7f.run\n.venv\\Scripts\\python.exe -B -m scripts.phase7f.validate\nstart "" "results\\phase7f\\phase7f_factor_selection_dashboard.html"\n```\n\nThe methodology, candidate curves, eigenvalues/ratios, loadings, input panels, variable/month exclusion audits and cap sensitivity are stored alongside this report. Actual executed tests, browser checks, determinism and before/after file hashes are recorded in phase7f_validation.json.\n'
    (OUT/'phase7f_results.md').write_text(results,encoding='utf8')
    payload=dict(summary=summary.to_dict('records'),criteria=curves.to_dict('records'),spectrum=spectrum.to_dict('records'),
        loadings=loads[['model','sample','original_variable','factor','loading','loading_standardized_input','eigenvector']].to_dict('records'),
        variables=variables[['model','sample','original_variable','balance_status','frequency','transformation','observations_original','missing_in_retained_window','formal_scale','formal_weight']].to_dict('records'),caps=caps.to_dict('records'),context=context,
        methodology=methodology,models=summary.model.drop_duplicates().tolist(),samples=summary['sample'].drop_duplicates().tolist(),
        main=MAIN,groups=['GROUP_F1','GROUP_F2','GROUP_F3','GROUP_F4','GROUP_F5'])
    html=Path(__file__).with_name('dashboard.html').read_text(encoding='utf8')
    data=json.dumps(safe(payload),allow_nan=False,separators=(',',':')).replace('</','<\\/')
    (OUT/'phase7f_factor_selection_dashboard.html').write_text(html.replace('__DATA__',data),encoding='utf8',newline='\n')
