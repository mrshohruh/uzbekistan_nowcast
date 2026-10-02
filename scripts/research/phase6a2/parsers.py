"""Strict monthly research parsers; no imputation or growth-index de-cumulation."""
import re,json,sys
from pathlib import Path
import pandas as pd,numpy as np
from recovery import OUT,ROOT
MONTHS={m.lower():i for i,m in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'],1)}
def number(v):
 if isinstance(v,(int,float)):return float(v)
 t=str(v).strip().replace('\xa0','').replace(' ','')
 if re.fullmatch(r'-?\d{1,3}(,\d{3})+(\.\d+)?',t):t=t.replace(',','')
 elif ',' in t and '.' not in t:t=t.replace(',','.')
 if not re.fullmatch(r'-?\d+(\.\d+)?',t):raise ValueError('Non-numeric cell '+str(v))
 return float(t)
def pos_period(text):
 # Use the explicitly reported transactions interval, never article update year.
 pat=r'(?:in|throughout)\s+(?:January|Yanuary|Januar)[\s–—-]+([A-Za-z]+)\s+(?:of\s+)?(20\d{2})'
 m=re.search(pat,text,re.I)
 if m and m[1].lower() in MONTHS:return pd.Period(year=int(m[2]),month=MONTHS[m[1].lower()],freq='M')
 m=re.search(r'POS[\s–-]*terminals\s+in\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:of\s+)?(20\d{2})',text,re.I)
 if m:return pd.Period(year=int(m[2]),month=MONTHS[m[1].lower()],freq='M')
 m=re.search(r'as of\s+(?:the\s+)?(?:(\d{1,2})\s+([A-Za-z]+)|([A-Za-z]+)\s+(\d{1,2}))\s*,?\s*(20\d{2})',text,re.I)
 if m:
  day=int(m[1] or m[4]);mo=MONTHS.get((m[2] or m[3]).lower())
  if not mo:raise ValueError('Unknown month')
  return (pd.Timestamp(int(m[5]),mo,day)-pd.Timedelta(days=1 if day==1 else 0)).to_period('M')
 raise ValueError('Explicit reporting interval not found')
def parse_pos(r):
 if 'error' in r:raise ValueError(r['error'])
 header=' '.join(str(c) for t in r['file_tables'] for row in t[:4] for c in row)
 # Also inspect the HTML body, which retains explicit English interval/unit.
 text=header+' '+r['text'];period=pos_period(text)
 if not re.search(r'mln|million|млн',text,re.I):raise ValueError('POS unit not explicitly million UZS')
 if not ('pos' in text.lower() or 'терминал' in text.lower()):raise ValueError('POS definition absent')
 totals=[]
 for t in r['file_tables']:
  for row in t:
   if any(str(c).strip().lower() in {'total','жами','jami','итого','всего'} for c in row):
    try:totals.append(number(row[-1]))
    except ValueError:pass
 html=[]
 for t in r['tables']:
  for row in t:
   if any(str(c).strip().lower()=='total' for c in row):
    try:html.append(number(row[-1]))
    except ValueError:pass
 values=totals or html
 if not values:raise ValueError('No exact national Total row')
 if max(values)-min(values)>max(1.,abs(values[0])*1e-7):raise ValueError('Conflicting language-sheet totals')
 value=values[0];meta=r['file_meta'] if totals else r['meta']
 return dict(variable_key='pos_turnover',reference_period=str(period),reference_date=period.to_timestamp('M'),raw_value=value,unit='million UZS',frequency='M',flow_type='YTD cumulative flow',source_url=meta['source_url'],raw_file_path=meta['raw_file_path'],checksum=meta['checksum'],retrieved_at=meta['retrieved_at'],source_release_date=None,source_release_basis='Article date/update recorded separately; not historical first release',article_url=r['article_url'],selected_label='National Total, POS amount column',cumulative_definition_evidence='Explicit January-to-report-month transactions range; January single-month and December annual totals',html_file_rounding_difference=max([abs(z-value) for z in html],default=0),revision_status='archive_snapshot; cross-release YTD revisions unverified',parser_version='phase6a2.1')
def run_pos():
 rows=[];fail=[]
 for r in json.loads((OUT/'pos_sources.json').read_text(encoding='utf-8')):
  try:rows.append(parse_pos(r))
  except Exception as e:fail.append({'article_url':r['article_url'],'error':str(e)})
 pd.DataFrame(rows).to_csv(OUT/'pos_recovered_levels.csv',index=False)
 (OUT/'pos_parse_failures.json').write_text(json.dumps(fail,indent=2));print('POS parsed',len(rows),'failed',len(fail));print(fail[:15])
if __name__=='__main__':run_pos()
