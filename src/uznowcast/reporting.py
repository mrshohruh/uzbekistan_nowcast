"""Phase 2C database, availability, release-timing, and completion artifacts."""
from __future__ import annotations

from math import ceil
from pathlib import Path
import json

import numpy as np
import pandas as pd

from uznowcast.provenance import atomic_parquet, save_json


LONG_COLUMNS = [
    'variable_key', 'reference_period', 'reference_date', 'frequency', 'raw_value',
    'clean_value', 'raw_unit', 'clean_unit', 'transformation', 'provider', 'source_id',
    'source_url', 'source_release_date', 'retrieved_at', 'vintage_date', 'is_preliminary',
    'revision_status', 'quality_flag', 'raw_file_path', 'checksum_sha256',
]


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return '_No rows._'
    values = frame.fillna('').astype(str)
    header = '| ' + ' | '.join(values.columns) + ' |'
    separator = '| ' + ' | '.join(['---'] * len(values.columns)) + ' |'
    rows = ['| ' + ' | '.join(value.replace('|', '\\|').replace('\n', ' ') for value in row) + ' |'
            for row in values.itertuples(index=False, name=None)]
    return '\n'.join([header, separator, *rows])


def canonical_long(root: Path, registry) -> pd.DataFrame:
    source = root / 'metadata/observations_long.parquet'
    frame = pd.read_parquet(source) if source.exists() else pd.DataFrame()
    if not frame.empty:
        frame = frame.loc[frame.variable_key.isin(registry.rows)].copy()
    if 'checksum' in frame:
        frame = frame.rename(columns={'checksum': 'checksum_sha256'})
    for column in LONG_COLUMNS:
        if column not in frame:
            frame[column] = None
    frame = frame[LONG_COLUMNS]
    identity = ['variable_key', 'reference_period', 'frequency', 'retrieved_at',
                'checksum_sha256']
    if frame.duplicated(identity).any():
        raise ValueError('Canonical long database has duplicate vintage observations')
    atomic_parquet(frame, root / 'data/master/v1_observations_long.parquet')
    return frame


def _missing_periods(frame: pd.DataFrame) -> int:
    if frame.empty or frame.frequency.iloc[0] not in {'M', 'Q'}:
        return 0
    freq = frame.frequency.iloc[0]
    periods = pd.PeriodIndex(frame.reference_date, freq=freq)
    return len(pd.period_range(periods.min(), periods.max(), freq=freq).difference(periods))


def availability(root: Path, registry, series: dict, failures: dict, monthly: pd.DataFrame):
    predictor_rows = [row for row in registry.scope('v1') if row['native_frequency'] != 'Quarterly']
    records = []
    for row in registry.scope('v1'):
        key = row['variable_key']
        frame = series.get(key, pd.DataFrame())
        clean = frame.loc[frame.clean_value.notna()] if not frame.empty and 'clean_value' in frame else pd.DataFrame()
        complete = frame
        if not frame.empty and 'quality_flag' in frame:
            complete = frame.loc[~frame.quality_flag.fillna('').str.contains('partial_month|incomplete', regex=True)]
        warnings = []
        if not frame.empty and 'quality_flag' in frame:
            warnings = sorted({flag for value in frame.quality_flag.fillna('') for flag in value.split(';') if flag})
        records.append(dict(
            variable_key=key,
            variable=row['display_name'],
            first_raw_observation=(str(pd.Timestamp(frame.reference_date.min()).date()) if not frame.empty else None),
            first_usable_transformed_observation=(str(pd.Timestamp(clean.reference_date.min()).date()) if not clean.empty else None),
            last_observation=(str(pd.Timestamp(frame.reference_date.max()).date()) if not frame.empty else None),
            latest_complete_month=(str(pd.Timestamp(complete.reference_date.max()).date()) if not complete.empty else None),
            frequency=row['native_frequency'], missing_periods=_missing_periods(frame),
            observations=len(frame), usable_observations=len(clean),
            current_status='automated' if key in series else 'unresolved',
            warnings='; '.join(warnings + ([failures[key]] if key in failures else [])),
        ))
    detail = pd.DataFrame(records)
    fields = [row['clean_model_field'] for row in predictor_rows]
    values = monthly.set_index('date')[fields]
    for record, row in zip((r for r in records if registry.rows[r['variable_key']]['native_frequency'] != 'Quarterly'), predictor_rows):
        field = row['clean_model_field']
        record['percent_missing_union_panel'] = float(values[field].isna().mean() * 100)
        started = values[field].first_valid_index()
        own = values.loc[started:, field] if started is not None else values[field]
        record['percent_missing_from_own_start'] = float(own.isna().mean() * 100) if len(own) else 100.0
    detail = pd.DataFrame(records)
    atomic_parquet(detail, root / 'metadata/availability_analysis.parquet')

    counts = values.notna().sum(axis=1)
    thresholds = {}
    for percentage in (25, 50, 75, 90):
        required = ceil(len(fields) * percentage / 100)
        qualifying = counts[counts >= required]
        thresholds[str(percentage)] = str(qualifying.index[0].date()) if len(qualifying) else None
    annual = []
    for year, group in counts.groupby(counts.index.year):
        annual.append(dict(year=int(year), peak_predictors=int(group.max()),
                           predictors_at_year_end_or_latest=int(group.iloc[-1])))
    latest_date = counts.index.max()
    latest = values.loc[latest_date]
    short = detail.loc[(detail.frequency != 'Quarterly') & (detail.observations < 36), 'variable_key'].tolist()
    breaks = [key for key, row in registry.rows.items()
              if any(token in str(row['structural_breaks_caveats']).lower()
                     for token in ('break', 'rebas', 'methodolog', 'coverage', 'rollout', 'covid'))]
    summary = dict(
        union_start=str(values.index.min().date()), union_end=str(values.index.max().date()),
        predictors=len(fields), thresholds=thresholds, annual=annual,
        latest_month=str(latest_date.date()), latest_available=int(latest.notna().sum()),
        latest_available_variables=[row['variable_key'] for row in predictor_rows
                                    if pd.notna(latest[row['clean_model_field']])],
        latest_missing_variables=[row['variable_key'] for row in predictor_rows
                                  if pd.isna(latest[row['clean_model_field']])],
        unusually_short_histories=short, structural_break_variables=breaks,
    )
    save_json(root / 'metadata/availability_summary.json', summary)

    display = detail.rename(columns={
        'variable': 'Variable', 'first_raw_observation': 'First raw observation',
        'first_usable_transformed_observation': 'First usable transformed observation',
        'last_observation': 'Last observation', 'frequency': 'Frequency',
        'missing_periods': 'Missing periods', 'current_status': 'Current status', 'warnings': 'Warnings'})
    text = '# V1 availability and ragged-edge analysis\n\n' + _markdown_table(
        display[['Variable', 'First raw observation', 'First usable transformed observation',
                 'Last observation', 'Frequency', 'Missing periods', 'Current status', 'Warnings']])
    text += '\n\n## Coverage thresholds\n\n' + _markdown_table(pd.DataFrame([
        {'Predictor share': f'{key}%', 'First month': value} for key, value in thresholds.items()]))
    text += '\n\n## Predictors available by calendar year\n\n' + _markdown_table(pd.DataFrame(annual))
    text += (f'\n\n## Latest-month ragged edge\n\nLatest union month: {summary["latest_month"]}. '
             f'{summary["latest_available"]} of {len(fields)} predictors have usable transformed values.\n\n'
             f'Available: {", ".join(summary["latest_available_variables"])}.\n\n'
             f'Missing: {", ".join(summary["latest_missing_variables"])}.\n\n'
             f'Unusually short histories (<36 raw observations): {", ".join(short) or "None"}.\n')
    (root / 'docs/v1_availability_analysis.md').write_text(text, encoding='utf-8')
    return detail, summary


def release_audit(root: Path, registry, long: pd.DataFrame) -> pd.DataFrame:
    classifications = {}
    for key, row in registry.rows.items():
        if row['automation_status'] == 'ARCHIVE_SPIDER':
            category = 'archive-date proxy available'
        elif row['provider'] in {'SIAT', 'World Bank Pink Sheet'} or key in {'m2', 'fx_reserves_ex_gold'}:
            category = 'current release/update timestamp only'
        elif row['automation_status'] == 'DERIVED':
            category = 'current release/update timestamp only'
        elif key in {'usd_uzs', 'rub_uzs'}:
            category = 'retrieval timestamp only'
        else:
            category = 'no reliable historical release timing'
        subset = long.loc[long.variable_key == key]
        known = pd.to_datetime(subset.source_release_date, utc=True, errors='coerce') if len(subset) else pd.Series(dtype='datetime64[ns, UTC]')
        classifications[key] = dict(
            variable_key=key, classification=category,
            source_release_dates_observed=int(known.notna().sum()),
            first_observed_release_timestamp=(known.min().isoformat() if known.notna().any() else None),
            latest_observed_release_timestamp=(known.max().isoformat() if known.notna().any() else None),
            evidence=row['lag_basis_release_convention'])
    result = pd.DataFrame(classifications.values())
    atomic_parquet(result, root / 'metadata/release_availability.parquet')
    text = ('# Release metadata audit\n\nHistorical first-release dates are never inferred from '
            'typical registry lags. Archive article update dates remain explicitly classified as proxies.\n\n' +
            _markdown_table(result))
    (root / 'docs/release_metadata_audit.md').write_text(text, encoding='utf-8')
    return result


def ensure_failure_artifacts(root: Path, registry, series: dict, failures: dict):
    columns = [column for column in LONG_COLUMNS if column != 'checksum_sha256'] + ['checksum']
    for key, row in registry.rows.items():
        path = root / f'data/processed/{key}.parquet'
        if key not in series and not path.exists():
            atomic_parquet(pd.DataFrame({column: pd.Series(dtype='object') for column in columns}), path)
            save_json(path.with_suffix('.failure.json'), {
                'variable_key': key, 'status': 'unresolved',
                'failure_reason': failures.get(key, 'no successful observations'),
                'no_observations_fabricated': True,
            })


def phase2c_docs(root: Path, registry, report: dict, detail: pd.DataFrame,
                 availability_summary: dict, release: pd.DataFrame, monthly: pd.DataFrame,
                 long: pd.DataFrame):
    recommendations = [
        ('manufacturing', 'Row / field selector', 'Manufacturing',
         'Live SIAT row is Code=C; Klassifikator_en=Manufacturing industry.',
         'Official SIAT dataset 590 archived in data/raw/siat/manufacturing.',
         'Adopt exact machine selector Code=C; Klassifikator_en=Manufacturing industry.'),
        ('electricity_gas', 'Row / field selector', 'Electricity, gas, steam and air conditioning supply',
         'Live SIAT row is Code=D; Klassifikator_en=Electricity, gas, steam and air conditioning.',
         'Official SIAT dataset 590 archived in data/raw/siat/electricity_gas.',
         'Adopt the exact live code/label selector.'),
        ('retail_trade', 'Raw unit', 'billion UZS', 'Live SIAT metadata says million sums.',
         'Official SIAT dataset 2699 archived in data/raw/siat/retail_trade.',
         'Record source raw unit as million UZS and an explicit 0.001 standardization scale.'),
        ('wholesale_trade', 'Raw unit', 'billion UZS', 'Live SIAT metadata says million sums.',
         'Official SIAT dataset 964 archived in data/raw/siat/wholesale_trade.',
         'Record source raw unit as million UZS and an explicit 0.001 standardization scale.'),
        ('gold_exports_proxy', 'Row / field selector', 'Other goods (gold-dominated residual category)',
         'Live SIAT machine row is Code=9; Klassifikator_en=Other goods.',
         'Official SIAT dataset 3082 archived in data/raw/siat/gold_exports_proxy.',
         'Retain proxy concept but add the exact machine selector.'),
        ('fx_reserves_ex_gold', 'Machine/download URL',
         'https://cbu.uz/upload/open_data/0017/4-009-0017_eng.json',
         'JSON is stale/incomplete; official page resolves complete IR_Uzbekistan_MCD_STA.xlsx through 2026-M08.',
         'Official CBU page and workbook archived in data/raw/cbu/fx_reserves_ex_gold.',
         'Use the official page as resolver for the current XLSX.'),
        ('interbank_payments', 'Raw unit', 'UZS (transaction amount)',
         'Archive tables explicitly publish total amounts in thousand sum.',
         'Official CBU archive articles/files under data/raw/cbu/interbank_payments.',
         'Record thousand UZS as source unit and retain explicit 1e-6 conversion to billion UZS.'),
        ('russia_ipi', 'Source structure', 'Rosstat enterprise_industrial page',
         'rosstat.gov.ru leaf is signed by "Russian Trusted Sub CA" (Russian Federation national PKI); '
         'not in certifi, Mozilla NSS, or Windows ROOT store. UZNOWCAST_USE_SYSTEM_TRUST=1 opt-in uses '
         'the OS store when the operator installs the Russian Trusted Root; fedstat.ru is the only '
         'Rosstat-operated host with a Western-trusted TLS chain but geo-blocks non-RU clients (HTTP 403).',
         'docs/phase2c1_results.md diagnostic; ssl.enum_certificates("ROOT") enumeration; '
         'unverified handshake capture of leaf issuer; Let\'s Encrypt fedstat.ru chain probe.',
         'Either register an operator opt-in for the Russian Trusted Root, or add a fedstat.ru '
         'machine URL executable from a network that can reach it; keep provider = Rosstat.'),
        ('ppi', 'Structural breaks / caveats',
         'Starting from April 2024, the coverage of industrial producer price index (registry paraphrase)',
         'Live SIAT Note reads "since April 2024 the scope of reporting entities has been expanded, price '
         'indices for January, February, March 2024 have been recalculated."',
         'Official SIAT dataset archived in data/raw/siat/ppi.',
         'Update the registry caveat text to match the current source wording verbatim.'),
        ('ppi', 'Period label encoding', '2013-M01 … 2026-M08 (Latin M)',
         "Live SIAT payload mixes Cyrillic 'М' (U+041C) for 2016-M01 through 2020-M12 with Latin 'M' for all other months.",
         'Official SIAT dataset archived in data/raw/siat/ppi; parser normalizes Cyrillic М → Latin M without rewriting archived raw.',
         'Document the mixed-encoding anomaly in the registry Structural breaks column.'),
        ('retail_trade', 'Row / field selector',
         'Republic of Uzbekistan / retail turnover',
         'Live SIAT selector uses "Republic of Uzbekistan / retail trade turnover" (adds the word "trade").',
         'Config diff and SIAT dataset archived in data/raw/siat/retail_trade.',
         'Update registry selector text to match the exact SIAT label.'),
        ('wholesale_trade', 'Row / field selector',
         'Republic of Uzbekistan / wholesale turnover',
         'Live SIAT selector uses "Republic of Uzbekistan / wholesale trade turnover" (adds the word "trade").',
         'Config diff and SIAT dataset archived in data/raw/siat/wholesale_trade.',
         'Update registry selector text to match the exact SIAT label.'),
    ]
    recommendation_frame = pd.DataFrame(recommendations, columns=[
        'Variable', 'Field', 'Current registry value', 'Observed behavior', 'Evidence', 'Recommended change'])
    rec_text = ('# Phase 2C registry recommendations\n\nNo recommendation in this file mutates V1.1. '
                'V1.1 remains authoritative pending explicit approval.\n\n' + _markdown_table(recommendation_frame))
    (root / 'docs/phase2c_registry_recommendations.md').write_text(rec_text, encoding='utf-8')

    coverage = detail[['variable_key', 'first_raw_observation',
                       'first_usable_transformed_observation', 'last_observation',
                       'observations', 'current_status', 'warnings']]
    archive_keys = [key for key, row in registry.rows.items() if row['automation_status'] == 'ARCHIVE_SPIDER']
    external_keys = [key for key, row in registry.rows.items() if row['automation_status'] == 'EXTERNAL']
    derived_keys = [key for key, row in registry.rows.items() if row['automation_status'] == 'DERIVED']
    revisions_path = root / 'metadata/revisions.parquet'
    revisions = pd.read_parquet(revisions_path) if revisions_path.exists() else pd.DataFrame()
    text = f'''# Phase 2C results

## 1. Implementation summary

Registry {registry.version} ({registry.verification_date}) drove all 29 V1 attempts. GDP remains quarterly; the monthly panel is ragged and contains no imputation or interpolation. The build status is `{report['status']}` with {len(report['series'])} automated series and {len(report['failures'])} unresolved series.

## 2. Test results

The completion test command and final count are recorded after the final offline replay. Pipeline validation status: `{report['status']}`.

## 3. Actual coverage of all 29 variables

{_markdown_table(coverage)}

## 4. Variables successfully automated

{', '.join(report['series']) or 'None'}.

## 5. Variables requiring archive spiders

{', '.join(archive_keys)}.

## 6. External-series status

{', '.join(f'{key}: {"automated" if key in report["series"] else report["failures"].get(key, "unresolved")}' for key in external_keys)}.

## 7. Derived-series status

{', '.join(f'{key}: {"automated" if key in report["series"] else report["failures"].get(key, "unresolved")}' for key in derived_keys)}.

## 8. Missingness analysis

The union panel spans {availability_summary['union_start']} to {availability_summary['union_end']}. Threshold dates: {json.dumps(availability_summary['thresholds'])}. Missingness is preserved, not filled.

## 9. Ragged-edge analysis

At {availability_summary['latest_month']}, {availability_summary['latest_available']} of {availability_summary['predictors']} predictors are usable. Missing: {', '.join(availability_summary['latest_missing_variables'])}.

## 10. Structural breaks

Registry-caveat screening identifies: {', '.join(availability_summary['structural_break_variables'])}.

## 11. Outlier summary

All quality flags remain in processed data. Existing industrial-production outliers are unchanged; no outlier was removed. See `metadata/industrial_production_outliers.parquet` and the per-variable warning column above.

## 12. Revision behavior

{len(revisions)} revision records are stored in `metadata/revisions.parquet`. Parser/schema changes are classified separately by the revision utility.

## 13. Release-date availability

{_markdown_table(release[['variable_key', 'classification', 'source_release_dates_observed']])}

## 14. Master dataset dimensions

`v1_monthly`: {monthly.shape[0]} rows × {monthly.shape[1]} columns. `v1_observations_long`: {long.shape[0]} rows × {long.shape[1]} columns. GDP is separate in `gdp_quarterly`.

## 15. Source discrepancies

{len(recommendations)} confirmed discrepancies are listed in `docs/phase2c_registry_recommendations.md`; none silently changed V1.1.

## 16. Registry recommendations

See `docs/phase2c_registry_recommendations.md`. Changes require explicit approval for a later registry version.

## 17. Unresolved risks

{json.dumps(report['failures'], indent=2)}

Historical release timing is incomplete for current-snapshot sources. Archive dates are not treated as fabricated first-release dates. External-source TLS/schema availability remains an operational risk.

## 18. Recommended Phase 3 steps

Approve or reject the Phase 2C registry recommendations; schedule periodic source/replay checks; accumulate genuine vintages and release histories; and define pseudo-real-time information-set tests. Forecasting should begin only after those governance decisions.
'''
    (root / 'docs/phase2c_results.md').write_text(text, encoding='utf-8')


def write_phase2c_artifacts(root: Path, registry, report: dict, series: dict,
                            monthly: pd.DataFrame):
    ensure_failure_artifacts(root, registry, series, report['failures'])
    long = canonical_long(root, registry)
    detail, summary = availability(root, registry, series, report['failures'], monthly)
    release = release_audit(root, registry, long)
    revisions = root / 'metadata/revisions.parquet'
    if not revisions.exists():
        atomic_parquet(pd.DataFrame(columns=[
            'variable_key', 'reference_period', 'old_value', 'new_value', 'old_vintage_date',
            'new_vintage_date', 'absolute_revision', 'relative_revision', 'revision_type',
            'value_field']), revisions)
    atomic_parquet(detail, root / 'metadata/validation_summary.parquet')
    phase2c_docs(root, registry, report, detail, summary, release, monthly, long)
    return dict(long_rows=len(long), availability=summary)
