from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import random

import numpy as np

from agents.base_agent import AgentContext, BaseAgent, Quote, enforce_non_crossing


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0, x)


def _relu_grad(x: np.ndarray) -> np.ndarray:
    return (x > 0).astype(np.float64)


class SmallMLP:
    """Tiny 2-hidden-layer MLP for DQN. No PyTorch/TF dependency."""

    def __init__(self, input_dim: int, hidden: int, output_dim: int, lr: float = 1e-3, seed: int = 0) -> None:
        rng = np.random.RandomState(seed)
        scale1 = np.sqrt(2.0 / input_dim)
        scale2 = np.sqrt(2.0 / hidden)
        self.W1 = rng.randn(input_dim, hidden).astype(np.float64) * scale1
        self.b1 = np.zeros(hidden, dtype=np.float64)
        self.W2 = rng.randn(hidden, hidden).astype(np.float64) * scale2
        self.b2 = np.zeros(hidden, dtype=np.float64)
        self.W3 = rng.randn(hidden, output_dim).astype(np.float64) * np.sqrt(2.0 / hidden)
        self.b3 = np.zeros(output_dim, dtype=np.float64)
        self.lr = lr

    def forward(self, x: np.ndarray) -> tuple[np.ndarray, tuple[np.ndarray, ...]]:
        z1 = x @ self.W1 + self.b1
        a1 = _relu(z1)
        z2 = a1 @ self.W2 + self.b2
        a2 = _relu(z2)
        out = a2 @ self.W3 + self.b3
        return out, (x, z1, a1, z2, a2)

    def train_step(self, x: np.ndarray, target_q: np.ndarray) -> float:
        q_vals, cache = self.forward(x)
        x_in, z1, a1, z2, a2 = cache
        loss = float(np.mean((q_vals - target_q) ** 2))

        d_out = 2.0 * (q_vals - target_q) / len(x)
        dW3 = a2.T @ d_out
        db3 = d_out.sum(axis=0)
        da2 = d_out @ self.W3.T
        dz2 = da2 * _relu_grad(z2)
        dW2 = a1.T @ dz2
        db2 = dz2.sum(axis=0)
        da1 = dz2 @ self.W2.T
        dz1 = da1 * _relu_grad(z1)
        dW1 = x_in.T @ dz1
        db1 = dz1.sum(axis=0)

        self.W3 -= self.lr * dW3
        self.b3 -= self.lr * db3
        self.W2 -= self.lr * dW2
        self.b2 -= self.lr * db2
        self.W1 -= self.lr * dW1
        self.b1 -= self.lr * db1
        return loss


@dataclass
class ReplayBuffer:
    capacity: int = 5000
    buf: list[tuple[np.ndarray, int, float, np.ndarray, bool]] = field(default_factory=list, repr=False)
    pos: int = 0

    def push(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool) -> None:
        transition = (state, action, reward, next_state, done)
        if len(self.buf) < self.capacity:
            self.buf.append(transition)
        else:
            self.buf[self.pos] = transition
        self.pos = (self.pos + 1) % self.capacity

    def sample(self, batch_size: int, rng: random.Random) -> list[tuple[np.ndarray, int, float, np.ndarray, bool]]:
        return rng.sample(self.buf, min(batch_size, len(self.buf)))

    def __len__(self) -> int:
        return len(self.buf)


@dataclass
class DQNAgent(BaseAgent):
    """DQN market maker with experience replay and target network."""

    state_dim: int = 4
    n_actions: int = 5
    hidden: int = 32
    lr: float = 5e-4
    gamma_discount: float = 0.97
    epsilon: float = 0.15
    epsilon_start: float = 0.3
    epsilon_end: float = 0.02
    batch_size: int = 32
    target_update_freq: int = 50
    order_size: int = 1
    agent_id: str = "dqn"
    seed: int | None = None

    _q_net: SmallMLP | None = field(default=None, init=False, repr=False)
    _target_net: SmallMLP | None = field(default=None, init=False, repr=False)
    _replay: ReplayBuffer | None = field(default=None, init=False, repr=False)
    _rng: random.Random | None = field(default=None, init=False, repr=False)
    _last_state: np.ndarray | None = field(default=None, init=False, repr=False)
    _last_action: int | None = field(default=None, init=False, repr=False)
    _last_equity: float | None = field(default=None, init=False, repr=False)
    _step_count: int = field(default=0, init=False, repr=False)
    _spread_actions: list[float] = field(default_factory=lambda: [3.0, 6.0, 9.0, 13.0, 18.0], init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        np_rng = np.random.RandomState(self.seed or 0)
        self._q_net = SmallMLP(self.state_dim, self.hidden, self.n_actions, self.lr, self.seed or 0)
        self._target_net = SmallMLP(self.state_dim, self.hidden, self.n_actions, self.lr, self.seed or 0)
        self._sync_target()
        self._replay = ReplayBuffer(capacity=5000)

    def _sync_target(self) -> None:
        if self._q_net and self._target_net:
            self._target_net.W1 = self._q_net.W1.copy()
            self._target_net.b1 = self._q_net.b1.copy()
            self._target_net.W2 = self._q_net.W2.copy()
            self._target_net.b2 = self._q_net.b2.copy()
            self._target_net.W3 = self._q_net.W3.copy()
            self._target_net.b3 = self._q_net.b3.copy()

    def _get_state(self, ctx: AgentContext) -> np.ndarray:
        inv_norm = ctx.inventory / 20.0
        vol = ctx.volatility
        mid_ret = 0.0
        if hasattr(self, "_prev_mid") and self._prev_mid is not None and self._prev_mid > 0:
            mid_ret = (ctx.mid_price - self._prev_mid) / self._prev_mid
        self._prev_mid = ctx.mid_price
        remaining = ctx.remaining_steps / max(1, ctx.remaining_steps + ctx.timestamp)
        return np.array([inv_norm, vol, mid_ret, remaining], dtype=np.float64)

    def quote(self, context: AgentContext) -> Quote:
        state = self._get_state(context)
        action = self._choose_action(state)
        self._last_state = state
        self._last_action = action
        self._last_equity = context.cash + context.inventory * context.mid_price

        spread_bps = self._spread_actions[action]
        half = context.mid_price * spread_bps / 20_000.0
        skew = -context.inventory * half * 0.15
        center = context.mid_price + skew
        bid, ask = enforce_non_crossing(context.mid_price, center - half, center + half)
        return Quote(bid, ask, self.order_size, self.order_size)

    def learn(self, equity: float, inventory: int, volatility: float) -> None:
        if self._last_state is None or self._last_action is None or self._last_equity is None:
            return
        state = self._last_state
        action = self._last_action
        reward = equity - self._last_equity - 0.001 * abs(inventory)
        next_state = self._get_state(
            AgentContext(0, 0, volatility, inventory, equity, 1, 0.01)
        )
        self._replay.push(state, action, reward, next_state, False)
        self._step_count += 1

        if self._step_count % self.target_update_freq == 0:
            self._sync_target()

        if len(self._replay) >= self.batch_size:
            batch = self._replay.sample(self.batch_size, self._rng)
            s_batch = np.array([t[0] for t in batch])
            a_batch = np.array([t[1] for t in batch])
            r_batch = np.array([t[2] for t in batch])
            ns_batch = np.array([t[3] for t in batch])

            q_next, _ = self._target_net.forward(ns_batch)
            max_q_next = q_next.max(axis=1)
            q_vals, _ = self._q_net.forward(s_batch)
            targets = q_vals.copy()
            for i in range(len(batch)):
                targets[i, a_batch[i]] = r_batch[i] + self.gamma_discount * max_q_next[i]
            self._q_net.train_step(s_batch, targets)

    def _choose_action(self, state: np.ndarray) -> int:
        if self._rng.random() < self.epsilon:
            return self._rng.randrange(self.n_actions)
        q_vals, _ = self._q_net.forward(state.reshape(1, -1))
        return int(np.argmax(q_vals[0]))

    def save_q_values(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "W1": self._q_net.W1.tolist(),
            "b1": self._q_net.b1.tolist(),
            "W2": self._q_net.W2.tolist(),
            "b2": self._q_net.b2.tolist(),
            "W3": self._q_net.W3.tolist(),
            "b3": self._q_net.b3.tolist(),
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def load_q_values(self, path: str | Path) -> None:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        self._q_net.W1 = np.array(payload["W1"])
        self._q_net.b1 = np.array(payload["b1"])
        self._q_net.W2 = np.array(payload["W2"])
        self._q_net.b2 = np.array(payload["b2"])
        self._q_net.W3 = np.array(payload["W3"])
        self._q_net.b3 = np.array(payload["b3"])
        self._sync_target()
