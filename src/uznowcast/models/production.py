"""Phase 4A.1 production-mode guardrails on top of the Phase 4A evaluator.

The Phase 4A framework happily runs against any master file passed via
``--master-dir``. Phase 4A.1 tightens that contract:

* The active master directory must not be the fixture-based rehearsal
  directory (``data/master_from_fixtures``) — the fixture rehearsal is
  a development aid, not a production input.
* Every expected non-experimental Tier A/B/C predictor is checked for
  presence in the master; a missing predictor emits an explicit warning
  and is recorded in ``results/phase4a1_resolved_tiers.json`` rather than
  silently disappearing.
* The registry SHA-256, master SHA-256s, row/column counts, and
  first/last periods are recorded on every run so the operator can
  prove which V1.2 build produced the numbers.
* The most recent four GDP quarters are reserved as the frozen
  validation set and refused to any Phase 4A.1 evaluation loop.
* Effective-training safeguards enforce
  ``max(12, 3 × free_parameters)`` on the *complete* training rows
  entering each regression (not just the count of prior GDP quarters).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Sequence
import json
import warnings

import pandas as pd

from uznowcast.models.data import (
    ModelingDataset, TIER_A, TIER_B_ADDITIONAL, TIER_C_ADDITIONAL,
    EXPERIMENTAL_KEYS, EXCLUDED_KEYS,
)


FIXTURE_MASTER_DIR_NAMES: tuple[str, ...] = (
    'master_from_fixtures',
    'data/master_from_fixtures',
)
"""Directory suffixes that identify the fixture rehearsal and must be
refused by any Phase 4A.1 production command."""


class FixtureMasterRefused(RuntimeError):
    """Raised when a Phase 4A.1 command is pointed at the fixture rehearsal."""


class MissingTierVariables(RuntimeError):
    """Raised when the strict tier resolver is run and required predictors
    are missing from the frozen V1.2 master."""


def guard_master_dir(master_dir: str, *, allow_fixture: bool = False) -> None:
    """Refuse the fixture rehearsal directory when running production.

    ``allow_fixture=True`` is provided only so tests can point at a
    synthetic path that happens to sit under ``data/master_from_fixtures``;
    the CLI never sets that flag.
    """
    normalized = master_dir.replace('\\', '/').rstrip('/')
    if allow_fixture:
        return
    for suffix in FIXTURE_MASTER_DIR_NAMES:
        if normalized == suffix or normalized.endswith('/' + suffix):
            raise FixtureMasterRefused(
                f'Phase 4A.1 refuses the fixture rehearsal directory: '
                f'{master_dir!r}. Use data/master/ produced by '
                f"'python -m uznowcast.cli build --scope v1'.")


def _hash_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class MasterFingerprint:
    """Immutable identity of the frozen V1.2 master files a run consumed."""

    master_dir: str
    monthly_path: str
    quarterly_path: str
    registry_path: str
    monthly_sha256: str | None
    quarterly_sha256: str | None
    registry_sha256: str | None
    monthly_rows: int
    monthly_predictor_columns: int
    monthly_first_period: str | None
    monthly_last_period: str | None
    quarterly_rows: int
    quarterly_first_quarter: str | None
    quarterly_last_quarter: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def master_fingerprint(root: Path, dataset: ModelingDataset,
                       master_dir: str = 'data/master',
                       monthly_name: str = 'v1_monthly.parquet',
                       gdp_name: str = 'gdp_quarterly.parquet',
                       registry_relative: str
                       = 'registry/uzbekistan_nowcasting_v1.2_registry.xlsx',
                       ) -> MasterFingerprint:
    root = Path(root).resolve()
    monthly_path = root / master_dir / monthly_name
    quarterly_path = root / master_dir / gdp_name
    registry_path = root / registry_relative
    monthly_columns = [c for c in dataset.monthly.columns]
    return MasterFingerprint(
        master_dir=str((root / master_dir).relative_to(root)),
        monthly_path=str(monthly_path.relative_to(root)),
        quarterly_path=str(quarterly_path.relative_to(root)),
        registry_path=str(registry_path.relative_to(root)),
        monthly_sha256=_hash_file(monthly_path),
        quarterly_sha256=_hash_file(quarterly_path),
        registry_sha256=_hash_file(registry_path),
        monthly_rows=int(len(dataset.monthly)),
        monthly_predictor_columns=int(len(monthly_columns)),
        monthly_first_period=(str(dataset.monthly.index.min().date())
                              if len(dataset.monthly) else None),
        monthly_last_period=(str(dataset.monthly.index.max().date())
                             if len(dataset.monthly) else None),
        quarterly_rows=int(len(dataset.gdp)),
        quarterly_first_quarter=(str(dataset.gdp['quarter'].iloc[0])
                                 if len(dataset.gdp) else None),
        quarterly_last_quarter=(str(dataset.gdp['quarter'].iloc[-1])
                                if len(dataset.gdp) else None),
    )


@dataclass(frozen=True)
class TierResolution:
    """Which registry keys landed in which tier vs. were dropped."""

    tier: str
    configured_keys: tuple[str, ...]
    found_keys: tuple[str, ...]
    missing_keys: tuple[str, ...]
    excluded_keys: tuple[str, ...]         # experimental/unresolved skipped by design
    found_fields: tuple[str, ...]
    kind: str = 'production'              # 'production' or 'informational'

    def to_dict(self) -> dict:
        return dict(
            tier=self.tier,
            kind=self.kind,
            configured_keys=list(self.configured_keys),
            found_keys=list(self.found_keys),
            missing_keys=list(self.missing_keys),
            excluded_keys=list(self.excluded_keys),
            found_fields=list(self.found_fields),
        )


def resolve_tiers(dataset: ModelingDataset, *, strict: bool = True) -> list[TierResolution]:
    """Report per-tier configured/found/missing/excluded key sets.

    Production predictor tiers are A/B/C. ``experimental`` and
    ``excluded`` also appear, but their missing-key checks are informational
    only.
    """
    plans = [
        ('A', TIER_A, 'production'),
        ('B', TIER_A + TIER_B_ADDITIONAL, 'production'),
        ('C', TIER_A + TIER_B_ADDITIONAL + TIER_C_ADDITIONAL, 'production'),
        ('experimental', EXPERIMENTAL_KEYS, 'informational'),
        ('excluded', EXCLUDED_KEYS, 'informational'),
    ]
    monthly_columns = set(dataset.monthly.columns)
    key_to_field = dataset.clean_field_by_key
    resolutions: list[TierResolution] = []
    strict_missing: dict[str, list[str]] = {}
    for tier, configured, kind in plans:
        found_keys: list[str] = []
        missing_keys: list[str] = []
        excluded_keys: list[str] = []
        found_fields: list[str] = []
        for key in configured:
            if kind == 'informational' or key in EXPERIMENTAL_KEYS or key in EXCLUDED_KEYS:
                excluded_keys.append(key) if kind == 'production' else None
                if kind != 'production':
                    # Informational tier still records found/missing so the
                    # operator can see coverage over the experimental block.
                    field = key_to_field.get(key)
                    if field and field in monthly_columns:
                        found_keys.append(key)
                        found_fields.append(field)
                    else:
                        missing_keys.append(key)
                continue
            field = key_to_field.get(key)
            if field is None:
                missing_keys.append(key)
                continue
            if field in monthly_columns:
                found_keys.append(key)
                found_fields.append(field)
            else:
                missing_keys.append(key)
        resolutions.append(TierResolution(
            tier=tier, kind=kind,
            configured_keys=tuple(configured), found_keys=tuple(found_keys),
            missing_keys=tuple(missing_keys), excluded_keys=tuple(excluded_keys),
            found_fields=tuple(found_fields),
        ))
        if kind == 'production' and missing_keys:
            strict_missing[tier] = missing_keys
    if strict and strict_missing:
        detail = '; '.join(f'{tier}: {keys}' for tier, keys in strict_missing.items())
        message = (f'Phase 4A.1 strict tier resolution: expected predictors '
                    f'missing from the master ({detail}). Run '
                    f"'python -m uznowcast.cli build --scope v1' or pass "
                    f'--allow-missing to proceed anyway.')
        raise MissingTierVariables(message)
    if strict_missing:
        warnings.warn(f'Phase 4A.1 production tiers have missing predictors: {strict_missing}')
    return resolutions


# --- Frozen validation set --------------------------------------------------


HOLDOUT_QUARTERS: int = 4


@dataclass(frozen=True)
class FrozenValidation:
    holdout_quarters: tuple[str, ...]
    development_quarters: tuple[str, ...]

    def to_dict(self) -> dict:
        return dict(
            holdout_quarters=list(self.holdout_quarters),
            development_quarters=list(self.development_quarters),
            holdout_count=len(self.holdout_quarters),
            development_count=len(self.development_quarters),
            rule=('the last 4 GDP quarters are reserved and never used '
                  'for specification/predictor/factor/lag/robust selection'),
        )


def freeze_validation(dataset: ModelingDataset,
                      *, holdout: int = HOLDOUT_QUARTERS) -> FrozenValidation:
    """Reserve the last ``holdout`` GDP quarters as an unopened validation set.

    The Phase 4A.1 evaluator only runs on the development quarters
    (everything strictly before the holdout). Any attempt to smuggle a
    holdout quarter into the training or evaluation loop raises.
    """
    quarters = dataset.gdp['quarter'].astype(str).tolist()
    if len(quarters) <= holdout:
        return FrozenValidation(holdout_quarters=tuple(),
                                development_quarters=tuple(quarters))
    holdout_slice = tuple(quarters[-holdout:])
    development = tuple(quarters[:-holdout])
    return FrozenValidation(holdout_quarters=holdout_slice,
                            development_quarters=development)


# --- Effective-training thresholds ------------------------------------------


PRIMARY_MIN_ROWS: int = 12
"""Absolute floor on the effective training rows for the primary run."""

SMALL_SAMPLE_MIN_ROWS: int = 8
"""Number of quarters used only for the small-sample sensitivity run."""


def minimum_effective_rows(free_parameters: int) -> int:
    return max(PRIMARY_MIN_ROWS, 3 * int(free_parameters))
