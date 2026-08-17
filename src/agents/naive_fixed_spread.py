from __future__ import annotations

from dataclasses import dataclass

from agents.base_agent import AgentContext, BaseAgent, Quote, enforce_non_crossing


@dataclass
class NaiveFixedSpreadAgent(BaseAgent):
    base_spread_bps: float = 8.0
    order_size: int = 1
    agent_id: str = "naive"

    def quote(self, context: AgentContext) -> Quote:
        half_spread = context.mid_price * self.base_spread_bps / 20_000.0
        bid, ask = enforce_non_crossing(
            context.mid_price,
            context.mid_price - half_spread,
            context.mid_price + half_spread,
        )
        return Quote(bid, ask, self.order_size, self.order_size)
