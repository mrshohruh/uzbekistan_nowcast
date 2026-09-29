from types import SimpleNamespace
import pytest
import requests
from uznowcast.io.http import Downloader


def response(status=200, body=b'[{"x":1}]', content_type='application/json'):
    return SimpleNamespace(status_code=status,content=body,url='https://cbu.uz/test',headers={'Content-Type':content_type})


def test_retry_temporary_status_and_archive_every_attempt(tmp_path,registry,monkeypatch):
    client=Downloader(tmp_path,'run',delay=0)
    responses=iter([response(503),response()])
    calls=[]
    def get(*args,**kwargs):
        calls.append(args[0]); return next(responses)
    monkeypatch.setattr(client.session,'get',get)
    monkeypatch.setattr('uznowcast.io.http.time.sleep',lambda seconds:None)
    row=registry.rows['usd_uzs']
    obj,meta=client.get(row,'https://cbu.uz/test')
    assert obj==[{'x':1}] and len(calls)==2
    assert len(list((tmp_path/'data/raw').rglob('*.payload')))==2
    client.get(row,'https://cbu.uz/test')
    assert len(calls)==2


@pytest.mark.parametrize('status,body,kind',[(404,b'not found','text/plain'),(200,b'<html>error</html>','text/html'),(200,b'','application/json')])
def test_permanent_errors_not_retried(tmp_path,registry,monkeypatch,status,body,kind):
    client=Downloader(tmp_path,'run',delay=0)
    calls=[]
    def get(*args,**kwargs):
        calls.append(1); return response(status,body,kind)
    monkeypatch.setattr(client.session,'get',get)
    with pytest.raises(ValueError): client.get(registry.rows['usd_uzs'],'https://cbu.uz/test')
    assert len(calls)==1
    assert len(list((tmp_path/'data/raw').rglob('*.payload')))==1


def test_timeouts_bounded_and_logged(tmp_path,registry,monkeypatch):
    client=Downloader(tmp_path,'run',delay=0)
    def get(*args,**kwargs): raise requests.Timeout('test timeout')
    monkeypatch.setattr(client.session,'get',get)
    monkeypatch.setattr('uznowcast.io.http.time.sleep',lambda seconds:None)
    with pytest.raises(requests.Timeout): client.get(registry.rows['usd_uzs'],'https://cbu.uz/test')
    assert len(client.events)==3


def test_offline_checks_payload_checksum(tmp_path,registry,monkeypatch):
    client=Downloader(tmp_path,'run',delay=0)
    monkeypatch.setattr(client.session,'get',lambda *a,**kw:response())
    row=registry.rows['usd_uzs']
    _,meta=client.get(row,'https://cbu.uz/test')
    offline=Downloader(tmp_path,'offline',offline=True)
    assert offline.get(row,'https://cbu.uz/test')[0]==[{'x':1}]
    (tmp_path/meta['raw_file_path']).write_bytes(b'bad')
    with pytest.raises(ValueError,match='checksum'):
        Downloader(tmp_path,'another',offline=True).get(row,'https://cbu.uz/test')


def test_system_trust_off_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv('UZNOWCAST_USE_SYSTEM_TRUST', raising=False)
    client = Downloader(tmp_path, 'run', delay=0)
    assert client.system_trust is False


def test_system_trust_opt_in_calls_truststore(tmp_path, monkeypatch):
    monkeypatch.setenv('UZNOWCAST_USE_SYSTEM_TRUST', '1')
    calls = []
    import types
    fake = types.ModuleType('truststore')
    fake.inject_into_ssl = lambda: calls.append('injected')
    monkeypatch.setitem(__import__('sys').modules, 'truststore', fake)
    client = Downloader(tmp_path, 'run', delay=0)
    assert client.system_trust is True and calls == ['injected']


def test_system_trust_ignored_in_offline_mode(tmp_path, monkeypatch):
    monkeypatch.setenv('UZNOWCAST_USE_SYSTEM_TRUST', '1')
    client = Downloader(tmp_path, 'run', delay=0, offline=True)
    assert client.system_trust is False


def test_system_trust_missing_package_raises(tmp_path, monkeypatch):
    monkeypatch.setenv('UZNOWCAST_USE_SYSTEM_TRUST', '1')
    import sys
    monkeypatch.setitem(sys.modules, 'truststore', None)  # ImportError on `import truststore`
    with pytest.raises(RuntimeError, match='truststore'):
        Downloader(tmp_path, 'run', delay=0)
