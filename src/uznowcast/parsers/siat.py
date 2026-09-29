"""Parse the observed SIAT multilingual wide table; reject ambiguous dimensions."""
import re
import numpy as np
import pandas as pd

DIMENSIONS = {'Code', 'Klassifikator', 'Klassifikator_ru', 'Klassifikator_en', 'Klassifikator_uzc'}


def parse_siat(payload, row: dict, contract: dict) -> pd.DataFrame:
    if not isinstance(payload, list) or len(payload) != 1 or set(payload[0]) != {'metadata', 'data'}:
        raise ValueError('SIAT expected a single metadata/data table')
    if row['row_field_selector'] != contract['registry_selector'] or row['raw_unit'] != contract['registry_unit']:
        raise ValueError('Registry selector/unit changed; review SIAT adapter')
    if row['rule_codes'] != contract['rule_codes']:
        raise ValueError('Registry transformation changed; review SIAT adapter')
    metadata = payload[0]['metadata']

    def check(name, expected):
        values = {m['value_en'] for m in metadata if m.get('name_en') == name}
        if values != {expected}:
            raise ValueError(f'SIAT metadata mismatch for {name}: {values}; expected {expected}')

    check('Indicator identification number (code)', row['native_indicator_dataset_id'])
    check('Unit of measurement', contract['unit'])
    frequencies = {m['value_en'].lower() for m in metadata if m.get('name_en') == 'Periodicity'}
    if frequencies != {contract['frequency']} or row['native_frequency'].lower() != contract['frequency']:
        raise ValueError('SIAT frequency mismatch')
    rows = payload[0]['data']
    matches = [r for r in rows if r.get('Code') == contract['code'] and r.get('Klassifikator_en') == contract['label']]
    if len(matches) != 1:
        raise ValueError(f'SIAT exact row selector matched {len(matches)} rows')
    selected_raw = matches[0]
    # SIAT's PPI payload mixes Cyrillic 'М' (U+041C) and Latin 'M' in period labels
    # for different year ranges. Normalize before matching but retain the mapping so
    # the raw payload is not silently rewritten.
    label_map = {k: (k.replace('М', 'M') if isinstance(k, str) else k) for k in selected_raw}
    selected = {label_map[k]: v for k, v in selected_raw.items()}
    pattern = r'\d{4}-Q[1-4]' if contract['frequency'] == 'quarterly' else r'\d{4}-M(?:0[1-9]|1[0-2])'
    unexpected = set(selected) - DIMENSIONS - {k for k in selected if re.fullmatch(pattern, k)}
    if unexpected or not DIMENSIONS <= selected.keys():
        raise ValueError(f'SIAT unexpected dimensions/period labels: {unexpected}')
    records = []
    notes = [m['value_en'] for m in metadata if m.get('name_en') == 'Note']
    if contract.get('required_note_fragment') and not any(contract['required_note_fragment'] in note for note in notes):
        raise ValueError('SIAT source no longer confirms the registry price basis')
    for label, value in selected.items():
        if label in DIMENSIONS:
            continue
        if value is None:
            number = np.nan
        elif isinstance(value, (int, float)) and not isinstance(value, bool) and np.isfinite(value):
            number = float(value)
        else:
            raise ValueError(f'SIAT unexpected nonnumeric value: {label}: {value!r}')
        freq = 'Q' if contract['frequency'] == 'quarterly' else 'M'
        period = pd.Period(label.replace('-M', '-').replace('-Q', 'Q'), freq=freq)
        scale = float(contract.get('source_to_registry_scale', 1.0))
        records.append(dict(reference_period=str(period), reference_date=period.to_timestamp(how='end').normalize(),
                            frequency=freq, source_raw_value=number, raw_value=number * scale,
                            source_raw_unit=contract['unit'], unit_conversion_scale=scale, clean_value=np.nan,
                            quality_flag='missing_raw' if pd.isna(number) else '', source_notes='; '.join(notes),
                            selected_code=contract['code'], selected_label=contract['label']))
    if not records:
        raise ValueError('SIAT selected row has no observations')
    result = pd.DataFrame(records).sort_values('reference_date').reset_index(drop=True)
    if result.reference_period.duplicated().any():
        raise ValueError('SIAT duplicate periods')
    return result
