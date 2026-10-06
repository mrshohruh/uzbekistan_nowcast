"""Run relevant offline suites with all test artifacts inside Phase 6G.2."""
import sys
import uuid
import xml.etree.ElementTree as ET
from scripts.phase6g2.run import OUT, verify
from scripts.phase6f.experiment import dump


def main():
    import pytest
    from _pytest.tmpdir import TempPathFactory
    temp=OUT/('validation_tmp_'+uuid.uuid4().hex[:8]);temp.mkdir()
    if sys.platform=='win32':
        def base(self):self._basetemp=temp;return temp
        def mktemp(self,basename,numbered=True):
            p=temp/(basename[:12]+uuid.uuid4().hex[:8]);p.mkdir();return p
        TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    paths=['scripts/phase6g2/test_phase6g2.py','scripts/phase6e/test_phase6e.py',
           'scripts/phase6f/test_phase6f.py','scripts/phase6g/test_phase6g.py',
           'scripts/phase6g1/test_phase6g1.py','scripts/phase6g1/test_driver_dashboard.py',
           'scripts/phase6g1/test_m1_dashboard.py','tests/models']
    scope='new' if len(sys.argv)>1 and sys.argv[1]=='new' else 'all'
    if scope=='new':paths=paths[:1]
    suffix='_new' if scope=='new' else ''
    xml=OUT/f'phase6g2_tests{suffix}.xml'
    code=int(pytest.main([*paths,'-q','-p','no:cacheprovider','--junitxml',str(xml)]))
    suites=list(ET.parse(xml).getroot().iter('testsuite'))
    counts={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
    counts['exit_code']=code;dump(OUT/f'phase6g2_tests{suffix}.json',counts)
    verify()
    manifest=OUT/'phase6g2_run_manifest.json'
    import json
    data=json.loads(manifest.read_text());data['tests'+suffix]=counts;dump(manifest,data)
    return code


if __name__=='__main__':sys.exit(main())
