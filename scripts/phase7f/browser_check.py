"""Render and exercise every offline diagnostic panel/sample/tab in Edge."""
from pathlib import Path
import html
import json
import re
import subprocess
import uuid
from scripts.phase7f.protection import ROOT,OUT,sha


def check():
    page=OUT/'phase7f_factor_selection_dashboard.html'
    original=page.read_text(encoding='utf8')
    test=r'''<script>
    let checks=[],errors=[];window.addEventListener('error',e=>errors.push(e.message));
    for(const model of D.models)for(const sample of D.samples){$('model').value=model;$('sample').value=sample;$('sample').dispatchEvent(new Event('change'));for(const name of tabs){document.querySelector(`[data-tab="${name}"]`).click();checks.push({model,sample,tab:name,nonempty:$('content').textContent.length>60});}}
    $('model').value='E2';$('sample').value='ORIGINAL_COMPLETE';$('sample').dispatchEvent(new Event('change'));tab=tabs[1];render();let criterionCharts=document.querySelectorAll('svg').length;tab=tabs[2];render();let spectrumCharts=document.querySelectorAll('svg').length;
    tab=tabs[4];factorLimit=row().k_max;render();let originalLoads=document.querySelectorAll('#loadings tbody tr').length;$('search').value='CPI';$('search').dispatchEvent(new Event('input'));let searchLoads=document.querySelectorAll('#loadings tbody tr').length;$('factor-limit').value='2';$('factor-limit').dispatchEvent(new Event('change'));let twoPCLoads=document.querySelectorAll('#loadings tbody tr').length;let heatmapCells=document.querySelectorAll('.heatmap rect').length;
    query='';let sortedTables=0;for(const name of tabs){tab=name;render();for(const t of [...document.querySelectorAll('table')]){t.querySelector('th').click();sortedTables++;}}
    $('sample').value='COMMON_STRICT';tab=tabs[0];render();let unavailableWarning=$('content').textContent.includes('Unavailable sample');$('sample').value='ORIGINAL_COMPLETE';tab=tabs[0];render();
    let marker=document.createElement('div');marker.id='browser-test';marker.textContent=JSON.stringify({checks,criterionCharts,spectrumCharts,originalLoads,searchLoads,twoPCLoads,heatmapCells,sortedTables,unavailableWarning,errors,externalResources:performance.getEntriesByType('resource').filter(r=>!r.name.startsWith('file:')).length});document.body.appendChild(marker);
    </script>'''
    test_page=OUT/'phase7f_browser_test.html';test_page.write_text(original.replace('</body>',test+'</body>'),encoding='utf8',newline='\n')
    edge=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    if not edge.is_file():raise RuntimeError('Edge is not installed; cannot claim rendering passed')
    profile=OUT/('tmp_edge_'+uuid.uuid4().hex[:8])
    result=subprocess.run([str(edge),'--headless=new','--disable-gpu','--disable-background-networking','--no-first-run',
        '--user-data-dir='+str(profile),'--window-size=1440,1300','--virtual-time-budget=6000',
        '--screenshot='+str(OUT/'phase7f_dashboard_preview.png'),'--dump-dom',test_page.as_uri()],capture_output=True,timeout=60)
    (OUT/'phase7f_browser.log').write_bytes(result.stderr)
    match=re.search(r'<div id="browser-test">(.*?)</div>',result.stdout.decode('utf8',errors='replace'),re.S)
    report=json.loads(html.unescape(match.group(1))) if match else dict(error='No browser marker')
    report.update(exit_code=result.returncode,tested_dashboard_sha256=sha(page))
    report['passed']=bool(result.returncode==0 and len(report.get('checks',[]))==18*6*7
        and all(c['nonempty'] for c in report.get('checks',[])) and report.get('criterionCharts')==3
        and report.get('spectrumCharts')==4 and report.get('originalLoads')==91*10
        and report.get('searchLoads',0)>0 and report.get('twoPCLoads',0)==report.get('heatmapCells',-1)
        and report.get('twoPCLoads',0)<report.get('searchLoads',0) and report.get('sortedTables',0)==9
        and report.get('unavailableWarning') and report.get('externalResources')==0 and not report.get('errors',[]))
    (OUT/'phase7f_browser_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    if not report['passed']:raise RuntimeError('Offline dashboard test failed: '+json.dumps({k:v for k,v in report.items() if k!='checks'}))
    return report


if __name__=='__main__':print(json.dumps({k:v for k,v in check().items() if k!='checks'},indent=2))
