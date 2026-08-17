from __future__ import annotations

import random

from market.lob import Side
from order_flow.noise_traders import MarketOrder, _poisson


class InformedTraderFlow:
    def __init__(self, intensity: float, max_order_size: int = 3, seed: int | None = None) -> None:
        self.intensity = intensity
        self.max_order_size = max_order_size
        self.rng = random.Random(seed)

    def sample(
        self,
        dt: float,
        timestamp: int,
        future_return: float,
        jump_flag: bool,
    ) -> list[MarketOrder]:
        if not jump_flag and abs(future_return) < 1e-9:
            return []
        lam = self.intensity * dt * (4.0 if jump_flag else 1.0)
        count = _poisson(self.rng, lam)
        side: Side = "buy" if future_return > 0 else "sell"
        return [
            MarketOrder(
                side=side,
                quantity=self.rng.randint(1, self.max_order_size),
                trader_id=f"informed_{timestamp}_{i}",
                informed=True,
            )
            for i in range(count)
        ]
