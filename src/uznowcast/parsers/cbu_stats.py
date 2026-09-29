"""Strict parsers for CBU monthly statistical workbooks."""
from io import BytesIO
import re

import numpy as np
import openpyxl
import pandas as pd


def parse_reserves_xlsx(content: bytes, row: dict) -> pd.DataFrame:
    target = 'Foreign currency reserves (in convertible foreign currencies)'
    if row['row_field_selector'] != target or row['raw_unit'] != 'million USD, end of period':
        raise ValueError('CBU reserves registry contract changed')
    workbook = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
    try:
        if workbook.sheetnames != ['Dataset']:
            raise ValueError('CBU reserves workbook sheet changed')
        sheet = workbook['Dataset']
        if sheet['A1'].value != 'International Reserves of the Republic of Uzbekistan' or sheet['A2'].value != row['raw_unit']:
            raise ValueError('CBU reserves workbook title/unit changed')
        headers = [cell.value for cell in sheet[4]]
        labels = [(cells[0].row, str(cells[0].value).replace('\xa0', ' ').strip())
                  for cells in sheet.iter_rows(min_col=1, max_col=1) if cells[0].value]
        matches = [number for number, label in labels if target in label]
        if len(matches) != 1:
            raise ValueError(f'CBU reserves exact row matched {len(matches)} rows')
        selected = matches[0]
        records = []
        for column, label in enumerate(headers[1:], 2):
            if label is None:
                continue
            if not isinstance(label, str) or not re.fullmatch(r'\d{4}-(?:0[1-9]|1[0-2])', label):
                raise ValueError(f'CBU reserves unexpected period: {label!r}')
            value = sheet.cell(selected, column).value
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not np.isfinite(value) or value <= 0:
                raise ValueError(f'CBU reserves invalid value: {label}: {value!r}')
            period = pd.Period(label, freq='M')
            records.append(dict(reference_period=str(period),
                                reference_date=period.to_timestamp(how='end').normalize(),
                                frequency='M', raw_value=float(value), clean_value=np.nan,
                                quality_flag='', selected_label=target))
        result = pd.DataFrame(records)
        expected = pd.period_range(result.reference_period.iloc[0], result.reference_period.iloc[-1], freq='M')
        if list(result.reference_period) != [str(value) for value in expected]:
            raise ValueError('CBU reserves periods are not contiguous')
        return result
    finally:
        workbook.close()
