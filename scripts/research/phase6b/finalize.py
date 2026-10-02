"""Verify completed outputs, test evidence and persistent protected baseline."""
import json
import xml.etree.ElementTree as ET

import pandas as pd

from run import ROOT, OUT, DOC, protect, sha, save_json


def main():
    protect()
    required = ['results.md','run_manifest.json','model_specifications.json','pca_diagnostics.csv','factor_loadings.csv',
                'factor_series.csv','factor_stability.csv','forecasts.csv','matched_forecasts.csv','horizon_metrics.csv',
                'model_metrics.csv','quarter_level_errors.csv','benchmark_comparison.csv','combination_metrics.csv',
                'services_break_diagnostics.csv','imports_diagnostics.csv','convergence_diagnostics.csv','failed_origins.csv']
    for suffix in required:
        assert (OUT / ('phase6b_'+suffix)).is_file(), suffix
    reference = json.loads((OUT/'phase6b_determinism_reference.json').read_text())
    current = {n:sha(OUT/n) for n in reference}
    assert current == reference, 'core numeric tables changed on rerun'
    determinism = dict(numeric_tables_checked=len(reference), byte_identical=True, before=reference, after=current)
    save_json('phase6b_determinism_check.json', determinism)
    xml = ET.parse(OUT/'phase6b_test_results.xml')
    suite = xml.getroot().find('testsuite')
    tests = {k:int(suite.attrib[k]) for k in ['tests','errors','failures','skipped']}
    assert tests['errors']==tests['failures']==tests['skipped']==0
    forecasts = pd.read_csv(OUT/'phase6b_forecasts.csv')
    assert not forecasts.duplicated(['model','target_quarter','horizon','lag_mode']).any()
    assert forecasts.prediction.notna().sum() == 528
    assert forecasts.loc[forecasts.prediction.notna(),'n_GDP_quarters'].min() >= 12
    assert set(forecasts.evidence_class) == {'CALENDAR_PSEUDO_REAL_TIME_RESEARCH'}
    states = pd.read_csv(OUT/'phase6b_factor_series.csv')
    assert not states.loc[states.forecast_eligible.eq(True),'factor_source'].str.contains('SMOOTHED').any()
    manifest = json.loads((OUT/'phase6b_run_manifest.json').read_text())
    manifest['test_results'] = tests
    manifest['determinism_verification'] = dict(numeric_tables_checked=len(reference), byte_identical=True)
    manifest['two_factor_status'] = 'NOT_ESTIMABLE_WITH_CURRENT_SAMPLE'
    manifest['phase6b_classification'] = 'PROMISING_RESEARCH_CHALLENGER: primary equal-weight combination; standalone evidence mixed'
    manifest['model_classifications'] = pd.read_csv(OUT/'phase6b_classifications.csv').to_dict('records')
    manifest['code_hashes'] = {p.name:sha(p) for p in (ROOT/'scripts/research/phase6b').glob('*.py')}
    verification = f"\n\nFinal verification: **{tests['tests']} tests passed**, no failures/skips. **{len(reference)} core numeric tables byte-identical across reruns**. **{len(protect())} protected artifacts unchanged**. Test XML and determinism hashes are saved beside the manifest.\n"
    for path in [OUT/'phase6b_results.md', DOC/'phase6b_dfm_feasibility_report.md']:
        content = path.read_text(encoding='utf-8')
        if '\n\nFinal verification:' in content:
            content = content.split('\n\nFinal verification:')[0]
        path.write_text(content+verification, encoding='utf-8')
    manifest['output_hashes'] = {p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name not in
                               ['phase6b_run_manifest.json','phase6b_pipeline.log']}
    manifest['report_hash'] = sha(DOC/'phase6b_dfm_feasibility_report.md')
    manifest['dashboard_hash'] = sha(ROOT/'dashboard/phase6b_dfm_research.html')
    save_json('phase6b_run_manifest.json',manifest)
    protect()


if __name__ == '__main__':
    main()
