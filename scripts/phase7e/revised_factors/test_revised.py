"""Scientific boundary, exclusion and matched-output checks without downloads."""
from dataclasses import replace
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd
import pytest

from scripts.phase7d.data import read_workbook, release_gate
from scripts.phase7d.run import information_gdp
from scripts.phase7d.evaluation import KEYS
from scripts.phase7e.grouping import inventory, core_columns
from scripts.phase7e.models import estimate, SPECS
from scripts.phase7e.revised_factors.configuration import RevisedFactors, EXCLUSIONS
from scripts.phase7e.revised_factors.run import comparisons
from scripts.phase7e.protection import verify

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'results/phase7e/revised_factors'


@pytest.fixture(scope='module')
def environment():
    digest = json.loads((ROOT/'results/phase7d/phase7d_run_manifest.json').read_text())['workbook_sha256']
    inputs = read_workbook(ROOT/'results/phase7d/input'/f'{digest}.xlsx', ROOT/'data/master/gdp_quarterly.parquet')
    return inputs, inventory(inputs,'2026-10-05'), pd.read_csv(ROOT/'data/current/gdp_vintages.csv')


@pytest.fixture(scope='module')
def current(environment):
    inputs, grouping, events = environment
    _, gdp = information_gdp(events, '2026Q3', '2026-10-05')
    cache = {}
    return {m: estimate(inputs, grouping, m, '2026Q3', 'H3', '2026-10-05', gdp, events,
                        cache, configuration=RevisedFactors()) for m in SPECS}


def test_exact_exclusions_preserve_inventory_and_assignments(environment):
    inputs, grouping, _ = environment
    config = RevisedFactors(); revised = config.inventory(inputs, grouping)
    assert len(revised) == 96 and len(inputs.monthly.columns) == 91
    assert revised.loc[revised.frequency.eq('M') & ~revised.revised_factor_included, 'original_label'].tolist() == list(EXCLUSIONS)
    pd.testing.assert_series_equal(revised.economic_group, grouping.economic_group)
    assert revised.loc[revised.revised_factor_included].economic_group.value_counts().to_dict() == dict(F1=28,F2=14,F3=5,F4=5,F5=36)
    assert revised.revised_core_selected.sum() == 15
    for b in SPECS['E2']:
        original = core_columns(inputs.monthly)[b]
        assert config.columns(inputs.monthly, grouping, b, True) == [c for c in original if c not in EXCLUSIONS]
    with pytest.raises(ValueError, match='labels missing'):
        config.inventory(replace(inputs, monthly=inputs.monthly.drop(columns=list(EXCLUSIONS))), grouping)


@pytest.mark.parametrize('model', list(SPECS))
def test_all_specifications_exclude_exact_labels(model, current):
    r = current[model]
    assert not set(r.loadings.original_label).intersection(EXCLUSIONS)
    assert len(r.loadings) == (52 if model == 'E1' else 15 if model == 'ECONOMIC_CORE' else 88)
    assert r.bridge['quarterly_declared'] == (5 if model == 'E4' else 0)
    assert abs(r.contributions.value.sum()-r.prediction) < 1e-10
    assert r.diagnostics.pca_converged.all() and r.diagnostics.objective_monotone.all()
    assert r.diagnostics.spectral_radius.lt(.98).all()
    assert r.factors.loc[:'2023-12-31', 'F2' if model != 'E3' else 'F2_RESIDUAL'].isna().all()


@pytest.mark.parametrize('model', list(SPECS))
def test_removed_values_have_no_effect(model, environment, current):
    inputs, grouping, events = environment
    monthly = inputs.monthly.copy(); monthly.loc[:, list(EXCLUSIONS)] = 1e12
    _, gdp = information_gdp(events, '2026Q3', '2026-10-05')
    r = estimate(replace(inputs, monthly=monthly), grouping, model, '2026Q3','H3','2026-10-05',
                 gdp, events, configuration=RevisedFactors())
    assert r.prediction == pytest.approx(current[model].prediction, abs=1e-12)
    pd.testing.assert_frame_equal(r.loadings, current[model].loadings)


@pytest.mark.parametrize('model', list(SPECS))
def test_unavailable_predictors_and_gdp_cannot_leak(model, environment):
    inputs, grouping, events = environment
    target='2025Q2';origin='2025-04-30'
    _, gdp = information_gdp(events, target, origin)
    a = estimate(inputs, grouping, model, target, 'H1', origin, gdp, events, configuration=RevisedFactors())
    monthly=inputs.monthly.copy();quarterly=inputs.quarterly.copy()
    for f in [monthly, quarterly]:
        visible = release_gate(f, inputs.inventory, origin)
        f.mask(f.notna() & visible.isna(), 1e10, inplace=True)
    quarterly.loc[target:] = 1e10
    changed_events = events.copy()
    changed_events.loc[pd.to_datetime(changed_events.publication_date)>pd.Timestamp(origin), 'value'] = 1e10
    _, changed_gdp = information_gdp(changed_events,target,origin)
    b = estimate(replace(inputs,monthly=monthly,quarterly=quarterly),grouping,model,target,'H1',origin,
                 changed_gdp,changed_events,configuration=RevisedFactors())
    assert a.prediction == pytest.approx(b.prediction, abs=1e-12)
    pd.testing.assert_frame_equal(a.factors,b.factors)
    pd.testing.assert_frame_equal(a.loadings,b.loadings)


def test_cache_separates_original_and_revised(environment, current):
    inputs, grouping, events=environment
    _, gdp=information_gdp(events,'2026Q3','2026-10-05');cache={}
    old=estimate(inputs,grouping,'E2','2026Q3','H3','2026-10-05',gdp,events,cache)
    new=estimate(inputs,grouping,'E2','2026Q3','H3','2026-10-05',gdp,events,cache,configuration=RevisedFactors())
    assert len(old.loadings)==91 and len(new.loadings)==88
    assert new.prediction==current['E2'].prediction
    assert len(cache)==10


@pytest.mark.parametrize('model',['E2','ECONOMIC_CORE'])
def test_orientation_does_not_change_predictions_or_attribution(model, environment, current, monkeypatch):
    from scripts.phase7e import models
    original_orient=models.orient
    def flip(f,l,anchor):
        f,l=original_orient(f,l,anchor)
        return -f,-l
    monkeypatch.setattr(models,'orient',flip)
    inputs,grouping,events=environment
    _,gdp=information_gdp(events,'2026Q3','2026-10-05')
    r=estimate(inputs,grouping,model,'2026Q3','H3','2026-10-05',gdp,events,configuration=RevisedFactors())
    assert r.prediction==pytest.approx(current[model].prediction,abs=1e-10)
    np.testing.assert_allclose(r.contributions.value,current[model].contributions.value,atol=1e-10,rtol=0)


def test_matching_requires_identical_actuals_and_unique_origins():
    rows=[dict(model=m,origin=str(i),target_quarter=f'2025Q{i}',horizon='H1',evaluation_group='HOLDOUT',
               actual=float(i),prediction=float(i)+e) for i in range(1,4) for m,e in [*( (m,1.) for m in SPECS),('AR1',2.),('COMBO_50_50',1.5)]]
    old=pd.DataFrame(rows);new=old.loc[old.model.isin(SPECS)].copy()
    new.loc[(new.model=='E2') & (new.origin=='1'),'prediction']=np.nan
    score,selected,keys=comparisons(old,new)
    assert len(keys)==2
    assert score.query("sample == 'MATCHED_ALL' and horizon == 'ALL'").revised_n_forecasts.eq(2).all()
    bad=new.copy();bad.loc[bad.index[0],'actual']=1e9
    with pytest.raises(ValueError,match='Different actual'):
        comparisons(old,bad)
    with pytest.raises(ValueError,match='Duplicate'):
        comparisons(old,pd.concat([new,new.iloc[:1]]))


def test_generated_evidence_matches_results(current):
    f=pd.read_csv(OUT/'revised_phase7e_forecasts.csv',float_precision='round_trip')
    assert not f.duplicated(['model',*KEYS]).any()
    old=pd.read_csv(ROOT/'results/phase7e/phase7e_forecasts.csv',float_precision='round_trip')
    score,_,keys=comparisons(old,f)
    published=pd.read_csv(OUT/'revised_phase7e_comparison.csv',float_precision='round_trip')
    pd.testing.assert_frame_equal(score,published,check_dtype=False)
    assert len(keys)==18
    for m,r in current.items():
        assert f.loc[f.model.eq(m)&f.evaluation_group.eq('CURRENT'),'prediction'].iloc[0]==pytest.approx(r.prediction,abs=1e-12)
    contrib=pd.read_csv(OUT/'revised_phase7e_gdp_contributions.csv',float_precision='round_trip')
    assert contrib.groupby(['model',*KEYS]).apply(lambda x:abs(x.value.sum()-x.prediction.iloc[0]),include_groups=False).max()<1e-10
    loadings=pd.read_csv(OUT/'revised_phase7e_factor_loadings.csv')
    assert not set(loadings.original_label).intersection(EXCLUSIONS)
    baseline=json.loads((OUT/'revised_phase7e_protection_baseline.json').read_text())
    assert verify(baseline)>0
    manifest=json.loads((OUT/'revised_phase7e_run_manifest.json').read_text())
    assert manifest['original_successes_reproduced']==95
    assert manifest['production_forecast']==8.180901340616275 and not manifest['promotion_allowed']


def test_dashboard_offline_payload_and_distinct_versions():
    text=(OUT/'revised_phase7e_dashboard.html').read_text(encoding='utf8')
    d=json.loads(re.search(r'<script id="revised-phase7e-data" type="application/json">(.*?)</script>',text,re.S).group(1))
    assert set(d['models'])==set(SPECS)
    assert set(r['specification'] for r in d['forecasts'])=={'ORIGINAL','REVISED'}
    assert len(d['matched_origins'])==18
    assert len(d['compositions'])==96
    assert not re.search(r'\b(fetch\(|XMLHttpRequest|WebSocket\()',text)
    assert '<script src=' not in text and '<link ' not in text
