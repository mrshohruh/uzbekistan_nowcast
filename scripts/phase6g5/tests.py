"""Relevant offline suite using the repository's Windows inherited-ACL workaround."""
import sys
import uuid
import json
import xml.etree.ElementTree as ET
from scripts.phase6g5.run import OUT

def main():
    import pytest
    from _pytest.tmpdir import TempPathFactory
    temp=OUT/('validation_tmp_'+uuid.uuid4().hex[:8]);temp.mkdir()
    if sys.platform=='win32':
        def base(self):self._basetemp=temp;return temp
        def mktemp(self,basename,numbered=True):
            p=temp/(basename[:12]+uuid.uuid4().hex[:8]);p.mkdir();return p
        TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    paths=['tests/models','scripts/research/phase6b2/test_vintages.py',
           'scripts/research/phase6c/test_phase6c.py',
           *[f'scripts/{p}/test_{p}.py' for p in ['phase6e','phase6f','phase6g','phase6g1','phase6g2','phase6g3','phase6g4','phase6g5']]]
    xml=OUT/'phase6g5_tests.xml'
    code=int(pytest.main([*paths,'-q','-p','no:cacheprovider','--junitxml',str(xml)]))
    suites=list(ET.parse(xml).getroot().iter('testsuite'))
    result={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
    result.update(passed=result['tests']-result['failures']-result['errors']-result['skipped'],exit_code=code)
    (OUT/'phase6g5_test_results.json').write_text(json.dumps(result,indent=2)+'\n')
    return code

if __name__=='__main__':sys.exit(main())
