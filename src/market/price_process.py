from __future__ import annotations

from dataclasses import dataclass
import math
import random


@dataclass(frozen=True)
class PriceProcessParams:
    initial_price: float = 100.0
    drift: float = 0.0
    sigma: float = 0.2
    jump_intensity: float = 0.0
    jump_mean: float = 0.0
    jump_std: float = 0.0
    dt: float = 1 / 252


@dataclass(frozen=True)
class PricePath:
    prices: list[float]
    returns: list[float]
    jump_flags: list[bool]


def price_path_from_prices(prices: list[float], jump_z: float = 4.0) -> PricePath:
    if len(prices) < 2:
        raise ValueError("Need at least two prices to build a price path.")
    clean = [max(0.01, float(price)) for price in prices]
    returns = [math.log(clean[i] / clean[i - 1]) for i in range(1, len(clean))]
    mean = sum(returns) / len(returns)
    variance = sum((ret - mean) ** 2 for ret in returns) / max(1, len(returns) - 1)
    stdev = math.sqrt(max(variance, 1e-12))
    jump_flags = [abs(ret - mean) > jump_z * stdev for ret in returns]
    return PricePath(prices=clean, returns=returns, jump_flags=jump_flags)


def simulate_jump_diffusion(
    steps: int,
    params: PriceProcessParams,
    seed: int | None = None,
) -> PricePath:
    rng = random.Random(seed)
    prices = [float(params.initial_price)]
    returns: list[float] = []
    jump_flags: list[bool] = []
    for _ in range(steps):
        diffusion = (
            (params.drift - 0.5 * params.sigma**2) * params.dt
            + params.sigma * math.sqrt(params.dt) * rng.gauss(0.0, 1.0)
        )
        jump = 0.0
        jumped = rng.random() < params.jump_intensity * params.dt
        if jumped:
            jump = rng.gauss(params.jump_mean, params.jump_std)
        log_return = diffusion + jump
        prices.append(max(0.01, prices[-1] * math.exp(log_return)))
        returns.append(log_return)
        jump_flags.append(jumped)
    return PricePath(prices=prices, returns=returns, jump_flags=jump_flags)


def method_of_moments_fit(prices: list[float], dt: float, jump_z: float = 3.0) -> PriceProcessParams:
    if len(prices) < 3:
        raise ValueError("Need at least 3 prices to calibrate a process.")
    returns = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices)) if prices[i - 1] > 0]
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / max(1, len(returns) - 1)
    stdev = math.sqrt(max(variance, 1e-12))
    jumps = [r for r in returns if abs(r - mean) > jump_z * stdev]
    diffusion_returns = [r for r in returns if r not in jumps] or returns
    diffusion_mean = sum(diffusion_returns) / len(diffusion_returns)
    diffusion_var = sum((r - diffusion_mean) ** 2 for r in diffusion_returns) / max(
        1, len(diffusion_returns) - 1
    )
    jump_mean = sum(jumps) / len(jumps) if jumps else 0.0
    jump_std = (
        math.sqrt(sum((j - jump_mean) ** 2 for j in jumps) / max(1, len(jumps) - 1))
        if len(jumps) > 1
        else 0.0
    )
    return PriceProcessParams(
        initial_price=prices[0],
        drift=diffusion_mean / dt + 0.5 * diffusion_var / dt,
        sigma=math.sqrt(diffusion_var / dt),
        jump_intensity=len(jumps) / (len(returns) * dt),
        jump_mean=jump_mean,
        jump_std=jump_std,
        dt=dt,
    )
