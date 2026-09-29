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
