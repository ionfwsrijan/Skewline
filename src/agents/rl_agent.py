from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import random

from agents.base_agent import AgentContext, BaseAgent, Quote, enforce_non_crossing


@dataclass
class TabularRLAgent(BaseAgent):
    """Tabular Q-learning market maker with discrete spread actions."""

    epsilon: float = 0.05
    alpha: float = 0.05
    gamma_discount: float = 0.95
    order_size: int = 1
    agent_id: str = "rl"
    seed: int | None = None
    q_values_path: str | None = None
    q_values: dict[tuple[int, int, int], float] = field(default_factory=dict)
    _last_state_action: tuple[int, int, int] | None = field(default=None, init=False)
    _last_equity: float | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        if self.q_values_path:
            self.load_q_values(self.q_values_path)

    def quote(self, context: AgentContext) -> Quote:
        state = self._state(context.inventory, context.volatility)
        action = self._choose_action(state)
        self._last_state_action = (*state, action)
        self._last_equity = context.cash + context.inventory * context.mid_price
        spread_bps = [5.0, 9.0, 15.0][action]
        half = context.mid_price * spread_bps / 20_000.0
        center = context.mid_price - state[0] * half * 0.3
        bid, ask = enforce_non_crossing(context.mid_price, center - half, center + half)
        return Quote(bid, ask, self.order_size, self.order_size)

    def learn(self, equity: float, inventory: int, volatility: float) -> None:
        if self._last_state_action is None or self._last_equity is None:
            return
        next_state = self._state(inventory, volatility)
        reward = equity - self._last_equity - 0.002 * abs(inventory)
        old_value = self.q_values.get(self._last_state_action, 0.0)
        next_best = max(self.q_values.get((*next_state, action), 0.0) for action in (0, 1, 2))
        self.q_values[self._last_state_action] = old_value + self.alpha * (
            reward + self.gamma_discount * next_best - old_value
        )

    def _choose_action(self, state: tuple[int, int]) -> int:
        best_action = max(
            (0, 1, 2),
            key=lambda action: self.q_values.get((*state, action), 0.0),
        )
        if self._rng.random() < self.epsilon:
            return self._rng.choice([0, 1, 2])
        return best_action

    @staticmethod
    def _state(inventory: int, volatility: float) -> tuple[int, int]:
        inventory_bucket = max(-3, min(3, round(inventory / 5)))
        vol_bucket = 1 if volatility > 0.25 else 0
        return inventory_bucket, vol_bucket

    def save_q_values(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"|".join(map(str, key)): value for key, value in self.q_values.items()}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def load_q_values(self, path: str | Path) -> None:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self.q_values = {
            tuple(int(part) for part in key.split("|")): float(value)
            for key, value in raw.items()
        }
