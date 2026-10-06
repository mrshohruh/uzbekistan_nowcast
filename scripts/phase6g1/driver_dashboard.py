"""Refit the frozen current D0/D2 designs and render a research-only driver panel."""
from html import escape
import json
import re
import numpy as np
import pandas as pd
from scripts.phase6g1.run import ROOT
from scripts.phase6g.run import production_info
from scripts.phase6e.models import frames,dfm,sw
from scripts.phase6e.dashboard import LABELS,fmt
from scripts.phase6f.experiment import lagged_dfm,sha,dump
from uznowcast.models.data import quarter_start

OUT=ROOT/'results/phase6g1'
HTML=ROOT/'dashboard/phase6g1_m2_lag_driver_dashboard.html'
COLUMNS=['model','indicator','display_name','latest_period','latest_factor_cell_period','latest_value',
         'quarter_months_available','quarter_mean_z','loading','signal','direction','normalized_share_pct',
         'loading_share_pct','transformation','interpretation','decomposition_type']

def calculate(fit,model,target,transformations):
    """Scale only on pre-target training data; retain missing quarter measurements."""
    end=quarter_start(target)-pd.Timedelta(days=1)
    z,mean,sd=sw.common.kernel().standardize(fit['frame'],end,False)
    loading=pd.Series(fit['loadings'],index=z.columns)
    # Estimator aligns its largest absolute loading positive. Explicitly retain
    # that orientation without substituting another model's loadings or scaling.
    alignment=1. if loading.loc[loading.abs().idxmax()]>=0 else -1.
    loading=loading*alignment
    rows=[]
    for indicator in z:
        observed=z[indicator].dropna()
        quarter=observed.loc[observed.index.to_period('Q')==pd.Period(target,'Q')]
        cell=observed.index.max().to_period('M') if len(observed) else None
        source=cell-2 if cell is not None and model=='D2' and indicator=='m2' else cell
        qmean=float(quarter.mean()) if len(quarter) else np.nan
        signal=qmean*loading[indicator]
        direction='unavailable' if pd.isna(signal) else 'positive' if signal>0 else 'negative' if signal<0 else 'neutral'
        rows.append(dict(model=model,indicator=indicator,
            display_name='Broad money · M2 (2-month lag)' if model=='D2' and indicator=='m2' else LABELS[indicator],
            latest_period=str(source) if source is not None else None,
            latest_factor_cell_period=str(cell) if cell is not None else None,
            latest_value=float(fit['frame'].loc[observed.index.max(),indicator]) if len(observed) else np.nan,
            quarter_months_available=len(quarter),quarter_mean_z=qmean,loading=float(loading[indicator]),signal=signal,
            direction=direction,loading_share_pct=float(100*abs(loading[indicator])/loading.abs().sum()),
            transformation='100*ln(M2_t/M2_t-12)' if indicator=='m2' else transformations[indicator],
            interpretation='No released target-quarter measurement' if direction=='unavailable' else
                'Supporting factor signal' if direction=='positive' else 'Weakening factor signal' if direction=='negative' else 'Neutral factor signal',
            decomposition_type='loading-based descriptive'))
    result=pd.DataFrame(rows)
    denominator=result.signal.abs().sum(min_count=1)
    result['normalized_share_pct']=100*result.signal.abs()/denominator if denominator>0 else np.nan
    return result[COLUMNS].sort_values('signal',key=lambda s:s.abs(),ascending=False,na_position='last').reset_index(drop=True),mean,sd

def bars(frame,fx=False):
    """Phase 6E bar geometry and formatting with explicit source/cell tooltips."""
    scale=max(frame.signal.abs().max(),1e-12)
    result='<div class="bars">'
    for r in frame.to_dict('records'):
        v=r['signal'];valid=pd.notna(v);sign=r['direction'] if valid else 'neutral'
        width=abs(v)/scale*48 if valid else 0
        position=f'left:50%;width:{width}%' if valid and v>=0 else f'right:50%;width:{width}%'
        tooltip=[f"Data period: {fmt(r.get('latest_period'))}",f"Transformation: {r['transformation']}"]
        if not fx:
            if r['indicator']=='m2':tooltip += [f"Underlying M2 period: {r['latest_period']}",f"Factor-cell period: {r['latest_factor_cell_period']}",
                'Lag treatment: shifted two months in the DFM factor design']
            tooltip += [f"Quarter mean z: {fmt(r['quarter_mean_z'],9)}",f"Loading: {fmt(r['loading'],9)}",f"Signal: {fmt(v,9)}",
                        f"Signal share: {fmt(r['normalized_share_pct'],4)}%",f"Loading share: {fmt(r['loading_share_pct'],4)}%"]
        else:tooltip += [f"Exact forecast contribution in pp: {fmt(v,9)}"]
        title=escape(' · '.join(tooltip),quote=True)
        result+=f'<div class="barrow" title="{title}" data-indicator="{r["indicator"]}"><span>{escape(r["display_name"])}</span><div class="track"><i class="{sign}" style="{position}"></i></div><b class="{sign}">{fmt(v)}</b></div>'
    return result+'</div>'

def finite_records(frame):
    return json.loads(frame.to_json(orient='records',double_precision=15))

def render(d0,d2,now,fx,style,metadata):
    m0=d0.set_index('indicator').loc['m2'];m2=d2.set_index('indicator').loc['m2']
    u=float(now['U_MIDAS'])
    comparison=[('DFM nowcast',fmt(now['D0'],4),fmt(now['D2'],4)),('U-MIDAS',fmt(u,4),fmt(u,4)),
        ('50/50 nowcast',fmt(.5*(now['D0']+u),4),fmt(.5*(now['D2']+u),4)),
        ('M2 loading share · descriptive factor statistic',fmt(m0.loading_share_pct,2)+'%',fmt(m2.loading_share_pct,2)+'%'),
        ('M2 signal share · descriptive factor statistic',fmt(m0.normalized_share_pct,2)+'%',fmt(m2.normalized_share_pct,2)+'%')]
    table='<div class="scroll"><table><thead><tr><th>Measure</th><th>Current M2</th><th>M2-L2</th></tr></thead><tbody>'+''.join(
        f'<tr><td>{escape(label)}</td><td>{a}</td><td>{b}</td></tr>' for label,a,b in comparison)+'</tbody></table></div>'
    payload=dict(metadata=metadata,nowcasts=now,D0=finite_records(d0),D2=finite_records(d2),UMIDAS=finite_records(fx))
    serialized=json.dumps(payload,allow_nan=False,ensure_ascii=False).replace('<','\\u003c')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M2-L2 research driver dashboard</title><style>{style}</style></head>
<body><main><header><div class="wordmark">Economic monitoring / Uzbekistan</div><div class="date">Phase 6G.1 · Research challenger · Frozen {escape(metadata['target'])} {escape(metadata['horizon'])}</div></header>
<h1>M2-L2 driver comparison</h1><p class="note">Research only · Phase 6E production retained · Frozen information cutoff {escape(metadata['origin'])}. Historical predictor value vintages remain unverified.</p>
<section><h2>Current M2 and M2-L2</h2>{table}<p class="note">Loading and signal shares are descriptive factor statistics, not GDP contributions. The current D0 M2 signal of {fmt(m0.signal,9)} is not +{fmt(m0.signal,9)} percentage points of GDP.</p></section>
<section><h2>What is driving the M2-L2 nowcast?</h2><p class="note">Green supports the factor signal; red weakens it. Hover for the data period, transformation, M2 source period and lagged factor-cell period. Model associations do not imply causality.</p>
<h3>DFM factor signals · M2 lagged 2 months · descriptive standardized units</h3>{bars(d2)}
<p class="note">Mean of released target-quarter standardized observations × sign-aligned fitted loading. These signals do not add to GDP growth. POS has no released target-quarter observation; its signal is unavailable and excluded from the signal-share denominator.</p>
<h3>U-MIDAS exchange-rate channel · exact forecast contribution in pp</h3>{bars(fx,True)}<p class="note">U-MIDAS is unchanged across the M2-lag comparison. Its USD / UZS contribution is copied from the existing production model, including the three FX lag terms.</p></section>
<footer>Self-contained research output. M2 source dates remain distinct from lagged factor-cell dates. No production promotion.</footer></main>
<script id="driver-payload" type="application/json">{serialized}</script></body></html>'''

def main():
    # Protect all prior audit outputs as well as the established production baseline.
    baseline=json.loads((OUT/'phase6g1_protected_before.json').read_text())
    old={str(p.relative_to(ROOT)):sha(p) for p in OUT.iterdir() if p.is_file() and p.name not in
         ['phase6g1_d2_current_drivers.csv','phase6g1_d0_vs_d2_driver_comparison.csv','phase6g1_driver_dashboard_validation.json']}
    before={**baseline,**old}
    assert all(sha(ROOT/name)==digest for name,digest in before.items())
    info,origin,snapshot=production_info(ROOT);panel,dataset,available=frames(info,ROOT,origin)
    p0,f0=dfm(panel,dataset,available,info['target'],info['horizon'],origin)
    p2,f2=lagged_dfm(panel,dataset,available,info['target'],info['horizon'],origin,2)
    existing=pd.read_csv(ROOT/'results/phase6e/phase6e_current_drivers.csv',float_precision='round_trip')
    transformations=existing.loc[existing.source_model.eq('PHASE6C_DFM')].set_index('indicator').transformation.to_dict()
    d0,mu0,sd0=calculate(f0,'D0',info['target'],transformations);d2,mu2,sd2=calculate(f2,'D2',info['target'],transformations)
    frozen=pd.read_csv(OUT/'phase6g1_current_nowcasts.csv',float_precision='round_trip').set_index('model')
    u=float(2*frozen.loc['D0','ensemble_nowcast']-frozen.loc['D0','DFM_nowcast'])
    np.testing.assert_allclose([p0,p2,.5*(p2+u)],[8.301152885464585,8.413700638995717,8.237175217381841],rtol=0,atol=1e-9)
    m0=d0.set_index('indicator').loc['m2'];m2=d2.set_index('indicator').loc['m2']
    np.testing.assert_allclose([m0.signal,m0.normalized_share_pct],[.72607378641098619,67.407878026807396],rtol=0,atol=1e-10)
    assert abs(m2.normalized_share_pct-78.93)<.01 and abs(m2.loading_share_pct-47.02)<.01
    for frame in [d0,d2]:
        assert pd.isna(frame.set_index('indicator').loc['pos_turnover','signal'])
    d2.to_csv(OUT/'phase6g1_d2_current_drivers.csv',index=False,float_format='%.17g')
    fields={'signal':'signal','normalized_share_pct':'signal_share_pct','loading':'loading','loading_share_pct':'loading_share_pct',
            'quarter_mean_z':'quarter_mean_z','latest_period':'latest_period'}
    a=d0.set_index('indicator')[list(fields)].rename(columns={k:'D0_'+v for k,v in fields.items()})
    b=d2.set_index('indicator')[list(fields)+['latest_factor_cell_period']].rename(columns={**{k:'D2_'+v for k,v in fields.items()},'latest_factor_cell_period':'D2_latest_factor_cell_period'})
    comp=a.join(b).reset_index()
    order=['indicator']+[f'{model}_{name}' for name in ['signal','signal_share_pct','loading','loading_share_pct','quarter_mean_z','latest_period'] for model in ['D0','D2']]+['D2_latest_factor_cell_period']
    comp[order].to_csv(OUT/'phase6g1_d0_vs_d2_driver_comparison.csv',index=False,float_format='%.17g')
    fx=existing.loc[existing.source_model.eq('U_MIDAS')].copy().rename(columns={'contribution_or_signal':'signal'})
    fx['display_name']=fx.indicator.map(LABELS)
    template=(ROOT/'dashboard/uzbekistan_nowcast_v2.html').read_text(encoding='utf-8')
    style=re.search(r'<style>(.*?)</style>',template,re.S).group(1)
    metadata=dict(target=info['target'],horizon=info['horizon'],origin=str(origin),snapshot=str(snapshot.relative_to(ROOT)),
        training_mean_D0=mu0.to_dict(),training_sd_D0=sd0.to_dict(),training_mean_D2=mu2.to_dict(),training_sd_D2=sd2.to_dict())
    now=dict(D0=p0,D2=p2,U_MIDAS=u,E0=.5*(p0+u),E2=.5*(p2+u))
    html=render(d0,d2,now,fx,style,metadata);HTML.write_text(html,encoding='utf-8')
    assert all(sha(ROOT/name)==digest for name,digest in before.items()),'Protected artifact changed'
    dump(OUT/'phase6g1_driver_dashboard_validation.json',dict(research_only=True,protected_files_unchanged=len(before),
        production_unchanged=True,M2=m2.to_dict(),nowcasts=now,outputs={str(p.relative_to(ROOT)):sha(p) for p in
        [HTML,OUT/'phase6g1_d2_current_drivers.csv',OUT/'phase6g1_d0_vs_d2_driver_comparison.csv']}))

if __name__=='__main__':main()
