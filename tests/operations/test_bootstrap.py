"""External data restoration preserves containment and byte-level integrity."""
import hashlib
import json
import os
from pathlib import Path
import pytest
from scripts.operations.bootstrap import restore


def fixture(tmp_path, relative='data/sample.csv'):
    source=tmp_path/'source';target=tmp_path/'target'
    (source/'data').mkdir(parents=True);(target/'config').mkdir(parents=True)
    payload=b'date,value\n2026-01,1\n'
    (source/'data/sample.csv').write_bytes(payload)
    manifest={'files':{relative:hashlib.sha256(payload).hexdigest()}}
    (target/'config/bootstrap_inputs.json').write_text(json.dumps(manifest))
    return source,target,payload


@pytest.mark.parametrize('extended',[False,True])
def test_restore_verifies_bytes_with_equivalent_windows_paths(tmp_path,monkeypatch,extended):
    source,target,payload=fixture(tmp_path)
    if extended:
        if os.name!='nt':pytest.skip('Windows extended path spelling')
        original=Path.resolve
        def resolve(path,*args,**kwargs):
            value=str(original(path,*args,**kwargs))
            return Path(value if value.startswith('\\\\?\\') else '\\\\?\\'+value)
        monkeypatch.setattr(Path,'resolve',resolve)
    assert restore(source,target)==1
    assert (target/'data/sample.csv').read_bytes()==payload


def test_bootstrap_rejects_path_traversal(tmp_path):
    source,target,_=fixture(tmp_path,'../escape.csv')
    with pytest.raises(ValueError,match='Unsafe bootstrap path'):restore(source,target)
    assert not (tmp_path/'escape.csv').exists()


def test_bootstrap_rejects_changed_source_bytes(tmp_path):
    source,target,_=fixture(tmp_path)
    (source/'data/sample.csv').write_bytes(b'changed')
    with pytest.raises(ValueError,match='Missing or changed bootstrap input'):restore(source,target)
    assert not (target/'data/sample.csv').exists()
