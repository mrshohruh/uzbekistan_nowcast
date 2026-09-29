from types import SimpleNamespace
import pandas as pd
import pytest
from uznowcast.provenance import archive_response, read_raw
from uznowcast.vintages import compare_revisions, store_vintages, available_asof
from uznowcast.validation.schema import schema_fingerprint, strict_json_loads


def test_immutable_archive_and_checksum(tmp_path,registry):
    response=SimpleNamespace(content=b'[{"x":1}]',url='https://cbu.uz/example',status_code=200,headers={'Content-Type':'application/json'})
    row=registry.rows['usd_uzs']
    a=archive_response(tmp_path,row,response.url,response,'a')
    b=archive_response(tmp_path,row,response.url,response,'b')
    assert a['raw_file_path']!=b['raw_file_path']
    assert a['checksum']==b['checksum']
    assert read_raw(tmp_path,a)==[{'x':1}]
    (tmp_path/a['raw_file_path']).write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='checksum'): read_raw(tmp_path,a)


def test_schema_fingerprint_tracks_structure_not_dates_values():
    a=[dict(Code='a',**{'2024-M01':1.})]
    b=[dict(Code='b',**{'2024-M01':2.,'2024-M02':3.})]
    assert schema_fingerprint(a)==schema_fingerprint(b)
    assert schema_fingerprint(a)!=schema_fingerprint([dict(Code='a',region='new')])


def test_duplicate_json_period_is_not_silently_overwritten():
    with pytest.raises(ValueError,match='Duplicate JSON key'):
        strict_json_loads('{"2024-M01": 1, "2024-M01": 2}')


def test_revision_retention(tmp_path):
    a=pd.DataFrame([dict(variable_key='x',reference_period='2024-01',frequency='M',raw_value=10.,clean_value=1.,
                         retrieved_at='2024-02-01T00:00:00+00:00',vintage_date='2024-02-01T00:00:00+00:00',
                         source_release_date=None,raw_file_path='a',checksum='a',parser_version='1',schema_fingerprint='s')])
    b=a.copy(); b['raw_value']=12.; b['vintage_date']=b['retrieved_at']='2024-03-01T00:00:00+00:00'; b['checksum']='b'
    revision=compare_revisions(a,b)
    assert revision.absolute_revision.iloc[0]==2
    assert revision.revision_type.iloc[0]=='source_revision'
    store_vintages(a,tmp_path); store_vintages(b,tmp_path); store_vintages(b,tmp_path)
    assert len(pd.read_parquet(tmp_path/'metadata/observations_long.parquet'))==2
    all_values=pd.concat([a,b],ignore_index=True)
    assert available_asof(all_values,'2024-01-31').empty
    assert available_asof(all_values,'2024-02-15').raw_value.iloc[0]==10.
    assert available_asof(all_values,'2024-03-15').raw_value.iloc[0]==12.
