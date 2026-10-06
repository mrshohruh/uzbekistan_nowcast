"""Run isolated research: python -m scripts.phase6g2.run."""
from pathlib import Path
import json
import logging
import sys
import os
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from scripts.phase6g2.core import MODELS, log_change, design, fit, metrics
from scripts.phase6e.models import frames, FIELDS, sw
from scripts.phase6f.experiment import sha, dump, parse_fdi, bridge_fit
from scripts.phase6g.run import production_info, protect
from uznowcast.models.data import load_dataset, horizon_month_end

OUT = ROOT/'results/phase6g2'
LOG = logging.getLogger('phase6g2')


def csv(name, data):
    pd.DataFrame(data).to_csv(OUT/f'phase6g2_{name}.csv', index=False, float_format='%.17g')


def hashes():
    before = protect(ROOT)
    for folder in ['results/phase6g', 'results/phase6g1', 'scripts/phase6g', 'scripts/phase6g1', 'data/master', 'data/processed']:
        for p in (ROOT/folder).glob('*'):
            if p.is_file():
                before[p.relative_to(ROOT).as_posix()] = sha(p)
    before['run_nowcast.bat'] = sha(ROOT/'run_nowcast.bat')
    return before


def verify():
    before = json.loads((OUT/'phase6g2_protected_before.json').read_text())
    after = {p: sha(ROOT/p) if (ROOT/p).is_file() else None for p in before}
    dump(OUT/'phase6g2_protected_after.json', after)
    if before != after:
        raise ValueError('Protected artifacts changed: '+str([p for p in before if before[p]!=after[p]]))
    return len(before)


def audit(panel, dataset):
    raw = pd.read_parquet(ROOT/'data/processed/m2.parquet')
    if raw.reference_period.duplicated().any():
        raise ValueError('Duplicate raw M2 month')
    levels = pd.Series(raw.raw_value.to_numpy(), index=pd.PeriodIndex(raw.reference_period, freq='M').to_timestamp('M'))
    yoy, qoq = log_change(levels, 12), log_change(levels, 3)
    pair = pd.concat([panel.m2.rename('frozen'), yoy.rename('raw_recomputed')], axis=1, sort=True).dropna()
    if not np.allclose(pair.frozen, pair.raw_recomputed, atol=1e-10, rtol=0):
        raise ValueError('Raw M2 snapshot differs from frozen accepted history')
    csv('m2_transformation_comparison', pd.DataFrame({'date':levels.index, 'M2_level':levels,
        'm2_yoy_log':yoy, 'm2_qoq_log':qoq}).reset_index(drop=True))
    diagnostics = []
    for name, series in [('m2_yoy_log',yoy),('m2_qoq_log',qoq)]:
        s = series.dropna()
        diagnostics.append(dict(series=name, N=len(s), mean=s.mean(), std=s.std(), minimum=s.min(), maximum=s.max(),
            autocorrelation_L1=series.autocorr(1), autocorrelation_L3=series.autocorr(3), autocorrelation_L12=series.autocorr(12),
            yoy_qoq_correlation=yoy.corr(qoq), extreme_count_3sd=int(((s-s.mean()).abs()>3*s.std()).sum()),
            extreme_periods=json.dumps([str(x.to_period('M')) for x in s.index[(s-s.mean()).abs()>3*s.std()]])))
    csv('m2_diagnostics',diagnostics)
    csv('m2_month_of_year_diagnostics',[
        dict(series=name,calendar_month=month,N=len(g.dropna()),mean=g.mean(),std=g.std())
        for name,s in [('m2_yoy_log',yoy),('m2_qoq_log',qoq)] for month,g in s.groupby(s.index.month)])
    receipt=json.loads((ROOT/'results/phase6f/raw/receipt.json').read_text())
    if sha(ROOT/receipt['raw_file'])!=receipt['checksum']:
        raise ValueError('FDI checksum mismatch')
    fdi=parse_fdi(ROOT/receipt['raw_file']);fdi['retrieved_at']=receipt['retrieved_at']
    evidence=[]
    for directory in ['src','scripts','config','docs','registry','results']:
        paths=[]
        for base, dirs, files in os.walk(ROOT/directory):
            dirs[:]=[x for x in dirs if not x.startswith(('test','validation_tmp','t_','__pycache__','_vendor','_pytest','phase6g2','snapshots','browser_profile'))]
            paths.extend(Path(base)/name for name in files)
        for p in paths:
            if p.suffix not in ('.py','.md','.json','.csv','.yaml','.txt') or 'phase6g2' in p.parts or any(x.startswith(('test_tmp','validation_tmp','t_','__pycache__','_vendor','_pytest')) for x in p.parts):
                continue
            try:
                for n,line in enumerate(p.read_text(encoding='utf8').splitlines(),1):
                    if 'fdi' in line.lower() or 'direct investment' in line.lower():
                        evidence.append(dict(file=p.relative_to(ROOT).as_posix(),line=n,text=line[:1500]))
            except (OSError,UnicodeError):
                continue
    csv('fdi_repository_evidence',evidence)
    csv('fdi_transformation_audit',[dict(FDI_TRANSFORMATION_USED='FDI_million_USD / 1000 (nominal levels; linear scaling)',
        source=receipt['source_url'], frequency='Q',unit='million USD nominal',source_series='Direct investment: liabilities; net incurrence of liabilities',
        levels_used=True,ln_used=False,log1p_used=False,asinh_used=False,standardized=False,monthly_DFM=False,quarterly_bridge=True,
        B3='M0 factor + GDP(q-1) + economic-L1 M2 quarter mean + latest gated FDI/1000',
        B4='B3 with FDI additional exact reference-quarter lag',B5='M1 factor + GDP(q-1) + latest gated FDI/1000; no separate M2 regressor',
        evidence='scripts/phase6f/experiment.py:96-156,254-260',zero_count=int(fdi.value.eq(0).sum()),negative_count=int(fdi.value.lt(0).sum()),
        ln_valid=bool(fdi.value.dropna().gt(0).all()),release_lags='90/120 days assumed; source release dates unknown',retrieved_at=receipt['retrieved_at'])])
    row=next(r for r in dataset.registry.scope('v1') if r['variable_key']=='m2')
    dump(OUT/'phase6g2_audit.json',dict(m2_source=row['machine_download_url'],raw_frequency='M',raw_unit=str(raw.raw_unit.iloc[0]),
        current_transformation='100 * (ln(M2_t) - ln(M2_t-12))',publication_lag_days=dataset.release_lag_days['m2'],
        ordering='transformation -> source release mask -> economic lag -> balanced start -> training-only standardization',
        first_raw=str(levels.first_valid_index()),first_yoy=str(yoy.first_valid_index()),first_qoq=str(qoq.first_valid_index()),
        matched_raw_frozen_months=len(pair),maximum_raw_frozen_difference=float((pair.frozen-pair.raw_recomputed).abs().max()),
        raw_m2_nonpositive_count=int(levels.le(0).sum()),raw_m2_missing_count=int(levels.isna().sum()),
        historical_value_vintages_verified=False,FDI_TRANSFORMATION_USED='nominal million USD / 1000'))
    return qoq, fdi, receipt


def run():
    OUT.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(OUT/'phase6g2_pipeline.log',encoding='utf8'),logging.StreamHandler()])
    dump(OUT/'phase6g2_protected_before.json',hashes())
    dataset=load_dataset(ROOT)
    panel=pd.read_csv(ROOT/'results/phase6c/phase6c_research_monthly_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip')
    qoq,fdi,receipt=audit(panel,dataset)
    events=pd.read_csv(ROOT/'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    frozen=pd.read_csv(ROOT/'results/phase6g/phase6g_origin_level_forecasts.csv',float_precision='round_trip')
    eligible=pd.read_csv(ROOT/'results/phase6g/phase6g_origin_eligibility.csv')
    keys=eligible.loc[eligible.common_origin_eligible,['target_quarter','horizon']]
    info,origin,snapshot=production_info(ROOT);current_panel,ds,av=frames(info,ROOT,origin)
    contexts=[]
    for r in keys.itertuples(index=False):
        o=horizon_month_end(r.target_quarter,r.horizon)
        a=sw.common.vintage_kernel().available_gdp_vintage_as_of(events,o,target=r.target_quarter,timing_rule='STRICT')
        old=frozen.loc[frozen.target_quarter.eq(r.target_quarter)&frozen.horizon.eq(r.horizon)&frozen.model.eq('S0')].iloc[0]
        contexts.append((r.target_quarter,r.horizon,o,panel,dataset,a,float(old.actual),False))
    contexts.append((info['target'],info['horizon'],origin,current_panel,ds,av,np.nan,True))
    forecasts=[];samples=[];loads=[];now=[];failures=[];fdirows=[];reproduction=[];factorseries=[]
    cache={}
    production=json.loads((ROOT/'results/phase6e/phase6e_current_nowcast.json').read_text())
    for target,horizon,o,p,ds,a,actual,current in contexts:
        sw.common.vintage_kernel().assert_boundary(a,target)
        qp=p.copy();qp['m2']=qoq.reindex(p.index)
        # Current snapshot's M2 missing cells are authoritative release/scope restrictions.
        if current:
            qp.loc[p.m2.isna(),'m2']=np.nan
        designs={m:design(qp if m.startswith('Q') else p,ds,target,horizon,m) for m in MODELS}
        start=max(v[0].index.min() for v in designs.values())
        for sample in ['NATURAL','COMMON']:
            fitted={}
            for model in MODELS:
                frame,spec,masks,end=designs[model]
                if sample=='COMMON':frame=frame.loc[start:]
                samples.append(dict(sample=sample,model=model,target_quarter=target,horizon=horizon,current=current,
                    complete_panel_start=str(frame.index.min()),n_DFM_training_observations=len(frame.loc[:end]),n_m2_training_observations=int(frame.loc[:end,'m2'].count())))
                try:
                    pred,f=fit(frame,spec,end,a,target,o,cache);fitted[model]=f
                    if sample=='NATURAL' and model.startswith('M'):
                        expected=production['dfm_forecast'] if current and model=='M0' else None
                        if not current:
                            old=frozen.loc[frozen.target_quarter.eq(target)&frozen.horizon.eq(horizon)&frozen.model.eq('S'+model[-1])]
                            expected=float(old.prediction.iloc[0])
                        if expected is not None:
                            reproduction.append(dict(model=model,target_quarter=target,horizon=horizon,current=current,error=pred-expected,passed=abs(pred-expected)<1e-7))
                            if abs(pred-expected)>=1e-7:raise RuntimeError('Benchmark reproduction failure')
                    if current:
                        now.append(dict(sample=sample,model=model,target_quarter=target,nowcast=pred,difference_vs_production_DFM=pred-production['dfm_forecast'],status='RESEARCH_ONLY'))
                    else:
                        forecasts.append(dict(sample=sample,model=model,target_quarter=target,horizon=horizon,forecast_origin=str(o),actual=actual,prediction=pred))
                    source=(frame.m2.dropna().index.to_period('M')-int(model[-1])).to_timestamp('M')
                    if not bool((source+pd.Timedelta(days=ds.release_lag_days['m2'])<=horizon_month_end(target,horizon)).all()):raise RuntimeError('M2 timing leak')
                    base=fitted['M0']['factors'].iloc[:,0];factor=f['factors'].iloc[:,0]
                    corr=base.corr(factor);sign=-1 if corr<0 else 1
                    for field,loading in zip(FIELDS,f['loadings']):
                        loads.append(dict(sample=sample,model=model,target_quarter=target,horizon=horizon,current=current,indicator=field,
                            factor_loading=float(loading)*sign,factor_M2_correlation=factor.corr(f['z'].m2)*sign,factor_correlation_vs_M0=abs(corr),
                            training_mean=float(f['means'][field]),training_std=float(f['scales'][field]),**f['diagnostics']))
                    if current:
                        factorseries.extend(dict(sample=sample,model=model,date=str(t),factor=float(v)*sign) for t,v in factor.items())
                except (ValueError,KeyError,np.linalg.LinAlgError) as exc:
                    failures.append(dict(sample=sample,model=model,target_quarter=target,horizon=horizon,current=current,error=str(exc)))
            if sample=='COMMON' and 'Q2' in fitted:
                for days in [90,120]:
                    for transform in ['LEVELS','ASINH']:
                        name='Q2_FDI_'+transform+('_120D' if days==120 else '')
                        # Revised snapshot is not valid evidence at the frozen production cutoff.
                        if current and pd.Timestamp(receipt['retrieved_at'])>o.tz_localize('Asia/Tashkent').tz_convert('UTC'):
                            now.append(dict(sample=sample,model=name,target_quarter=target,nowcast=np.nan,status='UNAVAILABLE_SNAPSHOT_POSTDATES_FROZEN_CUTOFF'))
                            continue
                        fd=fdi.copy()
                        if transform=='ASINH':fd['value']=1000*np.arcsinh(fd.value) # bridge helper divides by 1000
                        try:
                            pred,coeff=bridge_fit(fitted['Q2'],a,target,o,p.m2,fdi=fd,fdidays=days)
                            fdirows.append(dict(model=name,target_quarter=target,horizon=horizon,actual=actual,prediction=pred,
                                release_lag_days=days,evidence_class='REVISED_HISTORY_NOT_VINTAGE_REAL_TIME',current=current))
                        except (ValueError,KeyError) as exc:
                            failures.append(dict(sample=sample,model=name,target_quarter=target,horizon=horizon,current=current,error=str(exc)))
        csv('sample_comparison',samples);csv('origin_forecasts',forecasts);csv('failures',failures)
        LOG.info('Completed %s %s current=%s',target,horizon,current)
    f=pd.DataFrame(forecasts);m=metrics(f);csv('horizon_metrics',m)
    comparison=m.loc[m.horizon.eq('POOLED')].copy()
    for h in ['H1','H2','H3']:
        comparison=comparison.merge(m.loc[m.horizon.eq(h),['sample','model','RMSE']].rename(columns={'RMSE':h+'_RMSE'}),on=['sample','model'])
    comparison=comparison.merge(pd.DataFrame(now).loc[lambda x:x.model.isin(MODELS),['sample','model','nowcast']],on=['sample','model'])
    ld=pd.DataFrame(loads)
    summary=ld.loc[ld.indicator.eq('m2')].groupby(['sample','model']).agg(
        mean_M2_factor_loading=('factor_loading','mean'),mean_factor_M2_correlation=('factor_M2_correlation','mean'),
        mean_factor_correlation_vs_M0=('factor_correlation_vs_M0','mean'),all_fits_converged=('converged','all')).reset_index()
    comparison=comparison.merge(summary,on=['sample','model'])
    csv('model_comparison',comparison);csv('current_nowcasts',now);csv('factor_loadings',loads);csv('current_factor_series',factorseries);csv('reproduction',reproduction)
    loo=[]
    for q in sorted(f.target_quarter.unique()):
        table=metrics(f.loc[f.target_quarter.ne(q)])
        loo.extend(dict(excluded_quarter=q,**r) for r in table.loc[table.horizon.eq('POOLED')].to_dict('records'))
    csv('leave_one_quarter_out',loo)
    csv('fdi_results',fdirows)
    from scripts.phase6g2.report import report
    classification=report(comparison,m,pd.DataFrame(loads),pd.DataFrame(loo),pd.DataFrame(fdirows),now)
    protected_count=verify()
    dump(OUT/'phase6g2_run_manifest.json',dict(classification=classification,research_only=True,production_unchanged=True,
        protected_artifacts=protected_count,protected_hashes_identical=True,forecast_origins=len(keys),automatic_promotion=False,
        current_cutoff=str(origin),historical_value_vintages_verified=False,failures=failures,
        inputs={str(p.relative_to(ROOT)):sha(p) for p in [snapshot,ROOT/'data/processed/m2.parquet',ROOT/'results/phase6c/phase6c_research_monthly_panel.csv',ROOT/receipt['raw_file']]},
        code_hashes={p.name:sha(p) for p in (ROOT/'scripts/phase6g2').glob('*.py')}))
    from scripts.phase6g2.finalize import main as finalize
    finalize()


if __name__=='__main__':run()
