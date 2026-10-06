"""Attach completed tests, deterministic-refit and protected-artifact evidence."""
import json
from scripts.phase6g.run import ROOT,check_protected
from scripts.phase6f.experiment import dump,sha


def main():
    out=ROOT/'results/phase6g'
    reports=[json.loads((out/f'phase6g_tests_{scope}.json').read_text()) for scope in ['existing','new']]
    summary={k:sum(r[k] for r in reports) for k in ['tests','passed','failures','errors','skipped']}
    summary['scopes']=reports
    if summary['failures'] or summary['errors'] or summary['skipped']:
        raise ValueError('Validation is not fully passing: '+str(summary))
    deterministic=json.loads((out/'phase6g_determinism.json').read_text())
    actual={p.name:sha(p) for p in out.glob('*.csv')}
    if not deterministic['identical_csv_hashes'] or deterministic['second']!=actual:
        raise ValueError('Deterministic outputs mismatch')
    before=json.loads((out/'phase6g_protected_before.json').read_text())
    n=check_protected(ROOT,before,out)
    summary.update(deterministic_rerun_status='IDENTICAL_NUMERICAL_CSV_CHECKSUMS',numerical_csvs=len(actual),
        protected_artifact_hash_status='UNCHANGED',protected_artifacts=n,
        historical_M2_value_vintages_verified=False,evidence_class='AVAILABILITY_AWARE_PSEUDO_REAL_TIME; REVISION_VALUE_LEAKAGE_UNRESOLVED')
    dump(out/'phase6g_validation_evidence.json',summary)
    path=out/'phase6g_results.md'
    rec=json.loads((out/'phase6g_recommendation.json').read_text())
    ending=rec['classification']+'\n\n'+rec['recommendation']+'\n'
    text=path.read_text(encoding='utf8')
    if not text.endswith(ending):raise ValueError('Report final classification mismatch')
    text=text[:-len(ending)]
    # Idempotent report finalization.
    text=text.split('## Completed validation')[0].rstrip()
    evidence=(f'\n\n## Completed validation\n\n'
        f'{summary["tests"]} tests: {summary["passed"]} passed, {summary["failures"]} failures, '
        f'{summary["errors"]} errors, {summary["skipped"]} skips. '
        f'The existing Phase 6E/6F and model suite passed {reports[0]["passed"]} tests; '
        f'the new Phase 6G suite passed {reports[1]["passed"]}. '
        f'Two independent complete refits produced identical checksums for all {len(actual)} numerical CSV outputs. '
        f'All {n} protected artifact checksums remain unchanged. '
        'Completed XML, scope counts and JSON validation evidence are stored in this folder. '
        'These tests establish the stated availability rules and deterministic computation; they do not recover missing historical predictor value vintages.\n\n')
    path.write_text(text+evidence+ending,encoding='utf8')
    manifest_path=out/'phase6g_run_manifest.json'
    manifest=json.loads(manifest_path.read_text())
    manifest.update(validation=summary,report_checksum=sha(path),
        code_hashes={p.name:sha(p) for p in (ROOT/'scripts/phase6g').glob('*.py')})
    dump(manifest_path,manifest)


if __name__=='__main__':main()
