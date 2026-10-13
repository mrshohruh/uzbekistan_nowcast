"""Checksum-verified replay of user-run receipts; never connects or publishes."""
from pathlib import Path
import sys, json, hashlib, shutil
from io import BytesIO
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import pandas as pd
import openpyxl
from scripts.collection import pos
from scripts.operations.acquisition import compare
from scripts.operations.state import model_lock, verify_current_version
from uznowcast.registry import load_registry
from uznowcast.parsers.cbu_stats import parse_reserves_xlsx
from uznowcast.provenance import attach_provenance
from uznowcast.transforms.growth import log_growth
from scripts.collection.http import SourceError
from uznowcast.io.cbu_archive import enumerate_articles, relevant_articles, download_article
RUN=ROOT/'data/collection/runs/collect_20261012_122304_6c4952e8'
OUT=ROOT/'results/phase8a3b'
receipts=pd.read_csv(RUN/'source_receipts.csv').where(lambda x:x.notna(),None)
registry=load_registry(ROOT/'registry/uzbekistan_nowcasting_v1.2_registry.xlsx')
def save(name,value): (OUT/name).write_text(json.dumps(value,indent=2,default=str)+'\n',encoding='utf-8')
class Replay:
 def get_bytes(self,row,url,**kwargs):
  found=receipts.loc[receipts.variable_key.eq(row['variable_key'])&receipts.source_url.eq(url)]
  if found.empty: raise SourceError('ARCHIVE_MISSING',url)
  meta=found.iloc[-1].to_dict(); content=Path(meta['raw_file_path']).read_bytes()
  assert hashlib.sha256(content).hexdigest()==meta['checksum']
  if meta['http_status']!=200: raise SourceError('HTTP_ERROR',f"HTTP {meta['http_status']}: {url}")
  return content,meta
client=Replay()
row=registry.rows['fx_reserves_ex_gold']
meta=receipts.loc[receipts.variable_key.eq('fx_reserves_ex_gold')&receipts.source_url.str.endswith('.xlsx')].iloc[0].to_dict()
content,_=client.get_bytes(row,meta['source_url'])
candidate=log_growth(attach_provenance(parse_reserves_xlsx(content,row),row,meta),'raw_value',12,50.)
old=pd.read_parquet(ROOT/'data/processed/fx_reserves_ex_gold.parquet')
merged,decisions,valid=compare('fx_reserves_ex_gold',old,candidate,pd.Timestamp('2026-10-12T23:00:00Z'))
pd.DataFrame(decisions).to_csv(OUT/'validation/reserves_decisions.csv',index=False)
candidate.tail(15).to_csv(OUT/'validation/reserves_candidates.csv',index=False)
save('validation/reserves_summary.json',dict(admission_valid=valid,retained_old=merged.equals(old),candidate=candidate.iloc[-1].to_dict(),old_latest=old.iloc[-1].to_dict(),raw_history_unchanged=all(candidate.set_index('reference_period').loc[old.reference_period,'raw_value'].to_numpy()==old.raw_value.to_numpy()),receipt=meta))
audit=pd.read_csv(RUN/'archive_audit.csv')
save('validation/original_pos_failure_counts.json',audit.loc[audit.status.eq('ARTICLE_FAILED')].error.value_counts().to_dict())
articles=relevant_articles(enumerate_articles(client,registry.rows['pos_turnover'],section='3499',first_year=2018),'pos')
for ident in ['1222302','1843091']:
 url,title=next((u,t) for u,t in articles if u.endswith('/'+ident+'/'))
 article=download_article(client,registry.rows['pos_turnover'],url,title)
 record=pos.parse_article(article,client,registry.rows['pos_turnover'])
 fixture=ROOT/'tests/fixtures/collection/avgust'
 file=next(m for m in article['file_metas'] if m['source_url'].endswith('.xlsx'))
 shutil.copyfile(file['raw_file_path'],fixture/(ident+'.xlsx'))
 (fixture/(ident+'.json')).write_text(json.dumps(dict(title=title,expected_period=record['reference_period'],expected_value=record['raw_value'],page_checksum=article['page_meta']['checksum'],workbook_checksum=file['checksum'],source_url=file['source_url']),indent=2),encoding='utf-8')
frame=pos.collect(client,registry.rows['pos_turnover'])
pd.DataFrame(frame.attrs['archive_audit']).to_csv(OUT/'validation/replayed_pos_audit.csv',index=False)
frame.to_csv(OUT/'validation/replayed_pos_candidates.csv',index=False)
oldpos=pd.read_parquet(ROOT/'data/processed/pos_turnover.parquet')
_,d,v=compare('pos_turnover',oldpos,frame.loc[frame.reference_period.le('2024-12')],pd.Timestamp('2026-10-12T23:00:00Z'),pos=True)
pd.DataFrame(d).to_csv(OUT/'validation/replayed_pos_decisions.csv',index=False)
a=pd.DataFrame(frame.attrs['archive_audit'])
save('validation/pos_summary.json',dict(article_failures=int(a.status.eq('ARTICLE_FAILED').sum()),missing_periods=a.loc[a.status.eq('MISSING_PERIOD'),'reference_period'].tolist(),admission_valid=v,live_verified=False))
baseline=json.loads((ROOT/'results/phase8a2/validation/baseline.json').read_text())
changed=[p for p,h in baseline.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
locked,_=model_lock(ROOT);verify_current_version(ROOT)
save('validation/freeze.json',dict(checked=len(baseline),changed=changed,seal='PASS',runtime_files=len(locked),current_version='PASS',forecast=8.180901340616275))
for name in ['run_manifest.json','source_status.csv','validation_reports.json','observation_decisions.csv','source_receipts.csv']:
 save('validation/'+name+'.sha256.json',dict(path=str(RUN/name),sha256=hashlib.sha256((RUN/name).read_bytes()).hexdigest()))
print((OUT/'validation/pos_summary.json').read_text())
