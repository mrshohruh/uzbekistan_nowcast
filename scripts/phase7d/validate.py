"""Reconcile full-suite results with final tests of generated research artifacts."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/phase7d'


def cases(path):
    root=ET.parse(path).getroot();result={}
    for item in root.iter('testcase'):
        status='failures' if item.find('failure') is not None else 'errors' if item.find('error') is not None else 'skipped' if item.find('skipped') is not None else 'passed'
        result[(item.attrib.get('classname'),item.attrib['name'])]=status
    return result


def summarize(result):
    return dict(tests=len(result),**{key:list(result.values()).count(key) for key in ['passed','failures','errors','skipped']})


def main():
    full=cases(OUT/'phase7d_tests.xml');final=cases(OUT/'phase7d_final_tests.xml')
    all_cases=dict(full);all_cases.update(final)
    result=dict(summarize(all_cases),full_suite=summarize(full),final_phase7d=summarize(final),
        scope='Full existing suite followed by final Phase 7D tests; identical test IDs reconciled using latest result',
        passed_all=all(v=='passed' for v in all_cases.values()))
    (OUT/'phase7d_validation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))
    if not result['passed_all']:raise RuntimeError('A test remains failed, errored or skipped')


if __name__=='__main__':main()
