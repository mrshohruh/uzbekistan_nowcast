"""Write all test reports/temp artifacts within Phase 6G.3."""
import json
import sys
import uuid
import xml.etree.ElementTree as ET
from scripts.phase6g3.protection import OUT,verify,ROOT
from scripts.phase6f.experiment import dump,sha


def main():
    import pytest
    from _pytest.tmpdir import TempPathFactory
    temp=OUT/('validation_tmp_'+uuid.uuid4().hex[:8]);temp.mkdir()
    if sys.platform=='win32':
        def base(self):self._basetemp=temp;return temp
        def mktemp(self,basename,numbered=True):
            p=temp/(basename[:12]+uuid.uuid4().hex[:8]);p.mkdir();return p
        TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    paths=['scripts/phase6g3/test_phase6g3.py','scripts/research/phase6b2/test_vintages.py',
           'scripts/phase6e/test_phase6e.py','scripts/phase6g/test_phase6g.py','scripts/phase6g2/test_phase6g2.py','tests/models']
    scope='new' if len(sys.argv)>1 and sys.argv[1]=='new' else 'all'
    if scope=='new':paths=paths[:1]
    suffix='_new' if scope=='new' else ''
    xml=OUT/f'tests{suffix}.xml';code=int(pytest.main([*paths,'-q','-p','no:cacheprovider','--junitxml',str(xml)]))
    suites=list(ET.parse(xml).getroot().iter('testsuite'))
    counts={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']};counts['exit_code']=code
    dump(OUT/f'tests{suffix}.json',counts)
    manifest=OUT/'run_manifest.json';data=json.loads(manifest.read_text());data.update(protected_artifacts=verify(),
        code_hashes={p.name:sha(p) for p in (ROOT/'scripts/phase6g3').glob('*.py')});data['tests'+suffix]=counts;dump(manifest,data)
    from scripts.phase6g3.finalize import main as finalize
    finalize()
    return code


if __name__=='__main__':sys.exit(main())
