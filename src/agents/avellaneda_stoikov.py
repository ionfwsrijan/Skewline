from __future__ import annotations

from dataclasses import dataclass
import math

from agents.base_agent import AgentContext, BaseAgent, Quote, enforce_non_crossing


@dataclass
class AvellanedaStoikovAgent(BaseAgent):
    gamma: float = 0.08
    kappa: float = 1.5
    order_size: int = 1
    agent_id: str = "avellaneda_stoikov"

    def quote(self, context: AgentContext) -> Quote:
        horizon = max(context.remaining_steps * context.dt, context.dt)
        reservation_price = (
            context.mid_price
            - context.inventory * self.gamma * context.volatility**2 * horizon
        )
        optimal_half_spread = (
            0.5 * self.gamma * context.volatility**2 * horizon
            + math.log(1.0 + self.gamma / self.kappa) / self.gamma
        )
        bid, ask = enforce_non_crossing(
            context.mid_price,
            reservation_price - optimal_half_spread,
            reservation_price + optimal_half_spread,
        )
        return Quote(bid, ask, self.order_size, self.order_size)
