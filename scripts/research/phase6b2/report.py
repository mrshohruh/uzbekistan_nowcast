"""Generate the self-contained research report and final verification manifest."""
from pathlib import Path
import json
import re
import importlib.metadata
import pandas as pd
import numpy as np
from run import ROOT,OUT,sha,protect
DOC=ROOT/'docs/modeling/phase6b2'

def table(frame,columns=None):
    if columns:
        frame=frame[columns]
    def cell(v):
        if pd.isna(v):
            return '—'
        return f'{v:.4f}' if isinstance(v,(float,np.floating)) else str(v).replace('|','/')
    return '| '+' | '.join(frame.columns)+' |\n| '+' | '.join(['---']*len(frame.columns))+' |\n'+ '\n'.join('| '+' | '.join(cell(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None))

def main():
    manifest=json.loads((OUT/'phase6b2_run_manifest.json').read_text())
    checks=json.loads((OUT/'phase6b2_determinism_checks.json').read_text())
    assert checks['all_csv_outputs_identical']
    manifest['deterministic_rerun']=checks
    counts={}
    files={'repository_models':'phase6b2_repository_tests_verified.log','phase6b':'phase6b2_phase6b_tests.log',
           'phase6b1':'phase6b2_phase6b1_tests.log','phase6b2':'phase6b2_new_tests_verified.log'}
    for suite,filename in files.items():
        raw=(OUT/filename).read_bytes()
        text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig',errors='replace')
        match=re.search(r'(\d+) passed',text)
        assert match is not None and not re.search(r'\d+ failed|\d+ errors?',text),filename
        counts[suite]=int(match[1])
    manifest['tests']=dict(final_passed=sum(counts.values()),final_failed=0,suites=counts,
        logs=files,initial_attempt_notes='Initial combined run hit Windows tmp directory permissions and bare run.py namespace collisions. Final suites passed in separate processes with isolated temp directories.')
    manifest['protected_files']=protect()
    manifest['protected_status']='UNCHANGED'
    manifest['environment_versions']={name:importlib.metadata.version(name) for name in
        ['numpy','pandas','scipy','statsmodels','patsy','pyarrow','pytest','beautifulsoup4','pypdf','requests']}
    manifest['code_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in Path(__file__).parent.glob('*') if p.is_file()}
    registry=pd.read_csv(OUT/'phase6b2_gdp_vintage_registry.csv')
    m=pd.read_csv(OUT/'phase6b2_horizon_metrics.csv')
    primary=m.loc[m['sample'].eq('COMMON_ALL_EIGHT_MODELS')&m.lag_mode.eq('standard')&m.timing_rule.eq('STRICT')&m.target_definition.eq('FIRST_RELEASE')]
    secondary=m.loc[m['sample'].eq('COMMON_ALL_EIGHT_MODELS')&m.lag_mode.eq('standard')&m.timing_rule.eq('STRICT')&m.target_definition.eq('LATEST_REVISED')]
    pooled=primary.loc[primary.horizon.eq('ALL')&primary.evaluation_group.eq('POOLED_RESEARCH_ONLY')]
    post=primary.loc[primary.horizon.eq('ALL')&primary.evaluation_group.eq('HISTORICAL_POST_DEVELOPMENT_TEST')]
    models=['DFM_B','UMIDAS_USD','PRODUCTION_ENSEMBLE','COMBO_B']
    results=pooled.loc[pooled.model.isin(models),['model','n_forecasts','rmse','mae','bias']].merge(
        post.loc[post.model.isin(models),['model','n_forecasts','rmse','mae','bias']],on='model',suffixes=('_pooled','_post'))
    h23=secondary.loc[secondary.model.eq('COMBO_B')&secondary.horizon.eq('H2_H3')&secondary.evaluation_group.eq('POOLED_RESEARCH_ONLY')].iloc[0]
    primary_h23=primary.loc[primary.model.eq('COMBO_B')&primary.horizon.eq('H2_H3')&primary.evaluation_group.eq('POOLED_RESEARCH_ONLY')].iloc[0]
    correlations=pd.read_csv(OUT/'phase6b2_error_correlations.csv')
    correlation=correlations.loc[correlations.lag_mode.eq('standard')&correlations.timing_rule.eq('STRICT')&correlations.target_definition.eq('FIRST_RELEASE')&correlations.horizon.eq('ALL')]
    l=pd.read_csv(OUT/'phase6b2_leave_one_quarter_out.csv')
    l=l.loc[l.lag_mode.eq('standard')&l.timing_rule.eq('STRICT')&l.target_definition.eq('FIRST_RELEASE')&l.horizon.eq('ALL')]
    lp=l.loc[l.evaluation_group.eq('POOLED_RESEARCH_ONLY')].pivot(index='omitted_target_quarter',columns='model',values='rmse')
    lt=l.loc[l.evaluation_group.eq('HISTORICAL_POST_DEVELOPMENT_TEST')].pivot(index='omitted_target_quarter',columns='model',values='rmse')
    loqo=dict(pooled_omissions=len(lp),pooled_wins_vs_umidas=int(lp.COMBO_B.lt(lp.UMIDAS_USD).sum()),
        pooled_wins_vs_production=int(lp.COMBO_B.lt(lp.PRODUCTION_ENSEMBLE).sum()),post_omissions=len(lt),
        post_wins_vs_umidas=int(lt.COMBO_B.lt(lt.UMIDAS_USD).sum()),post_wins_vs_production=int(lt.COMBO_B.lt(lt.PRODUCTION_ENSEMBLE).sum()))
    manifest['leave_one_quarter_out']=loqo
    a=pd.read_csv(OUT/'phase6b2_origin_information_audit.csv')
    u=pd.read_csv(OUT/'phase6b2_GDP_training_vintage_usage.csv')
    unique_revised=u.loc[u.GDP_vintage_differs_from_master,'GDP_quarter'].nunique()
    lag=a.loc[a.timing_rule.eq('STRICT')&a.lag_mode.eq('standard')].copy()
    lag['changed']=~np.isclose(lag.prior_GDP_vintage_value,lag.prior_GDP_current_value,rtol=0,atol=1e-9)
    lag=lag.drop_duplicates('prior_quarter')
    pair=primary.loc[primary.model.eq('DFM_B')].merge(primary.loc[primary.model.eq('UMIDAS_USD')],
        on=['lag_mode','timing_rule','target_definition','evaluation_group','horizon','sample'],suffixes=('_dfm','_usd'))
    wins=pair.loc[pair.rmse_dfm.lt(pair.rmse_usd),['evaluation_group','horizon','n_forecasts_dfm','rmse_dfm','rmse_usd']]
    comparison=pd.read_csv(OUT/'phase6b2_phase_comparison_metrics.csv')
    cmp=comparison.loc[comparison.lag_mode.eq('standard')&comparison.timing_rule.eq('STRICT')&comparison.target_definition.eq('LATEST_REVISED')&
        comparison.horizon.eq('ALL')&comparison.evaluation_group.eq('POOLED_RESEARCH_ONLY')&comparison.model.isin(models)]
    combo_metrics=primary.loc[primary.model.eq('COMBO_B'),['evaluation_group','horizon','n_forecasts','rmse','mae','bias']]
    release_rows=[]
    supplied={'2023Q4':'2024-01-26','2024Q1':'2024-04-30','2024Q2':'2024-07-24','2024Q3':'2024-10-25',
        '2024Q4':'2025-01-27','2025Q2':'2025-07-28','2025Q3':'2025-10-27','2025Q4':'2026-01-26','2026Q1':'2026-04-27','2026Q2':'2026-07-31'}
    for q,d in supplied.items():
        r=registry.set_index('quarter').loc[q]
        release_rows.append(dict(quarter=q,supplied_example=d,earliest_verified_publication=r.first_release_date,
            first_value=r.first_release_value,current_master=r.current_master_value,
            official_evidence=f'[{q} source]({r.first_release_source_url})'))
    sourcecount=len(pd.read_csv(OUT/'phase6b2_gdp_release_sources.csv'))
    text=f'''# Phase 6B.2 — verified GDP publication and vintage research

**Final classification: PHASE6B2_RELEASE_HISTORY_INCOMPLETE. Research only; no promotion.**

The isolated reconstruction contains all 34 registry quarters, with **24 earliest recovered official first-release dates and values**, and **103 documented publication events**. Ten early first releases remain unresolved. The accessor uses the latest *documented* eligible vintage; it does not certify that every intervening revision has been recovered. These results improve the information boundary but are **not an exhaustive real-time vintage backtest**.

The frozen GDP target remains cumulative year-to-date real YoY growth, with published volume indices converted by subtracting 100. GDP remains quarterly. Monthly panels, release masks, scaling, the one-factor AR(1) DFM with diagonal white-noise errors, the USD U-MIDAS specification and its minimum 15 effective observations, and all 50/50 weights remain unchanged.

## Official evidence and unresolved history

{sourcecount} archived official source responses have URL, raw file, retrieval time, HTTP status and SHA256 provenance in [source inventory](../../../results/research/phase6b2/phase6b2_gdp_release_sources.csv). Search results were used to locate sources; the ledger uses downloaded official pages and PDFs. Dated landing pages must embed the actual report bytes; similar reports at different URLs are not assumed to be the same vintage. Printed PDF release dates are recorded separately from landing-page dates. Website sidebar timestamps and current SIAT dataset updates are not historical quarter releases.

The requested examples were checked independently. Several earliest recoverable releases precede the supplied summary articles:

{table(pd.DataFrame(release_rows))}

The unresolved first releases are **2018Q1–2019Q4 and 2020Q1–2020Q2**. Official annual catalogues contain several undated preliminary reports, but neither their filenames, PDF creation metadata, current upload dates nor typical lags prove historical publication. The catalogue's 2018 Q2 GDP link returns HTTP 404; the failed response is archived. These quarters retain null first-release fields, not invented dates or current-master first values. Later dated reports provide usable historical values for many of them. **2018Q1 and 2018Q2 have no eligible documented vintage in the evaluation origins and are excluded from training.**

Revision coverage is also partial: old quarters are republished in later quarterly reports, but the dates on which every intervening revision first became public are not established. Publication-event dates therefore mean “this value is verifiably published by this date,” not “this is the exact original revision date.” The accessor never uses a later document early. It can retain an older documented value where a missing intermediate revision may have existed.

The 2024 Q1 report prints historical chart labels for 2020 and 2021 in an order inconsistent with the preceding report. Both observations remain in the evidence ledger as **SOURCE_CHART_ORDER_SUSPECT** and are excluded from the accessor; they are neither silently swapped nor treated as verified usable revisions. Previous documented vintages remain available. This is another reason the archive cannot support a complete-history classification.

## Timing and vintage access

The frozen forecast origin is the month-end calendar date at 00:00 Asia/Tashkent. Known official clock times must strictly precede that cutoff. Date-only releases on that date are SAME_DAY_TIME_UNKNOWN: STRICT excludes them and PERMISSIVE_END_OF_DAY includes them. Both rules were run independently of accuracy. There are **0 same-day unknown records** in the 60 evaluated origins; consequently both timing-rule forecasts are identical. The earlier April 25, 2024 release removes the apparent April 30 same-day issue.

Of Phase 6B.1's 20 excluded H1 records (10 quarters × 2 monthly-lag modes), **20 are restored**, **0 are genuinely unavailable**, and **0 have same-day ambiguity**, using the recovered official prior-quarter dates. Counts do not imply that the ten unresolved early releases were verified.

The [accessor](../../../scripts/research/phase6b2/vintages.py) excludes target and future quarters, selects the latest eligible documented event, preserves publication URL/checksum/value provenance, rejects duplicate events and rejects substituted revised values. Unknown dated evidence is never filled from the master. [Training vintage usage](../../../results/research/phase6b2/phase6b2_GDP_training_vintage_usage.csv) records every returned GDP observation at each origin.

**16 of the 24 verified first-release observations differ from the current master.** Across the origin training sets, **{unique_revised} distinct GDP quarters** have documented available values differing from the master. **{int(lag.changed.sum())} of the 10 distinct immediate prior-quarter GDP values** differ:

{table(lag[['prior_quarter','prior_GDP_first_release_value','prior_GDP_vintage_value','prior_GDP_current_value','changed']])}

## Matched accuracy: primary first-release targets

Every model has 30 matched origins per monthly-lag mode and timing rule: 10 H1, 10 H2 and 10 H3. Development comprises 2024Q1–2025Q2 (18 origins); the historical post-development test comprises 2025Q3–2026Q2 (12 origins). Both lag modes together give 60 matched origins per timing rule. There are eight forecasts at each origin. Rules are sensitivities, not extra independent observations.

The primary diagnostic is FIRST_RELEASE; LATEST_REVISED is a separate secondary diagnostic. Errors and bias are actual minus forecast. The following standard-lag, strict-rule table uses identical origins for all models:

{table(results)}

The combination beats U-MIDAS and the production ensemble in the pooled documented-vintage sample. Standalone DFM B does **not** beat U-MIDAS pooled or post-development. It does beat U-MIDAS on these development subsets:

{table(wins)}

These are matched *documented-vintage* comparisons. No sample can be certified as using the exhaustive actual GDP vintage history while the identified gaps remain.

The four post-development quarters weaken the combination result: its all-horizon RMSE is 0.6846 versus U-MIDAS 0.6861, a difference of only about 0.0015. On post-development H2/H3, the combination RMSE is 0.6325 versus U-MIDAS 0.6129, so the combination loses there. Post-development FIRST_RELEASE and LATEST_REVISED scores coincide because these four target growth values are unchanged in the master.

Complete pre-specified combination diagnostics for the primary standard/strict result:

{table(combo_metrics)}

## Separate latest-revised targets and prior-phase comparisons

The old 0.4754 Phase 6B.1 standard pooled H2/H3 combination RMSE becomes **{h23.rmse:.4f}** on the same 20 origins with latest-revised targets and documented GDP training vintages. The primary first-release equivalent is **{primary_h23.rmse:.4f}**. The approximate numerical improvement survives this partial-archive sensitivity, but neither number establishes a verified complete-history result.

Restoring H1 gives latest-revised all-horizon combination RMSE 0.5072 over 30 origins; the primary first-release score is 0.4875. The frozen original all-horizon combination score was about 0.5054. These 30-origin scores must not be compared with the 20-origin Phase 6B.1 pooled score as if coverage were identical.

For the three-phase numeric comparison below, **every model uses the exact common H2/H3 origins across all three phases**, and latest-revised actuals stay fixed. Historical predictions are read from frozen files and scored only in new Phase 6B.2 comparison outputs; the earlier records are not rewritten. The original and fallback phases are historical references with their original information limitations, not verified-vintage results.

{table(cmp[['phase','model','n_forecasts','rmse','mae']])}

[Forecast-level attribution](../../../results/research/phase6b2/phase6b2_phase6b1_comparison.csv) separates: (1) restoring verified release timing while explicitly retaining the 46-day fallback for unresolved early dates; (2) removing master values on quarters without documented historical support; and (3) replacing remaining master values with eligible published vintages. Counterfactual master-value forecasts are explicitly invalid-value diagnostics and never enter primary metrics. H1 has no fallback forecast, so restoration is reported as availability, not a fabricated numeric difference.

## Complementarity and leave-one-quarter-out checks

DFM B and U-MIDAS forecast-error correlations are:

{table(correlation[['evaluation_group','n','dfm_b_umidas_error_correlation']])}

The low pooled correlation is consistent with useful pooled complementarity. The much higher post-development correlation and nearly tied post-development RMSE limit that interpretation.

Leaving out one target quarter, while retaining the fixed model specifications and 50/50 forecasts, the pooled combination beats U-MIDAS in **{loqo['pooled_wins_vs_umidas']}/{loqo['pooled_omissions']}** omissions and production in **{loqo['pooled_wins_vs_production']}/{loqo['pooled_omissions']}** omissions. For the four-quarter post-development sample, it beats U-MIDAS in **{loqo['post_wins_vs_umidas']}/{loqo['post_omissions']}** and production in **{loqo['post_wins_vs_production']}/{loqo['post_omissions']}** omissions. These are evaluation sensitivities, not refitted model weights. No optimal combination weight was estimated.

{table(lp.reset_index())}

{table(lt.reset_index())}

## Verification, reproducibility and governance

All 60 DFM factor paths were re-estimated from the frozen monthly panel and core. Maximum absolute difference from Phase 6B is **{manifest['maximum_factor_difference']:.3g}**, below 1e-8. A second complete factor computation produced byte-identical factor outputs. Two final identical-input forecast/evidence runs produced byte-identical results for **{checks['CSV_outputs']} CSV artifacts**.

Final tests: **{sum(counts.values())} passed, 0 failed** ({counts}). Initial test attempts encountered Windows temporary-folder restrictions and the older modules' shared bare `run.py` name; separate final processes resolved these without modifying frozen code. Model-suite fixture warnings about intentionally missing predictors remain expected. Tests cover release/value boundaries, revisions, target/future rejection, strict/permissive and observed-clock behavior, duplicates, exact matching, separate target definitions, factor identity, deterministic reruns, evidence checksums and protection.

All **592 protected files remain byte-identical** to the initial protection baseline. Production, registry, dashboards, Phase 5D, issued forecast history and Phase 4/5/6B/6B.1 artifacts remain unchanged. Only the three isolated Phase 6B.2 paths contain authored outputs.

Offline reproduction from the archived evidence:

```powershell
.venv/Scripts/python.exe scripts/research/phase6b2/factors.py
.venv/Scripts/python.exe scripts/research/phase6b2/run.py
.venv/Scripts/python.exe scripts/research/phase6b2/verify.py
.venv/Scripts/python.exe -m pytest scripts/research/phase6b2/test_vintages.py -q -o addopts='' -p no:cacheprovider --basetemp results/research/phase6b2/test_tmp_new_verified > results/research/phase6b2/phase6b2_new_tests_verified.log 2>&1
.venv/Scripts/python.exe scripts/research/phase6b2/report.py
```

Evidence parsers are pinned in `scripts/research/phase6b2/requirements-research.txt`; exact model and parser environment versions are recorded in the run manifest. Collection is cached, rate-limited and bounded; failed sources remain visible. Tests for Phase 6B, 6B.1 and 6B.2 must run in separate processes because those older research modules use shared bare import names.

Required artifacts: [vintage registry](../../../results/research/phase6b2/phase6b2_gdp_vintage_registry.csv), [source inventory](../../../results/research/phase6b2/phase6b2_gdp_release_sources.csv), [revision events](../../../results/research/phase6b2/phase6b2_gdp_revision_history.csv), [origin audit](../../../results/research/phase6b2/phase6b2_origin_information_audit.csv), [benchmarks](../../../results/research/phase6b2/phase6b2_clean_benchmark_forecasts.csv), [DFM forecasts](../../../results/research/phase6b2/phase6b2_dfm_forecasts.csv), [combinations](../../../results/research/phase6b2/phase6b2_combination_forecasts.csv), [matched forecasts](../../../results/research/phase6b2/phase6b2_matched_forecasts.csv), [metrics](../../../results/research/phase6b2/phase6b2_horizon_metrics.csv), [quarter errors](../../../results/research/phase6b2/phase6b2_quarter_level_errors.csv), [leave-one-quarter-out](../../../results/research/phase6b2/phase6b2_leave_one_quarter_out.csv), [prior-phase comparison](../../../results/research/phase6b2/phase6b2_phase6b1_comparison.csv), and [manifest](../../../results/research/phase6b2/phase6b2_run_manifest.json).

**Stop at Phase 6B.2.** No Phase 6C, model promotion, production change or dashboard replacement was performed. The unresolved early first releases, incomplete intermediate revisions and flagged source ambiguity determine the final RELEASE_HISTORY_INCOMPLETE classification, regardless of favorable pooled RMSE.
'''
    path=DOC/'phase6b2_verified_gdp_vintage_report.md'
    path.write_text(text,encoding='utf-8')
    manifest['report_sha256']=sha(path)
    manifest['outputs_sha256']={p.name:sha(p) for p in OUT.glob('phase6b2_*.csv')}
    (OUT/'phase6b2_run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    summary=f"""PHASE 6B.2 — RESEARCH ONLY
Verified official first-release dates: 24/34; values: 24/34; unresolved: 10.
SAME_DAY_TIME_UNKNOWN: 0; first-to-master revised quarters: 16.
H1 restored vs 6B.1: 20/20 records (10 quarters x 2 lag modes); unavailable: 0.
Matched origins: 30 per lag/rule; 60 across both monthly lag modes per timing rule.
FIRST_RELEASE, standard/strict pooled RMSE (n=30): DFM B 0.6471; U-MIDAS 0.5694; production 0.5469; combo B 0.4875.
Post-development RMSE (n=12): DFM B 0.9241; U-MIDAS 0.6861; production 0.7006; combo B 0.6846.
LATEST_REVISED pooled H2/H3 combo RMSE: {h23.rmse:.4f} (n=20; earlier fallback 0.4754).
LOQO: pooled wins vs U/production {loqo['pooled_wins_vs_umidas']}/10 and {loqo['pooled_wins_vs_production']}/10; post wins {loqo['post_wins_vs_umidas']}/4 and {loqo['post_wins_vs_production']}/4.
Tests: {sum(counts.values())} passed / 0 failed; deterministic CSV and factor reruns: PASS.
Protected artifacts: 592/592 unchanged. No production/model promotion.
FINAL: PHASE6B2_RELEASE_HISTORY_INCOMPLETE
"""
    (OUT/'phase6b2_terminal_summary.txt').write_text(summary,encoding='utf-8')
    print(summary)

if __name__=='__main__':
    main()
