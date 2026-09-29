from copy import deepcopy
from pathlib import Path
import json
import openpyxl
import pandas as pd
import pytest

from conftest import ROOT
from uznowcast.parsers.cbu import parse_m2_xlsx
from uznowcast.transforms.growth import log_growth
from uznowcast.io.cbu import download_m2


def contracts():
    return json.loads((ROOT / 'config/cbu_contracts.json').read_text(encoding='utf-8'))


def test_frozen_m2_exact_row_unit_frequency_and_growth(registry):
    content = (ROOT / 'tests/fixtures/m2.xlsx').read_bytes()
    frame = parse_m2_xlsx(content, registry.rows['m2'], contracts()['m2'])
    assert len(frame) == 164
    assert frame.reference_period.iloc[0] == '2013-01'
    assert frame.reference_period.iloc[-1] == '2026-08'
    assert set(frame.frequency) == {'M'}
    assert frame.raw_value.iloc[0] == pytest.approx(24432.690855)
    transformed = log_growth(frame, 'raw_value', 12)
    assert transformed.clean_value.notna().sum() == 152
    assert transformed.clean_value.iloc[12] == pytest.approx(
        100 * __import__('numpy').log(frame.raw_value.iloc[12] / frame.raw_value.iloc[0]))


@pytest.mark.parametrize('cell,value', [('A2', 'million sum'), ('A17', 'M2'), ('B4', '2013-02')])
def test_m2_schema_changes_fail(tmp_path, registry, cell, value):
    source = ROOT / 'tests/fixtures/m2.xlsx'
    target = tmp_path / 'm2.xlsx'
    target.write_bytes(source.read_bytes())
    workbook = openpyxl.load_workbook(target)
    workbook['Dataset'][cell] = value
    workbook.save(target)
    workbook.close()
    with pytest.raises(ValueError):
        parse_m2_xlsx(target.read_bytes(), registry.rows['m2'], contracts()['m2'])


def test_ready_page_resolves_official_workbook_and_release_date(registry):
    page = (ROOT / 'tests/fixtures/m2_page.html').read_bytes()
    workbook = (ROOT / 'tests/fixtures/m2.xlsx').read_bytes()

    class Archive:
        def __init__(self):
            self.urls = []

        def get_bytes(self, row, url, **kwargs):
            self.urls.append(url)
            meta = dict(source_url=url, raw_file_path=f'raw-{len(self.urls)}',
                        retrieved_at='2026-09-29T00:00:00+00:00', checksum='hash',
                        schema_fingerprint='schema')
            return (page if url == row['human_source_url'] else workbook), meta

    archive = Archive()
    content, meta = download_m2(archive, registry.rows['m2'])
    assert content == workbook
    assert archive.urls[-1] == 'https://cbu.uz/sdmx/public/DCS_Uzbekistan_Online.xlsx'
    assert meta['source_release_date'] == '2026-09-25T09:40:00+05:00'
    assert meta['page_raw_file_path'] == 'raw-1'
