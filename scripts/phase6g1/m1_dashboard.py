"""Frozen M0/M1/M2 driver research, with a common visual scale."""
from html import escape
import json
import re
import numpy as np
import pandas as pd
from scripts.phase6g1 import driver_dashboard as previous
from scripts.phase6g1.driver_dashboard import ROOT,OUT,calculate,finite_records
from scripts.phase6e.dashboard import LABELS,fmt
from scripts.phase6e.models import frames,dfm,sw
from scripts.phase6g.run import production_info
from scripts.phase6f.experiment import lagged_dfm,sha,dump
from uznowcast.models.data import quarter_start,horizon_month_end

LABEL='Phase 6F original common holdout / revised-history diagnostic'
FILES=[OUT/'phase6g1_m1_current_drivers.csv',OUT/'phase6g1_m0_m1_m2_driver_comparison.csv',
       OUT/'phase6g1_m0_m1_m2_model_comparison.csv',ROOT/'dashboard/phase6g1_m1_driver_dashboard.html',
       ROOT/'dashboard/phase6g1_m0_m1_m2_comparison.html']

def driver_frame(fit,lag,target,transformations):
    # Reuse the established calculation, then assign source dates from the
    # actual lag of this fit. The computation always uses this fit's frame.
    f,mean,sd=calculate(fit,'D0',target,transformations)
    f['model']='M'+str(lag)
    m=f.indicator.eq('m2')
    f.loc[m,'latest_period']=f.loc[m,'latest_factor_cell_period'].map(lambda x:str(pd.Period(x,'M')-lag))
    if lag:
        f.loc[m,'display_name']=f'Broad money · M2 ({lag}-month lag)'
        f.loc[m,'transformation']=f'100*ln(M2_t/M2_t-12), then shifted {lag} calendar '+('month' if lag==1 else 'months')+' in the DFM factor design'
    f['source_period']=f.latest_period;f['factor_cell_period']=f.latest_factor_cell_period
    f['signal_share_pct']=f.normalized_share_pct
    # A historical POS value is not a current quarter observation.
    f.loc[f.quarter_months_available.eq(0),'latest_value']=np.nan
    return f,mean,sd

def panel(f,lag,scale,fx=False):
    result=f'<div class="bars" data-model="M{lag}" data-scale="{scale:.17g}">'
    for r in f.to_dict('records'):
        v=r['signal'];valid=pd.notna(v);sign=r['direction'] if valid else 'neutral'
        width=48*abs(v)/scale if valid else 0
        pos=f'left:50%;width:{width}%' if valid and v>=0 else f'right:50%;width:{width}%'
        tip=[f"Data period: {r['latest_period']}",f"Transformation: {r['transformation']}"]
        if not fx:
            if r['indicator']=='m2':tip += [f"Underlying M2 source period: {r['source_period']}",f"Factor-cell period: {r['factor_cell_period']}",
                f"M2 YoY transformed value: {fmt(r['latest_value'],9)}",f"Lag treatment: shifted {lag} calendar months in the DFM factor design"]
            tip += [f"Quarter mean z: {fmt(r['quarter_mean_z'],9)}",f"DFM loading: {fmt(r['loading'],9)}",
                f"Loading share: {fmt(r['loading_share_pct'],4)}%",f"Current factor signal: {fmt(v,9)}",f"Signal share: {fmt(r['signal_share_pct'],4)}%"]
        result+=f'<div class="barrow" title="{escape(" · ".join(tip),quote=True)}" data-indicator="{r["indicator"]}"><span>{escape(r["display_name"])}</span><div class="track"><i class="{sign}" style="{pos}"></i></div><b class="{sign}">{fmt(v)}</b></div>'
    return result+'</div>'

def summary(models):
    a=models.set_index('model');lines=[]
    for model in ['M1','M2']:
        r=a.loc[model];base=a.loc['M0'];gain=base.pooled_RMSE-r.pooled_RMSE
        best=max(['H1','H2','H3'],key=lambda h:base[h+'_RMSE']-r[h+'_RMSE'])
        change=r.M2_signal_share_pct-base.M2_signal_share_pct
        loading_change=r.M2_loading_share_pct-base.M2_loading_share_pct
        lines.append(f'{model} '+('lowers' if gain>0 else 'does not lower')+f' pooled RMSE versus M0 by {gain:.6f} pp; largest horizon gain is {best}. '
            f'M2 signal dominance is '+('stronger' if change>0 else 'weaker')+f' ({change:+.4f} pp of share); loading share changes {loading_change:+.4f} pp. '
            f'Current DFM nowcast changes {r.dfm_nowcast-base.dfm_nowcast:+.9f} pp versus M0.')
    gain=a.loc['M1','pooled_RMSE']-a.loc['M2','pooled_RMSE']
    lines.append('M2 '+('lowers' if gain>0 else 'does not lower')+f' pooled RMSE versus M1 by {gain:.6f} pp. These are descriptive associations for research challengers, not fully vintage-real-time evidence.')
    return lines

def render(data,models,fx,style,metadata,comparison=False):
    scale=max(float(f.signal.abs().max()) for f in data.values()) if comparison else float(data['M1'].signal.abs().max())
    rows=[('M2 lag','m2_lag_months',0),('DFM nowcast','dfm_nowcast',4),('U-MIDAS','u_midas_nowcast',4),('50/50 nowcast','ensemble_50_50',4),
          ('H1 RMSE','H1_RMSE',6),('H2 RMSE','H2_RMSE',6),('H3 RMSE','H3_RMSE',6),('Pooled RMSE','pooled_RMSE',6),
          ('M2 loading share · descriptive','M2_loading_share_pct',2),('M2 signal share · descriptive','M2_signal_share_pct',2)]
    table='<div class="scroll"><table><thead><tr><th>Measure</th><th>M0</th><th>M1</th><th>M2</th></tr></thead><tbody>'
    for label,key,digits in rows:
        table+='<tr><td>'+escape(label)+'</td>'+''.join('<td>'+fmt(r[key],digits)+('m' if key=='m2_lag_months' else '%' if 'share' in key else '')+'</td>' for r in models.to_dict('records'))+'</tr>'
    table+='</tbody></table></div>'
    subtitle='Green supports the factor signal; red weakens it. Hover for the data period, transformation, M2 source period and lagged factor-cell period. Model associations do not imply causality.'
    if comparison:
        sections='<div class="three">'+''.join(f'<section><h2>{model} · {title}</h2><p class="note">{subtitle}</p><h3>DFM factor signals · descriptive standardized units</h3>{panel(data[model],lag,scale)}</section>' for model,lag,title in [('M0',0,'Contemporaneous M2'),('M1',1,'M2 lagged 1 month'),('M2',2,'M2 lagged 2 months')])+'</div>'
        heading='M0 / M1 / M2 research driver comparison'
    else:
        heading='What is driving the M2-L1 nowcast?'
        sections=f'<section><h2>{heading}</h2><p class="note">{subtitle}</p><h3>DFM factor signals · M2 lagged 1 month · descriptive standardized units</h3>{panel(data["M1"],1,scale)}</section>'
    payload=dict(metadata=metadata,drivers={key:finite_records(f) for key,f in data.items()},models=finite_records(models),UMIDAS=finite_records(fx),shared_scale=scale)
    js=json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    extra='.three{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.three section{padding:20px}.three .barrow{grid-template-columns:120px 1fr 60px;gap:8px}@media(max-width:1050px){.three{grid-template-columns:1fr}}'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{heading}</title><style>{style}</style><style>{extra}</style></head><body><main>
<header><div class="wordmark">Economic monitoring / Uzbekistan</div><div class="date">Phase 6G.1 · Research only · {metadata['target']} {metadata['horizon']}</div></header><h1>{heading}</h1>
<section><h2>Current M0 / M1 / M2 comparison</h2>{table}<p class="note">{LABEL}. Identical 12 holdout origins; revised predictor history, not fully vintage-real-time. Signal and loading shares are descriptive factor statistics, not GDP contributions.</p></section>
{sections}<p class="note">Signals use each fit’s training-only scaling and sign-aligned loadings. POS remains Unavailable; missing signals are excluded from the signal-share denominator. {'All three panels share the same horizontal scale.' if comparison else ''}</p>
<section><h3>U-MIDAS exchange-rate channel · exact forecast contribution in pp</h3>{previous.bars(fx,True)}<p class="note">U-MIDAS is unchanged across M0, M1 and M2. Only the treatment of M2 inside the DFM changes.</p></section>
<section><h2>Research interpretation</h2>{''.join('<p>'+escape(line)+'</p>' for line in summary(models))}</section><footer>RESEARCH_ONLY · PHASE6E_PRODUCTION_UNCHANGED · Frozen cutoff {metadata['origin']}</footer></main><script id="driver-payload" type="application/json">{js}</script></body></html>'''

def run():
    baseline=json.loads((OUT/'phase6g1_protected_before.json').read_text())
    newnames={p.name for p in FILES}|{'phase6g1_m1_driver_validation.json','phase6g1_m1_driver_tests.xml'}
    protected={**baseline,**{str(p.relative_to(ROOT)):sha(p) for p in OUT.iterdir() if p.is_file() and p.name not in newnames},
        str(previous.HTML.relative_to(ROOT)):sha(previous.HTML)}
    assert all(sha(ROOT/name)==digest for name,digest in protected.items())
    info,origin,snapshot=production_info(ROOT);p,ds,av=frames(info,ROOT,origin)
    prior=pd.read_csv(ROOT/'results/phase6e/phase6e_current_drivers.csv',float_precision='round_trip')
    transformations=prior.loc[prior.source_model.eq('PHASE6C_DFM')].set_index('indicator').transformation.to_dict()
    reference=pd.read_csv(ROOT/'results/phase6f/phase6f_current_nowcasts.csv',float_precision='round_trip').set_index('model')
    u=float(reference.loc['U_MIDAS','nowcast'])
    metrics=pd.read_csv(ROOT/'results/phase6f/phase6f_horizon_metrics.csv',float_precision='round_trip')
    data={};fits={};pred={};scaling={};gates=[]
    for lag in range(3):
        model='M'+str(lag)
        pred[model],fits[model]=dfm(p,ds,av,info['target'],info['horizon'],origin) if lag==0 else lagged_dfm(p,ds,av,info['target'],info['horizon'],origin,lag)
        assert abs(pred[model]-reference.loc[model,'nowcast'])<1e-10
        data[model],mu,sd=driver_frame(fits[model],lag,info['target'],transformations)
        scaling[model]=dict(training_mean=mu.to_dict(),training_sd=sd.to_dict(),training_start=str(fits[model]['frame'].index.min()),training_end=str(quarter_start(info['target'])-pd.Timedelta(days=1)))
        # Compare every lagged design cell with publication-masked parent M2.
        kernel=sw.common.kernel();spec=kernel.Spec('gate',tuple(p.columns),1,2,'2019-01-31',True,False)
        masked,_=kernel.mask(p,spec,info['target'],info['horizon'],ds.release_lag_days,'standard')
        actual=fits[model]['frame'].m2;expected=masked.m2.shift(lag).reindex(actual.index)
        pd.testing.assert_series_equal(actual,expected,check_names=False)
        sources=actual.dropna().index.to_period('M')-lag
        gate=bool((sources.to_timestamp('M')+pd.Timedelta(days=ds.release_lag_days['m2'])<=horizon_month_end(info['target'],info['horizon'])).all())
        assert gate;gates.append(dict(model=model,mask_before_economic_lag=True,source_release_gate_passed=gate))
    rows=[]
    for lag in range(3):
        model='M'+str(lag);f=data[model].set_index('indicator');m=f.loc['m2']
        met=metrics.loc[metrics.model.eq(model)&metrics['sample'].eq('PAIRWISE_COMMON')].set_index('horizon')
        assert met.loc['POOLED','N']==12 and (met.loc[['H1','H2','H3'],'N']==4).all()
        rows.append(dict(model=model,m2_lag_months=lag,dfm_nowcast=pred[model],u_midas_nowcast=u,ensemble_50_50=.5*(pred[model]+u),
            **{h+'_RMSE':float(met.loc[h,'RMSE']) for h in ['H1','H2','H3']},pooled_RMSE=float(met.loc['POOLED','RMSE']),
            delta_pooled_RMSE_vs_M0=float(met.loc['POOLED','RMSE']-metrics.loc[metrics.model.eq('M0')&metrics.horizon.eq('POOLED'),'RMSE'].iloc[0]),
            factor_correlation_with_M0=abs(fits[model]['factors'].iloc[:,0].corr(fits['M0']['factors'].iloc[:,0])),
            M2_loading_share_pct=m.loading_share_pct,M2_signal_share_pct=m.signal_share_pct,
            largest_loading_indicator=f.loading.abs().idxmax(),largest_signal_indicator=f.signal.abs().idxmax(),sample_label=LABEL,N=12))
    models=pd.DataFrame(rows)
    np.testing.assert_allclose(models.pooled_RMSE,[.678442,.620965,.613137],rtol=0,atol=5e-7)
    cols=['model','indicator','display_name','source_period','factor_cell_period','latest_period','latest_factor_cell_period','latest_value','quarter_months_available','quarter_mean_z','loading','loading_share_pct','signal','signal_share_pct','direction','transformation','interpretation','decomposition_type']
    data['M1'][cols].to_csv(FILES[0],index=False,float_format='%.17g')
    comp=pd.DataFrame(index=data['M0'].indicator)
    for name in ['signal','signal_share_pct','loading','loading_share_pct','quarter_mean_z','latest_period']:
        for model,f in data.items():comp[model+'_'+name]=f.set_index('indicator')[name]
    for model in ['M1','M2']:comp[model+'_latest_factor_cell_period']=data[model].set_index('indicator').latest_factor_cell_period
    comp.reset_index().to_csv(FILES[1],index=False,float_format='%.17g');models.to_csv(FILES[2],index=False,float_format='%.17g')
    fx=prior.loc[prior.source_model.eq('U_MIDAS')].copy().rename(columns={'contribution_or_signal':'signal'});fx['display_name']=fx.indicator.map(LABELS)
    style=re.search(r'<style>(.*?)</style>',(ROOT/'dashboard/uzbekistan_nowcast_v2.html').read_text(encoding='utf-8'),re.S).group(1)
    meta=dict(target=info['target'],horizon=info['horizon'],origin=str(origin),snapshot=str(snapshot.relative_to(ROOT)),scaling=scaling,gates=gates)
    for path,comparison in [(FILES[3],False),(FILES[4],True)]:path.write_text(render(data,models,fx,style,meta,comparison),encoding='utf-8')
    assert all(sha(ROOT/name)==digest for name,digest in protected.items()),'Protected artifacts changed'
    return dict(protected_files_unchanged=len(protected),production_unchanged=True,gates=gates,models=finite_records(models),
                M1_M2_driver=finite_records(data['M1'].loc[data['M1'].indicator.eq('m2')])[0],
                M2_M2_driver=finite_records(data['M2'].loc[data['M2'].indicator.eq('m2')])[0])

def main():
    run();first={str(p.relative_to(ROOT)):sha(p) for p in FILES}
    evidence=run();second={str(p.relative_to(ROOT)):sha(p) for p in FILES}
    assert first==second,'Non-deterministic output'
    evidence.update(deterministic_two_complete_reruns=True,output_hashes=second,decision='RESEARCH_ONLY',sample_label=LABEL)
    dump(OUT/'phase6g1_m1_driver_validation.json',evidence)

if __name__=='__main__':main()
