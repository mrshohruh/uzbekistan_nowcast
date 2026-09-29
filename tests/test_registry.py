import shutil
import openpyxl
import pytest
from conftest import ROOT
from uznowcast.registry import load_registry, PILOT, PILOT8


def test_row_four_and_original_labels(registry):
    assert len(registry.rows) == 29
    assert registry.original_labels['variable_key'] == 'Variable key'
    assert set(PILOT) <= registry.rows.keys()
    assert set(PILOT8) <= registry.rows.keys()
    assert [row['variable_key'] for row in registry.scope('pilot8')] == list(PILOT8)
    assert registry.rows['industrial_production']['clean_model_field'] == 'ind_prod_yoy_log'
    assert registry.rows['usd_uzs']['rule_codes'] == ['FX_DAILY_TO_MONTHLY']


def test_registry_v1_2_carries_phase3b_corrections():
    v12 = load_registry(ROOT / 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx')
    assert v12.version == 'V1.2'
    assert v12.verification_date == '2026-09-29'
    assert len(v12.rows) == 29
    assert v12.rows['manufacturing']['row_field_selector'] == \
        'Code=C; Klassifikator_en=Manufacturing industry'
    assert v12.rows['electricity_gas']['row_field_selector'] == \
        'Code=D; Klassifikator_en=Electricity, gas, steam and air conditioning'
    assert v12.rows['gold_exports_proxy']['row_field_selector'] == \
        'Code=9; Klassifikator_en=Other goods (gold-dominated residual category)'
    assert v12.rows['retail_trade']['raw_unit'] == \
        'billion UZS (source: million sums; standardization scale 0.001)'
    assert v12.rows['wholesale_trade']['raw_unit'] == \
        'billion UZS (source: million sums; standardization scale 0.001)'
    assert v12.rows['fx_reserves_ex_gold']['machine_download_url'] == \
        'https://cbu.uz/en/statistics/e-gdds/data/111574/'
    assert 'thousand UZS' in v12.rows['interbank_payments']['raw_unit']
    breaks = v12.rows['ppi']['structural_breaks_caveats']
    assert 'since April 2024 the scope of reporting entities has been expanded' in breaks
    assert "Cyrillic 'М'" in breaks and "Latin 'M'" in breaks
    # russia_ipi kept unchanged in V1.2 per Phase 3B rule
    assert v12.rows['russia_ipi']['provider'] == 'Rosstat'


@pytest.mark.parametrize('cell,value', [('B6', 'gdp_real_yoy'), ('X5','UNKNOWN'), ('S5','guess a transformation'),
                                       ('E5',None), ('K5','Annual'), ('J5',None), ('T6','gdp_real_yoy_pct')])
def test_invalid_registry(tmp_path, cell, value):
    path=tmp_path/'registry.xlsx'
    shutil.copyfile(ROOT/'registry/uzbekistan_nowcasting_v1_registry.xlsx',path)
    w=openpyxl.load_workbook(path)
    w['V1 Registry'][cell]=value
    w.save(path)
    w.close()
    with pytest.raises(ValueError):
        load_registry(path,ROOT/'config/registry_contracts.json')
