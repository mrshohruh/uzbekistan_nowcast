"""Close the audit only after exact reruns and both offline suites pass."""
import json
from scripts.phase6g1.run import ROOT
from scripts.phase6f.experiment import dump,sha

def main():
    out=ROOT/'results/phase6g1'
    suites=[json.loads((out/f'phase6g1_tests_{scope}.json').read_text()) for scope in ['existing','new']]
    assert all(s['exit_code']==0 and s['failures']==0 and s['errors']==0 and s['skipped']==0 for s in suites)
    rerun=json.loads((out/'phase6g1_determinism.json').read_text())
    assert rerun['identical_csv_hashes'] and rerun['first']==rerun['second']
    assert all(sha(out/name)==digest for name,digest in rerun['second'].items())
    protected=json.loads((out/'phase6g1_protected_before.json').read_text())
    assert all(sha(ROOT/name)==digest for name,digest in protected.items())
    validation=dict(tests_passed=sum(s['passed'] for s in suites),suites=suites,
        deterministic_csv_count=rerun['checked'],protected_files_unchanged=len(protected),research_only=True)
    dump(out/'phase6g1_validation.json',validation)
    report=out/'phase6g1_results.md';text=report.read_text(encoding='utf-8')
    marker='M2 DIAGNOSIS:'
    evidence=f"Validation completed: {validation['tests_passed']} offline tests passed, {rerun['checked']} numerical CSV artifacts identical across two complete reruns, and {len(protected)} protected files unchanged. Publication-mask checks passed; historical predictor-value vintage leakage remains unresolved. See phase6g1_validation.json and phase6g1_determinism.json.\n\n"
    if evidence not in text:text=text.replace(marker,evidence+marker)
    report.write_text(text,encoding='utf-8')
    manifest=json.loads((out/'phase6g1_run_manifest.json').read_text())
    manifest['validation']=validation
    manifest['code_hashes']={p.name:sha(p) for p in (ROOT/'scripts/phase6g1').glob('*.py')}
    manifest['outputs']={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='phase6g1_run_manifest.json'}
    dump(out/'phase6g1_run_manifest.json',manifest)

if __name__=='__main__':main()
