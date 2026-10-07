"""Archive official GDP checks; never infer first releases from SIAT updates."""
from datetime import datetime, timezone
import hashlib
import json
import time
from urllib.parse import urlparse

import pandas as pd
import requests
import math

from scripts.operations.prospective.common import ROOT, OUT, freeze, file_hash, digest, safe, append_record, records
from uznowcast.models.data import load_dataset
from uznowcast.parsers.siat import parse_siat


def official(url):
    host = urlparse(url).hostname
    return url.startswith('https://') and host in {'stat.uz','www.stat.uz','siat.stat.uz','api.siat.stat.uz'}


def download(url, out=OUT):
    if not official(url):
        raise ValueError('Unofficial GDP source URL')
    directory = out / 'source_checks'
    directory.mkdir(parents=True,exist_ok=True)
    response = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers={'User-Agent':'UzbekistanNowcast-Phase6D/1.0 research source audit'}, timeout=(10,30))
        except (requests.Timeout, requests.ConnectionError):
            if attempt==2:
                raise
            time.sleep(2**attempt)
            continue
        stamp = datetime.now(timezone.utc).isoformat()
        h = hashlib.sha256(response.content).hexdigest()
        path = directory/(h+'.payload')
        if not path.exists():
            with path.open('xb') as handle:
                handle.write(response.content)
        elif file_hash(path)!=h:
            raise ValueError('Source archive corrupted')
        info = dict(source_url=url,retrieved_at=stamp,http_status=response.status_code, checksum=h,
                    raw_file_path=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                    content_type=response.headers.get('Content-Type'))
        freeze(directory/(digest(info)+'.json'),info)
        if response.status_code in [429,500,502,503,504] and attempt<2:
            time.sleep(2**attempt)
            continue
        response.raise_for_status()
        if not response.content:
            raise ValueError('Empty official payload')
        return response,info
    raise ValueError('GDP request retry limit reached')


def check_current(out=OUT):
    dataset = load_dataset(ROOT)
    row = dataset.registry.rows['gdp_real_yoy']
    contract = json.loads((ROOT/'config/siat_contracts.json').read_text())['gdp_real_yoy']
    response,descriptor = download(row['machine_download_url'],out)
    metadata = response.json()
    if not isinstance(metadata,dict) or not metadata.get('file'):
        raise ValueError('SIAT GDP descriptor changed schema')
    response,payload = download(metadata['file'],out)
    parsed = parse_siat(response.json(), {**row,'rule_codes':contract['rule_codes']}, contract)
    parsed = parsed.loc[parsed.raw_value.notna()].copy()
    parsed['value'] = parsed.raw_value-100
    check = dict(checked_at_utc=payload['retrieved_at'], descriptor=descriptor,payload=payload,
                 latest_quarter=parsed.reference_period.max(), available_quarters=parsed.reference_period.tolist(),
                 values=dict(zip(parsed.reference_period, parsed.value)), source_verified=True,
                 observed_dataset_update=metadata.get('updated_at'), first_release_dates_verified=False,
                 note='Current official national series only; dataset update is not a first publication date')
    freeze(out/'source_checks'/(digest(check)+'_check.json'),safe(check))
    return check


def validate_check(check,out=OUT):
    if not check.get('source_verified') or pd.Timestamp.now(tz='UTC')-pd.Timestamp(check['checked_at_utc'])>pd.Timedelta(hours=24):
        raise ValueError('Source check must be verified and less than 24 hours old')
    if pd.Timestamp(check['checked_at_utc'])>pd.Timestamp.now(tz='UTC'):
        raise ValueError('Future source check')
    archived=out/'source_checks'/(digest(check)+'_check.json')
    if not archived.exists() or json.loads(archived.read_text())!=check:
        raise ValueError('Source check lacks intact archived audit record')
    for kind in ['descriptor','payload']:
        receipt=check[kind]
        from scripts.operations.seal import resolve_provenance
        path=resolve_provenance(ROOT,receipt['raw_file_path'])
        if not official(receipt['source_url']) or receipt['http_status']!=200 or not path.is_relative_to((out/'source_checks').resolve()) or file_hash(path)!=receipt['checksum']:
            raise ValueError('Source check archive invalid')
    return check


REALIZATION_COLUMNS = ['target_quarter','first_release_date','first_release_value','latest_revised_value','source',
                       'source_verified','ingested_timestamp','eligible_for_scoring','evidence_status']


def register_realization(evidence, bundle, out=OUT):
    """Accept reviewed dated official FIRST_RELEASE/REVISION evidence only.

    This explicit evidence interface avoids treating a mutable SIAT snapshot as
    the first release. The operator supplies the reviewed source extraction,
    its official dated release-page URL, checksum, and literal value selector.
    """
    required = {'target_quarter','first_release_date','value','source_url','raw_file_path','checksum',
                'source_verified','first_release_verified','date_basis','extraction_evidence','event_kind'}
    if not required.issubset(evidence) or evidence['event_kind'] not in {'FIRST_RELEASE','REVISION'}:
        raise ValueError('Incomplete reviewed GDP first-release evidence')
    if not official(evidence['source_url']) or evidence['source_verified'] is not True or evidence['first_release_verified'] is not True:
        raise ValueError('Unverified/unofficial first release')
    if evidence['date_basis'] not in {'DATED_OFFICIAL_FIRST_RELEASE_REPORT','DATED_OFFICIAL_FIRST_RELEASE_ARTICLE'}:
        raise ValueError('Dataset update or estimated lag cannot establish first release')
    if len(evidence['extraction_evidence'])<20:
        raise ValueError('Reviewed quarter/value/date extraction evidence required')
    if isinstance(evidence['value'], bool) or not math.isfinite(float(evidence['value'])):
        raise ValueError('Realization must have a finite numeric GDP value')
    if evidence['event_kind']=='REVISION' and not evidence.get('revision_release_date'):
        raise ValueError('Revision requires its own observed release date')
    if evidence['event_kind']=='REVISION':
        revised=pd.Timestamp(evidence['revision_release_date']).date()
        if revised>datetime.now(timezone.utc).date() or revised<pd.Timestamp(evidence['first_release_date']).date():
            raise ValueError('Revision date must be observed and no earlier than first release')
    quarter = str(pd.Period(evidence['target_quarter'],freq='Q'))
    if quarter!=evidence['target_quarter']:
        raise ValueError('Invalid target quarter')
    release = pd.Timestamp(evidence['first_release_date'])
    if release.normalize()<=pd.Period(quarter,freq='Q').end_time.normalize():
        raise ValueError('GDP released before reference quarter ends')
    cutoff = pd.Timestamp(datetime.now(timezone.utc))
    if release.tzinfo is None:
        release = release.tz_localize('Asia/Tashkent')
    if release.tz_convert('UTC')>cutoff:
        raise ValueError('Future release cannot be registered')
    raw = (ROOT/evidence['raw_file_path']).resolve()
    if not raw.is_relative_to((out/'source_checks').resolve()) or not raw.is_file() or file_hash(raw)!=evidence['checksum']:
        raise ValueError('Realization needs an intact Phase6D archived official source')
    # Source URL and hash must match an archived HTTP-success retrieval receipt.
    receipts = [json.loads(p.read_text()) for p in (out/'source_checks').glob('*.json')]
    if not any(r.get('source_url')==evidence['source_url'] and r.get('checksum')==evidence['checksum'] and r.get('http_status')==200 for r in receipts):
        raise ValueError('Official retrieval receipt does not support realization source')
    prior = [r for r in records(out/'realization_records') if r['target_quarter']==quarter]
    if evidence['event_kind']=='FIRST_RELEASE' and prior:
        first = next(r for r in prior if r['event_kind']=='FIRST_RELEASE')
        if evidence['value']!=first['value'] or evidence['first_release_date']!=first['first_release_date']:
            raise ValueError('Cannot overwrite first-release value/date')
        return
    if evidence['event_kind']=='REVISION' and not prior:
        raise ValueError('Revision cannot substitute for unknown first release')
    record = dict(evidence, ingested_timestamp=datetime.now(timezone.utc).isoformat())
    append_record(out/'realization_records',digest(record),record)


def realization_registry(out=OUT):
    events = records(out/'realization_records')
    rows = []
    for q in sorted({r['target_quarter'] for r in events}):
        block = [r for r in events if r['target_quarter']==q]
        firsts = [r for r in block if r['event_kind']=='FIRST_RELEASE']
        if len(firsts)!=1:
            raise ValueError('Ambiguous first-release record')
        first = firsts[0]
        latest = max(block,key=lambda r:r['ingested_timestamp'])
        rows.append(dict(target_quarter=q,first_release_date=first['first_release_date'], first_release_value=first['value'],
                         latest_revised_value=latest['value'],source=first['source_url'], source_verified=True,
                         ingested_timestamp=first['ingested_timestamp'], eligible_for_scoring=True,
                         evidence_status='REVIEWED_OFFICIAL_FIRST_RELEASE'))
    return pd.DataFrame(rows,columns=REALIZATION_COLUMNS)
