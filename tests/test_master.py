import pandas as pd
import pytest
from uznowcast.master import build_monthly


def test_names_spine_and_determinism(registry):
    f=pd.DataFrame(dict(reference_date=pd.to_datetime(['2024-01-31','2024-03-31']),frequency='M',clean_value=[1.,2.]))
    series={'industrial_production':f,'usd_uzs':f.copy(),
            'gdp_real_yoy':pd.DataFrame(dict(frequency=['Q'],clean_value=[7.]))}
    result=build_monthly(series,registry)
    assert result.columns.tolist()==['date','ind_prod_yoy_log','usd_uzs_mom_dlog']
    assert result.date.is_unique and len(result)==3
    assert pd.isna(result.ind_prod_yoy_log.iloc[1])
    pd.testing.assert_frame_equal(result,build_monthly(series,registry))


def test_quarterly_predictor_rejected(registry):
    f=pd.DataFrame(dict(reference_date=[pd.Timestamp('2024-03-31')],frequency=['Q'],clean_value=[1.]))
    with pytest.raises(ValueError): build_monthly({'industrial_production':f},registry)


def test_pilot8_clean_fields_order_gdp_exclusion_and_fx_completeness(registry):
    rows = registry.scope('pilot8')
    monthly_keys = [row['variable_key'] for row in rows if row['native_frequency'] != 'Quarterly']
    expected_fields = [row['clean_model_field'] for row in rows if row['native_frequency'] != 'Quarterly']
    base = pd.DataFrame(dict(reference_date=pd.to_datetime(['2026-08-31', '2026-09-30']),
                             frequency=['M', 'M'], clean_value=[1.0, 2.0],
                             quality_flag=['', '']))
    series = {key: base.copy() for key in monthly_keys}
    series['usd_uzs']['is_complete_month'] = [True, False]
    series['usd_uzs']['quality_flag'] = ['', 'partial_month']
    series['gdp_real_yoy'] = pd.DataFrame(dict(reference_date=[pd.Timestamp('2026-06-30')],
                                                frequency=['Q'], clean_value=[7.0]))
    result = build_monthly(series, registry, scope='pilot8')
    assert result.columns.tolist() == (['date'] + expected_fields +
                                       ['usd_uzs_is_complete', 'usd_uzs_quality_flag'])
    assert 'gdp_real_yoy_pct' not in result
    assert bool(result.usd_uzs_is_complete.iloc[0]) is True
    assert bool(result.usd_uzs_is_complete.iloc[1]) is False
    assert result.usd_uzs_quality_flag.iloc[1] == 'partial_month'
