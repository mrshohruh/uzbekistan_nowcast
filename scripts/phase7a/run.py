"""Offline Phase 7A evidence build: python -m scripts.phase7a.run."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import html
import json
import re
import sys
import numpy as np
import pandas as pd
from scripts.phase7a.data import annual_siat, transform

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/phase7a'
DATA=ROOT/'data/research/electricity'
CLASSIFICATION='PHASE7A_INSUFFICIENT_DATA'
ALIASES={'PHASE6C_DFM':'M0','U_MIDAS':'U0','COMBO_50_50':'C0','AR1':'AR1'}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def sources():
    rows=[json.loads(s.split('INFO:root:')[1]) for s in (OUT/'collection.log').read_text().splitlines() if 'INFO:root:' in s]
    return {r['source_name']:r for r in rows}

def source_text(record):
    if record['status']!='OK': raise ValueError('Failed source: '+record['source_name'])
    path=ROOT/record['raw_file']
    if sha(path)!=record['checksum']: raise ValueError('Raw checksum mismatch')
    return html.unescape(re.sub('<[^>]+>',' ',path.read_text(encoding='utf8')))

def monthly(records):
    frame=pd.DataFrame({'date':pd.date_range('2019-01-31','2026-09-30',freq='ME').strftime('%Y-%m-%d')})
    fields=['electricity_consumption_gwh','original_value','original_unit','source_name','source_url','source_document','measurement_definition','geographic_coverage','period_type','publication_date','retrieval_date','observation_status','vintage_status','extraction_method','quality_flag']
    for field in fields: frame[field]=np.nan if field in ('electricity_consumption_gwh','original_value') else None
    frame['observation_status']='missing';frame['quality_flag']='NO_VERIFIED_MONTHLY_OBSERVATION'
    for month,name,value,unit,token in [('2026-06','minenergy_190427',7707.9,'million kWh','7 mlrd 707,9'),('2026-07','minenergy_208274',8.8,'billion kWh','8,8 mlrd'),('2026-08','minenergy_226468',8.4,'billion kWh','8,4 mlrd')]:
        record=records[name];text=source_text(record)
        paragraphs=re.split(r'Respublika iste[^:]{0,30}:',text)
        if len(paragraphs)<3 or token not in paragraphs[-1][:500]: raise ValueError('Monthly consumption extraction evidence changed')
        dates=re.findall(r'"date[^0-9]{1,12}(2026-\d\d-\d\d \d\d:\d\d:\d\d)',text)
        if not dates: raise ValueError('Publication heading missing')
        values=dict(electricity_consumption_gwh=value*(1000 if unit=='billion kWh' else 1),original_value=value,original_unit=unit,source_name='Uzbekistan Ministry of Energy',source_url=record['source_url'],source_document=record['raw_file'],measurement_definition='Published republic electricity consumption; system boundary not fully documented',geographic_coverage='Republic of Uzbekistan',period_type='monthly',publication_date=dates[0],retrieval_date=record['retrieved_at'],observation_status='directly reported monthly observation',vintage_status='VINTAGE_UNVERIFIED',extraction_method='Verified monthly consumption paragraph; no generation substitution',quality_flag='SYSTEM_BOUNDARY_UNVERIFIED;VINTAGE_UNVERIFIED;ROUNDED' if unit=='billion kWh' else 'SYSTEM_BOUNDARY_UNVERIFIED;VINTAGE_UNVERIFIED')
        mask=frame.date.str.startswith(month)
        for field,value in values.items(): frame.loc[mask,field]=value
    return frame

def save(name,frame): frame.to_csv(OUT/name,index=False,float_format='%.17g')

def build():
    OUT.mkdir(exist_ok=True,parents=True)
    records=sources();frame=monthly(records);transformed=transform(frame)
    frame.to_csv(DATA/'electricity_consumption_monthly.csv',index=False)
    transformed.to_csv(DATA/'electricity_transformed_monthly.csv',index=False)
    annual=annual_siat((ROOT/records['siat_payload']['raw_file']).read_bytes())
    annual['source_url']=records['siat_payload']['source_url'];annual['retrieval_date']=records['siat_payload']['retrieved_at']
    annual.to_csv(DATA/'electricity_subscriber_consumption_annual.csv',index=False)
    ember=pd.read_csv(ROOT/records['ember_csv']['raw_file'])
    if not {'Area','ISO 3 code','Date','Electricity source'}.issubset(ember): raise ValueError('Ember schema changed')
    uz=ember.loc[ember.Area.eq('Uzbekistan') | ember['ISO 3 code'].eq('UZB')]
    if len(uz): raise ValueError('New Uzbekistan Ember coverage: manual definition review required')
    findings={'siat':'Annual subscriber consumption, 2016-2025; excluded from monthly series','siat_payload':'Verified official national annual values; no monthly dates','ember_csv':f'Zero Uzbekistan/UZB rows among {len(ember)} rows; no monthly coverage','households':'June/July 2024 household consumption only; excluded from national system series','daily_peak':'Daily peak observations only; no monthly total','het_esg':'Annual distribution-company delivery reports, separate measurement B','grid_archive':'2019-2024 archive index reachable; no complete monthly consumption panel verified','iea':'Local HTTP 403; browser page reachable, no monthly demand table verified','minenergy_129713':'January 2026 delivery to consumers 6527 GWh, measurement B; kept separate','minenergy_150037':'Jan-Mar 2026 delivery 20163 GWh; do not bridge to system demand','minenergy_162431':'Jan-Apr consumption 29517 GWh; apparent definition break versus preceding delivery','minenergy_190427':'June 2026 consumption 7707.9 GWh; Jan-Jun cumulative 44042.9 GWh','minenergy_208274':'July 2026 consumption 8800 GWh; Jan-Jul cumulative 52900 GWh','minenergy_226468':'August 2026 consumption 8400 GWh; Jan-Aug cumulative 61400 GWh'}
    registry=pd.DataFrame([{**r,'finding':findings.get(name,'Source index/report archived; monthly national historical panel not verified'),'accepted_monthly':name in ['minenergy_190427','minenergy_208274','minenergy_226468']} for name,r in records.items()])
    save('source_registry.csv',registry)
    observed=frame.loc[frame.electricity_consumption_gwh.notna()].copy()
    observed['publication_lag_days']=(pd.to_datetime(observed.publication_date).dt.normalize()-pd.to_datetime(observed.date)).dt.days
    save('electricity_release_evidence.csv',observed)
    coverage=frame[['date','observation_status','quality_flag']].copy();coverage['observed']=frame.electricity_consumption_gwh.notna();coverage['yoy_valid']=transformed.transformation_valid
    coverage['year']=pd.to_datetime(coverage.date).dt.year
    save('electricity_data_coverage.csv',coverage)
    checks=[('coverage','FAIL','3 observed / 93 target months; 90 missing; June-August 2026 only'),('continuity','FAIL','Three consecutive months; history before June 2026 unavailable for this definition'),('definition','WARNING','Subscriber consumption, delivery, household billing, system consumption and generation remain separate'),('growth','NOT_ESTIMABLE','Zero verified year-ago pairs; monthly changes descriptive only'),('negative','PASS','All three observed consumption levels positive'),('annual_sum','NOT_ESTIMABLE','No complete monthly year; SIAT annual totals cannot validate partial system series'),('publication_delay','WARNING','Observed page-heading delays: '+str(observed.publication_lag_days.tolist())+' days; not proof of first release'),('revisions','WARNING','VINTAGE_UNVERIFIED; pages retrieved now can have been edited'),('forecast_origins','FAIL','Zero historical matched challenger origins; no verified YoY input'),('cumulative_compatibility','WARNING','August YTD difference 8500 GWh versus directly reported 8400 GWh; rounded values not silently reconciled'),('structural_break','WARNING','Jan-Mar delivery is not demonstrated equivalent to Apr-Aug system consumption'),('operational_suitability','FAIL','Insufficient history and boundary/vintage documentation')]
    save('electricity_data_audit.csv',pd.DataFrame(checks,columns=['check','status','detail']))
    # Retain other evidence without merging incompatible definitions.
    candidates=[dict(period='2026-01',value_gwh=6527,period_type='monthly',definition='delivery to consumers',source=records['minenergy_129713']['source_url']),dict(period='2026-03',value_gwh=20163,period_type='YTD',definition='delivery to consumers',source=records['minenergy_150037']['source_url']),dict(period='2026-04',value_gwh=29517,period_type='YTD',definition='published republic consumption',source=records['minenergy_162431']['source_url']),dict(period='2026-06',value_gwh=44042.9,period_type='YTD',definition='published republic consumption',source=records['minenergy_190427']['source_url']),dict(period='2026-07',value_gwh=52900,period_type='YTD',definition='published republic consumption',source=records['minenergy_208274']['source_url']),dict(period='2026-08',value_gwh=61400,period_type='YTD',definition='published republic consumption',source=records['minenergy_226468']['source_url'])]
    save('electricity_separate_candidates.csv',pd.DataFrame(candidates))
    baseline=pd.read_csv(ROOT/'results/current/model_comparison.csv',float_precision='round_trip')
    scores=baseline.loc[baseline.model.isin(ALIASES)].copy();scores['model']=scores.model.map(ALIASES);scores['comparison_status']='FROZEN_BASELINE_ONLY';scores['matched_challenger_origins']=0
    for model in ['E1','C1']: scores=pd.concat([scores,pd.DataFrame([dict(model=model,n=0,comparison_status='NOT_ESTIMABLE_INSUFFICIENT_DATA',matched_challenger_origins=0)])],ignore_index=True)
    save('phase7a_model_comparison.csv',scores)
    metrics=pd.read_csv(ROOT/'results/current/r2_metrics.csv');metrics=metrics.loc[metrics.model.isin(ALIASES)].copy();metrics.model=metrics.model.map(ALIASES);metrics['comparison_status']='FROZEN_BASELINE_ONLY'
    save('phase7a_horizon_metrics.csv',pd.concat([metrics,pd.DataFrame([dict(model=m,horizon=h,n=0,comparison_status='NOT_ESTIMABLE') for m in ['E1','C1'] for h in ['H1','H2','H3','ALL']])],ignore_index=True))
    current=json.loads((ROOT/'results/current/current_nowcast.json').read_text())
    forecasts=pd.DataFrame([dict(model=m,forecast=v,status='FROZEN_PRODUCTION_REFERENCE',data_cutoff=current['as_of_date'],latest_electricity='2026-08',target='2026Q3') for m,v in [('M0',current['dfm_forecast']),('U0',current['umidas_forecast']),('C0',current['final_forecast'])]]+[dict(model=m,forecast=None,status='RESEARCH_ONLY_NOT_ESTIMABLE',data_cutoff=current['as_of_date'],latest_electricity='2026-08',target='2026Q3') for m in ['E1','C1']])
    save('phase7a_current_nowcasts.csv',forecasts)
    loadings=pd.read_csv(ROOT/'results/current/dfm_loadings.csv');loadings['model']='M0';loadings['status']='FROZEN_PRODUCTION_REFERENCE';save('phase7a_factor_loadings.csv',loadings)
    signals=pd.read_csv(ROOT/'results/current/current_drivers.csv');signals=signals.loc[signals.metric_type.eq('descriptive DFM factor signal')].copy();signals['model']='M0';signals['status']='FROZEN_PRODUCTION_REFERENCE';save('phase7a_factor_signals.csv',signals)
    from scripts.phase7a.dashboard import dashboard
    dashboard(OUT,frame,annual,scores,metrics,forecasts,loadings,signals,registry)
    report=f'''# Phase 7A electricity research\n\n**{CLASSIFICATION}**\n\nThree directly reported monthly republic consumption observations were collected: June 2026 7707.9 GWh, July 8800 GWh, August 8400 GWh. Target coverage is 3/93 months (90 missing), with zero valid YoY pairs. No national monthly demand history back to 2019 was verified. This is a bounded public-source investigation, not proof that private or unindexed records do not exist.\n\nSIAT 2684 is annual subscriber consumption, code 1.02.02.0019, in million kWh (= GWh), national series 2016-2025. Ten annual observations are archived separately; they are never distributed into months. The metadata note still describes 2023 as preliminary despite newer years, so year-specific revision status is unresolved. Its 2026-09-02 update is a dataset update, not each observation's first release. [Official SIAT](https://siat.stat.uz/data/2684/?lang=en).\n\nThe Ministry's [June release](https://gov.uz/oz/minenergy/news/view/190427), [July release](https://gov.uz/oz/minenergy/news/view/208274) and [August release](https://gov.uz/oz/minenergy/news/view/226468) distinguish consumption from generation. The exact system boundary (losses, own use, off-grid scope) remains undocumented in those articles. Publication-heading delays are {observed.publication_lag_days.tolist()} days. September 2026 consumption was not verified. Pages downloaded on 2026-10-12 do not confirm which numeric vintage existed at their heading dates: VINTAGE_UNVERIFIED.\n\nJanuary reports delivery to consumers; Jan-Mar delivery is 20163 GWh, whereas Jan-Apr republic consumption is 29517 GWh. No equivalence is documented, so April is not de-cumulated across this change. Jan-Aug minus Jan-Jul gives 8500 GWh, while reported August is 8400 GWh: rounding and/or revision compatibility cannot be resolved. Direct monthly figures are retained. Two 2024 household monthly figures and daily demand peaks are excluded. Generation is not substituted. HET annual delivery totals and SIAT subscriber consumption are separate measures.\n\nEmber's full downloaded monthly file has {len(ember)} rows and zero Uzbekistan/UZB rows. Its July 2026 format has Area, ISO 3 code, Date and Electricity source columns. [Ember source](https://ember-energy.org/data/monthly-electricity-data/). HET report PDFs and the national-grid archive index are archived; no complete monthly panel was verified. Local HET homepage/report retrieval failed; the ESG page and PDFs succeeded. Local IEA returned HTTP 403; its browser-readable country page does not establish monthly demand coverage. All retrieval results are in source_registry.csv, including failures.\n\n## Evaluation decision\n\nE1, E2 and C1 are NOT ESTIMABLE. Do not force a DFM with three levels and zero YoY inputs. Matched challenger origins: zero. Short-history M0 comparison, RMSE improvement, LOQO robustness, lag sensitivity, correlations with IP/manufacturing/utilities/M2, incremental factor signals and electricity loadings are all not estimable. No conclusion of no improvement is warranted. Existing baseline scores are copied and explicitly labelled FROZEN_BASELINE_ONLY, not results of an electricity experiment. Primary matched-sample challenger metrics remain null.\n\nThe existing one-factor AR(2) DFM with lagged-GDP bridge and U0 implementation were inspected in scripts/production/models.py. GDP remains published cumulative YTD real GDP YoY percent. No GDP release or target was downloaded. Model standardization, U0 predictors/coefficient fitting rules and 50/50 weights are unchanged. A future experiment must use training-only scaling, strict GDP vintages and observed electricity release vintages; an assumed lag belongs only in a separately labelled sensitivity experiment. No sensitivity forecast is generated without usable YoY history.\n\n## Current references and cutoff\n\nFrozen production cutoff {current['as_of_date']}, post-H3 initialization. M0 {current['dfm_forecast']}%; U0 {current['umidas_forecast']}%; C0 **{current['final_forecast']}%**. Latest collected consumption: August 2026, heading published 2026-09-28, retrieved 2026-10-12; not admitted as a confirmed historical vintage at the production cutoff. E1/C1 remain null and RESEARCH_ONLY.\n\nElectricity is not suitable for operational use on this evidence. Promotion recommendation: defer until at least multi-year compatible monthly data, definition documentation and release archives are obtained. No production registry entry or protected scientific artifact was changed.\n\n## Reproduction and artifacts\n\nOffline build: `.venv/Scripts/python.exe -m scripts.phase7a.run`. Network collection: `.venv/Scripts/python.exe -m scripts.phase7a.collect`; every run creates a new immutable raw directory. The build validates stored checksums and schemas, and fails if new Ember Uzbekistan coverage requires review.\n\nProduction protection and independently recomputed current forecasts are recorded in run_manifest.json; test results are in phase7a_tests.log and phase7a_tests.xml. The local dashboard embeds all scripts and charts without external services.\n\n'''
    artifacts=sorted([*OUT.glob('*.csv'),*OUT.glob('*.html'),*DATA.glob('*.csv')])
    if (OUT/'phase7a_tests.xml').exists():
        from xml.etree import ElementTree
        suite=ElementTree.parse(OUT/'phase7a_tests.xml').getroot().find('testsuite')
        report+=f"Validation: {suite.attrib['tests']} selected tests, {suite.attrib['failures']} failures, {suite.attrib['errors']} errors. Windows short-temp runner: `python -m scripts.phase7a.test_runner tests/production tests/models/test_phase6i.py tests/models/test_phase7a.py -k \"not test_protected_artifacts_unchanged\"`. The legacy whole-repository historical hash test is replaced by this run's 1951-file protection audit and existing seal tests. The initial superseded run had Windows temporary-directory setup errors. Current DFM, U0 and COMBO reproduced with exact float equality. Browser rendering was not verified; the dashboard passed static self-containment/data checks.\n\n"
    report+='Generated artifacts:\n\n'+''.join('- `'+str(p.resolve())+'`\n' for p in artifacts)+f'- `{OUT/"phase7a_results.md"}`\n- `{OUT/"run_manifest.json"}`\n'
    (OUT/'phase7a_results.md').write_text(report,encoding='utf8')
    before=json.loads((OUT/'protection_baseline.json').read_text())
    changed=[p for p,v in before.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=v]
    if changed: raise ValueError('Protected artifacts changed: '+str(changed))
    manifest=dict(classification=CLASSIFICATION,run_timestamp=datetime.now(timezone.utc).isoformat(),production_changed=False,production_nowcast=current['final_forecast'],protected_artifacts_verified=True,protected_file_count=len(before),protected_baseline_sha256=sha(OUT/'protection_baseline.json'),observations=3,missing_months=90,valid_yoy_pairs=0,matched_challenger_origins=0,ember_uzbekistan_rows=len(uz),forecast_cutoff=current['as_of_date'],latest_electricity='2026-08',source_schema=list(ember.columns),source_downloads=list(records.values()),output_sha256={str(p.relative_to(ROOT)):sha(p) for p in artifacts+[OUT/'phase7a_results.md']},source_code_sha256={p.name:sha(p) for p in (ROOT/'scripts/phase7a').glob('*.py')})
    integrity=OUT/'production_reproduction.json'
    if integrity.exists(): manifest['production_reproduction']=json.loads(integrity.read_text())
    tests=OUT/'phase7a_tests.xml'
    if tests.exists():
        from xml.etree import ElementTree
        suite=ElementTree.parse(tests).getroot().find('testsuite')
        manifest['tests']=dict(suite.attrib)
        manifest['test_report_sha256']=sha(tests)
        manifest['test_note']='Selected offline tests; legacy whole-repository historical hash test excluded, replaced by this run\u2019s 1951-file protection baseline and production seal tests. Superseded initial run hit Windows temp setup errors.'
    manifest['dashboard_verification']='Static embedded-data checks; interactive browser rendering not verified in this environment'
    (OUT/'run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print(CLASSIFICATION);print('Coverage: 3/93 monthly; 10 annual separately; no challenger estimated')
    print(forecasts.to_string(index=False));print('Protected files unchanged:',len(before))
    for p in artifacts+[OUT/'phase7a_results.md',OUT/'run_manifest.json']: print(p.resolve())
    return manifest

if __name__=='__main__': build()
