from __future__ import annotations

from dataclasses import dataclass
import random

from market.lob import Side


@dataclass(frozen=True)
class MarketOrder:
    side: Side
    quantity: int
    trader_id: str
    informed: bool = False


class NoiseTraderFlow:
    def __init__(self, intensity: float, max_order_size: int = 3, seed: int | None = None) -> None:
        self.intensity = intensity
        self.max_order_size = max_order_size
        self.rng = random.Random(seed)

    def sample(self, dt: float, timestamp: int) -> list[MarketOrder]:
        count = _poisson(self.rng, self.intensity * dt)
        return [
            MarketOrder(
                side="buy" if self.rng.random() < 0.5 else "sell",
                quantity=self.rng.randint(1, self.max_order_size),
                trader_id=f"noise_{timestamp}_{i}",
            )
            for i in range(count)
        ]


def _poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    limit = pow(2.718281828459045, -lam)
    k = 0
    product = 1.0
    while product > limit:
        k += 1
        product *= rng.random()
    return k - 1
