"""Rebuild presentation from exact saved results without fitting or input writes."""
import json
import pandas as pd
from scripts.phase7d.run import ROOT, OUT, sha, write_json
from scripts.phase7d.data import read_workbook
from scripts.phase7d.report import report


def main():
    manifest=json.loads((OUT/'phase7d_run_manifest.json').read_text(encoding='utf8'))
    if not manifest['protected_artifacts_verified']:
        raise ValueError('Presentation finalization requires successful protection verification')
    digest=manifest['workbook_sha256'];workbook=OUT/'input'/f'{digest}.xlsx'
    if sha(workbook)!=digest:raise ValueError('Archived workbook changed')
    inputs=read_workbook(workbook,ROOT/'data/master/gdp_quarterly.parquet')
    inputs.inventory=pd.read_csv(OUT/'phase7d_predictor_inventory.csv',float_precision='round_trip')
    names=['model_metrics','horizon_metrics','forecasts','factor_signals','factor_loadings',
           'signal_contributions','origin_availability','robustness']
    frames=[pd.read_csv(OUT/f'phase7d_{n}.csv',float_precision='round_trip') for n in names]
    nowcast=json.loads((OUT/'phase7d_current_nowcast.json').read_text(encoding='utf8'))
    frozen=pd.read_csv(OUT/'phase7d_frozen_production_metrics.csv',float_precision='round_trip')
    report(inputs,*frames,nowcast,manifest,frozen,OUT)
    manifest['output_sha256']={p.name:sha(p) for p in OUT.glob('phase7d_*') if p.is_file() and p.suffix!='.log' and p.name!='phase7d_run_manifest.json'}
    manifest['code_sha256']={p.name:sha(p) for p in (ROOT/'scripts/phase7d').glob('*') if p.is_file()}
    write_json('run_manifest',manifest)
    print('Presentation regenerated from saved results; verified production unchanged')


if __name__=='__main__':main()
