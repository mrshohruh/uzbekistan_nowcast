"""Production V2 source-update entry point, preserving legacy transactional operations."""
import subprocess
import sys
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def main():
    # Existing operations retain raw archives, bounded retries, release gates,
    # transaction journals, legacy predictions and frozen challenger snapshots.
    command=[sys.executable,'-m','scripts.operations.run_update',*sys.argv[1:]]
    subprocess.run(command,cwd=ROOT,check=True)
    if any(flag in sys.argv for flag in ['--check-only','--dry-run','--as-of']):return
    active=ROOT/'results/operations/current_production.json'
    if active.exists():
        pointer=json.loads(active.read_text(encoding='utf8'))
        policy=json.loads((ROOT/pointer['policy']).read_text(encoding='utf8'))
        if policy.get('production_version')!='V2' or policy.get('status')!='PHASE6E_PROMOTED':return
    subprocess.run([sys.executable,'-m','scripts.production.run'],cwd=ROOT,check=True)


if __name__=='__main__':main()
