"""Restore explicitly listed, checksum-verified external data into a checkout."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from concurrent.futures import ThreadPoolExecutor

def canonical(path: Path) -> Path:
    """Resolve links and normalize equivalent Windows extended-path spelling."""
    value=str(path.resolve())
    if value.startswith('\\\\?\\UNC\\'):
        value='\\\\'+value[8:]
    elif value.startswith('\\\\?\\'):
        value=value[4:]
    return Path(value)

def restore(source_root: Path, target_root: Path):
    source_root=canonical(source_root);target_root=canonical(target_root)
    manifest=json.loads((target_root/'config/bootstrap_inputs.json').read_text(encoding='utf-8'))
    def copy_entry(entry):
        rel,expected=entry
        source=canonical(source_root/rel);target=canonical(target_root/rel)
        if not source.is_relative_to(source_root) or not target.is_relative_to(target_root):
            raise ValueError('Unsafe bootstrap path: '+rel)
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=expected:
            raise ValueError('Missing or changed bootstrap input: '+rel)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        return 1
    with ThreadPoolExecutor(max_workers=16) as pool:
        return sum(pool.map(copy_entry,manifest['files'].items()))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',required=True,type=Path)
    parser.add_argument('--target-root',type=Path,default=Path(__file__).resolve().parents[2])
    args=parser.parse_args()
    print(json.dumps({'restored_files':restore(args.source_root,args.target_root)}))
