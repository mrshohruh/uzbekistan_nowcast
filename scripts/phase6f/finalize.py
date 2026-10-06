"""Attach actual validation evidence without modifying numerical artifacts."""
import json
import xml.etree.ElementTree as ET
import pandas as pd
from scripts.phase6f.experiment import ROOT, sha, dump


def main():
    out=ROOT/'results/phase6f'
    scopes=[]
    for filename in ['phase6f_test_results.xml','phase6f_corrected_test_results.xml']:
        path=out/filename
        if not path.exists():
            raise ValueError('Missing completed test evidence: '+filename)
        cases=list(ET.parse(path).getroot().iter('testcase'))
        scopes.append(dict(file=filename,tests=len(cases),failures=sum(c.find('failure') is not None for c in cases),
            errors=sum(c.find('error') is not None for c in cases),skipped=sum(c.find('skipped') is not None for c in cases)))
    # The initial full suite used the pre-fix test date parser. Require all its
    # failures to be exactly that test, and a fully passing corrected rerun.
    first=list(ET.parse(out/'phase6f_test_results.xml').getroot().iter('testcase'))
    unresolved=[c.attrib for c in first if c.find('error') is not None or
                (c.find('failure') is not None and c.get('name')!='test_no_false_real_time_claims_or_timing_leaks')]
    if unresolved or scopes[-1]['failures'] or scopes[-1]['errors'] or scopes[-1]['skipped']:
        raise ValueError('Unresolved test failures: '+str(unresolved))
    before=json.loads((out/'phase6f_protected_before.json').read_text())
    after=json.loads((out/'phase6f_protected_after.json').read_text())
    if before!=after or any(sha(ROOT/p)!=h for p,h in before.items()):
        raise ValueError('Protected artifact changed')
    det=json.loads((out/'phase6f_determinism.json').read_text())
    now={p.name:sha(p) for p in out.glob('*.csv')}
    if not det['identical_csv_hashes'] or now!=det['second']:
        raise ValueError('Current outputs do not match deterministic reruns')
    summary=dict(scopes=scopes,unresolved_failures=0,corrected_failure='Mixed fractional-second timestamps in test date parser; fixed with explicit pandas mixed-format parsing',
        protected_artifacts=len(before),protected_unchanged=True,identical_numerical_csvs=len(now))
    dump(out/'phase6f_validation_evidence.json',summary)
    path=out/'phase6f_results.md'
    report=path.read_text(encoding='utf8').rsplit('\n\nPHASE6F_INCONCLUSIVE',1)[0]
    b=pd.read_csv(out/'phase6f_bridge_coefficients.csv');b=b.loc[b.current]
    vif=b.groupby('model').vif.max()
    d=pd.read_csv(out/'phase6f_dfm_diagnostics.csv');d=d.loc[d.current & d.field.eq('m2')].set_index('model')
    paragraph=(f'\n\n## Completed validation and diagnostic interpretation\n\n'
        f'M0 also serves as B0, the unchanged benchmark bridge. Current B1 VIF {vif.B1:.2f} '
        f'versus M0 {vif.M0:.2f}: explicitly adding M2 while retaining M2 in factor extraction creates substantial redundancy. '
        f'Current B2 VIF {vif.B2:.2f}. Do not automatically retain the duplicate M2 channel. '
        f'M1 and M2 factors correlate {d.loc["M1","factor_correlation_vs_M0"]:.4f} and '
        f'{d.loc["M2","factor_correlation_vs_M0"]:.4f} with M0; current M2 loadings are '
        f'{d.loc["M0","loading"]:.4f}, {d.loc["M1","loading"]:.4f}, {d.loc["M2","loading"]:.4f}. '
        'Factor/GDP-AR slopes remain positive in M0/M1/M2. Explicit bridge M2 makes the factor slope change sign, consistent with the VIF warning. '
        'Historical B5 has much lower collinearity than B3, but its FDI improvement still lacks verified historical value vintages.\n\n'
        f'The complete requested relevant suite executed {scopes[0]["tests"]} tests. '
        'Its one Phase 6F test initially failed because pandas inferred a timestamp format without fractional seconds. '
        f'That parser was corrected; all {scopes[1]["tests"]} Phase 6F tests then passed without skips. '
        f'Unresolved failures: 0. Windows sandbox temporary-directory errors were resolved by running the offline suite outside the sandbox. '
        f'Independent reruns matched all {len(now)} numerical CSV checksums exactly. '
        f'All {len(before)} protected artifact hashes remain unchanged. XML and JSON evidence are in this folder.\n\n'
        'PHASE6F_INCONCLUSIVE\n\nKEEP_PHASE6E_PRODUCTION\n')
    path.write_text(report+paragraph,encoding='utf8')
    manifest=json.loads((out/'phase6f_run_manifest.json').read_text())
    manifest['validation']=summary
    manifest['code_hashes']={p.name:sha(p) for p in (ROOT/'scripts/phase6f').glob('*.py')}
    manifest['report_checksum']=sha(path)
    dump(out/'phase6f_run_manifest.json',manifest)


if __name__=='__main__':
    main()
