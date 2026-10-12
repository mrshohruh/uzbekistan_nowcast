"""Independent deterministic refit check of the current S1 research specification."""
from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from scripts.phase6i.run import current_inputs
from scripts.phase7b.data import parse,transform
from scripts.phase7b.models import estimate,CACHE
from uznowcast.models.data import load_dataset

def run():
    ds=load_dataset(ROOT);cd,g,info,origin,_,_=current_inputs(ds)
    panel=pd.DataFrame(info['panel']).set_index('month').astype(float);panel.index=pd.to_datetime(panel.index)
    sat=transform(parse(ROOT/'data/research/satellite/input/uzbekistan_nightlights_monthly.csv'))
    fits=[]
    for _ in range(2):
        CACHE.clear();fits.append(estimate(panel,cd,g,info['target'],info['horizon'],origin,sat,('NTL_YOY',),0))
    a,b=fits;checks=dict(prediction_equal=a[0]==b[0],loadings_equal=np.array_equal(a[3],b[3]),factors_equal=a[2].equals(b[2]),forecast=a[0])
    if not all(checks[k] for k in ['prediction_equal','loadings_equal','factors_equal']):raise ValueError('Non-deterministic research fits')
    (ROOT/'results/phase7b/determinism.json').write_text(json.dumps(checks,indent=2))
    print(checks)
if __name__=='__main__':run()
