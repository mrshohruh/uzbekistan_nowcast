"""Actual unit/regression tests, full diagnostic replay and final byte audit."""
import contextlib
import json
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

import pytest
from _pytest.tmpdir import TempPathFactory
from scripts.phase7f.protection import ROOT,OUT,sha,verify,active_baseline
from scripts.phase7f.browser_check import check


def validate():
    original=OUT/'phase7f_factor_selection_dashboard.html'
    if not original.exists():raise RuntimeError('Run phase7f.run first')
    before={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*.csv') if 'tmp_' not in str(p)}
    html_hash=sha(original)
    with (OUT/'phase7f_replay.log').open('w',encoding='utf8') as log:
        replay=subprocess.run([sys.executable,'-B','-m','scripts.phase7f.run','--replay'],cwd=ROOT,stdout=log,stderr=log)
    changed=[p for p,h in before.items() if sha(OUT/p)!=h]
    deterministic=replay.returncode==0 and not changed and sha(original)==html_hash
    temp=OUT/('tmp_tests_'+uuid.uuid4().hex[:8]);temp.mkdir()
    def base(self):self._basetemp=temp;return temp
    def mktemp(self,basename,numbered=True):
        p=temp/uuid.uuid4().hex[:8];p.mkdir();return p
    if sys.platform=='win32':
        TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    paths=['scripts/phase7f/test_selection.py','tests/production/test_current_dfm.py',
           'tests/production/test_configuration.py','tests/models/test_phase7d.py','scripts/phase7e/test_research.py']
    with (OUT/'phase7f_tests.log').open('w',encoding='utf8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        code=pytest.main([*paths,'-q','-p','no:cacheprovider','--junitxml',str(OUT/'phase7f_tests.xml')])
    suites=ET.parse(OUT/'phase7f_tests.xml').getroot().findall('testsuite')
    tests={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
    tests.update(passed=tests['tests']-tests['failures']-tests['errors']-tests['skipped'],exit_code=int(code),
        scope='Phase 7F scientific tests plus unchanged production configuration/DFM, Phase 7D and Phase 7E research regressions')
    try:
        cache=OUT/'phase7f_browser_validation.json'
        cached=json.loads(cache.read_text()) if cache.exists() else {}
        browser=cached if cached.get('passed') and cached.get('tested_dashboard_sha256')==sha(original) else check()
    except Exception as exc:browser=dict(passed=False,error=str(exc))
    count=verify(json.loads(active_baseline().read_text()))
    manifest_path=OUT/'phase7f_run_manifest.json';manifest=json.loads(manifest_path.read_text())
    manifest.update(protected_artifacts_verified=True,protected_file_count=count,
        protection_baseline=active_baseline().name,tests=tests,determinism_passed=deterministic,browser_passed=browser.get('passed',False))
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf8')
    audit_path=OUT/'phase7f_resumption_audit.json'
    audit=json.loads(audit_path.read_text()) if audit_path.exists() else None
    value=dict(tests=tests,determinism=dict(passed=deterministic,full_diagnostic_pipeline_replayed=True,
        replay_exit_code=replay.returncode,compared_csv_files=len(before),changed_csv_files=changed,dashboard_byte_identical=sha(original)==html_hash),
        browser=dict(passed=browser.get('passed',False),error=browser.get('error'),
            model_sample_tab_checks=len(browser.get('checks',[])),javascript_errors=browser.get('errors',[]),external_resources=browser.get('externalResources')),
        production_forecast=8.180901340616275,protected_artifacts_verified=True,protected_file_count=count,
        protection_scope='All existing files at the resumed user request baseline, except bytecode/temporary paths and Phase 7F-owned outputs/code',
        resumption_audit=audit,passed=bool(code==0 and deterministic and browser.get('passed')))
    (OUT/'phase7f_validation.json').write_text(json.dumps(value,indent=2),encoding='utf8')
    with (OUT/'phase7f_results.md').open('a',encoding='utf8') as report:
        report.write('\n## Executed validation\n\n'+f"{tests['passed']} tests passed; {tests['failures']} failures, {tests['errors']} errors, {tests['skipped']} skips. Full diagnostic CSV/HTML replay: {'passed' if deterministic else 'failed'}. Offline browser: {'passed' if browser.get('passed') else 'failed'}. {count:,} files verified unchanged against the resumed baseline.\n")
        if audit and audit['initial_to_resumed_changes']:
            report.write('\nConcurrent-workspace disclosure: Phase 7E models.py acquired an optional configuration interface between the earlier 2026-10-13 baseline and the user’s repeated 2026-10-14 request. Phase 7F did not edit that file; the original audit is retained, the changed file is preserved, and frozen Phase 7E data/forecast artifacts remain the diagnostic reference. See phase7f_resumption_audit.json.\n')
    print(json.dumps(value,indent=2))
    return 0 if value['passed'] else 1


if __name__=='__main__':raise SystemExit(validate())
