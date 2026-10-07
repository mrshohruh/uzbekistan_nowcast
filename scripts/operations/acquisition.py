"""Approved source adapters and observation-level acceptance decisions."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import shutil
import numpy as np
import pandas as pd
from uznowcast.io.http import Downloader
from uznowcast.io import siat, cbu, cbu_stats, external
from uznowcast.provenance import attach_provenance
from uznowcast.parsers.siat import parse_siat
from uznowcast.parsers.cbu import parse_m2_xlsx, deduplicate_daily
from uznowcast.parsers.cbu_stats import parse_reserves_xlsx
from uznowcast.parsers.external import parse_world_bank_gold
from uznowcast.transforms.growth import log_growth, gdp_target
from uznowcast.transforms.decumulate import decumulate_ytd
from uznowcast.transforms.frequency import fx_monthly
from uznowcast.transforms.prices import monthly_index_log
from uznowcast.archive_series import build_payment_archive
from uznowcast.validation.observations import validate_series
from scripts.operations.state import sha, read, write

ACTIVE=('industrial_production','ppi','usd_uzs','rub_uzs','gold_price','m2','fx_reserves_ex_gold','pos_turnover')
CHANGE_COLUMNS=['variable','period','old_value','new_value','change_type','absolute_change','relative_change','accepted','reason']
RECEIPT_COLUMNS=['variable','source','retrieval_timestamp','source_reference','http_status','raw_file','sha256','latest_observation','status']


def critical_validation_error(variable,error):
    # HTTP/unreachable sources may leave a usable retained information set.
    # A decoded critical signal with a changed schema/unit must abort promotion.
    return variable=='usd_uzs' and isinstance(error,ValueError) and not str(error).startswith(('HTTP ','Offline cache missing'))


class OperationsDownloader(Downloader):
    """Reuse approved HTTP/retry/parser contracts without crawling research JSON payloads as receipts."""
    def __init__(self, root, staging, run_id, force=()):
        super().__init__(staging,run_id,offline=False,refresh=True,delay=.2)
        self.root=root;self.archive=root/'data/raw/current_updates'/run_id
        self.receipts=[];self.archived={};self.force=set(force)
        logs=pd.read_parquet(root/'metadata/download_log.parquet')
        good=logs.loc[logs.http_status.eq(200) & logs.raw_file_path.notna()]
        for r in good.sort_values('retrieved_at').to_dict('records'):
            self.cache[(r['variable_key'],r['source_url'])]=r

    def event(self, record):
        super().event(record)
        if record.get('raw_file_path'):
            self.archive_meta(record)

    def archive_meta(self, meta):
        key=(meta['raw_file_path'],str(meta['retrieved_at']))
        if key in self.archived:return self.archived[key]
        path=self.root/meta['raw_file_path']
        if sha(path)!=meta['checksum']:raise ValueError('Source archive checksum mismatch')
        folder=self.archive/meta['variable_key'];folder.mkdir(parents=True,exist_ok=True)
        payload=folder/path.name
        if not payload.exists():shutil.copyfile(path,payload)
        result=dict(meta,raw_file_path=payload.relative_to(self.root).as_posix())
        write(payload.with_suffix('.json'),result)
        self.receipts.append(dict(variable=meta['variable_key'],source=meta['provider'],retrieval_timestamp=meta['retrieved_at'],
            source_reference=meta['source_url'],http_status=meta.get('http_status'),raw_file=result['raw_file_path'],sha256=meta['checksum'],
            latest_observation=None,status=meta.get('status','ARCHIVED')))
        self.archived[key]=result
        return result

    def get(self,row,url,**kwargs):
        obj,meta=super().get(row,url,**kwargs)
        return obj,self.archive_meta(meta)

    def get_bytes(self,row,url,**kwargs):
        obj,meta=super().get_bytes(row,url,**kwargs)
        return obj,self.archive_meta(meta)


def real_industry_contract(root, registry):
    """Pin the already-approved SIAT 577 descriptor from actual archived receipts."""
    approved_url=read(root/'config/industry_source.json')['approved_descriptor_url']
    row=dict(registry.rows['industrial_production'],native_indicator_dataset_id='1.02.01.0004',
        machine_download_url=approved_url,native_frequency='Monthly',raw_unit='Percent',
        row_field_selector='Code=1700 AND Klassifikator_en=Republic of Uzbekistan',rule_codes=['PUBLISHED_REAL_INDEX_MINUS_100'],
        required_transformation='Published real cumulative growth index minus 100; NOT de-cumulated',clean_model_field='industrial_production')
    contract=dict(registry_selector=row['row_field_selector'],registry_unit='Percent',code='1700',label='Republic of Uzbekistan',
        frequency='monthly',unit='Percent',rule_codes=row['rule_codes'],table_id='577',
        indicator_code='1.02.01.0004',indicator_name='Index of the physical volume of industrial production (monthly)')
    return row,contract


def approved_real_industry(client,row,contract):
    """Check descriptor/table identity independently of the internal indicator code.

    Both URLs and the metadata contract are evidenced by the Phase 6A2 archived
    SIAT 577 descriptor/payload, not inferred from a numeric indicator code.
    """
    url=urlparse(row['machine_download_url'])
    if (url.scheme!='https' or url.netloc!='api.siat.stat.uz' or
        url.path!=f'/sdmx/{contract["table_id"]}/table/download/' or
        parse_qs(url.query)!={'download_format':['json']}):
        raise ValueError('Approved industrial SIAT table/descriptor identity mismatch')
    descriptor,descriptor_meta=client.get(row,row['machine_download_url'])
    expected=f'https://api.siat.stat.uz/media/uploads/sdmx/sdmx_data_{contract["table_id"]}.json'
    if not isinstance(descriptor,dict) or descriptor.get('file')!=expected or not descriptor.get('updated_at'):
        raise ValueError('Approved industrial SIAT descriptor resolved to a different table/schema')
    release=pd.Timestamp(descriptor['updated_at']).isoformat()
    basis='dataset_update_timestamp; not historical first release'
    payload,meta=client.get(row,expected,source_release_date=release,source_release_basis=basis)
    if not isinstance(payload,list) or len(payload)!=1 or not isinstance(payload[0],dict):
        raise ValueError('Approved industrial SIAT payload schema changed')
    names={m.get('value_en') for m in payload[0].get('metadata',[]) if m.get('name_en')=='Indicator name'}
    if names!={contract['indicator_name']} or row['native_indicator_dataset_id']!=contract['indicator_code']:
        raise ValueError('Approved industrial SIAT indicator name/code contract mismatch')
    # The unchanged strict parser checks internal code, unit, frequency, national
    # selector, dimensions, numeric values and duplicates.
    frame=parse_siat(payload,row,contract)
    meta=dict(meta,descriptor_raw_file_path=descriptor_meta['raw_file_path'],source_release_date=release,source_release_basis=basis)
    frame=attach_provenance(frame,row,meta)
    frame['siat_table_id']=contract['table_id'];frame['siat_indicator_code']=contract['indicator_code']
    frame['clean_value']=frame.raw_value-100
    return frame


def acquire(key,client,registry,root,asof,*,real=False):
    row=dict(registry.rows[key]);contracts=read(root/'config/siat_contracts.json')
    if real:
        row,contract=real_industry_contract(root,registry)
        frame=approved_real_industry(client,row,contract)
    elif row['provider']=='SIAT':
        payload,meta=siat.download(client,row)
        frame=attach_provenance(parse_siat(payload,row,contracts[key]),row,meta)
        if key=='gdp_real_yoy':frame=gdp_target(frame)
        elif row['rule_codes']==['DECUM_YTD','FLOW_YOY_LOG']:
            frame=log_growth(decumulate_ytd(frame,3.),'monthly_flow',12,50.)
        elif row['rule_codes']==['MOM_INDEX_LOG']:frame=monthly_index_log(frame)
        else:raise ValueError('Unapproved SIAT transformation chain')
    elif key in {'usd_uzs','rub_uzs'}:
        old=pd.read_parquet(root/f'data/processed/{key}_daily.parquet')
        # Retrieve every activation in the overlapping month; combine with retained daily history.
        start=(pd.Timestamp(old.reference_date.max())-pd.Timedelta(days=35)).to_period('M').start_time
        latest=cbu.download(client,row,str(start.date()),str(asof.date()),currency=key.split('_')[0].upper())
        combined=pd.concat([old,latest],ignore_index=True).sort_values('retrieved_at').drop_duplicates('reference_date',keep='last')
        daily=deduplicate_daily(combined.sort_values('reference_date').reset_index(drop=True))
        if not np.isfinite(daily.normalized_daily).all() or daily.normalized_daily.le(0).any():raise ValueError('Invalid daily FX rate')
        frame=fx_monthly(daily,str(pd.Timestamp(daily.reference_date.min()).date()),str(asof.date()),50.)
        frame.attrs['daily']=daily
    elif key=='m2':
        content,meta=cbu.download_m2(client,row)
        frame=log_growth(attach_provenance(parse_m2_xlsx(content,row,read(root/'config/cbu_contracts.json')[key]),row,meta),'raw_value',12,50.)
    elif key=='fx_reserves_ex_gold':
        content,meta=cbu_stats.download_reserves(client,row)
        frame=log_growth(attach_provenance(parse_reserves_xlsx(content,row),row,meta),'raw_value',12,50.)
    elif key=='gold_price':
        content,meta=external.download_world_bank_gold(client,row)
        parsed,release=parse_world_bank_gold(content,row)
        meta=dict(meta,source_release_date=release,source_release_basis='Official workbook update; not first release')
        frame=log_growth(attach_provenance(parsed,row,meta),'raw_value',1,50.)
    elif key=='pos_turnover':
        frame,_=build_payment_archive(client,row)
    else:raise ValueError('Unapproved source: '+key)
    frame['clean_model_field']=row['clean_model_field']
    validate_series(frame,row)
    return frame


def equal(a,b):
    return (pd.isna(a) and pd.isna(b)) or (pd.notna(a) and pd.notna(b) and float(a)==float(b))


def compare(variable,old,new,asof,*,gdp=False,pos=False,verified_gdp=()):
    """Retain disappeared values and reject suspicious candidates without repairs."""
    if new.reference_period.duplicated().any():raise ValueError('Duplicate candidate periods')
    if not new.reference_date.is_monotonic_increasing:raise ValueError('Unsorted candidate periods')
    expected='Q' if gdp else 'M'
    if set(new.frequency)!={expected}:raise ValueError('Frequency changed')
    old_by=old.set_index('reference_period') if len(old) else old
    new_by=new.set_index('reference_period');changes=[];rejected=False;accepted_periods=[]
    local=asof.tz_convert('Asia/Tashkent').tz_localize(None) if asof.tzinfo else asof
    for period in sorted(set(old_by.index)|set(new_by.index)):
        a=old_by.loc[period] if period in old_by.index else None
        b=new_by.loc[period] if period in new_by.index else None
        old_value=a.clean_value if a is not None else np.nan
        new_value=b.clean_value if b is not None else np.nan
        same=b is not None and a is not None and equal(a.raw_value,b.raw_value) and equal(old_value,new_value)
        if variable=='industrial_production_approved_real' and b is not None and a is not None and equal(a.raw_value,b.raw_value):
            # The approved CSV's decimal serialization loses a few ULPs. Only
            # identical published indices with an old value consistent with the
            # frozen index-minus-100 formula qualify; retain the old bytes/value.
            tolerance=2*np.spacing(max(abs(float(b.raw_value)),1.))
            same=same or (equal(new_value,b.raw_value-100) and
                          np.isclose(old_value,new_value,rtol=0,atol=tolerance))
        kind='UNCHANGED' if same else 'MISSING_IN_NEW_SOURCE' if b is None else 'REVISION' if a is not None else 'NEW_OBSERVATION'
        accepted=kind in {'REVISION','NEW_OBSERVATION'};reason='Retain old provenance' if same else 'Validated source observation'
        if b is None:accepted=False;reason='Source omission never deletes history'
        partial_fx=(b is not None and variable in {'usd_uzs','rub_uzs'} and
                    pd.Period(period,'M')==local.to_period('M') and
                    local.normalize()<pd.Period(period,'M').end_time.normalize())
        if b is not None and (not same or partial_fx):
            freq=pd.Period(period,freq=expected)
            bad=(not np.isfinite(b.raw_value) or b.raw_value<=0 or
                 freq>local.to_period(expected) or (expected=='Q' and freq.end_time.normalize()>local.normalize()))
            release=pd.to_datetime(b.get('source_release_date'),utc=True,errors='coerce')
            retrieval=pd.to_datetime(b.get('retrieved_at'),utc=True,errors='coerce')
            cutoff=asof.tz_localize('UTC') if asof.tzinfo is None else asof.tz_convert('UTC')
            if pd.isna(retrieval) or retrieval>cutoff or (pd.notna(release) and release>cutoff):
                bad=True
            flags=str(b.get('quality_flag',''))
            extreme='extreme' in flags or (pd.notna(new_value) and abs(new_value)>50)
            if bad or extreme:
                kind='INVALID';accepted=False;reason='FAIL: nonpositive/nonfinite, future timing or extreme change requires review';rejected=True
            elif partial_fx or (variable in {'usd_uzs','rub_uzs'} and 'partial' in flags):
                kind='PARTIAL_CURRENT_MONTH' if partial_fx else 'INCOMPLETE_PERIOD'
                accepted=False;reason='Daily FX archived; incomplete monthly mean/change withheld from completed-month observations'
            elif pd.isna(new_value) and not any(word in flags for word in ['missing_growth','partial','missing_previous','missing_lag']):
                kind='INVALID';accepted=False;reason='FAIL: unexplained missing transformed value';rejected=True
            elif gdp and period not in verified_gdp:
                accepted=False;reason='GDP_VALUE_DETECTED_UNVERIFIED: master/realization requires documented first-release review'
            elif pos and freq>pd.Period('2024-12','M') and not (isinstance(b.get('scope_verified'),(bool,np.bool_)) and bool(b['scope_verified'])):
                accepted=False;reason='SCOPE_VERIFICATION_REQUIRED: POS/E-POS definition boundary; not substituted or filled'
            else:accepted_periods.append(period)
        changes.append(dict(variable=variable,period=period,old_value=old_value,new_value=new_value,change_type=kind,
            absolute_change=new_value-old_value if pd.notna(new_value) and pd.notna(old_value) else None,
            relative_change=(new_value-old_value)/abs(old_value) if pd.notna(old_value) and old_value!=0 and pd.notna(new_value) else None,
            accepted=accepted,reason=reason))
    if rejected:
        for row in changes:
            if row['accepted']:row.update(accepted=False,reason='Series withheld because another candidate observation failed validation')
        return old.copy(),changes,False
    if not accepted_periods:
        return old.copy(),changes,True
    merged=pd.concat([old.loc[~old.reference_period.isin(accepted_periods)],new.loc[new.reference_period.isin(accepted_periods)]],ignore_index=True)
    merged=merged.sort_values('reference_date').reset_index(drop=True)
    return merged,changes,True
