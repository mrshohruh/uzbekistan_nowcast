"""Collect independently verified tests and refresh reports from saved forecasts."""
import json
import xml.etree.ElementTree as ET

import pandas as pd

from run import ROOT, OUT, sha
from audit import assert_protected
from report import report


def main():
    # The combined exploratory invocation passed all 261 repository tests,
    # but prior phases' bare `run` imports collided. Those research suites
    # were subsequently rerun in independent processes without changing tests.
    xml = OUT / 'phase6c_all_tests.xml'
    cases = [c for c in ET.parse(xml).getroot().iter('testcase') if c.get('classname','').startswith('tests.')]
    counts = dict(tests=len(cases), errors=sum(c.find('error') is not None for c in cases),
                  failures=sum(c.find('failure') is not None for c in cases), skipped=sum(c.find('skipped') is not None for c in cases))
    counts['passed'] = counts['tests']-counts['errors']-counts['failures']-counts['skipped']
    counts['scope'] = 'repository'
    counts['source'] = 'phase6c_all_tests.xml; repository testcases only'
    counts['exit_code'] = int(bool(counts['errors'] or counts['failures']))
    components = [counts] + [json.loads((OUT / f'phase6c_{s}_test_results.json').read_text()) for s in ['new','phase6b','phase6b1','phase6b2']]
    assert all(c['exit_code']==0 for c in components)
    result = {k: sum(c[k] for c in components) for k in ['tests','passed','errors','failures','skipped']}
    result.update(exit_code=0, components=components)
    (OUT / 'phase6c_test_results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    before = json.loads((OUT / 'phase6c_protected_before.json').read_text())
    checks = assert_protected(ROOT, before)
    protocol = json.loads((OUT / 'phase6c_protocol.json').read_text())
    report(OUT, protocol, pd.read_csv(OUT / 'phase6c_predictor_audit.csv'),
           pd.read_csv(OUT / 'phase6c_forecasts.csv'), pd.read_csv(OUT / 'phase6c_horizon_metrics.csv'), checks)
    manifest = json.loads((OUT / 'phase6c_run_manifest.json').read_text())
    manifest.update(tests=result, determinism=json.loads((OUT / 'phase6c_determinism_checks.json').read_text()),
                    outputs={p.name:sha(p) for p in OUT.glob('*.csv')})
    (OUT / 'phase6c_run_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__=='__main__':
    main()
