"""Execute full-suite, offline browser, determinism and protected-file checks."""
from pathlib import Path
import contextlib
import json
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

import pytest
from _pytest.tmpdir import TempPathFactory
from scripts.phase7e.protection import sha,verify
from scripts.phase7e.browser_check import check

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/phase7e'


def main():
    if not (OUT/'phase7e_results.md').exists(): raise RuntimeError('Run scripts.phase7e.run first')
    old=json.loads((OUT/'phase7e_validation.json').read_text())
    hashes={p.name:sha(p) for p in OUT.glob('*.csv')}
    dashboard=sha(OUT/'phase7e_economic_dfm_dashboard.html')
    # A complete second execution verifies all numerical outputs, not only one fit.
    with (OUT/'phase7e_reproducibility.log').open('w',encoding='utf8') as log:
        rerun=subprocess.run([sys.executable,'-B','-m','scripts.phase7e.run','--numerical-replay'],cwd=ROOT,stdout=log,stderr=log)
    changes=[name for name,digest in hashes.items() if sha(OUT/name)!=digest]
    deterministic=rerun.returncode==0 and not changes and sha(OUT/'phase7e_economic_dfm_dashboard.html')==dashboard
    temp=OUT/('tmp_tests_'+uuid.uuid4().hex[:8]);temp.mkdir()
    def base(self): self._basetemp=temp;return temp
    def mktemp(self,basename,numbered=True):
        p=temp/uuid.uuid4().hex[:8];p.mkdir();return p
    if sys.platform=='win32':
        TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    with (OUT/'phase7e_tests.log').open('w',encoding='utf8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        code=pytest.main(['tests','scripts/phase7e/test_research.py','-q','-p','no:cacheprovider','--junitxml',str(OUT/'phase7e_tests.xml')])
    suites=ET.parse(OUT/'phase7e_tests.xml').getroot().findall('testsuite')
    tests={key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ['tests','failures','errors','skipped']}
    tests['passed']=tests['tests']-tests['failures']-tests['errors']-tests['skipped']
    tests['exit_code']=int(code)
    try:
        cache_path=OUT/'phase7e_browser_validation.json'
        cached=json.loads(cache_path.read_text()) if cache_path.exists() else {}
        browser=cached if cached.get('passed') and cached.get('tested_dashboard_sha256')==sha(OUT/'phase7e_economic_dfm_dashboard.html') else check()
    except Exception as exc: browser=dict(passed=False,error=str(exc))
    count=verify(json.loads((OUT/'phase7e_protection_baseline.json').read_text()))
    manifest_path=OUT/'phase7e_run_manifest.json'
    manifest=json.loads(manifest_path.read_text())
    manifest['protected_artifacts_verified']=True
    manifest['verification_scope']='Initial snapshot through complete numerical replay, pytest and browser validation'
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf8')
    validation=dict(old,tests=tests,tests_status='PASSED' if code==0 else 'FAILED',browser_status='PASSED' if browser.get('passed') else 'FAILED',
        determinism=dict(passed=deterministic,full_pipeline_rerun=True,rerun_exit_code=rerun.returncode,n_csv_files=len(hashes),changed_numerical_files=changes,dashboard_byte_identical=sha(OUT/'phase7e_economic_dfm_dashboard.html')==dashboard),
        production_preservation=True,protected_file_count=count,
        passed=bool(code==0 and browser.get('passed') and deterministic))
    (OUT/'phase7e_validation.json').write_text(json.dumps(validation,indent=2),encoding='utf8')
    with (OUT/'phase7e_results.md').open('a',encoding='utf8') as report:
        report.write('\n## Executed validation\n\n'+f"{tests['passed']} tests passed; {tests['failures']} failures, {tests['errors']} errors, {tests['skipped']} skips. Offline Edge browser checks: {'passed' if browser.get('passed') else 'failed'}. Full-pipeline numerical and HTML reproducibility: {'passed' if deterministic else 'failed'}. All {count:,} protected prior files verified unchanged. Details: phase7e_validation.json and phase7e_browser_validation.json.\n")
    print(json.dumps(validation,indent=2))
    raise SystemExit(0 if validation['passed'] else 1)


if __name__=='__main__': main()
