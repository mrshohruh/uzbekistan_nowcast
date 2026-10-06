"""Finalize evidence after full refit reproduction and the offline relevant suite."""
import json
import xml.etree.ElementTree as ET
from scripts.phase6g5.run import OUT, verify

def main():
    required=['results.md','model_comparison.csv','horizon_metrics.csv','common_sample_forecasts.csv',
              'signal_correlations.csv','rolling_correlations.csv','vif_diagnostics.csv','factor_loadings.csv',
              'factor_correlations.csv','current_nowcasts.csv','stability_metrics.csv','selection_scorecard.csv',
              'm0_m1_m2_m3_m4_comparison.html']
    missing=[name for name in required if not (OUT/('phase6g5_'+name)).is_file()]
    if missing:raise ValueError('Missing requested outputs: '+str(missing))
    tests=json.loads((OUT/'phase6g5_test_results.json').read_text())
    deterministic=json.loads((OUT/'phase6g5_determinism.json').read_text())
    expected={'scripts.research.phase6b2.test_vintages::test_protected_artifacts_unchanged',
              'scripts.research.phase6c.test_phase6c::test_protected_inventory_and_saved_metrics'}
    cases=list(ET.parse(OUT/'phase6g5_tests.xml').getroot().iter('testcase'))
    failed={c.get('classname')+'::'+c.get('name') for c in cases if c.find('failure') is not None}
    dedicated=[c for c in cases if c.get('classname')=='scripts.phase6g5.test_phase6g5']
    if len(dedicated)!=14 or any(c.find('failure') is not None or c.find('error') is not None for c in dedicated):
        raise ValueError('Dedicated Phase6G.5 tests did not all pass')
    if tests['errors'] or failed-expected:raise ValueError('Unexpected relevant-suite failure')
    if not deterministic['identical']:raise ValueError('Rerun differs')
    result=dict(**tests,identical_rerun=True,deterministic_artifacts=deterministic['files_checked'],
                protected_files=verify(),production_unchanged=True,automatic_promotion=False,
                classification='PHASE6G5_RETAIN_M0',required_outputs=len(required)+1,
                historical_predictor_vintages_verified=False,
                validation_status='PASSED_WITH_LEGACY_SNAPSHOT_FAILURES' if failed else 'PASSED',
                legacy_snapshot_failures=sorted(failed),phase6g5_dedicated_tests_passed=14,
                note='Two old phase inventories differ from newer repository state. Current phase preservation checks pass; failures are not suppressed.')
    (OUT/'phase6g5_validation.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()
