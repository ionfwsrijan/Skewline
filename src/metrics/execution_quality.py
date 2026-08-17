from __future__ import annotations

from market.lob import Fill


def effective_spread_bps(fills: list[Fill], mid_prices: list[float], agent_id: str) -> float:
    values: list[float] = []
    for fill in fills:
        if fill.maker_agent_id != agent_id and fill.taker_agent_id != agent_id:
            continue
        mid = mid_prices[min(fill.timestamp, len(mid_prices) - 1)]
        if mid <= 0:
            continue
        signed = _signed_side(fill, agent_id)
        values.append(2.0 * signed * (fill.price - mid) / mid * 10_000.0)
    return sum(values) / len(values) if values else 0.0


def realized_spread_bps(
    fills: list[Fill],
    mid_prices: list[float],
    agent_id: str,
    horizon_steps: int = 5,
) -> float:
    values: list[float] = []
    for fill in fills:
        if fill.maker_agent_id != agent_id and fill.taker_agent_id != agent_id:
            continue
        start_mid = mid_prices[min(fill.timestamp, len(mid_prices) - 1)]
        future_mid = mid_prices[min(fill.timestamp + horizon_steps, len(mid_prices) - 1)]
        if start_mid <= 0:
            continue
        signed = _signed_side(fill, agent_id)
        values.append(2.0 * signed * (fill.price - future_mid) / start_mid * 10_000.0)
    return sum(values) / len(values) if values else 0.0


def markout_bps(
    fills: list[Fill],
    mid_prices: list[float],
    agent_id: str,
    horizon_steps: int = 5,
) -> float:
    values: list[float] = []
    for fill in fills:
        if fill.maker_agent_id != agent_id and fill.taker_agent_id != agent_id:
            continue
        mid = mid_prices[min(fill.timestamp, len(mid_prices) - 1)]
        future_mid = mid_prices[min(fill.timestamp + horizon_steps, len(mid_prices) - 1)]
        if mid <= 0:
            continue
        signed_inventory = _signed_inventory_change(fill, agent_id)
        values.append(signed_inventory * (future_mid - fill.price) / mid * 10_000.0)
    return sum(values) / len(values) if values else 0.0


def maker_fill_ratio(fills: list[Fill], agent_id: str) -> float:
    agent_fills = [
        fill
        for fill in fills
        if fill.maker_agent_id == agent_id or fill.taker_agent_id == agent_id
    ]
    if not agent_fills:
        return 0.0
    maker_fills = [fill for fill in agent_fills if fill.maker_agent_id == agent_id]
    return len(maker_fills) / len(agent_fills)


def summarize_execution_quality(
    fills: list[Fill],
    mid_prices: list[float],
    agent_id: str,
) -> dict[str, float]:
    return {
        "effective_spread_bps": effective_spread_bps(fills, mid_prices, agent_id),
        "realized_spread_5_bps": realized_spread_bps(fills, mid_prices, agent_id, 5),
        "markout_5_bps": markout_bps(fills, mid_prices, agent_id, 5),
        "maker_fill_ratio": maker_fill_ratio(fills, agent_id),
    }


def _signed_side(fill: Fill, agent_id: str) -> int:
    if fill.maker_agent_id == agent_id:
        return 1 if fill.maker_side == "sell" else -1
    return 1 if fill.taker_side == "buy" else -1


def _signed_inventory_change(fill: Fill, agent_id: str) -> int:
    if fill.maker_agent_id == agent_id:
        return fill.quantity if fill.maker_side == "buy" else -fill.quantity
    return fill.quantity if fill.taker_side == "buy" else -fill.quantity
