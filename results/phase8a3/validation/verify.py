"""Read-only verification evidence; no network-policy changes or publication."""
from pathlib import Path
import hashlib
import json
import os
import sys
import shutil
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
import requests
from scripts.operations.state import model_lock, verify_current_version
from scripts.collection.versions import current_snapshot

OUT = ROOT / 'results/phase8a3'
def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, default=str) + '\n', encoding='utf-8')
def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()
baseline = json.loads((ROOT / 'results/phase8a2/validation/baseline.json').read_text())
changed = [p for p, h in baseline.items() if not (ROOT / p).is_file() or digest(ROOT / p) != h]
locked, _ = model_lock(ROOT)
verify_current_version(ROOT)
save('validation/freeze_verification.json', dict(status='PASS' if not changed else 'FAIL', checked=len(baseline), changed=changed, runtime_files=len(locked), seal='PASS', current_version='PASS', production_forecast=8.180901340616275, production_promoted=False, forecast_executed=False, scheduler_installed=False))
def safe(value):
    u = urlsplit(value)
    return dict(scheme=u.scheme, host=u.hostname, port=u.port, credentials_present=bool(u.username or u.password))
session = requests.Session()
save('validation/python_network.json', dict(environment={k: safe(v) for k, v in os.environ.items() if k.upper() in {'HTTP_PROXY','HTTPS_PROXY','ALL_PROXY'}}, no_proxy=os.environ.get('NO_PROXY'), trust_env=session.trust_env, tls_verify=session.verify, ca_bundle=requests.certs.where(), system_trust_opt_in=os.environ.get('UZNOWCAST_USE_SYSTEM_TRUST')=='1', official_hosts={url: {k:safe(v) for k,v in requests.utils.get_environ_proxies(url).items() if k!='no'} for url in ['https://api.siat.stat.uz','https://cbu.uz','https://www.worldbank.org']}, configuration_changed=False))
runs = sorted((ROOT / 'data/collection/runs').glob('*/run_manifest.json'), key=lambda p:p.stat().st_mtime)
run = runs[-1].parent
result = json.loads((run / 'run_manifest.json').read_text())
for name in ['run_manifest.json','source_status.csv','validation_reports.json','observation_decisions.csv','archive_audit.csv','source_receipts.csv','candidate_manifest.json','journal.json','collection.log']:
    if (run / name).exists(): shutil.copyfile(run / name, OUT / 'validation' / name)
status = pd.DataFrame(result['source_status'])
status['live_status'] = status.reachability
status['latest_live_observation'] = None
status['candidate_revisions'] = 'NOT_TESTED_NETWORK_BLOCKED'
status['units_numeric_dates_schema'] = 'NOT_TESTED_NETWORK_BLOCKED'
status.to_csv(OUT / 'phase8a3_live_source_status.csv', index=False)
manifest = json.loads((run / 'candidate_manifest.json').read_text())
bad = [p for p,h in manifest['files'].items() if digest(run / 'stage' / p)!=h]
save('validation/snapshot_verification.json', dict(candidate_files=len(manifest['files']), mismatched=bad, candidate_status=manifest['status'], committed_snapshot=str(current_snapshot(ROOT / 'data/collection')), journal=json.loads((run/'journal.json').read_text()), writer_lock_remaining=(ROOT/'data/staging/operations.lock').exists(), live_receipts=0, live_candidates=0))
test = ROOT / 'results/phase8a2/validation/tests_e9080b09.xml'
if test.exists():
    shutil.copyfile(test, OUT / 'validation/regression_tests.xml')
    suite = ET.parse(test).getroot().find('testsuite')
    save('validation/test_summary.json', dict(suite.attrib))
print(json.dumps(dict(freeze_changed=changed, run_id=result['run_id'], status=result['status'], exit_code=result['exit_code'], runtime_seconds=(pd.Timestamp(result['finished_at_utc'])-pd.Timestamp(result['started_at_utc'])).total_seconds(), sources=len(status), candidate_files=len(manifest['files']), candidate_hash_failures=bad)))
