"""Repeat the complete experiment and compare deterministic scientific artifacts."""
import subprocess,sys,json
from scripts.phase6g4.run import OUT,ROOT,verify
from scripts.phase6f.experiment import sha,dump

def main():
    paths=sorted(OUT.glob('phase6g4_*.csv'))+[OUT/'phase6g4_results.md',OUT/'phase6g4_run_manifest.json']
    before={p.name:sha(p) for p in paths}
    with (OUT/'phase6g4_rerun.log').open('w',encoding='utf8') as log:
        result=subprocess.run([sys.executable,'-m','scripts.phase6g4.run'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError('Rerun failed; see phase6g4_rerun.log')
    after={p.name:sha(p) for p in paths};different=[p for p in before if before[p]!=after[p]]
    dump(OUT/'phase6g4_determinism.json',dict(identical=not different,files_checked=len(paths),different=different,hashes=after))
    verify()
    if different:raise RuntimeError('Scientific artifacts changed on rerun: '+str(different))
    print(f'Deterministic rerun: {len(paths)} identical artifacts; protected files unchanged.')

if __name__=='__main__':main()
