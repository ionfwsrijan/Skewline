from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from agents.base_agent import AgentContext, BaseAgent, Quote, enforce_non_crossing
from order_flow.noise_traders import MarketOrder


@dataclass
class FlowImbalanceAgent(BaseAgent):
    base_spread_bps: float = 8.0
    skew_multiplier: float = 0.8
    widen_multiplier: float = 1.2
    signal_window: int = 25
    order_size: int = 1
    agent_id: str = "flow_imbalance"
    _signed_flow: deque[int] = field(default_factory=deque, init=False)

    def observe_order_flow(self, orders: list[MarketOrder]) -> None:
        for order in orders:
            signed = order.quantity if order.side == "buy" else -order.quantity
            self._signed_flow.append(signed)
            while len(self._signed_flow) > self.signal_window:
                self._signed_flow.popleft()

    def quote(self, context: AgentContext) -> Quote:
        imbalance = sum(self._signed_flow) / max(1, sum(abs(x) for x in self._signed_flow))
        base_half = context.mid_price * self.base_spread_bps / 20_000.0
        half_spread = base_half * (1.0 + self.widen_multiplier * abs(imbalance))
        center = context.mid_price + self.skew_multiplier * imbalance * half_spread
        inventory_skew = context.inventory * base_half * 0.05
        bid, ask = enforce_non_crossing(
            context.mid_price,
            center - half_spread - inventory_skew,
            center + half_spread - inventory_skew,
        )
        return Quote(bid, ask, self.order_size, self.order_size)
