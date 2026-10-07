"""Run maintained tests with short Windows temporary paths."""
import os
import shutil
from pathlib import Path
import sys
import uuid
import pytest
from _pytest.tmpdir import TempPathFactory
ROOT=Path(__file__).resolve().parents[2]
def main():
    temp=ROOT/'data/t'/uuid.uuid4().hex[:8]
    temp.mkdir(parents=True)
    def base(self):self._basetemp=temp;return temp
    def mktemp(self,basename,numbered=True):
        path=temp/(basename[:8]+uuid.uuid4().hex[:6]);path.mkdir();return path
    if sys.platform=='win32':
        TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    paths=sys.argv[1:] or ['tests']
    try:
        return int(pytest.main([*paths,'-p','no:cacheprovider','-q','--junitxml',str(ROOT/'results/repository_cleanup/phase6h1_current_tests.xml')]))
    finally:
        if not temp.resolve().is_relative_to((ROOT/'data/t').resolve()):raise ValueError('Unsafe test cleanup')
        shutil.rmtree(temp)
if __name__=='__main__':sys.exit(main())
