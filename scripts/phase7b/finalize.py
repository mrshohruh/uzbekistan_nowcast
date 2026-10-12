"""Regenerate research reports from completed fits and reverify protected artifacts."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import json,logging
import pandas as pd
from scripts.phase7b.run import ROOT,OUT,DATA,sha
from scripts.phase7b.data import parse,transform
from scripts.phase7b.report import report
from scripts.operations.prospective.common import safe

def finalize():
    logging.basicConfig(level=logging.INFO)
    before=json.loads((OUT/'protection_baseline.json').read_text())
    def changed(item):
        p,h=item;return p if not (ROOT/p).is_file() or sha(ROOT/p)!=h else None
    with ThreadPoolExecutor(max_workers=8) as pool:bad=[p for p in pool.map(changed,before.items()) if p]
    if bad:raise ValueError('Protected files changed: '+str(bad))
    f=parse(DATA/'input/uzbekistan_nightlights_monthly.csv');original=sha(DATA/'input/uzbekistan_nightlights_monthly.csv');archive=DATA/'raw'/original/'uzbekistan_nightlights_monthly.csv'
    if sha(archive)!=original:raise ValueError('Archive mismatch')
    def read(name):return pd.read_csv(OUT/name,float_precision='round_trip')
    historical=read('phase7b_historical_predictions.csv');current=read('phase7b_current_nowcasts.csv');production=json.loads((OUT/'production_reproduction.json').read_text())
    if any(v['error']!=0 for v in production.values()):raise ValueError('Production differs')
    manifest=dict(classification='PHASE7B_SATELLITE_INCONCLUSIVE',provenance='SOURCE_METADATA_UNVERIFIED',satellite_vintages='VINTAGE UNVERIFIED',source_sha256=original,archive=str(archive.relative_to(ROOT)),source_url=None,source_release_date=None,sensor_product=None,measurement_units=None,counts=f.count().to_dict(),protected_artifacts_verified=True,protected_file_count=len(before),protected_hashes=before,production_reproduction=production,forecast_cutoff='2026-10-05',run_timestamp=datetime.now(timezone.utc).isoformat(),n_historical_origins=historical[['origin','target_quarter','horizon']].drop_duplicates().shape[0],GDP_vintage_rule='STRICT unchanged existing vintage kernel',origin_rule='Existing H1/H2/H3; satellite assumed month end + 0/1/2/3 calendar months',production_nowcast=8.180901340616275)
    report(f,transform(f),read('phase7b_model_comparison.csv'),read('phase7b_horizon_metrics.csv'),historical,current,read('phase7b_factor_loadings.csv'),read('phase7b_factor_signals.csv'),read('phase7b_robustness.csv'),manifest)
    for name in ['determinism.json','browser_validation.json']:
        if (OUT/name).exists():manifest[name.removesuffix('.json')]=json.loads((OUT/name).read_text())
    if (OUT/'phase7b_tests.xml').exists():
        from xml.etree import ElementTree
        suite=ElementTree.parse(OUT/'phase7b_tests.xml').getroot().find('testsuite');manifest['tests']=dict(suite.attrib)
    manifest['source_code_sha256']={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'scripts/phase7b').glob('*.py')}
    manifest['output_sha256']={p.name:sha(p) for p in OUT.glob('*') if p.is_file() and p.name not in ['run_manifest.json','pipeline.log','terminal_summary.txt']}
    (OUT/'run_manifest.json').write_text(json.dumps(safe(manifest),indent=2,allow_nan=False),encoding='utf8')
    metadata=archive.parent/'provenance.json'
    if not metadata.exists():
        with metadata.open('x',encoding='utf8') as h:json.dump(dict(source_sha256=original,original_path=str(DATA/'input/uzbekistan_nightlights_monthly.csv'),provenance_status='SOURCE_METADATA_UNVERIFIED',source_url=None,source_release_date=None,provenance_recorded_at=manifest['run_timestamp']),h,indent=2)
    print(manifest['classification']);print('Protected files unchanged:',len(before));print(OUT/'phase7b_satellite_comparison.html');print(OUT/'phase7b_results.md')
if __name__=='__main__':finalize()
