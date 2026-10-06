"""Official SIAT payloads and calendar-quarter nominal transformations."""
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from scripts.phase6g3.protection import OUT, ROOT
from scripts.phase6f.experiment import dump, sha


def fetch(url, key):
    """Archive response bytes before decoding, with bounded transient retries."""
    if urlparse(url).hostname not in {'api.siat.stat.uz','siat.stat.uz','stat.uz','www.stat.uz'}:
        raise ValueError('Unofficial source')
    directory=OUT/'raw';directory.mkdir(exist_ok=True)
    session=requests.Session();session.headers['User-Agent']='UzbekistanNowcastResearch/Phase6G.3 (GDP target audit)'
    session.mount('https://',HTTPAdapter(max_retries=Retry(total=3,backoff_factor=1,status_forcelist=[429,500,502,503,504])))
    stamp=datetime.now(timezone.utc).isoformat()
    response=session.get(url,timeout=(15,60))
    if urlparse(response.url).hostname not in {'api.siat.stat.uz','siat.stat.uz','stat.uz','www.stat.uz'}:raise ValueError('Unofficial redirect')
    checksum=hashlib.sha256(response.content).hexdigest()
    path=directory/(key+'_'+uuid.uuid4().hex[:12]+'.payload');path.write_bytes(response.content)
    receipt=dict(variable_key=key,provider='SIAT/Statistics Agency',source_url=url,response_url=response.url,retrieved_at=stamp,
        http_status=response.status_code,content_type=response.headers.get('Content-Type'),checksum=checksum,
        raw_file_path=path.relative_to(ROOT).as_posix(),parser_version='phase6g3-v1',source_release_date=None)
    dump(path.with_suffix('.json'),receipt)
    response.raise_for_status()
    if not response.content:raise ValueError('Empty payload')
    return response.content,receipt


def parse(payload, indicator, frequency):
    if not isinstance(payload,list) or len(payload)!=1 or set(payload[0])!={'metadata','data'}:raise ValueError('SIAT schema changed')
    metadata=payload[0]['metadata']
    values={m.get('value_en') for m in metadata if m.get('name_en') in ['Indicator identification number (code)','Datasets Identification Number (code)']}
    if values!={indicator}:raise ValueError('Wrong nominal GDP indicator: '+str(values))
    for name,value in [('Periodicity',frequency),('Unit of measurement','national currency, billion soums')]:
        if {m.get('value_en') for m in metadata if m.get('name_en')==name}!={value}:raise ValueError('Unit/frequency mismatch: '+name)
    selected=[r for r in payload[0]['data'] if r.get('Code')=='1700' and r.get('Klassifikator_en')=='Republic of Uzbekistan']
    if len(selected)!=1:raise ValueError('National GDP row missing or ambiguous')
    pattern=r'\d{4}-Q[1-4]' if frequency=='quarterly' else r'\d{4}'
    dimensions={'Code','Klassifikator','Klassifikator_en','Klassifikator_ru','Klassifikator_uzc'}
    if set(selected[0])-dimensions-{k for k in selected[0] if re.fullmatch(pattern,k)}:raise ValueError('Unknown nominal GDP dimensions')
    records=[]
    for k,v in selected[0].items():
        if k in dimensions:continue
        if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v)):raise ValueError('Nonnumeric GDP value')
        records.append(dict(quarter=k.replace('-Q','Q') if frequency=='quarterly' else k,cumulative_nominal_gdp=v,unit='billion UZS'))
    return pd.DataFrame(records).sort_values('quarter')


def load_siat(dataset, indicator, frequency):
    cache=OUT/f'siat_{dataset}_receipt.json'
    if cache.exists():
        meta=json.loads(cache.read_text());path=ROOT/meta['raw_file_path']
        if sha(path)!=meta['checksum']:raise ValueError('Archived SIAT checksum mismatch')
        return parse(json.loads(path.read_bytes()),indicator,frequency),meta
    url=f'https://api.siat.stat.uz/sdmx/{dataset}/table/download/?download_format=json'
    body,descriptor=fetch(url,'nominal_gdp_'+str(dataset)+'_descriptor');decoded=json.loads(body)
    if not {'file','updated_at'}<=decoded.keys():raise ValueError('SIAT descriptor changed')
    body,meta=fetch(decoded['file'],'nominal_gdp_'+str(dataset))
    meta.update(dataset_update_date=decoded['updated_at'],descriptor_raw_file_path=descriptor['raw_file_path'],
        schema_fingerprint=hashlib.sha256(json.dumps([(m.get('name_en'),m.get('value_en')) for m in json.loads(body)[0]['metadata']],sort_keys=True).encode()).hexdigest())
    dump(cache,meta)
    return parse(json.loads(body),indicator,frequency),meta


def transform(cumulative):
    """No Q4->Q1 subtraction; no missing-quarter or nonpositive growth filling."""
    s=cumulative.copy()
    if s.index.has_duplicates:raise ValueError('Duplicate nominal GDP quarter')
    if not isinstance(s.index,pd.PeriodIndex) or s.index.freqstr!='Q-DEC':raise ValueError('Expected calendar quarters')
    s=s.sort_index().reindex(pd.period_range(s.index.min(),s.index.max(),freq='Q'))
    flow=pd.Series(np.nan,index=s.index,dtype=float);flags=[]
    for q,v in s.items():
        flag=[]
        if pd.isna(v):flag.append('MISSING_CUMULATIVE')
        elif q.quarter==1:flow.loc[q]=v
        elif pd.isna(s.get(q-1,np.nan)):flag.append('MISSING_PREVIOUS_QUARTER')
        else:flow.loc[q]=v-s.loc[q-1]
        if pd.notna(flow.loc[q]) and flow.loc[q]<=0:flag.append('NONPOSITIVE_STANDALONE')
        flags.append(';'.join(flag))
    prior=flow.shift(4);valid=flow.gt(0)&prior.gt(0)
    log=pd.Series(np.nan,index=s.index);pct=log.copy()
    log.loc[valid]=100*(np.log(flow.loc[valid])-np.log(prior.loc[valid]))
    pct.loc[valid]=100*(flow.loc[valid]/prior.loc[valid]-1)
    return pd.DataFrame(dict(quarter=s.index.astype(str),cumulative_nominal_gdp=s.to_numpy(),standalone_nominal_gdp=flow.to_numpy(),
        nominal_gdp_yoy_log=log.to_numpy(),nominal_gdp_yoy_pct=pct.to_numpy(),quality_flag=flags,unit='billion UZS')).set_index('quarter',drop=False)
