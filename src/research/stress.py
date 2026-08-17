from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import math

from config import deep_merge
from engine.simulation_engine import SimulationEngine, SimulationResult
from market.price_process import price_path_from_prices
from research.reporting import write_comparison_report, write_result_artifacts


@dataclass(frozen=True)
class StressWindow:
    start: int
    end: int
    cumulative_return: float
    realized_volatility: float


@dataclass(frozen=True)
class StressResult:
    window: StressWindow
    simulation: SimulationResult


def find_stress_windows(
    prices: list[float],
    window_size: int,
    top_n: int = 3,
) -> list[StressWindow]:
    if window_size < 2:
        raise ValueError("window_size must be at least 2")
    if len(prices) < window_size:
        raise ValueError("price series is shorter than window_size")
    windows: list[StressWindow] = []
    for start in range(0, len(prices) - window_size + 1):
        end = start + window_size
        window = prices[start:end]
        returns = [math.log(window[i] / window[i - 1]) for i in range(1, len(window))]
        cumulative = math.log(window[-1] / window[0])
        mean = sum(returns) / len(returns)
        variance = sum((ret - mean) ** 2 for ret in returns) / max(1, len(returns) - 1)
        windows.append(
            StressWindow(
                start=start,
                end=end,
                cumulative_return=cumulative,
                realized_volatility=math.sqrt(max(variance, 0.0)),
            )
        )
    ranked = sorted(windows, key=lambda w: (w.cumulative_return, -w.realized_volatility))
    selected: list[StressWindow] = []
    for candidate in ranked:
        if all(candidate.end <= existing.start or candidate.start >= existing.end for existing in selected):
            selected.append(candidate)
        if len(selected) >= top_n:
            break
    return selected


def run_stress_replay(
    base_config: dict[str, Any],
    prices: list[float],
    window_size: int,
    top_n: int = 3,
) -> list[StressResult]:
    results: list[StressResult] = []
    for window in find_stress_windows(prices, window_size, top_n):
        window_prices = prices[window.start : window.end]
        cfg = deep_merge(
            base_config,
            {
                "initial_price": window_prices[0],
                "horizon_steps": len(window_prices) - 1,
            },
        )
        result = SimulationEngine(cfg, price_path=price_path_from_prices(window_prices)).run()
        results.append(StressResult(window=window, simulation=result))
    return results


def write_stress_artifacts(results: list[StressResult], output_dir: str | Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    simulations = []
    for idx, result in enumerate(results, start=1):
        run_dir = output_dir / f"stress_{idx:03d}_{result.simulation.agent_id}"
        write_result_artifacts(result.simulation, run_dir)
        (run_dir / "stress_window.csv").write_text(
            "start,end,cumulative_return,realized_volatility\n"
            f"{result.window.start},{result.window.end},"
            f"{result.window.cumulative_return},{result.window.realized_volatility}\n",
            encoding="utf-8",
        )
        simulations.append(result.simulation)
    return write_comparison_report(simulations, output_dir, title="Stress Replay")
