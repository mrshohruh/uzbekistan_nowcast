"""Registry-grounded read-only audit and protected artifact inventory."""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

BLOCKS = {
    'PRODUCTION': ('industrial_production', 'manufacturing', 'mining', 'electricity_gas'),
    'DOMESTIC_DEMAND': ('retail_trade', 'wholesale_trade', 'construction'),
    'PRICES': ('cpi_headline', 'cpi_food', 'cpi_services', 'ppi'),
    'EXTERNAL': ('exports_total', 'imports_total', 'exports_non_gold', 'gold_exports_proxy', 'gold_price', 'russia_ipi'),
    'FINANCIAL': ('usd_uzs', 'rub_uzs', 'm2', 'fx_reserves_ex_gold'),
    'CREDIT_BANKING': ('household_credit', 'corporate_credit', 'household_deposits', 'corporate_deposits'),
    'PAYMENTS': ('pos_turnover', 'interbank_payments', 'instant_payments'),
}
BLOCK_BY_KEY = {key: block for block, keys in BLOCKS.items() for key in keys}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    result = {}
    roots = ['src', 'scripts', 'config', 'registry', 'results', 'dashboard', 'docs',
             'data/master', 'data/processed', 'metadata', 'data/research/phase6a2']
    for directory in roots:
        for path in (root / directory).rglob('*'):
            relative = path.relative_to(root).as_posix()
            if any(s in relative for s in ['/phase6c/', '__pycache__', '_pytest', 'test_tmp', '_vendor', '.pyc']):
                continue
            if path.is_file():
                result[relative] = sha(path)
    return result


def assert_protected(root, before):
    changed = [p for p, h in before.items() if not (root / p).is_file() or sha(root / p) != h]
    if changed:
        raise AssertionError('Protected artifacts changed: ' + json.dumps(changed))
    return {'protected_files': len(before), 'changed': [], 'protected_artifacts_changed': False}


def build_audit(root, dataset, out, save):
    index = pd.date_range('2019-01-31', '2026-09-30', freq='ME')
    panel = pd.DataFrame(index=index)
    recovered = pd.read_csv(root / 'data/research/phase6a2/cbu_midas_monthly_panel.csv')
    recovered.index = pd.PeriodIndex(recovered.reference_period, freq='M').to_timestamp('M')
    provenance = pd.read_csv(root / 'results/research/phase6a2/phase6a2_provenance.csv')
    approved = {'industrial_production': 'industrial_production', 'retail_trade': 'retail_trade',
                'construction': 'construction', 'imports_total': 'imports_total_monthly_log_yoy',
                'pos_turnover': 'pos_turnover_monthly_log_yoy'}
    source_files = provenance.loc[provenance.selected_for_panel.eq(True) & provenance.variable_key.isin(approved),
                                  ['raw_file_path', 'checksum']].drop_duplicates()
    integrity = []
    for row in source_files.itertuples(index=False):
        path = (root / row.raw_file_path).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('Archived research source outside repository')
        checksum = sha(path) if path.is_file() else None
        integrity.append(dict(raw_file_path=row.raw_file_path, expected_checksum=row.checksum,
                              actual_checksum=checksum, verified=checksum == row.checksum))
    integrity = pd.DataFrame(integrity)
    save('recovered_source_integrity', integrity)
    if integrity.empty or not integrity.verified.all():
        raise ValueError('Approved recovery archive missing or checksum mismatch')
    rows = []
    for record in dataset.registry.scope('v1'):
        key = record['variable_key']
        if key == 'gdp_real_yoy':
            continue
        field = record['clean_model_field']
        series = dataset.monthly[field] if field in dataset.monthly else pd.Series(dtype=float)
        series = pd.to_numeric(series, errors='raise').replace([np.inf, -np.inf], np.nan)
        canonical_start, canonical_end = series.first_valid_index(), series.last_valid_index()
        research_transform = record['required_transformation']
        basis = 'REGISTRY_V1.2_FROZEN_MASTER'
        if key in approved:
            series = pd.to_numeric(recovered[approved[key]], errors='raise').copy()
            if key == 'pos_turnover':
                series = series.where(recovered.pos_turnover_scope_verified.eq(True))
            basis = 'APPROVED_PHASE6A2_RESEARCH_RECOVERY; canonical master/registry unchanged'
            if key in ('industrial_production', 'retail_trade', 'construction'):
                research_transform = 'Published real activity growth percent (index minus 100); same convention as frozen Phase6B; research-only deviation from nominal-flow registry clean field'
        panel[key] = series.reindex(index)
        raw_path = root / 'data/processed' / f'{key}.parquet'
        raw_start = raw_end = None
        if raw_path.exists():
            raw = pd.read_parquet(raw_path)
            if 'reference_date' in raw:
                dates = pd.to_datetime(raw.reference_date, errors='coerce')
                raw_start, raw_end = dates.min(), dates.max()
            elif 'reference_period' in raw:
                dates = pd.to_datetime(raw.reference_period, errors='coerce')
                raw_start, raw_end = dates.min(), dates.max()
        if key in approved:
            raw_field = key + '_raw_level'
            if raw_field in recovered:
                raw_dates = recovered.index[recovered[raw_field].notna()]
                raw_start, raw_end = raw_dates.min(), raw_dates.max()
        dev = panel.loc[:'2025-06-30', key]
        observed = int(dev.count())
        missing = float(dev.isna().mean())
        lag = dataset.release_lag_days.get(key)
        reason = ''
        if observed < 24:
            reason = 'fewer_than_24_pre_holdout_months'
        if lag is None:
            reason = 'no_documented_release_lag'
        if key == 'russia_ipi':
            reason = 'no_validated_stored_Rosstat_observations; approved acquisition previously failed TLS'
        if key in ('exports_non_gold', 'gold_exports_proxy'):
            reason = 'redundant_or_proxy_trade_measure; use_total_exports_only'
        if key in ('cpi_food', 'cpi_services'):
            reason = 'redundant_CPI_subcomponents; retain_headline_and_PPI'
        if key in ('manufacturing', 'mining', 'electricity_gas'):
            reason = 'predeclared_aggregate_industrial_representative; avoid_four_series_production_dominance'
        if key == 'wholesale_trade':
            reason = 'predeclared_retail_representative_for_trade_demand_block'
        eligible = not reason
        provider = record['provider']
        url = record.get('machine_download_url') or record.get('human_source_url')
        if key in approved:
            sources = provenance.loc[provenance.variable_key.eq(key) & provenance.selected_for_panel.eq(True)]
            provider = '; '.join(sorted(sources.provider.dropna().unique()))
            url = '; '.join(sorted(sources.source_url.dropna().unique()))
        rows.append(dict(variable=key, economic_block=BLOCK_BY_KEY[key], source=record['provider'],
                         actual_research_provider=provider, source_url=url,
                         raw_start_date=raw_start, raw_end_date=raw_end,
                         usable_start_date=series.first_valid_index(), usable_end_date=series.last_valid_index(),
                         canonical_usable_start_date=canonical_start, canonical_usable_end_date=canonical_end,
                         release_lag=lag, transformation=research_transform,
                         registry_transformation=record['required_transformation'],
                         clean_model_field=field, frequency='M', missing_share=missing,
                         pre_holdout_observations=observed,
                         eligible_for_long_core=bool(eligible and missing <= .05 and dev.first_valid_index() <= pd.Timestamp('2019-01-31')),
                         eligible_for_ragged_panel=eligible, reason_for_exclusion_if_any=reason,
                         metadata_basis=basis,
                         predictor_vintage_limit='Latest stored values; release-lag pseudo-real-time, not verified historical predictor vintages'))
    audit = pd.DataFrame(rows)
    save('predictor_audit', audit)
    save('data_coverage', audit[['variable', 'raw_start_date', 'raw_end_date', 'usable_start_date', 'usable_end_date',
                                'pre_holdout_observations', 'missing_share']])
    save('block_definition', audit[['variable', 'economic_block', 'eligible_for_long_core', 'eligible_for_ragged_panel',
                                   'reason_for_exclusion_if_any']])
    save('transformations', audit[['variable', 'clean_model_field', 'transformation', 'metadata_basis']])
    save('research_monthly_panel', panel.rename_axis('date').reset_index())
    correlations = panel.loc[:'2025-06-30'].corr(min_periods=24).rename_axis('variable').stack().rename('correlation').reset_index()
    correlations.columns = ['variable', 'other_variable', 'correlation']
    correlations['diagnostic_only'] = True
    save('predictor_correlations', correlations)
    (out / 'phase6c_existing_dfm_audit.md').write_text(
        '# Existing DFM and information-set audit\n\n'
        'The production `src/uznowcast/models/dfm.py` is an approximate EM-PCA model, '
        'with no Kalman transition, one factor by default, training-only scaling and '
        'a quarterly mean factor plus lagged GDP bridge. It is not modified.\n\n'
        'The clean Phase 6B.2 comparison uses the immutable Phase 6B DOMESTIC_3 '
        'state-space kernel: industrial production, construction and retail published growth '
        'from the separately validated CBU research panel; one VAR(1) factor, diagonal '
        'white-noise idiosyncratic errors, training-only scaling, missing-observation Kalman '
        'filtering, no smoothed factors in forecasts. It starts January 2021. '
        'DFM-0 is its saved STRICT Bridge A path; Bridge B remains a separate benchmark.\n\n'
        'Monthly horizons and standard/conservative lags come verbatim from models.data. '
        'GDP uses Phase 6B.2 documented publication events and strict same-day exclusion. '
        'Unresolved GDP value vintages remain excluded; the 46-day Phase 6B.1 fallback '
        'is a date assumption, not evidence for a historical value. No current-master GDP '
        'values are substituted into undocumented vintage gaps.\n\n'
        'Phase 6C uses the frozen registry master plus explicitly identified approved '
        'Phase 6A.2 recoveries. Industrial, retail and construction use published real '
        'growth, consistently with DFM-0, rather than silently calling them nominal '
        'de-cumulated registry flow growth. These research deviations are recorded '
        'per variable; no registry or canonical master is changed. Published industrial '
        'growth begins January 2019, retail January 2020 and construction January 2021. '
        'POS is retained only through its verified December 2024 scope boundary. '
        'Longer history of the identical three-variable domestic panel is still blocked '
        'by construction coverage. DFM-1 therefore changes composition as well as history.\n\n'
        'All predictor coverage and eligibility decisions use data through June 2025. '
        'Sparse banking/payments are not silently backfilled. Exact historical predictor '
        'revision vintages are unavailable, so the study is explicitly release-lag '
        'pseudo-real-time with verified partial GDP vintages, not full real-time evidence.\n', encoding='utf-8')
    return panel, audit
