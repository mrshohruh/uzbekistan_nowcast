"""Render the offline dashboard and exercise every tab and selector."""
from pathlib import Path
import subprocess,json,re,html,uuid
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/phase7c'

def main():
    text=(OUT/'phase7c_economic_coverage_dashboard.html').read_text(encoding='utf8')
    test='''<script>let checks=[];for(const [label,key] of Object.entries(tabs)){active=key;render();checks.push({tab:key,nonempty:document.getElementById('content').textContent.length>0});}document.getElementById('candidate').value='R1';document.getElementById('horizon').value='H2';active='historical_predictions';render();let e=document.createElement('div');e.id='browser-test';e.textContent=JSON.stringify({checks,candidate:document.getElementById('candidate').value,horizon:document.getElementById('horizon').value,svg_count:document.querySelectorAll('svg').length,table:document.getElementById('content').textContent.includes('R1')});document.body.appendChild(e);</script>'''
    page=OUT/'browser_test.html';page.write_text(text.replace('</html>',test+'</html>'),encoding='utf8')
    edge=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    args=[str(edge),'--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--user-data-dir='+str(OUT/('tmp_edge_'+uuid.uuid4().hex[:8])),'--window-size=1440,1600','--virtual-time-budget=3000','--screenshot='+str(OUT/'dashboard_preview.png'),'--dump-dom',page.as_uri()]
    r=subprocess.run(args,capture_output=True,timeout=50)
    (OUT/'browser.log').write_bytes(r.stderr)
    m=re.search(r'<div id="browser-test">(.*?)</div>',r.stdout.decode('utf8',errors='replace'),re.S)
    result=json.loads(html.unescape(m.group(1))) if m else {}
    result['exit_code']=r.returncode
    result['passed']=r.returncode==0 and result.get('svg_count',0)>0 and result.get('table',False) and all(x['nonempty'] for x in result.get('checks',[]))
    (OUT/'browser_validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    if not result['passed']:raise ValueError('Offline dashboard rendering failed')
if __name__=='__main__':main()
