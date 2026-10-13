"""Full existing + new pytest suite using Windows-compatible temporary paths."""
from pathlib import Path
import contextlib
import json
import sys
import uuid
import xml.etree.ElementTree as ET
import pytest
from _pytest.tmpdir import TempPathFactory

ROOT=Path(__file__).resolve().parents[2]


def main():
    out=ROOT/'results/phase7d';out.mkdir(parents=True,exist_ok=True)
    temp=out/('tmp_tests_'+uuid.uuid4().hex[:8]);temp.mkdir()
    def base(self):self._basetemp=temp;return temp
    def mktemp(self,basename,numbered=True):
        p=temp/uuid.uuid4().hex[:8];p.mkdir();return p
    if sys.platform=='win32':
        TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    with (out/'phase7d_tests.log').open('w',encoding='utf8') as log, contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        code=pytest.main(['tests','-q','-p','no:cacheprovider','--junitxml',str(out/'phase7d_tests.xml')])
    tree=ET.parse(out/'phase7d_tests.xml')
    suites=tree.getroot().findall('testsuite')
    result={key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ['tests','failures','errors','skipped']}
    result.update(exit_code=code,scope='All existing tests and new Phase 7D tests')
    (out/'phase7d_validation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2));raise SystemExit(code)


if __name__=='__main__':main()
