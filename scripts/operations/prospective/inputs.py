"""Actual retrieval gating combined with the unchanged calendar lag mask."""
import pandas as pd
import numpy as np
from scripts.operations.prospective.common import ROOT, FIELDS, safe, digest
from uznowcast.models.data import load_dataset


def eligible(frame, asof):
    frame = frame.copy()
    retrieved = pd.to_datetime(frame.retrieved_at, utc=True, errors='coerce')
    release = pd.to_datetime(frame.source_release_date, utc=True, errors='coerce')
    return frame.loc[retrieved.notna() & retrieved.le(asof) & (release.isna() | release.le(asof))]


def inputs(asof):
    dataset = load_dataset(ROOT)
    observations = eligible(pd.read_parquet(ROOT/'metadata/observations_long.parquet'), asof)
    observations = observations.loc[observations.frequency.astype(str).isin(['M','monthly'])]
    recovered = eligible(pd.read_csv(ROOT/'data/current/predictor_provenance.csv'), asof)
    recovered = recovered.loc[recovered.selected_for_panel.eq(True)]
    research = pd.read_csv(ROOT/'data/current/recovered_monthly.csv').set_index('reference_period')
    index = pd.date_range('2013-01-31', asof.tz_localize(None), freq='ME')
    panel = pd.DataFrame(index=index, columns=FIELDS, dtype=float)
    provenance = []
    for key in FIELDS:
        source = recovered if key in ['industrial_production','pos_turnover'] else observations
        source = source.loc[source.variable_key.eq(key)].copy()
        source['month'] = pd.PeriodIndex(source.reference_period.astype(str),freq='M').to_timestamp('M')
        source['retrieval'] = pd.to_datetime(source.retrieved_at,utc=True)
        source = source.sort_values('retrieval').drop_duplicates('month',keep='last')
        for row in source.to_dict('records'):
            month = row['month']
            if month not in panel.index:
                continue
            value = row['clean_value']
            if key in ['industrial_production','pos_turnover']:
                period = str(month.to_period('M'))
                if period not in research.index:
                    continue
                if key=='pos_turnover':
                    if month>pd.Timestamp('2024-12-31') or research.loc[period,'pos_turnover_scope_verified'] != True:
                        continue
                    value = research.loc[period,'pos_turnover_monthly_log_yoy']
                else:
                    value = research.loc[period,key]
            if pd.notna(value):
                panel.loc[month,key] = float(value)
                provenance.append(safe(dict(variable=key,reference_period=row['reference_period'],value=float(value),
                    retrieved_at=row['retrieved_at'],source_release_date=row['source_release_date'],
                    raw_file_path=row['raw_file_path'],checksum=row['checksum'],source_url=row['source_url'])))
    monthly = dataset.monthly.reindex(dataset.monthly.index.union(panel.index)).copy()*np.nan
    monthly['usd_uzs_mom_dlog'] = panel.usd_uzs.reindex(monthly.index)
    from dataclasses import replace
    return panel, replace(dataset, monthly=monthly), provenance


def status(panel, lags, origin):
    rows=[]
    for key in FIELDS:
        latest=panel[key].last_valid_index()
        expected=(origin-pd.Timedelta(days=lags[key])).to_period('M').to_timestamp('M')
        if expected>origin:
            expected=(expected.to_period('M')-1).to_timestamp('M')
        stale=None if latest is None else max(0, expected.to_period('M').ordinal-latest.to_period('M').ordinal)
        rows.append(dict(variable=key,latest_usable_month=latest,expected_month=expected,stale_months=stale,
            latest_observation=latest,expected_latest_observation=expected,release_lag=lags[key],months_stale=stale,
            missing_recent=int(panel[key].tail(3).isna().sum()),source_status='AVAILABLE_WITH_GAPS' if latest is not None else 'UNAVAILABLE',
            historical_vintage_status='LATEST_RETRIEVED_RESEARCH_HISTORY; NOT COMPLETE HISTORICAL REAL-TIME VINTAGES',
            current_vintage_hash=digest(safe(panel[key].dropna().reset_index().to_dict('records'))),
            model_usage_status='FROZEN_INCLUDED_NO_IMPUTATION',warning='Scope-limited stale POS' if key=='pos_turnover' else 'Missing release dates remain unknown',
            status='RED' if latest is None or stale>2 else 'AMBER' if stale else 'GREEN',
            note='Verified scope ends December 2024; later cells excluded' if key=='pos_turnover' else 'Observed retrieval gated; unknown release dates remain null'))
    return pd.DataFrame(rows)
