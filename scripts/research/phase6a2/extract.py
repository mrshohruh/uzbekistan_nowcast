"""Conservative, evidence-bearing extraction into research observations only."""
import json,re,hashlib
from pathlib import Path
import pandas as pd
import numpy as np
from recovery import ROOT,OUT,sha
from parsers import number

VERSION='phase6a2.2'
MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December']
NUM=r'(?:\d{1,3}(?:[ ,\u00a0]\d{3})+|\d+)[.,]\d+'

def compact(text):return re.sub(r'\s+',' ',text.replace('\u00ad','').replace('–','-').replace('−','-')).replace('indus trial','industrial').replace('volu me','volume').replace(', ', ',')

def report_period(pages):
 text=compact(' '.join(pages[:3]))
 matches=list(re.finditer(r'January\s*(?:-\s*('+ '|'.join(MONTHS)+r'))?\s*,?\s*((?:19|20)\d{2})',text,re.I))
 if not matches:raise ValueError('No explicit January-to-month reference period in document')
 m=matches[0];month=next((i+1 for i,v in enumerate(MONTHS) if v.lower()==str(m.group(1)).lower()),1)
 return pd.Period(f'{m.group(2)}-{month:02d}',freq='M')

def observation(key,period,value,meta,unit,kind,selector,evidence,verified=True,method='direct'):
 return {'variable_key':key,'reference_period':str(period),'reference_date':str(period.end_time.date()),'raw_value':float(value),'clean_value':float(value)-100 if kind=='real_ytd_growth_index' else float(value),'unit':unit,'frequency':'M','flow_type':kind,'provider':'CBU' if 'cbu.uz' in meta['source_url'] else 'Statistics Agency / SIAT','source_url':meta['source_url'],'raw_file_path':meta['raw_file_path'],'checksum':meta['checksum'],'retrieved_at':meta['retrieved_at'],'source_release_date':meta.get('source_release_date'),'source_release_basis':'printed release date of this vintage; historical first release not inferred' if meta.get('source_release_date') else 'unknown; never backfilled from typical lag','observed_source_update_date':meta.get('observed_source_update_date'),'revision_status':'latest retrieved snapshot; historical first release unknown','parser_version':VERSION,'schema_fingerprint':hashlib.sha256((selector+'|'+kind+'|'+unit).encode()).hexdigest(),'table_selector':selector,'definition_evidence':evidence,'definition_verified':verified,'reconstruction_method':method,'source_vintage':meta.get('source_vintage',meta['raw_file_path'])}

def source_metas():
 rows=[]
 for p in OUT.glob('phase6a2_fetch_log*.json'):rows.extend(json.loads(p.read_text(encoding='utf-8')))
 for name in ['stat_sources.json','pos_sources.json','cbu_bulletin_sources.json','additional_evidence.json']:
  if (OUT/name).exists():
   for r in json.loads((OUT/name).read_text(encoding='utf-8')):
    for k in ['meta','file_meta','article_meta']:
     if r.get(k) and r[k].get('raw_file_path'):rows.append(r[k])
 return {r['raw_file_path']:r for r in rows if r.get('raw_file_path')}

def siat_sources():
 """Read actual descriptor URLs; enforce the exact national code and label."""
 metas=source_metas();result=[];findings=[]
 keys={577:('industrial_production','real_ytd_growth_index'),2406:('construction','real_ytd_growth_index'),2700:('retail_trade','real_ytd_growth_index'),3216:('services_output','real_ytd_growth_index'),3215:('services_output_nominal_ytd','nominal_ytd'),2414:('imports_total','nominal_ytd'),556:('industrial_large_enterprises_candidate','nominal_ytd')}
 for id,(key,kind) in keys.items():
  directory=ROOT/f'data/raw/research/phase6a2/siat_{id}'
  payloads=[]
  for p in directory.glob('*.json'):
   d=json.loads(p.read_text(encoding='utf-8'))
   if isinstance(d,list) and d and 'data' in d[0]:payloads.append((p,d[0]))
  if len(payloads)!=1:raise ValueError(f'SIAT {id}: expected one frozen payload, found {len(payloads)}')
  p,d=payloads[0];rel=p.relative_to(ROOT).as_posix();meta=metas.get(rel)
  if not meta:
   descriptors=[json.loads(q.read_text(encoding='utf-8')) for q in directory.glob('*.json') if q!=p]
   url=next(x['file'] for x in descriptors if isinstance(x,dict) and 'file' in x)
   from recovery import fetch
   _,meta=fetch(url,f'siat_{id}')
  selected=[r for r in d['data'] if str(r.get('Code'))=='1700' and r.get('Klassifikator_en')=='Republic of Uzbekistan']
  if len(selected)!=1:raise ValueError(f'SIAT {id}: exact national selector not unique')
  md={r['name_en']:r.get('value_en') for r in d['metadata'] if r.get('name_en')};meta=dict(meta)
  updates=[r.get('value_en') for r in d['metadata'] if r.get('name_en')=='Last modified date'];meta['observed_source_update_date']=max(str(x) for x in updates if x)
  findings.append({'dataset_id':id,'key':key,'metadata':d['metadata'],'columns':list(selected[0])})
  for date,value in selected[0].items():
   if re.fullmatch(r'\d{4}-M\d{2}',date) and value is not None:
    period=pd.Period(date.replace('-M','-'),freq='M')
    result.append(observation(key,period,number(value),meta,md.get('Unit of measurement','unknown'),kind,f'SIAT {id}; Code=1700 AND Klassifikator_en=Republic of Uzbekistan',md.get('Calculation methodology (briefly)',md.get('Calculation methodology',''))+'; '+md.get('Indicator name',''),id!=556))
 (OUT/'siat_metadata_audit.json').write_text(json.dumps(findings,indent=2),encoding='utf-8')
 return result

def national_service_table(pages):
 for i,text in enumerate(pages):
  t=compact(text)
  if not (('billion' in t.lower() or 'bln.' in t.lower()) and 'growth' in t.lower()):continue
  title_ok=re.search(r'(?:[Mm]ain|[Kk]ey)(?: performance)? indicators of (?:services? production|production (?:of )?services|the service sector|services) by region|[Pp]roduction of services by region|[Vv]olume of (?:production )?services by region|[Oo]utput of services by region',t)
  total_share_table=('specific weight in the total volume' in t.lower() and 'service sector' in t.lower())
  if not (title_ok or total_share_table):continue
  m=re.search(r'(?:Republic|Rep\.)\s*of Uzbekistan\s*(?:\*\)?|\d\))?\s*('+NUM+r')\s+('+NUM+r')(?:\s+('+NUM+r'))?',t)
  if m and ('service' in t.lower()):
   level=number(m.group(1));second=number(m.group(2));third=number(m.group(3)) if m.group(3) else None
   # 2023 tables place national share=100 between level and growth.
   growth=third if second==100 and 'specific weight' in t.lower() else second
   if not 50<growth<200:continue
   return level,growth,i+1,m.group(0)
 # Some 2019 files duplicate font overlays and extract growth in a separate column.
 # The national headline must independently identify the same volume and growth.
 for i,text in enumerate(pages):
  t=compact(text).replace('bi llion','billion')
  m=re.search(r'volume of market services rendered.{0,130}?reached\s*('+NUM+r')\s*billion soums.{0,160}?growth rate was\s*(\d+[.,]\d+)\s*%',t,re.I)
  if m:return number(m.group(1)),number(m.group(2)),i+1,m.group(0)+'; independently corroborated in national table'
 raise ValueError('Exact national services volume/growth row unavailable')

def headline_values(pages,family):
 t=compact(' '.join(pages[:2]));page=1
 if family=='construction':
  m=re.search(r'volume of (?:completed )?construction work(?:s)?.{0,180}?(?:amounted to|reached|was)\s*('+NUM+r')\s*billion.{0,160}?(?:growth rate[^%]{0,110}?|increased[^%]{0,60}?)(\d+[.,]\d+)\s*%',t,re.I)
  if not m:raise ValueError('No national construction headline')
  return number(m.group(1)),number(m.group(2)),page,m.group(0)
 if family=='industrial_production':
  m=re.search(r'(?:produced|manufactured).{0,100}?industrial (?:output|products).{0,100}?(?:for|of|amounted to|worth)\s*('+NUM+r')\s*(billion|trillion)',t,re.I)
  if not m:raise ValueError('No national industrial headline')
  rest=t[m.end():m.end()+200];g=re.search(r'(?:growth rate|index of physical volume)[^%]{0,150}?(\d+[.,]\d+)\s*%',rest,re.I)
  if not g:raise ValueError('No national industrial growth headline')
  return number(m.group(1))*(1000 if m.group(2).lower()=='trillion' else 1),number(g.group(1)),page,m.group(0)+' '+g.group(0)
 if family=='retail_trade':
  m=re.search(r'retail trade turnover.{0,180}?(?:reached|amounted to)\s*('+NUM+r')\s*billion.{0,180}?(?:increased[^%]{0,150}?by\s*|growth rate[^%]{0,60}?)(\d+[.,]\d+)\s*%',t,re.I)
  if not m:raise ValueError('No national retail headline')
  g=number(m.group(2));g=g+100 if 'increased' in m.group(0).lower() else g
  return number(m.group(1)),g,page,m.group(0)

def trade_values(pages):
 t=compact(' '.join(pages[:3]));out=[]
 for key,label in [('imports_historical_candidate','import'),('exports_total_official_ytd','export')]:
  m=re.search(r'(?:volume of\s+)?'+label+r'(?:s)?\s*(?:volume)?\s*(?:amounted to|was|reached|in the amount of|of|amounting to|-)?\s*('+NUM+r')\s*(?:million|mln)',t,re.I)
  if m:out.append((key,number(m.group(1)),1,m.group(0),True))
 # Modern comparative table: previous year first, current reference year second.
 for i,text in enumerate(pages):
  c=compact(text)
  m=re.search(r'Total(?: exports)?\s*('+NUM+r')\s+('+NUM+r')',c,re.I)
  if m and re.search(r'II\.\s*Export',c,re.I) and ('2025 2026' in c or '2024 2025' in c):
   out=[r for r in out if r[0]!='exports_total_official_ytd']
   out.append(('exports_total_official_ytd',number(m.group(2)),i+1,m.group(0)+'; current-year second column',True))
  m=re.search(r'Total(?: imports)?\s*('+NUM+r')\s+('+NUM+r')',c,re.I)
  if m and re.search(r'III\.\s*Import',c,re.I) and ('2025 2026' in c or '2024 2025' in c):
   out=[r for r in out if r[0]!='imports_historical_candidate']
   out.append(('imports_historical_candidate',number(m.group(2)),i+1,m.group(0)+'; current-year second column',True))
 direct=None;gold=None
 for i,text in enumerate(pages):
  t=compact(text)
  if i>2 and re.search(r'III\.\s*Import|IMPORT(?:S)? OF THE REPUBLIC',t,re.I):break
  if direct is None:
   m=re.search(r'exports without gold[^.]{0,70}?(?:reached|amounted to|was|of)\s*('+NUM+r')\s*million',t,re.I)
   if m:direct=(number(m.group(1)),i+1,m.group(0))
   else:
    m=re.search(r'volume of exports of goods and services amounted to\s*('+NUM+r')\s*million[^.]{0,70}?(?:in addition to|excluding|except)[^)]{0,30}non-monetary gold',t,re.I)
    if m:direct=(number(m.group(1)),i+1,m.group(0))
  if gold is None:
   m=re.search(r'Non[- ]monetary gold\s*\((?:except(?: for)?|excluding) gold ores?\s*(?:and|&)\s*concentrates?\)\s*('+NUM+r')',t,re.I)
   if m:gold=(number(m.group(1)),i+1,m.group(0),True)
  if gold is None:
   m=re.search(r'\bGold\s*('+NUM+r')',t)
   if m:gold=(number(m.group(1)),i+1,m.group(0),False)
 exports=next((v for k,v,*_ in out if k=='exports_total_official_ytd'),None)
 if gold:
  val,page,evidence,exact=gold;out.append(('gold_non_monetary_official_ytd' if exact else 'gold_unspecified_official_candidate',val,page,evidence,exact))
  if exports is not None:
   out.append(('exports_ex_gold_exact' if exact else 'exports_ex_gold_scope_unknown_candidate',exports-val,page,evidence+'; total exports minus this gold row',exact))
 if direct:
  value,page,evidence=direct
  # Prefer directly published no-gold total; retain its subtraction cross-check.
  earlier=next((r[1] for r in out if r[0]=='exports_ex_gold_exact'),None)
  mismatch=earlier is not None and abs(earlier-value)>1
  if mismatch:
   out=[r for r in out if r[0]!='exports_ex_gold_exact']
   out.append(('exports_ex_gold_subtraction_mismatch_candidate',earlier,page,'Gold subtraction differs from direct published no-gold total; definition verification required',False))
  out=[r for r in out if r[0]!='exports_ex_gold_exact']
  out.append(('exports_ex_gold_direct_mismatch_candidate' if mismatch else 'exports_ex_gold_exact',value,page,evidence+'; '+('non-monetary gold corroborated in commodity table' if gold and gold[3] else 'direct official exports-without-gold statement; scope caveat retained'),not mismatch))
 return out

def stat_sources():
 result=[];failures=[]
 for source in json.loads((OUT/'stat_sources.json').read_text(encoding='utf-8')):
  if not source.get('pages'):
   failures.append({'source_url':source['source_url'],'variable':source['variable'],'error':source.get('error'),'stage':'download'});continue
  try:
   pages=source['pages'];period=report_period(pages);meta=dict(source['meta']);family=source['variable']
   release=re.search(r'(?:Release date|Publication Date|Date of publication)\s*:\s*(\d{2})[.,](\d{2})[.,](\d{4})',compact(pages[0]),re.I)
   if release:meta['source_release_date']=f'{release.group(3)}-{release.group(2)}-{release.group(1)}'
   if period.year!=source['index_year']:raise ValueError(f'Index year {source["index_year"]} differs from document {period}')
   if family=='services_output':
    level,growth,page,evidence=national_service_table(pages)
    result.append(observation('services_output',period,growth,meta,'previous year=100','real_ytd_growth_index',f'PDF page {page}; exact national volume/growth row',evidence))
    result.append(observation('services_output_nominal_ytd',period,level,meta,'billion UZS','nominal_ytd',f'PDF page {page}; exact national volume/growth row',evidence))
   elif family=='foreign_trade':
    values=trade_values(pages)
    if not values:raise ValueError('No strictly selected trade headline or commodity row')
    for key,value,page,evidence,verified in values:result.append(observation(key,period,value,meta,'million USD','nominal_ytd',f'PDF page {page}; national headline/commodity row',evidence,verified,'total exports minus official gold' if 'minus this gold' in evidence else 'direct published total'))
   else:
    level,growth,page,evidence=headline_values(pages,family)
    # Published historical growth retained separately until scope/real-volume mapping is verified.
    result.append(observation(family+'_historical_growth_candidate',period,growth,meta,'previous year=100','published_ytd_growth_index',f'PDF page {page}; national headline',evidence,False))
    result.append(observation(family+'_historical_nominal_ytd',period,level,meta,'billion UZS','nominal_ytd',f'PDF page {page}; national headline',evidence,False))
  except Exception as e:failures.append({'source_url':source['source_url'],'variable':source['variable'],'error':str(e),'stage':'parse'})
 (OUT/'stat_parse_failures.json').write_text(json.dumps(failures,indent=2),encoding='utf-8')
 return result

def pos_bulletins():
 result=[]
 for source in json.loads((OUT/'cbu_bulletin_sources.json').read_text(encoding='utf-8')):
  meta=dict(source['meta']);title=source['title'];meta['source_vintage']=title
  table=source.get('tables',{}).get('6.4')
  if table:
   if 'since the beginning of the year' not in str(table[:5]).lower():continue
   for row in table[5:]:
    try:
     date=pd.to_datetime(row[0],format='%d.%m.%Y') if re.match(r'\d{2}\.\d{2}\.\d{4}',str(row[0])) else pd.Timestamp(row[0])
     if date.day!=1:raise ValueError('POS as-of date is not month start')
     period=(date-pd.Timedelta(days=1)).to_period('M')
     result.append(observation('pos_turnover',period,number(row[4])*1000,meta,'million UZS','nominal_ytd','CBU bulletin Table 6.4; date col1 amount col5','Explicit since beginning of year, billion UZS converted x1000',True))
    except (ValueError,TypeError):
     if str(row[0]).strip():raise
  elif source.get('pages') and ('2018 year' in title or '2019 annual' in title):
   for i,text in enumerate(source['pages']):
    if not (re.search(r'Table 6\.3',text) and 'Total amount' in text):continue
    for line in text.splitlines():
     m=re.match(r'(01\.\d{2}\.\d{4})\s+(.+)',line.strip())
     if not m:continue
     # Final comma-decimal group is the POS amount; preceding columns are integer stocks.
     amount=re.search(r'(\d{1,3}(?:\s\d{3})*[,.]\d+)\s*$',m.group(2))
     if not amount:raise ValueError('Historical POS amount not identifiable')
     period=(pd.to_datetime(m.group(1),format='%d.%m.%Y')-pd.Timedelta(days=1)).to_period('M')
     result.append(observation('pos_turnover',period,number(amount.group(1))*1000,meta,'million UZS','nominal_ytd',f'CBU bulletin Table 6.3 PDF page {i+1}; final amount column','YTD interpretation validated against explicitly cumulative monthly archive files and January resets',True))
 return result

def main():
 rows=siat_sources()+stat_sources()+pos_bulletins()
 pos=pd.read_csv(OUT/'pos_recovered_levels.csv').to_dict('records')
 for r in pos:
  period=pd.Period(r['reference_period'],freq='M');meta={k:r[k] for k in ['source_url','raw_file_path','checksum','retrieved_at']}
  rows.append(observation('pos_turnover',period,r['raw_value'],meta,'million UZS','nominal_ytd',r['selected_label'],r['cumulative_definition_evidence'],True))
 # Exact published monthly receipts; no interpolation of the rounded August growth.
 evidence=json.loads((OUT/'additional_evidence.json').read_text(encoding='utf-8'))
 source=next(r for r in evidence if '/403913/' in r.get('meta',{}).get('source_url',''))
 text=source['text']
 if not ('12,6' in text and '11,1' in text):raise ValueError('Verified June/July receipts values absent')
 for date,value in [('2020-06',12.6),('2020-07',11.1)]:rows.append(observation('trade_paid_services_receipts',pd.Period(date,freq='M'),value,source['meta'],'trillion UZS','nominal_monthly_flow','CBU 10 September 2020 monetary-policy decision; receipts paragraph','Trade and paid-services receipts: June 12.6; July 11.1 trillion UZS; nominal, paper real deflator unspecified',True))
 df=pd.DataFrame(rows).sort_values(['variable_key','reference_period','retrieved_at'])
 df.to_csv(OUT/'all_recovered_observations.csv',index=False,encoding='utf-8-sig')
 print(df.groupby('variable_key').agg(start=('reference_period','min'),end=('reference_period','max'),rows=('raw_value','size')).to_string())
if __name__=='__main__':main()
