"""Rebuild summary tables from saved fits without changing model estimates."""
import json
import numpy as np
import pandas as pd
from scripts.phase6g2.run import ROOT, OUT, csv, verify
from scripts.phase6g2.core import metrics, MODELS
from scripts.phase6g2.report import report
from scripts.phase6f.experiment import dump, sha


def main():
    def read(name):return pd.read_csv(OUT/f'phase6g2_{name}.csv',float_precision='round_trip')
    f=read('origin_forecasts');m=metrics(f);csv('horizon_metrics',m)
    loads=read('factor_loadings');now=read('current_nowcasts')
    now=now.loc[~now['sample'].eq('PRODUCTION_REFERENCE')]
    comparison=m.loc[m.horizon.eq('POOLED')].copy()
    for h in ['H1','H2','H3']:
        comparison=comparison.merge(m.loc[m.horizon.eq(h),['sample','model','RMSE']].rename(columns={'RMSE':h+'_RMSE'}),on=['sample','model'])
    comparison=comparison.merge(now.loc[now.model.isin(MODELS),['sample','model','nowcast']],on=['sample','model'])
    summary=loads.loc[loads.indicator.eq('m2')].groupby(['sample','model']).agg(
        mean_M2_factor_loading=('factor_loading','mean'),mean_factor_M2_correlation=('factor_M2_correlation','mean'),
        mean_factor_correlation_vs_M0=('factor_correlation_vs_M0','mean'),all_successful_fits_converged=('converged','all')).reset_index()
    failures=read('failures')
    summary=summary.merge(failures.groupby(['sample','model']).size().rename('failed_fit_count').reset_index(),on=['sample','model'],how='left')
    summary['failed_fit_count']=summary.failed_fit_count.fillna(0).astype(int)
    csv('model_comparison',comparison.merge(summary,on=['sample','model']))
    loo=[]
    for q in sorted(f.target_quarter.unique()):
        table=metrics(f.loc[f.target_quarter.ne(q)])
        loo.extend(dict(excluded_quarter=q,**r) for r in table.loc[table.horizon.eq('POOLED')].to_dict('records'))
    csv('leave_one_quarter_out',loo)
    fdi=read('fdi_results')
    classification=report(comparison,m,loads,pd.DataFrame(loo),fdi,now.to_dict('records'))
    audit=json.loads((OUT/'phase6g2_audit.json').read_text())
    raw=pd.read_parquet(ROOT/'data/processed/m2.parquet')
    audit.update(raw_m2_nonpositive_count=int(raw.raw_value.le(0).sum()),raw_m2_missing_count=int(raw.raw_value.isna().sum()))
    dump(OUT/'phase6g2_audit.json',audit)
    samples=read('sample_comparison')
    for name in ['first_raw','first_yoy','first_qoq']:samples[name]=audit[name]
    csv('sample_comparison',samples)
    transformations=read('m2_transformation_comparison');transformations['date']=pd.to_datetime(transformations.date)
    csv('m2_month_of_year_diagnostics',[
        dict(series=name,calendar_month=month,N=int(g[name].count()),mean=g[name].mean(),std=g[name].std())
        for name in ['m2_yoy_log','m2_qoq_log'] for month,g in transformations.groupby(transformations.date.dt.month)])
    details=['\n## Convergence and fair-origin exclusions\n',
        f'{len(failures)} failed fits across sample regimes (including optional bridge failures). These are explicitly recorded in failures.csv; no failed fit is used as a forecast. All estimators keep the accepted convergence settings.',
        f'All six models and both regimes share {int(comparison.N.min())} scored origins. Natural/common RMSE differences therefore reflect estimation history, rather than different realized forecast-origin selections.']
    within=pd.concat([metrics(f.loc[f['sample'].eq(s)]) for s in ['NATURAL','COMMON']],ignore_index=True)
    csv('within_regime_horizon_metrics',within)
    details.append('The strict cross-regime intersection excludes all 2025Q3–2026Q2 holdout origins because natural Q0/Q1 do not converge. Consequently the headline metrics are retrospective development-period diagnostics, with ZERO complete recent holdout origins. No holdout performance claim is justified by that table.')
    details.append('Supplementary within_regime_horizon_metrics.csv uses a separate six-model intersection for each sample regime, preserving the additional successful COMMON-sample holdout fits; these supplemental scores cannot be used for a matched natural-versus-common comparison.')
    for sample,group in within.loc[within.horizon.eq('POOLED')].groupby('sample'):
        details.append(f'Supplementary {sample} origin count: {int(group.N.min())}; pooled RMSEs: '+str(dict(zip(group.model,group.RMSE))))
    counts=failures.groupby(['sample','model']).size()
    details.extend(f'{sample} {model}: {count} failures.' for (sample,model),count in counts.items())
    wide=f.pivot(index=['target_quarter','horizon'],columns=['sample','model'],values='prediction')
    wide=wide.reindex(columns=pd.MultiIndex.from_product([['NATURAL','COMMON'],MODELS]))
    eligibility=wide.notna().all(axis=1).rename('scored_common_origin').reset_index()
    csv('scoring_origin_eligibility',eligibility)
    details.append('Origins removed from BOTH regimes: '+str(eligibility.loc[~eligibility.scored_common_origin,['target_quarter','horizon']].to_dict('records')))
    if not fdi.empty:
        widefd=fdi.pivot(index=['target_quarter','horizon'],columns='model',values='prediction').dropna()
        actual=fdi.drop_duplicates(['target_quarter','horizon']).set_index(['target_quarter','horizon']).actual
        base=f.loc[f['sample'].eq('COMMON')&f.model.eq('Q2')].set_index(['target_quarter','horizon']).prediction
        valid=widefd.index.intersection(base.dropna().index)
        brmse=float(np.sqrt(np.mean((actual.reindex(valid)-base.reindex(valid))**2)))
        details.append(f'On the exact {len(valid)} FDI challenger origins, Q2 without FDI has RMSE {brmse:.6f}.')
        for name in widefd:
            rmse=float(np.sqrt(np.mean((actual.reindex(valid)-widefd[name].reindex(valid))**2)))
            details.append(f'{name}: RMSE difference versus identical-origin Q2 without FDI {rmse-brmse:.6f} pp. Improvement versus the base Q2 bridge: {rmse<brmse}.')
        fdilo=[]
        for name in widefd:
            for quarter in sorted(set(valid.get_level_values('target_quarter'))):
                keep=valid[valid.get_level_values('target_quarter')!=quarter]
                err=actual.reindex(keep)-widefd[name].reindex(keep)
                be=actual.reindex(keep)-base.reindex(keep)
                fdilo.append(dict(model=name,excluded_quarter=quarter,N=len(keep),RMSE=float(np.sqrt(np.mean(err**2))),delta_RMSE_vs_Q2=float(np.sqrt(np.mean(err**2))-np.sqrt(np.mean(be**2)))))
        csv('fdi_leave_one_quarter_out',fdilo)
        for name,group in pd.DataFrame(fdilo).groupby('model'):
            details.append(f'{name}: improvement versus Q2 survives every quarter exclusion: {bool(group.delta_RMSE_vs_Q2.lt(0).all())}.')
        details.append('Small FDI gains relative to the weak Q2 bridge do not rescue the three-month transformation relative to YoY M2. The longer release lag attenuates the gain, and revised-history FDI evidence remains insufficient for promotion.')
    path=OUT/'phase6g2_results.md';path.write_text(path.read_text(encoding='utf8')+'\n\n'.join(details)+'\n',encoding='utf8')
    manifest=OUT/'phase6g2_run_manifest.json';value=json.loads(manifest.read_text())
    value.update(classification=classification,scored_common_origins=int(comparison.N.min()),protected_artifacts=verify(),
        code_hashes={p.name:sha(p) for p in (ROOT/'scripts/phase6g2').glob('*.py')},
        outputs={p.name:sha(p) for p in OUT.glob('*.csv')})
    dump(manifest,value)
    print((OUT/'phase6g2_terminal_summary.txt').read_text(encoding='utf8'))


if __name__=='__main__':main()
