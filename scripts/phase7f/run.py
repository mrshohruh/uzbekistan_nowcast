"""Run read-only static factor-number diagnostics on frozen model information."""
import argparse
import json
import logging
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'src'))
from scripts.phase7f.protection import OUT,capture,verify,sha,active_baseline
from scripts.phase7f.panels import build_panels,complete_rows,balanced,subset,MAIN
from scripts.phase7f.criteria import select
from scripts.operations.prospective.common import safe

VARIANTS=['ORIGINAL_COMPLETE','COMMON_STRICT','COMMON_CALENDAR_SUBSET','LONG_HISTORY_RECTANGLE',
          'UNWEIGHTED_ORIGINAL','BALANCED_RESTANDARDIZED']


def save(name,frame):
    frame.to_csv(OUT/f'phase7f_{name}.csv',index=False,float_format='%.17g')


def write(name,value):
    (OUT/f'phase7f_{name}.json').write_text(json.dumps(safe(value),indent=2,allow_nan=False)+'\n',encoding='utf8')


def run(reuse_baseline=False,replay=False):
    OUT.mkdir(parents=True,exist_ok=True)
    baseline_path=active_baseline()
    if reuse_baseline or replay:before=json.loads(baseline_path.read_text())
    else:
        before=capture();baseline_path=OUT/'phase7f_protection_baseline.json'
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(OUT/'pipeline.log',mode='w',encoding='utf8')])
    panels,context=build_panels()
    common=complete_rows(panels[MAIN[0]])
    for name in MAIN[1:]:common=common.intersection(complete_rows(panels[name]))
    # Same calendar support, with every incomplete variable explicitly excluded.
    starts=[max(v.values[c].first_valid_index() for c in v.values) for name,v in panels.items() if name in MAIN]
    ends=[min(v.values[c].last_valid_index() for c in v.values) for name,v in panels.items() if name in MAIN]
    calendar=pd.date_range(max(starts),min(ends),freq='ME')
    context.update(common_strict_months=len(common),common_calendar_start=str(calendar.min().date()),
        common_calendar_end=str(calendar.max().date()),common_calendar_months=len(calendar),
        missing_data_policy='OBSERVED_BALANCED_SUBPANELS_NO_IMPUTATION',minimum_formal_months=12,
        main_kmax_rule='min(10, floor(min(N,T)/2), numerical_rank-1)',
        canonical_normalization='existing origin training mean/sample std, existing measurement weights, retained-row demeaning')
    summaries=[];curves=[];spectrum=[];loadings=[];variables=[];observations=[];caps=[]
    input_fingerprints={}
    for name,panel in panels.items():
        for variant in VARIANTS:
            meta=dict(model=name,sample=variant,declared_variables=len(panel.values.columns),
                original_training_months=len(panel.values),original_observed_cells=int(panel.values.count().sum()),
                original_missing_cells=int(panel.values.isna().sum().sum()),current_factors=panel.current_factors,
                current_factor_definition=panel.meaning,quarterly_covariates=panel.quarterly_covariates,
                generated_signal_heuristic=panel.generated,cutoff=context['cutoff'],training_end=context['training_end'])
            rows=pd.DatetimeIndex([]);cols=pd.Index([])
            try:
                rows,cols=subset(panel,variant,common,calendar)
                frame,rows,cols,weights=balanced(panel,variant,common,calendar)
                fit=select(frame)
                identifier=name+'__'+variant
                fingerprints=sha_bytes(frame)
                input_fingerprints[identifier]=fingerprints
                record=dict(meta,**fit.summary,status='OK',failure=None,
                    sample_start=str(rows.min().date()),sample_end=str(rows.max().date()),
                    excluded_variables=len(panel.values.columns)-len(cols),
                    excluded_months=len(panel.values)-len(rows),calendar_gaps=int(len(pd.date_range(rows.min(),rows.max(),freq='ME'))-len(rows)),
                    panel_sha256=fingerprints)
                summaries.append(record)
                curves.extend(fit.criteria.assign(model=name,sample=variant).to_dict('records'))
                spectrum.extend(fit.spectrum.assign(model=name,sample=variant).to_dict('records'))
                loadings.extend(fit.loadings.assign(model=name,sample=variant,
                    loading_standardized_input=fit.loadings.apply(lambda r:r.loading/weights[r.original_variable],axis=1)).to_dict('records'))
                folder=OUT/'panels';folder.mkdir(exist_ok=True)
                frame.reset_index(names='month').to_csv(folder/f'{identifier}.csv',index=False,float_format='%.17g')
                for requested in [5,10,15]:
                    sensitivity=select(frame,requested,conservative=False)
                    caps.append(dict(model=name,sample=variant,requested_cap=requested,**sensitivity.summary))
            except ValueError as exc:
                summaries.append(dict(meta,status='UNAVAILABLE',failure=str(exc),n_variables=len(cols),n_months=len(rows)))
                logging.warning('%s %s unavailable: %s',name,variant,exc)
            dictionary=panel.variables.set_index('original_variable')
            for c in panel.values:
                missing_window=int(panel.values.reindex(rows)[c].isna().sum()) if len(rows) else None
                status='INCLUDED' if c in cols else ('EXCLUDED_MISSING_WITHIN_CALENDAR' if missing_window else 'EXCLUDED_NO_INFORMATION_OR_BALANCE_POLICY')
                variables.append(dict(**{**dictionary.loc[c].to_dict(),**meta},original_variable=c,balance_status=status,missing_in_retained_window=missing_window,
                    observations_original=int(panel.values[c].count()),first_observed=str(panel.values[c].first_valid_index()),
                    last_observed=str(panel.values[c].last_valid_index()),measurement_weight=float(panel.weights[c]),
                    formal_raw_center=float(panel.values.reindex(rows)[c].mean()) if len(rows) else np.nan,
                    formal_scale=float(panel.values.reindex(rows)[c].std(ddof=1)) if variant=='BALANCED_RESTANDARDIZED' else dictionary.loc[c].get('origin_scale'),
                    formal_weight=1. if variant=='UNWEIGHTED_ORIGINAL' else float(panel.weights[c])))
            for date in panel.values.index:
                missing=panel.values.columns[panel.values.loc[date].isna()].tolist()
                observations.append(dict(model=name,sample=variant,month=str(date.date()),included=date in rows,
                    missing_variable_count=len(missing),missing_variables=' | '.join(missing),
                    exclusion_reason=None if date in rows else 'NOT_IN_DECLARED_BALANCED_SUBPANEL'))
    summary=pd.DataFrame(summaries)
    save('factor_selection',summary);save('criteria',pd.DataFrame(curves));save('eigenvalues',pd.DataFrame(spectrum))
    save('factor_loadings',pd.DataFrame(loadings));save('variable_audit',pd.DataFrame(variables));save('observation_audit',pd.DataFrame(observations))
    save('kmax_sensitivity',pd.DataFrame(caps));write('context',context)
    from scripts.phase7f.report import report
    report(summary,pd.DataFrame(curves),pd.DataFrame(spectrum),pd.DataFrame(loadings),pd.DataFrame(variables),context)
    count=len(before) if replay else verify(before)
    write('run_manifest',dict(protected_file_count=count,protected_artifacts_verified=not replay,
        protection_baseline=baseline_path.name,
        production_forecast=context['production_forecast'],input_panel_fingerprints=input_fingerprints,
        code_sha256={p.name:sha(p) for p in (ROOT/'scripts/phase7f').glob('*') if p.is_file()},
        artifact_sha256={p.name:sha(p) for p in OUT.glob('*.csv')},
        dashboard_sha256=sha(OUT/'phase7f_factor_selection_dashboard.html'),decision='KEEP_PRODUCTION_NO_FACTOR_PROMOTION'))
    print(summary.loc[summary['sample'].eq('ORIGINAL_COMPLETE'),['model','n_variables','n_months','ICp1','ICp2','ICp3','ER','status']].to_string(index=False))


def sha_bytes(frame):
    import hashlib
    # Includes periods and exact column order as well as numeric values.
    return hashlib.sha256(frame.to_csv(float_format='%.17g',lineterminator='\n').encode('utf8')).hexdigest()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-baseline',action='store_true',help='Use separately captured baseline and verify it at completion')
    parser.add_argument('--replay',action='store_true',help='Numerical validation replay; owning validator performs final protected-file verification')
    args=parser.parse_args();run(args.reuse_baseline,args.replay)
