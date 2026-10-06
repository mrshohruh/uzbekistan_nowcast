"""Independent complete reruns; compare all numerical artifacts exactly."""
from scripts.phase6g1.run import ROOT,run
from scripts.phase6f.experiment import dump,sha

def main():
    out=ROOT/'results/phase6g1'
    run();before={p.name:sha(p) for p in out.glob('*.csv')}
    run();after={p.name:sha(p) for p in out.glob('*.csv')}
    dump(out/'phase6g1_determinism.json',dict(identical_csv_hashes=before==after,checked=len(before),first=before,second=after))
    if before!=after:raise ValueError('Numerical rerun mismatch')

if __name__=='__main__':main()
