"""Reviewed GDP extraction ledger tied to archived official source bytes."""
import json
import re
from pathlib import Path
import hashlib
from urllib.parse import urlparse,parse_qs,urljoin
import pandas as pd
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'results/research/phase6b2'
EVIDENCE=OUT/'evidence'
CONVENTION='CUMULATIVE_YEAR_TO_DATE_REAL_GDP_YOY_PERCENT; published volume index minus 100'

# Quarter, archived report ID, dated landing page ID (or explicit printed date),
# reviewed real-growth values in year order, page selector. No filename dates.
LEDGER=[
 ('2020Q3','d152b932ed5f22817e6b','d840d613e6675ba52490',{2018:5.7,2019:5.9,2020:.4},'PDF p1 physical-volume index chart'),
 ('2020Q4','732d48ef11b6c735791f','4eb240a20488a58001eb',{2018:5.4,2019:5.8,2020:1.6},'PDF pp2-3 national GDP and growth-rate chart'),
 ('2021Q1','73384989a17d7f971236','952b52032c5beea1b54e',{2019:6.,2020:4.6,2021:3.},'PDF pp2-3 prose and national GDP chart'),
 ('2021Q2','27a56959afe86de3541c','fe817776d43cd907149e',{2019:5.8,2020:1.1,2021:6.2},'PDF pp2-3 prose and national GDP chart'),
 ('2021Q3','d15a6239e34a90f34d4b','fd509014f95b8e3b24f4',{2019:5.6,2020:.8,2021:6.9},'PDF pp2,4 prose and national GDP chart'),
 ('2021Q4','01aa76fbe460ec6689ff','0fba4d743734fca37a1e',{2019:5.7,2020:1.9,2021:7.4},'PDF pp2,4 prose and national GDP chart'),
 ('2022Q1','229e56fb11a24ccd1e21','6cec42fe536006e8410b',{2020:4.8,2021:2.6,2022:5.8},'PDF pp2,4 prose explicitly maps years'),
 ('2022Q2','a45cdfcd13382a5dc5a9','76bb265e75348144a74d',{2020:1.,2021:7.2,2022:5.4},'PDF pp2,4 prose explicitly maps years'),
 ('2022Q3','97312a1df55545d0646a','7db8e40324882ffc06b1',{2018:5.5,2019:5.6,2020:.5,2021:7.4,2022:5.8},'PDF p2 national GDP growth chart'),
 ('2022Q4','9953abb13b11fe5a5ed9','745f19ec4ade3f08d942',{2018:5.5,2019:6.,2020:2.,2021:7.4,2022:5.7},'PDF p2 national GDP growth chart'),
 ('2023Q1','a6cac86b0ffaeab7e3e6','b817a89d4174371b939c',{2019:6.1,2020:3.2,2021:5.6,2022:6.1,2023:5.5},'PDF p2 national GDP growth chart'),
 ('2023Q2','efa3a95c2a9f76fda50f','426de4a6cc9c8497866e',{2019:6.,2020:1.4,2021:7.2,2022:5.4,2023:5.6},'PDF p2 national GDP growth chart'),
 ('2023Q3','48be31d60f1a49169da2','999f933fdb51ec570ccf',{2019:5.9,2020:.7,2021:7.6,2022:6.2,2023:5.8},'PDF p2 national GDP growth chart'),
 ('2024Q1','feb4e1c53084506c1f7f','185651d727d45d5c6549',{2020:5.6,2021:3.2,2022:6.2,2023:5.7,2024:6.2},'PDF p2 national GDP chart as printed; 2020/2021 ordering suspect'),
 ('2024Q2','614d9ba012eb2fac114f','5bc5df1dec8c841baa9b',{2020:1.4,2021:7.2,2022:4.8,2023:6.2,2024:6.4},'PDF p2 national GDP growth chart'),
 ('2024Q3','458e2f05d55dc5fdc11c','13c799227663edb91e3a',{2020:0.,2021:8.8,2022:5.3,2023:6.5,2024:6.6},'PDF p2 chart; non-observed economy revision'),
 ('2024Q4','ddde7482e4e017e566f0','3439df5103c78cdf37e8',{2020:1.6,2021:8.,2022:6.,2023:6.3,2024:6.5},'PDF p2 chart; non-observed economy revision'),
 ('2025Q1','5ffbd345a35a19e7a703','2025-04-29',{2021:4.8,2022:5.1,2023:6.4,2024:6.4,2025:6.8},'PDF p1 national GDP chart and printed release date'),
 ('2025Q2','0ba6374371d3051c3750','2025-07-28',{2021:8.4,2022:4.5,2023:7.1,2024:6.6,2025:7.2},'PDF p1 national GDP chart and printed release date'),
 ('2025Q3','dfe1dffa9232353598d2','2025-10-28',{2021:8.8,2022:5.3,2023:6.5,2024:6.6,2025:7.6},'PDF p1 national GDP chart and printed release date'),
 ('2025Q4','117bcee322cfaef39629','2026-01-26',{2021:8.2,2022:6.1,2023:6.3,2024:6.7,2025:7.7},'PDF p1 national GDP chart and printed release date'),
 ('2026Q1','40213b344e8ab0cb19e6','2026-04-27',{2022:5.1,2023:6.4,2024:6.4,2025:6.8,2026:8.7},'PDF p1 national GDP chart and printed release date'),
 ('2026Q2','aacee5857aaccbeddac0','2026-07-30',{2022:4.5,2023:7.1,2024:6.6,2025:7.2,2026:8.5},'PDF p1 national GDP chart and printed release date'),
]
# Dated standalone GDP text. These precede some embedded reports.
ARTICLES=[('2023Q4','a5468ce2389464ed5370',6.),('2022Q2','50121a8d635b63c7c999',5.4),
          ('2024Q2','a95c4ecb5b56e5cf487a',6.4),('2025Q3','b7bb887034fe724304cf',7.6)]

def metadata(key):
    m=json.loads((EVIDENCE/(key+'.json')).read_text(encoding='utf-8'))
    assert hashlib.sha256((ROOT/m['raw_file_path']).read_bytes()).hexdigest()==m['sha256']
    return m

def article_info(key):
    m=metadata(key)
    soup=BeautifulSoup((ROOT/m['raw_file_path']).read_bytes(),'html.parser')
    article=soup.select_one('div.item-page')
    title=article.select_one('[itemprop=headline]').get_text(' ',strip=True)
    date=pd.to_datetime(article.select_one('p.text-gray-600').get_text(' ',strip=True)).date().isoformat()
    return title,date,article.get_text(' ',strip=True)

def reconstruct():
    events=[]
    for target,key,datekey,values,selector in LEDGER:
        m=metadata(key)
        if len(datekey)==10:
            date=datekey; date_url=m['source_url'];date_basis='PRINTED_OFFICIAL_PDF_RELEASE_DATE'
            title=m['source_title'] or ' '.join((EVIDENCE/(key+'.txt')).read_text(encoding='utf-8').split()[:60])
        else:
            title,date,_=article_info(datekey)
            landing=metadata(datekey)
            # Validate actual iframe URL, not a presumed relationship from report period.
            soup=BeautifulSoup((ROOT/landing['raw_file_path']).read_bytes(),'html.parser')
            urls=[urljoin(landing['source_url'],parse_qs(urlparse(t['src']).query).get('file',[t['src']])[0]) for t in soup.select('div.item-page iframe[src]')]
            if m['source_url'] not in urls:
                # Identical report copies in annual catalogue can differ in URL.
                hashes=[metadata(hashlib.sha256(u.encode()).hexdigest()[:20])['sha256'] for u in urls]
                assert m['sha256'] in hashes,('Unproven report/date relationship',target,key,urls)
            date_url=landing['source_url'];date_basis='DATED_OFFICIAL_LANDING_PAGE_WITH_EMBEDDED_REPORT'
        quarter=int(target[-1])
        for year,value in values.items():
            q=f'{year}Q{quarter}'
            quality='SOURCE_CHART_ORDER_SUSPECT' if target=='2024Q1' and year in [2020,2021] else 'VERIFIED_PUBLISHED_VALUE_IN_PARTIAL_ARCHIVE'
            events.append(dict(quarter=q,publication_date=date,publication_time=None,time_verified=False,value=value,
                value_verified=True,date_verified=True,source_url=m['source_url'],source_title=title,
                date_source_url=date_url,date_basis=date_basis,sha256=m['sha256'],raw_file_path=m['raw_file_path'],
                retrieved_at=m['retrieved_at'],selector=selector,quality=quality,is_first_candidate=(q==target)))
    for q,key,value in ARTICLES:
        m=metadata(key);title,date,text=article_info(key)
        assert re.search(str(value).rstrip('0').rstrip('.')+r'\s*%',text) or str(value).rstrip('0').rstrip('.')+' %' in text
        events.append(dict(quarter=q,publication_date=date,publication_time=None,time_verified=False,value=value,
            value_verified=True,date_verified=True,source_url=m['source_url'],source_title=title,date_source_url=m['source_url'],
            date_basis='DATED_OFFICIAL_ARTICLE_BODY',sha256=m['sha256'],raw_file_path=m['raw_file_path'],
            retrieved_at=m['retrieved_at'],selector='Article body: national real GDP growth',
            quality='VERIFIED_PUBLISHED_VALUE_IN_PARTIAL_ARCHIVE',is_first_candidate=True))
    f=pd.DataFrame(events).sort_values(['quarter','publication_date','source_url'])
    # Multiple official copies on one date are corroboration, not duplicate vintages.
    for _,g in f.groupby(['quarter','publication_date']):
        assert g.value.nunique()==1,'Conflicting same-day published GDP'
    f=f.drop_duplicates(['quarter','publication_date'],keep='first').reset_index(drop=True)
    f['previous_documented_value']=f.groupby('quarter').value.shift()
    f['documented_revision']=f.value-f.previous_documented_value
    f['event_kind']=f.is_first_candidate.map({True:'FIRST_RELEASE_CANDIDATE',False:'LATER_DOCUMENTED_VINTAGE'})
    f.to_csv(OUT/'phase6b2_gdp_revision_history.csv',index=False,float_format='%.12g')
    master=pd.read_parquet(ROOT/'data/master/gdp_quarterly.parquet')
    registry=[]
    for row in master.itertuples():
        g=f.loc[f.quarter.eq(row.quarter)]
        first=g.loc[g.is_first_candidate].sort_values('publication_date')
        r=first.iloc[0].to_dict() if len(first) else {}
        later=g.loc[g.publication_date.gt(r.get('publication_date','9999-01-01'))]
        registry.append(dict(quarter=row.quarter,reference_period=row.quarter,target_convention=CONVENTION,
            first_release_date=r.get('publication_date'),first_release_time_if_available=None,first_release_value=r.get('value'),
            first_release_source_url=r.get('source_url'),first_release_page_title=r.get('source_title'),
            source_publication_date=r.get('publication_date'),source_type=r.get('date_basis'),retrieved_at=r.get('retrieved_at'),
            release_date_verified=bool(r),release_time_verified=False,first_release_value_verified=bool(r),
            current_master_value=row.gdp_real_yoy_pct,
            revision_from_first_release=row.gdp_real_yoy_pct-r['value'] if r else None,
            later_revision_dates_if_identifiable=json.dumps(later.publication_date.tolist()),
            later_revision_values_if_identifiable=json.dumps(later.value.tolist()),
            vintage_quality='EARLIEST_VERIFIABLE_RELEASE_PARTIAL_REVISION_ARCHIVE' if r else 'FIRST_RELEASE_UNRESOLVED',
            notes='Earliest found dated official publication; intervening revision completeness not established. Undated PDFs and filename dates never used as historical availability.'))
    registry=pd.DataFrame(registry)
    registry.to_csv(OUT/'phase6b2_gdp_vintage_registry.csv',index=False,float_format='%.12g')
    sources=[]
    for p in EVIDENCE.glob('*.json'):
        m=json.loads(p.read_text(encoding='utf-8'))
        if not isinstance(m,dict) or 'raw_file_path' not in m:
            continue
        usage=f.loc[f.source_url.eq(m['source_url'])|f.date_source_url.eq(m['source_url'])]
        source_date=None
        if m['raw_file_path'].endswith('.html'):
            soup=BeautifulSoup((ROOT/m['raw_file_path']).read_bytes(),'html.parser')
            page=soup.select_one('div.item-page')
            if page is not None and page.select_one('p.text-gray-600') is not None and page.select_one('[itemprop=headline]') is not None:
                m['source_title'],source_date,_=article_info(p.stem)
        sources.append(dict(**m,source_publication_date=source_date,source_type='PDF' if m['raw_file_path'].endswith('.pdf') else 'HTML',
            source_publication_dates=json.dumps(sorted(usage.publication_date.unique().tolist())),
            GDP_quarters=json.dumps(sorted(usage.quarter.unique().tolist())),used_in_vintage_accessor=bool(len(usage)),
            evidence_role='VERIFIED_PUBLICATION_EVENT' if len(usage) else 'DISCOVERY_OR_UNDATED_REPORT_NOT_HISTORICAL_AVAILABILITY'))
    pd.DataFrame(sources).sort_values('source_url').to_csv(OUT/'phase6b2_gdp_release_sources.csv',index=False)
    return registry,f

if __name__=='__main__':
    r,f=reconstruct()
    print('Verified first releases',int(r.release_date_verified.sum()),'of',len(r),'documented events',len(f))
