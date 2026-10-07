"""Checkpoint only explicit Phase 6H changes, never pre-existing dirty paths."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/repository_cleanup'
EVIDENCE=OUT/'phase6h1_checkpoint'


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,encoding='utf-8',errors='replace',stderr=subprocess.PIPE)


def prepare():
    EVIDENCE.mkdir(exist_ok=True)
    if git('diff','--cached','--name-only').strip():
        raise RuntimeError('Index already contains staged changes; refusing to include or unstage them')
    before=json.loads((OUT/'pre_cleanup_manifest.json').read_text())
    original={line[3:] for line in before['working_tree_status'].splitlines() if line.strip()}
    # This audit tool was created by Phase 6H before it recorded its own baseline.
    # Conversation history and the Phase 6H migration inventory establish ownership.
    original.discard('scripts/maintenance/repository_freeze.py')
    with (OUT/'deleted_files.csv').open(encoding='utf-8') as handle:
        deleted=[r['path'] for r in csv.DictReader(handle) if r['recoverable_commit']]
    paths=set(deleted)
    paths.update(['README.md','scripts/operations/test_operations.py','scripts/phase6e/tests.py',
                  'requirements-models.txt','config/production.json','results/current/index.json','results/diagnostics/index.json'])
    paths.update(f'scripts/phase6e/{n}.py' for n in ['models','diagnostics','dashboard','run','update'])
    for directory in ['scripts/production','tests/production','scripts/maintenance']:
        for path in (ROOT/directory).glob('*.py'):
            rel=path.relative_to(ROOT).as_posix()
            # Existing maintenance utilities not created/changed by Phase 6H stay out.
            if rel.startswith('scripts/maintenance/') and rel not in {
                'scripts/maintenance/repository_freeze.py','scripts/maintenance/consolidate_repository.py',
                'scripts/maintenance/validate_freeze.py','scripts/maintenance/report_freeze.py',
                'scripts/maintenance/cleanup_validation_workspaces.py','scripts/maintenance/checkpoint_consolidation.py'}:continue
            paths.add(rel)
    # Preserve completed audit evidence, not repeated generated builds or logs.
    paths.update(p.relative_to(ROOT).as_posix() for p in OUT.iterdir()
                 if p.is_file() and p.suffix in {'.json','.csv','.md','.xml','.txt'})
    conflicts=sorted(paths & original)
    if conflicts:raise RuntimeError('Selected paths overlap pre-cleanup dirty state: '+str(conflicts))
    for name,args in [('status',['status','--porcelain=v1','--untracked-files=all']),
                      ('diff_stat',['diff','--stat']),('diff',['diff']),
                      ('untracked',['ls-files','--others','--exclude-standard'])]:
        (EVIDENCE/(name+'.txt')).write_text(git(*args),encoding='utf-8')
    report=dict(base_commit=git('rev-parse','HEAD').strip(),paths=sorted(paths),
                excluded_preexisting_paths=sorted(original),index_was_empty=True,
                protected_production_files=[p for p in sorted(paths) if p.startswith(('scripts/production/','tests/production/')) or p in {'README.md','config/production.json'}])
    (EVIDENCE/'explicit_paths.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    pathfile=EVIDENCE/'pathspec.nul';pathfile.write_bytes(b'\0'.join(p.encode() for p in sorted(paths))+b'\0')
    print(json.dumps(dict(selected_paths=len(paths),base_commit=report['base_commit'],preexisting_paths_excluded=len(original))))


def commit():
    report=json.loads((EVIDENCE/'explicit_paths.json').read_text())
    if git('rev-parse','HEAD').strip()!=report['base_commit'] or git('diff','--cached','--name-only').strip():
        raise RuntimeError('HEAD/index changed since checkpoint preparation')
    subprocess.run(['git','add','--pathspec-from-file='+str(EVIDENCE/'pathspec.nul'),'--pathspec-file-nul'],cwd=ROOT,check=True)
    selected=set(git('diff','--cached','--name-only','-z').split('\0'))-{''}
    if not selected.issubset(set(report['paths'])):raise RuntimeError('Unexpected staged paths; refusing commit')
    subprocess.run(['git','diff','--cached','--check'],cwd=ROOT,check=True)
    subprocess.run(['git','commit','-m','Checkpoint Phase 6H production consolidation and exact reproduction evidence'],cwd=ROOT,check=True)
    value=dict(commit=git('rev-parse','HEAD').strip(),staged_paths=sorted(selected),
               index_clean=not git('diff','--cached','--name-only').strip())
    (EVIDENCE/'checkpoint_commit.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(commit=value['commit'],checkpoint_paths=len(selected))))


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='commit':commit()
    else:prepare()
