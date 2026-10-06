"""Read-only inventory of production and preceding research artifacts."""
import json
from pathlib import Path
from scripts.phase6g2.run import hashes as previous_hashes
from scripts.phase6f.experiment import sha, dump

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/phase6g3'


def snapshot():
    OUT.mkdir(exist_ok=True)
    hashes=previous_hashes()
    for folder in ['scripts/phase6g2','results/phase6g2']:
        for p in (ROOT/folder).glob('*'):
            if p.is_file():hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    historic=json.loads((ROOT/'results/research/phase6b2/phase6b2_protected_before.json').read_text())
    for name in historic:
        if (ROOT/name).is_file():hashes.setdefault(name,sha(ROOT/name))
    dump(OUT/'protected_before.json',hashes)


def verify():
    before=json.loads((OUT/'protected_before.json').read_text())
    extra=OUT/'protected_supplemental_before.json'
    if extra.exists():before.update(json.loads(extra.read_text()))
    after={p:sha(ROOT/p) if (ROOT/p).is_file() else None for p in before}
    dump(OUT/'protected_after.json',after)
    changed=[p for p in before if before[p]!=after[p]]
    if changed:raise ValueError('Protected artifacts changed: '+str(changed))
    return len(before)


if __name__=='__main__':snapshot()
