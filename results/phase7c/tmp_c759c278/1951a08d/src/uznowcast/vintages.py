"""Retain every retrieval vintage; compare values without rewriting history."""
import pandas as pd
from uznowcast.provenance import append_table


def available_asof(observations: pd.DataFrame, asof) -> pd.DataFrame:
    """Conservative observed information set, never backdate a revised retrieval.

    Provider dataset-update dates do not prove that today's historical values were
    available then. This utility therefore gates on retrieval as well as any known
    release timestamp. It does not reconstruct unobserved first-release history.
    """
    cutoff = pd.Timestamp(asof)
    cutoff = cutoff.tz_localize('UTC') if cutoff.tzinfo is None else cutoff.tz_convert('UTC')
    retrieved = pd.to_datetime(observations.retrieved_at, utc=True, format='mixed')
    release = pd.to_datetime(observations.source_release_date, utc=True, format='mixed')
    eligible = observations.loc[(retrieved <= cutoff) & (release.isna() | (release <= cutoff))]
    return eligible.sort_values('retrieved_at').drop_duplicates(['variable_key', 'reference_period', 'frequency'], keep='last')


def compare_revisions(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    columns = ['variable_key', 'reference_period', 'old_value', 'new_value', 'old_vintage_date',
               'new_vintage_date', 'absolute_revision', 'relative_revision', 'revision_type', 'value_field']
    if old.empty:
        return pd.DataFrame(columns=columns)
    keys = ['variable_key', 'reference_period', 'frequency']
    latest = old.sort_values('retrieved_at').drop_duplicates(keys, keep='last')
    merged = latest.merge(new, on=keys, suffixes=('_old', '_new'))
    records = []
    for _, item in merged.iterrows():
        for field in ('raw_value', 'clean_value'):
            a, b = item[f'{field}_old'], item[f'{field}_new']
            if (pd.isna(a) and pd.isna(b)) or (pd.notna(a) and pd.notna(b) and a == b):
                continue
            kind = 'source_revision'
            if item.parser_version_old != item.parser_version_new or item.schema_fingerprint_old != item.schema_fingerprint_new:
                kind = 'suspected_schema_or_parser_change'
            if field == 'clean_value' and kind == 'source_revision':
                kind = 'transformed_value_revision'
            records.append(dict(variable_key=item.variable_key, reference_period=item.reference_period,
                                old_value=a, new_value=b, old_vintage_date=item.vintage_date_old,
                                new_vintage_date=item.vintage_date_new, absolute_revision=b-a,
                                relative_revision=(b-a)/abs(a) if pd.notna(a) and a != 0 else None,
                                revision_type=kind, value_field=field))
    return pd.DataFrame(records, columns=columns)


def store_vintages(frame, root):
    path = root / 'metadata/observations_long.parquet'
    old = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    revisions = compare_revisions(old, frame)
    if not revisions.empty:
        append_table(revisions, root / 'metadata/revisions.parquet', ['variable_key', 'reference_period', 'old_vintage_date', 'new_vintage_date', 'value_field'])
    identity = ['variable_key', 'reference_period', 'frequency', 'retrieved_at', 'checksum', 'parser_version']
    append_table(frame, path, identity)
    append_table(frame[['variable_key', 'frequency', 'vintage_date', 'retrieved_at', 'source_release_date', 'raw_file_path', 'checksum', 'parser_version']].drop_duplicates(),
                 root / 'metadata/vintages.parquet', ['variable_key', 'frequency', 'vintage_date', 'checksum', 'parser_version'])
    return len(revisions)
