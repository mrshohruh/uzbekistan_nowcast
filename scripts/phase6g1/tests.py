"""Offline suite with inherited Windows temporary-directory ACLs."""
import sys
import uuid
import xml.etree.ElementTree as ET
from scripts.phase6g1.run import ROOT
from scripts.phase6f.experiment import dump

def main():
    import pytest
    from _pytest.tmpdir import TempPathFactory
    scope=sys.argv[1] if len(sys.argv)>1 else 'new';out=ROOT/'results/phase6g1'
    paths=['scripts/phase6e/test_phase6e.py','scripts/phase6f/test_phase6f.py','scripts/phase6g/test_phase6g.py','tests/models'] if scope=='existing' else ['scripts/phase6g1/test_phase6g1.py']
    temp=out/('validation_tmp_'+uuid.uuid4().hex[:8]);temp.mkdir()
    if sys.platform=='win32':
        def base(self):self._basetemp=temp;return temp
        def mktemp(self,basename,numbered=True):
            p=temp/(basename[:12]+uuid.uuid4().hex[:8]);p.mkdir();return p
        TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    xml=out/f'phase6g1_tests_{scope}.xml'
    code=int(pytest.main([*paths,'-q','-p','no:cacheprovider','--junitxml',str(xml)]))
    suites=list(ET.parse(xml).getroot().iter('testsuite'))
    r={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
    r.update(scope=scope,passed=r['tests']-r['failures']-r['errors']-r['skipped'],exit_code=code)
    dump(out/f'phase6g1_tests_{scope}.json',r);return code

if __name__=='__main__':sys.exit(main())
