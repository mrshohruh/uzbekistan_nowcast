"""Apply the narrowly audited Phase 6H moves and Git-recoverable deletions.

No directories are recursively deleted. Untracked, modified, source-data and
checksum-protected files are always retained. The immutable baseline is required.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts.maintenance.repository_freeze import ROOT, OUT, checksum, git, table, write


def apply():
    if (OUT/'deleted_files.csv').exists():
        raise FileExistsError('Cleanup already applied; refusing to overwrite recovery evidence')
    baseline = json.loads((OUT/'pre_cleanup_manifest.json').read_text())
    if git('rev-parse', 'HEAD').strip() != baseline['commit']:
        raise RuntimeError('HEAD changed since baseline')
    tracked = set(git('ls-files', '-z').split('\0')) - {''}
    dirty = set(git('diff', 'HEAD', '--name-only', '-z').split('\0')) - {''}
    protected = set(baseline['checksums'])
    # Frozen manifests are operational inputs, including their historical paths.
    for rel in ['results/phase6e/phase6e_pre_change_state.json',
                'results/phase6d/phase6d_protected_start.json']:
        value = json.loads((ROOT/rel).read_text())
        protected.update(value.get('hashes', value))
    for path in (ROOT/'results').glob('phase6d/*frozen*.json'):
        value = json.loads(path.read_text())
        for key in ['code_hashes','source_artifact_hashes','static_specification_hashes']:
            protected.update(value.get(key, {}))
    candidates = sorted(p for p in tracked if
                        p.startswith(('scripts/phase6f/', 'scripts/phase6g', 'results/phase6f/', 'results/phase6g')) or
                        p.startswith(('dashboard/phase6f', 'dashboard/phase6g')))
    deleted, retained = [], []
    for rel in candidates:
        path = (ROOT/rel).resolve()
        if not path.is_relative_to(ROOT.resolve()):
            raise ValueError('Unsafe cleanup path: '+rel)
        if rel in protected or rel in dirty or '/raw/' in rel or not path.is_file() or path.is_symlink():
            retained.append(dict(path=rel, reason='protected, dirty, raw source, absent or symlink'))
            continue
        deleted.append(dict(path=rel, sha256=checksum(path), recoverable_commit=baseline['commit'],
                            reason='Rejected Phase 6F/6G experiment; unchanged tracked file'))
    # Refuse dangling references in retained executable code. Historical prose and
    # manifests remain evidence; they are not automatically rewritten.
    doomed = {r['path'] for r in deleted}
    for rel in tracked-doomed:
        path=ROOT/rel
        if not rel.startswith(('scripts/','src/','tests/')) or path.suffix != '.py' or not path.is_file():
            continue
        content=path.read_text(encoding='utf-8-sig')
        for prefix in ['scripts.phase6f','scripts.phase6g','scripts/phase6f','scripts/phase6g']:
            if prefix in content and rel != 'scripts/maintenance/consolidate_repository.py':
                raise RuntimeError('Resolve retained dependency before deletion: '+rel+' -> '+prefix)
    migrations=[]
    (ROOT/'scripts/production').mkdir(exist_ok=True)
    (ROOT/'scripts/production/__init__.py').write_text('"""Current production orchestration, models and diagnostics."""\n')
    for name in ['models','diagnostics','dashboard','run','update']:
        old=f'scripts/phase6e/{name}.py';new=f'scripts/production/{name}.py'
        if old in dirty:
            raise RuntimeError('Refusing to migrate user-modified file: '+old)
        content=(ROOT/old).read_text(encoding='utf-8')
        for node in ast.parse(content).body:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                migrations.append(dict(function=node.name,old_path=old,new_path=new,change='Move; scientific body unchanged'))
        # Keep generated policy text and historical filenames byte-compatible.
        content=content.replace('from scripts.phase6e.', 'from scripts.production.')
        if name=='update':
            content=content.replace("'scripts.phase6e.run'", "'scripts.production.run'")
        if name=='run':
            content=content.replace("(root/'scripts/phase6e').glob('*.py')", "(root/'scripts/production').glob('*.py')")
        (ROOT/new).write_text(content,encoding='utf-8')
        # Immutable policy entrypoints and historical consumers retain compatibility.
        wrapper=f'"""Compatibility entry point; implementation lives in scripts.production.{name}."""\nfrom scripts.production.{name} import *  # noqa: F401,F403\n'
        if name in {'run','update'}:
            wrapper += "\nif __name__ == '__main__':\n    main()\n"
        (ROOT/old).write_text(wrapper,encoding='utf-8')
    old=ROOT/'scripts/phase6e/test_phase6e.py'
    new=ROOT/'tests/production/test_production.py';new.parent.mkdir(exist_ok=True)
    content=old.read_text(encoding='utf-8').replace('from scripts.phase6e.', 'from scripts.production.')
    new.write_text(content,encoding='utf-8')
    migrations.append(dict(function='production regression tests',old_path=old.relative_to(ROOT).as_posix(),
                           new_path=new.relative_to(ROOT).as_posix(),change='Move into default pytest discovery'))
    deleted.append(dict(path=old.relative_to(ROOT).as_posix(),sha256=checksum(old),recoverable_commit=baseline['commit'],reason='Moved to tests/production'))
    harness=ROOT/'scripts/phase6e/tests.py'
    harness.write_text(harness.read_text().replace("'scripts/phase6e/test_phase6e.py'", "'tests/production/test_production.py'"),encoding='utf-8')
    # Save recovery evidence before removing each explicitly audited file.
    table('deleted_files.csv',deleted,['path','sha256','recoverable_commit','reason'])
    table('function_migrations.csv',migrations,['function','old_path','new_path','change'])
    write('cleanup_exceptions.json',retained)
    for row in deleted:
        path=(ROOT/row['path']).resolve()
        if not path.is_relative_to(ROOT.resolve()) or checksum(path)!=row['sha256']:
            raise RuntimeError('File changed after audit: '+row['path'])
        path.unlink()
    # Empty audited folders only; untracked/ignored files are untouched.
    for directory in sorted({(ROOT/r['path']).parent for r in deleted},key=lambda p:len(p.parts),reverse=True):
        if directory.exists() and not any(directory.iterdir()):directory.rmdir()
    print(json.dumps(dict(deleted=len(deleted),migrated_functions=len(migrations),exceptions=len(retained))))


if __name__=='__main__':
    apply()
