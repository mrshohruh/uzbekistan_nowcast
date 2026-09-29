from copy import deepcopy
import pytest
from uznowcast.parsers.siat import parse_siat
from uznowcast.transforms.growth import gdp_target
from uznowcast.transforms.prices import monthly_index_log


def test_gdp_quarterly(registry, contracts, fixture_json):
    frame=parse_siat(fixture_json('gdp_real_yoy'),registry.rows['gdp_real_yoy'],contracts['gdp_real_yoy'])
    got=gdp_target(frame)
    assert len(got)==34
    assert set(got.frequency)=={'Q'}
    assert got.clean_value.iloc[0]==pytest.approx(5.9)
    assert set(got.reference_date.dt.month)<={3,6,9,12}


def test_industrial_exact_total(registry,contracts,fixture_json):
    got=parse_siat(fixture_json('industrial_production'),registry.rows['industrial_production'],contracts['industrial_production'])
    assert len(got)==91
    assert got.raw_value.iloc[0]==22233.6
    assert set(got.selected_code)=={'B, C, D, E'}


@pytest.mark.parametrize('key,code,label,first,last', [
    ('construction', '1700', 'Republic of Uzbekistan', 5860.8, 259405.4),
    ('exports_total', '1700', 'Republic of Uzbekistan', 694.7, 22866.9),
    ('imports_total', '1700', 'Republic of Uzbekistan', 1639.2, 34535.6),
])
def test_phase2b_ytd_siat_exact_rows(key, code, label, first, last, registry, contracts, fixture_json):
    got = parse_siat(fixture_json(key), registry.rows[key], contracts[key])
    assert len(got) == 68
    assert set(got.selected_code) == {code}
    assert set(got.selected_label) == {label}
    assert got.raw_value.iloc[0] == first and got.raw_value.iloc[-1] == last


def test_cpi_exact_published_monthly_index(registry, contracts, fixture_json):
    parsed = parse_siat(fixture_json('cpi_headline'), registry.rows['cpi_headline'], contracts['cpi_headline'])
    assert len(parsed) == 68 and set(parsed.selected_code) == {'1'}
    assert set(parsed.selected_label) == {'Cumulative index'}
    transformed = monthly_index_log(parsed)
    assert transformed.clean_value.iloc[0] == pytest.approx(100 * __import__('numpy').log(1.01))


@pytest.mark.parametrize('change',['duplicate','label','code','unit','id','dimension','bad_period','text_value','price_basis'])
def test_schema_changes_fail(change,registry,contracts,fixture_json):
    obj=deepcopy(fixture_json('industrial_production'))
    data=obj[0]['data']
    if change=='duplicate': data.append(deepcopy(data[0]))
    if change=='label': data[0]['Klassifikator_en']='Industrial production (regional)'
    if change=='code': data[0]['Code']='other'
    if change in ('unit','id'):
        name='Unit of measurement' if change=='unit' else 'Indicator identification number (code)'
        for m in obj[0]['metadata']:
            if m['name_en']==name: m['value_en']='WRONG'
    if change=='dimension': data[0]['region']='unknown'
    if change=='bad_period': data[0]['2019-M13']=1
    if change=='text_value': data[0]['2019-M01']='unexpected missing token'
    if change=='price_basis':
        obj[0]['metadata']=[m for m in obj[0]['metadata'] if m['name_en']!='Note']
    with pytest.raises(ValueError):
        parse_siat(obj,registry.rows['industrial_production'],contracts['industrial_production'])
