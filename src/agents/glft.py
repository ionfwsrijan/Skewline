from __future__ import annotations

from dataclasses import dataclass
import math

from agents.base_agent import AgentContext, BaseAgent, Quote, enforce_non_crossing


@dataclass
class GLFTAgent(BaseAgent):
    gamma: float = 0.06
    kappa: float = 1.4
    inventory_penalty: float = 0.015
    max_inventory: int = 50
    order_size: int = 1
    agent_id: str = "glft"

    def quote(self, context: AgentContext) -> Quote:
        inventory_ratio = context.inventory / max(1, self.max_inventory)
        half_spread = (
            math.log(1.0 + self.gamma / self.kappa) / self.gamma
            + self.inventory_penalty * abs(inventory_ratio)
            + 0.5 * self.gamma * context.volatility**2 * context.dt
        )
        center = context.mid_price - inventory_ratio * half_spread
        bid_size = self.order_size if context.inventory < self.max_inventory else 0
        ask_size = self.order_size if context.inventory > -self.max_inventory else 0
        bid, ask = enforce_non_crossing(context.mid_price, center - half_spread, center + half_spread)
        return Quote(bid, ask, bid_size, ask_size)
