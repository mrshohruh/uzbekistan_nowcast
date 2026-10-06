"""Cross-check archived SIAT, processed GDP, master and publication vintages."""
import json
import numpy as np
import pandas as pd
from scripts.phase6g3.protection import ROOT, OUT
from scripts.phase6f.experiment import sha, dump


def real_audit():
    processed=pd.read_parquet(ROOT/'data/processed/gdp_real_yoy.parquet').set_index('reference_period')
    master=pd.read_parquet(ROOT/'data/master/gdp_quarterly.parquet').set_index('quarter')
    registry=pd.read_csv(ROOT/'results/research/phase6b2/phase6b2_gdp_vintage_registry.csv').set_index('quarter')
    observations=[];sources={}
    for path in processed.raw_file_path.unique():
        p=ROOT/path
        expected=set(processed.loc[processed.raw_file_path.eq(path),'checksum'])
        if expected!={sha(p)}:raise ValueError('Real GDP raw checksum mismatch')
        payload=json.loads(p.read_bytes());rows=payload[0]['data']
        selected=[r for r in rows if r.get('Code')=='1700' and r.get('Klassifikator_en')=='Republic of Uzbekistan']
        if len(selected)!=1:raise ValueError('Real GDP national selector changed')
        metadata=payload[0]['metadata']
        codes={m.get('value_en') for m in metadata if m.get('name_en')=='Indicator identification number (code)'}
        if codes!={'1.01.01.0059'}:raise ValueError('Wrong real GDP indicator')
        sources[path]=selected[0]
    for q in pd.period_range('2018Q1',max(processed.index),freq='Q').astype(str):
        if q not in processed.index:raise ValueError('Missing processed real GDP quarter '+q)
        r=processed.loc[q];raw=sources[r.raw_file_path][q.replace('Q','-Q')]
        target=float(master.loc[q,'gdp_real_yoy_pct'])
        consistent=bool(np.isclose(raw-100,r.clean_value,atol=1e-12,rtol=0) and np.isclose(target,r.clean_value,atol=1e-12,rtol=0))
        vr=registry.loc[q] if q in registry.index else None
        verified=bool(vr is not None and vr.first_release_value_verified and vr.release_date_verified)
        first=float(vr.first_release_value) if verified else np.nan
        observations.append(dict(quarter=q,raw_SIAT_value=raw,source_definition='Growth rates of Gross domestic product (production method, quarterly); constant-price volume index relative to corresponding YTD period',
            cumulative_or_standalone='CUMULATIVE_YEAR_TO_DATE',period_coverage=['January-March','January-June','January-September','January-December'][int(q[-1])-1],
            model_target_value=target,processed_target_value=r.clean_value,transformation_applied='published_index - 100',
            first_release_date=vr.first_release_date if verified else None,first_release_growth_value=first,
            current_revised_status='CURRENT_SIAT_REVISED_SNAPSHOT_NON_OBSERVED_ECONOMY_SNA2008',revision_from_documented_first=target-first if verified else np.nan,
            internally_consistent=consistent,raw_file_path=r.raw_file_path,checksum=r.checksum,source_url=r.source_url,
            source_indicator=r.source_id,source_update_timestamp=r.source_release_date,source_update_is_first_release=False,retrieved_at=r.retrieved_at,
            source_notes=r.source_notes,model_target_convention='YTD real GDP YoY percent, quarter-end indexed; not standalone-quarter YoY',
            conceptual_finding='PERIOD_DEFINITION_DIFFERENCE: requested nominal target is standalone, current real target is YTD'))
    f=pd.DataFrame(observations);f.to_csv(OUT/'gdp_target_audit.csv',index=False,float_format='%.17g')
    dump(OUT/'gdp_lineage.json',dict(source_page='https://siat.stat.uz/data/3698/?lang=en',indicator='1.01.01.0059',dataset='3698',selector='Code=1700, Klassifikator_en=Republic of Uzbekistan',
        route=['registry row -> SIAT official download descriptor -> archived national wide payload','src/uznowcast/parsers/siat.py:parse_siat',
            'src/uznowcast/transforms/growth.py:gdp_target (raw_value - 100)','data/processed/gdp_real_yoy.parquet -> data/master/gdp_quarterly.parquet',
            'dated official report/article -> verified Phase6B2 publication events -> available_gdp_vintage_as_of STRICT -> GDP bridge training/prior quarter',
            'frozen evaluation actual from existing first-release framework'],
        transformation_consistent=bool(f.internally_consistent.all()),quarters=len(f),first_releases_unknown=int(f.first_release_date.isna().sum()),
        arithmetic_issue=False,period_definition_issue='YTD cumulative reporting periods differ from standalone-quarter interpretation; already documented by Phase6B2',
        proposed_registry_clarification='Explicitly label GDP clean target as cumulative YTD real YoY at quarterly reporting frequency. A standalone-real target requires official quarterly volume levels/weights; never subtract YoY rates.',
        registry_amended=False))
    return f
