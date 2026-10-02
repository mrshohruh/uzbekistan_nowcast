"""Targeted archive collection; every source and parse failure remains visible."""
import sys,re,json
from pathlib import Path
from urllib.parse import urljoin
from io import BytesIO
from recovery import fetch,OUT,ROOT
from bs4 import BeautifulSoup
from pypdf import PdfReader
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

def archive_pos():
 old=pd.read_parquet(ROOT/'metadata/download_log.parquet')
 listings=old[(old.variable_key=='pos_turnover')&old.source_url.str.contains('set_filter',na=False)&(old.status=='downloaded')]
 articles={}
 for _,r in listings.iterrows():
  soup=BeautifulSoup((ROOT/r.raw_file_path).read_bytes(),'html.parser')
  for a in soup.find_all('a',href=True):
   if re.search(r'/paysistem/\d+/',a['href']) and 'pos' in a.get_text().lower():articles[urljoin('https://cbu.uz',a['href'])]=a.get_text(' ',strip=True)
 results=[]
 for n,(url,title) in enumerate(sorted(articles.items())):
  try:
   content,meta=fetch(url,'pos_turnover');soup=BeautifulSoup(content,'html.parser')
   tables=[[[c.get_text(' ',strip=True) for c in row.find_all(['td','th'])] for row in table.find_all('tr')] for table in soup.find_all('table')]
   text=soup.get_text(' ',strip=True)
   # Preserve official source files; machine file first, avoid duplicate PDF downloads.
   files=sorted(set(urljoin(url,a['href']) for a in soup.find_all('a',href=True) if re.search(r'\.(xlsx?|pdf)(?:\?|$)',a['href'],re.I)),key=lambda u:('.pdf' in u.lower(),u))
   fm=None;file_tables=[]
   for file_url in files[:1]:
    try:
     b,fm=fetch(file_url,'pos_turnover')
     if b.startswith(b'PK') or b.startswith(bytes.fromhex('d0cf11e0')):
      book=pd.ExcelFile(BytesIO(b),engine='openpyxl' if b.startswith(b'PK') else 'xlrd')
      for name in book.sheet_names:file_tables.append(book.parse(name,header=None).fillna('').values.tolist())
    except Exception as e:fm={'error':str(e),'source_url':file_url}
   results.append({'article_url':url,'listing_title':title,'text':text,'tables':tables,'file_tables':file_tables,'meta':meta,'file_meta':fm})
   print('POS',n+1,len(articles),url,len(tables),len(file_tables),flush=True)
  except Exception as e:results.append({'article_url':url,'error':str(e)});print('POS ERROR',url,str(e)[:150],flush=True)
  (OUT/'pos_sources.json').write_text(json.dumps(results,indent=2,default=str),encoding='utf-8')

def archive_stat():
 years={2018:'https://stat.uz/en/press-releases/5827-for-2018-year',2019:'https://stat.uz/en/press-releases/5826-for-2019-year',2020:'https://stat.uz/en/press-releases/5825-for-2020-year',2021:'https://stat.uz/en/press-releases/7659-for-2021-year',2022:'https://stat.uz/en/press-releases/17513-2023',2023:'https://stat.uz/en/press-releases/34346-2023-2'}
 sources=json.loads((OUT/'stat_sources.json').read_text(encoding='utf-8')) if (OUT/'stat_sources.json').exists() else []
 known={r['source_url'] for r in sources}
 for year,url in years.items():
  b,meta=fetch(url,'stat_release_index');soup=BeautifulSoup(b,'html.parser')
  links={}
  for a in soup.find_all('a',href=True):
   t=a.get_text(' ',strip=True).lower();href=a['href']
   family='services_output' if any(z in t for z in ['service sector','services sector','service sphere','development of the service']) else 'industrial_production' if 'industrial production' in t else 'construction' if ('construction works' in t or 'constuction works' in t) else 'retail_trade' if 'consumer market' in t or 'internal trade' in t else 'foreign_trade' if 'foreign trade' in t else None
   if family and ('.pdf' in href.lower() or '/files/' in href or 'frontfile.download' in href):
    if family=='services_output' or (family=='industrial_production' and year==2018) or (family in ['retail_trade','construction'] and year<=2020) or family=='foreign_trade':links[urljoin(url,href)]=family
  print('STAT YEAR',year,'sources',len(links),flush=True)
  for n,(u,family) in enumerate(links.items()):
   if u in known:continue
   try:
    b,m=fetch(u,family)
    if not b.startswith(b'%PDF'):raise ValueError('Linked source is not PDF')
    pages=[p.extract_text() for p in PdfReader(BytesIO(b)).pages]
    sources.append({'index_year':year,'variable':family,'source_url':u,'meta':m,'pages':pages})
    print('STAT',year,n+1,len(links),family,len(pages),flush=True)
   except Exception as e:sources.append({'index_year':year,'variable':family,'source_url':u,'error':str(e)});print('STAT ERROR',u,str(e)[:130],flush=True)
   (OUT/'stat_sources.json').write_text(json.dumps(sources,indent=2),encoding='utf-8')

def archive_siat():
 for id in [2700,3218,556,2403,2699,1162,3082,3083]:
  try:
   b,m=fetch(f'https://siat.stat.uz/data/{id}/?lang=en',f'siat_{id}')
   soup=BeautifulSoup(b,'html.parser')
   links=[a['href'].replace('http://','https://') for a in soup.find_all('a',href=True) if 'download_format=json' in a['href']]
   if not links:raise ValueError('No official JSON link')
   b,m=fetch(links[0],f'siat_{id}');d=json.loads(b);fetch(d['file'],f'siat_{id}');print('SIAT',id,'archived',flush=True)
  except Exception as e:print('SIAT ERROR',id,str(e)[:120],flush=True)
if __name__=='__main__':
 {'pos':archive_pos,'stat':archive_stat,'siat':archive_siat}[sys.argv[1]]()
