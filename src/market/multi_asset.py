from __future__ import annotations

from dataclasses import dataclass
import math
import random

from market.price_process import PricePath, PriceProcessParams


@dataclass(frozen=True)
class CorrelatedPricePaths:
    primary: PricePath
    hedge: PricePath
    correlation: float
    beta: float


def simulate_correlated_paths(
    steps: int,
    primary_params: PriceProcessParams,
    hedge_params: PriceProcessParams,
    correlation: float,
    beta: float = 1.0,
    seed: int | None = None,
) -> CorrelatedPricePaths:
    if not -1.0 <= correlation <= 1.0:
        raise ValueError("correlation must be in [-1, 1]")
    rng = random.Random(seed)
    primary_prices = [float(primary_params.initial_price)]
    hedge_prices = [float(hedge_params.initial_price)]
    primary_returns: list[float] = []
    hedge_returns: list[float] = []
    primary_jumps: list[bool] = []
    hedge_jumps: list[bool] = []
    orthogonal_scale = math.sqrt(max(0.0, 1.0 - correlation**2))
    for _ in range(steps):
        z_primary = rng.gauss(0.0, 1.0)
        z_hedge = correlation * z_primary + orthogonal_scale * rng.gauss(0.0, 1.0)
        primary_jump, primary_jumped = _jump_component(rng, primary_params)
        hedge_jump, hedge_jumped = _jump_component(rng, hedge_params)
        primary_ret = (
            (primary_params.drift - 0.5 * primary_params.sigma**2) * primary_params.dt
            + primary_params.sigma * math.sqrt(primary_params.dt) * z_primary
            + primary_jump
        )
        hedge_ret = (
            (hedge_params.drift - 0.5 * hedge_params.sigma**2) * hedge_params.dt
            + hedge_params.sigma * math.sqrt(hedge_params.dt) * z_hedge
            + beta * hedge_jump
        )
        primary_prices.append(max(0.01, primary_prices[-1] * math.exp(primary_ret)))
        hedge_prices.append(max(0.01, hedge_prices[-1] * math.exp(hedge_ret)))
        primary_returns.append(primary_ret)
        hedge_returns.append(hedge_ret)
        primary_jumps.append(primary_jumped)
        hedge_jumps.append(hedge_jumped)
    return CorrelatedPricePaths(
        primary=PricePath(primary_prices, primary_returns, primary_jumps),
        hedge=PricePath(hedge_prices, hedge_returns, hedge_jumps),
        correlation=correlation,
        beta=estimate_hedge_beta(primary_returns, hedge_returns) if hedge_returns else beta,
    )


def estimate_hedge_beta(primary_returns: list[float], hedge_returns: list[float]) -> float:
    n = min(len(primary_returns), len(hedge_returns))
    if n < 2:
        return 0.0
    x = hedge_returns[:n]
    y = primary_returns[:n]
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    var_x = sum((value - mean_x) ** 2 for value in x)
    cov_xy = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    return cov_xy / var_x if var_x else 0.0


def estimate_correlation(left_returns: list[float], right_returns: list[float]) -> float:
    n = min(len(left_returns), len(right_returns))
    if n < 2:
        return 0.0
    left = left_returns[:n]
    right = right_returns[:n]
    mean_left = sum(left) / n
    mean_right = sum(right) / n
    cov = sum((left[i] - mean_left) * (right[i] - mean_right) for i in range(n))
    var_left = sum((value - mean_left) ** 2 for value in left)
    var_right = sum((value - mean_right) ** 2 for value in right)
    denom = math.sqrt(var_left * var_right)
    return cov / denom if denom else 0.0


def _jump_component(rng: random.Random, params: PriceProcessParams) -> tuple[float, bool]:
    jumped = rng.random() < params.jump_intensity * params.dt
    if not jumped:
        return 0.0, False
    return rng.gauss(params.jump_mean, params.jump_std), True
