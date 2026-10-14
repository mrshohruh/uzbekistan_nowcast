"""Real offline Edge rendering and interaction checks, without network assets."""
from pathlib import Path
import html
import json
import re
import subprocess
import uuid
import hashlib

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/phase7e'


def check():
    original=(OUT/'phase7e_economic_dfm_dashboard.html').read_text(encoding='utf8')
    embedded=json.loads(re.search(r'<script id="phase7e-data" type="application/json">(.*?)</script>',original,re.S).group(1))
    expected_cpi=sum('cpi' in r['original_label'].lower() for r in embedded['inventory'])
    test=r'''<script>
    let checks=[],failures=[];window.addEventListener('error',e=>failures.push(e.message));
    for(const m of D.models){$('model').value=m;$('model').dispatchEvent(new Event('change'));for(const name of tabNames){document.querySelector(`[data-tab="${name}"]`).click();checks.push({model:m,tab:name,nonempty:$('content').textContent.length>60});}}
    for(const s of ['MATCHED_ALL','MATCHED_DEVELOPMENT','MATCHED_HOLDOUT'])for(const h of ['ALL','H1','H2','H3']){$('sample').value=s;$('sample').dispatchEvent(new Event('change'));$('horizon').value=h;$('horizon').dispatchEvent(new Event('change'));tab=tabNames[4];render();checks.push({sample:s,horizon:h,nonempty:document.querySelectorAll('#accuracy tbody tr').length===11});}
    $('model').value='E2';$('model').dispatchEvent(new Event('change'));$('sample').value='MATCHED_HOLDOUT';$('horizon').value='ALL';query='';tab=tabNames[6];render();let inventoryCount=document.querySelectorAll('#inventory tbody tr').length;$('search').value='CPI';$('search').dispatchEvent(new Event('input'));let searchCount=document.querySelectorAll('#inventory tbody tr').length;document.querySelector('#inventory th[data-key="original_label"]').click();let sortedFirst=document.querySelector('#inventory tbody td').textContent;
    query='';tab=tabNames[2];render();let loadingCount=document.querySelectorAll('#loadings tbody tr').length;$('factor-filter').value='F1';$('factor-filter').dispatchEvent(new Event('change'));let filteredCount=document.querySelectorAll('#loadings tbody tr').length;
    tab=tabNames[3];render();let reconciliation=D.contributions.filter(r=>r.model==='E2').reduce((a,r)=>a+r.value,0)-D.nowcast.models.find(r=>r.model==='E2').prediction;
    tab=tabNames[4];render();let chartCount=document.querySelectorAll('svg').length;tab=tabNames[1];render();let factorChartCount=document.querySelectorAll('svg').length;let summary=document.querySelector('summary');summary.click();let distributionOpened=summary.parentElement.open;
    let sortedTables=0;for(const name of tabNames){tab=name;render();for(const t of [...document.querySelectorAll('table')]){const header=t.querySelector('th');header.click();sortedTables++;}}
    tab=tabNames[0];render();let blankAssets=performance.getEntriesByType('resource').filter(e=>!e.name.startsWith('file:'));let marker=document.createElement('div');marker.id='browser-test';marker.textContent=JSON.stringify({checks,inventoryCount,searchCount,sortedFirst,loadingCount,filteredCount,reconciliation,chartCount,factorChartCount,distributionOpened,sortedTables,errors:failures,externalResources:blankAssets.length,modelOptions:$('model').options.length});document.body.appendChild(marker);
    </script>'''
    page=OUT/'phase7e_browser_test.html'
    page.write_text(original.replace('</body>',test+'</body>'),encoding='utf8')
    edge=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    if not edge.is_file(): raise RuntimeError('Edge unavailable: cannot claim browser validation')
    profile=OUT/('tmp_edge_'+uuid.uuid4().hex[:8])
    result=subprocess.run([str(edge),'--headless=new','--disable-gpu','--disable-background-networking','--no-first-run',
        '--user-data-dir='+str(profile),'--window-size=1440,1300','--virtual-time-budget=5000',
        '--screenshot='+str(OUT/'phase7e_dashboard_preview.png'),'--dump-dom',page.as_uri()],capture_output=True,timeout=60)
    (OUT/'phase7e_browser.log').write_bytes(result.stderr)
    dom=result.stdout.decode('utf8',errors='replace')
    match=re.search(r'<div id="browser-test">(.*?)</div>',dom,re.S)
    report=json.loads(html.unescape(match.group(1))) if match else dict(error='No browser-test marker')
    report['exit_code']=result.returncode
    report['tested_dashboard_sha256']=hashlib.sha256((OUT/'phase7e_economic_dfm_dashboard.html').read_bytes()).hexdigest()
    report['passed']=bool(result.returncode==0 and report.get('inventoryCount')==96 and report.get('loadingCount')==91
        and report.get('filteredCount')==29 and report.get('searchCount')==expected_cpi and report.get('modelOptions')==5
        and abs(report.get('reconciliation',1))<1e-10 and report.get('chartCount',0)>=2
        and report.get('factorChartCount',0)>=5 and report.get('distributionOpened') and report.get('sortedTables',0)>=10
        and report.get('externalResources')==0 and not report.get('errors',[])
        and len(report.get('checks',[]))==52 and all(c['nonempty'] for c in report['checks']))
    (OUT/'phase7e_browser_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    if not report['passed']: raise RuntimeError('Offline browser functionality failed: '+json.dumps(report))
    return report


if __name__=='__main__': print(json.dumps({k:v for k,v in check().items() if k!='checks'},indent=2))
