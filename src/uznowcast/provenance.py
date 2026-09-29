"""Immutable HTTP evidence and atomic tabular metadata exports."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from io import BytesIO
import hashlib
import json
import re
import zipfile
import pandas as pd

from uznowcast import PARSER_VERSION
from uznowcast.validation.schema import schema_fingerprint, strict_json_loads


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_json(path: Path, obj, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x' if exclusive else 'w', encoding='utf-8') as file:
        json.dump(obj, file, ensure_ascii=False, indent=2, default=str)


def _binary_schema_fingerprint(content: bytes, content_type: str) -> str:
    """Fingerprint non-JSON container/markup structure without hashing values."""
    structure: object
    if content.startswith(b'PK'):
        with zipfile.ZipFile(BytesIO(content)) as archive:
            structure = {'content_type': content_type, 'members': sorted(archive.namelist())}
    elif 'html' in content_type.lower():
        text = content.decode('utf-8', errors='replace')
        structure = {'content_type': content_type,
                     'tags': re.findall(r'<\s*([a-zA-Z0-9]+)(?:\s|>)', text)}
    else:
        structure = {'content_type': content_type}
    encoded = json.dumps(structure, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()


def archive_response(root: Path, row: dict, url: str, response, run_id: str,
                     source_release_date=None, source_release_basis=None) -> dict:
    timestamp = utc_now()
    folder = root / 'data/raw' / row['provider'].lower() / row['variable_key']
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}_{uuid4().hex}.payload'
    with path.open('xb') as file:
        file.write(response.content)
    try:
        obj = strict_json_loads(response.content)
        fingerprint = schema_fingerprint(obj)
        rows_raw = len(obj) if isinstance(obj, list) else None
        if isinstance(obj, list) and len(obj) == 1 and isinstance(obj[0], dict) and isinstance(obj[0].get('data'), list):
            rows_raw = len(obj[0]['data'])
        if row['provider'] == 'SIAT' and isinstance(obj, dict) and 'updated_at' in obj:
            source_release_date = pd.Timestamp(obj['updated_at']).isoformat()
            source_release_basis = 'dataset_update_timestamp; not historical first release'
    except (ValueError, UnicodeError):
        fingerprint = _binary_schema_fingerprint(response.content, response.headers.get('Content-Type', ''))
        rows_raw = None
    meta = dict(run_id=run_id, variable_key=row['variable_key'], provider=row['provider'],
                source_id=row['native_indicator_dataset_id'], source_url=url,
                response_url=response.url, retrieved_at=timestamp, source_release_date=source_release_date,
                source_release_basis=source_release_basis,
                http_status=response.status_code, content_type=response.headers.get('Content-Type', ''),
                raw_file_path=path.relative_to(root).as_posix(),
                checksum=hashlib.sha256(response.content).hexdigest(), schema_fingerprint=fingerprint,
                parser_version=PARSER_VERSION, rows_raw=rows_raw)
    save_json(path.with_suffix('.json'), meta, exclusive=True)
    return meta


def read_raw(root: Path, meta: dict):
    content = read_raw_bytes(root, meta)
    return strict_json_loads(content)


def read_raw_bytes(root: Path, meta: dict) -> bytes:
    content = (root / meta['raw_file_path'].replace('\\', '/')).read_bytes()
    if hashlib.sha256(content).hexdigest() != meta['checksum']:
        raise ValueError(f'Raw checksum mismatch: {meta["raw_file_path"]}')
    return content


def atomic_parquet(frame: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    frame.to_parquet(temp, index=False)
    temp.replace(path)


def append_table(frame: pd.DataFrame, path: Path, identity: list[str]):
    previous = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    combined = pd.concat([previous, frame], ignore_index=True) if not previous.empty else frame.copy()
    combined = combined.drop_duplicates(identity, keep='first')
    atomic_parquet(combined, path)


def attach_provenance(frame: pd.DataFrame, row: dict, meta: dict) -> pd.DataFrame:
    result = frame.copy()
    for key in ('variable_key', 'provider'):
        result[key] = row[key]
    result['source_id'] = row['native_indicator_dataset_id']
    for key in ('source_url', 'retrieved_at', 'raw_file_path', 'checksum', 'schema_fingerprint'):
        result[key] = meta[key]
    result['source_release_date'] = meta.get('source_release_date')
    result['source_release_basis'] = meta.get('source_release_basis')
    result['vintage_date'] = meta['retrieved_at']
    result['parser_version'] = PARSER_VERSION
    result['raw_unit'] = row['raw_unit']
    result['unit'] = row['raw_unit']
    result['transformation'] = row['required_transformation']
    result['is_preliminary'] = None
    result['revision_status'] = 'retrieved_vintage'
    return result
