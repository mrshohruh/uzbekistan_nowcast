"""Self-contained management dashboard; values come only from calculated outputs."""
from html import escape
import json
import numpy as np
import pandas as pd

LABELS={'industrial_production':'Industrial production','ppi':'Producer prices','usd_uzs':'USD / UZS',
        'rub_uzs':'RUB / UZS','gold_price':'World gold price','m2':'Broad money · M2',
        'fx_reserves_ex_gold':'FX reserves excluding gold','pos_turnover':'POS turnover',
        'PHASE6C_DFM':'DFM · Phase 6C','U_MIDAS':'U-MIDAS','COMBO_50_50':'50 / 50 combination',
        'COMBO_DEV_WEIGHT':'Development-weight combination','LEGACY_PRODUCTION_V1':'Legacy production V1',
        'NO_NEW_INFORMATION':'No new information','PARAMETER_REESTIMATION':'Parameter re-estimation'}


def fmt(value,digits=3):
    if value is None or pd.isna(value) or isinstance(value,(int,float)) and not np.isfinite(value):return 'Unavailable'
    return f'{value:.{digits}f}' if isinstance(value,(int,float,np.number)) else escape(str(value))


def table(frame,columns,primary=False):
    head=''.join(f'<th>{escape(label)}</th>' for key,label in columns)
    body=''
    for row in frame.to_dict('records'):
        cls='primary' if primary and row.get('production_status')=='PRIMARY' else ''
        cells=''.join(f'<td>{escape(LABELS.get(str(row.get(key)),str(row.get(key)))) if key in ("indicator","variable","model") else fmt(row.get(key))}</td>' for key,label in columns)
        body+=f'<tr class="{cls}">{cells}</tr>'
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def bars(frame,value,share=None):
    rows=frame.to_dict('records')
    scale=max([abs(r[value]) for r in rows if r[value] is not None and pd.notna(r[value])]+[1e-12])
    result='<div class="bars">'
    for r in rows:
        v=r[value];valid=v is not None and pd.notna(v)
        sign='positive' if valid and v>0 else 'negative' if valid and v<0 else 'neutral'
        size=abs(v)/scale*48 if valid else 0
        position=f'left:50%;width:{size}%' if valid and v>=0 else f'right:50%;width:{size}%'
        tooltip=' · '.join(f'{key}: {fmt(val)}' for key,val in r.items())
        result+=f'<div class="barrow" title="{escape(tooltip)}"><span>{escape(LABELS.get(r["indicator"],r["indicator"]))}</span><div class="track"><i class="{sign}" style="{position}"></i></div><b class="{sign}">{fmt(v)}</b></div>'
    return result+'</div>'


def history_chart(matched,horizon):
    f=matched.loc[matched.horizon.eq(horizon)]
    wide=f.pivot(index='target_quarter',columns='model',values='prediction')
    wide['Actual GDP']=f.groupby('target_quarter').actual.first()
    columns=['Actual GDP','COMBO_50_50','U_MIDAS','PHASE6C_DFM']
    colors=['#172940','#087f72','#d69a24','#6579b6']
    low=float(wide[columns].min().min())-.2;high=float(wide[columns].max().max())+.2
    n=len(wide);svg='<svg viewBox="0 0 900 280" role="img" aria-label="Actual GDP and matched historical nowcasts">'
    for y in np.linspace(low,high,5):
        sy=235-(y-low)/(high-low)*195
        svg+=f'<path d="M55 {sy} H865" stroke="#e1e8ee"/><text x="15" y="{sy+4}" class="axis">{y:.1f}%</text>'
    for key,color in zip(columns,colors):
        points=[]
        for i,(q,row) in enumerate(wide.iterrows()):
            x=65+i/max(n-1,1)*780;y=235-(float(row[key])-low)/(high-low)*195
            points.append(f'{x},{y}')
            svg+=f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"><title>{q} · {LABELS.get(key,key)}: {row[key]:.4f}%</title></circle>'
        svg+=f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2.5"/>'
    for i,q in enumerate(wide.index):svg+=f'<text x="{65+i/max(n-1,1)*780}" y="267" text-anchor="middle" class="axis">{q}</text>'
    return svg+'</svg>'


def render(current,comparison,loadings,drivers,terms,news,matched,freshness,revision_history):
    c=current
    signal=drivers.loc[drivers.source_model.eq('PHASE6C_DFM')]
    fx=drivers.loc[drivers.source_model.eq('U_MIDAS')]
    final_news=news.loc[news.source_model.eq('COMBO_50_50')]
    latest=final_news.loc[final_news.new_as_of_date.eq(final_news.new_as_of_date.iloc[-1])] if len(final_news) else final_news
    revision=(f'<div class="cards"><div>Previous<b>{fmt(latest.old_forecast.iloc[0],6)}%</b></div><div>Current<b>{fmt(latest.new_forecast.iloc[0],6)}%</b></div><div>Revision<b>{fmt(latest.total_revision_pp.iloc[0],8)} pp</b></div></div>'+bars(latest,'news_impact_pp')+
              '<p class="note">Exact fixed-parameter Shapley contributions; refitting is shown separately when material. DFM and U-MIDAS channels combine at 50 / 50.</p>') if len(latest) else '<p>No comparable previous real-time vintage available</p>'
    shares=loadings[['indicator','normalized_loading_share_pct']].rename(columns={'normalized_loading_share_pct':'share'})
    loading_bars=''.join(f'<div class="loadingrow"><span>{escape(LABELS[r.indicator])}</span><div><i style="width:{r.share}%"></i></div><b>{r.share:.1f}%</b></div>' for r in shares.itertuples())
    plots=''.join(f'<div class="historical" id="chart-{h}" {"hidden" if h!="H3" else ""}>{history_chart(matched,h)}</div>' for h in ['H1','H2','H3'])
    metrics_table=table(comparison,[('model','Model'),('production_status','Status'),('rmse','RMSE · pp'),('mae','MAE · pp'),('bias','Bias · pp'),('r2','R²'),('r2_os_vs_ar1','R² OS vs AR(1)'),('H1_rmse','H1 RMSE'),('H2_rmse','H2 RMSE'),('H3_rmse','H3 RMSE')],True)
    term_table=table(terms,[('term','Actual term'),('observation_period','Observation period'),('coefficient','Coefficient'),('regressor_value','Current regressor'),('contribution_pp','Contribution · pp')])
    driver_table=table(drivers,[('indicator','Indicator'),('source_model','Model'),('metric_type','Measure'),('direction','Direction'),('contribution_or_signal','Signal / pp'),('normalized_share_pct','Within-measure share · %'),('latest_period','Latest period'),('transformation','Transformation')])
    freshness_table=table(freshness,[('variable','Indicator'),('latest_usable_month','Latest observation'),('release_update_date','Observed release / update'),('status','Status')])
    revision_table=table(revision_history,[('as_of_date','As-of'),('target_quarter','Target'),('horizon','Horizon'),('production_model','Model'),('DFM_forecast','DFM'),('UMIDAS_forecast','U-MIDAS'),('final_forecast','Final'),('change_from_previous','Revision · pp')])
    headline=fmt(c['final_forecast'],2)
    promoted=c['status']=='PHASE6E_PROMOTED'
    model_label='50% DFM + 50% U-MIDAS' if promoted else 'Legacy production V1 · promotion blocked'
    badge='Historical holdout promoted; prospective validation pending' if promoted else 'Promotion blocked · legacy production retained'
    html=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Uzbekistan GDP Nowcast</title>
<style>
:root{{--ink:#172940;--muted:#69788b;--green:#087f72;--red:#ba5464;--line:#e2e8ee}}*{{box-sizing:border-box}}body{{margin:0;background:#f3f6f9;color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}}main{{max-width:1280px;margin:auto;padding:36px 32px 70px}}header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:26px}}.wordmark{{font-weight:700;letter-spacing:.1em;font-size:13px;text-transform:uppercase}}.date{{color:var(--muted);font-size:13px}}h1{{font-size:30px;letter-spacing:-.03em;margin:0}}h2{{font-size:21px;letter-spacing:-.02em;margin:0 0 8px}}h3{{font-size:16px;margin:12px 0}}p{{margin:8px 0 16px}}.hero{{background:linear-gradient(120deg,#142e48,#1b4b5d);color:#fff;border-radius:22px;padding:38px;display:grid;grid-template-columns:1.2fr 1fr;gap:25px}}.eyebrow{{text-transform:uppercase;letter-spacing:.12em;font-size:12px;color:#b7d5dc}}.headline{{font-size:88px;line-height:1.2;letter-spacing:-.055em;font-weight:650;margin:8px 0}}.headline small{{font-size:40px}}.badge{{display:inline-block;padding:6px 11px;border:1px solid #7696a3;border-radius:20px;font-size:11px;color:#e2ecf0}}.herometa{{align-self:center;border-left:1px solid #537281;padding-left:32px}}.herometa strong{{display:block;margin-bottom:14px;font-size:16px}}.herometa span{{font-size:12px;color:#b7d5dc}}section{{background:#fff;border:1px solid var(--line);border-radius:18px;margin-top:22px;padding:28px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:18px 0}}.cards>div{{background:#f4f7f9;border-radius:12px;padding:18px;color:var(--muted);font-size:13px}}.cards b{{display:block;font-size:29px;color:var(--ink);font-weight:650}}.cards .accent{{background:#e4f3ef}}.formula{{font-size:16px;font-weight:600;color:var(--green)}}.note{{font-size:12px;color:var(--muted)}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}.two>section{{min-width:0}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:12px}}th{{color:var(--muted);font-size:11px;text-align:left;font-weight:600}}td,th{{padding:12px 10px;border-bottom:1px solid var(--line)}}td{{font-variant-numeric:tabular-nums}}tr.primary{{background:#e4f3ef;font-weight:600}}.bars{{margin:20px 0}}.barrow{{display:grid;grid-template-columns:190px 1fr 75px;align-items:center;gap:12px;padding:9px 0;font-size:12px}}.track{{height:22px;position:relative;background:linear-gradient(to right,transparent calc(50% - .5px),#ccd8e0 50%,transparent calc(50% + .5px))}}.track i{{position:absolute;top:3px;height:16px;border-radius:3px}}i.positive{{background:var(--green)}}i.negative{{background:var(--red)}}b.positive{{color:var(--green)}}b.negative{{color:var(--red)}}b.neutral{{color:var(--muted)}}.loadingrow{{display:grid;grid-template-columns:190px 1fr 52px;gap:12px;align-items:center;font-size:12px;margin:14px 0}}.loadingrow>div{{height:12px;background:#f1f5f8;border-radius:3px}}.loadingrow i{{display:block;background:#6579b6;height:12px;border-radius:3px}}svg{{width:100%;height:auto}}.axis{{font:12px system-ui;fill:#69788b}}select{{padding:6px;border:1px solid var(--line);border-radius:6px;color:var(--ink)}}.legend{{display:flex;gap:20px;flex-wrap:wrap;font-size:12px}}.legend i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}}details{{margin-top:15px}}summary{{cursor:pointer;color:var(--green);font-size:13px}}footer{{font-size:12px;color:var(--muted);margin-top:24px}}@media(max-width:850px){{main{{padding:20px 14px}}.hero,.two{{grid-template-columns:1fr}}.herometa{{border-left:0;padding:0}}.headline{{font-size:70px}}.cards{{grid-template-columns:1fr}}.barrow,.loadingrow{{grid-template-columns:140px 1fr 60px}}header{{display:block}}section{{padding:20px}}}}
</style></head><body><main><header><div class="wordmark">Economic monitoring / Uzbekistan</div><div class="date">Production V2 · Phase 6E · As-of {escape(c['as_of_date'])}</div></header>
<div class="hero"><div><div class="eyebrow">{escape(c['target_quarter'])} Real GDP Growth Nowcast</div><h1>Uzbekistan GDP Nowcast</h1><div class="headline" data-nowcast="{c['final_forecast']:.17g}">{headline}<small>%</small></div><span class="badge">{badge}</span></div>
<div class="herometa"><span>Production model</span><strong>{model_label}</strong><span>Current stage</span><strong>{escape(c['horizon'])} · {escape(c['stage'].replace('_',' ').title())}</strong><span>Last data update</span><strong>{escape(c['last_data_update'])}</strong><span>Historical-error reference range · ±1 RMSE</span><strong>{fmt(c['historical_error_reference_range'][0],2)}% – {fmt(c['historical_error_reference_range'][1],2)}%</strong><span>Indicative range; not a formal confidence interval</span></div></div>
<section><h2>Two perspectives. One nowcast.</h2><div class="cards"><div>DFM component<b>{fmt(c['dfm_forecast'],4)}%</b></div><div>U-MIDAS component<b>{fmt(c['umidas_forecast'],4)}%</b></div><div class="accent">Final combination<b>{fmt(c['combo_50_50_forecast'],4)}%</b></div></div><p class="formula">Final = 0.50 × DFM + 0.50 × U-MIDAS</p><p class="note">DFM summarizes eight monthly economic indicators. U-MIDAS combines timely exchange-rate information with GDP persistence. Combining them reduces dependence on a single signal.</p></section>
<section><h2>What is driving the current nowcast?</h2><p class="note">Green supports the factor signal; red weakens it. Hover for the data period, transformation and model. Model associations do not imply causality.</p><h3>DFM factor signals · descriptive standardized units</h3>{bars(signal,'contribution_or_signal')}<p class="note">Mean of released target-quarter standardized observations × factor loading. These signals do not add to GDP growth. POS has no released target-quarter observation; its signal is unavailable.</p><h3>U-MIDAS exchange-rate channel · exact forecast contribution in pp</h3>{bars(fx,'contribution_or_signal')}<p class="note">The three FX lag contributions are aggregated within U-MIDAS. DFM USD/UZS and U-MIDAS USD/UZS use distinct units and are displayed in separate labelled channels. Within-measure shares use separate denominators.</p><details><summary>View driver observations and transformations</summary>{driver_table}</details></section>
<section><h2>What changed since the previous update?</h2>{revision}</section>
<div class="two"><section><h2>Share of absolute DFM factor loading</h2><p class="note">These are factor loadings, not causal GDP effects.</p>{loading_bars}<p class="note">One latent factor · AR(2) state dynamics · Kalman likelihood · Bridge B · quarterly mean. Standardization uses pre-target training data.</p></section><section><h2>U-MIDAS structure</h2><p class="note">Actual fitted coefficients × current transformed regressors.</p>{term_table}<p class="formula">Sum = {fmt(terms.contribution_pp.sum(),6)}% = U-MIDAS prediction</p><p class="note">The intercept and lagged GDP enter the exact decomposition alongside the three unrestricted monthly FX lag terms.</p></section></div>
<section><h2>Matched historical model performance</h2><p class="note">12 identical origins · four holdout quarters · first-release GDP · standard release lags · STRICT GDP boundary. Bias = actual − prediction.</p>{metrics_table}<p class="note">The 50 / 50 and development-weight combinations perform nearly identically. Historical predictor releases use registry lag rules where complete historical observed vintages are unavailable.</p></section>
<section><h2>Actual GDP vs nowcast</h2><label>Horizon <select id="horizon"><option>H3</option><option>H2</option><option>H1</option></select></label>{plots}<div class="legend"><span><i style="background:#172940"></i>Actual GDP</span><span><i style="background:#087f72"></i>Primary combination</span><span><i style="background:#d69a24"></i>U-MIDAS</span><span><i style="background:#6579b6"></i>DFM</span></div></section>
<section><h2>Production input freshness</h2>{freshness_table}<p class="note">Unknown release dates remain unavailable. Retrieval and horizon gates remain active; unreleased monthly data are excluded. POS scope is verified only through December 2024.</p></section>
<section><h2>Production revision history</h2>{revision_table}<p class="note">Append-only ledger. Identical input fingerprints and forecasts do not create duplicate entries.</p></section>
<footer>Production V2 / Phase 6E · Promotion basis: matched historical holdout superiority · {c['prospective_realizations']} prospective realized quarters · Prospective validation pending. GDP target: published cumulative year-to-date real growth (January–September for Q3). Legacy production remains available for rollback. All visualizations are embedded and open locally.</footer></main>
<script>document.getElementById('horizon').addEventListener('change',e=>{{document.querySelectorAll('.historical').forEach(x=>x.hidden=x.id!=='chart-'+e.target.value)}});</script></body></html>'''
    if 'nan' in html.lower().split() or '>NaN<' in html or '>inf<' in html:raise ValueError('Nonfinite value in dashboard')
    return html
