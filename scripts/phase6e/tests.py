"""Isolate legacy pytest imports and use inherited Windows temporary ACLs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/phase6e/tests';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'));sys.dont_write_bytecode=True
SCOPES={'phase6e':['scripts/phase6e/test_phase6e.py'],'repository':['tests'],
        'operations':['scripts/operations/test_operations.py'],
        'phase6c':['scripts/research/phase6c/test_phase6c.py'],
        'phase6d':['scripts/research/phase6d/test_phase6d.py'],
        'phase6b':['scripts/research/phase6b/test_experiment.py'],
        'phase6b1':['scripts/research/phase6b1/test_boundary.py','scripts/research/phase6b1/test_reproduction.py'],
        'phase6b2':['scripts/research/phase6b2/test_vintages.py'],
        'phase6a2':['scripts/research/phase6a2/test_recovery.py']}


def main():
    scope=sys.argv[1] if len(sys.argv)>1 else 'all'
    if scope=='all':
        reports=[]
        for name in SCOPES:
            with (OUT/f'{name}.log').open('w',encoding='utf8') as log:
                subprocess.run([sys.executable,'-m','scripts.phase6e.tests',name],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                               env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1'))
            path=OUT/f'{name}.json'
            reports.append(json.loads(path.read_text()) if path.exists() else dict(scope=name,tests=0,passed=0,failures=0,errors=1,skipped=0,exit_code=1))
        result={key:sum(r[key] for r in reports) for key in ['tests','passed','failures','errors','skipped']}
        result['scopes']=reports
        (OUT.parent/'phase6e_test_results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
        print(json.dumps(result,indent=2));return int(bool(result['errors']+result['failures']))
    import pytest
    from _pytest.tmpdir import TempPathFactory
    temp=ROOT/'results/phase6e'/('t_'+uuid.uuid4().hex[:8]);temp.mkdir()
    def base(self):self._basetemp=temp;return temp
    def mktemp(self,basename,numbered=True):
        path=temp/(basename[:8]+uuid.uuid4().hex[:6]);path.mkdir();return path
    if sys.platform=='win32':TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    if scope=='phase6d':
        # The unmodified Phase 6D suite asserts the old default pointer is frozen.
        # Exercise that historical contract in a real isolated workspace seeded
        # with the sealed V1 dashboard, rather than weakening its assertions.
        from scripts.operations.workspace import seed
        stage=temp/'project';seed(ROOT,stage)
        sys.path.insert(0,str(stage));sys.path.insert(0,str(stage/'src'))
        paths=[str(stage/path) for path in SCOPES[scope]]
    else:paths=SCOPES[scope]
    xml=OUT/f'{scope}.xml'
    code=int(pytest.main([*paths,'-p','no:cacheprovider','--junitxml',str(xml),'-q']))
    suites=list(ET.parse(xml).getroot().iter('testsuite'))
    result={key:sum(int(s.get(key,0)) for s in suites) for key in ['tests','failures','errors','skipped']}
    result.update(scope=scope,passed=result['tests']-result['failures']-result['errors']-result['skipped'],exit_code=code)
    (OUT/f'{scope}.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return code


if __name__=='__main__':sys.exit(main())
