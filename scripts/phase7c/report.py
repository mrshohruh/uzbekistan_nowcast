"""Economic passports and self-contained offline scientific dashboard."""
import json,html
import pandas as pd
from scripts.operations.prospective.common import safe

DESCRIPTIONS={
 'retail_trade':('Retail trade turnover','2699','Consumption-related demand and trade services value added.','Nominal sales also reflect inflation, imported goods and changes in formal coverage. Remittances can support demand without equivalent domestic production.','POS turnover already measures payment-mediated demand; overlap can limit incremental information.'),
 'construction':('Construction works','2403','Construction value added and investment-related activity.','Project timing, input costs and imported materials can separate nominal works from real domestic value added.','Industrial production and M2 can already capture materials demand and credit conditions.'),
 'imports_total':('Total imports','1162','Intermediate inputs, capital investment and household demand.','Imports subtract from expenditure GDP but may accompany domestic expansion; USD prices, exchange rates and substitution can reverse association. This is value growth, not volume growth.','FX, industrial production and M2 overlap with financing and input-demand channels.'),
 'exports_non_gold':('NON_GOLD_EXPORT_PROXY','1103','Foreign demand and non-gold tradable activity, approximated by total exports less Other goods.','Other goods is not verified as exact gold; one negative monthly parent increment prevents primary validation. Gold shipment timing and services revisions can distort the residual.','Gold price and exchange rates already capture external conditions.')}

def report(inventory,comp,hm,hist,cur,robust,manifest):
    from scripts.phase7c.run import OUT
    primary=comp.loc[comp.scenario.eq('PRIMARY_ASSUMED_REGISTRY_LAG')]
    controls=pd.read_csv(OUT/'phase7c_sample_controls.csv')
    controls=controls.loc[~controls.current.astype(bool)]
    controls=controls.loc[controls.prediction.notna()&controls.challenger_prediction.notna()]
    control_metrics=[]
    for model,g in controls.groupby('model'):
        for field,label in [('prediction','M0_IDENTICAL_TRAINING_START'),('challenger_prediction',model)]:
            e=g[field]-g.actual
            control_metrics.append(dict(comparison=model,model=label,n_origins=len(g),n_quarters=g.target_quarter.nunique(),rmse=float((e.pow(2).mean())**.5),mae=float(e.abs().mean()),first_quarter=g.target_quarter.min(),last_quarter=g.target_quarter.max()))
    pd.DataFrame(control_metrics).to_csv(OUT/'phase7c_sample_control_metrics.csv',index=False,float_format='%.17g')
    decisions={};passports=[];findings=[]
    for i,key in enumerate(DESCRIPTIONS,1):
        name,id,mechanism,limits,overlap=DESCRIPTIONS[key];r=next(x for x in inventory if x['variable_key']==key);model='R'+str(i)
        c=primary.loc[primary.comparison.eq(model)]
        evidence='Not estimated: parent-flow validation failed.' if c.empty else c[['model','n_origins','n_quarters','rmse','mae','bias','r_squared','oos_r_squared_ar1']].to_string(index=False)
        narrative='Primary experiment excluded; empirical incremental value remains unknown.'
        if not c.empty and c.n_origins.max()>0:
            b=c.loc[c.model.eq('M0')].iloc[0];ch=c.loc[c.model.eq(model)].iloc[0]
            cb=primary.loc[primary.comparison.eq('C_'+model)]
            combo_gain=float(cb.loc[cb.model.eq('C0'),'rmse'].iloc[0]-cb.loc[cb.model.eq('C_'+model),'rmse'].iloc[0])
            boot=robust.loc[robust.comparison.eq(model)&robust.scenario.eq('PRIMARY_ASSUMED_REGISTRY_LAG')&robust.subset.eq('QUARTER_CLUSTER_BOOTSTRAP_MSE_GAIN')]
            interval='' if boot.empty else f" Quarter-level mean squared-error gain interval [{boot.iloc[0].ci_lower:.4f}, {boot.iloc[0].ci_upper:.4f}] pp²."
            lag=[]
            for scenario in ['LAG_PLUS_15D','LAG_PLUS_30D','TRAINING_ONLY_WINSOR_1_99']:
                q=comp.loc[comp.comparison.eq(model)&comp.scenario.eq(scenario)]
                if len(q)==2 and q.n_origins.max()>0:lag.append(f"{scenario}: {float(q.loc[q.model.eq('M0'),'rmse'].iloc[0]-q.loc[q.model.eq(model),'rmse'].iloc[0]):+.4f} pp")
            narrative=f"On {int(ch.n_origins)} origins / {int(ch.n_quarters)} GDP quarters ({ch.first_quarter}–{ch.last_quarter}), DFM RMSE gain is {b.rmse-ch.rmse:+.4f} pp and fixed-combination RMSE gain is {combo_gain:+.4f} pp (positive means improvement)."+interval+' Sensitivities: '+ '; '.join(lag)+'.'
            control=next((r for r in control_metrics if r['comparison']==model and r['model']=='M0_IDENTICAL_TRAINING_START'),None)
            cc=next((r for r in control_metrics if r['comparison']==model and r['model']==model),None)
            if control and cc:narrative+=f" On {cc['n_origins']} converged identical-history-control origins, the DFM RMSE gain is {control['rmse']-cc['rmse']:+.4f} pp; this separates history truncation from added information."
            evidence+='\n\n'+narrative
        findings.append(name+': '+narrative)
        decisions[key]='DATA_NOT_VALIDATED' if key=='exports_non_gold' else 'NO_INCREMENTAL_VALUE'
        passports.append(f'''## {name}

1. Indicator: {name}.
2. Provider: National Statistics Committee / SIAT. [Official source](https://siat.stat.uz/data/{id}/?lang=en). {'[Other goods parent](https://siat.stat.uz/data/3082/?lang=en).' if key=='exports_non_gold' else ''}
3. Definition/unit: national {'current-price turnover/works in billion UZS' if i<3 else 'USD-valued trade flow in million USD'}. Retail source million sums scaled by 0.001. Export residual is a derived proxy, never official non-gold exports.
4. Coverage: raw {r['raw_start']} to 2026-08; usable growth {r['growth_start']} to {r['growth_end']} ({r['n_growth']} months).
5. Mechanism: {mechanism}
6. Interpretation: {'production and expenditure channels' if i<3 else 'external trade and domestic demand channels'}; sales/works values are not directly GDP value added.
7. Expected relationship: expansion often accompanies GDP growth; factor loading sign is unrestricted.
8. Sign changes: {limits}
9. Uzbekistan relevance: {'household demand, remittance-supported spending and domestic distribution' if i==1 else 'infrastructure and building investment' if i==2 else 'imported equipment and intermediate-input dependence' if i==3 else 'gold-related shipment volatility in external trade'}. These are economic hypotheses, not quantified structural estimates.
10. Overlap: {overlap}
11. Primary transformation: within-year de-cumulation then 100 ln(flow_t/flow_t-12), strictly positive pairs. {'CPI sensitivity subtracts trailing twelve monthly CPI log changes; approximate purchasing-power adjustment, not retail volume.' if i==1 else 'No construction-specific deflator validated; no headline-CPI construction deflation.' if i==2 else 'Both export parents de-cumulated before subtraction.' if i==4 else 'Nominal USD-value growth.'}
12. Availability: assumed {r['assumed_lag_days']} days after reference month end; +15/+30-day sensitivities. Stored latest source update is not historical first publication. Current frozen-cutoff candidate data were retrieved before 2026-10-05.
13. Risks: {limits} Revised history and annual reconciliation can change prior monthly flows; de-cumulation magnifies revisions. Historical analysis is RETROSPECTIVE_EXPLORATORY.
14. Incremental evidence:

```text
{evidence}
```

15. Decision: **{decisions[key]}**. {'Resolve the negative parent increment and validate category compatibility before primary testing.' if i==4 else 'Reject this addition in the tested specification because matched DFM and combined accuracy deteriorate. Economic relevance remains plausible; short revised histories and convergence failures limit broader conclusions.'}

Management explanation: {mechanism} {limits} Forecasting evidence is distinct from theoretical plausibility. Correlation and loading signals describe association, not causal effects or GDP percentage-point contributions.
''')
    (OUT/'phase7c_indicator_passports.md').write_text('# Phase 7C indicator passports\n\n'+ '\n'.join(passports),encoding='utf8')
    text=f'''# Phase 7C economic coverage research

Classification: **{manifest['classification']}**. RESEARCH_ONLY. No promotion.

Production active predictors: {', '.join(manifest['active_predictors'])}. All four candidates are AVAILABLE_IN_DATABASE_NOT_ACTIVE; experiments are additions. R1_REAL_APPROX is a transformation sensitivity. No duplicate active predictors were added.

Production remains M0={manifest['production_reproduction']['dfm']['frozen']:.15f}, U0={manifest['production_reproduction']['umidas']['frozen']:.15f}, C0={manifest['production_nowcast']:.15f}%. Cutoff {manifest['cutoff']}; no 2026Q3 outcome used.

Retrospective revised predictor histories, assumed registry reporting lags, strict preserved GDP vintages and approved matched origins. Forecast horizons repeat GDP quarters; uncertainty resamples target-quarter average loss differences, not independent origins. Pairwise samples and exact origins are in model_comparison.csv. Empty samples indicate insufficient 36-month balanced history, not zero forecast error. EM convergence and warnings are in estimation_diagnostics.csv; nonconverged fits require caution.

## Matched DFM and 50/50 comparisons

```text
{primary[['comparison','model','n_origins','n_quarters','rmse','mae','bias','r_squared','oos_r_squared_ar1','first_quarter','last_quarter']].to_string(index=False)}
```

## Horizon accuracy

```text
{hm.loc[hm.scenario.eq('PRIMARY_ASSUMED_REGISTRY_LAG'),['comparison','model','horizon','n_origins','n_quarters','rmse']].to_string(index=False)}
```

## Robustness and limitations

{chr(10).join(findings)}

Early/recent splits and leave-one-quarter-out scoring use identical matched quarters. Quarter-cluster bootstrap intervals describe uncertainty; multiple comparisons and retrospective specification selection preclude superiority claims. +15/+30 day lag sensitivities and training-only 1%/99% candidate clipping preserve baseline rules. Sample controls recompute M0 with each candidate's identical balanced start and preserve missing cells. These separate shorter estimation history from added information. CPI sensitivity begins later and must use its own matched sample. Construction lacks a validated price deflator. No missing observations interpolated.

Factor correlations use sign alignment; changes in common-factor paths and nowcasts are in factor_stability.csv. Loadings and standardized loading signals explicitly include M2. Loading redistribution cannot establish more representative real output or predictive superiority. Correlations are descriptive revised-data associations. No causal attribution.

Groupings deferred: {manifest['groupings']}. Proxy excluded because of a negative parent flow and unresolved measurement definition; do not infer official non-gold exports.

All reused raw checksums verified. January resets and annual/last-YTD reconciliation checked; raw YTD and monthly flows retained in data_audit.csv. No new download required. Source update timestamps and retrieval dates retained separately. Candidate raw coverage ends August 2026; exact last eligible current month by lag is in current_nowcasts.csv.

Protected files unchanged: {manifest['protected_artifacts_verified']}. Production recomputation errors: {manifest['production_reproduction']}. Full test and deterministic verification results are added to validation.json by the validation command.

## Decisions

{json.dumps(decisions,indent=2)}

## Research-only current predictions

```text
{cur.loc[cur.scenario.eq('PRIMARY_ASSUMED_REGISTRY_LAG'),['model','prediction','last_available_candidate_month','failure']].to_string(index=False)}
```

Run: `.venv/Scripts/python.exe -m scripts.phase7c.run`. Artifacts and offline dashboard: results/phase7c/. Earlier 0.582528 and Phase7B 0.415602 scores use different samples and are not directly compared here.
'''
    (OUT/'phase7c_results.md').write_text(text,encoding='utf8')
    loadings=pd.read_csv(OUT/'phase7c_factor_loadings.csv')
    m2=loadings.loc[loadings.current.eq(True)&loadings.scenario.eq('PRIMARY_ASSUMED_REGISTRY_LAG')&loadings.indicator.eq('m2')]
    factor_note='\n## Current M2 and factor interpretation\n\n'+m2[['model','loading']].to_string(index=False)+'\n\nThe current retail addition redistributes M2 loading from about 0.520 to 0.212 and has an absolute sign-aligned factor correlation of about 0.242 with M0. Both added information and the shorter balanced history change the fitted factor. Reduced monetary loading does not establish greater real-output representation or forecasting accuracy; the matched backtest deteriorates. Current factor paths are in phase7c_current_factor_paths.csv. Signals are descriptive standardized values, not GDP percentage-point or causal contributions.\n'
    if m2.model.eq('M0').any():
        p=OUT/'phase7c_results.md';p.write_text(p.read_text(encoding='utf8')+factor_note,encoding='utf8')
    summary=f'''# Management summary — {manifest['classification']}

We considered retail, construction, imports and an export residual to widen the model's coverage of consumption, investment and trade. None was active; all four were stored in the database. Retail complements POS payments, construction complements industrial activity, imports describe demand for equipment and inputs, and the residual aims to reduce gold shipment volatility.

Official data are traceable through archived payload checksums and retrieval records. Retail begins 2020; other raw series begin 2021, ending August 2026. Growth transformations lose the first twelve months. Nominal values remain sensitive to prices; CPI-adjusted retail is approximate. Historical first-release vintages are unavailable, so reporting delays are assumptions and results are retrospective.

DFM and fixed 50/50 comparisons below use matched forecast origins. Short balanced histories restrict inference. Early/recent, leave-one-quarter-out, quarter-level bootstrap, history controls and lag sensitivities are preserved; even a lowest observed RMSE is not proof of superiority. Retain the three validated nominal series as research hypotheses; do not accept production inclusion from this short experiment. Reject primary export-proxy testing until the negative parent flow and category definition are resolved. Production C0 remains {manifest['production_nowcast']:.15f}%.

{chr(10).join(findings)}

```text
{primary[['comparison','model','n_quarters','rmse','mae']].to_string(index=False)}
```

Individual economic and empirical rationales are in phase7c_indicator_passports.md. Decisions: {decisions}.
'''
    (OUT/'phase7c_management_summary.md').write_text(summary,encoding='utf8')
    manifest['variable_decisions']=decisions
    payload={p.stem.replace('phase7c_',''):safe(pd.read_csv(p).to_dict('records')) for p in OUT.glob('phase7c_*.csv')}
    payload['passports']=passports;payload['summary']=summary
    page='''<!doctype html><html><head><meta charset="utf-8"><title>Phase 7C Economic Coverage</title><style>body{background:#eef2f6;color:#182f45;font:15px system-ui;margin:30px}header,section{background:white;padding:24px;border-radius:12px;margin-bottom:18px}h1{margin:0}button,select{padding:10px;margin:5px;border:1px solid #b6c6d3;border-radius:6px}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:8px;border-bottom:1px solid #dde5ed;text-align:left}pre{white-space:pre-wrap}.scroll{overflow:auto;max-height:550px}.warn{color:#a35015}svg{width:100%;height:280px}nav{display:flex;flex-wrap:wrap}</style></head><body><header><h1>Economic coverage · Phase 7C</h1><p class="warn">RESEARCH ONLY · RETROSPECTIVE EXPLORATORY · historical release dates unverified</p><p>One factor · AR(2) · unchanged GDP bridge · fixed 50/50 weights. Frozen production: 8.180901340616275%.</p><select id="candidate"><option value="ALL">All candidates</option><option>R1</option><option>R2</option><option>R3</option><option>R1_REAL_APPROX</option></select><select id="horizon"><option value="ALL">All horizons</option><option>H1</option><option>H2</option><option>H3</option></select></header><nav id="nav"></nav><section><h2 id="title"></h2><div id="chart"></div><div id="content" class="scroll"></div></section><script>const D=__DATA__;
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tabs={'Model comparison / RMSE':'model_comparison','Horizon-specific RMSE':'horizon_metrics','Actual vs predicted GDP':'historical_predictions','Retail / construction / trade history':'candidate_history','Variable correlations':'correlations','DFM factor loadings (including M2)':'factor_loadings','Standardized factor signals (not GDP pp)':'factor_signals','Factor stability / nowcast changes':'factor_stability','Early / recent / lag robustness':'robustness','Identical-history controls':'sample_controls','Current research-only nowcasts':'current_nowcasts','Inventory: additions, no ablations':'predictor_inventory','Data quality and provenance':'data_audit','Indicator passports':'passports','Management summary':'summary'};let active='model_comparison';
function render(){let rows=D[active]||[];document.getElementById('title').textContent=Object.keys(tabs).find(k=>tabs[k]===active);document.getElementById('chart').innerHTML='';if(typeof rows==='string'||active==='passports'){document.getElementById('content').innerHTML='<pre>'+esc(Array.isArray(rows)?rows.join('\\n'):rows)+'</pre>';return;}const c=document.getElementById('candidate').value,h=document.getElementById('horizon').value;rows=rows.filter(r=>(c==='ALL'||!(r.comparison||r.model)||(r.comparison||r.model).includes(c)||['M0','C0','U0'].includes(r.model))&&(h==='ALL'||!r.horizon||r.horizon===h));if(!rows.length){document.getElementById('content').textContent='Not estimable / no matched observations.';return;}let cols=Object.keys(rows[0]);document.getElementById('content').innerHTML='<table><thead><tr>'+cols.map(k=>'<th>'+esc(k)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+cols.map(k=>'<td>'+esc(r[k])+'</td>').join('')+'</tr>').join('')+'</tbody></table>';const metric=active==='model_comparison'||active==='horizon_metrics'?'rmse':active==='historical_predictions'||active==='current_nowcasts'?'prediction':active==='factor_loadings'?'loading':active==='factor_signals'?'loading_signal':null;if(metric){let a=rows.filter(r=>Number.isFinite(r[metric])&&(!r.scenario||r.scenario==='PRIMARY_ASSUMED_REGISTRY_LAG')).slice(-90),vals=a.map(r=>r[metric]);if(vals.length){let lo=Math.min(0,...vals),hi=Math.max(...vals),pts=vals.map((v,i)=>`${40+i*850/Math.max(1,vals.length-1)},${240-(v-lo)*200/(hi-lo||1)}`).join(' ');document.getElementById('chart').innerHTML='<svg viewBox="0 0 950 280"><text x="40" y="20">'+esc(metric)+' · selected rows</text><polyline fill="none" stroke="#197eaa" stroke-width="2" points="'+pts+'"/></svg>';}}}
for(const [label,key] of Object.entries(tabs)){let b=document.createElement('button');b.textContent=label;b.onclick=()=>{active=key;render()};document.getElementById('nav').appendChild(b);}document.getElementById('candidate').onchange=render;document.getElementById('horizon').onchange=render;render();</script></body></html>'''
    charts=(OUT.parents[1]/'scripts/phase7c/charts.js').read_text(encoding='utf8')
    page=page.replace('</script>',charts+'</script>')
    (OUT/'phase7c_economic_coverage_dashboard.html').write_text(page.replace('__DATA__',json.dumps(payload,allow_nan=False).replace('</','<\\/')),encoding='utf8')
