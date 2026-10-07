"""Current production integrity protocol with explicit migration acceptance.

Code/config hashes normalize CRLF to LF for portable Git checkouts. Data hashes
always refer to exact bytes. Initial data hashes are replay evidence; approved
operational successors are checked by version manifests and transactional gates.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path


def content_hash(path):
    payload=Path(path).read_bytes()
    if Path(path).suffix in {'.py','.json','.yaml','.yml','.toml','.txt','.bat'}:
        payload=payload.replace(b'\r\n',b'\n')
    return hashlib.sha256(payload).hexdigest()


def verify(root):
    path=root/'config/production_seal.json'
    seal=json.loads(path.read_text(encoding='utf-8'))
    if seal['status']=='MIGRATION_CANDIDATE':
        if os.environ.get('UZNOWCAST_SEAL_MIGRATION')!='1':raise ValueError('Production seal migration has not been accepted')
    elif seal['status']=='ACCEPTED':
        accepted=json.loads((root/'config/production_seal_acceptance.json').read_text())
        if accepted['seal_sha256']!=content_hash(path):raise ValueError('Production seal acceptance mismatch')
    else:raise ValueError('Unrecognized production seal status')
    changed=[rel for rel,h in seal['runtime_hashes'].items() if not (root/rel).is_file() or content_hash(root/rel)!=h]
    if changed:raise ValueError('Current production seal mismatch: '+', '.join(changed))
    pointer=json.loads((root/'results/operations/current_production.json').read_text(encoding='utf-8'))
    policy=json.loads((root/pointer['policy']).read_text(encoding='utf-8'))
    if any(policy.get(k)!=v for k,v in seal['scientific_policy'].items()):
        raise ValueError('Active scientific policy differs from production seal')
    if policy['specification_hashes']!=seal['specification_hashes']:
        raise ValueError('Active specification hashes differ from production seal')
    return {rel:hashlib.sha256((root/rel).read_bytes()).hexdigest() for rel in seal['runtime_hashes']},seal


def resolve_provenance(root,relative):
    mapping=json.loads((root/'config/provenance_relocations.json').read_text())
    path=(root/mapping.get(str(relative).replace('\\','/'),str(relative).replace('\\','/'))).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Unsafe provenance path')
    return path
