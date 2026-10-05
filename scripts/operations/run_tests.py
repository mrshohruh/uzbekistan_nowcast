"""Run isolated pytest groups using inherited Windows temporary-directory ACLs."""
import importlib.util
import json
from pathlib import Path
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/operations/implementation_tests';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'));sys.dont_write_bytecode=True


def run(scope):
    if scope!='operations':
        spec=importlib.util.spec_from_file_location('operations_test_adapter',ROOT/'scripts/maintenance/cleanup_validate.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        # Keep snapshot filenames under the Windows MAX_PATH limit. Reports still
        # live in the operations evidence directory; only disposable workspaces are short.
        short=ROOT/'results/op_tests';short.mkdir(parents=True,exist_ok=True);module.OUT=short
        code=module.tests(scope,'operations')
        for path in short.glob(f'*operations_{scope}_tests.*'):path.replace(OUT/path.name)
        return code
    import pytest
    from _pytest.tmpdir import TempPathFactory
    folder=ROOT/'results/op_tests'/('o_'+uuid.uuid4().hex[:8]);folder.mkdir(parents=True)
    def base(self):self._basetemp=folder;return folder
    def mktemp(self,basename,numbered=True):
        path=folder/(basename[:12]+uuid.uuid4().hex[:8]);path.mkdir();return path
    if sys.platform=='win32':TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    xml=OUT/'operations_operations_tests.xml'
    code=pytest.main(['scripts/operations/test_operations.py','-p','no:cacheprovider','--junitxml',str(xml),'-q'])
    return int(code)


def summarize():
    totals={key:0 for key in ['tests','failures','errors','skipped']};scopes=[]
    for xml in OUT.glob('operations_*_tests.xml'):
        scopes.append(xml.name)
        for suite in ET.parse(xml).getroot().iter('testsuite'):
            for key in totals:totals[key]+=int(suite.get(key,0))
    totals.update(passed=totals['tests']-totals['failures']-totals['errors']-totals['skipped'],failed=totals['failures']+totals['errors'],scopes=scopes)
    (OUT.parent/'implementation_test_results.json').write_text(json.dumps(totals,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(totals,indent=2))


if __name__=='__main__':
    if sys.argv[1]=='summarize':summarize()
    else:sys.exit(run(sys.argv[1]))
