"""Exercise every local-dashboard model, tab, horizon, sort and search in Edge."""
from pathlib import Path
import html
import json
import re
import subprocess
import uuid

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/phase7d'


def main():
    original=(OUT/'phase7d_dfm_dashboard.html').read_text(encoding='utf8')
    test="""<script>
    let checks=[],failures=[];window.addEventListener('error',e=>failures.push(e.message));
    for(const model of D.models){$('model').value=model;for(const name of tabNames){tab=name;render();checks.push({model,tab:name,nonempty:$('content').textContent.length>40});}}
    for(const sample of ['MATCHED_ALL','MATCHED_DEVELOPMENT','MATCHED_HOLDOUT'])for(const horizon of ['ALL','H1','H2','H3']){$('sample').value=sample;$('horizon').value=horizon;tab='Overview';render();checks.push({sample,horizon,metric_count:D.models.map(m=>metric(m)).length,kpis:document.querySelectorAll('.card').length===7});}
    $('model').value=D.nowcast.model;$('sample').value='MATCHED_ALL';$('horizon').value='ALL';tab='96 predictors';render();let fullInventory=document.querySelectorAll('#inventory tbody tr').length;let search=$('inventory-search');search.value='PPI';search.dispatchEvent(new Event('input'));let searchCount=document.querySelectorAll('#inventory tbody tr').length;window.invQuery='';tab='Transformation audit';window.auditLimit=10000;render();let auditCount=document.querySelectorAll('#audit tbody tr').length;tab='Overview';render();document.querySelector('#comparison th[data-key="rmse"]').click();let firstModel=document.querySelector('#comparison tbody tr td').textContent;tab='GDP & errors';render();let svgCount=document.querySelectorAll('svg').length;
    let marker=document.createElement('div');marker.id='browser-test';marker.textContent=JSON.stringify({checks,fullInventory,searchCount,auditCount,firstModel,svgCount,errors:failures,modelOptions:$('model').options.length,embeddedForecasts:D.forecasts.length});document.body.appendChild(marker);
    </script>"""
    page=OUT/'phase7d_browser_test.html';page.write_text(original.replace('</body>',test+'</body>'),encoding='utf8')
    edge=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    if not edge.is_file():raise RuntimeError('Microsoft Edge not found for browser validation')
    profile=OUT/('tmp_edge_'+uuid.uuid4().hex[:8])
    args=[str(edge),'--headless=new','--disable-gpu','--disable-background-networking',
        '--no-first-run','--user-data-dir='+str(profile),'--window-size=1440,1500',
        '--virtual-time-budget=3000','--screenshot='+str(OUT/'phase7d_dashboard_preview.png'),'--dump-dom',page.as_uri()]
    result=subprocess.run(args,capture_output=True,timeout=60)
    (OUT/'phase7d_browser.log').write_bytes(result.stderr)
    dom=result.stdout.decode('utf8',errors='replace')
    match=re.search(r'<div id="browser-test">(.*?)</div>',dom,re.S)
    report=json.loads(html.unescape(match.group(1))) if match else dict(error='No test marker in rendered DOM')
    report['exit_code']=result.returncode
    report['passed']=bool(result.returncode==0 and report.get('fullInventory')==96 and report.get('modelOptions')==9
        and report.get('searchCount',0)>0 and report.get('auditCount',0)>8000 and report.get('svgCount',0)>=2
        and not report.get('errors',[]) and all(c.get('nonempty',c.get('kpis',False)) for c in report.get('checks',[])))
    (OUT/'phase7d_browser_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
    if not report['passed']:raise RuntimeError('Offline browser interaction validation failed')


if __name__=='__main__':main()
