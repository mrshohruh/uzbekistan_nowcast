"""Refit revised Phase 7E factors at the exact archived research origins."""
from pathlib import Path
import json
import logging
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from scripts.phase7d.data import read_workbook, INFORMATION_CLASS
from scripts.phase7d.run import information_gdp
from scripts.phase7d.evaluation import KEYS, tables, metrics, matched
from scripts.phase7e.grouping import inventory
from scripts.phase7e.models import estimate, SPECS
from scripts.phase7e.protection import verify, sha
from scripts.phase7e.revised_factors.configuration import RevisedFactors, EXCLUSIONS
from scripts.operations.prospective.common import safe

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL = ROOT / 'results/phase7e'
OUT = ORIGINAL / 'revised_factors'
LOG = logging.getLogger('phase7e.revised_factors')


def save(name, frame):
    frame.to_csv(OUT / f'revised_phase7e_{name}.csv', index=False, float_format='%.17g')


def write_json(name, value):
    (OUT / f'revised_phase7e_{name}.json').write_text(
        json.dumps(safe(value), indent=2, allow_nan=False) + '\n', encoding='utf8')


def protected_snapshot():
    """Protect inputs, production, dashboards, code and original research files.

    Unused raw collections and historical pytest copies are never read or
    written by this offline experiment and need not be hashed on every run.
    """
    baseline = {}
    for folder in ['src','scripts','config','registry','data/master','data/current','metadata','dashboard',
                   'results/current','results/production','results/phase7d','results/phase7e','results/phase7f']:
        for directory, dirs, files in os.walk(ROOT/folder):
            dirs[:] = [d for d in dirs if d not in ['revised_factors','__pycache__'] and not d.startswith(('tmp','pytest_tmp','.'))]
            for name in files:
                p = Path(directory)/name
                if p.suffix != '.pyc':
                    baseline[p.relative_to(ROOT).as_posix()] = sha(p)
    for name in ['AGENTS.md','README.md','PROJECT_SPEC.md','requirements.txt','requirements-models.txt','pyproject.toml','.gitignore']:
        baseline[name] = sha(ROOT/name)
    return baseline


def comparisons(original, revised):
    """Keep the original multi-model common sample, then intersect revised fits."""
    old = original.loc[original.evaluation_group.ne('CURRENT')].copy()
    models = list(original.model.unique())
    old_common = matched(old, models)
    new = revised.loc[revised.evaluation_group.ne('CURRENT')].copy()
    old['specification'] = 'ORIGINAL'
    new['specification'] = 'REVISED'
    pooled = pd.concat([old, new], ignore_index=True)
    pooled['base_model'] = pooled.model
    pooled['model'] = pooled.specification + ':' + pooled.model
    complete = matched(pooled, ['ORIGINAL:' + m for m in models] + ['REVISED:' + m for m in SPECS])
    keys = old_common[KEYS].drop_duplicates().merge(complete[KEYS].drop_duplicates(), on=KEYS)
    selected = pooled.merge(keys, on=KEYS, validate='many_to_one')
    benchmark = old.loc[old.model.isin(['AR1', 'COMBO_50_50'])]
    rows = []
    for sample, condition in [('MATCHED_ALL', lambda q: q.notna()),
            ('MATCHED_DEVELOPMENT', lambda q: q < '2025Q3'),
            ('MATCHED_HOLDOUT', lambda q: q >= '2025Q3')]:
        part = selected.loc[condition(selected.target_quarter)]
        for h in ['ALL', 'H1', 'H2', 'H3']:
            subset = part if h == 'ALL' else part.loc[part.horizon.eq(h)]
            for model in SPECS:
                row = dict(sample=sample, horizon=h, model=model)
                for version in ['ORIGINAL', 'REVISED']:
                    f = subset.loc[subset.model.eq(version + ':' + model)]
                    score = metrics(f, benchmark)
                    # Additional OOS R² against the unchanged existing combo.
                    b = f.merge(benchmark.loc[benchmark.model.eq('COMBO_50_50'), KEYS + ['prediction']],
                                on=KEYS, suffixes=('', '_benchmark'), validate='one_to_one')
                    denominator = ((b.actual - b.prediction_benchmark)**2).sum()
                    score['r2_os_combo_50_50'] = 1 - ((b.actual-b.prediction)**2).sum()/denominator if len(b) == len(f) and len(b) and denominator > 1e-12 else np.nan
                    row.update({version.lower() + '_' + k: v for k, v in score.items()})
                row['rmse_change_pp'] = row['revised_rmse'] - row['original_rmse']
                row['rmse_improvement_pct'] = 100 * (1-row['revised_rmse']/row['original_rmse']) if row['original_rmse'] > 0 else np.nan
                row['performance'] = 'IMPROVED' if row['rmse_change_pp'] < -1e-12 else 'WORSENED' if row['rmse_change_pp'] > 1e-12 else 'UNCHANGED'
                rows.append(row)
    return pd.DataFrame(rows), selected, keys


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler(OUT/'pipeline.log', mode='w', encoding='utf8')])
    before = protected_snapshot()
    write_json('protection_baseline', before)
    manifest = json.loads((ROOT/'results/phase7d/phase7d_run_manifest.json').read_text())
    digest = manifest['workbook_sha256']
    workbook = ROOT/'results/phase7d/input'/f'{digest}.xlsx'
    if sha(workbook) != digest:
        raise ValueError('Archived workbook hash differs')
    inputs = read_workbook(workbook, ROOT/'data/master/gdp_quarterly.parquet')
    production = json.loads((ROOT/'results/current/current_nowcast.json').read_text())
    if production['final_forecast'] != 8.180901340616275:
        raise ValueError('Production nowcast differs from frozen requirement')
    original = pd.read_csv(ORIGINAL/'phase7e_forecasts.csv', float_precision='round_trip')
    original['origin'] = pd.to_datetime(original.origin).dt.strftime('%Y-%m-%d')
    original_specs = original.loc[original.model.isin(SPECS)]
    if original_specs.duplicated(KEYS + ['model']).any():
        raise ValueError('Duplicate archived model origins')
    cutoff = json.loads((ORIGINAL/'phase7e_current_nowcast.json').read_text())['cutoff']
    grouping = inventory(inputs, cutoff)
    configuration = RevisedFactors()
    revised_inventory = configuration.inventory(inputs, grouping)
    save('factor_compositions', revised_inventory)
    write_json('configuration', dict(exclusions=EXCLUSIONS, full_monthly_count=88, core_monthly_count=15,
        unchanged_factor_numbers=list(SPECS['E2']), f5_positive_sign_anchor='Retained M2 — Broad money in both full and core',
        anchor_effect='Orientation only; sign-invariant ridge predictions. No new indicator.',
        settings='All original transformations, thresholds, penalties, weighting formula, dynamics, bridge, origins and windows unchanged.',
        predictor_release_date_policy='Existing assumed-lag research gate; observed predictor releases and historical vintages unavailable.',
        authentic_real_time_validated=False, production_promotion_allowed=False))
    events = pd.read_csv(ROOT/'data/current/gdp_vintages.csv')
    records = []; loadings = []; contributions = []; diagnostics = []; availability = []
    paths = []; bridges = []; reproductions = []
    origins = original_specs[KEYS + ['evaluation_group', 'actual', 'actual_definition', 'information_class']].drop_duplicates(KEYS)
    for row in origins.itertuples(index=False):
        meta = row._asdict()
        target, horizon, origin = row.target_quarter, row.horizon, row.origin
        LOG.info('Refitting %s %s at %s', target, horizon, origin)
        _, gdp = information_gdp(events, target, origin)
        # Cache lifetime is one origin; configuration token separates fits.
        cache = {}
        for model in SPECS:
            archived = original_specs.loc[original_specs.model.eq(model) & original_specs.origin.eq(origin) &
                original_specs.target_quarter.eq(target) & original_specs.horizon.eq(horizon)].iloc[0]
            if np.isfinite(archived.prediction):
                old = estimate(inputs, grouping, model, target, horizon, origin, gdp, events, cache)
                delta = old.prediction - archived.prediction
                if abs(delta) > 1e-10:
                    raise ValueError(f'Original archive reproduction failed: {model} {origin}: {delta}')
                reproductions.append(dict(meta, model=model, archived_prediction=archived.prediction,
                    recomputed_prediction=old.prediction, difference=delta))
            try:
                r = estimate(inputs, grouping, model, target, horizon, origin, gdp, events, cache, configuration=configuration)
                records.append(dict(meta, model=model, specification='REVISED', prediction=r.prediction, failure=None,
                    n_monthly_declared=len(r.loadings), n_gdp_training=r.bridge['n_gdp_training']))
                for name, frame, collector in [('loadings',r.loadings,loadings),
                        ('contributions',r.contributions,contributions), ('diagnostics',r.diagnostics,diagnostics),
                        ('availability',r.availability,availability)]:
                    collector.extend(frame.assign(**meta, model=model, specification='REVISED', prediction=r.prediction).to_dict('records'))
                bridges.append(dict(meta, model=model, **r.bridge))
                if row.evaluation_group == 'CURRENT':
                    paths.extend(r.factors.rename_axis('date').reset_index().melt(id_vars='date', var_name='factor', value_name='value')
                        .assign(model=model, specification='REVISED').to_dict('records'))
            except (ValueError, np.linalg.LinAlgError) as exc:
                LOG.warning('%s %s %s failed: %s', model, target, horizon, exc)
                records.append(dict(meta, model=model, specification='REVISED', prediction=np.nan, failure=str(exc)))
        save('forecasts', pd.DataFrame(records))
    revised = pd.DataFrame(records)
    score, selected, keys = comparisons(original, revised)
    save('comparison', score)
    save('matched_forecasts', selected)
    save('matched_origins', keys)
    for name, rows in [('factor_loadings', loadings), ('gdp_contributions', contributions),
            ('estimation_diagnostics', diagnostics), ('origin_availability', availability),
            ('current_factor_paths', paths), ('bridge_diagnostics', bridges), ('original_reproduction', reproductions)]:
        save(name, pd.DataFrame(rows))
    save('failures', revised.loc[revised.prediction.isna()])
    old_now = original_specs.loc[original_specs.evaluation_group.eq('CURRENT')]
    new_now = revised.loc[revised.evaluation_group.eq('CURRENT')]
    current = old_now[['model','prediction']].rename(columns={'prediction':'original_prediction'}).merge(
        new_now[['model','prediction','failure','n_monthly_declared']].rename(columns={'prediction':'revised_prediction'}),
        on='model', validate='one_to_one')
    current['nowcast_change_pp'] = current.revised_prediction - current.original_prediction
    save('current_nowcasts', current)
    errors = pd.DataFrame(contributions).groupby(['model', *KEYS]).apply(
        lambda f: abs(f.value.sum()-f.prediction.iloc[0]), include_groups=False)
    write_json('run_manifest', dict(workbook_sha256=digest, cutoff=cutoff, target_quarter='2026Q3',
        information_class=INFORMATION_CLASS, authentic_real_time_validated=False,
        production_model='COMBO_50_50', production_forecast=production['final_forecast'], promotion_allowed=False,
        origin_count=len(origins), matched_origin_count=len(keys), original_successes_reproduced=len(reproductions),
        original_reproduction_max_error=max(abs(r['difference']) for r in reproductions),
        max_decomposition_error=errors.max(), failed_revised_forecasts=int(revised.prediction.isna().sum()),
        current_failures=int(new_now.prediction.isna().sum()),
        code_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'scripts/phase7e/models.py', *Path(__file__).parent.glob('*.py')]},
        run_timestamp_utc=datetime.now(timezone.utc).isoformat()))
    from scripts.phase7e.revised_factors.report import render
    render()
    count = verify(before)
    write_json('validation', dict(protected_artifacts_verified=True, protected_file_count=count,
        original_outputs_preserved=True, production_preserved=True,
        authentic_real_time_validated=False, tests_status='PENDING', browser_status='PENDING',
        decomposition_max_error=errors.max()))
    LOG.info('Completed; protected %d files, %d common origins', count, len(keys))


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    run()
