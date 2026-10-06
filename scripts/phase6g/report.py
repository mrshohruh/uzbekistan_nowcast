"""Explain strict-common-origin ensemble evidence and remaining vintage limits."""
import numpy as np
import pandas as pd
import re
from scripts.phase6g import analysis as a


def write_report(out,tables,current,recommendation,diagnostics):
    metrics=tables['horizon_metrics']
    common=tables['model_comparison'].loc[lambda f:f['sample'].eq('EXTENDED_COMMON')].set_index('model')
    hold=tables['model_comparison'].loc[lambda f:f['sample'].eq('ORIGINAL_HOLDOUT_COMMON')].set_index('model')
    elig=tables['origin_eligibility'];valid=elig.loc[elig.common_origin_eligible]
    err=tables['origin_level_errors'];extended=err.loc[err['sample'].eq('EXTENDED_COMMON')]
    revisions=tables['revision_stability'];corr=tables['error_correlations']
    wins=tables['win_rates'];loo=tables['leave_one_quarter_out']
    lines=['# Phase 6G — M2-L2 DFM ensemble promotion test','',
        'Phase 6E production is unchanged. The primary challenger is G2 = 50% M2-L2 DFM + 50% unchanged U-MIDAS; no FDI is read or fitted.',
        'The evaluation is **availability-aware pseudo-real-time**, not fully vintage-real-time. Reference-period/publication timing is masked and tested. Historical predictor revision-value leakage remains unresolved because M2 and other predictor value vintages are incomplete. All numerical conclusions below carry that limitation.',
        '## Reproduction and historical extension','',
        'The first stage refits Phase 6E DFM, U-MIDAS and COMBO_50_50 and Phase 6F M2-L1/L2 at each of the twelve frozen holdout origins and at the archived current cutoff. All 65 required reconstruction checks must pass absolute tolerance 1e-7 before extension or promotion conclusions are permitted. Reproduction failures stop the experiment.',
        f'The extended strict-common sample contains {int(common.loc["P0","N"])} origins across {valid.target_quarter.nunique()} realized quarters, beginning {valid.target_quarter.min()} and ending {valid.target_quarter.max()}. The unchanged original holdout contains {int(hold.loc["P0","N"])} origins across four quarters. {len(elig)-len(valid)} candidate origins were excluded; their exact missing-history, convergence or GDP-evidence reasons are in phase6g_origin_eligibility.csv.',
        'Earlier origins were attempted using the existing verified first-release GDP registry, publication-vintage accessor and frozen minimum-history rules. No earlier target is scored with revised GDP as a substitute for an unresolved first release. DFM needs at least 36 training months, the GDP bridge needs its frozen minimum quarters and released GDP(q−1), and U-MIDAS needs at least 15 usable training rows. Nonconverged or unstable DFM fits remain unavailable. All seven models must succeed at an origin for the main common comparison.',
        'The earlier extension overlaps the repository’s model development period. It is retrospective robustness evidence for an already chosen specification, not an independent holdout or a new prospective validation sample. Original holdout and earlier-development metrics are reported separately. Full-available scores are also reported; benchmark-relative metrics always pair identical origins. No unequal-sample RMSE difference is used for promotion.',
        '## Fixed model design','',
        'S0/S1/S2 retain the eight Phase 6E predictors: industrial production, PPI, USD/UZS, RUB/UZS, world gold, M2, reserves excluding gold and scope-limited POS. M2 transformation remains 100 ln(level_t/level_t−12). The 25-day registry publication gate is applied to the source series before assigning its transformed value to a month one/two months later. Thus an economic L2 means the factor cell at month t contains the observed transformed M2 value from t−2. This exactly reproduces Phase 6F rather than reversing the shift.',
        'One EM-MLE DynamicFactorMQ factor, AR(2), filtered states, no idiosyncratic AR(1), training-only standardization, balanced start and the original intercept + mean-quarter factor + GDP(q−1) bridge remain unchanged. Future within-quarter latent factor states are forecasts, not future observed monthly data. Factor dimensionality and monthly parameter count do not increase; lagging M2 can shorten the balanced training window and is explicitly documented in the convergence table.',
        '## Ensemble performance','',
        '| Sample | Model | N | H1 RMSE | H2 RMSE | H3 RMSE | Pooled RMSE | MAE | Bias |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for sample in ['ORIGINAL_HOLDOUT_COMMON','EXTENDED_COMMON','EARLIER_DEVELOPMENT_COMMON']:
        g=tables['model_comparison'].loc[lambda f:f['sample'].eq(sample)]
        for model in ['P0','G1','G2','S0','S1','S2','U0']:
            if model not in g.model.to_list():continue
            r=g.loc[g.model.eq(model)].iloc[0]
            lines.append(f'| {sample} | {model} | {r.N} | {r.H1_RMSE:.6f} | {r.H2_RMSE:.6f} | {r.H3_RMSE:.6f} | {r.pooled_RMSE:.6f} | {r.pooled_MAE:.6f} | {r.bias:.6f} |')
    lines+=['','Bias is actual minus forecast. Positive OOS R² = improvement, negative = worse: 1 − SSE_challenger/SSE_benchmark. G1/G2 use P0; standalone S1/S2 use S0. Correlation with actual GDP, median and maximum absolute errors, SSE and mean absolute revision appear in the horizon metrics. GDP remains the published cumulative YTD real YoY convention; it is not monthly interpolated.', '']
    lines.append(f'The extension tests the fragility of the Phase 6F result: standalone S2 RMSE changes from {hold.loc["S2","pooled_RMSE"]:.6f} versus S0 {hold.loc["S0","pooled_RMSE"]:.6f} in the original holdout to S2 {common.loc["S2","pooled_RMSE"]:.6f} versus S0 {common.loc["S0","pooled_RMSE"]:.6f} in the extended common sample. G1’s extended pooled gain is {common.loc["P0","pooled_RMSE"]-common.loc["G1","pooled_RMSE"]:.6f} pp; assess its magnitude rather than relabelling a tiny gain as strong promotion evidence.')
    for sample,label in [('ORIGINAL_HOLDOUT_COMMON','Original holdout'),('EXTENDED_COMMON','Extended common sample')]:
        g=metrics.loc[metrics['sample'].eq(sample)].pivot(index='horizon',columns='model',values='RMSE')
        improvement=float(g.loc['POOLED','P0']-g.loc['POOLED','G2'])
        percent=100*improvement/g.loc['POOLED','P0']
        lines.append(f'{label}: G2 pooled RMSE improvement {improvement:.6f} pp ({percent:.3f}%). '+
            ('At least 0.05 pp: economically meaningful diagnostic magnitude.' if improvement>=.05 else 'At least 0.03 pp: potentially meaningful diagnostic magnitude.' if improvement>=.03 else 'Below the 0.03 pp practical threshold, or worse than P0.'))
        for h in ['H1','H2','H3']:
            delta=g.loc[h,'G2']-g.loc[h,'P0']
            lines.append(f'{label} {h}: P0 {g.loc[h,"P0"]:.6f}; G2 {g.loc[h,"G2"]:.6f}; ΔRMSE G2−P0 {delta:.6f} pp ({"improves" if delta<0 else "worsens" if delta>0 else "ties"}).')
        w=wins.loc[wins['sample'].eq(sample)&wins.model.eq('G2')&wins.horizon.eq('POOLED')].iloc[0]
        l=loo.loc[loo['sample'].eq(sample)&loo.model.eq('G2')&loo.horizon.eq('POOLED')]
        lines.append(f'{label} origin-level G2 wins: {w.wins}/{w.N} ({w.win_rate_pct:.2f}%); ties {w.ties}; worse {w.worse}. Leave-one-quarter-out improvement survives every exclusion: {bool(l.delta_RMSE.lt(0).all())}; ΔRMSE range {l.delta_RMSE.min():.6f} to {l.delta_RMSE.max():.6f}.')
        r=revisions.loc[revisions['sample'].eq(sample)].groupby('model').agg(mean_abs=('mean_abs_revision','mean'),max_abs=('max_abs_revision','max'),directionally_consistent=('directionally_consistent','mean'))
        if {'P0','G2'}.issubset(r.index):
            label_stability='more stable' if r.loc['G2','mean_abs']<r.loc['P0','mean_abs'] else 'less stable' if r.loc['G2','mean_abs']>r.loc['P0','mean_abs'] else 'equally stable'
            lines.append(f'{label} revisions: P0 mean absolute {r.loc["P0","mean_abs"]:.6f}, maximum {r.loc["P0","max_abs"]:.6f}; G2 mean absolute {r.loc["G2","mean_abs"]:.6f}, maximum {r.loc["G2","max_abs"]:.6f}. G2 is {label_stability} by mean absolute revision. Directional consistency: P0 {100*r.loc["P0","directionally_consistent"]:.1f}%, G2 {100*r.loc["G2","directionally_consistent"]:.1f}%.')
    lines+=['','Revision chronology in this repository is **H1 → H2 → H3** (first to third month). The requested H3 → H2 → H1 view is also provided with reversed signs; it is a reverse traversal of the saved forecasts, not the calendar order. Absolute revision statistics are invariant to that reversal.',
        '## Error diversification and ensemble revision identity','']
    for sample in ['ORIGINAL_HOLDOUT_COMMON','EXTENDED_COMMON']:
        g=corr.loc[corr['sample'].eq(sample)&corr.horizon.eq('POOLED')].set_index('model_a')
        if not {'S0','S2'}.issubset(g.index):continue
        rho0=g.loc['S0','error_correlation'];rho2=g.loc['S2','error_correlation']
        own=.25*(g.loc['S2','component_MSE']-g.loc['S0','component_MSE'])
        cross=.5*(g.loc['S2','mean_error_product']-g.loc['S0','mean_error_product'])
        lines.append(f'{sample} pooled error correlations with U0: S0 {rho0:.6f}, S1 {g.loc["S1","error_correlation"]:.6f}, S2 {rho2:.6f}. '+
            ('M2-L2 reduces error correlation, increasing correlation-based diversification.' if rho2<rho0 else 'M2-L2 increases error correlation, reducing correlation-based diversification.')+
            f' Exact ensemble-MSE change splits into {own:.8f} from one-quarter of the DFM mean-squared-error change and {cross:.8f} from half the change in mean DFM×U-MIDAS error product. Their sum is {own+cross:.8f}. The U-MIDAS MSE term is unchanged. This decomposition includes bias, which correlation alone does not capture.')
    lines.append(f'At every eligible origin G2−P0 = 0.5(S2−S0), checked to 1e-12. Extended common-sample ensemble revision: mean {extended.G2_minus_P0.mean():.6f}, minimum {extended.G2_minus_P0.min():.6f}, maximum {extended.G2_minus_P0.max():.6f} pp. H1/H2/H3 diversification correlations are provided separately.')
    lines+=['','## Fixed-weight robustness and statistical uncertainty','']
    weight=tables['weight_sensitivity']
    for sample in ['ORIGINAL_HOLDOUT_COMMON','EXTENDED_COMMON']:
        for r in weight.loc[weight['sample'].eq(sample)&weight.horizon.eq('POOLED')].itertuples():
            lines.append(f'{sample}, DFM/U-MIDAS {r.dfm_weight:.0%}/{r.umidas_weight:.0%}: M2-L2 ensemble RMSE {r.RMSE:.6f}; Δ versus unchanged M2 at the same weights {r.delta_vs_same_weight:.6f}; Δ versus production 50/50 {r.delta_vs_P0_50_50:.6f}.')
    lines.append('Only 25/75, 50/50 and 75/25 fixed weights were assessed. G2 remains 50/50. Comparing the changed and unchanged DFM at identical weights isolates M2 timing; comparing with P0 also changes weights. These diagnostics cannot justify weight promotion from the same sample.')
    for r in tables['statistical_diagnostics'].itertuples():
        lines.append(f'{r.sample}: exploratory 95% paired quarter-cluster bootstrap interval for RMSE(G2)−RMSE(P0): [{r.RMSE_difference_CI_lower:.6f}, {r.RMSE_difference_CI_upper:.6f}] pp from {r.n_quarters} quarter clusters. Mean paired squared-loss difference {r.paired_mean_squared_loss_difference:.8f}.')
    lines.append('Horizons within a quarter are dependent. Four original holdout clusters are too few for strong significance claims; extended development results are not independent confirmation. Bootstrap intervals are descriptive and do not resolve revision-value leakage. No unsupported Diebold–Mariano p-value is asserted.')
    lines+=['','## Convergence, complexity and factors','']
    d=pd.DataFrame(diagnostics);historical=d.loc[~d.current]
    for model,g in historical.groupby('model'):
        lines.append(f'{model}: {len(g)} successful DFM fits; EM iterations median {g.iterations.median():.1f}, max {g.iterations.max()}; training months {g.n_training_months.min()}–{g.n_training_months.max()}; monthly parameters {int(g.n_monthly_parameters.iloc[0])}, factor AR order 2. Rejected fits remain excluded in the eligibility table.')
    lines.append('The balanced monthly start moves from January 2019 for S0 to February/March 2019 for S1/S2, shortening their training windows by one/two months. S2 fails the unchanged convergence gate at 2022Q3 H1 while H2/H3 are usable; all three DFM variants reject 2022Q4’s unstable transition. These exclusions are part of the evidence against unqualified promotion, not silently relaxed tolerances. Revision summaries require all three horizons in a quarter; the partial 2022Q3 common quarter contributes to forecast metrics but not three-horizon revision summaries.')
    current_d=d.loc[d.current].set_index('model')
    loads=pd.read_csv(out/'phase6g_factor_loadings.csv')
    current_l=loads.loc[loads.current]
    for model in ['S0','S1','S2']:
        r=current_d.loc[model];m=current_l.loc[current_l.model.eq(model)&current_l.variable.eq('m2')].iloc[0]
        lines.append(f'Current {model}: factor correlation with S0 {r.factor_correlation_vs_S0:.6f}, sign alignment {r.diagnostic_alignment_sign}, factor SD {r.factor_std:.6f}, lag-1 persistence {r.factor_persistence_lag1:.6f}; factor AR coefficients ({r.factor_AR1:.6f}, {r.factor_AR2:.6f}); M2 loading {m.loading:.6f}; converged {r.converged}.')
    lines.append('Factors are sign-aligned diagnostically before comparison. Predictions retain the untouched fitted factor/bridge pairing, so alignment cannot manufacture forecast changes. M2-L2 is not merely a sign flip. Loadings are measurement associations, not causal contributions. Every loading and its absolute share and change versus S0 is in phase6g_factor_loadings.csv; loading-share changes do not decompose GDP effects.')
    for r in current_l.loc[current_l.model.eq('S2') & current_l.variable.ne('m2')].itertuples():
        lines.append(f'S2 {r.variable}: loading {r.loading:.6f}, Δ vs S0 {r.delta_loading_vs_S0:.6f}, absolute loading share {r.absolute_loading_share_pct:.2f}%.')
    lines+=['','## Current quarter and governance','',
        '| Model | Frozen-cutoff 2026Q3 nowcast (%) | Δ vs P0 (pp) |','|---|---:|---:|']
    for model in a.MODELS:lines.append(f'| {model} | {current[model]:.9f} | {current[model]-current["P0"]:.9f} |')
    lines += ['',f'G2 is {current["G2"]:.9f}%, {current["G2"]-current["P0"]:.9f} pp above the unchanged {current["P0"]:.9f}% production estimate. These are rebuilt from the exact archived Phase 6E economic inputs at its 2026-10-05 cutoff, not hard-coded or refreshed to the execution date.',
        'The serious-candidate screen considers both original-holdout and extended common samples: at least 0.03 pp pooled improvement, no horizon deterioration, improvement after every quarter exclusion, at least 50% origin win rate, and no more than 25% mean-absolute-revision deterioration. The revision screen is a declared research governance tolerance, not an estimated model parameter. All successful fits must pass the unchanged convergence and information-boundary gates. The 0.05 pp threshold is highlighted as economically relevant, not automatic promotion.',
        f'Classification: {recommendation["classification"]}. Recommendation: {recommendation["recommendation"]}. '+
            ('G2 passes the stated screen for shadow monitoring only. It is not promoted to production.' if recommendation['recommendation'].startswith('ADVANCE') else 'The combined evidence does not justify advancing M2-L2 to shadow production under this screen.'),
        'Historical M2 value-vintage evidence remains unresolved even if a publication mask passes. No release dates are invented: assumed availability and verified GDP publication dates are distinguished. Predictor revision-value leakage cannot be ruled out. Phase 6E production, its COMBO_50_50 configuration and dashboards remain unchanged.',
        'Reproduce with `.venv/Scripts/python.exe -m scripts.phase6g.run`. Independent refit-rerun verification and completed test counts are attached in phase6g_validation_evidence.json and phase6g_determinism.json. Protected artifacts are hashed before and after; a changed protected file fails the run. No network request or production writer is invoked.',
        recommendation['classification'],recommendation['recommendation']]
    text='\n\n'.join(lines)+'\n'
    text=re.sub(r'(?m)(^\|[^\n]*)\n\n(?=\|)',r'\1\n',text)
    (out/'phase6g_results.md').write_text(text,encoding='utf8')
