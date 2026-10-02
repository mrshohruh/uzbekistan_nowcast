"""Repeat isolated computations and record deterministic output verification."""
import sys
import json
import subprocess
from pathlib import Path
from run import ROOT,OUT,sha,protect

def execute(script,log):
    with (OUT/log).open('w',encoding='utf-8') as stream:
        subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)

def main():
    protect()
    factor_names=['phase6b2_factor_series.csv','phase6b2_factor_core_identity_checks.csv']
    factor_before={n:sha(OUT/n) for n in factor_names}
    execute('scripts/research/phase6b2/factors.py','phase6b2_factor_rerun.log')
    assert factor_before=={n:sha(OUT/n) for n in factor_names},'Factor rerun is not byte-deterministic'
    execute('scripts/research/phase6b2/run.py','phase6b2_verified_run.log')
    before={p.name:sha(p) for p in OUT.glob('phase6b2_*.csv')}
    execute('scripts/research/phase6b2/run.py','phase6b2_deterministic_rerun.log')
    after={p.name:sha(p) for p in OUT.glob('phase6b2_*.csv')}
    assert before==after,'CSV outputs changed on identical-input rerun'
    record=dict(factor_outputs_identical=True,all_csv_outputs_identical=True,CSV_outputs=len(before),
                sha256=after,protected_files=protect(),protected_status='UNCHANGED')
    (OUT/'phase6b2_determinism_checks.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k!='sha256'},indent=2))

if __name__=='__main__':
    main()
