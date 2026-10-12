"""Use the repository's Windows-compatible pytest temporary-directory convention."""
from pathlib import Path
import contextlib,sys,uuid
import pytest
from _pytest.tmpdir import TempPathFactory
ROOT=Path(__file__).resolve().parents[2]

def main():
    temp=ROOT/'results/phase7c'/('tmp_'+uuid.uuid4().hex[:8]);temp.mkdir(parents=True)
    def base(self):self._basetemp=temp;return temp
    def mktemp(self,basename,numbered=True):
        p=temp/uuid.uuid4().hex[:8];p.mkdir();return p
    if sys.platform=='win32':TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    with (ROOT/'results/phase7c/tests.log').open('w',encoding='utf8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        status=pytest.main(['tests/production','tests/models/test_phase7c.py','-q','-p','no:cacheprovider','--junitxml',str(ROOT/'results/phase7c/tests.xml')])
    print('Test exit status:',status);return status
if __name__=='__main__':sys.exit(main())
