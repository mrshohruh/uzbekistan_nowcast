"""Verify existing science and production bytes, excluding only Phase 7F."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/phase7f'


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle,'sha256').hexdigest()


def capture(filename='phase7f_protection_baseline.json'):
    paths=[]
    for folder in ['src','scripts','config','registry','data','metadata','dashboard','results','docs','tests']:
        for directory,dirs,files in os.walk(ROOT/folder):
            dirs[:]=[d for d in dirs if d!='__pycache__' and not d.startswith(('pytest_tmp','tmp','.'))]
            for name in files:
                path=Path(directory)/name;rel=path.relative_to(ROOT).as_posix()
                if path.suffix!='.pyc' and not rel.startswith(('scripts/phase7f/','results/phase7f/')):
                    paths.append((rel,path))
    paths.extend((p.name,p) for p in ROOT.iterdir() if p.is_file() and (p.suffix in {'.md','.txt','.toml'} or p.name=='.gitignore'))
    with ThreadPoolExecutor(max_workers=16) as pool:
        hashes=dict(pool.map(lambda pair:(pair[0],sha(pair[1])),paths))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/filename).write_text(json.dumps(hashes,indent=2),encoding='utf8')
    return hashes


def active_baseline():
    manifest=OUT/'phase7f_run_manifest.json'
    if manifest.exists():
        saved=json.loads(manifest.read_text()).get('protection_baseline')
        if saved in {'phase7f_protection_baseline.json','phase7f_protection_resumed_baseline.json'} and (OUT/saved).exists():
            return OUT/saved
    resumed=OUT/'phase7f_protection_resumed_baseline.json'
    return resumed if resumed.exists() else OUT/'phase7f_protection_baseline.json'


def resume_capture():
    initial=json.loads((OUT/'phase7f_protection_baseline.json').read_text())
    current=capture('phase7f_protection_resumed_baseline.json')
    changes=[dict(path=p,initial_sha256=h,resumed_sha256=current.get(p)) for p,h in initial.items() if current.get(p)!=h]
    report=dict(context='User repeated the same request on 2026-10-14 after the original 2026-10-13 capture; preserve concurrent workspace changes.',
        initial_to_resumed_changes=changes,unchanged_initial_files=sum(current.get(p)==h for p,h in initial.items()),
        phase7f_modifications_confined_to=['scripts/phase7f','results/phase7f'],
        affected_source_note='Phase 7E optional configuration interface added outside this implementation; default path and frozen artifacts retained.')
    (OUT/'phase7f_resumption_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return current


def verify(hashes):
    with ThreadPoolExecutor(max_workers=16) as pool:
        changed=[v for v in pool.map(lambda pair:pair[0] if not (ROOT/pair[0]).is_file() or sha(ROOT/pair[0])!=pair[1] else None,hashes.items()) if v]
    if changed:raise ValueError('Protected files changed: '+str(changed))
    return len(hashes)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();print('Captured',len(resume_capture() if args.resume else capture()),'protected files')
