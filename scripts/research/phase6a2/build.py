"""Build isolated latest-vintage research panel, coverage audits and protection checks.

No model code is imported or estimated. Re-run extraction and this module against
the immutable archives to reproduce outputs. Latest-vintage coverage does not
assert historical release availability.
"""
from datetime import datetime,timezone
import hashlib,json,re,subprocess
import pandas as pd
import numpy as np
from recovery import ROOT,OUT,sha
from extract import source_metas,VERSION

DATA=ROOT/'data/research/phase6a2'
GRID=pd.period_range('2018-01','2026-08',freq='M')
KEYS=['industrial_production','construction','services_output','retail_trade','trade_paid_services_receipts','pos_turnover','exports_ex_gold_exact','imports_total','job_search_index']
CLASSES=['CLOSE_MATCH_VERIFIED','CLOSE_MATCH_VERIFIED','DEFINITION_BREAK','CLOSE_MATCH_VERIFIED','AVAILABLE_BUT_SHORT','PUBLIC_SERIES_RECOVERED','RECONSTRUCTED_FROM_OFFICIAL_DATA','PUBLIC_SERIES_RECOVERED','PUBLIC_SOURCE_CONFIRMED_QUERY_SPEC_UNKNOWN']
NOTES=[
 'SIAT 577 physical-volume index; published real cumulative growth. 2018 headline candidates remain separate; original exact selector unspecified.',
 'SIAT 2406 real published growth. 2018–2020 historical headlines remain separate pending universe/methodology reconciliation.',
 'Market-services national volume and comparable-price growth recovered from 2018 releases and SIAT 3215/3216. September 2024 hidden/informal-economy coverage break.',
 'SIAT 2700 published retail growth. Historical turnover candidates and catering/retail scope changes remain separate.',
 'Exact nominal monthly totals June/July 2020; 2022 annual cash+classified-terminal identity confirmed. No full monthly annex or paper deflator identified.',
 'Historical POS YTD archive/bulletins recovered; optional payment proxy, not an original-paper concept. E-POS label/coverage requires verification.',
 'Official goods-and-services exports excluding non-monetary gold, distinct research key. Nominal USD YTD; paper real deflator unspecified; conflicting direct/subtracted totals withheld; no HS71/Other-goods subtraction.',
 'SIAT 2414 nominal USD cumulative goods-and-services imports. Goods-only and real-paper versions require definition verification.',
 'CBU labour publication confirms Google Trends; no exact basket/topics/category/search type/normalization protocol disclosed; no invented exploratory basket.'
]

def longest(mask):
 best=[];current=[]
 for p,ok in mask.items():
  if ok:current.append(p)
  else:
   if len(current)>len(best):best=current
   current=[]
 if len(current)>len(best):best=current
 return (str(best[0]),str(best[-1]),len(best)) if best else (None,None,0)

def coverage(series):
 valid=series.reindex(GRID).notna();present=valid[valid].index
 internal=valid.loc[present.min():present.max()] if len(present) else valid
 a,b,n=longest(valid)
 return {'start_month':str(present.min()) if len(present) else None,'end_month':str(present.max()) if len(present) else None,'observation_count':int(valid.sum()),'missing_month_count':int((~valid).sum()),'internal_missing_months':int((~internal).sum()) if len(present) else None,'longest_internal_gap':longest(~internal)[2] if len(present) else None,'percentage_coverage_from_2018':round(100*valid.mean(),2),'longest_continuous_start':a,'longest_continuous_end':b,'longest_continuous_months':n,'continuous_2018_2026_through_august':bool(valid.all())}

def protection(manifest):
 after={p:sha(ROOT/p) if (ROOT/p).is_file() else None for p in manifest['protected_before']}
 changed=[p for p,h in after.items() if h!=manifest['protected_before'][p]]
 if changed:raise RuntimeError('STOP: protected files changed: '+', '.join(changed))
 return after

def choose_vintages(obs):
 """Prefer one explicitly cumulative bulletin per POS year over isolated snapshots."""
 obs=obs.copy();obs['selection_priority']=10
 obs.loc[obs.raw_file_path.str.contains('siat_'),'selection_priority']=30
 pos=obs.variable_key.eq('pos_turnover')
 for year,title in [(2017,'2018 year'),(2018,'2018 year'),(2019,'2019 annual'),*[(y,'2026 march') for y in range(2020,2027)]]:
  match=pos & obs.reference_period.str.startswith(str(year)) & obs.source_vintage.str.contains(title)
  obs.loc[match,'selection_priority']=50
 selected=obs.sort_values(['selection_priority','retrieved_at']).drop_duplicates(['variable_key','reference_period'],keep='last')
 return selected.sort_values(['variable_key','reference_period'])

def safe_flows(group):
 """De-cumulate only consecutive months of a consistent within-year raw vintage."""
 group=group.copy().sort_values('reference_period');group['period']=pd.PeriodIndex(group.reference_period,freq='M')
 if group.period.duplicated().any():raise ValueError('Duplicate reference months in flow input')
 levels=group.set_index('period').raw_value
 byperiod=group.set_index('period');flows={};log=[]
 for _,r in group.iterrows():
  p=r.period;prev=p-1;value=np.nan;reason=None
  if p.month==1:value=r.raw_value;reason='JANUARY_RESET'
  elif prev not in byperiod.index:reason='MISSING_PREVIOUS_MONTH'
  elif byperiod.loc[prev,'unit']!=r.unit:reason='UNIT_MISMATCH_WITHHELD'
  elif byperiod.loc[prev,'raw_file_path']!=r.raw_file_path:reason='VINTAGE_MISMATCH_WITHHELD'
  else:
   value=r.raw_value-levels.loc[prev];reason='WITHIN_YEAR_SAME_VINTAGE_DIFFERENCE'
   if value<0:value=np.nan;reason='NON_MONOTONIC_YTD_WITHHELD'
  flows[p]=value
  log.append({'variable_key':r.variable_key,'reference_period':str(p),'raw_ytd':r.raw_value,'previous_period':str(prev) if p.month>1 else None,'monthly_flow':value,'decision':reason,'source_url':r.source_url,'raw_file_path':r.raw_file_path,'cumulative_total_reconciliation':'same-vintage difference algebraically reconciles; incomplete years not certified'})
 flow=pd.Series(flows,dtype=float).sort_index();lag=flow.shift(12) if len(flow) and flow.index.equals(pd.period_range(flow.index.min(),flow.index.max(),freq='M')) else flow.reindex(pd.period_range(flow.index.min(),flow.index.max(),freq='M')).shift(12)
 current=flow.reindex(lag.index);positive=(current>0)&(lag>0)
 yoy=pd.Series(np.nan,index=current.index);yoy.loc[positive]=100*np.log(current.loc[positive]/lag.loc[positive])
 pct=pd.Series(np.nan,index=current.index);pct.loc[positive]=100*(current.loc[positive]/lag.loc[positive]-1)
 return flow,yoy,pct,log

def main():
 manifest=json.loads((OUT/'phase6a2_run_manifest.json').read_text());protection(manifest)
 # Read and fingerprint every authoritative Phase 6A.1 input; do not amend them.
 phase1=ROOT/'results/research/phase6a1';inputs={}
 for p in phase1.iterdir():
  if p.is_file():
   inputs[p.relative_to(ROOT).as_posix()]=sha(p)
   if p.suffix=='.csv':pd.read_csv(p)
   elif p.suffix=='.json':json.loads(p.read_text())
 report1=ROOT/'docs/modeling/phase6a/phase6a1_cbu_data_audit.md';report1.read_text(encoding='utf-8');inputs[report1.relative_to(ROOT).as_posix()]=sha(report1)
 obs=pd.read_csv(OUT/'all_recovered_observations.csv');selected=choose_vintages(obs)
 selected.to_csv(OUT/'selected_research_observations.csv',index=False,encoding='utf-8-sig')
 overlaps=[];quality=[]
 for (key,period),g in obs.groupby(['variable_key','reference_period']):
  if len(g)>1:
   overlaps.append({'variable_key':key,'reference_period':period,'source_count':len(g),'minimum_raw_value':g.raw_value.min(),'maximum_raw_value':g.raw_value.max(),'absolute_difference':g.raw_value.max()-g.raw_value.min(),'relative_difference_pct':100*(g.raw_value.max()/g.raw_value.min()-1) if g.raw_value.min()>0 else None,'unit_labels':'|'.join(g.unit.unique()),'interpretation':'overlapping vintages; changed values preserved; revisions vs parser/scope differences require evidence'})
 for key,g in selected.groupby('variable_key'):
  periods=pd.PeriodIndex(g.reference_period,freq='M');values=pd.Series(g.raw_value.to_numpy(),index=periods)
  for period,value in values.items():
   prev=period-1;flags=[]
   if value<0:flags.append('NEGATIVE_RAW_VALUE')
   if g.flow_type.eq('nominal_ytd').all() and period.month>1 and prev in values and value<values.loc[prev]:flags.append('NON_MONOTONIC_YTD')
   if prev in values and values.loc[prev]>0 and (value/values.loc[prev]>3 or value/values.loc[prev]<1/3) and period.month!=1:flags.append('EXTREME_LEVEL_CHANGE_WARNING')
   quality.append({'variable_key':key,'reference_period':str(period),'raw_value':value,'duplicate_selected_period':bool(periods.duplicated().any()),'january_reset_applied':period.month==1 and g.flow_type.eq('nominal_ytd').all(),'quality_flags':'|'.join(flags),'missing_previous_month':prev not in values,'interpolation_used':False})
 pd.DataFrame(overlaps).to_csv(OUT/'phase6a2_source_overlap_audit.csv',index=False,encoding='utf-8-sig')
 pd.DataFrame(quality).to_csv(OUT/'phase6a2_quality_audit.csv',index=False,encoding='utf-8-sig')
 panel=pd.DataFrame(index=GRID);recon=[]
 for key,g in selected.groupby('variable_key'):
  series=pd.Series(g.clean_value.to_numpy(),index=pd.PeriodIndex(g.reference_period,freq='M'))
  panel[key]=series.reindex(GRID)
  panel[key+'_raw_level']=pd.Series(g.raw_value.to_numpy(),index=series.index).reindex(GRID)
  if g.flow_type.eq('nominal_ytd').all():
   flow,yoy,pct,log=safe_flows(g);recon.extend(log)
   panel[key+'_monthly_flow']=flow.reindex(GRID);panel[key+'_monthly_log_yoy']=yoy.reindex(GRID);panel[key+'_monthly_pct_yoy']=pct.reindex(GRID)
 for key in KEYS:
  if key not in panel:panel[key]=np.nan
 # Original nominal registry transformations are preserved under explicit proxy names.
 master=pd.read_parquet(ROOT/'data/master/v1_monthly.parquet')
 index=pd.to_datetime(master.date).dt.to_period('M')
 for col in ['industrial_production_yoy','construction_yoy','retail_trade_yoy','exports_non_gold_yoy','imports_total_yoy']:
  if col in master:panel[col+'_registry_proxy']=pd.Series(master[col].to_numpy(),index=index).reindex(GRID)
 breaks=[
  {'variable_key':'services_output','break_month':'2024-09','type':'DEFINITION_BREAK','evidence':'SIAT metadata: from September 2024, informal and hidden economic activity survey results are included','action':'retain published observations with explicit regime flag; do not assume cross-regime comparability'},
  {'variable_key':'pos_turnover','break_month':'2025-01','type':'DEFINITION_BREAK','evidence':'Official Uzbek December 2025 article labels January–December POS (E-POS); prior definition equivalence and start date not confirmed','action':'2025-01 is a conservative boundary for the reported YTD window, NOT a verified system launch date; withhold YoY crossing boundary'},
  {'variable_key':'industrial_production','break_month':'2019-01','type':'UNVERIFIED','evidence':'2018 archived growth headlines vs SIAT physical-volume definition; historical universe not reconciled','action':'retain 2018 under distinct historical candidate key'},
  {'variable_key':'construction','break_month':'2021-01','type':'UNVERIFIED','evidence':'Historical headline universe and revised current SIAT coverage not reconciled','action':'retain 2018–2020 historical candidates separately'},
  {'variable_key':'retail_trade','break_month':'2020-01','type':'UNVERIFIED','evidence':'Catering/retail coverage and revision differences in historical reports','action':'retain 2018–2019 candidates separately; compare overlap'},
  {'variable_key':'imports_total','break_month':'2018-06','type':'DEFINITION_BREAK','evidence':'2018 trade release reports recalculation of 2017/first-half 2018 with inbound/outbound tourism survey','action':'imports are goods AND services; goods-only series remains separate definition gap'},
  {'variable_key':'exports_ex_gold_exact','break_month':'2024-03','type':'UNVERIFIED','evidence':'Direct no-gold total and subtraction disagree in March/April 2024 and other releases; both candidates retained','action':'both inconsistent versions excluded from exact research key'},
  {'variable_key':'exports_ex_gold_exact','break_month':'2026-08','type':'UNVERIFIED','evidence':'August 2026 release states that precious metals other than non-monetary gold are assigned to non-ferrous metals; effective change date not specified','action':'date marks observed metadata, not an invented effective break; subtract explicitly labelled non-monetary gold only'},
  {'variable_key':'job_search_index','break_month':'2024-01','type':'DEFINITION_BREAK','evidence':'CBU Q4 2025 labour review notes 2024–2025 shift toward social networks/apps','action':'do not assume stable Google Trends interpretation; exact protocol still unknown'}]
 panel['services_output_regime']=np.where(GRID<pd.Period('2024-09'),'before_2024_09','expanded_coverage_2024_09_onward')
 panel['pos_turnover_scope_verified']=GRID<pd.Period('2025-01')
 # Source definition changes cannot be crossed by mechanically differencing.
 panel.loc[pd.Period('2024-09'),'services_output_nominal_ytd_monthly_flow']=np.nan
 for row in recon:
  if row['variable_key']=='services_output_nominal_ytd' and row['reference_period']=='2024-09':row['monthly_flow']=np.nan;row['decision']='KNOWN_DEFINITION_BREAK_WITHHELD'
 for col in ['services_output_nominal_ytd_monthly_log_yoy','services_output_nominal_ytd_monthly_pct_yoy']:
  panel.loc[(GRID>=pd.Period('2024-09'))&(GRID<pd.Period('2025-09')),col]=np.nan
 for col in ['pos_turnover_monthly_log_yoy','pos_turnover_monthly_pct_yoy']:
  panel.loc[GRID>=pd.Period('2025-01'),col]=np.nan
 # No monthly GDP: quarterly target is read only for coverage accounting.
 quarterly=pd.read_parquet(ROOT/'data/master/gdp_quarterly.parquet');qset=set(quarterly.quarter)
 classifications=[];coverage_rows=[];gap=[];matrix=pd.DataFrame(index=GRID)
 counts=obs.groupby(['variable_key','reference_period']).size()
 for key,classification,note in zip(KEYS,CLASSES,NOTES):
  cov=coverage(panel[key]);coverage_rows.append({'variable_key':key,'coverage_basis':'published growth pct for real indices; nominal YTD level for imports/POS/non-gold; direct monthly receipts',**cov})
  classifications.append({'variable_key':key,'classification':classification,**cov,'conceptual_mapping':note,'source_release_date_policy':'historical first releases unknown; retrieval timestamp preserved','latest_source_date':'2026-07' if key=='pos_turnover' else cov['end_month']})
  for p in GRID:
   status='AVAILABLE' if pd.notna(panel.loc[p,key]) else 'MISSING'
   number=int(counts.get((key,str(p)),0))
   if status=='AVAILABLE' and number>1:status='DUPLICATE_SOURCE'
   if any(b['variable_key']==key and b['break_month']==str(p) and b['type']=='DEFINITION_BREAK' for b in breaks):status='DEFINITION_BREAK' if pd.notna(panel.loc[p,key]) else status
   matrix.loc[p,key]=status
   gap.append({'variable_key':key,'reference_period':str(p),'status':status,'source_count':number,'value_present':pd.notna(panel.loc[p,key]),'interpolated':False,'definition_regime':panel.loc[p,'services_output_regime'] if key=='services_output' else None})
 # Report all historical/proxy candidates separately as well.
 for key in panel.columns:
  if key not in KEYS and not key.endswith('_raw_level') and pd.api.types.is_numeric_dtype(panel[key]):coverage_rows.append({'variable_key':key,'coverage_basis':'separate candidate or derived research transformation',**coverage(panel[key])})
 core=['industrial_production','construction','retail_trade','imports_total'];numeric=core+['services_output','exports_ex_gold_exact','trade_paid_services_receipts'];full=numeric+['job_search_index']
 specs={'FULL_ORIGINAL_CBU_INDICATOR_SET':full,'CORE_NUMERIC_OFFICIAL_DATA_SET':numeric,'CORE_4':core,'CORE_PLUS_SERVICES':core+['services_output'],'CORE_PLUS_SERVICES_PLUS_EXACT_NON_GOLD':core+['services_output','exports_ex_gold_exact'],'CORE_PLUS_SERVICES_PLUS_RECEIPTS':core+['services_output','trade_paid_services_receipts'],'FULL_CBU_STYLE_SET':full}
 commons=[]
 for name,keys in specs.items():
  joint=panel[keys].notna().all(axis=1);cov=coverage(pd.Series(np.where(joint,1,np.nan),index=GRID));a,b,n=longest(joint)
  conservative=joint.copy()
  if 'services_output' in keys:conservative.loc[pd.Period('2024-09')]=False
  ca,cb,cn=longest(conservative)
  available_q=[q for q in sorted(qset) if joint.reindex(pd.period_range(pd.Period(q,freq='Q').start_time.to_period('M'),pd.Period(q,freq='Q').end_time.to_period('M'),freq='M')).fillna(False).all()]
  # Potential calendar origins only: no historical release or model usability assertion.
  available_quarters={pd.Period(q,freq='Q') for q in available_q}
  potential=sum(all(q-i in available_quarters for i in range(1,13)) for q in available_quarters)
  commons.append({'sample':name,'variable_keys':'|'.join(keys),'common_start':cov['start_month'],'common_end':cov['end_month'],'common_month_count':int(joint.sum()),'missing_months':int((~joint).sum()),'longest_continuous_start':a,'longest_continuous_end':b,'continuous_months':n,'longest_without_crossing_known_services_break_start':ca,'longest_without_crossing_known_services_break_end':cb,'longest_without_crossing_known_services_break_months':cn,'quarterly_gdp_reference_count':len(available_q),'potential_quarterly_forecast_origin_count_after_12_training_quarters':potential,'potential_H1_H2_H3_calendar_origin_count':3*potential,'usable_historical_first_release_verified_origin_count':0,'usable_historical_origin_count':None,'origin_count_basis':'latest-vintage calendar alignment only; historical releases, GDP target YTD convention and paper real trade/receipt deflators unresolved; no model estimated'})
 panel.index=panel.index.astype(str);panel.index.name='reference_period';panel.to_csv(DATA/'cbu_midas_monthly_panel.csv',encoding='utf-8-sig');panel.reset_index().to_parquet(DATA/'cbu_midas_monthly_panel.parquet',index=False)
 matrix.index=matrix.index.astype(str);matrix.index.name='month';matrix.to_csv(OUT/'phase6a2_coverage_matrix.csv',encoding='utf-8-sig')
 colors={'AVAILABLE':'#d5efdb','MISSING':'#f5caca','DUPLICATE_SOURCE':'#dae9fa','DEFINITION_BREAK':'#ffe1a0','UNIT_BREAK':'#ffd2aa','UNVERIFIED':'#e7d9fa'}
 html='<html><head><meta charset="utf-8"><title>Phase 6A.2 coverage</title><style>body{font:14px Arial;margin:24px}td,th{padding:5px;border:1px solid #ddd}table{border-collapse:collapse}thead{position:sticky;top:0;background:white}</style></head><body><h1>Phase 6A.2 research coverage</h1><p>January 2018–August 2026. Latest-vintage observations; historical release availability is not certified. Duplicate sources mean multiple preserved releases. Break cells identify boundaries, not missing values.</p><table><thead><tr><th>Month</th>'+''.join(f'<th>{k}</th>' for k in KEYS)+'</tr></thead><tbody>'
 for p,r in matrix.iterrows():html+='<tr><th>'+p+'</th>'+''.join(f'<td style="background:{colors[v]}">{v}</td>' for v in r)+'</tr>'
 (OUT/'phase6a2_coverage_matrix.html').write_text(html+'</tbody></table></body></html>',encoding='utf-8')
 for name,rows in [('collection_status',classifications),('candidate_coverage',coverage_rows),('monthly_gap_audit',gap),('definition_breaks',breaks),('reconstruction_log',recon),('common_sample_audit',commons)]:pd.DataFrame(rows).to_csv(OUT/f'phase6a2_{name}.csv',index=False,encoding='utf-8-sig')
 provenance=obs.copy();selected_keys=set(map(tuple,selected[['variable_key','reference_period','raw_file_path']].values))
 provenance['selected_for_panel']=[tuple(r) in selected_keys for r in obs[['variable_key','reference_period','raw_file_path']].values]
 provenance['publication_date']=provenance.source_release_date;provenance['assumed_release_lag_days']=None;provenance['file_type']=provenance.raw_file_path.str.extract(r'(\.[^.]+)$')[0]
 provenance.to_csv(OUT/'phase6a2_provenance.csv',index=False,encoding='utf-8-sig')
 inventory=[]
 for path,meta in source_metas().items():
  p=ROOT/path
  if not p.is_file():raise ValueError('Missing archived source: '+path)
  if sha(p)!=meta['checksum']:raise ValueError('Raw checksum mismatch: '+path)
  associated=obs[obs.raw_file_path==path]
  inventory.append({**meta,'institution':'CBU' if 'cbu.uz' in meta['source_url'] else 'Statistics Agency / SIAT','source_title':' | '.join(associated.variable_key.unique()),'publication_date':next(iter(associated.source_release_date.dropna()),None),'reference_start':associated.reference_period.min() if len(associated) else None,'reference_end':associated.reference_period.max() if len(associated) else None,'unit':' | '.join(associated.unit.unique()),'frequency':'M' if len(associated) else None,'selector':' | '.join(associated.table_selector.unique()),'parser_version':VERSION if len(associated) else None,'schema_fingerprint':' | '.join(associated.schema_fingerprint.unique()),'archive_hash_verified':True,'source_release_policy':'observed update/retrieval distinct from unknown historical first release'})
 pd.DataFrame(inventory).to_csv(OUT/'phase6a2_source_inventory.csv',index=False,encoding='utf-8-sig')
 archived_paths={p.relative_to(ROOT).as_posix() for p in (ROOT/'data/raw/research/phase6a2').rglob('*') if p.is_file()}
 if archived_paths-set(source_metas()):raise ValueError('STOP: research raw archives without source metadata')
 unknown='NOT_SPECIFIED_IN_ORIGINAL_PAPER';paperurl='https://cbu.uz/upload/iblock/3d6/6kbvfiumraqdb4ejh0qrzkc6y4pbr3vi/MIDAS_WP.pdf'
 paper=[('title','Краткосрочное прогнозирование ВВП с помощью MIDAS-модели','1'),('author','Руслан Яковлев / Ruslan Yakovlev; Monetary Policy Department','1'),('publication_date','2023-11-30; observed official publication index, not June 2025 page-update date','official index'),('sample_start','2018-01','5'),('sample_end','2023-10','5'),('target','real GDP growth; Q4 forecast interpreted as annual GDP growth; exact standalone-quarter/YTD conversion '+unknown,'6'),('all_indicator_transformation','real cumulative year-on-year growth; deflators, formulas and seasonal adjustment '+unknown,'6'),('units','percent/growth shown in figures; raw unit definitions '+unknown,'5–6'),('data_sources','CBU, Statistics Agency, open internet search queries; exact dataset/table IDs '+unknown,'6'),('query_methodology',unknown,'6'),('empirical_lag_count',unknown,'2–4,7'),('model_variants','AR1; arithmetic mean of three monthly observations; Almon; U-MIDAS; MIDAS-GETS; MIDAS-GETSIS','6–7')]
 terms=['промышленного производства','строительства','сервиса','розничная торговля','поступления от торговли и платных услуг','экспорт (без учета золота)','импорт','запросы людей по поиску работы']
 for key,term in zip(['industrial_production','construction','services_output','retail_trade','trade_paid_services_receipts','exports_ex_gold_exact','imports_total','job_search_index'],terms):paper.append((key,term,'6'))
 pd.DataFrame([{'field':k,'definition':v,'source_page':page,'source_url':paperurl,'exact_selector':unknown,'raw_unit':unknown,'real_deflator':unknown,'query_keywords':unknown,'query_topics':unknown,'query_geography':unknown,'query_category':unknown,'query_search_type':unknown,'query_normalization':unknown,'query_aggregation':unknown} for k,v,page in paper]).to_csv(OUT/'phase6a2_original_paper_definition_table.csv',index=False,encoding='utf-8-sig')
 recommendations={'next_action':'COLLECT_MORE_DATA','full_replication':'NOT_READY','backtest_2018_2026':'PARTIAL','research_panel_created':True,'models_estimated':False,'job_query_protocol':'PUBLIC_SOURCE_CONFIRMED_QUERY_SPEC_UNKNOWN','full_sample_months':0,'core_numeric_official_sample_months':0,'core4_common_continuous_months':next(r['continuous_months'] for r in commons if r['sample']=='CORE_4'),'priority_actions':['Recover a complete monthly cash plus trade/service classified-terminal receipts history; never use all POS as exact receipts.','Reconcile 2018–2020 real construction/retail and 2018 industrial scope against revised SIAT growth.','Recover missing historical exact non-monetary-gold trade totals; preserve conflicting published totals separately.','Verify September 2024 services methodology and POS/E-POS coverage before pooling regimes.','Obtain an official job-query basket/normalization protocol and document original real trade/receipt deflators.'],'historical_release_verified_forecast_origins':0,'production_modified':False,'phase5d_modified':False,'phase5c_frozen_evidence_modified':False,'historical_phase5_forecasts_modified':False,'canonical_master_modified':False}
 (OUT/'phase6a2_recommendations.json').write_text(json.dumps(recommendations,indent=2),encoding='utf-8')
 manifest.update(phase='6A.2',completed_at=datetime.now(timezone.utc).isoformat(),authoritative_phase6a1_inputs=inputs,protected_after=protection(manifest),protected_hash_failures=[],protected_file_count=len(manifest['protected_before']),models_estimated=False,canonical_master_modified=False,production_modified=False,phase5d_modified=False,phase5c_frozen_evidence_modified=False,historical_phase5_forecasts_modified=False,parser_version=VERSION,raw_source_count=len(inventory),raw_checksums_verified=True,source_log_limitation='Earlier concurrent collectors shared a fetch log; metadata recovered from collector source manifests and immutable filenames where needed. Missing HTTP headers remain null, never guessed.',registry_amended=False)
 (OUT/'phase6a2_run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 print(pd.DataFrame(classifications)[['variable_key','classification','start_month','end_month','observation_count','missing_month_count']].to_string(index=False))
 print(pd.DataFrame(commons)[['sample','common_month_count','continuous_months']].to_string(index=False))

if __name__=='__main__':main()
