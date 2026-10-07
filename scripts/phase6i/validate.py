"""Use the project's maintained short-path Windows fixture convention."""
from pathlib import Path
import sys
import uuid
import shutil
import json
import pytest
from _pytest.tmpdir import TempPathFactory
from scripts.phase6i.run import ROOT


def main():
    out=ROOT/'results/phase6i'
    temp=ROOT/'t6i'/uuid.uuid4().hex[:8]
    temp.mkdir(parents=True)
    def base(self):self._basetemp=temp;return temp
    def mktemp(self,basename,numbered=True):
        path=temp/(basename[:8]+uuid.uuid4().hex[:6]);path.mkdir();return path
    if sys.platform=='win32':
        TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    try:
        code=int(pytest.main(['tests','-p','no:cacheprovider','-q',
            '--junitxml',str(out/'phase6i_tests.xml')]))
        (out/'phase6i_validation.json').write_text(json.dumps(dict(pytest_exit_code=code,
            scope='Complete tests/ suite including new Phase6I tests',
            temp_path_convention='Existing scripts.maintenance.validate_current short-path Windows fixtures'),indent=2)+'\n')
        return code
    finally:
        if not temp.resolve().is_relative_to((ROOT/'t6i').resolve()):raise ValueError('Unsafe test cleanup')
        shutil.rmtree(temp)
        if not any((ROOT/'t6i').iterdir()):(ROOT/'t6i').rmdir()


if __name__=='__main__':sys.exit(main())
