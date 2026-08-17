from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import random

from market.lob import LimitOrder


@dataclass(frozen=True)
class DelayedOrder:
    release_time: int
    order: LimitOrder


class LatencyQueue:
    def __init__(
        self,
        latency_steps: int = 0,
        jitter_steps: int = 0,
        spike_probability: float = 0.0,
        spike_steps: int = 0,
        seed: int | None = None,
    ) -> None:
        self.latency_steps = max(0, int(latency_steps))
        self.jitter_steps = max(0, int(jitter_steps))
        self.spike_probability = max(0.0, min(1.0, float(spike_probability)))
        self.spike_steps = max(0, int(spike_steps))
        self.rng = random.Random(seed)
        self._orders: dict[int, list[LimitOrder]] = defaultdict(list)
        self.last_delay_steps = 0

    def submit(self, now: int, order: LimitOrder) -> None:
        delay = self.sample_delay()
        self.last_delay_steps = delay
        self._orders[now + delay].append(order)

    def release(self, now: int) -> list[LimitOrder]:
        return self._orders.pop(now, [])

    def sample_delay(self) -> int:
        jitter = self.rng.randint(0, self.jitter_steps) if self.jitter_steps else 0
        spike = self.spike_steps if self.rng.random() < self.spike_probability else 0
        return self.latency_steps + jitter + spike
