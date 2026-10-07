"""Scientific policy and code integrity are independent of historical paths."""
from pathlib import Path
import pytest
from scripts.operations.seal import verify
from scripts.operations.state import model_lock,read
ROOT=Path(__file__).resolve().parents[2]
def test_current_seal_has_no_historical_runtime_dependency():
    _,seal=verify(ROOT)
    assert not any('/phase' in p or 'scripts/research/' in p for p in seal['runtime_hashes'])
    assert seal['specification_hashes']==read(ROOT/'config/model_definitions.json')['specification_hashes']
def test_seal_rejects_code_mutation_in_private_copy(tmp_path):
    import shutil
    seal=read(ROOT/'config/production_seal.json')
    needed=set(seal['runtime_hashes']) | {'config/production_seal.json','config/production_seal_acceptance.json'}
    for rel in needed:
        if not (ROOT/rel).is_file():continue
        dest=tmp_path/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dest)
    target=tmp_path/'scripts/production/models.py';target.write_text(target.read_text()+'\n# tampered\n')
    with pytest.raises(ValueError,match='seal mismatch'):verify(tmp_path)
