"""Matched model tests, empirical dominance and an evidence-led report."""
import json
import re
import numpy as np
import pandas as pd
from scripts.phase6g1 import diagnostics as d
from scripts.phase6f.experiment import dump


def save(out,name,f):pd.DataFrame(f).to_csv(out/f'phase6g1_{name}.csv',index=False,float_format='%.17g')


def build_results(out,forecasts,conc,drivers,now,diagnostics):
    principal=['D0','D1','D2','E0','E1','E2']
    common=d.common_sample(forecasts,principal)
    samples={'EXTENDED_PRINCIPAL_COMMON':common,'ORIGINAL_HOLDOUT_PRINCIPAL_COMMON':common.loc[common.target_quarter.ge('2025Q3')],
        'REAL_M2_PAIRWISE_COMMON':d.common_sample(forecasts,['D0','D3','E0','E3']),
        'PHASE6G_REFERENCE_44':d.common_sample(forecasts,['D0','D2','E0','E2']),
        'ORIGINAL_HOLDOUT_REFERENCE_12':d.common_sample(forecasts.loc[forecasts.target_quarter.ge('2025Q3')],['D0','D2','E0','E2'])}
    metric=[d.metrics(forecasts,'FULL_PAIRWISE_AVAILABLE')]
    for sample,f in samples.items():
        if len(f):metric.append(d.metrics(f,sample))
    metrics=pd.concat(metric,ignore_index=True);save(out,'horizon_metrics',metrics)
    compare=[]
    for (sample,model),g in metrics.groupby(['sample','model']):
        r=g.loc[g.horizon.eq('POOLED')].iloc[0]
        current=now.loc[now.model.eq('D'+model[-1])].iloc[0]
        compare.append(dict(model=model,description={'0':'Current','1':'No M2','2':'M2-L2','3':'Real M2'}[model[-1]],sample=sample,
            predictor_count=7 if model[-1]=='1' else 8,N=r.N,H1_RMSE=g.loc[g.horizon.eq('H1'),'RMSE'].iloc[0] if g.horizon.eq('H1').any() else None,
            H2_RMSE=g.loc[g.horizon.eq('H2'),'RMSE'].iloc[0] if g.horizon.eq('H2').any() else None,
            H3_RMSE=g.loc[g.horizon.eq('H3'),'RMSE'].iloc[0] if g.horizon.eq('H3').any() else None,
            pooled_RMSE=r.RMSE,MAE=r.MAE,bias=r.bias,median_absolute_error=r.median_absolute_error,max_absolute_error=r.max_absolute_error,
            OOS_R2_vs_D0=r.OOS_R2 if model.startswith('D') else None,OOS_R2_vs_E0=r.OOS_R2 if model.startswith('E') else None,
            current_DFM_nowcast=current.DFM_nowcast,current_50_50_ensemble=current.ensemble_nowcast,
            delta_RMSE_vs_D0=r.delta_RMSE if model.startswith('D') else None,delta_RMSE_vs_E0=r.delta_RMSE if model.startswith('E') else None,
            relative_RMSE_change_pct=r.relative_RMSE_change_pct,status='RESEARCH_ONLY_NOT_FULL_VINTAGE_REAL_TIME',evidence_class=d.CAVEAT))
    comparison=pd.DataFrame(compare);save(out,'model_comparison',comparison.loc[comparison.model.str.startswith('D')]);save(out,'ensemble_comparison',comparison.loc[comparison.model.str.startswith('E')])
    loo=[]
    for sample,f in samples.items():
        if sample.endswith(('REFERENCE_44','REFERENCE_12')):continue
        for q in sorted(f.target_quarter.unique()):
            m=d.metrics(f.loc[f.target_quarter.ne(q)],sample)
            for r in m.loc[m.horizon.eq('POOLED')&~m.model.isin(['D0','E0'])].itertuples():
                loo.append(dict(sample=sample,model=r.model,excluded_quarter=q,benchmark_RMSE=r.benchmark_RMSE,challenger_RMSE=r.RMSE,delta_RMSE=r.delta_RMSE,challenger_better=r.delta_RMSE<0,evidence_class=d.CAVEAT))
    save(out,'leave_one_quarter_out',loo)
    # Existing development/holdout boundary, not a searched regime split.
    subs=[]
    for era,mask in [('EARLIER_DEVELOPMENT',common.target_quarter.lt('2025Q3')),('LATER_ORIGINAL_HOLDOUT',common.target_quarter.ge('2025Q3'))]:
        subs.append(d.metrics(common.loc[mask],era))
    save(out,'subsample_metrics',pd.concat(subs))
    current=conc.loc[conc.current&conc.model.eq('D0')].iloc[0]
    hist=conc.loc[~conc.current&conc.model.eq('D0')]
    stats=[d.distribution(hist[col],current[col],col) for col in ['m2_signal_share_pct','m2_loading_share_pct','m2_zscore','signal_HHI']]
    h3=hist.loc[hist.horizon.eq('H3')]
    stats.append(d.distribution(h3.m2_signal_share_pct,current.m2_signal_share_pct,'m2_signal_share_pct_H3_ONLY'))
    z=drivers.loc[drivers.model.eq('D0')&drivers.indicator.eq('m2')]
    zh=z.loc[~z.current];zc=z.loc[z.current].iloc[0]
    stats.append(d.distribution(zh.latest_standardized_value,zc.latest_standardized_value,'latest_M2_zscore'))
    stats=pd.DataFrame(stats);save(out,'dominance_distribution',stats)
    save(out,'m2_zscores',z[['forecast_origin','target_quarter','horizon','current','latest_period','standardized_current_value','latest_standardized_value','training_mean','training_std','months_available','evidence_class']])
    loading=drivers.loc[~drivers.current].groupby(['model','indicator']).factor_loading.agg(['mean','median','std','min','max']).reset_index()
    share=drivers.loc[~drivers.current].groupby(['model','indicator']).absolute_loading_share_pct.mean().reset_index(name='mean_absolute_loading_share_pct')
    current_load=drivers.loc[drivers.current,['model','indicator','factor_loading']].rename(columns={'factor_loading':'current_loading'})
    # Use sign-aligned loadings for cross-model summary.
    ld=pd.read_csv(out/'phase6g1_factor_loadings.csv')
    loading=ld.loc[~ld.current].groupby(['model','indicator']).factor_loading.agg(['mean','median','std','min','max']).reset_index()
    current_load=ld.loc[ld.current,['model','indicator','factor_loading']].rename(columns={'factor_loading':'current_loading'})
    save(out,'loading_summary',loading.merge(share,on=['model','indicator']).merge(current_load,on=['model','indicator']))
    availability=hist[['m2_signal_share_pct','available_indicator_count','available_target_quarter_month_count']].dropna()
    associations=[]
    for field in ['available_indicator_count','available_target_quarter_month_count']:
        associations.append(dict(comparison=field,N=len(availability),correlation=availability.m2_signal_share_pct.corr(availability[field]),
            note='Association, not causal attribution; excludes absent M2 signals',evidence_class=d.CAVEAT))
    median_available=availability.available_indicator_count.median()
    for name,g in [('AT_LEAST_MEDIAN_COVERAGE',availability.loc[availability.available_indicator_count.ge(median_available)]),
                   ('BELOW_MEDIAN_COVERAGE',availability.loc[availability.available_indicator_count.lt(median_available)])]:
        associations.append(dict(comparison=name,N=len(g),mean_M2_signal_share_pct=g.m2_signal_share_pct.mean(),median_available_indicator_cutoff=median_available,evidence_class=d.CAVEAT))
    save(out,'ragged_edge_associations',associations)
    # Within each observed historical chart remove POS only from its denominator.
    # This is descriptive re-normalization, not a model refit or missing-data fill.
    pos_effect=[]
    base=drivers.loc[~drivers.current&drivers.model.eq('D0')]
    for keys,g in base.groupby(d.KEYS):
        m=g.loc[g.indicator.eq('m2')].iloc[0];p=g.loc[g.indicator.eq('pos_turnover')].iloc[0]
        if pd.isna(m.descriptive_signal) or pd.isna(p.descriptive_signal):continue
        den=g.descriptive_signal.abs().sum(min_count=1)
        without=den-abs(p.descriptive_signal)
        if without>0:pos_effect.append(dict(target_quarter=keys[0],horizon=keys[1],actual_M2_share_pct=m.absolute_signal_share_pct,
            observed_POS_signal=p.descriptive_signal,M2_share_without_POS_pct=100*abs(m.descriptive_signal)/without,
            share_change_pct=100*abs(m.descriptive_signal)/without-m.absolute_signal_share_pct,
            interpretation='Historical observed-signal denominator removal only; does not estimate current missing POS or causal effect',evidence_class=d.CAVEAT))
    save(out,'pos_denominator_sensitivity',pos_effect)
    pooled=metrics.loc[metrics['sample'].eq('EXTENDED_PRINCIPAL_COMMON')&metrics.horizon.eq('POOLED')].set_index('model')
    no_m2_better=pooled.loc['D1','delta_RMSE']<0 and pooled.loc['E1','delta_RMSE']<0
    no_m2_worse=pooled.loc['D1','delta_RMSE']>0 and pooled.loc['E1','delta_RMSE']>0
    diagnosis='M2_DOMINANT_BUT_USEFUL' if no_m2_worse else 'M2_DOMINANT_AND_HARMFUL' if no_m2_better else 'M2_EVIDENCE_MIXED'
    # Forecast evidence and eras can disagree; do not equate dominance with harm.
    era=pd.concat(subs);r=era.loc[era.model.eq('D1')&era.horizon.eq('POOLED')]
    if r.delta_RMSE.lt(0).any() and r.delta_RMSE.gt(0).any():diagnosis='M2_EVIDENCE_MIXED'
    recommendation=dict(classification=diagnosis,recommendation='KEEP_CURRENT_DFM_AND_MONITOR_M2',automatic_promotion=False,
        current_share_range=stats.loc[stats.statistic.eq('m2_signal_share_pct'),'descriptive_range'].iloc[0],
        historical_value_vintages_verified=False,evidence_class=d.CAVEAT,
        reason='Fixed-specification accuracy, subsample and ragged-edge evidence; no challenger automatically advances or replaces production')
    dump(out/'phase6g1_recommendation.json',recommendation)
    write_report(out,comparison,metrics,conc,drivers,stats,diagnostics,pd.DataFrame(loo),recommendation,now,pd.DataFrame(associations),pd.DataFrame(pos_effect))
    return recommendation


def write_report(out,comparison,metrics,conc,drivers,stats,diagnostics,loo,rec,now,associations,pos_effect):
    c=conc.loc[conc.current&conc.model.eq('D0')].iloc[0];h=conc.loc[~conc.current&conc.model.eq('D0')]
    reconstruction=pd.read_csv(out/'phase6g1_m2_signal_reconstruction.csv');m=drivers.loc[drivers.current&drivers.model.eq('D0')&drivers.indicator.eq('m2')].iloc[0]
    ss=stats.set_index('statistic');dr=drivers.loc[drivers.current]
    lines=['# Phase 6G.1 — M2 dominance audit','',
        'Research only. Phase 6E production and its dashboard remain unchanged. No challenger is promoted. This is availability-aware pseudo-real-time, not fully vintage-real-time; predictor revision-value leakage remains unresolved.',
        '## Exact reconstruction and signal meaning','',
        f'The dashboard quarterly M2 signal is exactly reproducible: **{m.descriptive_signal:.12f}**, with current absolute signal share **{m.absolute_signal_share_pct:.9f}%** and absolute loading share **{m.absolute_loading_share_pct:.9f}%**. The latest-month signal is {m.latest_standardized_value*m.factor_loading:.12f}; it is a different quantity. Phase 6E DFM/U-MIDAS/ensemble, Phase 6F M2-L2 and both Phase 6G extended benchmark RMSEs are refitted and checked before challenger interpretation.',
        '| Month | Raw M2 (billion UZS) | YoY log value | Training mean | Training SD | z | Loading |','|---|---:|---:|---:|---:|---:|---:|']
    for r in reconstruction.itertuples():lines.append(f'| {r.reference_period} | {r.raw_M2_level:.9f} | {r.transformed_value:.9f} | {r.training_mean:.9f} | {r.training_std:.9f} | {r.standardized_value:.9f} | {r.factor_loading:.9f} |')
    lines += ['',f'Training-only mean {m.training_mean:.12f}, SD {m.training_std:.12f}; target-quarter mean z {m.standardized_current_value:.12f}; sign-aligned loading {m.factor_loading:.12f}. Two released Q3 M2 observations (July/August), arithmetic mean aggregation: mean(z_Jul,z_Aug) × loading = {m.descriptive_signal:.12f}. Latest transformed August value is {reconstruction.transformed_value.iloc[-1]:.12f}.',
        f'The signal denominator is {reconstruction.absolute_signal_sum.iloc[0]:.12f}, from exactly {reconstruction.denominator_indicators.iloc[0]}. POS has no Q3 signal and remains null. Loading share instead includes all eight estimated loadings, including POS. Loading share = |loading_i|/Σ|loading_j|. Signal share = |mean released-quarter z_i × loading_i|/Σ|available signals_j|.',
        'Neither share is a GDP contribution. The bridge has a valid additive intercept/factor/GDP-lag design, but an individual loading × current z is not the filtered factor’s full historical/state contribution. No per-indicator GDP contribution is fabricated; **0.726 is not +0.726 pp GDP**.',
        '## Coverage and source audit','',
        '| Indicator | Latest usable month | Q3 months | Missing months | Q3 mean z | Loading | Signal | Share % |','|---|---|---:|---:|---:|---:|---:|---:|']
    for r in dr.loc[dr.model.eq('D0')].itertuples():
        z='Unavailable' if pd.isna(r.standardized_current_value) else f'{r.standardized_current_value:.6f}'
        signal='Unavailable' if pd.isna(r.descriptive_signal) else f'{r.descriptive_signal:.6f}'
        share='Unavailable' if pd.isna(r.absolute_signal_share_pct) else f'{r.absolute_signal_share_pct:.3f}'
        lines.append(f'| {r.indicator} | {r.latest_period} | {r.months_available} | {r.missing_months} | {z} | {r.factor_loading:.6f} | {signal} | {share} |')
    lines += ['', 'POS stops at 2024-12 because the frozen Phase 6D input adapter explicitly rejects post-2024-12 records and requires scope verification. Newer CBU POS/BC/ATM archive records exist through 2026-06 in metadata; they are not verified as comparable POS-only production inputs. Some newer clean values also have missing-flow/extreme-change flags. This is an intentional scope guard, not a silently abandoned updater. No replacement is made.',
        'August industrial production exists in the approved official SIAT 577 archive: raw physical-volume index 108.0, clean growth 8.0. Its assumed release date is Aug31 + 33 days = Oct3, after the frozen nominal H3 Sep30 cutoff. The Oct5 late-init production snapshot retains the H3 mask, so July is correctly its latest usable month. This is not an August ingestion omission. The approved comparison contains no September real-index observation; repository absence does not prove live official publication delay.',
        'The dashboard bars renderer uses a zero-width visual bar for a null signal but labels it Unavailable and excludes it from the numerical denominator. That is not an observed zero. DFM input cells remain NaN; EM likelihood and filtered Kalman states handle missing observations. A stale POS history can affect estimated loadings/dynamics without providing a current Q3 measurement.',
        '## Historical dominance and standardization','',
        '| Statistic | N | Mean | Median | SD | Min | Max | p25 | p75 | p90 | Current | Current percentile |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in stats.itertuples():lines.append(f'| {r.statistic} | {r.N} | {r.mean:.4f} | {r.median:.4f} | {r.std:.4f} | {r.min:.4f} | {r.max:.4f} | {r.p25:.4f} | {r.p75:.4f} | {r.p90:.4f} | {r.current:.4f} | {r.current_percentile:.2f} |')
    largest=int(h.largest_signal_indicator.eq('m2').sum());observed=h.m2_signal_share_pct.dropna()
    lines += ['',f'Current M2 share is classified {ss.loc["m2_signal_share_pct","descriptive_range"]}: percentile {ss.loc["m2_signal_share_pct","current_percentile"]:.2f} across observed historical signals; horizon-matched H3 percentile {ss.loc["m2_signal_share_pct_H3_ONLY","current_percentile"]:.2f}. Descriptive labels use the empirical p75/p90, not a forecasting threshold. M2 is the largest signal at {largest}/{len(h)} origins ({100*largest/len(h):.2f}%). Share is defined at {len(observed)} of the 44 origins; missing Q3 M2 signals remain null, not zero.',
        f'Historical average signal HHI {h.signal_HHI.mean():.6f}; current HHI {c.signal_HHI:.6f}; current percentile {ss.loc["signal_HHI","current_percentile"]:.2f}.']
    for cutoff in [40,50,60]:lines.append(f'M2 share exceeds {cutoff}% at {int(observed.gt(cutoff).sum())}/{len(observed)} observed-share origins ({100*observed.gt(cutoff).mean():.2f}%), or {100*observed.gt(cutoff).sum()/len(h):.2f}% of all 44 candidate origins. Thresholds are descriptive only.')
    z=drivers.loc[~drivers.current&drivers.model.eq('D0')&drivers.indicator.eq('m2'),'latest_standardized_value'].dropna()
    lines.append(f'Latest-observation training z: current {m.latest_standardized_value:.6f}; {int(z.abs().gt(2).sum())} historical |z|>2, {int(z.abs().gt(3).sum())} |z|>3. Quarterly mean z is {m.standardized_current_value:.6f}. The current M2 observation is not an extreme |z|>2 event; its large loading and uneven observed-signal denominator must be distinguished from an extreme raw monetary-growth observation. No clipping/winsorization occurs.')
    lines+=['','## Ragged edge and POS denominator','']
    for r in associations.to_dict('records'):lines.append(f'{r["comparison"]}: N={r["N"]}; '+(f'correlation {r.get("correlation",np.nan):.6f}.' if pd.notna(r.get('correlation')) else f'mean M2 share {r.get("mean_M2_signal_share_pct",np.nan):.6f}%.'))
    lines.append('These associations exclude unavailable M2 signals and are descriptive; horizon and monetary era are confounded. They do not establish that ragged-edge missingness primarily causes M2 dominance. The current missing POS contribution cannot be identified without a valid released current POS observation.')
    if len(pos_effect):lines.append(f'For historical charts with both observed M2 and POS signals, removing only the observed POS term from the denominator increases M2 share by mean {pos_effect.share_change_pct.mean():.6f} pp, maximum {pos_effect.share_change_pct.max():.6f} pp. This shows denominator sensitivity; it does not assign that historical POS value to 2026Q3 or estimate a current causal effect.')
    lines += ['', '## Forecast tests — extended sample has priority','',
        '| Sample | Model | N | H1 RMSE | H2 RMSE | H3 RMSE | Pooled RMSE | Δ vs matched benchmark |','|---|---|---:|---:|---:|---:|---:|---:|']
    for r in comparison.loc[comparison['sample'].ne('FULL_PAIRWISE_AVAILABLE')].itertuples():
        delta=r.delta_RMSE_vs_D0 if r.model.startswith('D') else r.delta_RMSE_vs_E0
        lines.append(f'| {r.sample} | {r.model} | {r.N} | {r.H1_RMSE:.6f} | {r.H2_RMSE:.6f} | {r.H3_RMSE:.6f} | {r.pooled_RMSE:.6f} | {delta:.6f} |')
    lines += ['', 'D0/D1/D2 and E0/E1/E2 share identical principal origins. Challenger failures are excluded from all principal comparison models. The original 12-origin holdout is reported separately. Full pairwise and real-M2 comparisons use exact matched benchmark origins; no unequal-sample RMSE difference supports a conclusion.',
        'D1 fails the original unchanged convergence/stability gate at eight Phase 6G origins: 2022Q3 H2/H3 and all six 2025Q3/2025Q4 horizons. Consequently the principal D0/D1/D2 comparison has 36 extended origins and only six common original-holdout origins. The full 44-origin D0/D2 Phase 6G reference and original 12-origin D0/D2 holdout reference are retained in separate rows. Missing D1 forecasts are never filled or treated as numerical errors to score. Failure coverage is itself a limitation of the no-M2 challenger.',
        'D3 uses existing official SIAT monthly CPI: real M2 YoY log = nominal M2 YoY log − Σ of twelve consecutive monthly 100 ln(CPI_index/100) values. Each parent is publication-masked before transformation, and gaps invalidate a twelve-month sum. CPI begins January 2021; YoY inflation first exists December 2021, materially reducing D3’s balanced training history. D3 is therefore assessed on a separate reduced common sample rather than shrinking the main 44-origin question. Both baseline and real-M2 scores on that reduced sample are reported. CPI’s 2026 methodology change and revised-snapshot limitation remain.',
        'Earlier/later eras use the pre-existing 2025Q3 development/holdout boundary, not a searched break date. Earlier results overlap specification development and are retrospective robustness, not independent prospective validation. Bias is actual minus forecast; OOS R² = 1 − SSE_challenger/SSE_matched_baseline, positive improvement, negative worse.',
        '## Loadings, factors and bridge','']
    current_diag=diagnostics.loc[diagnostics.current].set_index('model')
    for model in ['D0','D1','D2','D3']:
        if model not in current_diag.index:continue
        r=current_diag.loc[model];g=dr.loc[dr.model.eq(model)]
        top=g.loc[g.absolute_loading_share_pct.idxmax()];top_signal=g.loc[g.absolute_signal_share_pct.idxmax()]
        lines.append(f'{model}: current factor correlation with D0 {r.factor_correlation_vs_D0:.6f}, factor SD {r.factor_std:.6f}, empirical persistence {r.factor_empirical_AR1:.6f}, fitted AR(2) ({r.factor_AR2_L1:.6f}, {r.factor_AR2_L2:.6f}), range [{r.factor_min:.6f}, {r.factor_max:.6f}], sign alignment {r.diagnostic_alignment_sign}. Largest loading {top.indicator} ({top.absolute_loading_share_pct:.2f}%); largest observed quarterly signal {top_signal.indicator} ({top_signal.absolute_signal_share_pct:.2f}%).')
    lines.append('Sign-aligned loadings are summarized with mean/median/SD/min/max, current loading and mean absolute share. Drivers retain their fitted factor orientation, so forecasts and within-model absolute shares do not change under diagnostic alignment. D1 cannot contain M2; it uses seven predictors and the unchanged one-factor AR(2) system. No M2 is added separately to the bridge. Removing one predictor can transfer dominance rather than guarantee balance; compare D1’s concentration and variable shares with D0.')
    lines.append('For D2, latest_period records the underlying source M2 month; latest_factor_cell_period records its two-month-later assignment in the factor design. Thus the lag does not create a new dated M2 observation. Monthly counts refer to occupied factor-design cells in the target quarter.')
    for indicator in ['industrial_production','pos_turnover','usd_uzs','rub_uzs']:
        g0=dr.loc[dr.model.eq('D0')&dr.indicator.eq(indicator)].iloc[0];g1=dr.loc[dr.model.eq('D1')&dr.indicator.eq(indicator)].iloc[0]
        lines.append(f'{indicator}: current absolute loading share D0 {g0.absolute_loading_share_pct:.3f}% → D1 {g1.absolute_loading_share_pct:.3f}%. POS remains without Q3 observations in both models.')
    bridge=pd.read_csv(out/'phase6g1_bridge_diagnostics.csv');b=bridge.loc[bridge.current]
    for model,g in b.groupby('model'):
        row=g.iloc[0]
        terms=', '.join(f'{r.term}={r.coefficient:.6f} (SE {r.standard_error:.6f})' for r in g.itertuples())
        lines.append(f'Current {model} bridge: {terms}; condition {row.condition_number:.4f}, max non-intercept VIF {g.VIF.max():.4f}, DW {row.Durbin_Watson:.4f}, leverage max {row.max_leverage:.4f}, Cook max {row.max_Cooks_distance:.4f}. SEs are descriptive in the small quarterly sample.')
    for model in ['D1','E1','D2','E2','D3','E3']:
        g=loo.loc[loo.model.eq(model)&loo['sample'].eq('EXTENDED_PRINCIPAL_COMMON' if model[-1]!='3' else 'REAL_M2_PAIRWISE_COMMON')]
        if len(g):lines.append(f'{model} leave-one-quarter-out: all exclusions improve={bool(g.challenger_better.all())}; ΔRMSE range {g.delta_RMSE.min():.6f} to {g.delta_RMSE.max():.6f}.')
    lines += ['', 'Training-period correlations of nominal M2 and M2-L2 with each other input are in phase6g1_m2_correlations.csv. They assess duplicated associations, not causality. Factor comparisons and bridge diagnostics provide conditional evidence; neither identifies a causal monetary effect.',
        '## Current nowcasts and decision','', '| Model | DFM nowcast | Fixed 50/50 ensemble | Δ ensemble vs production |','|---|---:|---:|---:|']
    for r in now.itertuples():lines.append(f'| {r.model} | {r.DFM_nowcast:.9f} | {r.ensemble_nowcast:.9f} | {r.difference_vs_production:.9f} |')
    lines += ['', 'Current estimates use the exact archived Oct5 Phase 6E information identity and fixed H3 mask. No refresh or promotion is performed. No missing POS signal is filled with zero or historical values. A large descriptive share alone cannot establish either usefulness or harm; matched extended-history performance, era stability and coverage must carry the model conclusion.',
        f'Diagnosis: {rec["classification"]}. Recommendation: {rec["recommendation"]}. Keep nominal M2 under monitoring; no direct production promotion or M2-L2 promotion follows this audit. Historical value vintages and comparable modern POS scope remain unresolved.',
        'Reproduce: `.venv/Scripts/python.exe -m scripts.phase6g1.run`. Exact numerical rerun, test and protected-hash evidence are attached separately after completed validation.',
        'M2 DIAGNOSIS:',rec['classification'],'MODEL RECOMMENDATION:',rec['recommendation']]
    text='\n\n'.join(lines)+'\n';text=re.sub(r'(?m)(^\|[^\n]*)\n\n(?=\|)',r'\1\n',text)
    text=text.replace('M2 DIAGNOSIS:\n\n','M2 DIAGNOSIS:\n').replace('MODEL RECOMMENDATION:\n\n','MODEL RECOMMENDATION:\n')
    (out/'phase6g1_results.md').write_text(text,encoding='utf8')
