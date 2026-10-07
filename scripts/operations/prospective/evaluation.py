"""Derived scoring views never modify forecast records."""
import pandas as pd
import numpy as np
from scripts.operations.prospective.common import OUT, ledger_rows, save, records
from scripts.operations.prospective.sources import realization_registry

METRIC_COLUMNS=['model','horizon','operational_stage','n','n_forecasts','n_target_quarters','rmse','mae','bias','median_absolute_error','target_definition','interpretation']


def evaluate(out=OUT):
    ledger=pd.DataFrame(ledger_rows(out))
    realized=realization_registry(out)
    save('realization_registry',realized,out)
    scored=[]
    withdrawn={r['snapshot_id'] for r in records(out/'withdrawal_records')}
    for r in ledger.to_dict('records'):
        if r['snapshot_id'] in withdrawn:
            continue
        match=realized.loc[realized.target_quarter.eq(r['target_quarter'])]
        if match.empty or r['forecast'] is None or not r['prospective_eligible']:
            continue
        actual=match.iloc[0]
        # A same-day date-only release does not establish pre-publication ordering.
        if pd.Timestamp(r['run_timestamp_utc']).tz_convert('Asia/Tashkent').date()>=pd.Timestamp(actual.first_release_date).date():
            continue
        error=float(actual.first_release_value)-r['forecast']
        scored.append(dict(r,realization_available=True,realization_first_release=actual.first_release_value,
                           forecast_error=error,absolute_error=abs(error),squared_error=error**2))
    view=pd.DataFrame(scored,columns=list(ledger.columns))
    save('scored_forecasts',view,out)
    if len(view):
        view=view.sort_values('run_timestamp_utc').drop_duplicates(['target_quarter','model','horizon','operational_stage'])
    save('primary_scored_forecasts',view,out)
    metrics=[]
    if len(view):
        for (model,stage),block in view.groupby(['model','operational_stage']):
            for horizon in ['H1','H2','H3','POOLED']:
                g=block if horizon=='POOLED' else block.loc[block.horizon.eq(horizon)]
                if g.empty: continue
                metrics.append(dict(model=model,horizon=horizon,operational_stage=stage,n=len(g),n_forecasts=len(g),
                    n_target_quarters=g.target_quarter.nunique(),rmse=float(np.sqrt(g.squared_error.mean())),
                    mae=float(g.absolute_error.mean()),bias=float(g.forecast_error.mean()),median_absolute_error=float(g.absolute_error.median()),
                    target_definition='VERIFIED_FIRST_RELEASE',interpretation='DESCRIPTIVE_ONLY_SMALL_SAMPLE'))
    save('prospective_metrics',pd.DataFrame(metrics,columns=METRIC_COLUMNS),out)
    keys=['target_quarter','horizon','operational_stage','snapshot_id']
    diagnostics=[]
    correlation=[]
    if len(view):
        pivot=view.pivot(index=keys,columns='model',values='forecast_error')
        for index,r in pivot.iterrows():
            record=dict(zip(keys,index))
            for m in ['PHASE6C_DFM','UMIDAS_USD','COMBO_50_50','COMBO_DEV_WEIGHT']:
                record[m+'_error']=r.get(m,np.nan)
            diagnostics.append(record)
        predictions=view.pivot(index=keys,columns='model',values='forecast')
        for stage,g in pivot.groupby(level='operational_stage'):
            if {'PHASE6C_DFM','UMIDAS_USD'}.issubset(g.columns):
                matched=g[['PHASE6C_DFM','UMIDAS_USD']].dropna()
                pred=predictions.loc[matched.index,['PHASE6C_DFM','UMIDAS_USD']].dropna()
                enough=len(matched)>=3 and matched.nunique().min()>1
                revision=ledger.loc[~ledger.snapshot_id.isin(withdrawn) & ledger.target_quarter.isin(view.target_quarter)
                    & ledger.operational_stage.eq(stage)].copy()
                revision['revision']=revision.sort_values('run_timestamp_utc').groupby(['target_quarter','model']).forecast.diff()
                revision_wide=revision.pivot(index=['target_quarter','snapshot_id'],columns='model',values='revision')
                revision_pairs=revision_wide.reindex(columns=['PHASE6C_DFM','UMIDAS_USD']).dropna()
                correlation.append(dict(operational_stage=stage,n=len(matched),
                    error_correlation=float(matched.corr().iloc[0,1]) if enough else None,
                    forecast_correlation=float(pred.corr().iloc[0,1]) if len(pred)>=3 and pred.nunique().min()>1 else None,
                    revision_correlation=float(revision_pairs.corr().iloc[0,1]) if len(revision_pairs)>=3 and revision_pairs.nunique().min()>1 else None,
                    interpretation='DESCRIPTIVE_ONLY_SMALL_SAMPLE'))
    save('combination_diagnostics',pd.DataFrame(diagnostics,columns=keys+[m+'_error' for m in ['PHASE6C_DFM','UMIDAS_USD','COMBO_50_50','COMBO_DEV_WEIGHT']]),out)
    save('combination_correlations',pd.DataFrame(correlation,columns=['operational_stage','n','error_correlation','forecast_correlation','revision_correlation','interpretation']),out)
    n=view.target_quarter.nunique() if len(view) else 0
    stage=['INITIALIZED','EARLY_EVIDENCE','INSUFFICIENT_EVIDENCE','PRELIMINARY_REVIEW','GOVERNANCE_REVIEW_ELIGIBLE'][min(n,4)]
    return view,stage,n
