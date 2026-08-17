from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from market.lob import LimitOrder
from order_flow.noise_traders import MarketOrder


@dataclass
class AgentContext:
    timestamp: int
    mid_price: float
    volatility: float
    inventory: int
    cash: float
    remaining_steps: int
    dt: float
    hedge_mid_price: float | None = None
    hedge_beta: float = 0.0


@dataclass
class Quote:
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int

    def to_orders(self, agent_id: str, timestamp: int) -> list[LimitOrder]:
        orders: list[LimitOrder] = []
        if self.bid_size > 0 and self.bid_price > 0:
            orders.append(
                LimitOrder(agent_id, "buy", self.bid_price, int(self.bid_size), timestamp)
            )
        if self.ask_size > 0 and self.ask_price > 0:
            orders.append(
                LimitOrder(agent_id, "sell", self.ask_price, int(self.ask_size), timestamp)
            )
        return orders


class MarketMakingAgent(Protocol):
    agent_id: str

    def quote(self, context: AgentContext) -> Quote:
        ...

    def observe_order_flow(self, orders: list[MarketOrder]) -> None:
        ...


class BaseAgent:
    agent_id = "base"

    def observe_order_flow(self, orders: list[MarketOrder]) -> None:
        return None


def enforce_non_crossing(mid: float, bid: float, ask: float, tick: float = 0.01) -> tuple[float, float]:
    bid = min(bid, mid - tick)
    ask = max(ask, mid + tick)
    return max(tick, bid), max(tick * 2, ask)
