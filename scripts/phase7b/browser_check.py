"""Headless offline dashboard rendering and selector smoke test."""
from pathlib import Path
import subprocess,json,re
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/phase7b'
def main():
    text=(OUT/'phase7b_satellite_comparison.html').read_text(encoding='utf8')
    test='''<script>document.getElementById('model').value='S3';document.getElementById('horizon').value='H2';document.getElementById('scenario').value='ASSUMED_LAG_3M';document.getElementById('model').dispatchEvent(new Event('change'));let e=document.createElement('div');e.id='browser-test';e.textContent=JSON.stringify({model:document.getElementById('model').value,horizon:document.getElementById('horizon').value,scenario:document.getElementById('scenario').value,svg_count:document.querySelectorAll('svg').length,current_contains_S3:document.getElementById('current').textContent.includes('S3'),comparison_contains_S3:document.getElementById('comparison').textContent.includes('S3')});document.body.appendChild(e);</script>'''
    page=ROOT/'.tmp/phase7b_browser_test.html';page.write_text(text.replace('</html>',test+'</html>'),encoding='utf8')
    args=['C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe','--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--user-data-dir='+str(ROOT/'.tmp/phase7b_edge4'),'--window-size=1440,1600','--virtual-time-budget=3000','--screenshot='+str(OUT/'dashboard_preview.png'),'--dump-dom',page.as_uri()]
    r=subprocess.run(args,capture_output=True,timeout=45)
    (OUT/'browser_dom.html').write_bytes(r.stdout);(OUT/'browser.log').write_bytes(r.stderr)
    match=re.search(r'<div id="browser-test">(.*?)</div>',r.stdout.decode('utf8',errors='replace'),re.S)
    result=json.loads(match.group(1)) if match else {}
    result.update(exit_code=r.returncode,screenshot=(OUT/'dashboard_preview.png').exists())
    result['passed']=r.returncode==0 and result.get('model')=='S3' and result.get('horizon')=='H2' and result.get('scenario')=='ASSUMED_LAG_3M' and result.get('svg_count',0)>=8 and result.get('current_contains_S3') and result.get('comparison_contains_S3')
    (OUT/'browser_validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    if not result['passed']:raise ValueError('Dashboard browser validation failed')
if __name__=='__main__':main()
