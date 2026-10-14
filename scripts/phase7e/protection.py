"""Hash prior scientific files, including Phase 7D, before and after research."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import os

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot():
    paths = []
    for folder in ['src', 'scripts', 'config', 'registry', 'data', 'metadata', 'dashboard', 'results', 'docs', 'tests']:
        for directory, dirs, files in os.walk(ROOT / folder):
            dirs[:] = [d for d in dirs if d != '__pycache__' and not d.startswith(('pytest_tmp', 'tmp', '.'))]
            for name in files:
                p = Path(directory) / name
                rel = p.relative_to(ROOT).as_posix()
                if p.suffix != '.pyc' and not rel.startswith(('scripts/phase7e/', 'results/phase7e/')):
                    paths.append((rel, p))
    paths.extend((p.name, p) for p in [ROOT/'AGENTS.md', ROOT/'README.md', ROOT/'PROJECT_SPEC.md', ROOT/'requirements.txt', ROOT/'requirements-models.txt', ROOT/'pyproject.toml', ROOT/'.gitignore'] if p.is_file())
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(pool.map(lambda item: (item[0], sha(item[1])), paths))


def verify(before):
    with ThreadPoolExecutor(max_workers=8) as pool:
        changes = [x for x in pool.map(lambda item: item[0] if not (ROOT/item[0]).is_file() or sha(ROOT/item[0]) != item[1] else None, before.items()) if x]
    if changes: raise ValueError('Protected artifacts changed: ' + str(changes))
    return len(before)
