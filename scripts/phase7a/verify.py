"""Independently rerun the unchanged production fit from its frozen snapshot."""
import json
import numpy as np
from scripts.phase6i.run import ROOT,current_inputs
from scripts.production.models import fit_info
from uznowcast.models.data import load_dataset

def verify():
    _,_,info,origin,current,snapshot=current_inputs(load_dataset(ROOT))
    fit=fit_info(info,ROOT,origin)
    expected={'dfm':current['dfm_forecast'],'umidas':current['umidas_forecast'],'final':current['final_forecast']}
    checks={k:dict(recomputed=fit[k],frozen=v,error=fit[k]-v,exact_float_equal=fit[k]==v) for k,v in expected.items()}
    for k,v in expected.items():
        if not np.isclose(fit[k],v,rtol=0,atol=1e-12): raise ValueError('Production reproduction failed: '+k)
    result=dict(snapshot=snapshot,origin=str(origin),checks=checks,tolerance=1e-12,passed=True)
    (ROOT/'results/phase7a/production_reproduction.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=='__main__':verify()
