"""Regenerate diagnostics/report from saved estimates, without refitting."""
import json
import numpy as np
import pandas as pd
from scripts.phase6g3.run import ROOT,OUT,csv
from scripts.phase6g3.protection import verify
from scripts.phase6g3.diagnostics import economic_diagnostics
from scripts.phase6g3.report import write_report, markdown_paragraphs
from scripts.phase6f.experiment import sha,dump
from uznowcast.models.data import load_dataset


def main():
    def read(name):return pd.read_csv(OUT/(name+'.csv'),float_precision='round_trip')
    gdp=read('nominal_gdp_growth').set_index('quarter',drop=False)
    panel=pd.read_csv(ROOT/'results/phase6c/phase6c_research_monthly_panel.csv',index_col='date',parse_dates=True,float_precision='round_trip')
    diag=economic_diagnostics(gdp,panel,load_dataset(ROOT),read('current_factor_series'));csv('target_diagnostics',diag)
    now=read('current_nowcasts')
    nominal=now.model.eq('NOMINAL_STANDALONE_LOG')
    now['conventional_yoy_pct_equivalent']=np.nan
    now.loc[nominal,'conventional_yoy_pct_equivalent']=100*np.expm1(now.loc[nominal,'nowcast']/100)
    csv('current_nowcasts',now)
    classification=write_report(read('gdp_target_audit'),gdp,read('target_model_comparison'),read('horizon_metrics'),now,read('model_failures'),diag)
    path=OUT/'phase6g3_results.md'
    extra=['\n## Verification evidence\n']
    tests=OUT/'tests.json'
    if tests.exists():
        counts=json.loads(tests.read_text());extra.append('Test results: '+str(counts)+'. Full output: tests.log and tests.xml.')
        legacy=OUT/'legacy_phase6b2_protection_diagnostic.json'
        if counts['failures'] and legacy.exists():
            details=json.loads(legacy.read_text())
            proven=[r['path'] for r in details['mismatches'] if r['preexisting_mismatch_proven_by_start_snapshot']]
            extra.append('The unchanged legacy Phase 6B.2 protection test compares today’s repository to its old phase-specific freeze and fails. Its discrepancies overlap files already different in the Phase 6G.3 starting inventory: '+str(proven)+'. Earlier phase tests/artifacts were not modified to hide this result. The Phase 6G.3 baseline protection check passes.')
    if (OUT/'tests_new.json').exists():extra.append('Final new Phase 6G.3 suite: '+str(json.loads((OUT/'tests_new.json').read_text()))+'.')
    factor=read('factor_loadings');current=factor.loc[factor.current,['indicator','factor_loading']]
    extra+=['\nAccepted current factor loadings (identical for both targets)\n','| Indicator | Loading |','|---|---:|']
    extra.extend(f'| {r.indicator} | {r.factor_loading:.6f} |' for r in current.itertuples())
    pairs=diag.loc[diag.diagnostic_type.eq('TARGET_PAIR_CORRELATION_LATEST_REVISED')&diag.indicator.eq('nominal_gdp_yoy_log')&diag.other_target.eq('real_gdp_ytd_yoy_log')]
    if len(pairs):extra.append(f'Latest-revised nominal standalone versus real cumulative log YoY correlation: {pairs.iloc[0].correlation:.6f}, N={int(pairs.iloc[0].N)}. Different reporting-period coverage limits interpretation.')
    extra.append(f'Nominal current log forecast {float(now.loc[nominal,"nowcast"].iloc[0]):.6f}% corresponds to conventional YoY growth {float(now.loc[nominal,"conventional_yoy_pct_equivalent"].iloc[0]):.6f}%.')
    extra.append('The protection inventory is supplemented with historical Phase 6B.2 paths omitted by the inherited Phase 6G.2 inventory. These supplemental hashes were captured during the audit; they are kept separately from the immutable Phase 6G.3 start snapshot. This phase’s production/model/data writers are never invoked.')
    count=verify();extra.append(f'{count} current-baseline protected artifact hashes match. No production or prior research artifact is changed.')
    path.write_text(markdown_paragraphs(path.read_text(encoding='utf8')+'\n\n'.join(extra)+'\n'),encoding='utf8')
    manifest=OUT/'run_manifest.json';m=json.loads(manifest.read_text());m.update(classification=classification,protected_artifacts=count,
        code_hashes={p.name:sha(p) for p in (ROOT/'scripts/phase6g3').glob('*.py')},outputs={p.name:sha(p) for p in OUT.glob('*.csv')})
    dump(manifest,m)


if __name__=='__main__':main()
