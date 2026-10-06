"""Two complete independent refits must generate identical numerical outputs."""
from scripts.phase6g.run import ROOT,run
from scripts.phase6f.experiment import sha,dump


def main():
    out=ROOT/'results/phase6g'
    run()
    before={p.name:sha(p) for p in out.glob('*.csv')}
    run()
    after={p.name:sha(p) for p in out.glob('*.csv')}
    dump(out/'phase6g_determinism.json',dict(identical_csv_hashes=before==after,checked=len(before),first=before,second=after,
        evidence_class='AVAILABILITY_AWARE_PSEUDO_REAL_TIME; REVISION_VALUE_LEAKAGE_UNRESOLVED'))
    if before!=after:raise ValueError('Independent numerical refits differ')


if __name__=='__main__':main()
