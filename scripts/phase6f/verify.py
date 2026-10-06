"""Two independent executions must produce identical numerical CSV artifacts."""
from scripts.phase6f.experiment import ROOT, run, sha, dump


def main():
    out=ROOT/'results/phase6f'
    run()
    before={p.name:sha(p) for p in out.glob('*.csv')}
    run()
    after={p.name:sha(p) for p in out.glob('*.csv')}
    dump(out/'phase6f_determinism.json',dict(identical_csv_hashes=before==after,
        checked=len(before), first=before, second=after))
    if before!=after:
        raise ValueError('Numerical CSV rerun differs')


if __name__=='__main__':
    main()
