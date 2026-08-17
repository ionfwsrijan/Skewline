from __future__ import annotations

from dataclasses import dataclass

from agents.base_agent import AgentContext, BaseAgent, Quote, enforce_non_crossing


@dataclass
class HedgedMultiAssetAgent(BaseAgent):
    base_spread_bps: float = 7.0
    hedge_ratio: float = 0.75
    hedge_threshold: int = 5
    hedge_fee_bps: float = 0.8
    order_size: int = 1
    agent_id: str = "hedged_multi_asset"
    hedge_inventory: float = 0.0
    hedge_cash: float = 0.0

    def quote(self, context: AgentContext) -> Quote:
        beta = context.hedge_beta or self.hedge_ratio
        hedge_price = context.hedge_mid_price or context.mid_price
        desired_hedge = -beta * context.inventory
        if abs(desired_hedge - self.hedge_inventory) >= self.hedge_threshold:
            trade = desired_hedge - self.hedge_inventory
            fee = abs(trade) * hedge_price * self.hedge_fee_bps / 10_000.0
            self.hedge_cash -= trade * hedge_price + fee
            self.hedge_inventory += trade
        half = context.mid_price * self.base_spread_bps / 20_000.0
        hedge_pressure = (context.inventory + self.hedge_inventory / max(abs(beta), 1e-9)) * 0.02
        bid, ask = enforce_non_crossing(
            context.mid_price,
            context.mid_price - half - hedge_pressure,
            context.mid_price + half - hedge_pressure,
        )
        return Quote(bid, ask, self.order_size, self.order_size)

    def hedge_value(self, mid_price: float, hedge_mid_price: float | None = None) -> float:
        hedge_price = hedge_mid_price or mid_price
        return self.hedge_cash + self.hedge_inventory * hedge_price
