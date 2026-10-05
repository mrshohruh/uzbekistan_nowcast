import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).parent))
from common import *
from frozen import initialize
from inputs import eligible,inputs
from monitor import context,calculate,select_target
from evaluation import evaluate
from sources import register_realization


def row(snapshot='a'*64):
    r={c:None for c in LEDGER_COLUMNS}
    r.update(snapshot_id=snapshot,run_timestamp_utc='2026-10-05T06:00:00+00:00',target_quarter='2026Q3',
        horizon='H3',model='AR1',forecast=8.,prospective_eligible=True,operational_stage='POST_H3_LATE_INITIALIZATION',
        realization_available=False)
    return r


def test_frozen_specification_and_weights():
    b=initialize();s=b['challengers']['PHASE6C_DFM']['factor_specification']
    assert tuple(s['fields'])==FIELDS and s['factors']==1 and s['order']==2
    assert s['start']=='2019-01-31' and s['balanced'] and not s['winsor']
    assert b['weights']['COMBO_DEV_WEIGHT']==dict(dfm=WEIGHT_DFM,umidas=WEIGHT_UMIDAS)
    assert b['weights']['COMBO_50_50']==dict(dfm=.5,umidas=.5)
    assert b['challengers']['UMIDAS_USD']['monthly_lags']==3
    assert b['challengers']['UMIDAS_USD']['with_gdp_lag']


def test_protected_artifacts_unchanged():
    verify_hashes(ROOT,json.loads((OUT/'phase6d_protected_start.json').read_text()))


def test_append_only_ledger_and_idempotence(tmp_path):
    one=row();append_ledger([one],tmp_path)
    before=(tmp_path/'phase6d_prospective_forecast_ledger.csv').read_bytes()
    assert not append_ledger([one],tmp_path)
    two=dict(row('b'*64),run_timestamp_utc='2026-10-06T06:00:00+00:00')
    append_ledger([two],tmp_path)
    assert (tmp_path/'phase6d_prospective_forecast_ledger.csv').read_bytes().startswith(before)
    assert ledger_rows(tmp_path)==[one,two]


def test_ledger_rewrite_rejected(tmp_path):
    append_ledger([row()],tmp_path)
    (tmp_path/'phase6d_prospective_forecast_ledger.csv').write_text('tampered')
    with pytest.raises(ValueError,match='altered'):ledger_rows(tmp_path)


def test_conflicting_snapshot_rejected(tmp_path):
    append_ledger([row()],tmp_path)
    with pytest.raises(ValueError,match='Conflicting'):append_ledger([dict(row(),forecast=9)],tmp_path)


def test_future_retrieval_and_release_excluded():
    f=pd.DataFrame(dict(retrieved_at=['2026-10-04Z','2026-10-07Z','2026-10-04Z'],
        source_release_date=[None,None,'2026-10-07Z'],value=[1,999,888]))
    f['retrieved_at']=['2026-10-04T00:00:00Z','2026-10-07T00:00:00Z','2026-10-04T00:00:00Z']
    f['source_release_date']=[None,None,'2026-10-07T00:00:00Z']
    assert eligible(f,pd.Timestamp('2026-10-05',tz='UTC')).value.tolist()==[1]


def test_future_gdp_excluded():
    events=pd.read_csv(ROOT/'results/research/phase6b2/phase6b2_gdp_revision_history.csv')
    future=events.iloc[-1].copy();future['quarter']='2026Q3';future['publication_date']='2026-11-02';future['value']=999
    events=pd.concat([events,pd.DataFrame([future])],ignore_index=True)
    available=vintage_kernel().available_gdp_vintage_as_of(events,'2026-10-05',target='2026Q3')
    assert (available.frame.index<'2026Q3').all() and not available.frame.value.eq(999).any()


def test_pos_missing_and_full_benchmark_history():
    panel,dataset,_=inputs(pd.Timestamp('2026-10-05T08:00:00Z'))
    assert panel.loc['2025-01-01':,'pos_turnover'].isna().all()
    assert panel.pos_turnover.last_valid_index()==pd.Timestamp('2024-12-31')
    assert dataset.monthly.usd_uzs_mom_dlog.loc[:'2018-12-31'].notna().any()


@pytest.mark.parametrize('date,horizon,stage',[
    ('2026-07-31','H1','ON_TIME'),('2026-08-31','H2','ON_TIME'),('2026-09-30','H3','ON_TIME'),
    ('2026-10-05','H3','POST_H3_LATE_INITIALIZATION')])
def test_frozen_calendar_horizons(date,horizon,stage):
    h,_,s,on=context('2026Q3',pd.Timestamp(date,tz='Asia/Tashkent'))
    assert (h,s,on)==(horizon,stage,stage=='ON_TIME')


def test_pending_no_metrics_no_scoring_rewrite(tmp_path):
    append_ledger([row()],tmp_path)
    before=(tmp_path/'phase6d_prospective_forecast_ledger.csv').read_bytes()
    view,stage,n=evaluate(tmp_path)
    assert view.empty and stage=='INITIALIZED' and n==0
    assert pd.read_csv(tmp_path/'phase6d_prospective_metrics.csv').empty
    assert (tmp_path/'phase6d_prospective_forecast_ledger.csv').read_bytes()==before


def test_mutable_dataset_update_not_first_release(tmp_path):
    e=dict(target_quarter='2026Q3',first_release_date='2026-10-04',value=8.,
       source_url='https://api.siat.stat.uz/media/uploads/sdmx/sdmx_data_3698.json',
       raw_file_path='unused',checksum='a'*64,source_verified=True,first_release_verified=True,
       date_basis='DATASET_UPDATE',extraction_evidence='A mutable dataset update cannot establish first release',event_kind='FIRST_RELEASE')
    with pytest.raises(ValueError,match='Dataset update'):register_realization(e,{},tmp_path)


def test_first_release_only_and_same_day_rejected(tmp_path):
    append_ledger([row()],tmp_path)
    r=dict(target_quarter='2026Q3',first_release_date='2026-10-06',value=8.4,event_kind='FIRST_RELEASE',
       ingested_timestamp='2026-10-06T10:00:00Z',source_url='https://stat.uz/test')
    append_record(tmp_path/'realization_records',digest(r),r)
    revised=dict(r,event_kind='REVISION',value=9.,ingested_timestamp='2026-10-07T10:00:00Z')
    append_record(tmp_path/'realization_records',digest(revised),revised)
    view,stage,n=evaluate(tmp_path)
    assert view.realization_first_release.iloc[0]==8.4 and abs(view.forecast_error.iloc[0]-.4)<1e-12
    assert stage=='EARLY_EVIDENCE' and n==1


def test_hashes_reproduce_and_snapshots_intact():
    b=initialize()
    assert {m:digest(d) for m,d in b['challengers'].items()}==b['specification_hashes']
    for folder in (OUT/'snapshots').iterdir():
        manifest=json.loads((folder/'manifest.json').read_text())
        info=json.loads((folder/'inputs.json').read_text())
        assert digest(info)==manifest['input_data_hash']
        for name,h in manifest['artifacts'].items():assert file_hash(folder/name)==h


def test_independent_recompute_determinism():
    rows=ledger_rows();current=rows[-7:];folder=OUT/'snapshots'/current[0]['snapshot_id']
    info=json.loads((folder/'inputs.json').read_text())
    panel=pd.DataFrame(info['panel']).set_index('month');panel.index=pd.to_datetime(panel.index)
    now=pd.Timestamp(current[0]['run_timestamp_utc']);_,dataset,_=inputs(now)
    available=vintage_kernel().available_gdp_vintage_as_of(pd.read_csv(ROOT/'results/research/phase6b2/phase6b2_gdp_revision_history.csv'),
        now.tz_convert('Asia/Tashkent').tz_localize(None),target=current[0]['target_quarter'])
    from dataclasses import replace
    dataset=replace(dataset,gdp=pd.DataFrame({'quarter':available.frame.index,dataset.target_field:available.frame.value.to_numpy()}))
    values,_=calculate(panel,dataset,available,current[0]['target_quarter'],current[0]['horizon'],available.origin)
    for r in current:assert abs(values[r['model']][0]-r['forecast'])<1e-8


def test_same_day_release_not_scored(tmp_path):
    append_ledger([row()],tmp_path)
    r=dict(target_quarter='2026Q3',first_release_date='2026-10-05',value=8.4,event_kind='FIRST_RELEASE',
       ingested_timestamp='2026-10-06T10:00:00Z',source_url='https://stat.uz/test')
    append_record(tmp_path/'realization_records',digest(r),r)
    assert evaluate(tmp_path)[0].empty


def test_withdrawal_preserves_ledger_and_excludes_scores(tmp_path):
    append_ledger([row()],tmp_path)
    r=dict(target_quarter='2026Q3',first_release_date='2026-10-06',value=8.4,event_kind='FIRST_RELEASE',
       ingested_timestamp='2026-10-06T10:00:00Z',source_url='https://stat.uz/test')
    append_record(tmp_path/'realization_records',digest(r),r)
    withdrawal=dict(snapshot_id='a'*64,reason='Test implementation correction')
    append_record(tmp_path/'withdrawal_records',digest(withdrawal),withdrawal)
    assert evaluate(tmp_path)[0].empty and len(ledger_rows(tmp_path))==1


def test_future_monthly_values_do_not_enter_mask():
    panel,dataset,_=inputs(pd.Timestamp('2026-10-05T08:00:00Z'))
    k=kernel();spec=k.Spec('frozen',FIELDS,1,2,'2019-01-31',True,False)
    original,_=k.mask(panel,spec,'2026Q3','H3',dataset.release_lag_days,'standard')
    changed=panel.copy();changed.loc[pd.Timestamp('2026-10-31')]=1e9
    masked,_=k.mask(changed,spec,'2026Q3','H3',dataset.release_lag_days,'standard')
    pd.testing.assert_frame_equal(original,masked)


def test_frozen_combinations_current_snapshot():
    latest={r['model']:r['forecast'] for r in ledger_rows()[-7:]}
    assert abs(latest['COMBO_50_50']-(.5*latest['PHASE6C_DFM']+.5*latest['UMIDAS_USD']))<1e-12
    assert abs(latest['COMBO_DEV_WEIGHT']-(WEIGHT_DFM*latest['PHASE6C_DFM']+WEIGHT_UMIDAS*latest['UMIDAS_USD']))<1e-12


def test_source_check_cannot_be_fabricated():
    from sources import validate_check
    check=dict(source_verified=True,checked_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),latest_quarter='2026Q3')
    with pytest.raises(ValueError,match='archived audit'):validate_check(check)


def test_target_advances_at_h1_without_imputing_previous_gdp():
    assert select_target('2026Q2',pd.Timestamp('2026-10-05',tz='Asia/Tashkent'))=='2026Q3'
    assert select_target('2026Q2',pd.Timestamp('2026-10-31',tz='Asia/Tashkent'))=='2026Q4'
    assert select_target('2026Q3',pd.Timestamp('2026-11-03',tz='Asia/Tashkent'))=='2026Q4'
