"""Fixture-guard, tier resolution, frozen validation, effective-training."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from uznowcast.models.data import ModelingDataset
from uznowcast.models.production import (
    FixtureMasterRefused, HOLDOUT_QUARTERS, MissingTierVariables,
    PRIMARY_MIN_ROWS, SMALL_SAMPLE_MIN_ROWS, TIER_A, TIER_B_ADDITIONAL,
    TIER_C_ADDITIONAL, freeze_validation, guard_master_dir,
    master_fingerprint, minimum_effective_rows, resolve_tiers,
)


# ---- fixture guard ---------------------------------------------------------

@pytest.mark.parametrize('path', [
    'data/master_from_fixtures',
    'data/master_from_fixtures/',
    '/tmp/foo/data/master_from_fixtures',
    'nested/dir/data/master_from_fixtures',
])
def test_fixture_dir_refused(path):
    with pytest.raises(FixtureMasterRefused):
        guard_master_dir(path)


def test_fixture_guard_allows_real_master():
    guard_master_dir('data/master')
    guard_master_dir('/tmp/foo/data/master')


def test_fixture_guard_bypass_only_for_tests():
    guard_master_dir('data/master_from_fixtures', allow_fixture=True)


# ---- tier resolution -------------------------------------------------------

def test_resolve_tiers_strict_raises_when_predictor_missing(synthetic_dataset):
    with pytest.raises(MissingTierVariables) as ex:
        resolve_tiers(synthetic_dataset, strict=True)
    message = str(ex.value)
    # Synthetic dataset lacks many Tier A variables (ppi, usd_uzs, ...).
    assert 'A' in message or 'B' in message or 'C' in message


def test_resolve_tiers_records_configured_found_missing(synthetic_dataset):
    resolutions = resolve_tiers(synthetic_dataset, strict=False)
    tiers = {r.tier: r for r in resolutions}
    # Tier A configured must equal TIER_A verbatim.
    assert tiers['A'].configured_keys == TIER_A
    # 'm2' is in the synthetic dataset; it is a Tier A variable and must be found.
    assert 'm2' in tiers['A'].found_keys
    # 'ppi' is Tier A and NOT in the synthetic dataset → recorded as missing.
    assert 'ppi' in tiers['A'].missing_keys
    # Experimental tier is informational only; not part of Tier A/B/C.
    assert tiers['experimental'].kind == 'informational'


def test_resolve_tiers_serializes_to_dict(synthetic_dataset):
    resolutions = resolve_tiers(synthetic_dataset, strict=False)
    data = [r.to_dict() for r in resolutions]
    assert all(set(row.keys()) >= {'tier', 'kind', 'configured_keys',
                                      'found_keys', 'missing_keys',
                                      'excluded_keys', 'found_fields'}
                for row in data)


# ---- frozen validation -----------------------------------------------------

def test_freeze_validation_reserves_last_four(synthetic_dataset):
    frozen = freeze_validation(synthetic_dataset, holdout=HOLDOUT_QUARTERS)
    quarters = synthetic_dataset.gdp['quarter'].astype(str).tolist()
    assert len(frozen.holdout_quarters) == 4
    assert frozen.holdout_quarters == tuple(quarters[-4:])
    assert frozen.development_quarters == tuple(quarters[:-4])
    # Development + holdout partition the target sample.
    assert set(frozen.holdout_quarters).isdisjoint(set(frozen.development_quarters))
    assert (set(frozen.holdout_quarters) | set(frozen.development_quarters)
            == set(quarters))


def test_freeze_validation_matches_documented_holdout(synthetic_dataset):
    # The Phase 4A.1 spec expects 2025-Q3/Q4 and 2026-Q1/Q2 when the
    # target ends at 2026-Q2; the synthetic dataset uses that exact tail
    # so the assertion checks the programmatic guarantee.
    frozen = freeze_validation(synthetic_dataset, holdout=HOLDOUT_QUARTERS)
    quarters = synthetic_dataset.gdp['quarter'].astype(str).tolist()
    if quarters[-1] == '2026-Q2':
        assert frozen.holdout_quarters == ('2025-Q3', '2025-Q4', '2026-Q1', '2026-Q2')


def test_freeze_validation_records_rule(synthetic_dataset):
    frozen = freeze_validation(synthetic_dataset, holdout=HOLDOUT_QUARTERS)
    payload = frozen.to_dict()
    assert payload['holdout_count'] == 4
    assert 'rule' in payload and 'never' in payload['rule']


# ---- effective-training threshold -----------------------------------------

def test_minimum_effective_rows_matches_spec():
    assert minimum_effective_rows(1) == 12
    assert minimum_effective_rows(2) == 12
    assert minimum_effective_rows(3) == 12
    assert minimum_effective_rows(4) == 12  # 3*4 = 12
    assert minimum_effective_rows(5) == 15
    assert minimum_effective_rows(6) == 18


# ---- master fingerprint ---------------------------------------------------

def test_master_fingerprint_records_dimensions(tmp_path, synthetic_dataset, monkeypatch):
    # master_fingerprint reads file bytes from disk; write minimal files so
    # the SHA-256 lookup exercises the real code path.
    master_dir = tmp_path / 'data/master'
    master_dir.mkdir(parents=True)
    (master_dir / 'v1_monthly.parquet').write_bytes(b'monthly')
    (master_dir / 'gdp_quarterly.parquet').write_bytes(b'quarterly')
    reg_dir = tmp_path / 'registry'
    reg_dir.mkdir()
    (reg_dir / 'uzbekistan_nowcasting_v1.2_registry.xlsx').write_bytes(b'registry')
    fingerprint = master_fingerprint(tmp_path, synthetic_dataset)
    assert fingerprint.monthly_rows == len(synthetic_dataset.monthly)
    assert fingerprint.quarterly_rows == len(synthetic_dataset.gdp)
    assert fingerprint.monthly_sha256 == \
        __import__('hashlib').sha256(b'monthly').hexdigest()
    assert fingerprint.quarterly_sha256 == \
        __import__('hashlib').sha256(b'quarterly').hexdigest()
    assert fingerprint.registry_sha256 == \
        __import__('hashlib').sha256(b'registry').hexdigest()


def test_master_fingerprint_survives_missing_files(tmp_path, synthetic_dataset):
    fingerprint = master_fingerprint(tmp_path, synthetic_dataset)
    assert fingerprint.monthly_sha256 is None
    assert fingerprint.quarterly_sha256 is None
    assert fingerprint.registry_sha256 is None
