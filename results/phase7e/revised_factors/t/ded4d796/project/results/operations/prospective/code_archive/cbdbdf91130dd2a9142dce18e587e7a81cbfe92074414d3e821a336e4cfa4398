"""Content-addressed immutable records; CSV/Parquet are rebuildable mirrors."""
from __future__ import annotations

import json
from pathlib import Path
from hashlib import sha256


def digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode()).hexdigest()


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def freeze(path: Path, value: dict) -> None:
    """Exclusive create or identical no-op; never replace a frozen record."""
    encoded = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != encoded:
            raise ValueError(f"Immutable record conflict: {path}")
        return
    with path.open("xb") as handle:
        handle.write(encoded)


def append_record(directory: Path, identity: str, record: dict) -> None:
    if len(identity) != 64 or any(c not in '0123456789abcdef' for c in identity):
        raise ValueError("Invalid content-addressed identity")
    path=directory / f"{identity}.json"
    freeze(path, record)
    freeze(directory / f"{identity}.seal.json", {'sha256':file_hash(path)})


def records(directory: Path) -> list[dict]:
    result=[]
    for path in sorted(directory.glob('*.json')):
        if path.name.endswith('.seal.json'):
            continue
        seal=path.with_name(path.stem+'.seal.json')
        if not seal.exists() or json.loads(seal.read_text())['sha256']!=file_hash(path):
            raise ValueError(f'Immutable ledger corruption: {path}')
        result.append(json.loads(path.read_text()))
    return result
