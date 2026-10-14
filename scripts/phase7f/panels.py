"""Read-only model inputs, origin normalization and audited balancing policies."""
from dataclasses import dataclass
import json
import numpy as np
import pandas as pd
from scripts.phase7d.data import read_workbook,release_gate
from scripts.phase7d.models import standardize as research_standardize
from scripts.phase7e.grouping import inventory,core_columns,family,BLOCKS
from scripts.phase7f.protection import ROOT,sha
from scripts.production.models import FIELDS,sw
from uznowcast.models.data import load_dataset

MAIN=['PRODUCTION_DFM','E1','E2','E3','E4','ECONOMIC_CORE']
MIN_MONTHS=12


@dataclass
class Panel:
    name:str
    values:pd.DataFrame
    z:pd.DataFrame
    weights:pd.Series
    current_factors:int
    meaning:str
    variables:pd.DataFrame
    quarterly_covariates:int=0
    generated:bool=False


def build_panels():
    frozen=json.loads((ROOT/'results/current/current_nowcast.json').read_text())
    manifest=json.loads((ROOT/'results/phase7e/phase7e_run_manifest.json').read_text())
    current=json.loads((ROOT/'results/phase7e/phase7e_current_nowcast.json').read_text())
    if frozen['final_forecast']!=8.180901340616275 or current['cutoff']!=frozen['as_of_date']:
        raise ValueError('Corresponding model cutoff/production forecast changed')
    target=frozen['target_quarter'];cutoff=frozen['as_of_date']
    end=(pd.Period(target,'Q')-1).end_time.normalize()
    archive=ROOT/'results/phase7d/input'/f"{manifest['workbook_sha256']}.xlsx"
    if sha(archive)!=manifest['workbook_sha256']:raise ValueError('Changed research input workbook')
    inputs=read_workbook(archive,ROOT/'data/master/gdp_quarterly.parquet')
    grouping=inventory(inputs,cutoff)
    m=release_gate(inputs.monthly,inputs.inventory,cutoff)
    m.index=m.index.to_timestamp('M');m=m.loc[:end]
    z,means,scales,estimable=research_standardize(m,end,minimum=12)
    if not estimable.all():raise ValueError('Current Phase 7E indicators unexpectedly unidentifiable')
    weights={}
    for b,part in grouping.loc[grouping.frequency.eq('M')].groupby('economic_group'):
        names=part.original_label.tolist();labels=pd.Series([family(c,b) for c in names],index=names)
        counts=labels.value_counts()
        weights.update({c:np.sqrt(len(names)/(len(counts)*counts[labels[c]])) for c in names})
    bundle=json.loads((ROOT/'config/model_definitions.json').read_text())['challengers']['PHASE6C_DFM']
    spec_config=bundle['factor_specification']
    if tuple(spec_config['fields'])!=FIELDS or spec_config['factors']!=1:raise ValueError('Production definition changed')
    k=sw.common.kernel();dataset=load_dataset(ROOT)
    raw=pd.read_csv(ROOT/'data/current/historical_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip')
    spec=k.Spec('DFM-4_R1_P2',FIELDS,1,2,'2019-01-31',True,False)
    prod,_=k.mask(raw,spec,target,frozen['horizon'],dataset.release_lag_days,'standard')
    prod,_=k.training_panel(prod,end,True)
    pz,pm,ps=k.standardize(prod,end,False)
    prod=prod.loc[:end];pz=pz.loc[:end]
    if len(prod)!=json.loads((ROOT/'results/current/dfm_structure.json').read_text())['diagnostics']['n_training_months']:
        raise ValueError('Production training sample differs from frozen fit')
    pv=pd.DataFrame([dict(original_variable=c,frequency='M',transformation=bundle['transformations'][c]['transformation'],
        transformation_basis=bundle['transformations'][c]['metadata_basis'],origin_mean=pm[c],origin_scale=ps[c],
        economic_group='PRODUCTION',publication_lag_days=dataset.release_lag_days[c]) for c in FIELDS])
    panels={'PRODUCTION_DFM':Panel('PRODUCTION_DFM',prod,pz,pd.Series(1.,index=prod.columns),1,
        'Eight-predictor EM-MLE dynamic factor, AR(2); formal tests use observed static span, not likelihood.',pv)}
    specs={'E1':['F1','F2','F3','F4'],'E2':list(BLOCKS),'E3':list(BLOCKS),'E4':list(BLOCKS),'ECONOMIC_CORE':list(BLOCKS)}
    core=core_columns(m)
    variables=grouping.rename(columns={'original_label':'original_variable'}).copy()
    variables['origin_mean']=variables.original_variable.map(means)
    variables['origin_scale']=variables.original_variable.map(scales)
    for name,blocks in specs.items():
        names=[c for b in blocks for c in core[b]] if name=='ECONOMIC_CORE' else grouping.loc[grouping.economic_group.isin(blocks),'original_label'].tolist()
        w=pd.Series(weights).reindex(names)
        if name=='ECONOMIC_CORE':
            own={}
            for b,cs in core.items():
                labels=pd.Series([family(c,b) for c in cs],index=cs);counts=labels.value_counts()
                own.update({c:np.sqrt(len(cs)/(len(counts)*counts[labels[c]])) for c in cs})
            w=pd.Series(own).reindex(names)
        panels[name]=Panel(name,m[names],z[names],w,len(blocks),
            'Unrestricted pooled monthly static-span diagnostic; current model imposes one factor per separate economic block.'+
            (' E3 also has a one-global/four-residual two-stage bridge.' if name=='E3' else ''),
            variables.loc[variables.original_variable.isin(names)].copy(),5 if name=='E4' else 0)
    for b in BLOCKS:
        for prefix,columns in [('GROUP_',grouping.loc[grouping.economic_group.eq(b),'original_label'].tolist()),('CORE_',core[b])]:
            name=prefix+b
            parent=panels['ECONOMIC_CORE'] if prefix=='CORE_' else panels['E2']
            panels[name]=Panel(name,m[columns],z[columns],parent.weights.reindex(columns),1,
                'One imposed block factor; unregularized static PCA diagnostic of its observed indicators.',
                variables.loc[variables.original_variable.isin(columns)].copy())
    saved=pd.read_csv(ROOT/'results/phase7e/phase7e_factor_timeseries.csv',float_precision='round_trip')
    saved=saved.loc[saved.evaluation_group.eq('CURRENT')]
    for name,base_model,factors in [('E3_STAGE2','E2',list(BLOCKS)),('E3_BRIDGE','E3',['GLOBAL','F1_RESIDUAL','F2_RESIDUAL','F3_RESIDUAL','F4_RESIDUAL'])]:
        path=saved.loc[saved.model.eq(base_model)].pivot(index='date',columns='factor',values='value').reindex(columns=factors)
        path.index=pd.to_datetime(path.index);path=path.loc[:end]
        variables_latent=pd.DataFrame([dict(original_variable=c,frequency='M',transformation='EXISTING_ONE_SIDED_LATENT_SIGNAL',
            origin_mean=0.,origin_scale=1.,economic_group='HIERARCHICAL_SIGNAL',source_uncertainty='Generated regressors; not independent observed series') for c in path])
        panels[name]=Panel(name,path,path,pd.Series(1.,index=path.columns),1 if name=='E3_STAGE2' else 5,
            'Generated-signal heuristic only: five first-stage block states feeding a single global factor.' if name=='E3_STAGE2' else
            'Generated-signal heuristic only: global plus four projected residual signals; F5 is reference, not an additional bridge residual.',variables_latent,generated=True)
    context=dict(target=target,cutoff=cutoff,training_end=str(end.date()),production_forecast=frozen['final_forecast'],
        workbook_sha256=manifest['workbook_sha256'],monthly_predictors=91,quarterly_predictors=5,
        production_mask_origin='2026-09-30',production_information_class='EXISTING_RELEASE_GATED_FROZEN_TRANSFORMED_PANEL',
        research_information_class='PSEUDO_REAL_TIME_NOT_VINTAGE_VERIFIED')
    return panels,context


def complete_rows(panel):
    return panel.values.index[panel.values.notna().all(axis=1)]


def longest_rectangle(frame,min_months=36):
    """Maximize observed T*N using missingness only, never data values or scores."""
    obs=frame.notna().to_numpy();best=None;best_key=None
    for start in range(len(frame)):
        valid=np.ones(frame.shape[1],dtype=bool)
        for end in range(start,len(frame)):
            valid &= obs[end]
            t=end-start+1;n=int(valid.sum())
            if t<min_months or n<2:continue
            key=(n*t,n,t,-start)
            if best_key is None or key>best_key:
                best_key=key;best=(frame.index[start:end+1],frame.columns[valid])
    return best


def subset(panel,variant,common_rows,common_calendar):
    if variant=='ORIGINAL_COMPLETE':rows=complete_rows(panel);cols=panel.values.columns
    elif variant=='COMMON_STRICT':rows=common_rows;cols=panel.values.columns
    elif variant=='COMMON_CALENDAR_SUBSET':
        rows=common_calendar;cols=panel.values.columns[panel.values.reindex(rows).notna().all(axis=0)]
    elif variant=='LONG_HISTORY_RECTANGLE':
        rectangle=longest_rectangle(panel.values)
        if rectangle is None:raise ValueError('No >=36-month fully observed rectangle with >=two variables')
        rows,cols=rectangle
    elif variant in ['UNWEIGHTED_ORIGINAL','BALANCED_RESTANDARDIZED']:
        rows=complete_rows(panel);cols=panel.values.columns
    else:raise ValueError('Unknown balancing variant')
    return rows,cols


def balanced(panel,variant,common_rows,common_calendar):
    rows,cols=subset(panel,variant,common_rows,common_calendar)
    selected=panel.z.reindex(index=rows,columns=cols).copy()
    if len(rows)<MIN_MONTHS or len(cols)<2:raise ValueError(f'Insufficient balanced panel: T={len(rows)}, N={len(cols)} (minimum T=12,N=2)')
    if not np.isfinite(selected.to_numpy()).all():raise ValueError('Unexpected missingness after balancing')
    # Constant columns carry no covariance information in this exact window;
    # their exclusion is explicitly recorded by the caller's variable audit.
    cols=selected.columns[selected.std(ddof=1).gt(1e-10)]
    selected=selected[cols]
    if len(cols)<2:raise ValueError('Fewer than two nonconstant balanced-sample variables')
    if variant=='BALANCED_RESTANDARDIZED':
        selected,_,_,ok=research_standardize(panel.values.reindex(index=rows,columns=cols),rows.max(),minimum=12)
        if not ok.all():raise ValueError('Unidentifiable balanced-sample standardization')
    weights=panel.weights.reindex(cols) if variant!='UNWEIGHTED_ORIGINAL' else pd.Series(1.,index=cols)
    return selected.mul(weights,axis=1),rows,cols,weights
