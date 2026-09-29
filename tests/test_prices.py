import numpy as np
import pandas as pd
import pytest

from uznowcast.transforms.prices import monthly_index_log


def test_previous_month_index_log_transform_preserves_raw():
    frame = pd.DataFrame(dict(reference_date=pd.to_datetime(['2024-01-31', '2024-02-29']),
                              raw_value=[101.0, 99.0], quality_flag=['', '']))
    result = monthly_index_log(frame)
    assert result.raw_value.tolist() == [101.0, 99.0]
    assert result.clean_value.iloc[0] == pytest.approx(100 * np.log(1.01))
    assert result.clean_value.iloc[1] == pytest.approx(100 * np.log(.99))


def test_nonpositive_price_index_is_null_and_flagged():
    frame = pd.DataFrame(dict(reference_date=pd.to_datetime(['2024-01-31']),
                              raw_value=[0.0], quality_flag=['']))
    result = monthly_index_log(frame)
    assert pd.isna(result.clean_value.iloc[0])
    assert 'nonpositive_price_index' in result.quality_flag.iloc[0]
