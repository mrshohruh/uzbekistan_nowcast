"""Collect verified archive links for the 2024–2026 trade extension."""
import json,re,sys
from urllib.parse import urljoin
from io import BytesIO
from recovery import fetch,OUT
from bs4 import BeautifulSoup
from pypdf import PdfReader
sys.stdout.reconfigure(encoding='utf-8')
sources=json.loads((OUT/'stat_sources.json').read_text(encoding='utf-8'))
known={r['source_url'] for r in sources}
for year,slug in [(2024,'50256-for-2024-year'),(2025,'59630-for-2025-year1'),(2026,'66211-for-2026-year')]:
 url='https://stat.uz/en/press-releases/'+slug
 b,meta=fetch(url,'stat_release_index')
 soup=BeautifulSoup(b,'html.parser')
 links={urljoin(url,a['href']):a.get_text(' ',strip=True) for a in soup.find_all('a',href=True) if 'foreign trade' in a.get_text().lower() and ('.pdf' in a['href'].lower() or '/files/' in a['href'] or 'frontfile.download' in a['href'])}
 print(year,len(links),flush=True)
 for u,title in links.items():
  if u in known:continue
  try:
   b,m=fetch(u,'foreign_trade')
   if not b.startswith(b'%PDF'):raise ValueError('Expected PDF')
   sources.append({'index_year':year,'variable':'foreign_trade','source_url':u,'meta':m,'pages':[p.extract_text() for p in PdfReader(BytesIO(b)).pages]})
   print(year,title,flush=True)
  except Exception as e:sources.append({'index_year':year,'variable':'foreign_trade','source_url':u,'error':str(e)});print('ERROR',u,str(e)[:100],flush=True)
  (OUT/'stat_sources.json').write_text(json.dumps(sources,indent=2),encoding='utf-8')
