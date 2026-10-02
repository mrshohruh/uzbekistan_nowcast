"""Evidence-driven report generation; no model selection or promotion."""
import html
import json

import numpy as np
import pandas as pd


def markdown(frame):
    if frame.empty:
        return 'No estimable matched origins.'
    cols = frame.columns.tolist()
    lines = ['| ' + ' | '.join(cols) + ' |', '| ' + ' | '.join(['---']*len(cols)) + ' |']
    for row in frame.itertuples(index=False, name=None):
        lines.append('| ' + ' | '.join(f'{v:.4f}' if isinstance(v, (float, np.floating)) else str(v) for v in row) + ' |')
    return '\n'.join(lines)


def write_report(root, out, doc, forecasts, comparison, common, pca, loadings, convergence, manifest):
    from experiment import prepare, SERVICES
    source = pd.read_csv(root/'data/research/phase6a2/cbu_midas_monthly_panel.csv')
    source.index = pd.PeriodIndex(source.reference_period, freq='M').to_timestamp('M')
    source = source.loc['2021-01-31':'2026-08-31']
    _, _, _, adjustment, adjusted = prepare(source[[SERVICES]], source.services_output_regime, source.index.max(), True)
    pd.DataFrame(dict(month=source.reference_period.to_numpy(), raw_services=source[SERVICES].to_numpy(),
                      adjusted_services=adjusted[SERVICES].to_numpy(), regime=source.services_output_regime.to_numpy(),
                      regime_adjustment=adjustment['regime_adjustment'],
                      usage='FULL_SAMPLE_DESCRIPTIVE_ONLY_NEVER_FORECAST_INPUT')).to_csv(out/'phase6b_services_descriptive_series.csv', index=False)
    standard = common.loc[common.lag_mode.eq('standard')]
    pooled = pd.read_csv(out/'phase6b_pooled_metrics.csv')
    pooled = pooled.loc[pooled.lag_mode.eq('standard')]
    classifications = []
    for name, block in forecasts.loc[forecasts.lag_mode.eq('standard')].groupby('model'):
        valid = block.dropna(subset=['prediction'])
        failure_rate = 1-len(valid)/len(block)
        if failure_rate > .2:
            status, reason = 'UNSTABLE', f'{failure_rate:.0%} origin failure rate'
        elif valid.target_quarter.nunique() < 8 or 'POS_HISTORICAL' in name:
            status, reason = 'INSUFFICIENT_EVIDENCE', 'fewer than eight distinct evaluation quarters'
        else:
            a = pooled.loc[pooled.model.eq(name) & pooled.horizon.eq('ALL')]
            u = pooled.loc[pooled.model.eq('umidas_usd_uzs_mom_dlog') & pooled.horizon.eq('ALL')]
            by_h = pooled.loc[pooled.model.eq(name) & pooled.horizon.ne('ALL')].set_index('horizon')
            uh = pooled.loc[pooled.model.eq('umidas_usd_uzs_mom_dlog') & pooled.horizon.ne('ALL')].set_index('horizon')
            if len(a) and len(u) and a.iloc[0].n == u.iloc[0].n and a.iloc[0].rmse < u.iloc[0].rmse and a.iloc[0].mae < u.iloc[0].mae and (by_h.rmse < uh.rmse).sum() >= 2:
                status, reason = 'PROMISING_RESEARCH_CHALLENGER', 'pooled matched RMSE/MAE gains with gains in at least two horizons; only exploratory evidence'
            else:
                status, reason = 'NO_INCREMENTAL_VALUE', 'does not meet prespecified standalone gain criteria; combinations reported separately'
        classifications.append(dict(model=name, classification=status, failure_rate=failure_rate, successful_origins=len(valid),
                                    quarters=valid.target_quarter.nunique(), rationale=reason))
    classes = pd.DataFrame(classifications)
    classes.to_csv(out/'phase6b_classifications.csv', index=False)
    pc = pca.loc[pca.component.eq(1), ['predictor_set','variance_pct','pc1_loadings']]
    full_load = loadings.loc[loadings.target_quarter.eq('FULL_SAMPLE_DESCRIPTIVE') & loadings.factor.eq(1), ['specification','variable','loading','idiosyncratic_variance']]
    imports = full_load.loc[full_load.variable.eq('imports_total_monthly_log_yoy')]
    primary = pooled.loc[pooled.model.eq('DFM_DOMESTIC_3__BRIDGE_B') & pooled.horizon.eq('ALL')]
    primary_a = pooled.loc[pooled.model.eq('DFM_DOMESTIC_3__BRIDGE_A') & pooled.horizon.eq('ALL')]
    u = pooled.loc[pooled.model.eq('umidas_usd_uzs_mom_dlog') & pooled.horizon.eq('ALL')]
    combo = pooled.loc[pooled.model.eq('COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B') & pooled.horizon.eq('ALL')]
    svc = pooled.loc[pooled.model.eq('DFM_DOMESTIC_3_SERVICES__BRIDGE_B') & pooled.horizon.eq('ALL')]
    imp = pooled.loc[pooled.model.eq('DFM_DOMESTIC_3_IMPORTS__BRIDGE_B') & pooled.horizon.eq('ALL')]
    post_primary = comparison.loc[comparison.model.eq('DFM_DOMESTIC_3__BRIDGE_B') & comparison.lag_mode.eq('standard') &
                                  comparison.horizon.eq('ALL') & comparison.evaluation_group.eq('HISTORICAL_POST_DEVELOPMENT_TEST') &
                                  comparison.comparison.eq('umidas_usd_uzs_mom_dlog')]
    post_combo = comparison.loc[comparison.model.eq('COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B') & comparison.lag_mode.eq('standard') &
                                comparison.horizon.eq('ALL') & comparison.evaluation_group.eq('HISTORICAL_POST_DEVELOPMENT_TEST') &
                                comparison.comparison.eq('umidas_usd_uzs_mom_dlog')]

    def delta(a, baseline):
        if a.empty or baseline.empty or a.iloc[0].n != baseline.iloc[0].n:
            return 'not comparable on this pooled sample; see exact pairwise tables'
        diff = a.iloc[0].rmse-baseline.iloc[0].rmse
        return f'RMSE {a.iloc[0].rmse:.4f} versus {baseline.iloc[0].rmse:.4f} ({diff:+.4f})'

    answers = [
        f'1. **Domestic factor:** yes. Domestic PC1 explains {pc.iloc[0].variance_pct:.2f}% over 68 months. This is descriptive coherence, not GDP predictive validation.',
        '2. **Variables loading:** industrial production, construction and retail form the coherent block. Signed PCA eigenvectors and standardized state-space loadings are both saved; their scales differ.',
        '3. **Imports:** its PCA loading is weak and adding it lowers PC1 share. One-factor GDP bridge B versus domestic bridge B: '+delta(imp,primary)+'. Two-factor identification is separately diagnosed; no interpretation of unidentified rotated factors.',
        '4. **Services:** training-only adjusted services bridge B versus domestic bridge B: '+delta(svc,primary)+'. Raw-break robustness is separate. A level dummy cannot prove the expanded reporting universe is economically comparable.',
        '5. **Standalone GDP forecasts:** primary domestic bridge B versus frozen U-MIDAS: '+delta(primary,u)+'. Bridge A versus B: '+delta(primary_a,primary)+'. AR(1) and the production ensemble have lower pooled RMSE than standalone DFM. On the four post-development quarters, domestic bridge B pooled RMSE is '+f'{post_primary.iloc[0].rmse:.4f} versus U-MIDAS {post_primary.iloc[0].benchmark_rmse:.4f}'+', so the standalone advantage does not persist in the later partition.',
        '6. **Combination:** equal-weight domestic bridge B plus U-MIDAS: '+delta(combo,u)+'. On the post-development partition: '+f'{post_combo.iloc[0].rmse:.4f} versus U-MIDAS {post_combo.iloc[0].benchmark_rmse:.4f}'+'. Each specification/bridge has its own combination; none was selected using its test errors.',
        '7. **Retain as active challenger:** the prespecified primary domestic model plus lagged GDP is promising chiefly as an equal-weight combination research candidate. Standalone evidence is mixed and does not support replacement. The pooled-rule labels below are provisional; only four later quarters are available. This run does not activate or promote any model.',
        '8. **Limits:** 68 monthly observations, only 12 initial GDP training quarters and 10 evaluation quarters, revised rather than first-release inputs, published cumulative real-activity growth versus nominal monthly import growth, an unresolved services universe change, and release-lag assumptions. Bridge sensitivity and convergence failures quantify additional limitations. A strong domestic factor alone does not establish incremental GDP information.'
    ]
    post = comparison.loc[comparison.lag_mode.eq('standard') & comparison.evaluation_group.eq('HISTORICAL_POST_DEVELOPMENT_TEST') &
                          comparison.comparison.eq('umidas_usd_uzs_mom_dlog') & ~comparison.model.str.startswith('COMBO_EQUAL')]
    combination_table = comparison.loc[comparison.lag_mode.eq('standard') & comparison.horizon.eq('ALL') &
                                      comparison.comparison.eq('umidas_usd_uzs_mom_dlog') & comparison.model.str.startswith('COMBO_EQUAL')]
    attempted = convergence.estimation_attempted.fillna(True).eq(True)
    failures = convergence.loc[attempted & ~convergence.converged.fillna(False)]
    weak_two = convergence.loc[convergence.specification.eq('DFM_TWO_FACTOR_IMPORTS')]
    attempted_two = weak_two.estimation_attempted.fillna(True).eq(True).sum()
    report = f'''# Phase 6B: small-scale DFM research

**{manifest['label']}. RESEARCH ONLY. No promotion, registry amendment or production replacement.**

## Sources and frozen definitions

Monthly panel: `data/research/phase6a2/cbu_midas_monthly_panel.csv`, January 2021–August 2026, **68 consecutive months**, no predictor interpolation or historical splice. GDP: `data/master/gdp_quarterly.parquet`, field `gdp_real_yoy_pct`, the existing published cumulative quarterly growth convention, unchanged. This is not a reconstructed standalone-quarter GDP growth target. Current GDP retrieval metadata differs from the original freeze; every GDP value was checked against saved frozen outcomes and agrees to 1e-10.

H1/H2/H3 are the first/second/third target-quarter month ends, exactly from `uznowcast.models.data.horizon_month_end`. Release masks call the frozen `information_cutoff_for_variable`: month end plus registry lag, standard or conservative (+15 days, minimum 3). Industrial production lag 33 days, construction 27, retail 24, imports 26. Services is not a V1.2 registry series: the inherited function's **30-day fallback** is explicit research timing metadata, not an observed release date. No registry was amended. POS uses its existing 18-day lag.

Quarter origins: **2024Q1–2026Q2**, ten distinct quarters. Frozen development subset: **2024Q1–2025Q2** (six); historical post-development subset: **2025Q3–2026Q2** (four). Both partitions are reported; none is claimed to be a pristine unseen holdout. Each full-coverage model/bridge has up to **10 H1, 10 H2, 10 H3 forecasts per lag mode**. Origin counts and failures are explicit CSV rows, not manufactured extra tests. Optional POS ends December 2024 and has only four calendar target quarters.

Saved AR/U-MIDAS predictions come from Phase 4B development and Phase 4C holdout artifacts underlying the Phase 5A frozen architecture. The saved Phase 5C USD U-MIDAS(3) challenger predictions were verified numerically identical on all matched non-missing origins (identity audit CSV). Production remains 0.5 AR(2) + 0.5 USD U-MIDAS(3). Phase 5C saved DFM metrics but **did not persist its origin-level predictions**. Those aggregate metrics are available at `results/challengers/phase5c/phase5c_dfm_metrics.csv`; they cannot support an exact Phase 6B matched-origin comparison and are not substituted or rerun.

## Estimation and leakage controls

State-space equation: standardized indicators = loadings × factors + diagonal white-noise measurement errors; factor dynamics are stationary AR(1), identity innovation variance. One factor for primary/robustness models; two-factor imports uses unrestricted VAR(1), rejected if covariance condition exceeds 1e12. L-BFGS is followed by BFGS only on nonconvergence; each capped at 400 iterations. Nonconverged/near-unit-root origins are unavailable rather than silently accepted.

At each origin, masks apply first. Services adjustment regresses its observed training values on an intercept and regime indicator; only the dummy coefficient is subtracted from post-break observations. With no training post-break observations, adjustment is zero and marked unidentified. Training means/stds use masked months strictly before the target quarter. DFM parameters are estimated on those same training months, then held fixed while filtering through the masked origin. Missing future target-quarter measurements remain null; latent states are model-predicted through quarter end. No observed predictor is filled. Bridges A/B use full-quarter means of **filtered/predicted states**, with at least 12 GDP quarters before the target. B adds prior-quarter GDP; A omits it. Full-sample smoothed states appear only in rows explicitly labelled descriptive and forecast-ineligible.

Sign normalization makes industrial loading positive. Two-factor signs do not remove rotational ambiguity. Predictor/factor correlations, expanding loading changes, training means/stds, services raw/adjusted values, regime adjustments and optimizer diagnostics are saved per origin. Descriptive full-sample loadings below are not forecast-origin parameters.

## Recomputed factor structure

{markdown(pc)}

Stored-panel results are checked against the requested approximate PC1 shares with a one-percentage-point tolerance; imports loading must have absolute magnitude <=0.12. Eigenvalues, all component shares and correlation matrices are saved.

{markdown(full_load)}

## Exactly common standard-lag origins

Intersection across successful primary one-factor variants/bridges and frozen benchmarks. POS and two-factor models do not reduce the main comparison intersection. Pairwise matched samples include these optional models separately. RMSE/MAE are percentage points; bias = actual minus forecast.

{markdown(standard[['model','horizon','n','quarters','rmse','mae','bias']])}

## Frozen post-development partition versus U-MIDAS

{markdown(post[['model','horizon','n','rmse','mae','bias','benchmark_rmse','rmse_difference']])}

## Equal-weight combinations

Separate combinations for every DFM/bridge avoid ex-post best-model selection. No error-based adaptive weights were fitted. Each row uses identical origins for the combination and U-MIDAS; development and post-development remain separate.

{markdown(combination_table[['model','evaluation_group','n','rmse','mae','benchmark_rmse','rmse_difference']])}

## Convergence, stability and research decisions

Nonconverged actual fit records: **{len(failures)}**. Failed-origin records (including identification and bridge failures): **{manifest['failed_origin_records']}**. Successful research forecasts across models, bridges and lag modes: **{manifest['successful_forecasts']}**. Two-factor fits attempted, including descriptive: **{attempted_two}**. Its first expanding-origin fit failed identification and remaining origins were explicitly skipped; this is **NOT_ESTIMABLE_WITH_CURRENT_SAMPLE**, not 60 optimizer failures. All optimizer warnings and covariance conditions are retained. Services dummy identification changes recursively after the break; its adjustment must not be interpreted as causal or a verified methodological correction.

{markdown(classes)}

The prespecified classification rule is recorded in the specifications JSON. Pooled gains are exploratory; the post-development sample is only four quarters. No significance claim is made, and repeated H1/H2/H3 errors are not 30 independent GDP outcomes.

## Required questions

{chr(10).join(answers)}

## Reproduction and governance

Run `.venv/Scripts/python.exe scripts/research/phase6b/run.py`; tests: `.venv/Scripts/python.exe -m pytest -q -o addopts='' scripts/research/phase6b/test_experiment.py`. Research dependency pins are local to this directory. Seeds and input/code hashes are in the manifest. Numeric tables are deterministic conditional on pinned libraries and stored inputs; timestamps/log durations change.

**{manifest['protected_count']} protected artifacts were SHA256-identical before and after execution.** The persistent baseline includes production code, registries, canonical masters/metadata, Phase 5 artifacts, Phase 5D monitoring, Phase 6A data/reports and current dashboard. Pre-existing inaccessible vendored reader/test-cache directories are outside the model/artifact inventory; their state was not repaired. Protected start/end inventories are separate artifacts; the runner refuses to overwrite the baseline. No forecast history was rewritten. Stop after Phase 6B; no collection phase starts automatically.
'''
    (out/'phase6b_results.md').write_text(report, encoding='utf-8')
    (doc/'phase6b_dfm_feasibility_report.md').write_text(report, encoding='utf-8')
    dashboard = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Phase 6B DFM research</title>
<style>body{{font:15px system-ui;margin:36px auto;max-width:1350px;color:#172033;padding:20px}}.banner{{background:#8d2525;color:white;padding:18px}}table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{border-bottom:1px solid #ddd;text-align:left;padding:7px}}.scroll{{overflow:auto}}h2{{margin-top:32px}}</style>
<div class="banner">PHASE 6B — RESEARCH ONLY — CALENDAR PSEUDO REAL TIME — NO PRODUCTION PROMOTION</div>
<h1>Uzbekistan domestic activity factor</h1><p>68 months · 10 GDP quarters · revised observations · four post-development quarters. No true real-time vintage claim.</p>
<h2>Factor structure</h2><div class="scroll">{pc.to_html(index=False,escape=True)}</div>
<h2>Matched standard-lag metrics</h2><div class="scroll">{standard.to_html(index=False,escape=True,float_format=lambda x:f'{x:.4f}')}</div>
<h2>Research classifications</h2>{classes.to_html(index=False,escape=True)}<h2>Interpretation</h2>
{''.join('<p>'+html.escape(a)+'</p>' for a in answers)}<p>Protected artifacts unchanged: {manifest['protected_count']}. Production architecture and dashboard remain frozen.</p></html>'''
    (root/'dashboard/phase6b_dfm_research.html').write_text(dashboard, encoding='utf-8')
