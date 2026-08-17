from __future__ import annotations

from dataclasses import asdict
import math
from pathlib import Path
from typing import Iterable

from market.price_process import PriceProcessParams, method_of_moments_fit


def fit_price_process_from_prices(prices: Iterable[float], dt: float) -> PriceProcessParams:
    return method_of_moments_fit([float(p) for p in prices], dt=dt)


def microstructure_stats(mid_prices: Iterable[float], spreads: Iterable[float]) -> dict[str, float]:
    prices = [float(p) for p in mid_prices]
    spread_values = [float(s) for s in spreads]
    returns = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices)) if prices[i - 1] > 0]
    mean_return = sum(returns) / len(returns) if returns else 0.0
    variance = (
        sum((r - mean_return) ** 2 for r in returns) / max(1, len(returns) - 1)
        if returns
        else 0.0
    )
    autocorr = _lag1_autocorr(returns)
    return {
        "mean_spread": sum(spread_values) / len(spread_values) if spread_values else 0.0,
        "realized_volatility": math.sqrt(max(variance, 0.0)),
        "return_autocorrelation_lag1": autocorr,
        "num_observations": float(len(prices)),
    }


def write_calibration_report(path: str | Path, params: PriceProcessParams, stats: dict[str, float]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["calibration_key,value"]
    for key, value in asdict(params).items():
        lines.append(f"{key},{value}")
    for key, value in stats.items():
        lines.append(f"{key},{value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _lag1_autocorr(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    mean = sum(values) / len(values)
    numerator = sum((values[i] - mean) * (values[i - 1] - mean) for i in range(1, len(values)))
    denominator = sum((v - mean) ** 2 for v in values)
    return numerator / denominator if denominator else 0.0
