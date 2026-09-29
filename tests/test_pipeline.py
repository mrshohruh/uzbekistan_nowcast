"""End-to-end offline fixture builds; no live HTTP is allowed by conftest."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import shutil
import pandas as pd

from conftest import ROOT
from uznowcast.pipeline import build
from uznowcast.provenance import archive_response


def stage(tmp_path, registry, fixture_json, scope='pilot'):
    shutil.copytree(ROOT/'config', tmp_path/'config')
    shutil.copytree(ROOT/'registry', tmp_path/'registry')
    for row in registry.scope(scope):
        key=row['variable_key']
        row=registry.rows[key]
        if row['provider']=='SIAT':
            # File links were observed in live descriptors; fixture wrappers omit user/contact fields.
            url=f'https://api.siat.stat.uz/media/uploads/sdmx/sdmx_data_{row["dataset_page_id"]}.json'
            descriptor=dict(file=url,updated_at='2026-09-02T14:12:47.106082+05:00')
            bodies=[(row['machine_download_url'],descriptor),(url,fixture_json(key))]
        elif key == 'usd_uzs':
            bodies=[(row['machine_download_url'].replace('{YYYY-MM-DD}','2026-09-29'),fixture_json('cbu_usd'))]
        else:
            bodies=[(row['human_source_url'], (ROOT/'tests/fixtures/m2_page.html').read_bytes()),
                    ('https://cbu.uz/sdmx/public/DCS_Uzbekistan_Online.xlsx',
                     (ROOT/'tests/fixtures/m2.xlsx').read_bytes())]
        for url,body in bodies:
            if isinstance(body, bytes):
                content=body
                content_type=('text/html; charset=UTF-8' if url.endswith('/') else
                              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            else:
                content=json.dumps(body).encode()
                content_type='application/json'
            response=SimpleNamespace(content=content,url=url,status_code=200,headers={'Content-Type':content_type})
            archive_response(tmp_path,row,url,response,'fixture')


def test_offline_build_replay_deterministic(tmp_path,registry,fixture_json):
    stage(tmp_path,registry,fixture_json)
    first=build(tmp_path,offline=True,fx_start='2026-09-29',fx_end='2026-09-29')
    assert first['status']=='passed_with_warnings' and not first['failures']
    before=pd.read_parquet(tmp_path/'data/master/pilot_monthly.parquet')
    vintage_before=pd.read_parquet(tmp_path/'metadata/observations_long.parquet')
    raw_before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path/'data/raw').rglob('*') if p.is_file()}
    second=build(tmp_path,offline=True,fx_start='2026-09-29',fx_end='2026-09-29')
    assert second['status']=='passed_with_warnings'
    pd.testing.assert_frame_equal(before,pd.read_parquet(tmp_path/'data/master/pilot_monthly.parquet'))
    pd.testing.assert_frame_equal(vintage_before,pd.read_parquet(tmp_path/'metadata/observations_long.parquet'))
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in raw_before.items())
    assert (tmp_path/'data/master/gdp_quarterly.xlsx').exists()
    assert (tmp_path/'metadata/download_log.parquet').exists()
    assert (tmp_path/'metadata/schema_log.parquet').exists()


def test_failure_does_not_publish_partial_master(tmp_path,registry,fixture_json):
    stage(tmp_path,registry,fixture_json)
    report=build(tmp_path,offline=True,fx_start='2026-01-01',fx_end='2026-09-29')
    assert report['status']=='failed' and 'usd_uzs' in report['failures']
    assert not (tmp_path/'data/master/pilot_monthly.parquet').exists()
    assert (tmp_path/'data/processed/gdp_real_yoy.parquet').exists()
    assert json.loads((tmp_path/'metadata/validation_summary.json').read_text())['status']=='failed'


def test_phase2b_offline_build_replay_and_outputs(tmp_path, registry, fixture_json):
    stage(tmp_path, registry, fixture_json, scope='pilot8')
    first=build(tmp_path,scope='pilot8',offline=True,fx_start='2026-09-29',fx_end='2026-09-29')
    assert first['status']=='passed_with_warnings' and not first['failures']
    master=pd.read_parquet(tmp_path/'data/master/pilot8_monthly.parquet')
    fields=[row['clean_model_field'] for row in registry.scope('pilot8')
            if row['native_frequency']!='Quarterly']
    assert master.columns.tolist()==['date']+fields+['usd_uzs_is_complete','usd_uzs_quality_flag']
    assert 'gdp_real_yoy_pct' not in master
    assert (tmp_path/'data/master/pilot8_monthly.xlsx').exists()
    assert all((tmp_path/f'data/processed/{key}.parquet').exists()
               for key in ('gdp_real_yoy','industrial_production','construction','cpi_headline',
                           'exports_total','imports_total','usd_uzs','m2'))
    before=master.copy()
    vintages=pd.read_parquet(tmp_path/'metadata/observations_long.parquet')
    raw={p:hashlib.sha256(p.read_bytes()).hexdigest()
         for p in (tmp_path/'data/raw').rglob('*') if p.is_file()}
    second=build(tmp_path,scope='pilot8',offline=True,fx_start='2026-09-29',fx_end='2026-09-29')
    assert second['status']=='passed_with_warnings'
    pd.testing.assert_frame_equal(before,pd.read_parquet(tmp_path/'data/master/pilot8_monthly.parquet'))
    pd.testing.assert_frame_equal(vintages,pd.read_parquet(tmp_path/'metadata/observations_long.parquet'))
    assert raw=={p:hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (tmp_path/'data/raw').rglob('*') if p.is_file()}
