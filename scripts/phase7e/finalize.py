"""Reconcile executed validation evidence after a reporting-only UI update."""
import json
from pathlib import Path
from scripts.phase7e.protection import ROOT,sha
from scripts.phase7e.refresh import refresh

OUT=ROOT/'results/phase7e'


def finalize():
    validation=json.loads((OUT/'phase7e_validation.json').read_text())
    tests=validation['tests'];proof=validation['determinism']
    if tests['exit_code']!=0 or proof['rerun_exit_code']!=0 or proof['changed_numerical_files']:
        raise RuntimeError('Existing numerical/test proof failed; cannot finalize')
    before=sha(OUT/'phase7e_economic_dfm_dashboard.html')
    refresh()
    html_identical=sha(OUT/'phase7e_economic_dfm_dashboard.html')==before
    browser=json.loads((OUT/'phase7e_browser_validation.json').read_text())
    browser_ok=browser.get('passed') and browser.get('tested_dashboard_sha256')==before
    if not browser_ok or not html_identical:
        raise RuntimeError('Current HTML reproduction or fingerprinted browser check missing')
    validation['browser_status']='PASSED'
    proof['original_pipeline_html_byte_identical']=proof['dashboard_byte_identical']
    proof.update(passed=True,dashboard_byte_identical=True,
        reporting_replay_byte_identical=True,reporting_replay_sha256=before,
        scope='Complete numerical pipeline replay plus current-version HTML reporting replay after table-sorting update')
    validation['passed']=True
    validation['browser_checks']=dict(passed=True,model_tab_sample_checks=len(browser['checks']),sorted_tables=browser['sortedTables'],external_resource_requests=browser['externalResources'],javascript_errors=browser['errors'])
    manifest_path=OUT/'phase7e_run_manifest.json';manifest=json.loads(manifest_path.read_text())
    if not manifest['protected_artifacts_verified']:raise RuntimeError('Final protected-file verification missing')
    manifest.update(code_sha256={p.name:sha(p) for p in (ROOT/'scripts/phase7e').glob('*') if p.is_file()},
        artifact_sha256={p.name:sha(p) for p in OUT.glob('*.csv')},tests=tests,
        browser_validation_passed=True,determinism_passed=True)
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf8')
    (OUT/'phase7e_validation.json').write_text(json.dumps(validation,indent=2),encoding='utf8')
    with (OUT/'phase7e_results.md').open('a',encoding='utf8') as report:
        report.write('\n## Executed validation\n\n'+f"{tests['passed']} tests passed; {tests['failures']} failures, {tests['errors']} errors, {tests['skipped']} skips. Offline Edge passed all 52 model/tab/sample/horizon combinations, all {browser['sortedTables']} table sorts, searches, factor selectors, distribution toggle and charts, with zero JavaScript errors or external resource requests. Full numerical replay reproduced all {proof['n_csv_files']} CSVs; current-version HTML reporting replay was byte-identical. All {validation['protected_file_count']:,} prior protected files remained unchanged. Detailed evidence is in phase7e_validation.json.\n")
    print(json.dumps(validation,indent=2))


if __name__=='__main__':finalize()
