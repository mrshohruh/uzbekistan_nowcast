"""Isolated official-source recovery: immutable archives and local cache reuse."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,time,sys,os
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'data/research/phase6a2/_vendor'))
import requests,pandas as pd
OUT=ROOT/'results/research/phase6a2'; RAW=ROOT/'data/raw/research/phase6a2'
LOG=OUT/f'phase6a2_fetch_log_{os.getpid()}.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fetch(url,variable='sources'):
 log=json.loads(LOG.read_text()) if LOG.exists() else []
 cache=[]
 for logfile in OUT.glob('phase6a2_fetch_log*.json'):
  try:cache.extend(json.loads(logfile.read_text()))
  except (ValueError,OSError):continue
 for row in reversed(cache):
  if row['source_url']==url and row.get('raw_file_path') and (ROOT/row['raw_file_path']).exists():
   return (ROOT/row['raw_file_path']).read_bytes(),row
 old=pd.read_parquet(ROOT/'metadata/download_log.parquet')
 found=old[(old.source_url==url)&(old.status=='downloaded')&old.raw_file_path.notna()]
 for _,r in found.iloc[::-1].iterrows():
  p=ROOT/r.raw_file_path
  if p.is_file() and sha(p)==r.checksum:
   row={'source_url':url,'raw_file_path':r.raw_file_path,'checksum':r.checksum,'retrieved_at':r.retrieved_at,'http_status':int(r.http_status),'content_type':r.content_type,'reused_existing_raw':True}
   log.append(row);LOG.write_text(json.dumps(log,indent=2));return p.read_bytes(),row
 archived=list(RAW.rglob('*_'+hashlib.sha256(url.encode()).hexdigest()[:12]+'.*'))
 if archived:
  p=sorted(archived)[-1];ts=datetime.strptime(p.name.split('_')[0],'%Y%m%dT%H%M%S%fZ').replace(tzinfo=timezone.utc).isoformat()
  row={'source_url':url,'raw_file_path':p.relative_to(ROOT).as_posix(),'checksum':sha(p),'retrieved_at':ts,'http_status':None,'content_type':None,'reused_existing_raw':True,'cache_note':'Recovered immutable archive after concurrent fetch-log writes; HTTP headers unavailable, not invented'}
  log.append(row);LOG.write_text(json.dumps(log,indent=2));return p.read_bytes(),row
 session=requests.Session();session.headers['User-Agent']='UzbekistanNowcast-Phase6A2/1.0 research official-source recovery'
 for attempt in range(3):
  try:
   response=session.get(url,timeout=55)
   if response.status_code in [429,500,502,503,504] and attempt<2:time.sleep(2**attempt);continue
   timestamp=datetime.now(timezone.utc); row={'source_url':url,'response_url':response.url,'retrieved_at':timestamp.isoformat(),'http_status':response.status_code,'content_type':response.headers.get('Content-Type'),'reused_existing_raw':False}
   content=response.content
   if not content:raise ValueError('Empty response')
   ext='.pdf' if content.startswith(b'%PDF') else '.xlsx' if content.startswith(b'PK') else '.xls' if content.startswith(bytes.fromhex('d0cf11e0')) else '.json' if 'json' in str(row['content_type']) else '.html'
   folder=RAW/variable;folder.mkdir(parents=True,exist_ok=True)
   p=folder/(timestamp.strftime('%Y%m%dT%H%M%S%fZ')+'_'+hashlib.sha256(url.encode()).hexdigest()[:12]+ext)
   with p.open('xb') as f:f.write(content)
   row.update(raw_file_path=p.relative_to(ROOT).as_posix(),checksum=sha(p));log.append(row);LOG.write_text(json.dumps(log,indent=2))
   response.raise_for_status();time.sleep(.25);return content,row
  except requests.RequestException as e:
   if attempt==2:
    log.append({'source_url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'error':str(e)});LOG.write_text(json.dumps(log,indent=2));raise
   if isinstance(e,requests.HTTPError) and e.response.status_code not in [429,500,502,503,504]:raise
   time.sleep(2**attempt)

def main():
 from pypdf import PdfReader
 from io import BytesIO
 sources={'original_paper':'https://cbu.uz/upload/iblock/3d6/6kbvfiumraqdb4ejh0qrzkc6y4pbr3vi/MIDAS_WP.pdf','paper_landing':'https://cbu.uz/ru/research/economic/2525870/','services_3215':'https://siat.stat.uz/data/3215/?lang=en','services_3217':'https://siat.stat.uz/data/3217/?lang=en'}
 for key,url in sources.items():
  b,m=fetch(url,key)
  if b.startswith(b'%PDF'):
   text='\n'.join(f'PAGE {i+1}\n'+p.extract_text() for i,p in enumerate(PdfReader(BytesIO(b)).pages))
   (OUT/(key+'_extracted.txt')).write_text(text,encoding='utf-8')
  print(key,m['http_status'],len(b),flush=True)
if __name__=='__main__':main()
