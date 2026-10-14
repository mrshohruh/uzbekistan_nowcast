"""Evidence-led research reporting and offline dashboard payload."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scripts.phase7e.grouping import BLOCKS, RATIONALE
from scripts.operations.prospective.common import safe


def md_table(frame,columns=None):
    f=frame if columns is None else frame[columns]
    def cell(x):
        if isinstance(x,(float,np.floating)): return f'{x:.6f}' if np.isfinite(x) else 'unavailable'
        return str(x).replace('|','/').replace('\n',' ')
    return '| '+' | '.join(f.columns)+' |\n| '+' | '.join(['---']*len(f.columns))+' |\n'+'\n'.join('| '+' | '.join(cell(x) for x in row)+' |' for row in f.itertuples(index=False,name=None))+'\n'


def report(inputs,grouping,scores,horizons,forecasts,factors,loads,contributions,diagnostics,earliest,robust,nowcast,out):
    # Propagate first-stage measurement loadings through E3's explicit projection.
    # These are composed approximate loadings, not a jointly estimated MLE.
    projection=pd.read_csv(out/'phase7e_hierarchical_projection.csv',float_precision='round_trip')
    loads=loads.copy()
    if 'loading_stage' in loads: loads=loads.loc[loads.loading_stage.eq('FIRST_STAGE_BLOCK_MEASUREMENT')].copy()
    loads['loading_stage']='FIRST_STAGE_BLOCK_MEASUREMENT'
    extra=[]
    for keys,part in loads.loc[loads.model.eq('E3')].groupby(['origin','target_quarter','horizon']):
        hp=projection.loc[projection.origin.eq(keys[0]) & projection.target_quarter.eq(keys[1]) & projection.horizon.eq(keys[2])].set_index('block')
        for row in part.to_dict('records'):
            p=hp.loc[row['economic_group']]
            extra.append(dict(row,factor='GLOBAL',loading=row['loading']*p.global_loading,anchor=False,
                loading_stage='TWO_STAGE_COMPOSED_GLOBAL_APPROXIMATION'))
            if p.residual_in_bridge:
                extra.append(dict(row,factor=row['economic_group']+'_RESIDUAL',loading=row['loading']*p.residual_scale,
                    loading_stage='TWO_STAGE_COMPOSED_RESIDUAL_APPROXIMATION'))
    derived=pd.DataFrame(extra)
    for _,part in derived.groupby(['model','origin','target_quarter','horizon','factor']):
        energy=part.loading.pow(2)
        derived.loc[part.index,'loading_energy_share']=energy/energy.sum()
    loads=pd.concat([loads,derived],ignore_index=True)
    loads.to_csv(out/'phase7e_factor_loadings.csv',index=False,float_format='%.17g')
    current=forecasts.loc[forecasts.evaluation_group.eq('CURRENT')]
    current_loads=loads.loc[loads.evaluation_group.eq('CURRENT')]
    current_diag=diagnostics.loc[diagnostics.evaluation_group.eq('CURRENT') & diagnostics.model.eq('FULL_BLOCKS')]
    stability=[]
    for (model,factor),part in loads.groupby(['model','factor']):
        pairs=[];previous=None
        for origin,block in part.sort_values('origin').groupby('origin',sort=True):
            v=block.set_index('original_label').loading.dropna()
            if previous is not None:
                matched=v.to_frame('new').join(previous.rename('old')).dropna()
                if len(matched)>2:
                    pairs.append(dict(model=model,factor=factor,origin=origin,matched_variables=len(matched),
                        loading_correlation=float(matched.new.corr(matched.old)),
                        sign_agreement=float((np.sign(matched.new)==np.sign(matched.old)).mean())))
            previous=v
        stability.extend(pairs)
    stable=pd.DataFrame(stability)
    stable.to_csv(out/'phase7e_loading_stability.csv',index=False,float_format='%.17g')
    descriptions=[]
    for row in current_diag.itertuples():
        l=current_loads.loc[current_loads.model.eq('E2') & current_loads.factor.eq(row.factor)].dropna(subset=['loading'])
        strongest=l.sort_values('loading',ascending=False)
        b=row.economic_group
        coherence='Broad nominal activity co-movement; cannot infer real output or sector GDP shares.' if b=='F1' else (
            'Short 2024-onward services history limits stability and development evaluation.' if b=='F2' else (
            'Demand proxies combine construction/trade with provisional enterprise definitions.' if b=='F3' else (
            'External/valuation signal combines trade flows and reserve stocks; not real net exports.' if b=='F4' else
            'Mixed liquidity/price/rate co-movement; not a coherent unified inflation or monetary-conditions factor.')))
        energy=l.groupby('family').loading_energy_share.sum().sort_values(ascending=False)
        dominant=energy.index[0];share=float(energy.iloc[0])
        assessment=coherence+f' Largest loading-energy family: {dominant} ({share:.1%}); positive loading share {row.positive_loading_share:.1%}.'
        descriptions.append(dict(factor=b,definition=RATIONALE[b],coherence_assessment=assessment,
            strongest_positive='; '.join(strongest.head(3).original_label),
            strongest_negative='; '.join(strongest.loc[strongest.loading.lt(0)].tail(3).original_label),
            dominance_family=dominant,dominance_share=share))
    desc=pd.DataFrame(descriptions)
    desc.to_csv(out/'phase7e_factor_interpretation.csv',index=False)
    # Interpretability review after estimation: no penalty/coefficient tuning.
    nowcast['economically_preferred_research_model']='E1'
    nowcast['predeclared_full_coverage_research_candidate']='E2'
    nowcast['research_preference_basis']='Economic interpretability review: full F5 is money-dominated with heterogeneous price/rate loadings; prefer the simpler four-channel explanation. Not an accuracy superiority claim.'
    (out/'phase7e_current_nowcast.json').write_text(json.dumps(safe(nowcast),indent=2,allow_nan=False)+'\n',encoding='utf8')
    scorecard=[]
    for model in ['E1','E2','E3','E4','ECONOMIC_CORE']:
        d=scores.loc[scores.model.eq(model) & scores['sample'].eq('MATCHED_DEVELOPMENT')].iloc[0]
        h=scores.loc[scores.model.eq(model) & scores['sample'].eq('MATCHED_HOLDOUT')].iloc[0]
        scorecard.append(dict(model=model,economic_coherence=(
            'Four activity/external channels; financing intentionally excluded' if model=='E1' else
            'Global plus four orthogonal block residuals; F5 reference, two-stage approximation' if model=='E3' else
            'Five channels plus five separate quarterly covariates' if model=='E4' else
            '17 exact economic-core indicators; clearer labels, smaller coverage' if model=='ECONOMIC_CORE' else
            'Five predeclared channels, all 91 monthly variables; price/finance interpretation conditional'),
            development_rmse=d.rmse,holdout_rmse=h.rmse,holdout_quarters=h.n_quarters,
            implementation_reliability='Converged current factors; unverified source/release vintage; services short-history restriction',
            assessment=('ECONOMICALLY_CLEARER_RESEARCH_EXPLANATION; no promotion' if model=='E1' else
                        'FULL_COVERAGE_RESEARCH_CANDIDATE; mixed F5 interpretation; no promotion' if model=='E2' else
                        'RESEARCH_ONLY_NO_PROMOTION; prospective vintage validation required')))
    scorecard=pd.DataFrame(scorecard);scorecard.to_csv(out/'phase7e_evaluation_scorecard.csv',index=False)
    rationale='''# Economic grouping rationale — Phase 7E

Every original predictor is inventoried once: 91 monthly observations assigned to exactly one F1–F5 block and five quarterly covariates in Q_BRIDGE. Original workbook labels, transformations, units, coverage, assumed lag and uncertainty are retained. No source registry or production transformation is changed.

Industrial production aggregates and detailed sectors overlap. Fixed label-based families (aggregate / broad sectors / manufacturing detail) receive equal squared measurement weight; every indicator remains represented. This reduces category multiplicity, but correlated measurement errors and overlap remain. GDP bridge contributions are never sector GDP accounting contributions.

All rendered market services stay in F2, including Trade: its reported service activity concept differs from trade turnover in F3. Transport/motor transport form a shared family. Enterprise counts stay in F3 as provisional business-activity proxies; the small-business cumulative interpretation requires source-owner verification. Construction and wholesale are not final expenditure.

USD gold price and foreign-currency/gold reserves join F4: external assets and valuation conditions, rather than industrial gold output or domestic liquidity. Exports/imports are nominal USD values despite workbook labels “volume”. No FX variable exists in this workbook; none is invented. CPI transport/financial/services categories are prices and therefore stay in F5, not services activity. CPI and PPI, money and rates form distinct equal-weight families. A single F5 factor is assessed empirically, never presumed an economically homogeneous monetary shock.

Quarterly investment growth, wages, FDI-financed investment, population income and secondary income credits retain Phase 7D definitions. Secondary income credits are not independently verified migrant remittances. All five enter E4 as q-1 released values or training-only released-history AR(1) projections, never actual target-quarter values.

The economic core selects __CORE_COUNT__ exact workbook series by predeclared conceptual label matching: 3 industry, 4 services, 3 demand, 3 external and 4 prices/financing. Quarterly covariates remain separately documented candidates and enter E4, not the monthly-only core diagnostic. All non-core variables retain full-block membership with explicit exclusion reasons.

No research deflator is introduced: the input archive lacks sufficiently verified price/concept matching to justify it. Nominal activity is clearly labeled, not re-described as real output. Zero prices, negative flows, missing cells and retained descriptive outliers are preserved in the copied Phase 7D transformation audit.
'''
    # Keep the count tied to the dictionary rather than prose bookkeeping.
    ncore=int(grouping.economic_core_selected.sum())
    rationale=rationale.replace('__CORE_COUNT__',str(ncore))
    (out/'economic_grouping_rationale.md').write_text(rationale,encoding='utf8')
    methodology='''# Phase 7E methodology

Research only. Operational production remains COMBO_50_50 = 8.180901340616275%. Target is official cumulative year-to-date real GDP YoY percent, index minus 100, concordant with the existing quarterly master. It is not standalone-quarter growth and is never interpolated to months.

## Predeclared rules and information boundaries

Use only the immutable SHA256-selected Phase 7D workbook. Apply its causal transformations and assumed lags without changing data, sources or registry. Inventory retains all 91 monthly and five quarterly explanatory columns. Original release dates and retrieval vintages are unavailable. All workbook historical research is PSEUDO_REAL_TIME_NOT_VINTAGE_VERIFIED: assumed reference-end lags gate latest-revised data, not authentic historical releases. GDP uses the existing STRICT vintage events, with target-quarter GDP excluded. Evaluation actuals are latest-revised cumulative-YTD workbook/master GDP, distinct from frozen first-release production evaluations.

H1/H2/H3 remain the first/second/third target-quarter month ends. Current research uses 2026-10-05, the sealed production calendar cutoff after H3; workbook vintage equivalence is unverified. Origins are investigated from 2019Q2 onward; 2019 data alone do not permit bridge estimation.

Each variable needs >=12 genuinely observed training months and nonconstant variance; each block needs >=two such indicators and >=12 months with two observed indicators. This increases Phase 7D's six-observation variable threshold for block identification. A factor is null before its first co-observed measurement month; services therefore stay null before 2024. No earlier factor or predictor history is manufactured. Every bridge requires >=12 released GDP training rows and >=four real quarterly factor signals for each included factor. Neutral ridge priors with separate missing indicators handle earlier missing block regressors, not fabricated observations. This is an explicitly reduced-history, unbalanced bridge; coefficients for services use only its actual available history. Failed earlier origins and per-variable coverage remain in audit outputs.

## Separate measurement factors

Within each block, standardize by training mean and sample standard deviation through the quarter preceding the target, using only origin-visible observations. Estimate rank-one missing-data PCA with fixed nuclear penalty 2, tolerance 1e-6, maximum 1000 iterations; fail on nonconvergence or nonmonotone objective. Factor scale is normalized on training filtered states. Fixed label families balance precision with mean squared weight one: weight sqrt(N / (number_of_families * family_size)). This necessary deviation from Phase 7D controls duplicated industrial/price categories while retaining all variables. The idiosyncratic variance floor remains .15 / weight².

Stable ridge AR(2) dynamics use Phase 7D's penalty 1, innovation variance floor .01 and spectral radius <.98, shrinking unstable coefficients by .95. Kalman measurement updates are strictly one-sided; no RTS smoother is used. Missing target-month measurements trigger state prediction. Monthly factor signals are averaged into quarterly regressors, requiring at least two nonnull latent monthly states. Historical trajectories are re-estimated at each forecast origin and must not be treated as immutable factor vintages.

Signs use predeclared positive anchors: manufacturing (fallback aggregate industry), transport services (fallback ICT), retail (fallback wholesale), exports (fallback gold price), headline CPI (fallback composite PPI). Fallbacks use origin-identifiable indicators only. Loadings are in standardized predictor units per one training-standardized filtered factor unit. Factors are co-movement indicators, not causally identified shocks. Loading stability compares consecutive origins on common observed indicator loadings.

## Specifications and bridge

E1 includes F1–F4; F5 excluded by design. E2 includes F1–F5, all 91 monthly indicators subject to identification. E4 adds all five separate quarterly predictors. ECONOMIC_CORE is a predeclared 17-column diagnostic, not a holdout-selected contestant, and does not include quarterly information.

E3 is a statistically explicit two-stage hierarchical approximation, not a jointly identified hierarchical state-space MLE. First extract a global common factor from the five one-sided block signals with missing-data PCA/AR(2)/Kalman filtering. Orient it to F1. Regress each block signal on an intercept and this global signal using only joint observed training rows. Block residuals are orthogonal to the global signal on their training support (verified covariance tolerance 1e-8). Use GLOBAL and F1–F4 residuals in the bridge; F5 is the predeclared reference block, preventing a redundant full set of global/block regressors. F5-specific residual information is omitted from this approximation. Residuals combine dynamic filtered signals, not separately identified orthogonal innovations; cross-block residual dependence remains. Global measurement loadings are block-level; the original variable loadings shown for E3 are its first-stage measurement audit, and projection coefficients are separately exported. No causal or full-MLE claim is made.

GDP(q) = intercept + sum(beta_b * standardized_quarterly_factor_b(q)) + gamma * standardized_available_GDP_lag(q) + released_quarterly_covariates + missing_indicators + error.

The GDP lag is the latest actually released GDP quarter strictly before the row's target, not automatically q-1. Training-row lags use their own H1/H2/H3 origin GDP vintages, while dependent training GDP is the origin's released vintage. Quarterly covariates use q-1 only and their row's simulated release gate: released q-1, or stable released-history AR(1) projected to q-1; absent history gives a neutral standardized prior and missing indicator. No actual target-quarter covariate enters. All bridge means/scales and coefficients use expanding training rows only. Coefficient ridge penalty 10, missing indicator penalty 20, unpenalized intercept; >=four nonmissing rows identify a covariate. Penalties and rules are fixed before evaluation, never tuned on holdout. Decomposition exports every standardized-regressor coefficient product, intercept and missing term and must reconstruct the prediction within 1e-10 GDP pp.

## Evaluation and limitations

Main tables use the intersection of successful origins for E1/E2/E3/E4/core and six legacy comparators. Per-model own-success samples are exported separately, never pooled as fair comparisons. Legacy matching-origin Phase 7D archives use the identical input hash and GDP definition; six frozen procedures are rerun read-only at 2026Q2 H3 to verify reproduction. No scientific archive is overwritten. The earlier experimental schedule has no new successful pre-legacy origins because services starts in 2024; failures explain why.

Holdout remains 2025Q3–2026Q2 and was already examined by previous phases. Bias is actual minus prediction: negative bias means overprediction. R²_OS uses matched AR1 squared errors. Quarter-cluster bootstrap resamples quarterly mean loss differences, retaining H1/H2/H3 dependence. Only four holdout quarter clusters imply highly limited uncertainty resolution. Horizon revisions, +15-day lag and training-only 1st/99th percentile winsorization are fixed sensitivity checks. No model is automatically promoted. Economic interpretation, performance and reliability are reviewed in an evidence-based scorecard without arbitrary composite weights. No final-holdout model choice is made; E2 remains the conditional primary research candidate.

The two-step PCA/Kalman approach follows the general estimator idea described by [Doz, Giannone and Reichlin](https://www.sciencedirect.com/science/article/pii/S030440761100039X). Arbitrary missing-data state-space maximum likelihood is a different method described by [Bańbura and Modugno, ECB WP 1189](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1189.pdf); this implementation does not claim to implement their EM-MLE. Their theory does not establish finite-sample consistency for these small block panels.

Source-definition uncertainty, nominal versus real activity mismatch, short services history, category redundancy, seasonal patterns, gold valuation and unverified releases remain material. Prospective source/vintage validation is necessary before any promotion review.
'''
    methodology += '\nEconomic preference review: E1 offers the clearer four-channel economic explanation because the estimated full F5 is M2-dominated with heterogeneous price/rate loadings. E2 remains the predeclared full-coverage candidate. This interpretability judgment does not use holdout RMSE to tune, select or promote a forecast. E3 exports both first-stage measurement loadings and their composed global/residual equivalents, labeled as a two-stage approximation; F5-specific residual measurement variation remains omitted from its bridge.\n'
    (out/'phase7e_methodology.md').write_text(methodology,encoding='utf8')
    interpretation='# Phase 7E economic interpretation\n\nFactors measure statistical co-movement. Bridge coefficient products are predictive GDP attribution in percentage points; they are not causal effects, structural multipliers, official sector shares or national-accounting contributions. The intercept and persistence term explain much of the forecast level; centered factor terms explain deviations relative to their bridge training means.\n\n'
    for item in descriptions:
        b=item['factor'];l=current_loads.loc[current_loads.model.eq('E2') & current_loads.factor.eq(b)]
        series=factors.loc[factors.model.eq('E2') & factors.evaluation_group.eq('CURRENT') & factors.factor.eq(b)]
        latest=series.dropna(subset=['value']).iloc[-1]
        diagnostic=current_diag.loc[current_diag.factor.eq(b)].iloc[0]
        interpretation+=f"## {b}: {BLOCKS[b]}\n\n{item['definition']} {item['coherence_assessment']}\n\nCurrent September signal: {latest.value:.6f} training standard deviations (filtered/predicted state, not necessarily observed activity). AR(2) coefficients: {diagnostic.ar1:.6f}, {diagnostic.ar2:.6f}; spectral radius {diagnostic.spectral_radius:.6f}. Observed training-cell share {diagnostic.observed_share:.1%}; effective loading count {diagnostic.effective_loading_count:.3f}.\n\nStrongest positive loadings: {item['strongest_positive']}. Strongest negative loadings: {item['strongest_negative'] or 'none'}.\n\n"
        interpretation+=md_table(l.sort_values('loading',ascending=False),['original_label','loading','loading_energy_share','family'])+'\n'
    c=contributions.loc[contributions.evaluation_group.eq('CURRENT')]
    interpretation+='## Current forecast attribution\n\n'+md_table(c.loc[c.value.abs().gt(1e-12)],['model','component','value'])
    core_diag=diagnostics.loc[diagnostics.evaluation_group.eq('CURRENT') & diagnostics.model.eq('CORE_BLOCKS')]
    interpretation+='\n## Core interpretation sensitivity\n\nThe core improves clarity by removing aggregate/component overlaps and enterprise/reserve ambiguity. It does not prove stronger latent economic coherence or forecasting performance. The same short services history and nominal/real caveat apply. Compare diagnostic evidence below; the core is never selected after reviewing holdout.\n\n'+md_table(pd.concat([current_diag,core_diag]),['model','factor','mean_pairwise_correlation','positive_loading_share','effective_loading_count','observed_share'])
    full_price=float(c.loc[c.model.eq('E2') & c.component.eq('F5'),'value'].iloc[0])
    core_price=float(c.loc[c.model.eq('ECONOMIC_CORE') & c.component.eq('F5'),'value'].iloc[0])
    interpretation+=f'\nThe price/financing contribution changes from {full_price:+.6f} pp in full E2 to {core_price:+.6f} pp in the core. This sign reversal is a material sensitivity to the measurement composition, not an identified change in a causal monetary effect. Simpler indicator labels alone do not resolve F5 coherence.\n'
    (out/'phase7e_economic_interpretation.md').write_text(interpretation,encoding='utf8')
    results='# Phase 7E results — research only\n\nOPERATIONAL_PRODUCTION_MODEL = COMBO_50_50; frozen forecast **8.180901340616275%** unchanged. ECONOMICALLY_PREFERRED_RESEARCH_MODEL = **E1 for the clearer four-channel economic explanation**. E2 remains the predeclared full-coverage research candidate. The estimated full F5 is M2-dominated with heterogeneous price/rate loadings; this economic interpretation review is not holdout-RMSE selection or permission to promote a forecast.\n\n'
    results+='Implemented E1, E2, E3 two-stage hierarchical approximation, E4 and the 17-variable economic core. All 91 monthly variables are assigned exactly once (F1=29, F2=14, F3=5, F4=5, F5=38), plus five separately inventoried quarterly predictors. Five base factors are successfully estimated at the current cutoff.\n\n'
    results+='## Current 2026Q3 cumulative real YTD GDP YoY\n\n'+md_table(current,['model','prediction','failure'])
    results+='\nResearch cutoff: 2026-10-05. September source observations are heavily incomplete. Factors extrapolate unavailable months with stable dynamics. Input release vintages are unverified; this is not a sealed production information-set reproduction.\n\n'
    results+='## Identical-origin performance\n\n'+md_table(scores,['sample','model','rmse','mae','bias','median_absolute_error','max_absolute_error','r2','r2_os_ar1','n_forecasts','n_quarters'])
    results+='\nBias is actual minus prediction. All main models use common successful origins. Latest-revised GDP scoring differs from the frozen first-release production evaluation; frozen original production holdout RMSE remains 0.5825277229410664 pp. No superiority claim is justified by four holdout quarters.\n\n'
    dev=scores.loc[scores['sample'].eq('MATCHED_DEVELOPMENT')]
    results+=f"The common development sample has only {int(dev.n_quarters.max())} distinct quarters and {int(dev.n_forecasts.max())} horizon forecasts per model. The services-start restriction sharply reduces comparison history; development scores are diagnostic and do not support tuning or definitive model ranking.\n\n"
    results+='## Historical availability\n\nEarliest workbook GDP: '+str(inputs.gdp.first_valid_index())+'.\n\n'+md_table(earliest)
    results+='\nEarlier failures, including nonidentifiable services before 2024/2025, remain in forecast/block-failure files. The extended schedule investigates 2019Q2 onward, but does not create valid 2019 forecasts. Earlier bridge regressors retain null short-history factors with missing indicators; this reduced-history bridge is explicitly labeled.\n\n'
    results+='## Economic and operational assessment\n\n'+md_table(scorecard)+'\n'+md_table(desc,['factor','coherence_assessment'])
    results+='\nNo challenger merits operational promotion now. E2/E4 merit future research review after verified releases, more services history and prospective validation; this is not permission to replace production. Core selection improves label transparency, not established forecast superiority. The full contribution arithmetic, factor stability, missingness and quarter-cluster evidence are in the accompanying CSVs.\n\n'
    results+='## Reproduction (Windows CMD)\n\n```cmd\ncd /d C:\\Users\\Sh.Nishonqulov\\Desktop\\uzbekistan_nowcast_codex_starter\n.venv\\Scripts\\python.exe -B -m scripts.phase7e.run\n.venv\\Scripts\\python.exe -B -m scripts.phase7e.validate\nstart "" "results\\phase7e\\phase7e_economic_dfm_dashboard.html"\n```\n\nValidation status and actual executed test/browser/reproducibility results are recorded by the validate command in phase7e_validation.json.\n'
    (out/'phase7e_results.md').write_text(results,encoding='utf8')
    # Payload excludes origin inventory's repeated noncurrent rows to keep HTML responsive.
    av=pd.read_csv(out/'phase7e_origin_availability.csv',float_precision='round_trip')
    root=Path(__file__).resolve().parents[2]
    frozen=json.loads((root/'results/current/current_nowcast.json').read_text())
    prior=json.loads((root/'results/phase7d/phase7d_current_nowcast.json').read_text())
    benchmarks=[dict(model='COMBO_50_50',prediction=frozen['final_forecast'],information_set='SEALED_PRODUCTION'),
        dict(model='M0',prediction=frozen['dfm_forecast'],information_set='SEALED_PRODUCTION'),
        dict(model='U0',prediction=frozen['umidas_forecast'],information_set='SEALED_PRODUCTION')]
    benchmarks.extend(dict(model=r['model'],prediction=r['prediction'],information_set='PHASE7D_WORKBOOK_PSEUDO_REAL_TIME') for r in prior['all_models'] if r['model']=='DFM_ALL_GROUPED')
    payload=dict(models=current.model.tolist(),comparators=sorted(forecasts.model.unique()),nowcast=nowcast,
        benchmark_nowcasts=benchmarks,
        inventory=grouping.to_dict('records'),metrics=scores.to_dict('records'),horizons=horizons.to_dict('records'),
        forecasts=forecasts.to_dict('records'),factors=factors.loc[factors.evaluation_group.eq('CURRENT')].to_dict('records'),
        loadings=current_loads.to_dict('records'),contributions=c.to_dict('records'),diagnostics=pd.concat([current_diag,core_diag]).to_dict('records'),
        stability=stable.to_dict('records'),interpretations=descriptions,scorecard=scorecard.to_dict('records'),
        availability=av.loc[av.evaluation_group.eq('CURRENT')].to_dict('records'),
        earliest=earliest.to_dict('records'),robustness=robust.to_dict('records'),
        methodology=methodology,block_names=BLOCKS)
    template=Path(__file__).with_name('dashboard.html').read_text(encoding='utf8')
    serialized=json.dumps(safe(payload),allow_nan=False,separators=(',',':')).replace('</','<\\/')
    (out/'phase7e_economic_dfm_dashboard.html').write_text(template.replace('__DATA__',serialized),encoding='utf8')
