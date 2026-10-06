"""Reviewed nominal levels from dated, immutable official GDP reports.

Historical dates come from the existing verified landing-page/PDF date evidence.
These are published cumulative levels, not inferred from growth or a deflator.
"""
import json
import re
import numpy as np
import pandas as pd
from scripts.research.phase6b2.evidence import LEDGER, metadata, article_info
from scripts.phase6g3.nominal import transform
from scripts.phase6g3.protection import ROOT, OUT
from scripts.phase6f.experiment import sha

# Reviewed exact national GDP table/level-chart values, billion UZS.
# Early tables alternate nominal levels with volume indices; only levels selected.
LEVELS={
 '2020Q3':{2018:290002.0,2019:363997.3,2020:408296.6},
 '2020Q4':{2018:406648.5,2019:510117.2,2020:580203.2},
 '2021Q1':{2019:93036.3,2020:112503.3,2021:128556.8},
 '2021Q2':{2019:231713.8,2020:266348.2,2021:318472.0},
 '2021Q3':{2019:378442.1,2020:428137.7,2021:519825.1},
 '2021Q4':{2019:529391.4,2020:602193.0,2021:734587.7},
 '2022Q1':{2020:117132.3,2021:133905.4,2022:162784.6},
 '2022Q2':{2020:265941.9,2021:320817.8,2022:389631.2},
 '2022Q3':{2018:304010.8,2019:378442.1,2020:426971.1,2021:520839.6,2022:627476.9},
 '2022Q4':{2018:426641.0,2019:532712.5,2020:605514.9,2021:738425.2,2022:888341.7},
 '2023Q1':{2019:98744.4,2020:117981.0,2021:136053.8,2022:166985.0,2023:198483.5},
 '2023Q2':{2019:233451.5,2020:267679.7,2021:323036.6,2022:397340.4,2023:469619.0},
 '2023Q3':{2019:380930.2,2020:429489.1,2021:523669.6,2022:638338.5,2023:750925.7},
 '2024Q1':{2020:117981.0,2021:136053.8,2022:167932.1,2023:201680.0,2024:242701.6},
 '2024Q2':{2020:267679.7,2021:323036.6,2022:398875.5,2023:473790.7,2024:567364.3},
 '2024Q3':{2020:473124.6,2021:582260.0,2022:707857.0,2023:842711.4,2024:1015331.8},
 '2024Q4':{2020:668038.0,2021:820536.6,2022:995573.1,2023:1204485.4,2024:1454573.9},
 '2025Q1':{2024:276923.5,2025:333592.7},
 '2025Q2':{2024:670065.5,2025:807937.1},
 '2025Q3':{2024:1079875.5,2025:1303702.1},
 '2025Q4':{2024:1535431.7,2025:1849650.0},
 '2026Q1':{2025:372829.9,2026:447935.3},
 '2026Q2':{2025:900694.2,2026:1072670.1},
}


def evidence_events():
    records=[]
    for target,key,datekey,_,_ in LEDGER:
        m=metadata(key)
        text=(ROOT/'results/research/phase6b2/evidence'/(key+'.txt')).read_text(encoding='utf8')
        if 'billion' not in text.lower() or 'soums' not in text.lower():raise ValueError('Nominal report unit changed')
        if len(datekey)==10:
            date=datekey;date_url=m['source_url'];basis='PRINTED_OFFICIAL_PDF_RELEASE_DATE'
        else:
            _,date,_=article_info(datekey);date_url=metadata(datekey)['source_url'];basis='DATED_OFFICIAL_LANDING_PAGE_WITH_EMBEDDED_REPORT'
        for year,value in LEVELS[target].items():
            # Every reviewed decimal must remain recoverable in the archived text.
            digits=f'{value:.1f}'.split('.')
            pattern=r'(?<!\d)'+r'\s*'.join(digits[0])+r'\s*[,.]\s*'+digits[1]+r'(?!\d)'
            if not re.search(pattern,text):raise ValueError(f'Nominal reviewed value not found: {target} {year} {value}')
            records.append(dict(quarter=f'{year}Q{target[-1]}',publication_date=date,value=value,
                source_url=m['source_url'],date_source_url=date_url,date_basis=basis,checksum=m['sha256'],raw_file_path=m['raw_file_path'],
                retrieved_at=m['retrieved_at'],unit='billion UZS',publication_time=None,time_verified=False,
                selector=f'National GDP level table/level chart; {year}, January through Q{target[-1]}; billion soums',
                precision_billion_UZS=.1,source_report_quarter=target))
    # Official dated article supplies a rounded FY2023 nominal release, not exact SIAT data.
    key='a5468ce2389464ed5370';m=metadata(key);_,date,text=article_info(key)
    if not re.search(r'1,066\.6\s+trillion',text):raise ValueError('FY2023 nominal article schema changed')
    records.append(dict(quarter='2023Q4',publication_date=date,value=1066600.,source_url=m['source_url'],date_source_url=m['source_url'],
        date_basis='DATED_OFFICIAL_ARTICLE_BODY',checksum=m['sha256'],raw_file_path=m['raw_file_path'],retrieved_at=m['retrieved_at'],
        unit='billion UZS',publication_time=None,time_verified=False,selector='Article body: GDP current prices 1,066.6 trillion UZS * 1000',
        precision_billion_UZS=100.,source_report_quarter='2023Q4'))
    events=pd.DataFrame(records).sort_values(['quarter','publication_date'])
    if events.duplicated(['quarter','publication_date']).any():raise ValueError('Conflicting nominal vintage event')
    events['previous_documented_value']=events.groupby('quarter').value.shift()
    events['revision']=events.value-events.previous_documented_value
    return events


def available(events, origin, target=None):
    """Strict date-only eligibility exactly mirrors the clean GDP accessor.

    Retrieval is provenance of an archived dated publication, not a historical
    release date. Current SIAT revised snapshots never enter this accessor.
    """
    origin=pd.Timestamp(origin)
    f=events.loc[pd.to_datetime(events.publication_date).dt.date<origin.date()].copy()
    if target is not None:f=f.loc[f.quarter.lt(target)]
    return f.sort_values(['quarter','publication_date']).drop_duplicates('quarter',keep='last').set_index('quarter')


def targets_as_of(events, origin, target):
    levels=available(events,origin,target)
    if levels.empty:return pd.DataFrame()
    transformed=transform(pd.Series(levels.value.to_numpy(),index=pd.PeriodIndex(levels.index,freq='Q')))
    rows=[]
    for q,r in transformed.iterrows():
        period=pd.Period(q,'Q')
        parents=[period,period-4]+([period-1,period-5] if period.quarter>1 else [])
        if pd.isna(r.nominal_gdp_yoy_log) or any(str(p) not in levels.index for p in parents):continue
        component=levels.loc[[str(p) for p in parents]]
        rows.append(dict(quarter=q,value=float(r.nominal_gdp_yoy_log),nominal_gdp_yoy_pct=float(r.nominal_gdp_yoy_pct),
            publication_date=component.publication_date.max(),parent_quarters=json.dumps([str(p) for p in parents]),
            parent_publication_dates=json.dumps(component.publication_date.to_dict()),parent_values=json.dumps(component.value.to_dict()),
            parent_checksums=json.dumps(component.checksum.to_dict()),parent_source_urls=json.dumps(component.source_url.to_dict()),
            mixed_publication_vintages=component.publication_date.nunique()>1,rounded_parent=bool(component.precision_billion_UZS.gt(.1).any())))
    return pd.DataFrame(rows).set_index('quarter') if rows else pd.DataFrame()
