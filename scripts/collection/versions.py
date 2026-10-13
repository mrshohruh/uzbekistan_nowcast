"""Immutable collection snapshots and atomic committed-pointer publication."""
from __future__ import annotations

import os
from pathlib import Path

from scripts.operations.state import read, write, sha


class InterruptedRun(RuntimeError):
    pass


def current_snapshot(store: Path) -> Path | None:
    """Read only a complete hash-verified immutable version; no mutable files."""
    pointer = store / 'current.json'
    if not pointer.exists():
        return None
    value = read(pointer)
    path = (store / 'versions' / value['version']).resolve()
    if not path.is_relative_to((store / 'versions').resolve()):
        raise ValueError('Unsafe collection version pointer')
    manifest = read(path / 'manifest.json')
    if sha(path / 'manifest.json') != value['manifest_sha256'] or manifest['status'] != 'VALIDATED':
        raise ValueError('Collection version is not committed/validated')
    _validate_files(path, manifest)
    return path


def _validate_files(path, manifest):
    for relative, digest in manifest['files'].items():
        target = (path / relative).resolve()
        if not target.is_relative_to(path) or sha(target) != digest:
            raise ValueError('Incomplete/corrupt collection version: ' + relative)


def assert_no_pending(store):
    pending = [p for p in (store / 'runs').glob('*/journal.json')
               if read(p)['status'] in {'COLLECTING', 'VALIDATED', 'PUBLISHING'}]
    if pending:
        raise InterruptedRun('Interrupted collection requires explicit recovery: ' + str(pending[0]))


def publish(store, stage, run_id, manifest, *, replace=os.replace):
    """One directory rename, then one atomic pointer; old reader versions survive."""
    run = store / 'runs' / run_id
    previous = read(store / 'current.json') if (store / 'current.json').exists() else None
    write(stage / 'manifest.json', manifest)
    _validate_files(stage.resolve(), manifest)
    versions = store / 'versions'
    versions.mkdir(parents=True, exist_ok=True)
    destination = versions / run_id
    write(run / 'journal.json', dict(status='PUBLISHING', run_id=run_id, previous=previous))
    # stage and versions are on the same filesystem; no mutable master replacement.
    replace(stage, destination)
    _validate_files(destination.resolve(), manifest)
    value = dict(version=run_id, manifest_sha256=sha(destination / 'manifest.json'))
    temporary = store / (run_id + '.pointer.tmp')
    write(temporary, value)
    replace(temporary, store / 'current.json')
    write(run / 'journal.json', dict(status='COMMITTED', run_id=run_id, previous=previous))
    return destination


def recover(store: Path, run_id: str):
    """Called with the shared writer lock held; never guesses an active lock stale."""
    if not run_id or Path(run_id).name != run_id:
        raise ValueError('Unsafe recovery run identifier')
    journal = store / 'runs' / run_id / 'journal.json'
    state = read(journal)
    if state['status'] not in {'COLLECTING', 'VALIDATED', 'PUBLISHING'}:
        return state['status']
    pointer = read(store / 'current.json') if (store / 'current.json').exists() else None
    if pointer and pointer['version'] == run_id:
        current_snapshot(store)  # A complete published version can finish its journal.
        status = 'COMMITTED'
    else:
        current_snapshot(store)  # Old committed version must still be readable.
        status = 'ABORTED_RECOVERED'
    # Preserve the interrupted stage/receipts for review; never promote it on recovery.
    write(journal, dict(state, status=status))
    return status
