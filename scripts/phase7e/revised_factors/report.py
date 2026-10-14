"""Round-trip CSV reporting and a self-contained interactive research dashboard."""
import json
from pathlib import Path

import pandas as pd

from scripts.phase7e.grouping import BLOCKS, RATIONALE
from scripts.phase7e.revised_factors.configuration import EXCLUSIONS
from scripts.operations.prospective.common import safe

OUT = Path(__file__).resolve().parents[3]/'results/phase7e/revised_factors'
ORIGINAL = OUT.parent


def read(name):
    return pd.read_csv(OUT/f'revised_phase7e_{name}.csv', float_precision='round_trip')


def table(frame, columns):
    def value(v):
        return 'unavailable' if pd.isna(v) else f'{v:.6f}' if isinstance(v, float) else str(v)
    return '| ' + ' | '.join(columns) + ' |\n| ' + ' | '.join(['---']*len(columns)) + ' |\n' + '\n'.join(
        '| ' + ' | '.join(value(v).replace('|','/') for v in row) + ' |' for row in frame[columns].itertuples(index=False, name=None)) + '\n'


def render():
    comparison = read('comparison'); now = read('current_nowcasts'); compositions = read('factor_compositions')
    forecasts = read('forecasts'); diagnostics = read('estimation_diagnostics'); loadings = read('factor_loadings')
    current_diag = diagnostics.loc[diagnostics.evaluation_group.eq('CURRENT')]
    current_loads = loadings.loc[loadings.evaluation_group.eq('CURRENT')]
    contributions = read('gdp_contributions')
    current_contrib = contributions.loc[contributions.evaluation_group.eq('CURRENT')]
    manifest = json.loads((OUT/'revised_phase7e_run_manifest.json').read_text())
    original_forecasts = pd.read_csv(ORIGINAL/'phase7e_forecasts.csv', float_precision='round_trip')
    original_contrib = pd.read_csv(ORIGINAL/'phase7e_gdp_contributions.csv', float_precision='round_trip')
    original_loads = pd.read_csv(ORIGINAL/'phase7e_factor_loadings.csv', float_precision='round_trip')
    original_contrib = original_contrib.loc[original_contrib.evaluation_group.eq('CURRENT')].assign(specification='ORIGINAL')
    original_loads = original_loads.loc[original_loads.evaluation_group.eq('CURRENT')].assign(specification='ORIGINAL')
    summary = []
    for b, name in BLOCKS.items():
        f = compositions.loc[compositions.economic_group.eq(b)]
        summary.append(dict(factor=b, interpretation=name, original_count=len(f),
            revised_count=int(f.revised_factor_included.sum()), original_core_count=int(f.original_core_selected.sum()),
            revised_core_count=int(f.revised_core_selected.sum())))
    summary = pd.DataFrame(summary)
    prose = (
        'Research experiment only. Production COMBO_50_50 remains **8.180901340616275%**; no promotion. '
        'Original Phase 7E outputs, master datasets and registry are preserved.\n\n'
        'The target is **2026Q3 cumulative real year-to-date GDP YoY**, not standalone-quarter growth. '
        f"The unchanged research cutoff is **{manifest['cutoff']}**. H1/H2/H3 are target-quarter month ends.\n\n"
        '**Information limit:** predictor release dates and historical vintages are absent from the original research workbook. '
        'The unchanged assumed-lag gate is respected, and GDP training uses STRICT observed publication vintages with target GDP excluded. '
        'This is PSEUDO_REAL_TIME_NOT_VINTAGE_VERIFIED; authentic predictor release restrictions cannot be verified from these inputs. '
        'No missing release date is invented. Revised-data and vintage uncertainty remains.\n\n'
        'Each factor, its training standardization, missing-data PCA, AR(2), one-sided filter, hierarchical projection and GDP bridge '
        'is refitted inside each archived origin. No fit is shared across origins. Target-quarter data never train factor parameters. '
        'All transformations, minimum-history thresholds, penalties, weighting formula, quarterly covariate rules, GDP actuals and windows are unchanged. '
        'Family weights are recomputed by the original formula on the retained measurement set.\n\n'
        'Both original F5 sign anchors are excluded. Retained broad money M2 fixes the revised F5 positive orientation in full and core fits. '
        'This changes the sign convention only; tests verify sign-invariant predictions and contributions. '
        'No indicator is added, replaced or moved. E3 remains the original two-stage hierarchical approximation, '
        'with F5 as reference block; E3 variable loadings here are first-stage measurement loadings.\n\n'
        'Bias is **actual minus prediction**, consistent with the original Phase 7E convention. '
        'Negative bias means overprediction. R² is 1−SSE/SST, not squared correlation; out-of-sample R² uses matched AR1 '
        'and unchanged COMBO_50_50 benchmark errors. COMBO research scores use the archived comparable GDP actuals; '
        'they are distinct from frozen production first-release metrics.\n\n'
    )
    md = '# Revised Phase 7E factors — research experiment\n\n' + prose
    md += '## Factor membership\n\n' + table(summary, list(summary))
    md += '\nDeliberate exclusions retained in the inventory:\n\n' + '\n'.join(
        f'- {b}: {label}. {reason}' for label, (b, reason) in EXCLUSIONS.items()) + '\n\n'
    md += 'E1 retains F1–F4 (52 monthly indicators); E2/E3 retain F1–F5 (88); E4 adds its unchanged five quarterly covariates. '
    md += 'The original 17-variable economic core becomes **15 variables**: F1=3, F2=4, F3=3, F4=3, F5=2. Aggregate industry was already absent from the core.\n\n'
    md += '## 2026Q3 research nowcasts\n\n' + table(now, ['model','original_prediction','revised_prediction','nowcast_change_pp'])
    md += '\n## Identical-origin evaluation\n\n'
    for sample in ['MATCHED_ALL','MATCHED_DEVELOPMENT','MATCHED_HOLDOUT']:
        md += f'### {sample}\n\n' + table(comparison.loc[comparison['sample'].eq(sample) & comparison.horizon.eq('ALL')],
            ['model','original_rmse','revised_rmse','revised_mae','revised_bias','revised_r2','revised_r2_os_ar1',
             'revised_r2_os_combo_50_50','revised_n_forecasts','revised_n_quarters','performance']) + '\n'
    md += 'All rows compare original and revised models on identical common successful origins and identical latest-revised GDP actuals. '
    md += 'The primary holdout remains 2025Q3–2026Q2 (four target quarters, 12 forecasts). Improvement means lower matched RMSE; '
    md += 'it is descriptive evidence on a small, previously examined holdout, not proof of forecast superiority.\n\n'
    md += '## Forecast performance by horizon\n\n' + table(comparison.loc[comparison['sample'].eq('MATCHED_HOLDOUT') & comparison.horizon.ne('ALL')],
        ['model','horizon','original_rmse','revised_rmse','original_mae','revised_mae','original_bias','revised_bias',
         'original_r2','revised_r2','revised_n_forecasts','performance'])
    md += '\n## Economic interpretation\n\n'
    md += 'F1–F4 retain their original economic meaning; F1 now omits the redundant total while preserving all components. '
    md += 'Full F5 retains detailed consumer and producer price indices, money and rates. Its interpretation remains price/monetary co-movement, '
    md += 'with heterogeneous loadings rather than a causal inflation shock. The core F5 now contains only M2 and the lending rate, '
    md += 'so it represents liquidity and financing conditions and has **no direct inflation measurement**. '
    md += 'The original F5 number and broad economic label remain, with this narrower core meaning explicitly disclosed. '
    md += 'Other caveats persist: nominal industrial/demand series, overlapping detailed components and short services history.\n\n'
    md += table(current_diag, ['model','factor','n_declared','n_estimable','anchor','mean_pairwise_correlation',
        'positive_loading_share','effective_loading_count','observed_share'])
    md += '\n## Current GDP attribution\n\n'
    md += 'Contributions are standardized bridge coefficient × signal, in GDP percentage points. Include intercept, available GDP lag and E4 covariates to reconcile totals. They are statistical attribution, not causal sector GDP contributions.\n\n'
    md += table(current_contrib.loc[~current_contrib.component.str.startswith('MISSING_')], ['model','component','value'])
    failures = forecasts.loc[forecasts.prediction.isna()]
    md += '\n## Failures and validation\n\n'
    md += f"{len(failures)} revised forecast attempts failed visibly, predominantly early origins without enough services history. "
    md += f"All {manifest['original_successes_reproduced']} successful original model/origin fits were recomputed; max archive discrepancy {manifest['original_reproduction_max_error']:.3g} pp. "
    md += f"Contribution reconciliation error: {manifest['max_decomposition_error']:.3g} pp. Failed forecasts are excluded symmetrically by origin matching, never filled. "
    md += 'See revised_phase7e_failures.csv and validation.json for executed tests, browser checks and protection hashes.\n\n'
    md += '## Reproduction\n\n```powershell\n.venv/Scripts/python.exe -B -m scripts.phase7e.revised_factors.run\n.venv/Scripts/python.exe -B -m scripts.phase7e.revised_factors.validate\n```\n\n'
    md += '## Exact retained variables (full blocks and core)\n\n'
    for b, name in BLOCKS.items():
        f = compositions.loc[compositions.economic_group.eq(b) & compositions.revised_factor_included]
        md += f'### {b} — {name}\n\n' + '\n'.join(
            '- ' + r.original_label + (' **[core]**' if r.revised_core_selected else '') for r in f.itertuples()) + '\n\n'
    (OUT/'revised_phase7e_results.md').write_text(md, encoding='utf8')
    payload = dict(models=list(now.model), production_forecast=manifest['production_forecast'], cutoff=manifest['cutoff'],
        target_quarter='2026Q3', comparisons=comparison.to_dict('records'), nowcasts=now.to_dict('records'),
        compositions=compositions.to_dict('records'), summary=summary.to_dict('records'),
        forecasts=pd.concat([original_forecasts.loc[original_forecasts.model.isin(now.model)].assign(specification='ORIGINAL'), forecasts], ignore_index=True).to_dict('records'),
        matched_origins=read('matched_origins').to_dict('records'),
        contributions=pd.concat([original_contrib,current_contrib], ignore_index=True).to_dict('records'),
        loadings=pd.concat([original_loads,current_loads], ignore_index=True).to_dict('records'),
        diagnostics=current_diag.to_dict('records'), block_names=BLOCKS,
        methodology=prose.replace('**',''), failures=failures.to_dict('records'),
        interpretation='F1–F4 retain their economic meaning. Full F5 retains detailed price indices, money and rates. Core F5 now measures M2 and lending-rate co-movement, without direct inflation measurement. Factors and contributions are descriptive, not causal.')
    template = Path(__file__).with_name('dashboard.html').read_text(encoding='utf8')
    serialized = json.dumps(safe(payload), allow_nan=False, separators=(',',':')).replace('</','<\\/')
    (OUT/'revised_phase7e_dashboard.html').write_text(template.replace('__DATA__',serialized), encoding='utf8')


if __name__ == '__main__':
    render()
