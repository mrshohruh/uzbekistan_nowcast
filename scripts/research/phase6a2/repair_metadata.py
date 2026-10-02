"""Recover metadata lost by early concurrent log writes using exact URL hashes."""
import json,re,hashlib
from datetime import datetime,timezone
from urllib.parse import urljoin
from recovery import ROOT,OUT,RAW,sha
from extract import source_metas
from bs4 import BeautifulSoup

def walk(value):
 if isinstance(value,str) and value.startswith(('https://','http://')):yield value
 elif isinstance(value,dict):
  for v in value.values():yield from walk(v)
 elif isinstance(value,list):
  for v in value:yield from walk(v)

def main():
 urls=set()
 for p in OUT.glob('*.json'):
  try:urls.update(walk(json.loads(p.read_text(encoding='utf-8'))))
  except (ValueError,UnicodeError):pass
 for directory in RAW.glob('siat_*'):
  id=directory.name.split('_')[1];base=f'https://siat.stat.uz/data/{id}/?lang=en';urls.add(base)
  for p in directory.glob('*.html'):
   soup=BeautifulSoup(p.read_bytes(),'html.parser')
   for a in soup.find_all('a',href=True):
    if 'download_format=json' in a['href']:urls.add(urljoin(base,a['href']).replace('http://','https://'))
  for p in directory.glob('*.json'):
   d=json.loads(p.read_text(encoding='utf-8'))
   if isinstance(d,dict) and d.get('file'):urls.add(d['file'])
 lookup={hashlib.sha256(u.encode()).hexdigest()[:12]:u for u in urls}
 known=source_metas();repaired=[];missing=[]
 for p in RAW.rglob('*'):
  if not p.is_file() or p.relative_to(ROOT).as_posix() in known:continue
  token=p.stem.split('_')[-1];url=lookup.get(token)
  if not url:missing.append(p.relative_to(ROOT).as_posix());continue
  ts=datetime.strptime(p.name.split('_')[0],'%Y%m%dT%H%M%S%fZ').replace(tzinfo=timezone.utc).isoformat()
  repaired.append({'source_url':url,'raw_file_path':p.relative_to(ROOT).as_posix(),'checksum':sha(p),'retrieved_at':ts,'http_status':None,'content_type':None,'cache_note':'URL verified by SHA256 URL hash; original HTTP headers unavailable after concurrent log writes','reused_existing_raw':False})
 (OUT/'phase6a2_fetch_log_repaired.json').write_text(json.dumps(repaired,indent=2),encoding='utf-8')
 if missing:raise ValueError('Unresolved source metadata: '+str(missing))
 print('Recovered',len(repaired),'source metadata records; no unresolved raw archives')
if __name__=='__main__':main()
