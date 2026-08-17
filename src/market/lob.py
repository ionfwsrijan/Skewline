from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from itertools import count
import random
from typing import Deque, Literal

Side = Literal["buy", "sell"]


@dataclass
class LimitOrder:
    agent_id: str
    side: Side
    price: float
    quantity: int
    timestamp: int
    order_id: int = field(default=0)


@dataclass(frozen=True)
class Fill:
    maker_agent_id: str
    taker_agent_id: str
    price: float
    quantity: int
    maker_side: Side
    taker_side: Side
    timestamp: int


@dataclass(frozen=True)
class BookSnapshot:
    timestamp: int
    best_bid: float | None
    best_ask: float | None
    bid_depth: int
    ask_depth: int
    spread: float | None


class LimitOrderBook:
    """Simplified price-time-priority limit order book."""

    def __init__(self, tick_size: float = 0.01) -> None:
        self.tick_size = tick_size
        self.bids: dict[float, Deque[LimitOrder]] = defaultdict(deque)
        self.asks: dict[float, Deque[LimitOrder]] = defaultdict(deque)
        self._ids = count(1)
        self._orders: dict[int, LimitOrder] = {}

    def add_limit_order(self, order: LimitOrder) -> int:
        if order.quantity <= 0:
            raise ValueError("Order quantity must be positive.")
        order.price = self._round_price(order.price)
        order.order_id = next(self._ids)
        book_side = self.bids if order.side == "buy" else self.asks
        book_side[order.price].append(order)
        self._orders[order.order_id] = order
        return order.order_id

    def submit_limit_order(self, order: LimitOrder) -> tuple[int | None, list[Fill]]:
        """Submit a limit order, executing immediately if it crosses the book."""
        fills: list[Fill] = []
        remaining = order.quantity
        if order.side == "buy":
            while remaining > 0 and self.asks and min(self.asks) <= order.price:
                price = min(self.asks)
                fills.extend(
                    self._consume_price_level(
                        self.asks,
                        price,
                        order.agent_id,
                        "buy",
                        remaining,
                        order.timestamp,
                    )
                )
                remaining = order.quantity - sum(fill.quantity for fill in fills)
        else:
            while remaining > 0 and self.bids and max(self.bids) >= order.price:
                price = max(self.bids)
                fills.extend(
                    self._consume_price_level(
                        self.bids,
                        price,
                        order.agent_id,
                        "sell",
                        remaining,
                        order.timestamp,
                    )
                )
                remaining = order.quantity - sum(fill.quantity for fill in fills)
        if remaining <= 0:
            return None, fills
        order.quantity = remaining
        return self.add_limit_order(order), fills

    def cancel_agent_orders(self, agent_id: str) -> int:
        removed = 0
        for book_side in (self.bids, self.asks):
            for price in list(book_side.keys()):
                queue = deque(order for order in book_side[price] if order.agent_id != agent_id)
                removed += len(book_side[price]) - len(queue)
                if queue:
                    book_side[price] = queue
                else:
                    del book_side[price]
        self._orders = {
            oid: order for oid, order in self._orders.items() if order.agent_id != agent_id
        }
        return removed

    def cancel_order(self, order_id: int) -> bool:
        order = self._orders.pop(order_id, None)
        if order is None:
            return False
        book_side = self.bids if order.side == "buy" else self.asks
        queue = book_side.get(order.price)
        if queue is None:
            return False
        book_side[order.price] = deque(o for o in queue if o.order_id != order_id)
        if not book_side[order.price]:
            del book_side[order.price]
        return True

    def match_market_order(
        self,
        taker_agent_id: str,
        side: Side,
        quantity: int,
        timestamp: int,
    ) -> list[Fill]:
        fills: list[Fill] = []
        resting_book = self.asks if side == "buy" else self.bids
        while quantity > 0 and resting_book:
            price = min(resting_book) if side == "buy" else max(resting_book)
            step_fills = self._consume_price_level(
                resting_book,
                price,
                taker_agent_id,
                side,
                quantity,
                timestamp,
            )
            fills.extend(step_fills)
            quantity -= sum(fill.quantity for fill in step_fills)
        return fills

    def cancel_stale_orders(
        self,
        now: int,
        max_age_steps: int,
        agent_id: str | None = None,
    ) -> int:
        removed = 0
        for book_side in (self.bids, self.asks):
            for price in list(book_side.keys()):
                keep: Deque[LimitOrder] = deque()
                for order in book_side[price]:
                    is_target = agent_id is None or order.agent_id == agent_id
                    is_stale = now - order.timestamp > max_age_steps
                    if is_target and is_stale:
                        self._orders.pop(order.order_id, None)
                        removed += 1
                    else:
                        keep.append(order)
                if keep:
                    book_side[price] = keep
                else:
                    del book_side[price]
        return removed

    def seed_liquidity_around_mid(
        self,
        mid_price: float,
        timestamp: int,
        levels: int = 5,
        quantity: int = 25,
        half_spread_bps: float = 4.0,
        agent_id: str = "external_liquidity",
        jitter: float = 0.0,
        rng: random.Random | None = None,
    ) -> None:
        rng = rng or random.Random(0)
        half_spread = max(self.tick_size, mid_price * half_spread_bps / 20_000.0)
        for level in range(levels):
            extra = level * self.tick_size
            size = max(1, int(quantity * (1.0 + 0.15 * level)))
            if jitter:
                size = max(1, int(size * (1.0 + rng.uniform(-jitter, jitter))))
            self.add_limit_order(
                LimitOrder(agent_id, "buy", mid_price - half_spread - extra, size, timestamp)
            )
            self.add_limit_order(
                LimitOrder(agent_id, "sell", mid_price + half_spread + extra, size, timestamp)
            )

    def best_bid(self) -> float | None:
        return max(self.bids) if self.bids else None

    def best_ask(self) -> float | None:
        return min(self.asks) if self.asks else None

    def mid_price(self, fallback: float) -> float:
        bid = self.best_bid()
        ask = self.best_ask()
        if bid is not None and ask is not None:
            return (bid + ask) / 2
        return fallback

    def depth(self, side: Side, levels: int = 5) -> list[tuple[float, int]]:
        book_side = self.bids if side == "buy" else self.asks
        prices = sorted(book_side.keys(), reverse=side == "buy")[:levels]
        return [(price, sum(order.quantity for order in book_side[price])) for price in prices]

    def total_depth(self, side: Side) -> int:
        book_side = self.bids if side == "buy" else self.asks
        return sum(order.quantity for queue in book_side.values() for order in queue)

    def snapshot(self, timestamp: int) -> BookSnapshot:
        bid = self.best_bid()
        ask = self.best_ask()
        spread = ask - bid if bid is not None and ask is not None else None
        return BookSnapshot(
            timestamp=timestamp,
            best_bid=bid,
            best_ask=ask,
            bid_depth=self.total_depth("buy"),
            ask_depth=self.total_depth("sell"),
            spread=spread,
        )

    def _consume_price_level(
        self,
        book_side: dict[float, Deque[LimitOrder]],
        price: float,
        taker_agent_id: str,
        taker_side: Side,
        quantity: int,
        timestamp: int,
    ) -> list[Fill]:
        fills: list[Fill] = []
        queue = book_side[price]
        while quantity > 0 and queue:
            maker = queue[0]
            fill_qty = min(quantity, maker.quantity)
            maker.quantity -= fill_qty
            quantity -= fill_qty
            fills.append(
                Fill(
                    maker_agent_id=maker.agent_id,
                    taker_agent_id=taker_agent_id,
                    price=price,
                    quantity=fill_qty,
                    maker_side=maker.side,
                    taker_side=taker_side,
                    timestamp=timestamp,
                )
            )
            if maker.quantity == 0:
                self._orders.pop(maker.order_id, None)
                queue.popleft()
        if not queue:
            del book_side[price]
        return fills

    def _round_price(self, price: float) -> float:
        return round(round(price / self.tick_size) * self.tick_size, 10)
