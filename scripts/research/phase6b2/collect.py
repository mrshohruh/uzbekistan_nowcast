"""Immutable, cached official evidence collection; no inferred release dates."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone
import time
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'results/research/phase6b2/evidence'

def archive(url):
    if not url.startswith(('https://stat.uz/', 'https://siat.stat.uz/', 'https://api.siat.stat.uz/')):
        raise ValueError('Unofficial evidence URL')
    key = hashlib.sha256(url.encode()).hexdigest()[:20]
    meta = OUT / (key + '.json')
    if meta.exists():
        record = json.loads(meta.read_text(encoding='utf-8'))
        assert hashlib.sha256((ROOT / record['raw_file_path']).read_bytes()).hexdigest() == record['sha256']
        if record['http_status']>=400:
            raise requests.HTTPError(f"Archived official source failure: {record['http_status']} {url}")
        return record
    session = requests.Session()
    session.headers['User-Agent'] = 'UzbekistanNowcastResearch/6B.2 (official GDP vintage audit)'
    for attempt in range(3):
        try:
            response = session.get(url, timeout=60)
            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()
            break
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    now = datetime.now(timezone.utc).isoformat()
    suffix = '.pdf' if response.content.startswith(b'%PDF') else '.html'
    raw = OUT / (key + suffix)
    raw.write_bytes(response.content)
    record = dict(source_url=url, response_url=response.url, retrieved_at=now,
                  http_status=response.status_code, content_type=response.headers.get('Content-Type'),
                  raw_file_path=raw.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(response.content).hexdigest(),
                  parser_version='phase6b2-evidence-v1')
    if suffix == '.html':
        soup = BeautifulSoup(response.content, 'html.parser')
        for tag in soup(['script','style','nav','footer','header']):
            tag.decompose()
        record['source_title'] = soup.title.get_text(' ', strip=True) if soup.title else ''
        (OUT / (key + '.txt')).write_text(soup.get_text(' ', strip=True), encoding='utf-8')
    else:
        from pypdf import PdfReader
        from io import BytesIO
        doc = PdfReader(BytesIO(response.content))
        (OUT / (key + '.txt')).write_text('\n'.join(page.extract_text() or '' for page in doc.pages), encoding='utf-8')
        record['source_title'] = str(doc.metadata.title or '') if doc.metadata else ''
    meta.write_text(json.dumps(record, indent=2), encoding='utf-8')
    response.raise_for_status()
    return record

if __name__ == '__main__':
    import sys
    for url in sys.argv[1:]:
        record = archive(url)
        print(record['raw_file_path'])
