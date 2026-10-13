"""Verified spelling fixtures; no network or production writes."""
from io import BytesIO
import hashlib
import json
from pathlib import Path
import openpyxl
import pandas as pd
import pytest
from scripts.collection.pos import _extract, reporting_period
from tests.collection.test_collection import isolated, updated, run, snapshot
from scripts.collection.http import SourceError
from scripts.operations.state import sha

FIX=Path(__file__).resolve().parents[1]/'fixtures/collection/avgust'

@pytest.mark.parametrize('identifier',['1222302','1843091'])
def test_official_avgust_range_and_amount(identifier):
    evidence=json.loads((FIX/(identifier+'.json')).read_text())
    content=(FIX/(identifier+'.xlsx')).read_bytes()
    assert hashlib.sha256(content).hexdigest()==evidence['workbook_checksum']
    period=reporting_period(evidence['title'])
    assert str(period)==evidence['expected_period']
    book=openpyxl.load_workbook(BytesIO(content),read_only=True,data_only=True)
    try:
        sheet=next(s for s in book if s.title.lower().endswith('eng'))
        assert _extract(list(sheet.values),period)==evidence['expected_value']
    finally: book.close()

def test_avgust_conflicting_range_stays_rejected():
    with pytest.raises(ValueError,match='disagree'):
        reporting_period('as of 1 Avgust 2024 transactions in January-June of 2024')

def test_truncated_total_is_explicit_failure():
    with pytest.raises(ValueError,match='lacks the amount column'):
        _extract([['as of August 1, 2024'],['bank','The amount of transactions through POS-terminals (million UZS)'],['Total']],pd.Period('2024-07'))

def test_failed_reserves_and_pos_keep_independent_gold_update(isolated):
    def fetch(key,*args):
        if key in {'fx_reserves_ex_gold','pos_turnover'}:
            raise SourceError('VALIDATION_FAILED','Isolated admission failure')
        return updated('gold_price',target='gold_price')(key,*args)
    result=run(isolated,fetch)
    assert result['status']=='COLLECTION_DEGRADED'
    stage=snapshot(result,isolated)
    for key in ['fx_reserves_ex_gold','pos_turnover']:
        assert sha(stage/f'data/processed/{key}.parquet')==sha(isolated/f'data/processed/{key}.parquet')
    assert sha(stage/'data/processed/gold_price.parquet')!=sha(isolated/'data/processed/gold_price.parquet')
    assert next(s for s in result['source_status'] if s['variable_key']=='gold_price')['admission']=='ACCEPTED'
