"""Archive verified source URLs and their explicitly linked downloads."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import logging
import re
from urllib.parse import urljoin
import requests

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    'minenergy': 'https://gov.uz/oz/minenergy',
    'stat': 'https://stat.uz/',
    'siat': 'https://siat.stat.uz/data/2684/?lang=en',
    'siat_json': 'https://api.siat.stat.uz/sdmx/2684/table/download/?download_format=json',
    'het': 'https://www.het.uz/',
    'het_esg': 'https://het.uz/ru/pages/view/ESG',
    'het_reports': 'https://www.het.uz/oz/lists/view/2211',
    'grid': 'https://www.uzbekistonmet.uz/',
    'grid_archive': 'https://arxiv.uzbekistonmet.uz/oz',
    'ember': 'https://ember-energy.org/data/monthly-electricity-data/',
    'ember_csv': 'https://files.ember-energy.org/public-downloads/generation/outputs/release_generation_monthly_global.csv',
    'iea': 'https://www.iea.org/countries/uzbekistan/electricity',
    'households': 'https://gov.uz/oz/minenergy/news/view/19204',
    'daily_peak': 'https://gov.uz/oz/minenergy/news/view/70840',
}

def collect():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = ROOT/'data/research/electricity/raw'/stamp
    folder.mkdir(parents=True)
    logging.basicConfig(filename=ROOT/'results/phase7a/collection.log', level=logging.INFO)
    def fetch(item):
        name,url = item
        record = dict(source_name=name, source_url=url, retrieved_at=datetime.now(timezone.utc).isoformat(), parser_version='phase7a-1')
        try:
            response = requests.get(url, timeout=(10,45), headers={'User-Agent':'UzNowcast-Phase7A/1.0 research','Accept':'application/json' if name=='siat_json' else '*/*'})
            suffix = '.pdf' if '.pdf' in url else '.csv' if name=='ember_csv' else '.json' if name in ('siat_json','siat_payload') else '.html'
            path = folder/(name+suffix)
            path.write_bytes(response.content)
            record.update(http_status=response.status_code, content_type=response.headers.get('Content-Type'), raw_file=str(path.relative_to(ROOT)), checksum=hashlib.sha256(response.content).hexdigest(), schema_fingerprint=hashlib.sha256(str((response.headers.get('Content-Type'),suffix)).encode()).hexdigest(), bytes=len(response.content), status='OK' if response.ok and response.content else 'FAILED', final_url=response.url)
            if name=='het_esg':
                record['download_links'] = sorted(set(urljoin(response.url,x) for x in re.findall(r'href=[\"\x27]([^\"\x27]+)', response.text) if re.search(r'\.(pdf|xlsx?|docx?)(?:\?|$)',x,re.I)))
        except requests.RequestException as exc:
            record.update(status='FAILED',error_message=str(exc), http_status=None)
        logging.info(json.dumps(record))
        return record
    with ThreadPoolExecutor(max_workers=3) as pool:
        records=list(pool.map(fetch,SOURCES.items()))
    siat = next((r for r in records if r['source_name']=='siat_json'),None)
    if siat and siat['status']=='OK':
        descriptor=json.loads((ROOT/siat['raw_file']).read_text())
        records.append(fetch(('siat_payload',descriptor['file'])))
    for record in list(records):
        for i,url in enumerate(record.get('download_links',[])):
            # Preserve linked reports with their real extension.
            extra=fetch((f'het_download_{i}',url))
            records.append(extra)
    (folder/'download_manifest.json').write_text(json.dumps(records,indent=2),encoding='utf8')
    print(folder)
    for r in records: print(r['source_name'],r['status'],r.get('bytes'),r.get('download_links',''))
    return folder

if __name__=='__main__': collect()
