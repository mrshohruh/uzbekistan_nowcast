"""Remove only disposable validation workspaces created after the Phase 6H baseline."""
import csv
import json
from pathlib import Path
import shutil
from scripts.maintenance.repository_freeze import ROOT, OUT, checksum, git, table, write


def main():
    baseline=json.loads((OUT/'pre_cleanup_manifest.json').read_text())
    exclusions=set(s.removeprefix('Inventory traversal excluded (not deleted): ') for s in baseline['inventory_errors'])
    with (OUT/'file_inventory_before.csv').open(encoding='utf-8') as handle:
        original={r['path'] for r in csv.DictReader(handle)}
    tracked=set(git('ls-files','-z').split('\0'))
    candidates=[ROOT/'results/h6',*(ROOT/'results/phase6e').glob('t_*')]
    for stage in (ROOT/'data/staging').glob('update_*'):
        manifest=ROOT/'results/operations'/stage.name/'run_manifest.json'
        if not manifest.is_file():continue
        run=json.loads(manifest.read_text())
        if (run.get('status')=='NO_INFORMATION_CHANGE' and run.get('mode')=='DRY_RUN'
                and not run.get('snapshot_appended') and not run.get('promoted_hashes')
                and not any(run.get('candidate_master_changes',{}).values())):
            candidates.append(stage)
    removed=[];records=[]
    for target in candidates:
        rel=target.relative_to(ROOT).as_posix()
        if not target.is_dir() or rel in exclusions or any(p==rel or p.startswith(rel+'/') for p in original|tracked):continue
        absolute=target.resolve()
        allowed=any(absolute.is_relative_to(base.resolve()) for base in [ROOT/'results',ROOT/'data/staging'])
        if target.is_symlink() or not allowed:raise ValueError('Unsafe temporary workspace: '+rel)
        files=[p for p in target.rglob('*') if p.is_file()]
        for p in files:
            if p.is_symlink():raise ValueError('Unexpected temporary symlink: '+str(p))
            records.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=checksum(p),recoverable_commit='',
                                reason='Reproducible temporary validation fixture created by Phase 6H; original inputs retained'))
        removed.append(dict(path=rel,files=len(files)))
    # Record every removed file; no raw source is selected outside these new fixtures.
    if records:
        with (OUT/'deleted_files.csv').open(encoding='utf-8') as handle:previous=list(csv.DictReader(handle))
        table('deleted_files.csv',previous+records,['path','sha256','recoverable_commit','reason'])
    evidence=OUT/'removed_validation_workspaces.json'
    previous_removed=json.loads(evidence.read_text()) if evidence.exists() else []
    write('removed_validation_workspaces.json',previous_removed+removed)
    for record in removed:
        target=(ROOT/record['path']).resolve()
        if not any(target.is_relative_to(base.resolve()) for base in [ROOT/'results',ROOT/'data/staging']):raise ValueError('Unsafe removal')
        shutil.rmtree(target)
    print(json.dumps(removed))


if __name__=='__main__':main()
