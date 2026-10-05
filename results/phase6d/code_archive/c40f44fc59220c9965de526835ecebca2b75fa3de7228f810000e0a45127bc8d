"""Inherited-ACL Windows test directories; all output confined to Phase 6D."""
import sys
import uuid
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from _pytest.tmpdir import TempPathFactory

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
OUT=ROOT/'results/phase6d'
TEMP=OUT/('t_'+uuid.uuid4().hex[:8]);TEMP.mkdir()
def base(self):self._basetemp=TEMP;return TEMP
def temp(self,basename,numbered=True):
    path=TEMP/(basename[:12]+uuid.uuid4().hex[:8]);path.mkdir();return path
if sys.platform=='win32':
    TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=temp
scope=sys.argv[1] if len(sys.argv)>1 else 'new'
paths={'new':['scripts/research/phase6d/test_phase6d.py'],'repository':['tests'],
       'phase6c':['scripts/research/phase6c/test_phase6c.py']}[scope]
xml=OUT/f'phase6d_{scope}_tests.xml'
code=pytest.main([*paths,'-p','no:cacheprovider','--junitxml',str(xml),'-q'])
suites=list(ET.parse(xml).getroot().iter('testsuite'))
counts={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','errors','failures','skipped']}
counts.update(passed=counts['tests']-counts['errors']-counts['failures']-counts['skipped'],exit_code=int(code),scope=scope)
(OUT/f'phase6d_{scope}_test_results.json').write_text(json.dumps(counts,indent=2))
sys.exit(code)
