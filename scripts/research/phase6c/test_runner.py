"""Run pytest with inherited Windows sandbox ACLs for disposable test folders.

Python 3.12's Windows mkdir(mode=0700), used by pytest, removes the sandbox
account's inherited access. Only the temporary directory factory is adapted;
test code and assertions are unchanged. No existing ACL is altered.
"""
import json
import sys
import uuid
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from _pytest.tmpdir import TempPathFactory

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
OUT = ROOT / 'results/phase6c'
TEMP = OUT / ('t_' + uuid.uuid4().hex[:8])
TEMP.mkdir(parents=True)


def getbasetemp(self):
    self._basetemp = TEMP
    return TEMP


def mktemp(self, basename, numbered=True):
    basename = self._ensure_relative_to_basetemp(basename)
    path = TEMP / (basename[:12] + uuid.uuid4().hex[:8] if numbered else basename)
    path.mkdir()
    return path


if sys.platform == 'win32':
    TempPathFactory.getbasetemp = getbasetemp
    TempPathFactory.mktemp = mktemp

scope = sys.argv[1] if len(sys.argv)>1 else 'all'
if scope == 'all':
    results = []
    for component in ['repository', 'new', 'phase6b', 'phase6b1', 'phase6b2']:
        with (OUT / f'phase6c_{component}_tests.log').open('w', encoding='utf-8') as log:
            code = subprocess.run([sys.executable, __file__, component], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
        result = json.loads((OUT / f'phase6c_{component}_test_results.json').read_text())
        results.append(result)
    totals = {k: sum(r[k] for r in results) for k in ['tests','passed','errors','failures','skipped']}
    totals['components'] = results
    totals['exit_code'] = int(any(r['exit_code'] for r in results))
    (OUT / 'phase6c_test_results.json').write_text(json.dumps(totals, indent=2), encoding='utf-8')
    print(json.dumps(totals, indent=2))
    sys.exit(totals['exit_code'])
paths = {
    'repository': ['tests'], 'new': ['scripts/research/phase6c/test_phase6c.py'],
    'phase6b': ['scripts/research/phase6b/test_experiment.py'],
    'phase6b1': ['scripts/research/phase6b1/test_boundary.py', 'scripts/research/phase6b1/test_reproduction.py'],
    'phase6b2': ['scripts/research/phase6b2/test_vintages.py'],
}[scope]
xml = OUT / f'phase6c_{scope}_tests.xml'
code = pytest.main([*paths, '-p', 'no:cacheprovider', '--junitxml', str(xml)])
if xml.exists():
    tree = ET.parse(xml)
    suites = list(tree.getroot().iter('testsuite'))
    counts = {k: sum(int(s.get(k, '0')) for s in suites) for k in ['tests', 'errors', 'failures', 'skipped']}
    counts['passed'] = counts['tests'] - counts['errors'] - counts['failures'] - counts['skipped']
    counts['exit_code'] = int(code)
    counts['scope'] = scope
    counts['Windows_temp_factory'] = 'inherited ACL; test assertions unchanged'
    (OUT / f'phase6c_{scope}_test_results.json').write_text(json.dumps(counts, indent=2), encoding='utf-8')
sys.exit(code)
