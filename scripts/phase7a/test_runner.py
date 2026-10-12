"""Run relevant offline tests with short Windows temp paths; save only research logs."""
from pathlib import Path
import contextlib
import sys
import uuid
import pytest
from _pytest.tmpdir import TempPathFactory

ROOT=Path(__file__).resolve().parents[2]

def main():
    temp=ROOT/'.tmp'/('e'+uuid.uuid4().hex[:6]);temp.mkdir(parents=True)
    def base(self): self._basetemp=temp;return temp
    def mktemp(self,basename,numbered=True):
        path=temp/uuid.uuid4().hex[:7];path.mkdir();return path
    if sys.platform=='win32':
        TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    with (ROOT/'results/phase7a/phase7a_tests.log').open('w',encoding='utf8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        paths=sys.argv[1:] or ['tests/production','tests/models/test_phase6i.py','tests/models/test_phase7a.py']
        status=pytest.main([*paths,'-q','-p','no:cacheprovider','--junitxml',str(ROOT/'results/phase7a/phase7a_tests.xml')])
    print('Test exit status:',status)
    return int(status)

if __name__=='__main__':sys.exit(main())
