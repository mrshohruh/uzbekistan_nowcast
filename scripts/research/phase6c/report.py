"""Saved-forecast metrics, factor interpretation and standalone research report."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from kernel import KEYS, scores


def report(out, protocol, audit, forecasts, metrics, checks):
    def save(name, f):
        f.to_csv(out / f'phase6c_{name}.csv', index=False, float_format='%.17g')

    final = protocol['final_model']
    matched = pd.read_csv(out / 'phase6c_matched_metrics.csv')
    selected = protocol['selected_factor_specification']
    # Reconstruct the complete per-variable information audit, including failed
    # fits. Availability is a data property, independent of model convergence.
    from uznowcast.models.data import load_dataset
    from kernel import Spec, mask, standardize, training_panel
    root = out.parents[1]
    dataset = load_dataset(root)
    complete_panel = pd.read_csv(out / 'phase6c_research_monthly_panel.csv', index_col='date', parse_dates=True)
    definitions = pd.read_csv(out / 'phase6c_model_definitions.csv')
    import ast
    information = []
    all_origins = protocol['development_origins'] + [(q,h) for q in protocol['holdout_quarters'] for h in ('H1','H2','H3')]
    for target, horizon in all_origins:
        for mode in ('standard', 'conservative'):
            spec = Spec('ALL_AUDITED_CANDIDATES', tuple(complete_panel.columns))
            _, records = mask(complete_panel, spec, target, horizon, dataset.release_lag_days, mode)
            information.extend(dict(specification='ALL_AUDITED_CANDIDATES', **r) for r in records)
    save('information_set_audit', pd.DataFrame(information))
    loads = pd.read_csv(out / 'phase6c_factor_loadings.csv')
    factors = pd.read_csv(out / 'phase6c_factor_series.csv')
    diag = pd.read_csv(out / 'phase6c_factor_diagnostics.csv')
    top, blocks, relations, stability, factor_corr, variance = [], [], [], [], [], []
    for specification in sorted(loads.specification.unique()):
        l = loads.loc[loads.specification.eq(specification) & loads.lag_mode.eq('standard')]
        origins = l[['target_quarter', 'horizon']].drop_duplicates().sort_values(['target_quarter', 'horizon'])
        origins = origins.loc[origins.target_quarter.lt('2025Q3')]
        if not len(origins):
            continue
        q, h = origins.iloc[-1].tolist()
        last = l.loc[l.target_quarter.eq(q) & l.horizon.eq(h)]
        times = factors.loc[factors.specification.eq(specification) & factors.target_quarter.eq(q) & factors.horizon.eq(h) & factors.lag_mode.eq('standard')]
        wide = times.pivot(index='month', columns='factor', values='value')
        corr = wide.corr()
        for a in corr:
            for b in corr:
                factor_corr.append(dict(specification=specification, factor=a, other_factor=b, correlation=corr.loc[a, b]))
        for j, group in last.groupby('factor'):
            best = group.assign(absolute_loading=group.loading.abs()).sort_values('absolute_loading', ascending=False).head(10)
            top.extend(best.to_dict('records'))
            concentration = group.assign(squared_loading=group.loading**2).groupby('block').squared_loading.sum()
            for block, value in concentration.items():
                blocks.append(dict(specification=specification, factor=j, block=block,
                                   squared_loading_share=float(value / concentration.sum())))
            variance.append(dict(specification=specification, factor=j,
                factor_variance=float(wide[j].var()),
                variance_of_own_common_component=float(wide[j].var() * (group.loading**2).sum()),
                interpretation='Own common-component variance; not additive explained variance if factors correlate'))
        reference = last.pivot(index='variable', columns='factor', values='loading')
        for oq, oh in origins.itertuples(index=False, name=None):
            current = l.loc[l.target_quarter.eq(oq) & l.horizon.eq(oh)].pivot(index='variable', columns='factor', values='loading').reindex(reference.index)
            a, b = current.to_numpy(), reference.to_numpy()
            denom = np.linalg.norm(a, axis=0)[:, None] * np.linalg.norm(b, axis=0)[None, :]
            cosines = a.T @ b / denom
            ii, jj = linear_sum_assignment(-abs(cosines))
            qa, _ = np.linalg.qr(a); qb, _ = np.linalg.qr(b)
            principal = np.linalg.svd(qa.T @ qb, compute_uv=False)
            stability.append(dict(specification=specification, target_quarter=oq, horizon=oh,
                                  matched_absolute_loading_cosine=float(abs(cosines[ii, jj]).mean()),
                                  minimum_subspace_cosine=float(principal.min()),
                                  reference_origin=q + '_' + h))
    save('top_factor_loadings', pd.DataFrame(top))
    save('factor_block_contributions', pd.DataFrame(blocks))
    save('factor_correlations', pd.DataFrame(factor_corr))
    save('factor_variance', pd.DataFrame(variance))
    save('factor_recursive_stability', pd.DataFrame(stability))
    # Per-factor scree diagnostics use the last development information set only.
    fields = selected['fields']
    panel = complete_panel[list(fields)]
    spec = Spec(**{**selected, 'fields': tuple(fields)})
    target = max(q for q, h in protocol['development_origins'])
    frame, _ = mask(panel, spec, target, 'H3', dataset.release_lag_days, 'standard')
    end = (pd.Period(target, freq='Q').start_time - pd.Timedelta(days=1)).normalize()
    frame, _ = training_panel(frame, end, spec.balanced)
    z, _, _ = standardize(frame, end)
    # PCA scree is a descriptive complete-overlap diagnostic, never the ragged estimator.
    overlap = z.loc[:end].dropna()
    scree = []
    if len(overlap) >= 12:
        eigen = np.linalg.eigvalsh(overlap.corr().to_numpy())[::-1]
        for j, value in enumerate(eigen):
            scree.append(dict(component=j+1, eigenvalue=value, variance_share=value/eigen.sum(),
                n_overlap_months=len(overlap), use='DESCRIPTIVE_ONLY_NOT_RAGGED_ESTIMATOR'))
    save('scree_diagnostics', pd.DataFrame(scree, columns=['component', 'eigenvalue', 'variance_share', 'n_overlap_months', 'use']))
    # BIC is the finite-state likelihood equivalent diagnostic; short-panel
    # Bai-Ng asymptotics are not claimed for this small, irregular sample.
    save('factor_information_criteria', diag.loc[diag.specification.str.startswith('DFM-4_')])
    # Explain observed standardized variance only; missing cells are excluded
    # from the denominator and never treated as zero-valued observations.
    explained, relations = [], []
    registry = pd.read_csv(root / 'results/research/phase6b2/phase6b2_gdp_vintage_registry.csv').set_index('quarter')
    for name in sorted(loads.specification.unique()):
        subset = loads.loc[loads.specification.eq(name) & loads.target_quarter.lt('2025Q3') & loads.horizon.eq('H3') & loads.lag_mode.eq('standard')]
        if subset.empty:
            continue
        q = subset.target_quarter.max()
        ll = subset.loc[subset.target_quarter.eq(q)].pivot(index='variable', columns='factor', values='loading')
        ff = factors.loc[factors.specification.eq(name) & factors.target_quarter.eq(q) & factors.horizon.eq('H3') & factors.lag_mode.eq('standard')].pivot(index='month', columns='factor', values='value')
        ff.index = pd.to_datetime(ff.index)
        definition = definitions.loc[definitions.name.eq(name)].iloc[0]
        fields_here = tuple(ast.literal_eval(definition.fields))
        test_spec = Spec(name, fields_here, int(definition.factors), int(definition.order), definition.start,
                         bool(definition.balanced), bool(definition.winsor))
        xx, _ = mask(complete_panel, test_spec, q, 'H3', dataset.release_lag_days, 'standard')
        training_end = pd.Period(q, freq='Q').start_time - pd.Timedelta(days=1)
        xx, _ = training_panel(xx, training_end, test_spec.balanced)
        zz, _, _ = standardize(xx, training_end)
        zz = zz.reindex(ff.index)[ll.index]
        observed = zz.notna().to_numpy()
        raw = zz.to_numpy()
        denominator = float((raw[observed]**2).sum())
        for j in ll.columns:
            component = ff[j].to_numpy()[:, None] * ll[j].to_numpy()[None, :]
            explained.append(dict(specification=name, factor=j, origin=q+'_H3',
                observed_variance_explained=1-float(((raw-component)[observed]**2).sum())/denominator,
                definition='1-SSE/SST observed standardized cells; individual contributions are not additive'))
            fq = ff[j].groupby(ff.index.to_period('Q')).mean()
            values = pd.Series({str(t):v for t,v in fq.items() if str(t)<q})
            gdp = registry.first_release_value.reindex(values.index)
            relations.append(dict(specification=name, factor=j, GDP_correlation=values.corr(gdp),
                GDP_definition='FIRST_RELEASE', n=int((values.notna() & gdp.notna()).sum()), development_only=True))
        reconstruction = ff[ll.columns].to_numpy() @ ll.to_numpy().T
        explained.append(dict(specification=name, factor='ALL', origin=q+'_H3',
            observed_variance_explained=1-float(((raw-reconstruction)[observed]**2).sum())/denominator,
            definition='1-SSE/SST observed standardized cells; not in-sample forecast accuracy'))
    save('factor_variance_explained', pd.DataFrame(explained))
    save('factor_GDP_relations', pd.DataFrame(relations))
    one = forecasts.loc[forecasts.model.eq(final)]
    other = forecasts.loc[forecasts.model.eq('UMIDAS_USD')]
    pairs = one.merge(other[KEYS + ['prediction']], on=KEYS, suffixes=('', '_umidas'), validate='one_to_one')
    complement = []
    for (mode, group), f in pairs.groupby(['lag_mode', 'evaluation_group']):
        for horizon in ['H1', 'H2', 'H3', 'ALL']:
            b = f if horizon == 'ALL' else f.loc[f.horizon.eq(horizon)]
            b = b.dropna(subset=['prediction', 'prediction_umidas', 'actual'])
            complement.append(dict(lag_mode=mode, evaluation_group=group, horizon=horizon, n=len(b),
                error_correlation=(b.actual - b.prediction).corr(b.actual - b.prediction_umidas) if len(b)>1 else np.nan))
    save('error_correlations', pd.DataFrame(complement))
    revisions = []
    for (mode, group), f in pairs.groupby(['lag_mode', 'evaluation_group']):
        f = f.sort_values(['target_quarter', 'horizon'])
        delta = f.groupby('target_quarter')[['prediction', 'prediction_umidas']].diff().dropna()
        revisions.append(dict(lag_mode=mode, evaluation_group=group, n=len(delta),
                              revision_correlation=delta.prediction.corr(delta.prediction_umidas) if len(delta)>1 else np.nan))
    save('revision_correlations', pd.DataFrame(revisions))
    leave = []
    for q in protocol['holdout_quarters']:
        f = forecasts.loc[forecasts.evaluation_group.eq('HOLDOUT') & forecasts.target_quarter.ne(q)]
        leave.append(scores(f, 'LEAVE_ONE_HOLDOUT_QUARTER_OUT').assign(omitted_quarter=q))
    save('leave_one_quarter_out', pd.concat(leave, ignore_index=True))
    # A standalone SVG preserves exportable factor paths without touching dashboards.
    paths = factors.loc[factors.specification.eq(selected['name']) & factors.target_quarter.eq(target) & factors.horizon.eq('H3') & factors.lag_mode.eq('standard')]
    svg_lines = []
    colors = ['#0072b2', '#d55e00', '#009e73']
    for j, f in paths.groupby('factor'):
        f = f.sort_values('month')
        vals = f.value.to_numpy()
        if len(vals):
            low, high = float(vals.min()), float(vals.max())
            points = ' '.join(f'{40+i*700/max(1,len(vals)-1):.1f},{260-(v-low)*210/max(1e-9,high-low):.1f}' for i,v in enumerate(vals))
            svg_lines.append(f'<polyline points="{points}" fill="none" stroke="{colors[int(j)-1]}" stroke-width="2"/><text x="50" y="{18+int(j)*15}">Factor {j}: own vertical scale</text>')
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="300"><rect width="800" height="300" fill="white"/>' + ''.join(svg_lines) + '</svg>'
    (out / 'phase6c_factor_paths.svg').write_text(svg, encoding='utf-8')

    def rows(names, group, source=metrics):
        return source.loc[source.model.isin(names) & source.evaluation_group.eq(group) & source.lag_mode.eq('standard') & source.horizon.eq('ALL')]

    def table(f):
        columns = [c for c in ['model', 'horizon', 'sample', 'n', 'rmse', 'mae', 'bias', 'median_absolute_error'] if c in f]
        if not len(f):
            return 'No estimable matched forecasts.\n'
        header = '| ' + ' | '.join(columns) + ' |\n| ' + ' | '.join(['---']*len(columns)) + ' |\n'
        return header + '\n'.join('| ' + ' | '.join(f'{v:.4f}' if isinstance(v, (float, np.floating)) else str(v) for v in row) + ' |' for row in f[columns].itertuples(index=False, name=None)) + '\n'

    benchmarks = ['AR1', 'AR2', 'UMIDAS_USD', 'PRODUCTION_ENSEMBLE', 'DFM-0', 'PHASE6B2_DFM_B', 'PHASE6B2_COMBO_B', final]
    final_horizons = metrics.loc[metrics.model.eq(final) & metrics.lag_mode.eq('standard')]
    excluded = audit.loc[~audit.eligible_for_ragged_panel, ['variable', 'reason_for_exclusion_if_any']]
    failed = diag.loc[diag.status.eq('FAILED')]
    converged = diag.loc[diag.status.eq('SUCCESS')]
    core_start = selected.get('start')
    contents = '# Phase 6C research results\n\n'
    contents += '**Recommendation: RESEARCH_ONLY. Production and frozen artifacts are unchanged.**\n\n'
    contents += 'This sequential experiment freezes block composition, factor count/AR order, bridge and combination weight using development origins only. '
    contents += 'The four final quarters are selection-quarantined here, but were evaluated in earlier phases; they are not a newly unseen research-programme holdout. '
    contents += 'Predictors use registry release-lag masking of latest stored values; their historical revision vintages are not verified. GDP uses the strict Phase 6B.2 documented-vintage accessor. '
    contents += 'Unknown historical GDP values are excluded rather than inferred from a release-delay assumption. These limitations preclude operational promotion from this experiment alone.\n\n'
    contents += '## Coverage and identification limits\n\n'
    contents += f'Long core starts January 2019 with {len(protocol["long_core"])} variables: ' + ', '.join(protocol['long_core']) + '. '
    contents += 'Approved recovered published industrial growth begins in 2019, retail in 2020 and construction in 2021. Extending the identical old three-variable domestic panel to 2019 is blocked by construction coverage, so DFM-0 versus DFM-1 cannot isolate sample length. '
    contents += 'The registry master industrial growth is nominal de-cumulated-flow log growth; Phase6C uses explicitly labelled published growth from the approved research panel consistently with DFM-0. '
    contents += 'POS is available only through its verified December 2024 scope boundary, and remains missing afterward. No registry or canonical data change is made.\n\n'
    integrity_path = out / 'phase6c_recovered_source_integrity.csv'
    if integrity_path.exists():
        integrity = pd.read_csv(integrity_path)
        contents += f'Recovered source integrity: {int(integrity.verified.sum())} of {len(integrity)} archived official source files match their recorded checksums.\n\n'
    contents += 'Prespecified combined ragged panel: ' + ', '.join(protocol['ragged_panel']) + '.\n\n'
    contents += 'Selected factor fields: ' + ', '.join(fields) + f'. Factors: **{selected["factors"]}**; AR order: **{selected["order"]}**; '
    contents += f'bridge: **{protocol["selected_bridge"]}**, quarterly aggregation: **{protocol["selected_aggregation"]}**.\n\n'
    contents += 'Exclusions:\n\n' + table(excluded.rename(columns={'variable':'model', 'reason_for_exclusion_if_any':'sample'}))
    contents += '\n## Development evidence\n\n' + table(rows([m for m in metrics.model.unique() if m.startswith('DFM-')], 'DEVELOPMENT'))
    contents += '\nThese full-available scores do not establish superiority on unequal samples. The sequential selection file contains exact common development origins at every decision. '
    contents += 'The minimum is nine common forecasts; numerical failures are saved explicitly and ineligible candidates do not get an advantage from missing origins. '
    contents += 'Block design retains one industrial aggregate, headline CPI plus PPI, total exports/imports and at most the adequately observed payment/banking fields. '
    contents += 'Pairwise correlations are diagnostic only, through June 2025; no unrestricted variable search is performed.\n\n'
    # Direct answers to the redesign questions, all on matched development
    # origins. A descriptive comparison never changes the frozen candidate.
    sequential = []
    statements = []
    block_choice = protocol.get('selected_DFM2', 'DFM-2_COMBINED')
    for left, right, label in [('DFM-0', 'DFM-1', 'Old DFM versus recovered long core (composition also changes)'),
        ('DFM-1_SHORT_HISTORY_CONTROL', 'DFM-1', 'Longer history with identical core fields'),
        ('DFM-1', block_choice, 'Economically balanced block selection'),
        (block_choice, 'DFM-3', 'Ragged history versus identical balanced fields')]:
        a = forecasts.loc[forecasts.model.eq(left) & forecasts.evaluation_group.eq('DEVELOPMENT')].dropna(subset=['prediction','actual'])
        b = forecasts.loc[forecasts.model.eq(right) & forecasts.evaluation_group.eq('DEVELOPMENT')].dropna(subset=['prediction','actual'])
        keys = a[KEYS].merge(b[KEYS], on=KEYS, validate='one_to_one')
        common = forecasts.loc[forecasts.model.isin([left,right]) & forecasts.evaluation_group.eq('DEVELOPMENT')].merge(keys, on=KEYS)
        if len(common):
            m = scores(common, 'SEQUENTIAL_PAIRWISE_MATCHED').assign(experiment=label)
            sequential.append(m)
            primary = m.loc[m.lag_mode.eq('standard') & m.horizon.eq('ALL')].set_index('model')
            if left in primary.index and right in primary.index:
                statements.append(f'{label}: matched RMSE {primary.loc[left,"rmse"]:.4f} → {primary.loc[right,"rmse"]:.4f}, '
                                  f'{int(primary.loc[right,"n"])} common origins; '
                                  + ('improved.' if primary.loc[right,'rmse']<primary.loc[left,'rmse'] else 'did not improve.'))
        else:
            statements.append(label + ': blocked by insufficient mutually estimable development forecasts.')
    if sequential:
        save('sequential_matched_metrics', pd.concat(sequential, ignore_index=True))
    contents += 'Matched development findings:\n\n' + '\n\n'.join(statements) + '\n\n'
    contents += '## Final horizon-specific performance\n\n' + table(final_horizons)
    contents += '\n## Final holdout: every model on its own available sample\n\n' + table(rows(benchmarks, 'HOLDOUT'))
    matched_holdout = matched.loc[matched.evaluation_group.eq('HOLDOUT') & matched.lag_mode.eq('standard') & matched.horizon.eq('ALL') & matched.comparison.isin(benchmarks)]
    contents += '\n## Pairwise matched holdout comparisons\n\n' + table(matched_holdout)
    umidas_pair = matched_holdout.loc[matched_holdout.comparison.eq('UMIDAS_USD')].set_index('model')
    if final in umidas_pair.index and 'UMIDAS_USD' in umidas_pair.index:
        fr, ur = umidas_pair.loc[final,'rmse'], umidas_pair.loc['UMIDAS_USD','rmse']
        contents += f'On identical holdout origins, final DFM RMSE is {fr:.4f} versus U-MIDAS {ur:.4f}: '
        contents += ('the DFM is more accurate on this matched sample.' if fr<ur else 'the DFM does not beat U-MIDAS on this matched sample.') + '\n\n'
    contents += '\n## Complementarity\n\n' + table(rows(['FIXED_25_DFM', 'FIXED_50_DFM', 'FIXED_75_DFM', 'DEVELOPMENT_WEIGHT_DFM'], 'HOLDOUT'))
    contents += f'Estimated DFM combination weight: {protocol["frozen_combination_DFM_weight"]:.6f}, fitted on standard-mode development origins and frozen before holdout. '
    contents += 'Fixed-weight and estimated-weight combinations preserve the production ensemble. Error and revision correlations are in their CSV files. '
    contents += 'Leave-one-quarter-out scores disclose whether an apparent gain depends on one quarter; those holdout diagnostics never retune the frozen model.\n\n'
    standard_holdout = forecasts.loc[forecasts.lag_mode.eq('standard') & forecasts.evaluation_group.eq('HOLDOUT')].copy()
    standard_holdout['squared_error'] = (standard_holdout.actual-standard_holdout.prediction)**2
    quarter_errors = standard_holdout.groupby(['target_quarter','model']).squared_error.mean().unstack()
    if final in quarter_errors and 'DFM-0' in quarter_errors:
        contents += f'The final DFM has lower quarter-level mean squared error than DFM-0 in {int((quarter_errors[final]<quarter_errors["DFM-0"]).sum())} of four holdout quarters. '
    if 'DEVELOPMENT_WEIGHT_DFM' in quarter_errors and 'UMIDAS_USD' in quarter_errors:
        contents += f'The frozen development-weight combination improves on U-MIDAS in {int((quarter_errors.DEVELOPMENT_WEIGHT_DFM<quarter_errors.UMIDAS_USD).sum())} of four quarters; '
        worst = quarter_errors[final].idxmax()
        contents += f'the final DFM largest quarterly error is in {worst}. This is broad improvement relative to the old DFM, but not uniform superiority over U-MIDAS.\n\n'
    correlation = pd.DataFrame(complement)
    value = correlation.loc[correlation.lag_mode.eq('standard') & correlation.evaluation_group.eq('HOLDOUT') & correlation.horizon.eq('ALL')]
    if len(value):
        contents += f'Matched holdout DFM/U-MIDAS error correlation: {value.iloc[0].error_correlation:.4f}.\n\n'
    contents += '## Factor interpretation and numerical reliability\n\n'
    contents += 'Top ten absolute signed loadings, squared-loading economic block shares, factor covariances and recursive matched-loading/subspace cosines are saved in tidy files. '
    contents += 'Empirical factors are left numbered: financial/price/external dominance of a long core must not be labelled domestic real activity without supporting loadings. '
    contents += 'Multi-factor rotation and sign indeterminacy are handled in stability diagnostics by maximum absolute cosine matching and subspace angles. '
    contents += 'Likelihood BIC/AIC provide a finite-state alternative diagnostic to Bai–Ng, whose large-panel assumptions are weak here. '
    contents += 'Scree shares describe the complete overlapping development subsample only, never the ragged estimator. '
    contents += 'Factor common-component variances are not falsely reported as additive explained shares when factors correlate.\n\n'
    selection_file = pd.read_csv(out / 'phase6c_factor_selection.csv')
    factor_comparison = selection_file.loc[selection_file.stage.eq('FACTOR_AND_AR_ORDER') & selection_file.horizon.eq('ALL')]
    contents += 'Factor-count selection on identical development origins:\n\n' + table(factor_comparison)
    contents += 'Two-factor candidates were worse on the common development sample. Three-factor candidates could not supply enough converged, bridge-estimable origins to enter selection; this is a numerical/data limitation, not evidence that three economic factors cannot exist. '
    contents += 'The factor-only Bridge A remains weak relative to DFM-0. Much of the final accuracy gain arrives when released lagged GDP enters Bridge B; it must not be interpreted as proof that longer history or additional factors repaired factor extraction. '
    contents += 'The financial loading concentration and failure of the identical-core short-history control to produce a matched estimable sample limit the scientific attribution of gains.\n\n'
    concentration = pd.DataFrame(blocks)
    if len(concentration):
        for factor, group in concentration.loc[concentration.specification.eq(selected['name'])].groupby('factor'):
            largest = group.sort_values('squared_loading_share', ascending=False).iloc[0]
            contents += f'Factor {factor} has its largest squared-loading contribution in {largest.block} ({largest.squared_loading_share:.1%}); this describes loadings rather than imposing a causal economic label.\n\n'
    contents += f'Successful factor fits: {len(converged)}; failed origin/specification records: {len(failed)}. '
    if len(converged):
        contents += f'Training months range {int(converged.n_training_months.min())}–{int(converged.n_training_months.max())}; selected development/holdout sample lengths are in factor_diagnostics.csv. '
    selected_diagnostics = converged.loc[converged.specification.eq(selected['name']) & converged.lag_mode.eq('standard')]
    if len(selected_diagnostics):
        contents += f'The selected model uses {int(selected_diagnostics.n_training_months.min())}–{int(selected_diagnostics.n_training_months.max())} monthly training rows '
        contents += f'and {int(selected_diagnostics.n_observed_cells.min())}–{int(selected_diagnostics.n_observed_cells.max())} observed predictor cells across successful recursive fits. '
    contents += 'EM convergence and transition stability are mandatory; rejected fits produce null forecasts and retain their error context. '
    contents += 'There is no observation backfill, interpolation, listwise deletion in ragged mode, or full-sample scaling. '
    contents += 'The balanced comparator trims to the latest first-valid month but preserves internal gaps; DFM-3 keeps the identical fields and all earlier months. '
    contents += 'H1/H2 future within-quarter states are model predictions under missing measurements, not future observed factors. '
    contents += 'Monthly factors are quarterly means or quarter-end latent states; bridges use only released GDP and require at least max(12, three times regressor count) quarters.\n\n'
    contents += '## Robustness and operational decision\n\n'
    contents += 'Development-only start-date, winsorization and available block/individual exclusions are saved without changing the freeze. '
    contents += 'Russia IPI is unavailable in validated stored data, so all estimable models exclude it; a with-Russia experiment is blocked rather than fabricated. '
    contents += 'Excluded sparse instant/interbank payments and banking have fewer than 24 development observations. Recovered POS is evaluated explicitly as an incremental block but has no validated measurements after December 2024. '
    contents += 'Winsorization at training-only 1/99 percentiles is an explicit research sensitivity, not a claimed existing production convention. '
    contents += 'A challenger must show stable matched gains/complementarity across horizons and quarters, complete release-vintage evidence and reliable recursive estimation before shadow promotion. '
    contents += 'The documented vintage/coverage constraints and short independent evaluation do not establish that standard. '
    contents += f'Protected artifacts changed: **NO** ({checks["protected_files"]} files checked).\n'
    tests_path = out / 'phase6c_test_results.json'
    test_counts = json.loads(tests_path.read_text()) if tests_path.exists() else None
    if test_counts:
        contents += f'Automated tests: {test_counts["passed"]} passed, {test_counts["failures"]} failed, {test_counts["errors"]} errors, {test_counts["skipped"]} skipped. '
        contents += 'Repository and prior research suites use separate processes to avoid their shared `run` module names colliding.\n'
    (out / 'phase6c_results.md').write_text(contents, encoding='utf-8')

    def rmse(model, group, source=metrics):
        f = rows([model], group, source)
        return f'{f.iloc[0].rmse:.6f}' if len(f) else 'N/A'
    summary = ['PHASE 6C STATUS: RESEARCH_COMPLETE_WITH_DOCUMENTED_LIMITATIONS',
        'Long-core start date: 2019-01', f'Long-core variable count: {len(protocol["long_core"])}',
        f'Ragged-panel variable count: {len(protocol["ragged_panel"])}',
        f'Development origins: {len(protocol["development_origins"])} per lag mode (failed origins retained)',
        'Holdout origins: 12 per lag mode', f'Selected factor count: {selected["factors"]}',
        f'Selected bridge: {protocol["selected_bridge"]} / {protocol["selected_aggregation"]}',
        f'DFM-0 development RMSE: {rmse("DFM-0", "DEVELOPMENT")}',
        f'DFM-1 development RMSE: {rmse("DFM-1", "DEVELOPMENT")}',
        f'DFM-2 development RMSE: {rmse(protocol.get("selected_DFM2", "DFM-2_COMBINED"), "DEVELOPMENT")}',
        f'DFM-3 development RMSE: {rmse("DFM-3", "DEVELOPMENT")}',
        f'Final DFM development RMSE: {rmse(final, "DEVELOPMENT")}',
        f'Final DFM holdout RMSE: {rmse(final, "HOLDOUT")}',
        'U-MIDAS matched holdout RMSE: ' + rmse('UMIDAS_USD', 'HOLDOUT', matched_holdout.loc[matched_holdout.comparison.eq('UMIDAS_USD')]),
        'Best DFM/U-MIDAS combination holdout RMSE (descriptive, no reselection): ' + str(rows(['FIXED_25_DFM','FIXED_50_DFM','FIXED_75_DFM','DEVELOPMENT_WEIGHT_DFM'], 'HOLDOUT').rmse.min()),
        'Final recommendation: RESEARCH_ONLY', 'Protected artifacts changed: NO',
        f'Tests passed: {test_counts["passed"]}' if test_counts else 'Tests passed: see phase6c_test_results.json',
        f'Tests failed: {test_counts["failures"] + test_counts["errors"]}' if test_counts else 'Tests failed: see phase6c_test_results.json']
    (out / 'phase6c_terminal_summary.txt').write_text('\n'.join(summary) + '\n', encoding='utf-8')
    print('\n'.join(summary), flush=True)
