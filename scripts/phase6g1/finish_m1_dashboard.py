"""Validate saved evidence and print the requested research completion record."""
import json
import xml.etree.ElementTree as ET
from scripts.phase6g1.m1_dashboard import ROOT,OUT,FILES
from scripts.phase6f.experiment import sha,dump

def main():
    path=OUT/'phase6g1_m1_driver_validation.json';v=json.loads(path.read_text())
    suites=list(ET.parse(OUT/'phase6g1_m1_driver_tests.xml').getroot().iter('testsuite'))
    assert all(int(s.get(k,0))==0 for s in suites for k in ['errors','failures','skipped'])
    passed=sum(int(s.get('tests',0)) for s in suites)
    assert passed>=37 and v['deterministic_two_complete_reruns'] and v['production_unchanged']
    assert all(sha(ROOT/name)==digest for name,digest in v['output_hashes'].items())
    protected=json.loads((OUT/'phase6g1_protected_before.json').read_text())
    assert all(sha(ROOT/name)==digest for name,digest in protected.items())
    v['tests_passed']=passed;v['test_xml_checksum']=sha(OUT/'phase6g1_m1_driver_tests.xml')
    dump(path,v)
    models={r['model']:r for r in v['models']}
    lines=['PHASE6G1_M1_DRIVER_ANALYSIS_COMPLETE']
    for model in models:lines.append(f"{model} DFM nowcast: {models[model]['dfm_nowcast']:.9f}%")
    for model in models:lines.append(f"{model} 50/50: {models[model]['ensemble_50_50']:.9f}%")
    for model in ['M1','M2']:lines.append(f"{model} pooled RMSE: {models[model]['pooled_RMSE']:.9f}")
    for challenger,base in [('M1','M0'),('M2','M0'),('M2','M1')]:
        lines.append(f"{challenger} improvement vs {base}: {models[base]['pooled_RMSE']-models[challenger]['pooled_RMSE']:.9f} pp")
    for model in ['M1','M2']:
        m=v[model+'_M2_driver']
        lines += [f"{model} M2 signal: {m['signal']:.12f}",f"{model} M2 signal share: {m['signal_share_pct']:.9f}%",
                  f"{model} M2 loading: {m['loading']:.12f}",f"{model} M2 loading share: {m['loading_share_pct']:.9f}%"]
    for model in ['M1','M2']:lines.append(f"{model} largest current signal: {models[model]['largest_signal_indicator']}")
    lines += ['POS status: NA / Unavailable; excluded from signal-share denominator',
              f'M1 dashboard path: {FILES[3]}',f'M0/M1/M2 comparison dashboard path: {FILES[4]}','CSV paths:']
    lines += [str(p) for p in FILES[:3]]
    lines += [f'tests passed: {passed}','determinism status: five output hashes identical across two complete reruns',
              f"protected production artifacts unchanged: YES ({v['protected_files_unchanged']} prior artifacts checked)",
              'FINAL DECISION:','RESEARCH_ONLY','PHASE6E_PRODUCTION_UNCHANGED']
    print('\n'.join(lines))

if __name__=='__main__':main()
