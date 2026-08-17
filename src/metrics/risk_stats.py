from __future__ import annotations

import math


def returns_from_equity(equity_curve: list[float]) -> list[float]:
    return [
        (equity_curve[i] - equity_curve[i - 1]) / abs(equity_curve[i - 1])
        for i in range(1, len(equity_curve))
        if abs(equity_curve[i - 1]) > 1e-12
    ]


def sharpe_ratio(equity_curve: list[float], periods_per_year: float = 252.0) -> float:
    returns = returns_from_equity(equity_curve)
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    stdev = math.sqrt(sum((r - mean) ** 2 for r in returns) / (len(returns) - 1))
    return mean / stdev * math.sqrt(periods_per_year) if stdev else 0.0


def sortino_ratio(equity_curve: list[float], periods_per_year: float = 252.0) -> float:
    returns = returns_from_equity(equity_curve)
    if not returns:
        return 0.0
    mean = sum(returns) / len(returns)
    downside = [min(0.0, r) for r in returns]
    downside_dev = math.sqrt(sum(r * r for r in downside) / len(downside))
    return mean / downside_dev * math.sqrt(periods_per_year) if downside_dev else 0.0


def max_drawdown(equity_curve: list[float]) -> float:
    peak = equity_curve[0] if equity_curve else 0.0
    drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def value_at_risk(equity_curve: list[float], alpha: float = 0.05) -> float:
    pnl_changes = [equity_curve[i] - equity_curve[i - 1] for i in range(1, len(equity_curve))]
    if not pnl_changes:
        return 0.0
    losses = sorted(-change for change in pnl_changes)
    index = min(len(losses) - 1, max(0, int((1.0 - alpha) * len(losses)) - 1))
    return losses[index]


def conditional_value_at_risk(equity_curve: list[float], alpha: float = 0.05) -> float:
    pnl_changes = [equity_curve[i] - equity_curve[i - 1] for i in range(1, len(equity_curve))]
    if not pnl_changes:
        return 0.0
    losses = sorted(-change for change in pnl_changes)
    index = min(len(losses) - 1, max(0, int((1.0 - alpha) * len(losses)) - 1))
    tail = losses[index:]
    return sum(tail) / len(tail)


def hit_rate(equity_curve: list[float]) -> float:
    pnl_changes = [equity_curve[i] - equity_curve[i - 1] for i in range(1, len(equity_curve))]
    if not pnl_changes:
        return 0.0
    return sum(1 for change in pnl_changes if change > 0) / len(pnl_changes)


def summarize_risk(equity_curve: list[float], inventory_curve: list[int], fills: int) -> dict[str, float]:
    return {
        "sharpe": sharpe_ratio(equity_curve),
        "sortino": sortino_ratio(equity_curve),
        "max_drawdown": max_drawdown(equity_curve),
        "var_95": value_at_risk(equity_curve, alpha=0.05),
        "cvar_95": conditional_value_at_risk(equity_curve, alpha=0.05),
        "hit_rate": hit_rate(equity_curve),
        "max_inventory": float(max((abs(x) for x in inventory_curve), default=0)),
        "fill_count": float(fills),
        "fill_rate": fills / max(1, len(equity_curve)),
    }
