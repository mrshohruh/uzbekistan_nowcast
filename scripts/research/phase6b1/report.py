"""Report corrected coverage and matched evidence without changing history."""
import numpy as np
import pandas as pd


def markdown(f):
    lines=['| '+' | '.join(f.columns)+' |','| '+' | '.join(['---']*len(f.columns))+' |']
    for row in f.itertuples(index=False,name=None):
        lines.append('| '+' | '.join(f'{v:.4f}' if isinstance(v,(float,np.floating)) and pd.notna(v) else ('unavailable' if pd.isna(v) else str(v)) for v in row)+' |')
    return '\n'.join(lines)


def write_report(root,out,doc,manifest,forecasts,metric,beforeafter,origins,bench_audit):
    available=metric.loc[metric['sample'].eq('ALL_AVAILABLE_ORIGIN') & metric.lag_mode.eq('standard')]
    pooled=available.loc[available.evaluation_group.eq('POOLED_RESEARCH_ONLY')]
    post=available.loc[available.evaluation_group.eq('HISTORICAL_POST_DEVELOPMENT_TEST')]
    matching=metric.loc[metric['sample'].eq('MATCHED_SAMPLE') & metric.lag_mode.eq('standard') &
                        metric.comparator.eq('UMIDAS_USD_CLEAN_GDP_BOUNDARY') & metric.horizon.eq('ALL')]
    oldnew=beforeafter.loc[beforeafter.lag_mode.eq('standard') & beforeafter.horizon.eq('ALL')]
    frozen_headlines=pd.read_csv(root/'results/research/phase6b/phase6b_pooled_metrics.csv')
    frozen_headlines=frozen_headlines.loc[frozen_headlines.lag_mode.eq('standard') & frozen_headlines.horizon.eq('ALL')]
    headline_rows=[]
    for clean_name,old_name in [('DFM_DOMESTIC_3__BRIDGE_A_CLEAN','DFM_DOMESTIC_3__BRIDGE_A'),
                              ('DFM_DOMESTIC_3__BRIDGE_B_CLEAN','DFM_DOMESTIC_3__BRIDGE_B'),
                              ('UMIDAS_USD_CLEAN_GDP_BOUNDARY','umidas_usd_uzs_mom_dlog'),
                              ('PRODUCTION_ENSEMBLE_CLEAN_GDP_BOUNDARY','ensemble_ar2_umidas_usd'),
                              ('COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN','COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B')]:
        old=frozen_headlines.loc[frozen_headlines.model.eq(old_name)].iloc[0]
        new=pooled.loc[pooled.model.eq(clean_name) & pooled.horizon.eq('ALL')].iloc[0]
        headline_rows.append(dict(model=clean_name,old_n=int(old.n),old_rmse=old.rmse,old_mae=old.mae,
                                  clean_n=int(new.n_forecasts),clean_rmse=new.rmse,clean_mae=new.mae,
                                  sample_note='DIFFERENT_SAMPLES: see matched table; no direct gain claim'))
    headline=pd.DataFrame(headline_rows)
    headline.to_csv(out/'phase6b1_headline_sample_comparison.csv',index=False)
    audit_counts=bench_audit.groupby(['benchmark_model','horizon','leakage_status']).size().reset_index(name='model_origin_count')
    by_h=origins.loc[~origins.prior_GDP_available_at_origin].groupby('horizon').size().to_dict()
    post_combo=post.loc[post.model.eq('COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN') & post.horizon.eq('ALL')].iloc[0]
    matched_combo=oldnew.loc[oldnew.model.eq('COMBO_EQUAL__DFM_DOMESTIC_3__BRIDGE_B_CLEAN') &
                           oldnew.evaluation_group.eq('HISTORICAL_POST_DEVELOPMENT_TEST')].iloc[0]
    report=f'''# Phase 6B.1 — GDP information-boundary repair

**{manifest['classification']} — research only.** Complementary DFM information survives on H2/H3, but the original all-horizon claim loses H1 coverage. No model was promoted; all historical Phase 6B evidence remains intact.

## Bug reproduction completed before repair

The immutable Phase 6B `bridge()` was imported and executed for **2024Q2 H1 standard**, origin **2024-04-30**. Registry timing puts 2024Q1 GDP availability at **2024-05-01**. Changing that unavailable GDP to 999999 changes the forecast; see the deterministic leak reproduction CSV/JSON. This is **LEAK_CONFIRMED under repository timing**, not proof of an observed actual historical publication date. The defect is unconditional chronological GDP selection in `run.py` and unconditional target-lag access in `bridge()`. Bridge A's dependent-variable training also has the same missing release gate.

## GDP source and availability audit

Existing target: `data/master/gdp_quarterly.parquet:gdp_real_yoy_pct`, SIAT dataset **3698**, native ID **1.01.01.0059**, Uzbekistan national selector **1700**. Quarterly published growth convention is unchanged; GDP is never interpolated.

Master, processed GDP, release calendar, release-availability analysis, observations, vintages, download log, raw descriptor/payload/provenance files and frozen Phase 4/5 code were inspected. **Zero of 34 quarters has a verified per-quarter historical release date.** Master dates refer to the dataset update on 2026-07-31. Raw metadata also has dataset-first-publication 2024-07-09: that is not a release calendar for every historical GDP observation. Neither date was assigned to individual quarterly first releases.

The explicit hierarchy accepts quarter-specific verified/publication metadata first, documented historical dates second, a justified conservative repository rule third, otherwise unavailable. No current stored evidence qualifies for the first two tiers. The fallback is **quarter end + 46 days**, derived from the existing registry's **31-day GDP lag** and the existing `effective_release_day(..., 'conservative')` **15-day cushion**, already used by Phase 5A `detect_target_quarter`. The same conservative GDP fallback applies to both monthly standard/conservative experiments; **monthly masks and lag definitions are unchanged**. The 31-day rule is shown only in the timing-sensitivity audit, not selected by forecast accuracy.

Actual `release_date` remains null. The separate `available_date` is explicitly an assumed rule cutoff, quality **APPROXIMATE_FALLBACK**, verified=false. All 34 quarterly availability decisions use this fallback; actual publication remains unknown for all 34. `available_for_H1/H2/H3` in the GDP audit refers to the following quarter's horizons. Thus this is defensible **calendar pseudo-real-time research under a documented conservative rule**, not a verified vintage backtest. Frozen benchmark availability is policy-auditable; actual historical timing is UNVERIFIABLE.

## Repair and preserved DFM

`available_gdp_as_of` gates GDP by explicit availability date before excluding the target/later quarters. The repaired bridge accepts only an `AvailableGDP` object carrying its origin and dated observations. Defensive assertions reject wrong origins, target GDP, later GDP or unreleased rows. Bridge A intersects available GDP with complete historical factor quarters. Bridge B also requires every training lag to be available and returns **PRIOR_QUARTER_GDP_NOT_AVAILABLE** when target-minus-one GDP is absent. No previous available quarter or model forecast is substituted.

The Phase 6B DynamicFactor implementation is imported unchanged: one factor, AR(1), diagonal white-noise idiosyncratic errors, identical training-only scaling and monthly masking, filtered factors and latent-state prediction through quarter end. All **60** primary factor-origin paths were re-estimated and checked against stored Phase 6B states; maximum discrepancy **{manifest['DFM_core_identity_max_error']:.3g}**, tolerance 1e-8. No imports/services/POS/two-factor model was rerun. Training audits give each dependent and lagged GDP cutoff.

## Origins and frozen benchmark audit

The unchanged monthly sample is **2021-01–2026-08**. Unchanged target quarters are **2024Q1–2026Q2**: six development and four historical post-development quarters. There are 30 calendar origins per monthly lag mode, not 30 independent GDP outcomes.

**{manifest['n_Bridge_B_origins_affected']} Bridge B origin records** lose prior GDP availability: {by_h}. This means **10 H1 forecasts per lag mode**; H2/H3 are unaffected. All ten target quarters' H1 origins are affected. Bridge A also excludes the prior GDP from H1 dependent-variable training. At 2024Q1 H1 this leaves only 11 aligned training GDP quarters, so Bridge A is unavailable; remaining H1 Bridge A origins can be estimated. Bridge B and its combinations remain unavailable at every H1.

Frozen Phase 4B `_benchmark_rows/_midas_rows`, Phase 4C `_forecast_rows`, `benchmarks.py` and `midas.py` use all chronological prior GDP. AR(1), AR(2), U-MIDAS and the ensemble therefore have the same GDP boundary defect under the conservative rule. Across all 22 frozen target quarters, **{manifest['n_benchmark_model_origins_affected']} model-origin records** are affected; **{manifest['n_benchmark_issued_forecasts_affected']}** had an issued finite forecast. Within the ten-quarter DFM window, **{manifest['n_benchmark_model_origins_affected_in_DFM_window']}** model-origin records are affected. Counts include both lag modes and each benchmark model separately, not distinct GDP outcomes.

{markdown(audit_counts)}

Clean research-only AR(1)/AR(2)/U-MIDAS/production-ensemble reruns retain the frozen OLS specifications and U-MIDAS minimum 15 effective rows. Missing target-minus-one GDP makes these exact one-step specifications unavailable; using the last available quarter would forecast the wrong quarter. No new recursive multi-step benchmark was introduced. On all eligible finite frozen origins, clean reruns reproduce the original forecasts within 1e-9. Production operational Phase 5A's availability-aware code was not changed; this audit concerns the frozen historical validation generator, not a claim that the current live production code shares its omission.

## Pooled standard-monthly-lag metrics

Bias = actual minus forecast. Zero-count horizons are explicit. These all-available rows may have different coverage; use the matched comparison below for accuracy claims.

{markdown(pooled[['model','horizon','n_forecasts','n_target_quarters','rmse','mae','bias']])}

## Exactly matched comparison against clean U-MIDAS

Both models in each row use the same origin set and denominator. Development, post-development and pooled results are separate. Bridge A H1 gains cannot be compared with an unavailable U-MIDAS H1 forecast.

{markdown(matching[['model','evaluation_group','n_forecasts','n_target_quarters','rmse','mae','benchmark_rmse','benchmark_mae']])}

## Before/after on identical surviving origins

{markdown(oldnew[['model','evaluation_group','n_forecasts','n_target_quarters','old_rmse','rmse','old_mae','mae','rmse_change']])}

For transparency, the original and corrected headline denominators are shown below. These **different-sample headlines cannot establish an accuracy gain**:

{markdown(headline)}

Bridge A's direct information-boundary effect on the same 29 standard origins is RMSE **0.866009 to 0.885054**, MAE **0.658079 to 0.677697**. Standalone Bridge B on the surviving 20 origins has RMSE **0.629909**, worse than clean U-MIDAS **0.615566**. Thus the old pooled standalone improvement also fails to survive on the clean comparison sample.

The original **0.7319** post-development combination RMSE covered **12 standard origins**. Its corrected headline covers **8 H2/H3 origins**, RMSE **{post_combo.rmse:.6f}**, MAE **{post_combo.mae:.6f}**. The old combination on those **same eight origins** has RMSE **{matched_combo.old_rmse:.6f}**. Consequently the smaller headline is a coverage change, not an accuracy improvement caused by the repair. The original all-horizon 0.7319 result **does not survive as a valid clean-information headline**; surviving H2/H3 forecasts and complementary information do survive unchanged.

## Required diagnostic answers

1. Old Bridge B used unavailable prior GDP at **20 origin records**, all H1 (10 standard, 10 conservative), **under the explicit 46-day policy**. Actual first-release counts cannot be verified.
2. Affected targets: every quarter 2024Q1–2026Q2 at H1. The 31-day sensitivity alone also excludes the Q2 H1 origins for 2024/2025/2026; these are assumptions, not recovered actual dates.
3. Bridge A's H1 dependent-variable training used the same unavailable prior GDP; repaired rows are removed and minimum-training failures are retained.
4. AR(1): same historical-generator boundary defect, now release-gated.
5. AR(2): same defect, now release-gated.
6. U-MIDAS: its GDP targets and target lag were not release-gated; clean reruns gate both while preserving its monthly kernel.
7. Frozen ensemble: inherits unavailable components. No change to the current production ensemble or operational code.
8. Bridge B RMSE is unchanged on identical surviving H2/H3 origins; old all-horizon comparisons must be withdrawn.
9. Combination RMSE likewise is unchanged on matched surviving origins; a denominator change must not be called a gain.
10. The 0.7319 all-horizon headline is withdrawn; the corrected eight-origin value is {post_combo.rmse:.6f}.
11. DFM retains complementary information on H2/H3 relative to clean U-MIDAS and its combination has lower RMSE than the clean production ensemble. Later-partition combination MAE is slightly higher than the production ensemble, so dominance on every metric is not claimed. Standalone Bridge B no longer beats U-MIDAS on pooled matched RMSE. Evidence is limited to ten GDP targets overall and four later quarters. No H1 combination claim remains. Classification: **PHASE6B_RESULT_WEAKENED** because useful matched combination evidence persists with materially reduced coverage and weaker standalone support.

## Governance and reproduction

All **{manifest['protected_count']} protected files**, including Phase 6B outputs/code/report/dashboard and earlier artifacts, are SHA256-identical before and after. Stored raw GDP archives also have inspection hashes checked during finalization. Registries, canonical datasets, production, Phase 5D, forecast history and dashboards were not modified. New writes are confined to the three Phase 6B.1 directories. Tests and finalization append their evidence below.

Run the commands in `scripts/research/phase6b1/README.md`. No network access or data collection occurs. Stop after Phase 6B.1; no Phase 6C action is started.
'''
    doc.mkdir(parents=True,exist_ok=True)
    (out/'phase6b1_results.md').write_text(report,encoding='utf-8')
    (doc/'phase6b1_gdp_information_boundary_report.md').write_text(report,encoding='utf-8')
