from __future__ import annotations

from dataclasses import dataclass, asdict
import csv
import math
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class OrderFlowCalibration:
    buy_intensity: float
    sell_intensity: float
    total_intensity: float
    mean_order_size: float
    buy_sell_imbalance: float
    signed_flow_autocorr: float
    toxicity_proxy: float
    fill_decay_kappa: float
    observations: int


def calibrate_order_flow(
    timestamps: Iterable[float],
    sides: Iterable[str],
    quantities: Iterable[float],
    prices: Iterable[float] | None = None,
    mid_prices: Iterable[float] | None = None,
) -> OrderFlowCalibration:
    ts = [float(value) for value in timestamps]
    side_values = [str(side).lower() for side in sides]
    qty = [float(value) for value in quantities]
    if not (len(ts) == len(side_values) == len(qty)):
        raise ValueError("timestamps, sides, and quantities must have equal lengths")
    if not ts:
        return OrderFlowCalibration(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)
    duration = max(1e-9, max(ts) - min(ts))
    buy_qty = sum(size for side, size in zip(side_values, qty) if side == "buy")
    sell_qty = sum(size for side, size in zip(side_values, qty) if side == "sell")
    buy_count = sum(1 for side in side_values if side == "buy")
    sell_count = sum(1 for side in side_values if side == "sell")
    signed = [size if side == "buy" else -size for side, size in zip(side_values, qty)]
    toxicity = _toxicity_proxy(signed, prices, mid_prices)
    kappa = _fill_decay_kappa(prices, mid_prices)
    return OrderFlowCalibration(
        buy_intensity=buy_count / duration,
        sell_intensity=sell_count / duration,
        total_intensity=(buy_count + sell_count) / duration,
        mean_order_size=sum(qty) / len(qty),
        buy_sell_imbalance=(buy_qty - sell_qty) / max(1e-9, buy_qty + sell_qty),
        signed_flow_autocorr=_lag1_autocorr(signed),
        toxicity_proxy=toxicity,
        fill_decay_kappa=kappa,
        observations=len(ts),
    )


def calibrate_order_flow_csv(
    path: str | Path,
    timestamp_col: str = "timestamp",
    side_col: str = "side",
    quantity_col: str = "quantity",
    price_col: str = "price",
    mid_col: str = "mid",
) -> OrderFlowCalibration:
    rows = list(csv.DictReader(Path(path).open("r", newline="", encoding="utf-8")))
    if not rows:
        return calibrate_order_flow([], [], [])
    timestamps = [_coerce_timestamp(row[timestamp_col]) for row in rows]
    sides = [_coerce_side(row.get(side_col, ""), row) for row in rows]
    quantities = [float(row.get(quantity_col, 1.0) or 1.0) for row in rows]
    prices = [float(row[price_col]) for row in rows] if price_col in rows[0] else None
    mids = [float(row[mid_col]) for row in rows] if mid_col in rows[0] else None
    return calibrate_order_flow(timestamps, sides, quantities, prices, mids)


def write_order_flow_calibration(path: str | Path, calibration: OrderFlowCalibration) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["metric,value"]
    lines.extend(f"{key},{value}" for key, value in asdict(calibration).items())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _toxicity_proxy(
    signed_flow: list[float],
    prices: Iterable[float] | None,
    mid_prices: Iterable[float] | None,
) -> float:
    if prices is None and mid_prices is None:
        return 0.0
    reference = [float(value) for value in (mid_prices if mid_prices is not None else prices or [])]
    if len(reference) < 2 or len(signed_flow) < 2:
        return 0.0
    future_returns = [reference[i + 1] - reference[i] for i in range(len(reference) - 1)]
    aligned_flow = signed_flow[: len(future_returns)]
    return _correlation(aligned_flow, future_returns)


def _fill_decay_kappa(
    prices: Iterable[float] | None,
    mid_prices: Iterable[float] | None,
) -> float:
    if prices is None or mid_prices is None:
        return 0.0
    distances = [abs(float(price) - float(mid)) / max(1e-9, float(mid)) for price, mid in zip(prices, mid_prices)]
    positive = [distance for distance in distances if distance > 0]
    if not positive:
        return 0.0
    return 1.0 / (sum(positive) / len(positive))


def _lag1_autocorr(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    return _correlation(values[1:], values[:-1])


def _correlation(left: list[float], right: list[float]) -> float:
    n = min(len(left), len(right))
    if n < 2:
        return 0.0
    x = left[:n]
    y = right[:n]
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    var_x = sum((value - mean_x) ** 2 for value in x)
    var_y = sum((value - mean_y) ** 2 for value in y)
    denom = math.sqrt(var_x * var_y)
    return cov / denom if denom else 0.0


def _coerce_timestamp(value: str) -> float:
    try:
        numeric = float(value)
        return numeric / 1000.0 if numeric > 10_000_000_000 else numeric
    except ValueError:
        from datetime import datetime

        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _coerce_side(value: str, row: dict[str, str]) -> str:
    side = value.lower()
    if side in {"buy", "sell"}:
        return side
    if "is_buyer_maker" in row:
        return "sell" if row["is_buyer_maker"].lower() in {"true", "1"} else "buy"
    return "buy"
