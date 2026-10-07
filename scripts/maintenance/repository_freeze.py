"""Read-only repository inventory and immutable Phase 6H baseline.

Never deletes files. Git's index supplies recoverability; ignored source data are
inventoried separately. Run before any cleanup, then use --after for comparison.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/repository_cleanup'


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT, encoding='utf-8', errors='replace')


def checksum(path: Path) -> str:
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def write(name: str, value) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, default=str) + '\n', encoding='utf-8')


def table(name: str, rows: list[dict], columns: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def inventory():
    tracked = set(git('ls-files', '-z').split('\0')) - {''}
    untracked = set(git('ls-files', '--others', '--exclude-standard', '-z').split('\0')) - {''}
    errors = []
    paths = set()
    def error(exc):
        errors.append(str(exc))
    for parent, dirs, files in os.walk(ROOT, onerror=error):
        excluded = [d for d in dirs if d in {'.git', '.venv', '__pycache__', '.pytest_cache', 'node_modules'} or
                    d.startswith(('t_', 'test_', 'validation_tmp', 'pytest_tmp', 'browser_profile', '_vendor',
                                  'op_tests', '_pytest', 'validation_workspaces'))]
        errors.extend('Inventory traversal excluded (not deleted): ' + (Path(parent)/d).relative_to(ROOT).as_posix() for d in excluded)
        dirs[:] = [d for d in dirs if d not in excluded]
        for name in files:
            paths.add((Path(parent) / name).relative_to(ROOT).as_posix())
    rows = []
    for rel in sorted(paths | tracked | untracked):
        path = ROOT / rel
        try:
            exists = path.is_file()
            size = path.stat().st_size if exists else None
        except OSError as exc:
            errors.append(f'{rel}: {exc}'); exists = False; size = None
        rows.append(dict(path=rel, tracked=rel in tracked, untracked=rel in untracked,
                         exists=exists, bytes=size, python=rel.endswith('.py')))
    return rows, errors


def graph(rows):
    """Conservative AST graph including dynamic literal paths and bare imports."""
    python = {r['path'] for r in rows if r['python'] and r['exists'] and '/_vendor/' not in r['path']}
    modules = {p.removeprefix('src/').removesuffix('.py').replace('/', '.').removesuffix('.__init__'): p for p in python}
    edges = []
    functions = {}
    for rel in sorted(python):
        try:
            tree = ast.parse((ROOT / rel).read_text(encoding='utf-8-sig'))
        except (OSError, SyntaxError, UnicodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or '']
                for name in names:
                    target = modules.get(name)
                    if not target:
                        candidate = (Path(rel).parent / (name.replace('.', '/') + '.py')).as_posix()
                        target = candidate if candidate in python else None
                    if target:
                        edges.append(dict(source=rel, target=target, kind='import'))
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value
                if value in python or value.startswith(('config/', 'registry/', 'data/', 'results/', 'dashboard/', 'scripts/')):
                    edges.append(dict(source=rel, target=value, kind='literal_path_or_template'))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                key = hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
                functions.setdefault(key, []).append(dict(path=rel, name=node.name, line=node.lineno))
    duplicate = [v for v in functions.values() if len(v) > 1]
    return edges, duplicate


def snapshot(after=False):
    name = 'post_cleanup_manifest.json' if after else 'pre_cleanup_manifest.json'
    if not after and (OUT / name).exists():
        raise FileExistsError('Baseline already exists; refusing to replace it')
    rows, errors = inventory()
    edges, duplicates = graph(rows)
    hashes = {}
    for row in rows:
        rel = row['path']
        if row['exists'] and (rel.startswith(('src/', 'config/', 'registry/', 'data/master/', 'data/processed/', 'metadata/')) or
                            rel.startswith(('results/phase6e/', 'results/production/', 'results/phase6d/')) and
                            not any(p.startswith(('t_', 'test_', 'browser_', 'rerun')) for p in Path(rel).parts)):
            try: hashes[rel] = checksum(ROOT / rel)
            except OSError as exc: errors.append(str(exc))
    pointer = json.loads((ROOT / 'results/operations/current_production.json').read_text())
    current = json.loads((ROOT / pointer['nowcast']).read_text())
    policy = json.loads((ROOT / pointer['policy']).read_text())
    manifest = dict(commit=git('rev-parse', 'HEAD').strip(), recent_commits=git('log', '-5', '--oneline'),
                    working_tree_status=git('status', '--porcelain'), inventory_errors=errors,
                    inventory_scope='Git tracked/untracked files plus accessible non-temporary files; excluded traversal directories and access errors explicitly recorded',
                    files=len(rows), accessible_files=sum(r['exists'] for r in rows),
                    python_files=sum(r['python'] and r['exists'] for r in rows),
                    tests=sum(r['exists'] and Path(r['path']).name.startswith('test_') and r['python'] for r in rows),
                    production_pointer=pointer, production_nowcast=current, production_policy=policy,
                    dfm_output=current['dfm_forecast'], umidas_output=current['umidas_forecast'],
                    combination_output=current['combo_50_50_forecast'], final_nowcast=current['final_forecast'],
                    checksums=hashes, untracked_files=[r['path'] for r in rows if r['untracked']],
                    untracked_scientific_inputs=[p for p in hashes if not next(r['tracked'] for r in rows if r['path']==p)])
    write(name, manifest)
    tag = 'after' if after else 'before'
    table(f'file_inventory_{tag}.csv', rows, ['path','tracked','untracked','exists','bytes','python'])
    write(f'dependency_graph_{tag}.json', edges)
    write(f'duplicate_functions_{tag}.json', duplicates)
    print(json.dumps({k: manifest[k] for k in ['commit','files','accessible_files','python_files','tests','final_nowcast']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--after', action='store_true')
    snapshot(parser.parse_args().after)
