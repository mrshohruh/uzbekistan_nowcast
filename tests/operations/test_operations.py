"""Offline operations contracts, real frozen reproduction and transaction fault tests."""
from pathlib import Path
import json
import os
import sys
import pandas as pd
import numpy as np
import pytest
from scripts.operations.state import ROOT,sha,read,write,promote,model_lock,verify
from scripts.operations.acquisition import compare,ACTIVE
from scripts.operations.run_update import cutoff,parser,validate_masters,production,inventory
from scripts.operations.workspace import current_check


def frame(periods=('2026-07','2026-08'),values=(100.,110.),clean=(1.,2.)):
    return pd.DataFrame(dict(reference_period=periods,reference_date=pd.PeriodIndex(periods,freq='M').to_timestamp('M'),
        raw_value=values,clean_value=clean,frequency='M',quality_flag='',retrieved_at='2026-10-02T00:00:00Z',source_release_date=None))


def test_no_change_keeps_values_and_provenance():
    old=frame();new=old.copy();new['retrieved_at']='2026-10-05T00:00:00Z'
    accepted,changes,valid=compare('ppi',old,new,pd.Timestamp('2026-10-05T01:00Z'))
    assert valid and accepted.equals(old)
    assert all(r['change_type']=='UNCHANGED' and not r['accepted'] for r in changes)


def test_new_observation_detected():
    old=frame();new=frame(('2026-07','2026-08','2026-09'),(100.,110.,120.),(1.,2.,3.))
    accepted,rows,valid=compare('ppi',old,new,pd.Timestamp('2026-10-05T01:00Z'))
    assert valid and len(accepted)==3
    assert rows[-1]['change_type']=='NEW_OBSERVATION' and rows[-1]['accepted']


def test_revision_explicit_and_old_input_unchanged():
    old=frame();before=old.copy();new=frame(values=(100.,111.),clean=(1.,3.))
    accepted,rows,valid=compare('ppi',old,new,pd.Timestamp('2026-10-05T01:00Z'))
    assert old.equals(before) and valid
    assert rows[-1]['change_type']=='REVISION' and rows[-1]['absolute_change']==1
    assert accepted.clean_value.iloc[-1]==3


@pytest.mark.parametrize('value',[0.,-1.,np.inf,np.nan])
def test_invalid_raw_observation_rejected(value):
    old=frame();new=frame(values=(100.,value))
    accepted,rows,valid=compare('m2',old,new,pd.Timestamp('2026-10-05T01:00Z'))
    assert not valid and accepted.equals(old) and not any(r['accepted'] for r in rows)


def test_failed_source_or_disappearance_never_erases_old_rows():
    old=frame();accepted,rows,valid=compare('m2',old,old.iloc[:1].copy(),pd.Timestamp('2026-10-05T01:00Z'))
    assert valid and accepted.equals(old)
    assert rows[-1]['change_type']=='MISSING_IN_NEW_SOURCE' and not rows[-1]['accepted']


def test_pos_scope_missing_after_december_2024():
    old=frame(('2024-11','2024-12'));new=frame(('2024-11','2024-12','2025-01'),(100.,110.,120.),(1.,2.,3.))
    accepted,rows,valid=compare('pos_turnover',old,new,pd.Timestamp('2026-10-05T01:00Z'),pos=True)
    assert valid and accepted.reference_period.max()=='2024-12'
    assert 'SCOPE_VERIFICATION_REQUIRED' in rows[-1]['reason']


def test_frozen_transformations_and_models_unchanged():
    paths,bundle=model_lock(ROOT)
    verify(ROOT,paths)
    spec=bundle['challengers']['PHASE6C_DFM']['factor_specification']
    assert spec==dict(name='DFM-4_R1_P2',fields=list(ACTIVE),factors=1,order=2,start='2019-01-31',balanced=True,winsor=False)
    assert bundle['challengers']['UMIDAS_USD']['monthly_lags']==3


def test_combination_weights_exact():
    _,bundle=model_lock(ROOT)
    assert bundle['weights']['COMBO_DEV_WEIGHT']==dict(dfm=.5438822544881572,umidas=.4561177455118428)
    assert bundle['weights']['COMBO_50_50']==dict(dfm=.5,umidas=.5)
    assert bundle['challengers']['PRODUCTION_ENSEMBLE']['components']==dict(AR2=.5,UMIDAS_USD=.5)


def test_future_retrieval_cannot_enter_earlier_information_set():
    old=frame();new=frame(values=(100.,111.),clean=(1.,3.));new['retrieved_at']='2026-10-06T00:00:00Z'
    accepted,rows,valid=compare('m2',old,new,pd.Timestamp('2026-10-05T01:00Z'))
    assert not valid and accepted.equals(old)


def test_future_release_rejected():
    old=frame();new=frame(values=(100.,111.),clean=(1.,3.));new['source_release_date']='2026-10-06T00:00:00Z'
    assert not compare('m2',old,new,pd.Timestamp('2026-10-05T01:00Z'))[2]


def test_unverified_gdp_not_promoted_or_scored():
    old=frame(('2026-03','2026-06'));old['reference_period']=['2026Q1','2026Q2'];old['frequency']='Q'
    new=old.copy();new.loc[1,'raw_value']=112.;new.loc[1,'clean_value']=12.
    accepted,rows,valid=compare('gdp_real_yoy',old,new,pd.Timestamp('2026-10-05T01:00Z'),gdp=True)
    assert valid and accepted.equals(old)
    assert 'GDP_VALUE_DETECTED_UNVERIFIED' in rows[-1]['reason']


def test_verified_registered_gdp_can_enter_current_master():
    old=frame(('2026-03','2026-06'));old['reference_period']=['2026Q1','2026Q2'];old['frequency']='Q'
    new=old.copy();new.loc[1,'raw_value']=112.;new.loc[1,'clean_value']=12.
    accepted,rows,valid=compare('gdp_real_yoy',old,new,pd.Timestamp('2026-10-05T01:00Z'),gdp=True,verified_gdp={'2026Q2'})
    assert valid and rows[-1]['accepted'] and accepted.clean_value.iloc[-1]==12.


def test_verified_realization_scores_stored_forecasts_only(tmp_path):
    from scripts.operations.prospective import common
    from scripts.operations.prospective.evaluation import evaluate
    row={c:None for c in common.LEDGER_COLUMNS};row.update(snapshot_id='a'*64,model='AR1',forecast=8.,target_quarter='2026Q3',horizon='H3',
        operational_stage='POST_H3_LATE_INITIALIZATION',run_timestamp_utc='2026-10-05T06:00:00Z',prospective_eligible=True)
    common.append_ledger([row],tmp_path)
    evidence=dict(target_quarter='2026Q3',event_kind='FIRST_RELEASE',first_release_date='2026-10-30',value=9.,
        ingested_timestamp='2026-10-31T00:00:00Z',source_url='https://stat.uz/verified.pdf')
    common.append_record(tmp_path/'realization_records',common.digest(evidence),evidence)
    before=(tmp_path/'prospective_forecast_ledger.csv').read_bytes()
    view,governance,n=evaluate(tmp_path)
    assert n==1 and governance=='EARLY_EVIDENCE' and view.forecast_error.iloc[0]==1.
    assert (tmp_path/'prospective_forecast_ledger.csv').read_bytes()==before


def test_transaction_rollback_restores_every_existing_file(tmp_path):
    root=tmp_path/'root';stage=tmp_path/'stage';root.mkdir();stage.mkdir()
    for name in ['a.parquet','b.parquet']:(root/name).write_bytes(b'old');(stage/name).write_bytes(b'new')
    calls=[]
    def faulty(source,target):
        calls.append(target)
        if len(calls)==2:raise OSError('injected commit failure')
        os.replace(source,target)
    with pytest.raises(OSError):promote(root,stage,['a.parquet','b.parquet'],'test',{p:sha(root/p) for p in ['a.parquet','b.parquet']},replace=faulty)
    assert (root/'a.parquet').read_bytes()==(root/'b.parquet').read_bytes()==b'old'
    assert read(root/'data/versions/test/transaction.json')['status']=='ROLLED_BACK'


def test_transaction_preserves_old_master_snapshot(tmp_path):
    root=tmp_path/'root';stage=tmp_path/'stage';root.mkdir();stage.mkdir()
    (root/'a.parquet').write_bytes(b'old');(stage/'a.parquet').write_bytes(b'new')
    result=promote(root,stage,['a.parquet'],'test',{'a.parquet':sha(root/'a.parquet')})
    assert result['a.parquet']==sha(stage/'a.parquet')
    assert (root/'data/versions/test/a.parquet').read_bytes()==b'old'


def test_concurrent_modification_aborts_before_promotion(tmp_path):
    root=tmp_path/'root';stage=tmp_path/'stage';root.mkdir();stage.mkdir()
    (root/'a').write_bytes(b'user edit');(stage/'a').write_bytes(b'candidate')
    with pytest.raises(RuntimeError,match='Concurrent'):promote(root,stage,['a'],'test',{'a':'incorrect'})
    assert (root/'a').read_bytes()==b'user edit'


def test_current_state_identity_does_not_rewrite_historical_release():
    lock,_=model_lock(ROOT)
    assert read(ROOT/'results/operations/initial_state_manifest.json')['does_not_replace_historical_release']
    verify(ROOT,lock)


def test_ledger_append_only_and_duplicate_idempotent(tmp_path):
    from scripts.operations.prospective import common
    row={c:None for c in common.LEDGER_COLUMNS};row.update(snapshot_id='a'*64,run_timestamp_utc='2026-10-05T00:00:00Z')
    common.append_ledger([row],tmp_path);before=(tmp_path/'prospective_forecast_ledger.csv').read_bytes()
    assert not common.append_ledger([row],tmp_path)
    assert (tmp_path/'prospective_forecast_ledger.csv').read_bytes()==before


def test_existing_snapshots_are_immutable():
    from scripts.operations.prospective import common
    for manifest in (ROOT/'results/operations/prospective/snapshots').glob('*/manifest.json'):
        for name,h in read(manifest)['artifacts'].items():assert sha(manifest.parent/name)==h


def test_information_fingerprint_ignores_clock_and_provenance_changes():
    from scripts.operations.shadow_worker import fingerprint
    from scripts.operations.prospective import common
    latest=common.ledger_rows()[-1];info=read(ROOT/'results/operations/prospective/snapshots'/latest['snapshot_id']/'inputs.json')
    bundle=read(ROOT/'config/model_definitions.json')
    altered=dict(info,provenance=[dict(retrieved_at='2099-01-01')])
    assert fingerprint(info,bundle,latest['operational_stage'])==fingerprint(altered,bundle,latest['operational_stage'])
    changed=json.loads(json.dumps(info));changed['benchmark_monthly'][-1]['usd_uzs_mom_dlog']+=.01
    assert fingerprint(info,bundle,latest['operational_stage'])!=fingerprint(changed,bundle,latest['operational_stage'])


def test_no_change_shadow_reproduction_detects_existing_snapshot():
    from scripts.operations.shadow_worker import prepare
    from scripts.operations.prospective import common
    latest=common.ledger_rows()[-1]
    check=max([read(p) for p in (ROOT/'results/operations/prospective/source_checks').glob('*_check.json')],key=lambda c:c['checked_at_utc'])
    before=sha(ROOT/'data/master/v1_monthly.parquet'),sha(ROOT/'data/master/gdp_quarterly.parquet'),sha(ROOT/'results/operations/prospective/prospective_forecast_ledger.csv')
    result=prepare(pd.Timestamp(latest['run_timestamp_utc']),check)
    assert result['duplicate_snapshot'] is not None
    for row in common.ledger_rows()[-7:]:assert result['forecasts'][row['model']]==pytest.approx(row['forecast'],abs=1e-8)
    assert before==(sha(ROOT/'data/master/v1_monthly.parquet'),sha(ROOT/'data/master/gdp_quarterly.parquet'),sha(ROOT/'results/operations/prospective/prospective_forecast_ledger.csv'))


def test_production_under_same_inputs_reproduces():
    rows=production(ROOT,dict(target='2026Q3'),pd.Timestamp('2026-10-05T08:00Z'))
    actual={r['model']:r['forecast'] for r in rows}
    assert actual['ar1']==pytest.approx(8.037443796835966)
    assert actual['ar2']==pytest.approx(7.333857441688032)
    assert actual['umidas_usd_uzs_mom_dlog']==pytest.approx(7.979937793462349)
    assert actual['ensemble_ar2_umidas_usd']==pytest.approx(7.65689761757519)


def test_future_asof_forbidden():
    with pytest.raises(ValueError,match='Future'):cutoff(parser().parse_args(['--as-of','2099-01-01']))


def test_old_source_check_never_fabricated_for_earlier_date(tmp_path):
    folder=tmp_path/'results/operations/prospective/source_checks';folder.mkdir(parents=True)
    write(folder/'x_check.json',dict(checked_at_utc='2026-10-05T00:00:00Z'))
    with pytest.raises(ValueError):current_check(tmp_path,tmp_path,asof=pd.Timestamp('2026-10-04T00:00Z'))


def test_model_lock_detects_tampering(tmp_path):
    path=tmp_path/'model.json';write(path,dict(spec='original'));expected={'model.json':sha(path)}
    write(path,dict(spec='retuned'))
    with pytest.raises(ValueError,match='Protected'):verify(tmp_path,expected)


def test_extreme_new_transformation_withheld():
    old=frame();new=frame(values=(100.,111.),clean=(1.,90.))
    accepted,rows,valid=compare('m2',old,new,pd.Timestamp('2026-10-05T01:00Z'))
    assert not valid and accepted.equals(old) and 'extreme' in rows[-1]['reason']


def test_reviewed_pos_scope_can_extend_without_changing_transform():
    old=frame(('2024-11','2024-12'));new=frame(('2024-11','2024-12','2025-01'),(100.,110.,120.),(1.,2.,3.))
    new['scope_verified']=True
    accepted,rows,valid=compare('pos_turnover',old,new,pd.Timestamp('2026-10-05T01:00Z'),pos=True)
    assert valid and accepted.reference_period.max()=='2025-01' and rows[-1]['accepted']


def test_missing_pos_review_does_not_manufacture_approval(tmp_path):
    from scripts.operations.pos_review import reviewed_pos
    assert reviewed_pos(tmp_path,{},pd.Timestamp('2026-10-05T01:00Z')) is None
    assert not (tmp_path/'config/operations_pos_scope_review.json').exists()


def test_pos_review_requires_actual_archived_receipt(tmp_path):
    from scripts.operations.pos_review import reviewed_pos
    write(tmp_path/'config/operations_pos_scope_review.json',dict(approved_assets=[dict(scope_verified=True,values_verified=True,
        definition_evidence='Documented equivalent scope',reviewer='test reviewer',receipt_file='outside.json')]))
    with pytest.raises(ValueError,match='archived'):reviewed_pos(tmp_path,{},pd.Timestamp('2026-10-05T01:00Z'))


def test_staged_worker_reproduces_without_touching_repository(tmp_path):
    from scripts.operations.workspace import seed,worker
    stage=tmp_path/'project'
    seed(ROOT,stage)
    check=current_check(ROOT,stage)
    before=sha(ROOT/'data/master/v1_monthly.parquet'),sha(ROOT/'results/operations/prospective/prospective_forecast_ledger.csv')
    result=worker(stage,dict(cutoff_utc='2026-10-05T08:00:00Z',check=check,historical=False))
    assert result['duplicate_snapshot'] and len(result['forecasts'])==7
    assert result['forecasts']['PHASE6C_DFM']==pytest.approx(8.301152885465,abs=1e-8)
    assert before==(sha(ROOT/'data/master/v1_monthly.parquet'),sha(ROOT/'results/operations/prospective/prospective_forecast_ledger.csv'))


def test_existing_acquisition_archives_before_parsing(tmp_path,monkeypatch):
    from scripts.operations.acquisition import OperationsDownloader
    from uznowcast.registry import load_registry
    from types import SimpleNamespace
    folder=tmp_path/'metadata';folder.mkdir()
    pd.DataFrame(columns=['http_status','raw_file_path','retrieved_at']).to_parquet(folder/'download_log.parquet',index=False)
    client=OperationsDownloader(tmp_path,tmp_path/'empty','test')
    row=load_registry(ROOT/'registry/uzbekistan_nowcasting_v1.2_registry.xlsx').rows['usd_uzs']
    url=row['machine_download_url'].replace('{YYYY-MM-DD}','2026-10-05')
    content=(ROOT/'tests/fixtures/cbu_usd.json').read_bytes()
    monkeypatch.setattr(client.session,'get',lambda *a,**k:SimpleNamespace(content=content,status_code=200,url=url,headers={'Content-Type':'application/json'}))
    obj,meta=client.get(row,url)
    assert obj and (tmp_path/meta['raw_file_path']).read_bytes()==content
    assert sha(tmp_path/meta['raw_file_path'])==meta['checksum'] and len(client.receipts)==1
    assert meta['raw_file_path'].startswith('data/raw/current_updates/test/usd_uzs/')


def test_http_failure_archives_response_without_erasing_data(tmp_path,monkeypatch):
    from scripts.operations.acquisition import OperationsDownloader
    from uznowcast.registry import load_registry
    from types import SimpleNamespace
    (tmp_path/'metadata').mkdir();pd.DataFrame(columns=['http_status','raw_file_path','retrieved_at']).to_parquet(tmp_path/'metadata/download_log.parquet',index=False)
    stored=tmp_path/'existing.parquet';stored.write_bytes(b'old data')
    client=OperationsDownloader(tmp_path,tmp_path/'empty','test');row=load_registry(ROOT/'registry/uzbekistan_nowcasting_v1.2_registry.xlsx').rows['usd_uzs']
    url=row['machine_download_url'].replace('{YYYY-MM-DD}','2026-10-05')
    monkeypatch.setattr(client.session,'get',lambda *a,**k:SimpleNamespace(content=b'not found',status_code=404,url=url,headers={'Content-Type':'text/html'}))
    with pytest.raises(ValueError,match='HTTP 404'):client.get(row,url)
    assert stored.read_bytes()==b'old data' and client.receipts[0]['http_status']==404


def test_staged_supported_writer_appends_only_private_fixture(tmp_path):
    from scripts.operations.workspace import seed,worker
    stage=tmp_path/'project';seed(ROOT,stage)
    before=(ROOT/'results/operations/prospective/prospective_forecast_ledger.csv').read_bytes()
    stored_before=(stage/'results/operations/prospective/prospective_forecast_ledger.csv').read_bytes()
    data_before={p.relative_to(ROOT).as_posix():sha(p) for directory in ['data/master','data/processed','metadata']
                 for p in (ROOT/directory).glob('*.parquet')}
    # A fixture-only news perturbation; this isolated project is never promoted.
    path=stage/'metadata/observations_long.parquet';observations=pd.read_parquet(path)
    now=pd.Timestamp.now(tz='UTC')
    # Explicit synthetic check fixture: exercise the writer's freshness/archive
    # contract offline. This private audit record is never a provider receipt or
    # promoted evidence; original receipt/release timestamps stay unchanged.
    from uznowcast.storage import digest
    check=dict(current_check(ROOT,stage),checked_at_utc=now.isoformat(),
               note='SYNTHETIC_TEST_FIXTURE: cached payload, simulated current check; never promote')
    write(stage/'results/operations/prospective/source_checks'/(digest(check)+'_check.json'),check)
    original=worker(stage,dict(cutoff_utc=now.isoformat(),check=check,historical=False))
    used=pd.DataFrame(original['info']['panel']).dropna(subset=['gold_price']).iloc[-1]
    period=str(pd.Timestamp(used['month']).to_period('M'))
    selected=observations.variable_key.eq('gold_price')&observations.frequency.eq('M')&observations.clean_value.notna()&observations.reference_period.eq(period)
    assert selected.any()
    observations.loc[selected,'clean_value']+=.01
    observations.to_parquet(path,index=False)
    preview=worker(stage,dict(cutoff_utc=now.isoformat(),check=check,historical=False))
    assert preview['duplicate_snapshot'] is None
    result=worker(stage,dict(cutoff_utc=now.isoformat(),check=check,historical=False,expected_fingerprint=preview['information_fingerprint']),'append')
    assert result['appended_snapshot']
    assert (stage/'results/operations/prospective/prospective_forecast_ledger.csv').read_bytes().startswith(stored_before)
    assert (ROOT/'results/operations/prospective/prospective_forecast_ledger.csv').read_bytes()==before
    verify(ROOT,data_before)


def current_manifest_fixture():
    from scripts.operations.state import validate_current_manifest
    specifications=read(ROOT/'config/model_definitions.json')['specification_hashes']
    return dict(scope='CURRENT_OPERATIONAL_STATE',does_not_replace_historical_release=True,historical_release_reproduction=False,
        candidate_only=True,promoted=False,model_specification_hashes=specifications,master_hashes=dict(monthly='a'*64,quarterly='b'*64),
        registry_hash='c'*64,timestamp_utc='2026-10-05T08:00:00Z'),specifications


def test_new_current_state_manifest_validates_required_identity_and_hashes():
    from scripts.operations.state import validate_current_manifest
    state,specs=current_manifest_fixture();validate_current_manifest(state,specs)


@pytest.mark.parametrize('mutation',[dict(scope='HISTORICAL_RELEASE_REPRODUCTION'),dict(promoted=True),dict(model_specification_hashes={})])
def test_current_state_manifest_rejects_false_claims(mutation):
    from scripts.operations.state import validate_current_manifest
    state,specs=current_manifest_fixture()
    with pytest.raises(ValueError):validate_current_manifest({**state,**mutation},specs)


def test_critical_schema_failure_aborts_promotion_but_http_failure_retains_cache():
    from scripts.operations.acquisition import critical_validation_error
    assert critical_validation_error('usd_uzs',ValueError('Currency/unit schema changed'))
    assert not critical_validation_error('usd_uzs',ValueError('HTTP 404: official source'))
    assert not critical_validation_error('pos_turnover',ValueError('Scope not verified'))


def test_post_replacement_validation_rolls_back_entire_group(tmp_path):
    root=tmp_path/'root';stage=tmp_path/'stage';root.mkdir();stage.mkdir()
    (root/'a').write_bytes(b'old');(stage/'a').write_bytes(b'new')
    def invalid():raise ValueError('critical final validation failed')
    with pytest.raises(ValueError):promote(root,stage,['a'],'test',{'a':sha(root/'a')},validate=invalid)
    assert (root/'a').read_bytes()==b'old'


def test_reporting_failure_rollback_restores_old_data_and_removes_new_snapshot(tmp_path):
    from scripts.operations.state import rollback_completed
    root=tmp_path/'root';stage=tmp_path/'stage';root.mkdir();stage.mkdir()
    (root/'master').write_bytes(b'old');(stage/'master').write_bytes(b'new');(stage/'new-snapshot').write_bytes(b'fixture')
    result=promote(root,stage,['master','new-snapshot'],'test',{'master':sha(root/'master'),'new-snapshot':None})
    rollback_completed(root,'test',result)
    assert (root/'master').read_bytes()==b'old' and not (root/'new-snapshot').exists()


# Phase 6D.1A: separate identities and completed-month source eligibility.
def industry_fixture():
    from scripts.operations.acquisition import real_industry_contract
    from uznowcast.registry import load_registry
    row,contract=real_industry_contract(ROOT,load_registry(ROOT/'registry/uzbekistan_nowcasting_v1.2_registry.xlsx'))
    receipts=read(ROOT/'tests/fixtures/industry_receipts.json')
    descriptor=next(r for r in receipts if '/sdmx/577/table/download/' in r['source_url'])
    payload=next(r for r in receipts if 'sdmx_data_577.json' in r['source_url'])
    return row,contract,descriptor,payload


def industry_client(descriptor,payload,alter=None):
    from types import SimpleNamespace
    def get(row,url,**kwargs):
        receipt=descriptor if '/table/download/' in url else payload
        obj=read(ROOT/receipt['raw_file_path'])
        if alter:alter(obj)
        return obj,dict(receipt,provider='SIAT',variable_key='industrial_production',parser_version='operations-test',schema_fingerprint='fixture',status='downloaded')
    return SimpleNamespace(get=get)


def test_siat_table_and_internal_indicator_identity_are_separate():
    row,contract,_,_=industry_fixture()
    assert contract['table_id']=='577' and contract['indicator_code']=='1.02.01.0004'
    assert row['native_indicator_dataset_id']==contract['indicator_code']
    assert '/sdmx/577/' in row['machine_download_url']


def test_correct_siat577_matches_all_approved_real_history():
    from scripts.operations.acquisition import approved_real_industry
    row,contract,d,p=industry_fixture()
    candidate=approved_real_industry(industry_client(d,p),row,contract)
    old=pd.read_csv(ROOT/'data/current/predictor_provenance.csv',float_precision='round_trip')
    old=old.loc[old.variable_key.eq('industrial_production')&old.selected_for_panel.eq(True)]
    overlap=old.merge(candidate,on='reference_period',suffixes=('_old','_new'),validate='one_to_one')
    assert len(overlap)==len(candidate)==92 and candidate.reference_period.max()=='2026-08'
    assert np.array_equal(overlap.raw_value_old,overlap.raw_value_new)
    assert np.allclose(overlap.clean_value_old,overlap.clean_value_new,rtol=0,atol=1e-12)
    assert (candidate.clean_value==candidate.raw_value-100).all()
    retained,changes,valid=compare('industrial_production_approved_real',old,candidate,pd.Timestamp('2026-10-05T11:00Z'))
    assert valid and retained.equals(old) and all(c['change_type']=='UNCHANGED' for c in changes)


@pytest.mark.parametrize('wrong',['indicator','descriptor','url','unit','frequency','name'])
def test_real_industry_rejects_wrong_identity_or_schema(wrong):
    from scripts.operations.acquisition import approved_real_industry
    row,contract,d,p=industry_fixture()
    if wrong=='url':row['machine_download_url']=row['machine_download_url'].replace('/577/','/590/')
    def alter(obj):
        if isinstance(obj,dict) and wrong=='descriptor':obj['file']=obj['file'].replace('_577','_590')
        if isinstance(obj,list):
            field={'indicator':'Indicator identification number (code)','unit':'Unit of measurement','frequency':'Periodicity','name':'Indicator name'}.get(wrong)
            for m in obj[0]['metadata']:
                if m.get('name_en')==field:m['value_en']='WRONG'
    with pytest.raises(ValueError):approved_real_industry(industry_client(d,p,alter),row,contract)


@pytest.mark.parametrize('variable',['usd_uzs','rub_uzs'])
@pytest.mark.parametrize('existing_partial',[True,False])
def test_october_fx_is_not_revision_or_completed_observation(variable,existing_partial):
    old=frame(('2026-08','2026-09'),(100.,110.),(1.,2.))
    new=frame(('2026-08','2026-09','2026-10'),(100.,110.,112.),(1.,2.,np.nan))
    new.loc[2,'quality_flag']='partial_month';new['is_complete_month']=[True,True,False]
    if existing_partial:
        old=new.copy();old.loc[2,'raw_value']=111.
    retained,changes,valid=compare(variable,old,new,pd.Timestamp('2026-10-05T11:00Z'))
    assert valid and retained.equals(old)
    assert changes[-1]['change_type']=='PARTIAL_CURRENT_MONTH' and not changes[-1]['accepted']
    assert retained.loc[retained.reference_period.eq('2026-09'),'clean_value'].iloc[0]==2.
    assert not any(c['accepted'] for c in changes)


def test_september_gold_new_observation_and_frozen_mask():
    from uznowcast.parsers.external import parse_world_bank_gold
    from uznowcast.transforms.growth import log_growth
    from uznowcast.registry import load_registry
    from uznowcast.models.data import load_dataset,information_cutoff_for_variable
    receipt=pd.read_csv(ROOT/'results/operations/update_20261005_105427_7eadf567/source_receipts.csv')
    receipt=receipt.loc[receipt.variable.eq('gold_price')&receipt.source_reference.str.endswith('.xlsx')].iloc[0]
    assert receipt.source_reference.startswith('https://thedocs.worldbank.org/')
    assert sha(ROOT/receipt.raw_file)==receipt.sha256
    row=load_registry(ROOT/'registry/uzbekistan_nowcasting_v1.2_registry.xlsx').rows['gold_price']
    new,release=parse_world_bank_gold((ROOT/receipt.raw_file).read_bytes(),row)
    new=log_growth(new,'raw_value',1,50.)
    new['retrieved_at']=receipt.retrieval_timestamp;new['source_release_date']=release
    # Freeze the prior information set; the live master may already contain September.
    old=new.loc[new.reference_period.lt('2026-09')].copy()
    retained,changes,valid=compare('gold_price',old,new,pd.Timestamp('2026-10-05T11:00Z'))
    sept=next(c for c in changes if c['period']=='2026-09')
    assert valid and sept['change_type']=='NEW_OBSERVATION' and sept['accepted']
    assert sept['new_value']==pytest.approx(-2.1077527144239383,abs=1e-12)
    assert not new.reference_period.duplicated().any()
    prices=new.set_index('reference_period').raw_value
    assert sept['new_value']==pytest.approx(100*np.log(prices['2026-09']/prices['2026-08']))
    lag=load_dataset(ROOT).release_lag_days
    assert information_cutoff_for_variable(pd.Timestamp('2026-09-30'),'gold_price',lag,'standard')<pd.Timestamp('2026-09-30')
    from scripts.operations.shadow_worker import common
    kernel=common.kernel()
    spec=kernel.Spec('DFM-4_R1_P2',common.FIELDS,1,2,'2019-01-31',True,False)
    panel=pd.DataFrame(1.,index=pd.date_range('2019-01-31','2026-09-30',freq='ME'),columns=common.FIELDS)
    panel.loc['2026-09-30','gold_price']=sept['new_value']
    masked,_=kernel.mask(panel,spec,'2026Q3','H3',lag,'standard')
    assert pd.isna(masked.loc['2026-09-30','gold_price'])
    assert masked.loc['2026-08-31','gold_price']==panel.loc['2026-08-31','gold_price']


def test_unexplained_provenance_change_rejected(tmp_path):
    import shutil
    from scripts.operations.state import verify_current_version
    seal=read(ROOT/'config/production_seal.json')
    needed={p for p in seal['initial_input_hashes'] if p.startswith(('data/','metadata/'))}
    needed.update({'config/production_seal.json','config/provenance_relocations.json','results/operations/initial_state_manifest.json'})
    needed.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'results/operations').glob('update_*/current_state_manifest.json'))
    needed.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'results/operations').glob('update_*/run_manifest.json'))
    for rel in needed:
        source=ROOT/rel
        if not source.is_file():continue
        target=tmp_path/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    verify_current_version(tmp_path)
    changed=tmp_path/'metadata/observations_long.parquet'
    with changed.open('ab') as f:f.write(b'corruption')
    with pytest.raises(ValueError,match='Unrecognized current input version'):verify_current_version(tmp_path)
