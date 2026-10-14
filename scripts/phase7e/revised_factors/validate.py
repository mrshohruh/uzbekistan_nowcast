"""Run regression tests, complete numerical replay and offline Edge controls."""
from pathlib import Path
import contextlib
import html
import json
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

import pytest
from _pytest.tmpdir import TempPathFactory

from scripts.phase7e.protection import sha, verify

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'results/phase7e/revised_factors'


def browser_check():
    source = (OUT/'revised_phase7e_dashboard.html').read_text(encoding='utf8')
    test = r'''<script>
    let checks=[],errors=[];window.addEventListener('error',e=>errors.push(e.message));
    for(const m of D.models)for(const v of ['ORIGINAL','REVISED']){ $('model').value=m;$('version').value=v;for(const t of tabNames){tab=t;render();checks.push({model:m,version:v,tab:t,nonempty:$('content').textContent.length>60});}}
    tab='Comparison';for(const s of ['MATCHED_ALL','MATCHED_DEVELOPMENT','MATCHED_HOLDOUT'])for(const h of ['ALL','H1','H2','H3']){$('sample').value=s;$('sample').dispatchEvent(new Event('change'));$('horizon').value=h;$('horizon').dispatchEvent(new Event('change'));checks.push({sample:s,horizon:h,rows:document.querySelectorAll('#comparison tbody tr').length,nonempty:document.querySelectorAll('#comparison tbody tr').length===5});}
    $('model').value='E2';$('version').value='REVISED';$('sample').value='MATCHED_HOLDOUT';$('horizon').value='ALL';tab='Factor composition';factor='ALL';query='';render();let full=document.querySelectorAll('#composition tbody tr').length,excluded=document.querySelectorAll('#excluded tbody tr').length;$('factor-filter').value='F1';$('factor-filter').dispatchEvent(new Event('change'));let industry=document.querySelectorAll('#composition tbody tr').length;
    factor='ALL';render();$('search').value='CPI';$('search').dispatchEvent(new Event('input'));let searchCount=document.querySelectorAll('#composition tbody tr').length;let expectedCpi=D.compositions.filter(r=>r.revised_factor_included&&r.original_label.includes('CPI')).length;
    query='';$('model').value='ECONOMIC_CORE';render();let core=document.querySelectorAll('#composition tbody tr').length;let corePrices=[...document.querySelectorAll('#composition tbody tr')].filter(r=>r.textContent.includes('CPI')||r.textContent.includes('PPI')).length;
    $('model').value='E2';tab='Historical forecasts';render();let historyRows=document.querySelectorAll('#history tbody tr').length,historyCharts=document.querySelectorAll('svg').length;
    tab='GDP contributions';render();let now=D.nowcasts.find(r=>r.model==='E2').revised_prediction;let reconciliation=D.contributions.filter(r=>r.model==='E2'&&r.specification==='REVISED').reduce((a,r)=>a+r.value,0)-now;
    let sorts=0;for(const t of tabNames){tab=t;render();const th=$('content').querySelector('th');if(th){th.click();sorts++;}}
    tab='Comparison';render();let external=performance.getEntriesByType('resource').filter(e=>!e.name.startsWith('file:')).length;let marker=document.createElement('div');marker.id='browser-test';marker.textContent=JSON.stringify({checks,full,excluded,industry,core,corePrices,searchCount,expectedCpi,historyRows,historyCharts,reconciliation,sorts,external,errors});document.body.appendChild(marker);
    </script>'''
    page=OUT/'browser_test.html';page.write_text(source.replace('</body>',test+'</body>'),encoding='utf8')
    edge=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    if not edge.exists():
        return dict(passed=False,error='Edge unavailable; browser validation not executed')
    result=subprocess.run([str(edge),'--headless=new','--disable-gpu','--disable-background-networking','--no-first-run',
        '--user-data-dir='+str(OUT/('tmp_edge_'+uuid.uuid4().hex[:8])),'--window-size=1440,1400',
        '--virtual-time-budget=5000','--screenshot='+str(OUT/'dashboard_preview.png'),'--dump-dom',page.as_uri()],
        capture_output=True,timeout=60)
    (OUT/'browser.log').write_bytes(result.stderr)
    dom=result.stdout.decode('utf8',errors='replace')
    match=re.search(r'<div id="browser-test">(.*?)</div>',dom,re.S)
    report=json.loads(html.unescape(match.group(1))) if match else dict(error='Browser emitted no validation marker')
    report['exit_code']=result.returncode
    report['dashboard_sha256']=sha(OUT/'revised_phase7e_dashboard.html')
    report['passed']=bool(result.returncode==0 and report.get('full')==88 and report.get('excluded')==3
        and report.get('industry')==28 and report.get('core')==15 and report.get('corePrices')==0
        and report.get('searchCount')==report.get('expectedCpi') and report.get('searchCount',0)>0
        and report.get('historyRows')==12 and report.get('historyCharts')==1
        and abs(report.get('reconciliation',1))<1e-10 and report.get('sorts')==7
        and report.get('external')==0 and not report.get('errors')
        and len(report.get('checks',[]))==82 and all(r['nonempty'] for r in report['checks']))
    (OUT/'revised_phase7e_browser_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return report


def main():
    baseline=json.loads((OUT/'revised_phase7e_protection_baseline.json').read_text())
    hashes={p.name:sha(p) for p in OUT.glob('revised_phase7e_*.csv')}
    dashboard=sha(OUT/'revised_phase7e_dashboard.html')
    with (OUT/'reproducibility.log').open('w',encoding='utf8') as log:
        replay=subprocess.run([sys.executable,'-B','-m','scripts.phase7e.revised_factors.run'],cwd=ROOT,stdout=log,stderr=log)
    changes=[n for n,h in hashes.items() if not (OUT/n).exists() or sha(OUT/n)!=h]
    deterministic=bool(replay.returncode==0 and not changes and sha(OUT/'revised_phase7e_dashboard.html')==dashboard)
    # Keep staged snapshot filenames below legacy Windows CopyFile2 limits.
    temp=OUT/'t';temp.mkdir(exist_ok=True)
    # Windows pytest ACL handling follows the existing Phase 7E validator.
    def base(self):
        self._basetemp=temp
        return temp
    def mktemp(self,basename,numbered=True):
        p=temp/uuid.uuid4().hex[:8];p.mkdir();return p
    if sys.platform=='win32':
        TempPathFactory.getbasetemp=base;TempPathFactory.mktemp=mktemp
    with (OUT/'tests.log').open('w',encoding='utf8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        code=pytest.main(['tests','scripts/phase7e/test_research.py','scripts/phase7e/revised_factors/test_revised.py',
            '-q','-p','no:cacheprovider','--junitxml',str(OUT/'tests.xml')])
    suites=ET.parse(OUT/'tests.xml').getroot().findall('testsuite')
    tests={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
    tests['passed']=tests['tests']-tests['failures']-tests['errors']-tests['skipped'];tests['exit_code']=int(code)
    try:
        browser=browser_check()
    except Exception as exc:
        browser=dict(passed=False,error=str(exc))
    count=verify(baseline)
    validation=dict(protected_artifacts_verified=True,protected_file_count=count,original_outputs_preserved=True,
        production_preserved=True,production_forecast=8.180901340616275,authentic_real_time_validated=False,
        tests=tests,tests_status='PASSED' if code==0 else 'FAILED',browser_status='PASSED' if browser.get('passed') else 'FAILED',
        browser=browser,determinism=dict(passed=deterministic,full_pipeline_replay=True,replay_exit_code=replay.returncode,
            changed_csv_files=changes,dashboard_byte_identical=sha(OUT/'revised_phase7e_dashboard.html')==dashboard),
        passed=bool(code==0 and browser.get('passed') and deterministic))
    (OUT/'revised_phase7e_validation.json').write_text(json.dumps(validation,indent=2),encoding='utf8')
    with (OUT/'revised_phase7e_results.md').open('a',encoding='utf8') as report:
        report.write('\n## Executed validation\n\n'+f"{tests['passed']} tests passed; {tests['failures']} failures, {tests['errors']} errors, {tests['skipped']} skips. "
            +f"Complete numerical replay: {'passed' if deterministic else 'failed'}. Offline Edge browser controls: {'passed' if browser.get('passed') else 'failed'}. "
            +f"All {count:,} protected prior files verified unchanged. Predictor historical vintage verification remains unavailable.\n")
    print(json.dumps({k:v for k,v in validation.items() if k!='browser'},indent=2))
    raise SystemExit(0 if validation['passed'] else 1)


if __name__=='__main__':
    main()
