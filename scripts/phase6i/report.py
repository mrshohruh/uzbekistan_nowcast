"""Self-contained presentation and auditable scientific interpretation."""
import html
import json
import pandas as pd
from scripts.phase6i.models import SPECS, KEYS


def report(out, tables, classification, best, dataset, current, latest):
    comparison=tables['model_comparison']
    metrics=tables['horizon_metrics']
    primary=metrics.loc[metrics['sample'].eq('strict_common') & metrics.evaluation_group.eq('HOLDOUT')]
    now=tables['current_nowcasts']
    winners={h:primary.loc[primary.horizon.eq(h)].sort_values('rmse').iloc[0].model for h in ['H1','H2','H3']}
    rmse='\n'.join(f'{r.model} = {r.pooled_rmse:.9f}' for r in comparison.itertuples())
    forecasts='\n'.join(f'{r.model} = {r.current_nowcast:.9f}%' for r in now.itertuples())
    transformations=[]
    for key in KEYS:
        row=next(r for r in dataset.registry.scope('v1') if r['variable_key']==key)
        transformations.append(dict(variable=key,field=row['clean_model_field'],transformation=row['required_transformation'],lag_days=dataset.release_lag_days[key]))
    interpretation=(
        'This is evidence generation only. The primary ranking uses identical HOLDOUT origins across U0–U6. '
        'Development and combined development/holdout results are supplementary, not independent validation. '
        'Only four holdout quarters are available, with three dependent horizons per quarter. '
        'A lower RMSE here is insufficient evidence for promotion. The largest model estimates 14 parameters '
        'from a short quarterly history; N/K below 3 is flagged as weak degrees of freedom. '
        'Proceed with U0 as the frozen benchmark and the lowest common-holdout RMSE challenger as a provisional '
        'candidate for prospective evaluation. Do not promote or tune lag lengths on this holdout.')
    if classification=='PHASE6I_KEEP_U0':
        interpretation+=' Every challenger has worse common-holdout pooled RMSE than U0. Retain U0; the best challenger is a comparator for further research, not a preferred production specification.'
    audit='''Target: published cumulative year-to-date real GDP YoY percent, volume index minus 100; GDP remains quarterly. This is not standalone-quarter GDP growth.

USD/UZS: Rate/Nominal, monthly mean, then 100 × change in log monthly mean; positive means UZS depreciation.

Design: intercept + one GDP lag + three monthly USD/UZS values, oldest to newest. Each predictor addition contributes three coefficients. U0 has K=5; U1/U2/U3 K=8; U4/U5 K=11; U6 K=14. OLS uses numpy.linalg.lstsq with rcond=None; classical conditional OLS standard errors are supplementary, not robust inference.

Lag alignment: last three nonmissing observations available at each quarter/horizon, NOT necessarily the three months in that quarter. Internal missing months are skipped exactly as in production; no filling or extrapolation. If fewer than three values exist, that training row is omitted or the target forecast fails. GDP lag follows the preceding available training quarter; target GDP lag is the latest strictly released quarter. This reproduces the production convention rather than silently changing it.

H1/H2/H3: end of first/second/third calendar month in target quarter. Each variable is masked by reference month end + registry typical lag <= nominal horizon origin. For current post-H3 initialization, actual retrieval/release gating uses the frozen snapshot cutoff, followed by the unchanged nominal H3 mask.

Training: expanding history of verified GDP vintages strictly available before forecast origin; no current/future target GDP. Every historical training predictor vector is reconstructed at its own same-horizon nominal origin. Minimum 15 complete quarterly rows. No lag search, feature scaling, ridge penalty or variable selection.

Historical evaluation: exact existing standard-lag STRICT GDP-vintage origins and stored scoring actuals, split into DEVELOPMENT and HOLDOUT. U0 is independently checked against both the production function and every frozen historical prediction. The current production scoring sample comprises 12 origins across four holdout quarters; this study also supplies the 36 development origins.

Historical predictors lack complete verified release vintages. Latest revised canonical master values are masked using the existing approved registry-lag pseudo-real-time convention. Typical lags are assumptions, not observed release dates; no dates or vintages are fabricated. This is not a full real-time backtest. Current added predictors are separately gated by observed retrieval and known release timestamp.

IP deliberately uses canonical ind_prod_yoy_log, not the approved Phase6A2 recovered real-activity percent-growth series used by DFM. These are different concepts; registry and production are unchanged. Retail uses retail_yoy_log (not retail_trade_yoy_log); M2 is nominal EOP stock YoY log growth, never real M2. All values are already approved transformed pipeline fields, not newly defined series.

Bias = actual minus forecast, in GDP percentage points. Correlations are pairwise complete monthly transformed inputs, with overlap counts; they are descriptive and never used for fitting or selection. Rank, raw design condition number, coefficient signs, ranges and standard deviations are supplied; condition numbers depend on units and the intercept. Standard errors are null when residual degrees of freedom or full rank are unavailable. Strong correlations alone do not disqualify a model.
'''
    incremental=[]
    for a,b,label in [('U0','U1','IP beyond FX'),('U1','U4','M2 after FX + IP'),('U4','U6','Retail after FX + IP + M2'),('U0','U2','M2 alone'),('U0','U3','Retail alone')]:
        rows=tables['incremental_value'].loc[tables['incremental_value'].baseline.eq(a)&tables['incremental_value'].challenger.eq(b)]
        pooled=rows.loc[rows.horizon.eq('POOLED')].iloc[0]
        improving=rows.loc[rows.horizon.ne('POOLED'),'delta_rmse'].lt(0).sum()
        incremental.append(f'{label} ({a} → {b}): matched pooled ΔRMSE {pooled.delta_rmse:+.6f} pp, ΔMAE {pooled.delta_mae:+.6f} pp; improves RMSE in {improving}/3 horizons. Improved origins {pooled.improved_origins}/{pooled.n_origins}. Total SSE gain {pooled.total_sse_gain:.6f}; top two quarter gains {pooled.top_two_quarter_sse_gain:.6f}. Interpret concentration cautiously.')
    corr=tables['predictor_correlations']
    severe=corr.loc[corr.variable_a.ne(corr.variable_b)&corr.correlation.abs().ge(.9)]
    unstable=tables['coefficient_stability'].loc[tables['coefficient_stability'].distinct_signs.gt(1)]
    numerical=f'{len(unstable)} coefficient/horizon groups change sign across successful origins. {len(severe)//2} predictor pairs have absolute monthly correlation >= 0.9. Full coefficient ranges and condition numbers are supplied in the coefficient and forecast CSVs. No causal interpretation is assigned to individual coefficients.'
    lines=[f'PHASE 6I CLASSIFICATION: {classification}', '', 'Current production U-MIDAS:',
        'U0: intercept + latest released GDP lag + three released USD/UZS monthly log changes (oldest first).','',
        'Best research challenger:',f'{best}: {" + ".join(SPECS[best])} (provisional RMSE leader; not a promotion).','',
        'Common-sample pooled RMSE:',rmse,'',*[f'Best {h} model: {m}' for h,m in winners.items()],'',
        'Current 2026Q3 research nowcasts:',forecasts,'','Production changed:','NO','',
        f'Production remains {current[4]["final_forecast"]}% = 50% DFM + 50% U-MIDAS. Current U0 is {current[4]["umidas_forecast"]}%.',
        '',interpretation,'',*incremental,'',numerical,'','Production U-MIDAS audit','',audit,
        'Registry transformation contract','',pd.DataFrame(transformations).to_csv(index=False),
        'Coverage and sample limits','',tables['sample_comparison'].to_csv(index=False),
        'Parsimony and numerical diagnostics','',
        tables['all_forecasts'].groupby('model').agg(n_train_min=('n_train','min'),n_train_max=('n_train','max'),
            n_over_k_min=('n_over_k','min'),weak_fits=('weak_degrees_of_freedom','sum'),
            condition_max=('condition_number','max'),rank_min=('rank','min')).to_csv(),
        'Reproducibility','', 'Run `.venv/Scripts/python.exe -m scripts.phase6i.run`. No network or production writer is invoked. '
        'The manifest records full before/after SHA256 inventories, code hashes, frozen snapshot and output hashes. '
        'Tests and deterministic rerun checks are recorded in phase6i_validation.json.']
    (out/'phase6i_results.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    def table(frame):return frame.to_html(index=False,border=0,float_format=lambda x:f'{x:.4f}',classes='data')
    def bars(frame,column):
        maximum=max(float(frame[column].max()),1e-9)
        return '<div class="bars">'+''.join(f'<div><b>{r.model}</b><span style="width:{max(1,float(getattr(r,column))/maximum*80):.2f}%"></span><em>{getattr(r,column):.4f}</em></div>' for r in frame.itertuples())+'</div>'
    hold=tables['common_sample_forecasts'].loc[tables['common_sample_forecasts'].evaluation_group.eq('HOLDOUT')]
    def chart(frame,errors=False):
        series=list(SPECS) if errors else ['actual',*SPECS]
        values={k:(frame.actual-frame[k] if errors else frame[k]).tolist() for k in series}
        v=[x for vals in values.values() for x in vals];lo=min(v)-.2;hi=max(v)+.2
        colors=['#f4c76e','#67d5d0','#6ea8fe','#b19afa','#f98fab','#a8d88b','#efac75','#e2e8f0']
        svg='<svg viewBox="0 0 1000 340" role="img" aria-label="Common holdout forecasts">'
        for k,color in zip(series,colors):
            pts=' '.join(f'{50+i*900/max(len(frame)-1,1):.2f},{280-(x-lo)/(hi-lo)*240:.2f}' for i,x in enumerate(values[k]))
            svg+=f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5"><title>{k}</title></polyline>'
        for i,r in enumerate(frame.itertuples()):svg+=f'<text x="{50+i*900/max(len(frame)-1,1):.2f}" y="310" text-anchor="middle" fill="#b9c7da" font-size="10">{r.target_quarter} {r.horizon}</text>'
        svg+='</svg><p>'+ ' · '.join(f'<span style="color:{c}">{k}</span>' for k,c in zip(series,colors))+'</p>'
        return svg
    sections=[('Conclusion',f'<h2>{html.escape(classification)}</h2><p>{html.escape(interpretation)}</p>'+table(comparison[['model','predictors','n_parameters','pooled_rmse','pooled_mae']])),
        ('2026Q3 research nowcasts',table(now[['model','horizon','current_nowcast','difference_from_U0','n_parameters','n_train','n_over_k']])),
        ('H1/H2/H3 RMSE', ''.join(f'<h3>{h}</h3>'+bars(primary.loc[primary.horizon.eq(h)],'rmse') for h in ['H1','H2','H3'])),
        ('Pooled RMSE',bars(comparison,'pooled_rmse')),('Pooled MAE',bars(comparison,'pooled_mae')),
        ('Common holdout forecasts vs actual (GDP %)',chart(hold)),('Forecast errors by quarter (actual − forecast, pp)',chart(hold,True)),
        ('Sample size and parameters',table(primary.loc[primary.horizon.eq('POOLED'),['model','n_origins','n_parameters','n_train_min','n_train_median','n_train_max']])),
        ('Maximum-available and common-sample metrics',table(metrics.loc[metrics.horizon.eq('POOLED')&metrics['sample'].isin(['maximum_available','strict_common']),['sample','evaluation_group','model','n_origins','rmse','mae','bias']])),
        ('Incremental value: U0 → U1 → U4 → U6',''.join('<p>'+html.escape(x)+'</p>' for x in incremental)),
        ('Predictor correlation matrix',table(tables['predictor_correlations'].pivot(index='variable_a',columns='variable_b',values='correlation').reset_index())),
        ('Current coefficients and monthly lag positions',table(tables['coefficients'].loc[tables['coefficients'].evaluation_group.eq('CURRENT'),['model','variable','monthly_position','coefficient','standard_error','sign','regressor_value','contribution_pp']])),
        ('Coefficient stability across origins','<p>'+html.escape(numerical)+'</p>'+table(tables['coefficient_stability'])),
        ('Latest usable data',table(pd.DataFrame([dict(variable=k,field=dataset.clean_field_by_key[k],latest_month=v,lag_days=dataset.release_lag_days[k]) for k,v in latest.items()]))),
        ('Scientific interpretation and audit',''.join('<p>'+html.escape(x)+'</p>' for x in audit.split('\n\n'))),
        ('Production unchanged',f'<h2>{current[4]["final_forecast"]:.12f}%</h2><p>Frozen 50/50 DFM + U-MIDAS. Research only. No promotion.</p>')]
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Uzbekistan · Phase 6I U-MIDAS research</title><style>
    *{box-sizing:border-box}body{margin:0;background:#0c1424;color:#e2e8f0;font:15px/1.65 system-ui,sans-serif}main{max-width:1250px;margin:auto;padding:35px}header{padding:30px 0;border-bottom:1px solid #334155}h1{font-size:36px;margin:5px 0}h2{color:#67d5d0}section{background:#152239;margin:24px 0;padding:26px;border:1px solid #2c3c55;border-radius:14px;overflow:auto}small,em{color:#b9c7da}.data{width:100%;border-collapse:collapse;font-size:13px}.data td,.data th{text-align:left;padding:9px;border-bottom:1px solid #334155;white-space:nowrap}.data th{color:#67d5d0}.bars div{display:flex;gap:12px;align-items:center;margin:12px 0}.bars span{height:18px;background:linear-gradient(90deg,#2f8f9e,#67d5d0);border-radius:3px}.bars b{width:28px}.bars em{font-style:normal}svg{width:100%;min-width:650px}p{max-width:1050px}.badge{display:inline-block;background:#254355;color:#85e3dc;padding:6px 13px;border-radius:30px}</style><main><header><span class="badge">RESEARCH ONLY · PRODUCTION UNCHANGED</span><h1>Uzbekistan U-MIDAS expansion</h1><small>Phase 6I · Strict common holdout comparison · GDP errors in percentage points</small></header>'''
    page+=''.join(f'<section><h2>{title}</h2>{body}</section>' for title,body in sections)
    page+='</main></html>'
    (out/'phase6i_umidas_comparison.html').write_text(page,encoding='utf8')
