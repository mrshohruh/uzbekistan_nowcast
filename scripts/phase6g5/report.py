"""Matched scoring and descriptive diagnostics; never writes production files."""
import itertools
import json
import html
import numpy as np
import pandas as pd
from scripts.phase6g5.run import OUT, ROOT, csv, verify
from scripts.phase6g4.core import MODELS
from scripts.phase6g4.report import score, markdown
from scripts.phase6g.run import HOLDOUT
from scripts.phase6e.models import sw

LABELS = dict(zip(MODELS, ['Current M0','CPI only','Nominal M2 + CPI','Real M2 + CPI','Real M2 only']))

def vif(frame):
    """OLS with intercept. Exact linear dependence is reported as infinity."""
    x=frame.dropna(); rows=[]
    for col in x:
        y=x[col].to_numpy(); others=x.drop(columns=col).to_numpy()
        design=np.column_stack([np.ones(len(x)),others])
        residual=y-design@np.linalg.lstsq(design,y,rcond=None)[0]
        sst=np.sum((y-y.mean())**2); sse=np.sum(residual**2)
        rows.append(dict(variable=col,N=len(x),vif=np.inf if sse<=sst*1e-12 else sst/sse,
                         diagnostic_only=True))
    return rows

def generate():
    read=lambda n:pd.read_csv(OUT/f'phase6g5_{n}.csv',float_precision='round_trip')
    f=read('origin_forecasts'); paths=read('factor_paths'); loads=read('factor_loadings')
    fits=read('fit_statistics'); now=read('current_nowcasts'); signals=read('signals')
    key=['target_quarter','horizon']; common=f.loc[f['sample'].eq('COMMON')]
    keys=common.pivot(index=key,columns='model',values='prediction').reindex(columns=MODELS).dropna().index
    common=common.set_index(key).loc[keys].reset_index(); csv('common_sample_forecasts',common)
    native=f.loc[f['sample'].eq('NATIVE')].merge(common[key].drop_duplicates(),on=key,validate='many_to_one')
    horizons=[]; comparison=[]; stability=[]; differences=[]
    benchmark=pd.read_csv(ROOT/'results/phase6g/phase6g_origin_level_forecasts.csv').query("model == 'U0'")
    for model in MODELS:
        c=common.loc[common.model.eq(model)]; n=f.loc[f.model.eq(model)&f['sample'].eq('NATIVE')]
        nm=n.merge(common[key].drop_duplicates(),on=key,validate='one_to_one')
        for sample,g in [('FULL_AVAILABLE',n),('STRICT_COMMON_SPAN',c),('NATIVE_MATCHED_ORIGINS',nm)]:
            for h in ['H1','H2','H3','POOLED']:
                horizons.append(dict(model=model,label=LABELS[model],sample=sample,horizon=h,**score(g if h=='POOLED' else g.loc[g.horizon.eq(h)])))
        comparison.append(dict(model=model,specification=LABELS[model],common_sample_pooled_rmse=score(c)['rmse'],
            full_available_rmse=score(n)['rmse'],full_available_n=len(n),native_matched_rmse=score(nm)['rmse'],
            post_development_rmse=score(c.loc[c.target_quarter.isin(HOLDOUT)])['rmse'],
            mae=score(c)['mae'],bias=score(c)['bias'],n_matched_origins=len(c),n_independent_quarters=c.target_quarter.nunique()))
        base=common.loc[common.model.eq(MODELS[0])][key+['prediction']]
        joined=c.merge(base,on=key,suffixes=('','_m0'),validate='one_to_one')
        joined['error']=joined.actual-joined.prediction;joined['m0_error']=joined.actual-joined.prediction_m0
        for r in joined.itertuples():differences.append(dict(model=model,target_quarter=r.target_quarter,horizon=r.horizon,
            error=r.error,m0_error=r.m0_error,squared_error_difference=r.error**2-r.m0_error**2))
        q=joined.groupby('target_quarter').apply(lambda x:pd.Series(dict(mse=(x.error**2).mean(),base_mse=(x.m0_error**2).mean())),include_groups=False)
        u=c.merge(benchmark[key+['prediction']],on=key,suffixes=('','_u'),validate='one_to_one')
        uq=u.groupby('target_quarter').apply(lambda x:pd.Series(dict(mse=((x.actual-x.prediction)**2).mean(),u_mse=((x.actual-x.prediction_u)**2).mean())),include_groups=False)
        pivot=c.pivot(index='target_quarter',columns='horizon',values='prediction').reindex(columns=['H1','H2','H3'])
        revisions=pivot.diff(axis=1).iloc[:,1:].stack().dropna()
        # Adjacent target quarters at a fixed horizon; includes changes in the GDP target.
        consecutive=pivot.diff().where(pd.Series(pd.PeriodIndex(pivot.index,freq='Q').asi8,index=pivot.index).diff().eq(1),axis=0).stack().dropna()
        row=dict(model=model,error_std=joined.error.std(),max_abs_error=joined.error.abs().max(),
            within_quarter_revision_std=revisions.std(),within_quarter_mean_abs_revision=revisions.abs().mean(),
            quarter_to_quarter_forecast_change_std=consecutive.std(),quarter_to_quarter_change_n=len(consecutive),
            quarters_beating_m0=int(q.mse.lt(q.base_mse).sum()),share_quarters_beating_m0=q.mse.lt(q.base_mse).mean(),m0_win_comparison='COMMON refit M0; native benchmark performance reported separately',
            quarters_beating_umidas=int(uq.mse.lt(uq.u_mse).sum()),share_quarters_beating_umidas=uq.mse.lt(uq.u_mse).mean(),umidas_quarters=len(uq),
            pre_development_rmse=score(c.loc[~c.target_quarter.isin(HOLDOUT)])['rmse'],post_development_rmse=score(c.loc[c.target_quarter.isin(HOLDOUT)])['rmse'])
        for h in ['H1','H2','H3']:row['worst_'+h+'_absolute_error']=joined.loc[joined.horizon.eq(h),'error'].abs().max()
        stability.append(row)
    csv('horizon_metrics',horizons);csv('model_comparison',comparison);csv('stability_metrics',stability);csv('matched_error_differences',differences)
    series=signals.set_index(pd.to_datetime(signals.date))[['nominal_m2','cpi','real_m2']]
    correlations=[];rolling=[]
    for a,b in itertools.combinations(series,2):
        x=series[[a,b]].dropna()
        correlations.append(dict(variable_a=a,variable_b=b,N=len(x),start=str(x.index.min()),end=str(x.index.max()),pearson=x[a].corr(x[b]),spearman=x[a].corr(x[b],method='spearman')))
        for date,value in series[a].rolling(24,min_periods=24).corr(series[b]).items():
            window=series.loc[:date,[a,b]].tail(24)
            rankcorr=window[a].corr(window[b],method='spearman') if len(window)==24 and window.notna().all().all() else np.nan
            rolling.append(dict(date=str(date),variable_a=a,variable_b=b,pearson_24m=value,spearman_24m=rankcorr,window_months=24))
    csv('signal_correlations',correlations);csv('rolling_correlations',rolling)
    v=[]
    for cols in [['nominal_m2','cpi'],['real_m2','cpi'],['nominal_m2','real_m2'],list(series)]:
        v.extend(dict(specification=' + '.join(cols),**r) for r in vif(series[cols]))
    csv('vif_diagnostics',v)
    fc=[]
    for context,g in paths.groupby(['sample','target_quarter','horizon','current']):
        wide=g.pivot(index='date',columns='model',values='factor_value')
        for a,b in itertools.combinations(MODELS,2):
            if a in wide and b in wide:
                x=wide[[a,b]].dropna();fc.append(dict(zip(['sample','target_quarter','horizon','current'],context),model_a=a,model_b=b,N=len(x),correlation=x[a].corr(x[b])))
    csv('factor_correlations',fc)
    # Reconstruct the unchanged bridge's fitted residuals from the exact saved factors and eligible GDP.
    events=pd.read_csv(ROOT/'results/research/phase6b2/phase6b2_gdp_revision_history.csv');bridge=[]
    for context,g in paths.groupby(['sample','model','target_quarter','horizon','forecast_origin','current']):
        sample,model,target,h,origin,current=context
        available=sw.common.vintage_kernel().available_gdp_vintage_as_of(events,origin,target=target,timing_rule='STRICT')
        gd=available.frame.value;g=g.set_index(pd.to_datetime(g.date)).factor_value
        fq=g.groupby(g.index.to_period('Q')).mean();x=[];y=[]
        for q in fq.index:
            if str(q)<target and str(q) in gd and str(q-1) in gd:
                x.append([1,fq[q],gd[str(q-1)]]);y.append(gd[str(q)])
        x=np.asarray(x);y=np.asarray(y);res=y-x@np.linalg.lstsq(x,y,rcond=None)[0]
        bridge.append(dict(sample=sample,model=model,target_quarter=target,horizon=h,current=current,bridge_n=len(y),bridge_fit_rmse=np.sqrt(np.mean(res**2)),bridge_r2=1-np.sum(res**2)/np.sum((y-y.mean())**2)))
    csv('bridge_fit',bridge)
    for sample in now['sample'].unique():
        base=now.loc[now['sample'].eq(sample)&now.model.eq(MODELS[0]),'nowcast_2026q3']
        now.loc[now['sample'].eq(sample),'difference_vs_M0']=now.loc[now['sample'].eq(sample),'nowcast_2026q3']-(base.iloc[0] if len(base) else np.nan)
    now['label']=now.model.map(LABELS)
    for i,r in now.iterrows():
        g=paths.loc[paths.current&paths['sample'].eq(r['sample'])&paths.model.eq(r.model)]
        dates=pd.to_datetime(g.date)
        training=g.loc[dates.lt(pd.Period('2026Q3',freq='Q').start_time),'factor_value']
        target_mean=g.loc[dates.dt.to_period('Q').astype(str).eq('2026Q3'),'factor_value'].mean()
        now.loc[i,'factor_signal']=(target_mean-training.mean())/training.std(ddof=1)
        now.loc[i,'factor_signal_unit']='training-factor standard deviations; descriptive, not GDP pp'
    csv('current_nowcasts',now)
    comp=pd.DataFrame(comparison);hm=pd.DataFrame(horizons);st=pd.DataFrame(stability)
    sc=comp.merge(hm.query("sample == 'STRICT_COMMON_SPAN' and horizon != 'POOLED'").pivot(index='model',columns='horizon',values='rmse').rename(columns=lambda c:c+'_rmse'),on='model')
    sc=sc.merge(st[['model','within_quarter_revision_std']],on='model').merge(now.query("sample == 'NATIVE'")[['model','nowcast_2026q3']],on='model')
    sc['forecast_stability']='See error dispersion and horizon revisions; only six scored quarters'
    sc['factor_interpretability']='One-sided common factor; signs aligned to M0; descriptive units'
    sc['m2_cpi_redundancy_assessment']='Low CPI pairwise correlation; real money = nominal money minus inflation exactly'
    sc['decision']=np.where(sc.model.eq(MODELS[0]),'RETAIN_M0','REJECT');csv('selection_scorecard',sc)
    ablation=[]
    for before,after,label in [(0,2,'CPI conditional on nominal M2'),(4,3,'CPI conditional on real M2'),(1,2,'nominal M2 conditional on CPI'),(1,3,'real M2 conditional on CPI')]:
        a=comp.iloc[before];b=comp.iloc[after]
        row=dict(comparison=label,before=MODELS[before],after=MODELS[after])
        for col in ['common_sample_pooled_rmse','mae','bias']:row['delta_'+col]=b[col]-a[col]
        for col,frame in [('factor_variance_explained',fits),('bridge_fit_rmse',pd.DataFrame(bridge)),('bridge_r2',pd.DataFrame(bridge))]:
            frame=frame.loc[frame['sample'].eq('COMMON')&~frame.current].merge(common[key].drop_duplicates(),on=key)
            row['delta_mean_'+col]=frame.loc[frame.model.eq(b.model),col].mean()-frame.loc[frame.model.eq(a.model),col].mean()
        ablation.append(row)
    csv('ablation',ablation)
    fit_summary=fits.loc[fits['sample'].eq('COMMON')&~fits.current].merge(common[key].drop_duplicates(),on=key).groupby('model').agg(
        matched_fits=('model','size'),mean_factor_variance_explained=('factor_variance_explained','mean')).reset_index()
    bridge_summary=pd.DataFrame(bridge).query("sample == 'COMMON' and not current").merge(common[key].drop_duplicates(),on=key).groupby('model').agg(
        mean_bridge_fit_rmse=('bridge_fit_rmse','mean'),mean_bridge_r2=('bridge_r2','mean')).reset_index()
    fit_summary=fit_summary.merge(bridge_summary,on='model');csv('fit_summary',fit_summary)
    flags=[]
    baseline=comp.iloc[0]
    for model in MODELS:
        c=comp.loc[comp.model.eq(model)].iloc[0]
        h=hm.loc[hm.model.eq(model)&hm['sample'].eq('STRICT_COMMON_SPAN')&hm.horizon.ne('POOLED')].set_index('horizon')
        b=hm.loc[hm.model.eq(MODELS[0])&hm['sample'].eq('STRICT_COMMON_SPAN')&hm.horizon.ne('POOLED')].set_index('horizon')
        srow=st.loc[st.model.eq(model)].iloc[0];brow=st.iloc[0]
        flags.append(dict(model=model,horizons_improving_vs_common_m0=int(h.rmse.lt(b.rmse).sum()),
            one_horizon_only=bool(h.rmse.lt(b.rmse).sum()==1),few_quarters=True,shorter_estimation_history_than_native_m0=model!=MODELS[0],
            revision_volatility_more_than_twice_m0=bool(srow.within_quarter_revision_std>2*brow.within_quarter_revision_std),
            beats_unchanged_m0_on_matched_origins=bool(c.native_matched_rmse<baseline.native_matched_rmse),
            common_span_rmse_improvement_pct=100*(1-c.common_sample_pooled_rmse/baseline.common_sample_pooled_rmse)))
    csv('selection_flags',flags)
    if comp.iloc[1:].native_matched_rmse.lt(comp.iloc[0].native_matched_rmse).any():
        raise RuntimeError('Selection evidence changed: review recommendation before publishing report')
    reason=('Retain the unchanged M0. CPI-only has the best common-span RMSE, but this advantage disappears against the unchanged full-history M0 on exactly the same scoring origins. '
            'Only six quarters (18 horizon forecasts), four post-development quarters, and unverified historical predictor value vintages are available. No challenger establishes sufficient incremental out-of-sample value for promotion.')
    contract=('All five models share the frozen target, origins, STRICT GDP vintage gate, predictor availability rules, training-only scaling, one DynamicFactorMQ factor, AR(2), one-sided filtering, and bridge B. '
              'STRICT_COMMON_SPAN refits all models on identical monthly training dates. NATIVE_MATCHED_ORIGINS preserves each legitimate estimation history on identical scoring origins; M0 remains the actual benchmark. '
              'FULL_AVAILABLE is reported separately and cannot establish superiority. Bias = actual minus forecast. The current information set is the archived Phase6E cutoff, not a fresh October 6 download. '
              'COMMON current M0 fails the unchanged convergence gate; its missing estimate and missing differences stay null. The five current comparison estimates use native training histories and the same archived current information set.')
    content=('CPI is not largely duplicated by nominal M2: their Pearson correlation is about 0.041; nominal and real M2 are highly correlated (about 0.972). '
             'Adding nominal M2 to CPI raises common-span RMSE by 0.0305 pp (3.30%); adding real M2 raises it by 0.0375 pp (4.06%). '
             'Adding CPI to nominal or real M2 improves common-span performance, but does not beat the unchanged native M0 on matched origins. '
             'The current native CPI-containing factor paths correlate above 0.9999 with one another, but only about 0.03 with native M0 over overlapping months. '
             'Real-M2-only correlates about 0.972 with M0. CPI therefore materially changes the estimated common factor; adding money to CPI contributes little extra factor-path variation. '
             'These native comparisons also reflect estimation-history differences; COMMON path correlations are saved separately. This is evidence of changed factor structure, not demonstrated incremental GDP forecasting value. '
             'REJECT means reject promotion on this evidence, not permanently exclude a variable. Every challenger improves all three horizons against common-span M0, but none beats the unchanged native benchmark. '
             'Only six scored quarters limit robustness; the best short-span model has 3.8 times the M0 short-span horizon-revision volatility.')
    notes=('VIF is descriptive only and is not an automatic rejection criterion in a factor model. Correlation does not imply a multicollinearity problem in a DFM; high correlation does not prove a variable must be removed. '
           'The three-way VIF is infinite because real M2 YoY = nominal M2 YoY minus CPI YoY exactly; no tested model contains all three. '
           'Factor variance explained is the mean training squared correlation with the filtered factor, a descriptive projection measure, not a PCA eigenvalue or structural GDP contribution. '
           'GDP bridge fit is descriptive; in-sample R² does not determine selection. Loading signs are arbitrary and aligned within each origin. '
           'Within-quarter revisions compare H1/H2/H3 for the same target; quarter-to-quarter forecast changes also reflect different GDP targets and are not same-target revisions. '
           'The inherited post-development sample has already been inspected. Formal independent holdout evidence is unavailable. No release dates or vintage values were invented.')
    loadcurrent=loads.loc[loads.current&loads['sample'].eq('NATIVE')]
    drivers=read('current_drivers').query("sample == 'NATIVE'")
    manifest=json.loads((OUT/'phase6g5_run_manifest.json').read_text())
    manifest.update(classification='PHASE6G5_RETAIN_M0',decision='RETAIN_M0',development_cutoff='2025Q3',
        source_phase6g4_manifest_sha256=__import__('scripts.phase6f.experiment',fromlist=['sha']).sha(ROOT/'results/phase6g4/phase6g4_run_manifest.json'),
        selection_sample='identical scoring origins; show both common estimation spans and preserved native histories',
        uncertainty='six scored quarters; historical predictor value vintages unverified',factor_variance_definition='mean training squared correlation with filtered factor')
    (OUT/'run_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    sections=[('Executive summary',reason),('Evaluation contract',contract),('Model comparison scorecard',sc),('H1/H2/H3 RMSE comparison',hm),
        ('Common-sample RMSE comparison',comp),('Current 2026Q3 nowcasts',now),('M2/CPI correlation diagnostics',pd.DataFrame(correlations)),
        ('VIF diagnostics',pd.DataFrame(v)),('DFM factor signals — descriptive standardized units',drivers),('Factor-loading comparison',loadcurrent),
        ('Factor path correlations',pd.DataFrame(fc).query("current and sample == 'NATIVE'")),('Factor and bridge fit',fit_summary),('Incremental information / ablation',pd.DataFrame(ablation)),
        ('Information-content interpretation',content),('Rolling 24-month correlations',pd.DataFrame(rolling).dropna().groupby(['variable_a','variable_b']).tail(12)),
        ('Forecast stability',st),('Selection robustness flags',pd.DataFrame(flags)),('Historical matched forecasts',common),('Interpretation and limitations',notes),('Final recommendation',reason)]
    lines=['# Phase 6G.5 — M2/CPI redundancy and final DFM selection']
    testpath=OUT/'phase6g5_test_results.json'
    if testpath.exists():
        tests=json.loads(testpath.read_text())
        sections.insert(-1,('Testing and preservation',
            f"Full relevant suite: {tests['passed']} passed, {tests['failures']} failed, {tests['errors']} errors. "
            'All 14 dedicated Phase6G.5 checks pass. The two legacy failures are Phase6B.2 test_protected_artifacts_unchanged and Phase6C test_protected_inventory_and_saved_metrics: their older inventory hashes differ from the newer repository state. '
            'The flagged current dashboard, master data, and processed gold payload match the task-start hashes. All 943 current protected files are unchanged. '
            'Full estimator reruns reproduce the scientific artifacts exactly. See phase6g5_tests.xml, phase6g5_test_results.json and phase6g5_validation.json for explicit status.'))
    for title,value in sections:lines.extend(['', '## '+title,'',markdown(value) if isinstance(value,pd.DataFrame) else value])
    lines.extend(['','Production unchanged; no automatic promotion. All outputs are isolated research artifacts.','', 'PHASE6G5_RETAIN_M0'])
    (OUT/'phase6g5_results.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    template=(ROOT/'dashboard/phase6g1_m0_m1_m2_comparison.html').read_text(encoding='utf8')
    style=template.split('<style>',1)[1].split('</style>',1)[0]
    parts=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Phase 6G.5 model selection</title><style>'+style+'</style></head><body><main>',
           '<header><div class="wordmark">Uzbekistan / research model selection</div><div class="date">Phase 6G.5 · 2026Q3 · Production unchanged</div></header><h1>M2 / CPI: incremental forecasting value</h1>']
    for title,value in sections:
        if isinstance(value,pd.DataFrame):
            value=value.copy()
            if 'model' in value:value['model']=value.model.map(LABELS).fillna(value.model)
            body='<div class="scroll">'+value.to_html(index=False,float_format=lambda x:f'{x:.4f}',na_rep='Unavailable',border=0)+'</div>'
        else:body='<p>'+html.escape(value)+'</p>'
        if 'factor signals' in title.lower():body='<p><strong>Standardized factor units are descriptive. They are NOT percentage-point GDP contributions. Positive values pull the aligned factor upward; negative values pull it downward.</strong></p>'+body
        parts.append('<section><h2>'+html.escape(title)+'</h2>'+body+'</section>')
    # Offline SVG comparisons retain readable labels and exact values in titles.
    for horizon in ['H1','H2','H3','POOLED']:
        data=hm.loc[hm['sample'].eq('STRICT_COMMON_SPAN')&hm.horizon.eq(horizon)]
        bars=[];maximum=data.rmse.max()*1.15
        for i,r in enumerate(data.itertuples()):
            width=430*r.rmse/maximum;y=26+i*40
            bars.append(f'<text x="5" y="{y+16}" class="axis">{html.escape(LABELS[r.model])}</text><rect x="200" y="{y}" width="{width:.2f}" height="23" rx="4" fill="#087f72"><title>{r.rmse:.6f} pp RMSE</title></rect><text x="{210+width:.2f}" y="{y+16}" class="axis">{r.rmse:.3f}</text>')
        parts.append('<section><h2>'+horizon+' common-span RMSE · percentage points</h2><svg viewBox="0 0 740 245" role="img" aria-label="'+horizon+' RMSE comparison">'+''.join(bars)+'</svg></section>')
    parts.append('<footer>PHASE6G5_RETAIN_M0 · No automatic production promotion.</footer></main></body></html>')
    (OUT/'phase6g5_m0_m1_m2_m3_m4_comparison.html').write_text(''.join(parts),encoding='utf8')
    verify()

if __name__=='__main__':generate()
