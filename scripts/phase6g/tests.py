"""Offline pytest runner using inherited Windows temporary-directory ACLs."""
import os
from pathlib import Path
import sys
import uuid
import xml.etree.ElementTree as ET
from scripts.phase6g.run import ROOT
from scripts.phase6f.experiment import dump


def main():
    import pytest
    from _pytest.tmpdir import TempPathFactory
    out=ROOT/'results/phase6g'
    scope=sys.argv[1] if len(sys.argv)>1 else 'new'
    paths=['scripts/phase6e/test_phase6e.py','scripts/phase6f/test_phase6f.py','tests/models'] if scope=='existing' else ['scripts/phase6g/test_phase6g.py']
    temp=out/('validation_tmp_'+uuid.uuid4().hex[:8]);temp.mkdir()
    if sys.platform=='win32':
        def getbase(self):
            self._basetemp=temp
            return temp
        def mktemp(self,basename,numbered=True):
            path=temp/(basename[:12]+uuid.uuid4().hex[:8]);path.mkdir()
            return path
        TempPathFactory.getbasetemp=getbase;TempPathFactory.mktemp=mktemp
    xml=out/f'phase6g_tests_{scope}.xml'
    code=int(pytest.main([*paths,'-q','-p','no:cacheprovider','--junitxml',str(xml)]))
    suites=list(ET.parse(xml).getroot().iter('testsuite'))
    result={key:sum(int(s.get(key,0)) for s in suites) for key in ['tests','failures','errors','skipped']}
    result.update(passed=result['tests']-result['failures']-result['errors']-result['skipped'],exit_code=code,scope=scope)
    dump(out/f'phase6g_tests_{scope}.json',result)
    return code


if __name__=='__main__':sys.exit(main())
