"""Build a Phase 4A-runnable master set from the frozen Phase 2B fixtures.

This script exists solely because raw data payloads are gitignored: a fresh
checkout has no ``data/raw/`` cache from which the standard
``python -m uznowcast.cli build --scope pilot8`` command could reproduce the
V1.2 masters without a live network.

The frozen fixtures under ``tests/fixtures/`` cover 6 real SIAT/CBU
variables (GDP, industrial production, construction, headline CPI, exports,
imports, M2). This script reuses the production parsers and transforms to
produce ``v1_monthly.parquet`` and ``gdp_quarterly.parquet`` in the target
directory. The result is a **strict subset** of a full V1.2 build — Tier A
is thin because USD/UZS/RUB/UZS/gold_price/fx_reserves have no fixtures —
so the phase4a results table this rehearsal produces is labelled as such.

When the operator later runs ``python -m uznowcast.cli build --scope v1``
against live sources, the same Phase 4A evaluator produces the full-panel
result over the exact same code paths.

USAGE
-----

    python scripts/build_master_from_fixtures.py \\
        --output data/master_from_fixtures

The output directory can then be passed to the modelling CLI via
``--master-dir``. The command never writes into ``data/master/``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import openpyxl
import pandas as pd

from uznowcast.registry import load_registry
from uznowcast.parsers.siat import parse_siat
from uznowcast.parsers.cbu import parse_m2_xlsx
from uznowcast.transforms.decumulate import decumulate_ytd
from uznowcast.transforms.growth import gdp_target, log_growth
from uznowcast.transforms.prices import monthly_index_log


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / 'registry/uzbekistan_nowcasting_v1.1_registry.xlsx'


def _load_json(name: str):
    with (ROOT / f'tests/fixtures/{name}.json').open() as file:
        return json.load(file)


def _fixture_frame(key: str, registry_row: dict, contract: dict) -> pd.DataFrame:
    payload = _load_json(key)
    parsed = parse_siat(payload, registry_row, contract)
    parsed['variable_key'] = key
    return parsed


def _apply_transforms(key: str, frame: pd.DataFrame, registry_row: dict) -> pd.DataFrame:
    codes = registry_row['rule_codes']
    if codes == ['GDP_TARGET']:
        return gdp_target(frame)
    if codes == ['DECUM_YTD', 'FLOW_YOY_LOG']:
        result = decumulate_ytd(frame, 3.0)
        return log_growth(result, 'monthly_flow', 12, 50.0)
    if codes == ['MOM_INDEX_LOG']:
        return monthly_index_log(frame)
    raise ValueError(f'Unhandled rule for fixture-based build: {codes}')


def _load_m2(registry_row: dict, contract: dict) -> pd.DataFrame:
    with (ROOT / 'tests/fixtures/m2.xlsx').open('rb') as file:
        content = file.read()
    parsed = parse_m2_xlsx(content, registry_row, contract)
    parsed['variable_key'] = 'm2'
    return log_growth(parsed, 'raw_value', 12, 50.0)


def build_master(output: Path) -> dict:
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    registry = load_registry(REGISTRY_PATH)
    contracts = json.loads((ROOT / 'config/siat_contracts.json').read_text())
    cbu_contracts = json.loads((ROOT / 'config/cbu_contracts.json').read_text())
    series = {}
    siat_keys = ['gdp_real_yoy', 'industrial_production', 'construction',
                 'cpi_headline', 'exports_total', 'imports_total']
    for key in siat_keys:
        raw = _fixture_frame(key, registry.rows[key], contracts[key])
        series[key] = _apply_transforms(key, raw, registry.rows[key])
    series['m2'] = _load_m2(registry.rows['m2'], cbu_contracts['m2'])

    monthly = _assemble_monthly(series, registry)
    quarterly = _assemble_quarterly(series['gdp_real_yoy'],
                                    registry.rows['gdp_real_yoy']['clean_model_field'])
    monthly.to_parquet(output / 'v1_monthly.parquet', index=False)
    quarterly.to_parquet(output / 'gdp_quarterly.parquet', index=False)
    return dict(
        monthly_rows=int(len(monthly)),
        quarterly_rows=int(len(quarterly)),
        monthly_columns=[c for c in monthly.columns if c != 'date'],
        output_dir=str(output),
    )


def _assemble_monthly(series: dict, registry) -> pd.DataFrame:
    inputs = []
    for row in registry.scope('v1'):
        if row['native_frequency'] == 'Quarterly':
            continue
        key = row['variable_key']
        if key not in series:
            continue
        frame = series[key]
        if set(frame.frequency) != {'M'}:
            continue
        index = pd.PeriodIndex(frame.reference_date, freq='M')
        inputs.append(pd.Series(frame.clean_value.to_numpy(dtype=float), index=index,
                                name=row['clean_model_field']))
    if not inputs:
        raise ValueError('No monthly predictors were built from fixtures')
    joined = pd.concat(inputs, axis=1).sort_index()
    joined = joined.reindex(pd.period_range(joined.index.min(), joined.index.max(), freq='M'))
    joined.index = joined.index.to_timestamp(how='end').normalize()
    return joined.rename_axis('date').reset_index()


def _assemble_quarterly(gdp_frame: pd.DataFrame, field: str) -> pd.DataFrame:
    columns = ['reference_period', 'clean_value']
    result = gdp_frame[columns].sort_values('reference_period').copy()
    result = result.rename(columns={'reference_period': 'quarter', 'clean_value': field})
    return result.reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/master_from_fixtures')
    args = parser.parse_args()
    summary = build_master(args.output)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
