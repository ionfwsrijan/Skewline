from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class WalkForwardSplit:
    train_start: int
    train_end: int
    test_start: int
    test_end: int


def make_walk_forward_splits(length: int, train_size: int, test_size: int) -> list[WalkForwardSplit]:
    splits: list[WalkForwardSplit] = []
    start = 0
    while start + train_size + test_size <= length:
        splits.append(
            WalkForwardSplit(start, start + train_size, start + train_size, start + train_size + test_size)
        )
        start += test_size
    return splits


def compare_stats(simulated: dict[str, float], realized: dict[str, float]) -> dict[str, float]:
    keys = sorted(set(simulated) & set(realized))
    return {f"{key}_abs_error": abs(simulated[key] - realized[key]) for key in keys}


def stress_replay(values: Iterable[float], runner: Callable[[list[float]], dict[str, float]]) -> dict[str, float]:
    return runner([float(v) for v in values])
