"""Compare all scientific artifacts against the preserved old-seal build."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
def compare(candidate='new_candidate'):
    p=ROOT/'results/repository_cleanup/phase6h1';a=p/'old_baseline';b=p/candidate
    rows=[]
    for f in a.iterdir():
        if f.suffix not in ('.csv','.json','.html') or f.name in ('phase6e_run_manifest.json','phase6e_production_policy.json'):continue
        g=b/f.name.removeprefix('phase6e_')
        rows.append(dict(file=g.name,exact=g.exists() and f.read_bytes()==g.read_bytes()))
    y=json.loads((b/'current_nowcast.json').read_text(encoding='utf-8'))
    result=dict(passed=all(v['exact'] for v in rows),scientific_outputs=rows,
        forecasts={k:y[k] for k in ['dfm_forecast','umidas_forecast','final_forecast']},
        exclusions=['Run manifest and policy code namespace/seal hashes only'])
    (p/'scientific_comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result
if __name__=='__main__':
    result=compare();print(json.dumps(result));raise SystemExit(int(not result['passed']))
