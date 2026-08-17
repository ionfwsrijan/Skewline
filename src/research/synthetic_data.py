from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import random

from market.price_process import PriceProcessParams, simulate_jump_diffusion


def write_synthetic_l1_csv(
    output: str | Path,
    steps: int = 3600,
    seed: int = 42,
    initial_price: float = 100.0,
    sigma: float = 0.18,
    spread_bps: float = 3.0,
    dt_seconds: float = 1.0,
) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    path = simulate_jump_diffusion(
        steps,
        PriceProcessParams(
            initial_price=initial_price,
            sigma=sigma,
            jump_intensity=0.0008,
            jump_mean=0.0,
            jump_std=0.006,
            dt=dt_seconds / (365.0 * 24.0 * 60.0 * 60.0),
        ),
        seed=seed,
    )
    start = datetime(2024, 1, 2, 14, 30, tzinfo=timezone.utc)
    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["timestamp", "bid", "ask", "price", "quantity"])
        writer.writeheader()
        for i, price in enumerate(path.prices[:-1]):
            dynamic_spread = price * spread_bps / 10_000.0 * (1.0 + rng.random() * 0.5)
            bid = price - dynamic_spread / 2.0
            ask = price + dynamic_spread / 2.0
            writer.writerow(
                {
                    "timestamp": (start + timedelta(seconds=i * dt_seconds)).isoformat(),
                    "bid": f"{bid:.6f}",
                    "ask": f"{ask:.6f}",
                    "price": f"{price:.6f}",
                    "quantity": rng.randint(1, 10),
                }
            )
    return output
