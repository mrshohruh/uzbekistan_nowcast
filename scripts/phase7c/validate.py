"""Targeted and production regression tests plus independent deterministic refits."""
from pathlib import Path
import sys,json,subprocess
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.dont_write_bytecode=True

def run():
    out=ROOT/'results/phase7c'
    result=subprocess.run([sys.executable,'-B','-m','scripts.phase7c.test_runner'],cwd=ROOT)
    from scripts.phase7c.run import audit,sha
    from scripts.phase7c.models import estimate,CACHE
    from scripts.phase6i.run import current_inputs
    from uznowcast.models.data import load_dataset
    ds=load_dataset(ROOT);candidate,delays,_,_=audit(ds);cd,g,info,origin,_,_=current_inputs(ds)
    panel=pd.DataFrame(info['panel']).set_index('month').astype(float);panel.index=pd.to_datetime(panel.index)
    checks=[]
    for field in ['retail_trade','construction','imports_total','retail_cpi_approx']:
        fits=[]
        for _ in range(2):
            CACHE.clear()
            try:fits.append(estimate(panel,cd,g,info['target'],info['horizon'],origin,candidate,(field,),delays))
            except ValueError as e:fits.append(str(e))
        a,b=fits
        if isinstance(a,str) or isinstance(b,str):checks.append(dict(indicator=field,prediction_equal=a==b,factors_equal=a==b,loadings_equal=a==b,status='DETERMINISTIC_NON_ESTIMABLE',reason=a))
        else:checks.append(dict(indicator=field,prediction_equal=a[0]==b[0],factors_equal=a[1].equals(b[1]),loadings_equal=np.array_equal(a[2],b[2]),status='DETERMINISTIC_ESTIMABLE'))
    manifest=json.loads((out/'run_manifest.json').read_text())
    from concurrent.futures import ThreadPoolExecutor
    def verify(item):
        p,h=item
        return p if not (ROOT/p).exists() or sha(ROOT/p)!=h else None
    with ThreadPoolExecutor(max_workers=8) as pool:changed=[p for p in pool.map(verify,manifest['protected_sha256'].items()) if p]
    validation=dict(pytest_exit_code=result.returncode,deterministic_refits=checks,protected_files_changed=changed,protected_files_unchanged=not changed)
    (out/'validation.json').write_text(json.dumps(validation,indent=2))
    manifest['validation']=validation
    manifest['artifact_sha256']={p.name:sha(p) for p in out.glob('*') if p.is_file() and p.name not in ['run_manifest.json','pipeline.log']}
    (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2))
    if result.returncode or changed or not all(all(c[k] for k in ['prediction_equal','factors_equal','loadings_equal']) for c in checks):raise ValueError('Validation failed; see tests.log / validation.json')
    print(json.dumps(validation,indent=2))
if __name__=='__main__':run()
