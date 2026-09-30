import numpy as np
import pandas as pd
import pytest

from uznowcast.models.splits import expanding_window, first_evaluation_quarter, evaluation_span
from uznowcast.models.preprocess import (
    Standardizer, robust_flag_mask, apply_robust_variant, training_slice,
)


def test_expanding_window_basic():
    quarters = [f'2019-Q{q}' for q in range(1, 5)] + [f'2020-Q{q}' for q in range(1, 5)]
    splits = expanding_window(quarters, min_train=4)
    assert len(splits) == 4
    assert splits[0].train == ('2019-Q1', '2019-Q2', '2019-Q3', '2019-Q4')
    assert splits[0].target == '2020-Q1'
    assert splits[-1].target == '2020-Q4'
    assert first_evaluation_quarter(splits) == '2020-Q1'
    assert evaluation_span(splits) == ('2020-Q1', '2020-Q4')


def test_expanding_window_no_leakage_of_target():
    quarters = ['2020-Q1', '2020-Q2', '2020-Q3', '2020-Q4', '2021-Q1']
    splits = expanding_window(quarters, min_train=3)
    # A model at step k may not see any quarter with index >= k+min_train
    for split in splits:
        assert split.target not in split.train
        target_idx = quarters.index(split.target)
        for t in split.train:
            assert quarters.index(t) < target_idx


def test_expanding_window_empty_when_min_train_too_large():
    assert expanding_window(['2020-Q1', '2020-Q2'], min_train=5) == []
    with pytest.raises(ValueError):
        expanding_window(['2020-Q1'], min_train=0)


def test_standardizer_uses_training_only():
    train = pd.DataFrame({'x': [1.0, 2.0, 3.0, 4.0, 5.0]})
    all_data = pd.DataFrame({'x': [1.0, 2.0, 3.0, 4.0, 5.0, 100.0, -100.0]})
    std = Standardizer.fit(train)
    tr = std.transform(all_data)
    # mean/std were computed on train only, so the last two rows should be
    # large in magnitude (not clipped by including them in the statistics).
    assert abs(tr['x'].iloc[-2]) > 30
    assert abs(tr['x'].iloc[-1]) > 30


def test_standardizer_guards_constant_columns():
    train = pd.DataFrame({'x': [3.0, 3.0, 3.0]})
    std = Standardizer.fit(train)
    tr = std.transform(pd.DataFrame({'x': [3.0, 4.0]}))
    assert not np.isnan(tr['x']).any()


def test_robust_variant_never_edits_database():
    frame = pd.DataFrame({'a': [1.0, 2.0, 3.0], 'b': [10.0, 20.0, 30.0]})
    mask = pd.DataFrame({'a': [False, True, False], 'b': [False, False, True]})
    masked = apply_robust_variant(frame, mask)
    assert frame.equals(pd.DataFrame({'a': [1.0, 2.0, 3.0], 'b': [10.0, 20.0, 30.0]}))
    assert np.isnan(masked.loc[1, 'a'])
    assert np.isnan(masked.loc[2, 'b'])


def test_robust_flag_mask_reads_quality_column():
    frame = pd.DataFrame({'a': [1.0, 2.0], 'quality_flag': ['', 'extreme_log_change']})
    mask = robust_flag_mask(frame, 'quality_flag')
    assert not mask.loc[0, 'a']
    assert mask.loc[1, 'a']


def test_training_slice_respects_train_end():
    monthly = pd.DataFrame({'x': range(24)},
                            index=pd.date_range('2020-01-31', periods=24, freq='ME'))
    monthly.index.name = 'date'
    slice_ = training_slice(monthly, ('2020-Q1', '2020-Q2', '2020-Q3'))
    assert slice_.index.max() == pd.Timestamp('2020-09-30')


def test_training_slice_begins_at_first_gdp_training_quarter():
    monthly = pd.DataFrame(
        {'x': range(732)},
        index=pd.date_range('1960-01-31', periods=732, freq='ME'))
    slice_ = training_slice(monthly, ('2018-Q1', '2018-Q2', '2018-Q3'))
    assert slice_.index.min() == pd.Timestamp('2018-01-31')
    assert slice_.index.max() == pd.Timestamp('2018-09-30')
    assert not (slice_.index.year == 1960).any()


def test_training_slice_empty_when_no_quarters():
    monthly = pd.DataFrame({'x': [1, 2]}, index=pd.date_range('2020-01-31', periods=2, freq='ME'))
    monthly.index.name = 'date'
    assert training_slice(monthly, ()).empty
