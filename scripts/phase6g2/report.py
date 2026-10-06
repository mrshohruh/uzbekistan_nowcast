"""Evidence-grounded research report; no production promotion."""
import json
import numpy as np
import pandas as pd


def report(comparison, metrics, loads, loo, fdi, now):
    from scripts.phase6g2.run import OUT, ROOT, csv
    common=comparison.loc[comparison['sample'].eq('COMMON')].set_index('model')
    natural=comparison.loc[comparison['sample'].eq('NATURAL')].set_index('model')
    best=common.RMSE.idxmin();qbest=common.loc[['Q0','Q1','Q2']].RMSE.idxmin()
    qloo=loo.loc[loo['sample'].eq('COMMON')&loo.model.eq(qbest)]
    robust=bool(qloo.delta_RMSE_vs_M0.lt(0).all())
    gain=common.loc['M0','RMSE']-common.loc[qbest,'RMSE']
    best_yoy=common.loc[['M0','M1','M2']].RMSE.idxmin()
    best_yoy_gain=common.loc[best_yoy,'RMSE']-common.loc[qbest,'RMSE']
    classification='PHASE6G2_QOQ_M2_PROMISING_RESEARCH_ONLY' if best_yoy_gain>0 else 'PHASE6G2_NO_IMPROVEMENT'
    audit=json.loads((OUT/'phase6g2_audit.json').read_text())
    production=json.loads((ROOT/'results/phase6e/phase6e_current_nowcast.json').read_text())
    lines=['# Phase 6G.2 research results','',classification,'',
        'Primary comparison: identical common start and global intersection of successful forecast origins across all six models in BOTH sample regimes. Errors and bias are actual minus forecast; OOS R² is 1 − SSE_model/SSE_M0.',
        '','| Model | M2 transform | Economic lag | H1 RMSE | H2 RMSE | H3 RMSE | Pooled RMSE | OOS R² | 2026Q3 |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,r in common.iterrows():
        lines.append(f'| {name} | {"YoY log" if name.startswith("M") else "3-month log"} | {name[-1]} | {r.H1_RMSE:.6f} | {r.H2_RMSE:.6f} | {r.H3_RMSE:.6f} | {r.RMSE:.6f} | {r.OOS_R2:.6f} | {r.nowcast:.6f} |')
    lines+=['','## Implementation audit','',
        f'M2 source: {audit["m2_source"]}. Monthly end-of-period stock, {audit["raw_unit"]}. Code and {audit["matched_raw_frozen_months"]} matched months verify 100 × ln(M2_t/M2_t−12); maximum reconstruction difference {audit["maximum_raw_frozen_difference"]:.3g}.',
        f'The publication assumption is {audit["publication_lag_days"]} days; it is separate from economic lag. Order: {audit["ordering"]}. Standardization uses the pre-target-quarter mean and sample standard deviation only. No filling, annualization or quarterly collapse occurs.',
        'Accepted kernels are reused: eight predictors, one DynamicFactorMQ factor, AR(2), no idiosyncratic AR(1), EM maxiter 500/tolerance 1e−5, missing-data M step, likelihood-decrease revert, filtered factors, quarterly mean bridge with intercept and GDP(q−1). GDP publication/vintage gating and target actuals remain unchanged.',
        '','## A–C. Transformation, economic lag and samples','',
        f'First raw M2 month: {audit["first_raw"]}; first YoY month: {audit["first_yoy"]}; first 3-month month: {audit["first_qoq"]}. The accepted specification keeps the January 2019 earliest start. Economic lags are applied after the release mask, including its initial boundary, exactly as Phase 6F. Natural balanced starts may therefore differ; common starts use the latest of all six starts per origin. Full starts and training counts are in sample_comparison.csv.',
        f'Natural best: {natural.RMSE.idxmin()}; common best: {best}. Primary common forecast count per model: {int(common.N.min())}. Best 3-month model: {qbest}; pooled improvement versus common M0: {gain:.6f} pp. Natural and common results are both reported, never blended.',
        f'Best YoY model is {best_yoy}; best 3-month improvement versus best YoY: {best_yoy_gain:.6f} pp.',
        '','## D. Factor behavior','']
    for name in ['Q0','Q1','Q2']:
        g=loads.loc[loads['sample'].eq('COMMON')&loads.model.eq(name)&loads.indicator.eq('m2')]
        lines.append(f'{name}: median factor correlation with M0 {g.factor_correlation_vs_M0.median():.6f}; current M2 loading {g.loc[g.current,"factor_loading"].iloc[0]:.6f}; current factor/M2 correlation {g.loc[g.current,"factor_M2_correlation"].iloc[0]:.6f}. Signs are aligned to M0 for comparisons; no forecast changes from alignment.')
    lines+=['','## E–G. FDI audit and bridge sensitivity','',
        'FDI_TRANSFORMATION_USED = FDI_million_USD / 1000 (nominal levels; linear scaling). Exact parser selects the CBU BOP Dataset row “Direct investment: liabilities”, quarterly net incurrence of liabilities, million USD. No ln, log1p, asinh or statistical standardization was used in Phase 6F. FDI only enters quarterly bridges.',
        'B3 = M0 factor + GDP(q−1) + economic-L1 M2 quarter mean + latest release-gated FDI/1000. B4 adds one exact reference-quarter FDI lag. B5 = M1 factor + GDP(q−1) + latest gated FDI/1000, without separate M2. Evidence: scripts/phase6f/experiment.py:96–156 and 254–260. Full repository text evidence is preserved in fdi_repository_evidence.csv.',
        'Q2 bridge challengers compare levels with asinh(FDI_million_USD), with no separate M2 bridge regressor. Both use identical factor histories and GDP gating. The inherited bridge helper’s /1000 scaling is cancelled for asinh inputs. Ordinary ln is optional and was not fitted; zero/negative counts are in fdi_transformation_audit.csv.',
        'FDI sensitivities use assumed quarter-end +90/+120 days at the same H stage in training. They are revised-history diagnostics, NOT vintage-real-time. Source release dates remain unknown. The FDI snapshot was retrieved after the frozen current production cutoff, so Q2_FDI_ASINH current estimates are unavailable. No post-cutoff value is injected.']
    fmetrics=[]
    if not fdi.empty:
        wide=fdi.pivot(index=['target_quarter','horizon'],columns='model',values='prediction').dropna()
        actual=fdi.drop_duplicates(['target_quarter','horizon']).set_index(['target_quarter','horizon']).actual.reindex(wide.index)
        for name in wide:
            e=actual-wide[name]
            fmetrics.append(dict(model=name,N=len(e),RMSE=float(np.sqrt(np.mean(e**2))),MAE=float(e.abs().mean()),bias=float(e.mean())))
        csv('fdi_metrics',fmetrics)
        for r in fmetrics:lines.append(f'{r["model"]}: N={r["N"]}, RMSE={r["RMSE"]:.6f}, MAE={r["MAE"]:.6f}, bias={r["bias"]:.6f}.')
    lines+=['','## H. Leave-one-quarter-out sensitivity','',
        f'{qbest} improves common M0 after every quarter exclusion: {robust}. RMSE delta range {qloo.delta_RMSE_vs_M0.min():.6f} to {qloo.delta_RMSE_vs_M0.max():.6f}. This removes a scoring quarter; it does not refit a cross-validation model. All model/exclusion results are in leave_one_quarter_out.csv.',
        '','## Explicit answers','',
        f'1. Best 3-month versus YoY M0 improvement: {gain:.6f} pp; versus corresponding YoY: {-common.loc[qbest,"delta_RMSE_vs_corresponding_YoY"]:.6f} pp.',
        f'2. Identical common-sample best is {best}; compare natural results in model_comparison.csv.',
        f'3. Best common M2 lag is {best[-1]} months ({best}).',
        '4. Factor correlations and loading differences above quantify the effect; loadings are descriptive associations, not causal contributions.',
        '5. Horizon-specific differences versus M0: '+ '; '.join(f'{h}: {common.loc[qbest,h+"_RMSE"]-common.loc["M0",h+"_RMSE"]:.6f} pp' for h in ['H1','H2','H3'])+'.',
        '6. FDI was not logarithmized; it used linearly scaled levels.',
        '7–8. See identical-origin FDI metrics below; robustness across 90/120 days is required and revised-history results cannot establish vintage-real-time gains.',
        '9. No challenger is promoted. Missing historical M2/FDI value vintages, retrospective specification testing and a small quarter sample preclude production-readiness.',
        '','## Volatility and current forecasts','',
        'm2_diagnostics.csv reports mean, sample standard deviation, extrema, calendar autocorrelations at 1/3/12, YoY/3-month correlation and >3 SD flags. No flagged observation is removed.',
        f'Unchanged production DFM {production["dfm_forecast"]:.9f}%; U-MIDAS {production["umidas_forecast"]:.9f}%; COMBO_50_50 {production["final_forecast"]:.9f}%. Research forecasts and differences versus production DFM are in current_nowcasts.csv.',
        '','Reproduce: `.venv/Scripts/python.exe -m scripts.phase6g2.run`; test: `.venv/Scripts/python.exe -m scripts.phase6g2.tests`. Only the new scripts/phase6g2 and results/phase6g2 areas are authored. Protected production, earlier research, processed/master data and dashboard bytes are verified before and after.']
    if fmetrics:
        fm=pd.DataFrame(fmetrics).set_index('model')
        for suffix in ['', '_120D']:
            delta=fm.loc['Q2_FDI_ASINH'+suffix,'RMSE']-fm.loc['Q2_FDI_LEVELS'+suffix,'RMSE']
            lines.append(f'ASINH minus levels RMSE ({120 if suffix else 90} days): {delta:.6f} pp; improvement: {delta<0}.')
    (OUT/'phase6g2_results.md').write_text('\n\n'.join(lines)+'\n',encoding='utf8')
    horizonbest={h:metrics.loc[metrics['sample'].eq('COMMON')&metrics.horizon.eq(h)].sort_values('RMSE').iloc[0].model for h in ['H1','H2','H3']}
    summary=['FDI_TRANSFORMATION_USED = nominal million USD / 1000']
    summary += [f'{name} pooled RMSE: {common.loc[name,"RMSE"]:.6f}' for name in common.index]
    summary += [f'Natural best: {natural.RMSE.idxmin()}; common best: {best}',f'Best horizons: {horizonbest}',
        '2026Q3 common forecasts: '+str(common.nowcast.to_dict()),
        f'Production DFM/U-MIDAS/COMBO: {production["dfm_forecast"]:.9f}/{production["umidas_forecast"]:.9f}/{production["final_forecast"]:.9f}',
        'FDI ASINH: '+str(fmetrics),classification,'Production files unchanged: verified by SHA-256 before/after']
    (OUT/'phase6g2_terminal_summary.txt').write_text('\n'.join(summary)+'\n',encoding='utf8')
    # Include immutable production references in the output alongside challengers.
    rows=list(now)
    for name,key in [('PHASE6E_PRODUCTION_DFM','dfm_forecast'),('U_MIDAS','umidas_forecast'),('COMBO_50_50','final_forecast')]:
        rows.append(dict(sample='PRODUCTION_REFERENCE',model=name,target_quarter='2026Q3',nowcast=production[key],
            difference_vs_production_DFM=production[key]-production['dfm_forecast'],status='UNCHANGED_PRODUCTION_REFERENCE'))
    csv('current_nowcasts',rows)
    return classification
