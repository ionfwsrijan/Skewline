from __future__ import annotations

from dataclasses import dataclass
import math
import random


@dataclass(frozen=True)
class PairedComparison:
    left: str
    right: str
    mean_difference: float
    t_stat: float
    bootstrap_ci_low: float
    bootstrap_ci_high: float
    probability_left_better: float
    observations: int


def paired_pnl_changes(left_equity: list[float], right_equity: list[float]) -> list[float]:
    n = min(len(left_equity), len(right_equity))
    if n < 2:
        return []
    left_changes = [left_equity[i] - left_equity[i - 1] for i in range(1, n)]
    right_changes = [right_equity[i] - right_equity[i - 1] for i in range(1, n)]
    return [left_changes[i] - right_changes[i] for i in range(len(left_changes))]


def paired_comparison(
    left_name: str,
    left_equity: list[float],
    right_name: str,
    right_equity: list[float],
    bootstrap_samples: int = 500,
    seed: int = 123,
) -> PairedComparison:
    differences = paired_pnl_changes(left_equity, right_equity)
    mean_diff = _mean(differences)
    stdev = _sample_stdev(differences)
    t_stat = mean_diff / (stdev / math.sqrt(len(differences))) if stdev and differences else 0.0
    ci_low, ci_high = bootstrap_mean_ci(differences, bootstrap_samples, seed=seed)
    probability = sum(1 for diff in differences if diff > 0) / len(differences) if differences else 0.0
    return PairedComparison(
        left=left_name,
        right=right_name,
        mean_difference=mean_diff,
        t_stat=t_stat,
        bootstrap_ci_low=ci_low,
        bootstrap_ci_high=ci_high,
        probability_left_better=probability,
        observations=len(differences),
    )


def bootstrap_mean_ci(
    values: list[float],
    samples: int = 500,
    confidence: float = 0.95,
    seed: int = 123,
) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(max(1, samples)):
        draw = [values[rng.randrange(len(values))] for _ in values]
        means.append(_mean(draw))
    means.sort()
    lower_q = (1.0 - confidence) / 2.0
    upper_q = 1.0 - lower_q
    return _quantile(means, lower_q), _quantile(means, upper_q)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _sample_stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    idx = min(len(values) - 1, max(0, round(q * (len(values) - 1))))
    return values[idx]
