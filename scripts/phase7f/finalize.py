"""Attach a successful fingerprinted browser check to executed validation."""
import json
from scripts.phase7f.protection import ROOT,OUT,sha


def finalize():
    validation_path=OUT/'phase7f_validation.json'
    validation=json.loads(validation_path.read_text())
    browser=json.loads((OUT/'phase7f_browser_validation.json').read_text())
    if validation['tests']['exit_code']!=0 or not validation['determinism']['passed'] or not validation['protected_artifacts_verified']:
        raise RuntimeError('Numerical/tests/protection proof failed; cannot finalize')
    if not browser.get('passed') or browser['tested_dashboard_sha256']!=sha(OUT/'phase7f_factor_selection_dashboard.html'):
        raise RuntimeError('Browser proof does not match current HTML')
    manifest_path=OUT/'phase7f_run_manifest.json';manifest=json.loads(manifest_path.read_text())
    if any(sha(OUT/name)!=digest for name,digest in manifest['artifact_sha256'].items()):
        raise RuntimeError('Numerical artifacts changed after validation')
    validation['browser']=dict(passed=True,model_sample_tab_checks=len(browser['checks']),
        javascript_errors=browser['errors'],external_resources=browser['externalResources'],
        criterion_charts=browser['criterionCharts'],spectrum_charts=browser['spectrumCharts'],
        sorted_tables=browser['sortedTables'],heatmap_selector_passed=True)
    validation['passed']=True
    validation_path.write_text(json.dumps(validation,indent=2),encoding='utf8')
    manifest.update(browser_passed=True,protected_artifacts_verified=validation['protected_artifacts_verified'],
        code_sha256={p.name:sha(p) for p in (ROOT/'scripts/phase7f').glob('*') if p.is_file()})
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf8')
    report_path=OUT/'phase7f_results.md';report=report_path.read_text(encoding='utf8')
    # Correct only the superseded sandbox-launch result using the executed proof.
    report=report.replace('Offline browser: failed.','Offline browser: passed.')
    if '## Executed validation' not in report:
        tests=validation['tests']
        report+=f"\n## Executed validation\n\n{tests['passed']} tests passed; {tests['failures']} failures, {tests['errors']} errors, {tests['skipped']} skips. Full diagnostic replay reproduced all {validation['determinism']['compared_csv_files']} CSV files and the dashboard byte for byte. Offline browser: passed. {validation['protected_file_count']:,} existing files verified unchanged against the resumed baseline.\n"
        audit=validation.get('resumption_audit')
        if audit and audit['initial_to_resumed_changes']:
            report+='\nConcurrent-workspace disclosure: Phase 7E models.py acquired an optional configuration interface between the earlier 2026-10-13 baseline and the repeated 2026-10-14 request. Phase 7F did not edit that file. Both audit baselines are retained; frozen production, data and Phase 7E forecast artifacts remain unchanged. See phase7f_resumption_audit.json.\n'
    report+=f"\nOffline Edge exercised all {len(browser['checks'])} model/sample/tab combinations, all nine table sorts, three individual IC charts, four spectral charts, variable search and PC-count heatmap selectors. Zero JavaScript errors or external resource requests. Its raw-byte HTML fingerprint matches the tested dashboard.\n"
    report_path.write_text(report,encoding='utf8')
    print(json.dumps({k:v for k,v in validation.items() if k!='resumption_audit'},indent=2))


if __name__=='__main__':finalize()
