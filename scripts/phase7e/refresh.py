"""Re-render reports from exact round-trip CSVs; never refit or change inputs."""
import json
import pandas as pd
from scripts.phase7d.data import read_workbook
from scripts.phase7e.protection import ROOT
from scripts.phase7e.report import report

OUT=ROOT/'results/phase7e'


def refresh():
    def frame(name): return pd.read_csv(OUT/f'phase7e_{name}.csv',float_precision='round_trip')
    manifest=json.loads((OUT/'phase7e_run_manifest.json').read_text())
    inputs=read_workbook(ROOT/'results/phase7d/input'/f"{manifest['workbook_sha256']}.xlsx",ROOT/'data/master/gdp_quarterly.parquet')
    nowcast=json.loads((OUT/'phase7e_current_nowcast.json').read_text())
    report(inputs,frame('variable_grouping'),frame('model_comparison'),frame('horizon_metrics'),frame('forecasts'),
        frame('factor_timeseries'),frame('factor_loadings'),frame('gdp_contributions'),frame('estimation_diagnostics'),
        frame('earliest_availability'),frame('robustness'),nowcast,OUT)


if __name__=='__main__': refresh()
