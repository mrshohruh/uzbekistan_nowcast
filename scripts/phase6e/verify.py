"""Independent model refit and byte-level output reconstruction verification."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]


def main():
    out=ROOT/'results/phase6e'
    subprocess.run([sys.executable,'-m','scripts.phase6e.run','--output-dir',str(out/'rerun'),'--no-publish'],cwd=ROOT,check=True)
    before=json.loads((out/'phase6e_run_manifest.json').read_text(encoding='utf8'))
    after=json.loads((out/'rerun/phase6e_run_manifest.json').read_text(encoding='utf8'))
    differences=[name for name,h in before['outputs'].items() if after['outputs'].get(name)!=h]
    if before['dashboard_sha256']!=after['dashboard_sha256']:differences.append('dashboard')
    result=dict(status='FAIL' if differences else 'PASS',differences=differences,
                compared_outputs=len(before['outputs'])+1,fresh_output_directory='results/phase6e/rerun',
                method='Independent fit from scratch; byte-identical generated CSV/JSON/report/dashboard')
    (out/'phase6e_determinism.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))
    return int(bool(differences))


if __name__=='__main__':sys.exit(main())
