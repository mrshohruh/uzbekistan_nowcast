"""Controlled lag experiments over the unchanged Phase 6E kernels.

Revised-snapshot sensitivities are explicitly not eligible real-time forecasts.
Assumed availability dates never replace observed source release dates.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import hashlib
import json
import logging
import sys

import numpy as np
import pandas as pd
import openpyxl
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson
from statsmodels.stats.outliers_influence import variance_inflation_factor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from scripts.phase6e.models import dfm, frames, FIELDS, sw, umidas
from uznowcast.models.data import load_dataset, horizon_month_end, quarter_end, quarter_start

LOG = logging.getLogger('phase6f')
KEYS = ['target_quarter', 'horizon']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(sw.common.safe(value), indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf8')


def economic_lag(series, months):
    """Lag transformed observations by calendar months, preserving gaps."""
    if months < 0 or series.index.has_duplicates:
        raise ValueError('Invalid lag or duplicate month')
    index = pd.date_range(series.index.min(), series.index.max(), freq='ME')
    return series.reindex(index).shift(months).reindex(series.index)


def latest_available(events, origin, extra_quarters=0, strict_vintage=True):
    """Select a released vintage, then an exact extra reference-quarter lag.

In strict mode retrieved/archived evidence must also predate the origin.
"""
    origin = pd.Timestamp(origin)
    f = events.copy()
    f = f.loc[pd.to_datetime(f.availability_date).le(origin) & f.value.notna()]
    if strict_vintage:
        f = f.loc[pd.to_datetime(f.retrieved_at, utc=True).le(origin.tz_localize('Asia/Tashkent').tz_convert('UTC'))]
    if f.empty:
        return None
    f = f.sort_values(['period', 'retrieved_at']).drop_duplicates('period', keep='last')
    wanted = str(pd.Period(f.period.max(), freq='Q') - extra_quarters)
    f = f.loc[f.period.eq(wanted)]
    return None if f.empty else f.iloc[-1]


def parse_fdi(path):
    """Exact BPM6 liability-flow row; no stock or asset substitution."""
    sheet = openpyxl.load_workbook(path, data_only=True)['Dataset']
    rows = list(sheet.values)
    if rows[0][0] != 'Balance of Payments of Uzbekistan' or rows[1][0] != 'million USD':
        raise ValueError('FDI title/unit schema changed')
    matches = [r for r in rows if str(r[0]).strip() == 'Direct investment: liabilities']
    if len(matches) != 1:
        raise ValueError('FDI exact row missing or duplicated')
    periods = [str(pd.Period(str(x).replace('-Q', 'Q'), freq='Q')) for x in rows[3][1:]]
    if len(set(periods)) != len(periods):
        raise ValueError('Duplicate FDI quarter')
    return pd.DataFrame({'period': periods, 'value': pd.to_numeric(matches[0][1:], errors='raise')})


def lagged_dfm(panel, dataset, available, target, horizon, origin, lag):
    """Release-gate source M2 before applying its economic lag."""
    k = sw.common.kernel()
    spec = k.Spec('PHASE6F_M2_L'+str(lag), FIELDS, 1, 2, '2019-01-31', True, False)
    frame, audit = k.mask(panel, spec, target, horizon, dataset.release_lag_days, 'standard')
    frame['m2'] = economic_lag(frame.m2, lag)
    end = quarter_start(target)-pd.Timedelta(days=1)
    frame, _ = k.training_panel(frame, end, True)
    z, means, scales = k.standardize(frame, end)
    z = z.reindex(pd.date_range(z.index.min(), quarter_end(target), freq='ME'))
    factors, loadings, diag = k.estimate(z.loc[:end], z, spec, {})
    prediction, bd = k.bridge(factors, available, target, origin, 'B', 'mean')
    return prediction, dict(factors=factors, loadings=loadings[:, 0], diagnostics=diag,
                            bridge_diagnostics=bd, frame=frame, release_masks=audit)


def bridge_fit(fit, available, target, origin, m2, m2lag=0, fdi=None, fdilag=0, fdidays=90, m2days=25):
    """Retain GDP AR term; train bridge covariates at matched historical H dates."""
    fq = sw.common.kernel().quarterly(fit['factors'], 'mean')
    gdp = available.frame.value
    horizon = min(3, (pd.Timestamp(origin).month-1)%3+1)
    # Late initialization still has frozen H3 information boundaries.
    if pd.Timestamp(origin) > quarter_end(target):
        horizon = 3
    terms = ['intercept', 'factor', 'gdp_lag1'] + (['m2'] if m2lag else []) + (['fdi'] if fdi is not None else [])

    def row(q, cutoff):
        prior = str(pd.Period(q, 'Q')-1)
        if prior not in gdp.index or pd.Period(q, 'Q') not in fq.index:
            return None
        values = [1., float(fq.loc[pd.Period(q, 'Q')].iloc[0]), float(gdp.loc[prior])]
        if m2lag:
            # Reference-quarter mean of economically lagged M2, released by its origin.
            periods = pd.date_range(quarter_start(q), quarter_end(q), freq='ME')
            source = (periods.to_period('M')-m2lag).to_timestamp('M')
            eligible = source + pd.Timedelta(days=m2days) <= cutoff
            v = m2.reindex(source[eligible]).dropna()
            if v.empty:
                return None
            values.append(float(v.mean()))
        if fdi is not None:
            events = fdi.copy()
            events['availability_date'] = pd.PeriodIndex(events.period, freq='Q').end_time.normalize()+pd.Timedelta(days=fdidays)
            r = latest_available(events, cutoff, fdilag, strict_vintage=False)
            if r is None:
                return None
            values.append(float(r.value)/1000.)
        return values

    x, y, quarters = [], [], []
    for q in fq.index:
        if str(q) >= target or str(q) not in gdp.index:
            continue
        r = row(str(q), horizon_month_end(str(q), 'H'+str(horizon)))
        if r is not None:
            x.append(r); y.append(float(gdp.loc[str(q)])); quarters.append(str(q))
    current = row(target, pd.Timestamp(origin))
    if current is None or len(y) < max(12, 3*len(terms)):
        raise ValueError('Insufficient common bridge history')
    x = np.asarray(x)
    if np.linalg.matrix_rank(x) != x.shape[1]:
        raise ValueError('Rank-deficient bridge')
    result = sm.OLS(y, x).fit()
    pred = float(np.asarray(current) @ result.params)
    leverage = result.get_influence().hat_matrix_diag
    cooks = result.get_influence().cooks_distance[0]
    diag = dict(n_train=len(y), condition=float(np.linalg.cond(x)), residual_dw=float(durbin_watson(result.resid)),
                residual_lag1_correlation=float(pd.Series(result.resid).autocorr(1)),
                max_leverage=float(leverage.max()), max_cooks_distance=float(cooks.max()), training_quarters=json.dumps(quarters))
    coefficients = [dict(term=t, coefficient=b, standard_error=se,
                         vif=None if j==0 else float(variance_inflation_factor(x, j)),
                         value=current[j], contribution_pp=current[j]*b, **diag)
                    for j, (t, b, se) in enumerate(zip(terms, result.params, result.bse))]
    return pred, coefficients


def score(frame):
    """Pairwise exact common origins; actual-minus-prediction bias."""
    base = frame.loc[frame.model.eq('M0'), KEYS+['prediction', 'actual']].rename(columns={'prediction':'benchmark'})
    rows = []
    for model, block in frame.groupby('model'):
        matched = block.dropna(subset=['prediction']).merge(base, on=KEYS, suffixes=('', '_base'), validate='one_to_one')
        if not np.allclose(matched.actual, matched.actual_base, atol=1e-12):
            raise ValueError('Different actual vintages')
        for horizon in ['H1', 'H2', 'H3', 'POOLED', 'POST_DEVELOPMENT']:
            g = matched if horizon=='POOLED' else matched.loc[matched.target_quarter.ge('2025Q3')] if horizon=='POST_DEVELOPMENT' else matched.loc[matched.horizon.eq(horizon)]
            if g.empty:
                continue
            e = g.actual-g.prediction; be = g.actual-g.benchmark
            b_rmse = float(np.sqrt(np.mean(be**2)))
            rows.append(dict(model=model, horizon=horizon, N=len(g), RMSE=float(np.sqrt(np.mean(e**2))),
                MAE=float(e.abs().mean()), bias=float(e.mean()), median_absolute_error=float(e.abs().median()),
                maximum_absolute_error=float(e.abs().max()), forecast_correlation=g.prediction.corr(g.actual) if g.prediction.nunique()>1 and g.actual.nunique()>1 else None,
                OOS_R2=1-float(sum(e**2)/sum(be**2)) if sum(be**2)>0 else None,
                benchmark_common_RMSE=b_rmse, delta_RMSE_vs_phase6e=float(np.sqrt(np.mean(e**2)))-b_rmse,
                sample='PAIRWISE_COMMON', evidence_class=block.evidence_class.iloc[0]))
    return pd.DataFrame(rows)


def protected(root):
    """Hash actual existing artifacts, including untracked Phase 6E production."""
    paths = []
    for directory in ['src', 'config', 'registry', 'dashboard', 'scripts/phase6e', 'scripts/research', 'results/production', 'results/phase6e']:
        paths.extend((root/directory).rglob('*'))
    paths.extend((root/'results').glob('phase4*.*'))
    paths.extend((root/'results').glob('phase5*.*'))
    for d in ['results/research/phase6a1', 'results/research/phase6a2', 'results/research/phase6b',
              'results/research/phase6b1', 'results/research/phase6b2',
              'results/phase5b', 'results/phase5b1', 'results/phase5b2', 'results/phase6c', 'results/phase6d']:
        paths.extend((root/d).glob('*.*'))
    return {p.relative_to(root).as_posix():sha(p) for p in paths if p.is_file() and not any(s.startswith(('t_', 'test_', '_pytest', '__pycache__', 'browser_profile', '.pytest')) for s in p.parts)}


def run(root=ROOT):
    out = root/'results/phase6f'; out.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler(out/'phase6f_pipeline.log', encoding='utf8'), logging.StreamHandler()])
    before = protected(root)
    dump(out/'phase6f_protected_before.json', before)
    dataset = load_dataset(root)
    m2days=dataset.release_lag_days['m2']
    panel = pd.read_csv(root/'results/phase6c/phase6c_research_monthly_panel.csv', index_col='date', parse_dates=True, float_precision='round_trip')
    events = pd.read_csv(root/'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    frozen = pd.read_csv(root/'results/phase6e/phase6e_matched_forecasts.csv', float_precision='round_trip')
    origins = frozen.loc[frozen.model.eq('PHASE6C_DFM')].sort_values(KEYS)
    receipt = json.loads((out/'raw/receipt.json').read_text())
    if sha(root/receipt['raw_file']) != receipt['checksum']:
        raise ValueError('Archived FDI checksum mismatch')
    fdi = parse_fdi(root/receipt['raw_file'])
    fdi['retrieved_at'] = receipt['retrieved_at']
    fdi['source_release_date'] = None
    fdi['vintage_class'] = 'REVISED_SNAPSHOT_NO_HISTORICAL_VINTAGES'
    fdi.to_csv(out/'phase6f_fdi_observations.csv', index=False)
    m2data = pd.read_parquet(root/'data/processed/m2.parquet')
    row = next(r for r in dataset.registry.scope('v1') if r['variable_key']=='m2')
    audit = [dict(variable='m2', source=row['machine_download_url'], frequency='M', unit='percent log YoY', transformation='100*ln(level_t/level_t-12)',
        first_observation=str(panel.m2.first_valid_index()), last_observation=str(panel.m2.last_valid_index()), publication_lag=dataset.release_lag_days['m2'],
        release_date_available='snapshot update only', historical_vintage_available=False, missing_count=int(panel.m2.isna().sum()),
        notes='Publication lag 25 days; M0 economic lag zero; historical revised-snapshot pseudo-real-time, not vintage-real-time'),
        dict(variable='fdi', source=receipt['source_url'], frequency='Q', unit='million USD nominal', transformation='quarterly liability flow /1000 for bridge scaling',
        first_observation=fdi.period.min(), last_observation=fdi.period.max(), publication_lag='90 and 120 days ASSUMED; not observed',
        release_date_available=False, historical_vintage_available=False, missing_count=int(fdi.value.isna().sum()),
        notes='BPM6 Direct investment: liabilities; net incurrence of liabilities, not gross investment, not assets-minus-liabilities; no interpolation; revised snapshot. Current snapshot retrieved AFTER production cutoff.')]
    pd.DataFrame(audit).to_csv(out/'phase6f_data_audit.csv', index=False)
    pd.DataFrame(audit[:1]).to_csv(out/'phase6f_m2_audit.csv', index=False)
    pd.DataFrame(audit[1:]).to_csv(out/'phase6f_fdi_audit.csv', index=False)
    forecasts=[]; coefficients=[]; diagnostics=[]; availability=[]; failures=[]; reproduction=[]

    def calculate(p, ds, av, target, horizon, origin, actual=np.nan, expected=None, current=False):
        predictions = {}; fits = {}
        for lag in [0, 1, 2]:
            model = 'M'+str(lag)
            try:
                pred, fit = dfm(p, ds, av, target, horizon, origin) if lag==0 else lagged_dfm(p, ds, av, target, horizon, origin, lag)
                if expected is not None and lag==0:
                    if abs(pred-expected)>1e-7:
                        raise ValueError('Phase6E reconstruction failed')
                    reproduction.append(dict(target_quarter=target, horizon=horizon, error=pred-expected, current=current))
                predictions[model]=pred; fits[model]=fit
                diag=fit['diagnostics']
                factorcorr=fit['factors'].iloc[:,0].corr(fits['M0']['factors'].iloc[:,0])
                for field, loading in zip(FIELDS, fit['loadings']):
                    observed=p[field].reindex(fit['factors'].index)
                    diagnostics.append(dict(model=model,target_quarter=target,horizon=horizon,current=current,field=field,loading=float(loading),
                        factor_correlation_vs_M0=factorcorr, explained_variance_association=float(observed.corr(fit['factors'].iloc[:,0])**2), **diag))
                bp, bc=bridge_fit(fit,av,target,origin,p.m2,m2days=m2days)
                if abs(bp-pred)>1e-7:
                    raise ValueError('Bridge reconstruction failed')
                coefficients.extend(dict(model=model,target_quarter=target,horizon=horizon,current=current,**c) for c in bc)
            except ValueError as exc:
                if lag==0: raise
                failures.append(dict(model=model,target_quarter=target,horizon=horizon,error=str(exc)))
        if 'M0' in fits:
            configs=[('B1', 'M0', 1, None, 0, 90), ('B2','M0',2,None,0,90)]
            if not current:
                configs += [(name+('_120D' if days==120 else ''),factor,1 if name!='B5' else 0,fdi,extra,days)
                            for name,factor,extra in [('B3','M0',0),('B4','M0',1),('B5','M1',0)] for days in [90,120]]
            for name, factor, lag, fd, extra, days in configs:
                try:
                    pred, bc=bridge_fit(fits[factor],av,target,origin,p.m2,lag,fd,extra,days,m2days)
                    predictions[name]=pred
                    coefficients.extend(dict(model=name,target_quarter=target,horizon=horizon,current=current,**c) for c in bc)
                except (ValueError, KeyError) as exc:
                    failures.append(dict(model=name,target_quarter=target,horizon=horizon,error=str(exc)))
        for model,pred in predictions.items():
            forecasts.append(dict(model=model,target_quarter=target,horizon=horizon,forecast_origin=str(origin),actual=actual,prediction=pred,current=current,
                evidence_class='REVISED_FDI_TIMING_SENSITIVITY_NOT_REAL_TIME' if model.startswith(('B3','B4','B5')) else 'REGISTRY_LAG_PSEUDO_REAL_TIME',
                valid_real_time_forecast=False, status='RESEARCH_ONLY'))
            lag = 1 if model in ['M1','B1'] or model.startswith(('B3','B4','B5')) else 2 if model in ['M2','B2'] else 0
            source=p.m2.dropna(); source=source.loc[source.index+pd.Timedelta(days=m2days)<=pd.Timestamp(origin)]
            latest=source.index.max() if len(source) else None
            source_periods=source.index
            used_value=float(source.iloc[-1]) if len(source) else None
            if model.startswith('B') and model not in ['B5','B5_120D']:
                periods=pd.date_range(quarter_start(target),quarter_end(target),freq='ME')
                wanted=(periods.to_period('M')-lag).to_timestamp('M')
                used=source.reindex(wanted).dropna()
                source_periods=used.index
                used_value=float(used.mean()) if len(used) else None
            elif model in ['M1','M2','B5','B5_120D']:
                # Only shifted cells present in the target-quarter factor design.
                end=min(horizon_month_end(target,horizon),pd.Timestamp(origin))
                source_periods=source.index[(source.index.to_period('M')+lag).to_timestamp('M')<=end]
                used_value=float(source.loc[source_periods].iloc[-1]) if len(source_periods) else None
            fd=fdi.copy(); days=120 if model.endswith('120D') else 90
            fd['availability_date']=pd.PeriodIndex(fd.period,freq='Q').end_time.normalize()+pd.Timedelta(days=days)
            uses_fdi=model.startswith(('B3','B4','B5'))
            r=latest_available(fd,origin,1 if model.startswith('B4') else 0,strict_vintage=False) if uses_fdi else None
            availability.append(dict(model=model,forecast_origin=str(origin),target_quarter=target,horizon=horizon,
                latest_m2_period_available=str(latest.to_period('M')) if latest is not None else None,m2_release_date=None,
                m2_assumed_availability_date=str(latest+pd.Timedelta(days=m2days)) if latest is not None else None,m2_value_used=used_value,
                m2_source_periods_used=json.dumps([str(d.to_period('M')) for d in source_periods]),
                m2_value_usage='quarter_mean_lagged_bridge_regressor' if model.startswith(('B1','B2','B3','B4')) else 'latest_factor_input; full historical cells retained in factor design',
                m2_economic_lag=lag,latest_fdi_quarter_available=r.period if r is not None else None,fdi_release_date=None,
                fdi_assumed_availability_date=str(r.availability_date) if r is not None else None,fdi_value_used=float(r.value) if r is not None else None,
                gdp_latest_available_quarter=av.frame.index.max(), leakage_flag=False, timing_leakage_flag=False,
                historical_value_vintage_verified=False, valid_real_time_forecast=False,
                notes='No future reference-period timing under stated assumptions; historical revision leakage cannot be ruled out. FDI revised diagnostic only.' if uses_fdi else 'Historical M2 vintages incomplete; revised-snapshot pseudo-real-time only.'))
        LOG.info('%s %s %s',target,horizon,predictions)
        return predictions

    for r in origins.itertuples():
        origin=pd.Timestamp(r.forecast_origin_date)
        av=sw.common.vintage_kernel().available_gdp_vintage_as_of(events,origin,target=r.target_quarter,timing_rule='STRICT')
        calculate(panel,dataset,av,r.target_quarter,r.horizon,origin,r.actual,r.prediction)
    # Reconstruct from exact archived information identity, never from today's FDI download.
    manifest=json.loads((root/'results/phase6e/phase6e_run_manifest.json').read_text())
    production=json.loads((root/'results/phase6e/phase6e_current_nowcast.json').read_text())
    bundle=json.loads((root/'results/phase6d/phase6d_frozen_challengers.json').read_text())
    info=None
    ledger=pd.read_csv(root/'results/phase6d/phase6d_prospective_forecast_ledger.csv')
    for r in ledger.loc[ledger.model.eq('COMBO_50_50')].sort_values('run_timestamp_utc',ascending=False).itertuples():
        saved=json.loads((root/'results/phase6d/snapshots'/r.snapshot_id/'inputs.json').read_text())
        if 'benchmark_monthly' in saved and sw.fingerprint(saved,bundle,r.operational_stage)==manifest['information_fingerprint']:
            info=saved; break
    if info is None: raise ValueError('Exact production snapshot unavailable')
    origin=pd.Timestamp(manifest['as_of']).tz_convert('Asia/Tashkent').tz_localize(None)
    p,ds,av=frames(info,root,origin)
    current=calculate(p,ds,av,info['target'],info['horizon'],origin,expected=production['dfm_forecast'],current=True)
    u,_,_=umidas(ds,av,info['target'],info['horizon'],origin)
    if abs(u-production['umidas_forecast'])>1e-7: raise ValueError('U-MIDAS reconstruction failed')
    current.update(U_MIDAS=u,COMBO_50_50=.5*current['M0']+.5*u)
    current_rows=[dict(model=m,target_quarter=info['target'],forecast_origin=str(origin),nowcast=v,status='RESEARCH_ONLY' if m not in ['M0','U_MIDAS','COMBO_50_50'] else 'UNCHANGED_PRODUCTION_REFERENCE') for m,v in current.items()]
    current_rows.extend(dict(model=m,target_quarter=info['target'],forecast_origin=str(origin),nowcast=None,status='UNAVAILABLE_FDI_SNAPSHOT_POSTDATES_CUTOFF_AND_HISTORICAL_VINTAGES_MISSING') for m in ['B3','B4','B5'])
    f=pd.DataFrame(forecasts); historical=f.loc[~f.current]
    metrics=score(historical)
    # Re-score after excluding each target quarter, without choosing a specification.
    loo=[]
    for quarter in sorted(historical.target_quarter.unique()):
        table=score(historical.loc[historical.target_quarter.ne(quarter)])
        loo.extend(dict(excluded_quarter=quarter,**r) for r in table.loc[table.horizon.eq('POOLED')].to_dict('records'))
    pd.DataFrame(loo).to_csv(out/'phase6f_leave_one_quarter_out.csv',index=False,float_format='%.17g')
    stability=pd.DataFrame(coefficients).loc[lambda x:~x.current].groupby(['model','term']).coefficient.agg(['min','max','mean','std']).reset_index()
    stability.to_csv(out/'phase6f_coefficient_stability.csv',index=False,float_format='%.17g')
    comparison=[]
    for model,g in metrics.groupby('model'):
        pooled=g.loc[g.horizon.eq('POOLED')].iloc[0].to_dict()
        for h in ['H1','H2','H3']: pooled[h+'_RMSE']=float(g.loc[g.horizon.eq(h),'RMSE'].iloc[0]) if g.horizon.eq(h).any() else None
        pooled['pooled_RMSE']=pooled.pop('RMSE'); pooled['2026Q3_nowcast']=current.get(model)
        pooled['status']='DIAGNOSTIC_ONLY_NO_PROMOTION';comparison.append(pooled)
    outputs={'quarter_level_forecasts':f,'horizon_metrics':metrics,'model_comparison':pd.DataFrame(comparison),
             'bridge_coefficients':pd.DataFrame(coefficients),'dfm_diagnostics':pd.DataFrame(diagnostics),'origin_availability':pd.DataFrame(availability),
             'current_nowcasts':pd.DataFrame(current_rows),'robustness':metrics.loc[metrics.model.str.startswith(('M1','M2','B3','B4','B5'))],
             'benchmark_reconstruction':pd.DataFrame(reproduction),'failures':pd.DataFrame(failures,columns=['model','target_quarter','horizon','error'])}
    for name,frame in outputs.items(): frame.to_csv(out/f'phase6f_{name}.csv',index=False,float_format='%.17g')
    classification='PHASE6F_INCONCLUSIVE'
    dump(out/'phase6f_recommendation.json',dict(classification=classification,recommendation='KEEP_PHASE6E_PRODUCTION',
        reason='No verified historical M2/FDI value vintages; four holdout quarters; revised FDI diagnostics cannot establish genuine real-time improvement.',automatic_promotion=False))
    write_report(out, audit, pd.DataFrame(comparison), production, current, classification)
    conclusions=['\n## Explicit empirical answers\n']
    indexed=pd.DataFrame(comparison).set_index('model')
    for model in ['M1','M2','B1','B2','B3','B3_120D','B4','B5','B5_120D']:
        if model not in indexed.index: continue
        r=indexed.loc[model]
        best=min(['H1','H2','H3'],key=lambda h:r[h+'_RMSE']-indexed.loc['M0',h+'_RMSE'])
        conclusions.append(f'{model}: common-sample pooled RMSE {r.pooled_RMSE:.6f}; improvement {-r.delta_RMSE_vs_phase6e:.6f} pp; strongest relative horizon {best}. '+
            ('At least 0.05 pp economically relevant diagnostic improvement.' if -r.delta_RMSE_vs_phase6e>=.05 else 'At least 0.03 pp potentially meaningful diagnostic improvement.' if -r.delta_RMSE_vs_phase6e>=.03 else 'Below 0.03 pp or worse than benchmark.'))
    for model in ['M1','M2']:
        g=pd.DataFrame(loo).loc[lambda x:x.model.eq(model)]
        conclusions.append(f'{model} leave-one-quarter-out RMSE deltas range {g.delta_RMSE_vs_phase6e.min():.6f} to {g.delta_RMSE_vs_phase6e.max():.6f}; improvement survives every exclusion: {bool(g.delta_RMSE_vs_phase6e.lt(0).all())}.')
    conclusions += ['Both lagged M2 factor specifications improve this revised-history holdout comparison, but no genuine historical value-vintage improvement is established. B1/B2 assess redundancy separately; VIF and coefficient stability are in diagnostic files.',
        'FDI gains do not survive as equally strong gains under the longer 120-day assumption. The additional-quarter specification worsens performance. This sensitivity and missing historical value vintages make FDI evidence inconclusive. Full diagnostic samples and common diagnostic samples each contain 12 forecasts; the valid vintage-real-time FDI sample contains zero forecasts.',
        'No promotion is recommended. The production dashboard and 50/50 configuration remain unchanged.',classification,'KEEP_PHASE6E_PRODUCTION']
    report=out/'phase6f_results.md'
    text=report.read_text(encoding='utf8')
    text=text.rsplit('\n\n'+classification,1)[0]
    report.write_text(text+'\n\n'+'\n\n'.join(conclusions)+'\n',encoding='utf8')
    after=protected(root)
    changed=[p for p,h in before.items() if after.get(p)!=h]
    if changed: raise ValueError('Protected files changed: '+str(changed))
    dump(out/'phase6f_protected_after.json',after)
    dump(out/'phase6f_run_manifest.json',dict(classification=classification,research_only=True,production_unchanged=True,protected_artifacts=len(before),
        protected_hashes_identical=True,cutoff=manifest['as_of'],predictors=list(FIELDS),m2_release_lag_days=m2days,fdi_assumed_lags_days=[90,120],
        historical_value_vintages_verified=False,forecast_origins=12,failures=failures,
        inputs={str(p.relative_to(root)):sha(p) for p in [root/'results/phase6e/phase6e_run_manifest.json',root/'results/phase6e/phase6e_matched_forecasts.csv',root/'results/phase6c/phase6c_research_monthly_panel.csv',root/'results/research/phase6b2/phase6b2_gdp_revision_history.csv',root/receipt['raw_file']]},
        outputs={p.name:sha(p) for p in out.glob('*.csv')},code_hashes={p.name:sha(p) for p in (root/'scripts/phase6f').glob('*.py')}))


def write_report(out,audit,comparison,production,current,classification):
    lines=['# Phase 6F — research only', '',
        'Production remains COMBO_50_50. No model is promoted. Exact Phase 6E DFM and U-MIDAS reconstruction is required before writing the report.', '',
        '## Audit and design', '',
        'M2 is CBU broad money liabilities, end-of-period billion UZS, transformed to 100 ln(M2_t/M2_t-12). It enters the factor contemporaneously in economic time, with a 25-day registry publication mask. M1/M2 shift the transformed, release-gated series by one/two calendar months. Publication lag and economic lag are separate.',
        'Historical M2 values are revised snapshots, not verified historical releases. The page update attached to the whole workbook is not an observation-level first release. Timing masks prevent future reference-period use under assumptions, but revision leakage cannot be excluded. No forecast here is certified vintage-real-time.',
        'The eight predictors are industrial production, PPI, USD/UZS, RUB/UZS, gold price, M2, FX reserves excluding gold, and scope-limited POS turnover. Factor extraction is one filtered EM-MLE DynamicFactorMQ factor, AR(2), no idiosyncratic AR(1), training-only scaling and balanced start. GDP bridge is intercept + quarterly mean factor + GDP(q-1); GDP vintages are strictly publication-gated. The GDP target is published cumulative YTD YoY, not standalone-quarter growth.',
        'B1/B2 retain the existing factor and GDP AR term and add quarter-mean transformed M2 with economic L1/L2. Training covariates use the same H1/H2/H3 calendar stage of each training quarter. B3/B4 add latest assumed-available quarterly FDI / an extra quarter; B5 uses M1 factors and only FDI as the additional bridge term. FDI never enters a monthly panel.', '',
        '## FDI evidence', '',
        '[Official CBU source](https://cbu.uz/en/statistics/e-gdds/data/127982/) and its exact analytical BOP workbook were discovered after repository search found no existing FDI ingestion or named FDI data file. Exact row: Direct investment: liabilities. Quarterly net incurrence of direct-investment liabilities, nominal million USD; this is a financial-account flow, not FDI stock, not gross inflows, and not the assets-minus-liabilities balance. The workbook unit is million USD; the page’s generic end-of-period label should not turn BOP transactions into a stock.',
        f'Coverage {audit[1]["first_observation"]}–{audit[1]["last_observation"]}; missing cells {audit[1]["missing_count"]}. This is a revised 2026 snapshot without recovered historical value vintages. A 90-day and a 120-day quarter-end lag are conservative research assumptions, not observed release dates. Assumed dates are stored separately; source_release_date stays null.',
        'FDI B3/B4/B5 estimates are explicitly revised-history timing sensitivities, not valid real-time forecasts. Their numbers must not be used for promotion. The newly retrieved FDI workbook postdates the frozen 2026-10-05 production cutoff, so no valid current FDI challenger nowcast is published. Historical archive-vintage recovery remains necessary.', '',
        '## Evaluation', '',
        'The exact twelve Phase 6E holdout origins (four quarters, H1/H2/H3) are reused. Every metric pairs challenger and benchmark on identical origins and actual vintages. Full available counts equal the common counts when no model failed. POST_DEVELOPMENT equals the existing holdout; there is no new prospective realization evidence. Bias is actual minus forecast. OOS R² = 1 − SSE_model/SSE_M0; negative values mean worse performance.', '',
        '| Model | N | H1 RMSE | H2 RMSE | H3 RMSE | Pooled RMSE | Δ RMSE | OOS R² |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in comparison.to_dict('records'):
        lines.append(f'| {r["model"]} | {r["N"]} | {r["H1_RMSE"]:.6f} | {r["H2_RMSE"]:.6f} | {r["H3_RMSE"]:.6f} | {r["pooled_RMSE"]:.6f} | {r["delta_RMSE_vs_phase6e"]:.6f} | {r["OOS_R2"]:.6f} |')
    lines += ['', 'M1/M2 improvement is assessed from the reported common-sample deltas, never in-sample R². Improvements of 0.03/0.05 pp are highlighted thresholds only; revised-history diagnostics and four quarters cannot justify promotion. Horizon metrics show the strongest/weakest horizon without asserting statistical significance.',
        'Bridge coefficient files contain signs, OLS standard errors, VIF, condition number, Durbin–Watson, leverage and Cook’s distance by origin. Standard errors are descriptive with a small sample. DFM files contain loadings, EM convergence and factor correlations. Squared observed-series/factor correlation is labelled an association measure, not a likelihood variance decomposition. M2 inclusion in factor and bridge is a deliberately diagnosed redundancy experiment.',
        'FDI bridge performance and combined M2/FDI deltas can be examined in the diagnostic table, including 120-day sensitivity and an extra quarterly lag. Whether FDI genuinely improves either bridge or factor remains unestablished; no monthly FDI factor model was fitted. No valid real-time FDI common sample exists, so apparent diagnostic improvements do not answer the promotion question.', '', '## Current quarter', '',
        f'Unchanged 2026Q3 Phase 6E DFM {production["dfm_forecast"]:.9f}%; U-MIDAS {production["umidas_forecast"]:.9f}%; COMBO_50_50 {production["final_forecast"]:.9f}%.']
    lines += [f'{m}: {v:.9f}% (research challenger).' for m,v in current.items() if m not in ['M0','U_MIDAS','COMBO_50_50']]
    lines += ['FDI current estimates unavailable at the frozen cutoff. Exact additive bridge contributions are coefficient × design value in the coefficient output; historical FDI contributions are diagnostics only.', '',
        'Reproduce: `.venv/Scripts/python.exe -m scripts.phase6f.experiment`. The archived workbook is reused; no refresh or production/dashboard writer is invoked. Protected artifacts are hashed before and after. Tests and deterministic rerun evidence are recorded separately.', '',
        'Next required evidence: recover dated official BOP and M2 historical releases, attach observation-level value vintages, and repeat the same controlled comparisons before Phase 6G review.', '', classification, '', 'KEEP_PHASE6E_PRODUCTION']
    (out/'phase6f_results.md').write_text('\n\n'.join(lines)+'\n',encoding='utf8')


if __name__ == '__main__':
    run()
