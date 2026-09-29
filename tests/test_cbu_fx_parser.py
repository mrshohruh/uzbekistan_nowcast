from copy import deepcopy
import numpy as np
import pandas as pd
import pytest
from uznowcast.parsers.cbu import parse_fx, deduplicate_daily
from uznowcast.transforms.frequency import fx_monthly
from uznowcast.io.cbu import download


def test_frozen_response(fixture_json):
    frame=parse_fx(fixture_json('cbu_usd'))
    assert frame.reference_date.iloc[0]==pd.Timestamp('2026-09-29')
    assert frame.normalized_daily.iloc[0]==11806.97


def test_nominal_and_duplicate_handling(fixture_json):
    obj=deepcopy(fixture_json('cbu_usd'))
    obj[0]['Nominal']='100'
    got=parse_fx(obj*2)
    assert len(got)==1
    assert got.normalized_daily.iloc[0]==pytest.approx(118.0697)
    other=deepcopy(obj[0]); other['Rate']='12000'
    with pytest.raises(ValueError,match='Conflicting'):
        parse_fx(obj+[other])


def test_monthly_mean_not_weighted_by_duplicate_days():
    # Synthetic transformation inputs; never used as production observations.
    payload=[dict(Ccy='USD',Date=d,Rate=str(r),Nominal='1') for d,r in
             [('01.01.2024',10),('08.01.2024',20),('08.01.2024',20),('01.02.2024',30),('08.02.2024',60)]]
    monthly=fx_monthly(parse_fx(payload),'2024-01-01','2024-02-29')
    assert monthly.monthly_mean.tolist()==[15,45]
    assert monthly.n_daily.tolist()==[2,2]
    assert monthly.clean_value.iloc[1]==pytest.approx(100*np.log(3))


def test_partial_month_keeps_mean_and_nulls_model_change():
    payload=[dict(Ccy='USD',Date=d,Rate='10',Nominal='1') for d in ['01.01.2024','01.02.2024']]
    monthly=fx_monthly(parse_fx(payload),'2024-01-01','2024-02-10')
    assert monthly.monthly_mean.iloc[-1]==10
    assert pd.isna(monthly.clean_value.iloc[-1])
    assert 'partial_month' in monthly.quality_flag.iloc[-1]


def test_change_lineage_includes_lagged_month_retrieval():
    payload=[dict(Ccy='USD',Date=d,Rate='10',Nominal='1') for d in ['01.01.2024','01.02.2024']]
    daily=parse_fx(payload)
    daily['retrieved_at']=['2024-03-02T00:00:00+00:00','2024-03-01T00:00:00+00:00']
    daily['source_url']=['https://cbu.uz/a','https://cbu.uz/b']
    daily['raw_file_path']=['a','b']
    daily['checksum']=['hash_a','hash_b']
    monthly=fx_monthly(daily,'2024-01-01','2024-02-29')
    assert monthly.retrieved_at.iloc[1]=='2024-03-02T00:00:00+00:00'
    assert monthly.raw_file_path.iloc[1]=='["a", "b"]'


def test_archive_walk_uses_observed_activation_dates(registry):
    class Archive:
        def __init__(self): self.urls=[]
        def get(self,row,url):
            self.urls.append(url)
            request=url.rstrip('/').split('/')[-1]
            activation={'2013-01-20':'15.01.2013','2013-01-14':'08.01.2013','2013-01-07':'01.01.2013'}[request]
            payload=[dict(Ccy='USD',Date=activation,Rate='100',Nominal='1')]
            meta=dict(source_url=url,retrieved_at='2026-09-29T00:00:00+00:00',raw_file_path=request,checksum=request,schema_fingerprint='s')
            return payload,meta
    archive=Archive()
    daily=download(archive,registry.rows['usd_uzs'],'2013-01-01','2013-01-20')
    assert len(daily)==3 and len(archive.urls)==3
    assert daily.reference_date.dt.day.tolist()==[1,8,15]
    assert daily.source_release_date.isna().all()


@pytest.mark.parametrize('field,value',[('Nominal','0'),('Rate','nan'),('Date','31.02.2024'),('Ccy','EUR')])
def test_invalid_fields(field,value,fixture_json):
    obj=fixture_json('cbu_usd'); obj[0][field]=value
    with pytest.raises(ValueError): parse_fx(obj)
