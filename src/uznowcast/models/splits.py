"""Expanding-window pseudo-out-of-sample splits over quarterly GDP."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence


@dataclass(frozen=True)
class Split:
    """One expanding-window step.

    ``train`` is the sequence of quarter labels the model may fit on;
    ``target`` is the single next quarter it must forecast. The model is
    forbidden from touching any quarter after ``target``.
    """

    train: tuple[str, ...]
    target: str


def expanding_window(quarters: Sequence[str], *, min_train: int) -> list[Split]:
    """Yield expanding-window splits.

    ``quarters`` must be a chronologically sorted sequence of quarter
    labels. ``min_train`` is the smallest training-sample size a model
    demands. The first ``Split`` therefore trains on
    ``quarters[:min_train]`` and forecasts ``quarters[min_train]``.
    """
    if min_train < 1:
        raise ValueError('min_train must be at least 1')
    if len(quarters) <= min_train:
        return []
    splits = []
    for stop in range(min_train, len(quarters)):
        splits.append(Split(train=tuple(quarters[:stop]), target=quarters[stop]))
    return splits


def first_evaluation_quarter(splits: list[Split]) -> str | None:
    return splits[0].target if splits else None


def evaluation_span(splits: list[Split]) -> tuple[str | None, str | None]:
    if not splits:
        return None, None
    return splits[0].target, splits[-1].target
