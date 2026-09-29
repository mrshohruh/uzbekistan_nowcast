"""Verify that the last successful pilot can be replayed from immutable raw archives."""
from pathlib import Path
import hashlib
import json
import logging
import pandas as pd

from uznowcast.pipeline import build
from uznowcast.provenance import save_json, utc_now


def main():
    root = Path.cwd()
    manifest = json.loads((root / 'data/master/build_manifest.json').read_text(encoding='utf-8'))
    scope = 'pilot8' if manifest['scope'] == 'Phase 2B' else 'pilot'
    keys = (('gdp_real_yoy', 'industrial_production', 'construction', 'cpi_headline',
             'exports_total', 'imports_total', 'usd_uzs', 'm2', 'usd_uzs_daily')
            if scope == 'pilot8' else
            ('gdp_real_yoy', 'industrial_production', 'usd_uzs', 'usd_uzs_daily'))
    paths = [root / f'data/processed/{key}.parquet' for key in
             keys]
    monthly_name = 'pilot8_monthly' if scope == 'pilot8' else 'pilot_monthly'
    paths += [root / f'data/master/{name}.{suffix}' for name in (monthly_name, 'gdp_quarterly')
              for suffix in ('parquet', 'xlsx')]

    def read(path):
        return pd.read_parquet(path) if path.suffix == '.parquet' else pd.read_excel(path)

    before = {path: read(path) for path in paths}
    observations = pd.read_parquet(root / 'metadata/observations_long.parquet')
    raw = {path: hashlib.sha256(path.read_bytes()).hexdigest()
           for path in (root / 'data/raw').rglob('*') if path.is_file()}
    report = build(root, scope=scope, offline=True, fx_start=manifest['fx_request_range']['start'],
                   fx_end=manifest['fx_request_range']['end'])
    if report['status'] == 'failed':
        raise RuntimeError(f'Offline replay failed: {report["failures"]}')
    for path, frame in before.items():
        pd.testing.assert_frame_equal(frame, read(path), check_exact=True)
    pd.testing.assert_frame_equal(observations, pd.read_parquet(root / 'metadata/observations_long.parquet'), check_exact=True)
    raw_after = {path: hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in (root / 'data/raw').rglob('*') if path.is_file()}
    if raw != raw_after:
        raise AssertionError('Offline replay changed the raw archive')
    if manifest['registry_sha256'] != report['registry_sha256']:
        raise AssertionError('Registry changed between builds')
    result = dict(status='passed', verified_at=utc_now(), original_run_id=manifest['run_id'],
                  replay_run_id=report['run_id'], scope=scope,
                  verified_artifacts=[p.relative_to(root).as_posix() for p in paths],
                  raw_files_unchanged=len(raw), observation_vintages_unchanged=len(observations),
                  registry_sha256=report['registry_sha256'])
    save_json(root / 'metadata/replay_verification.json', result)
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logging.getLogger('uznowcast.verification').info(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
