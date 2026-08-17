from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import deep_merge
from engine.simulation_engine import SimulationEngine, SimulationResult
from market.calibration import fit_price_process_from_prices
from market.price_process import price_path_from_prices
from metrics.validation import WalkForwardSplit, make_walk_forward_splits
from research.reporting import write_comparison_report, write_result_artifacts


@dataclass(frozen=True)
class WalkForwardResult:
    split: WalkForwardSplit
    calibration: dict[str, float]
    simulation: SimulationResult


def run_walk_forward_prices(
    base_config: dict[str, Any],
    prices: list[float],
    train_size: int,
    test_size: int,
    dt: float | None = None,
) -> list[WalkForwardResult]:
    splits = make_walk_forward_splits(len(prices), train_size, test_size)
    results: list[WalkForwardResult] = []
    effective_dt = float(dt or base_config.get("dt", 1.0))
    for split in splits:
        train_prices = prices[split.train_start : split.train_end]
        test_prices = prices[split.test_start : split.test_end]
        params = fit_price_process_from_prices(train_prices, dt=effective_dt)
        cfg = deep_merge(
            base_config,
            {
                "initial_price": test_prices[0],
                "horizon_steps": len(test_prices) - 1,
                "dt": effective_dt,
                "price_process": {
                    "drift": params.drift,
                    "sigma": params.sigma,
                    "jump_intensity": params.jump_intensity,
                    "jump_mean": params.jump_mean,
                    "jump_std": params.jump_std,
                },
            },
        )
        path = price_path_from_prices(test_prices)
        simulation = SimulationEngine(cfg, price_path=path).run()
        results.append(
            WalkForwardResult(
                split=split,
                calibration={
                    "drift": params.drift,
                    "sigma": params.sigma,
                    "jump_intensity": params.jump_intensity,
                    "jump_mean": params.jump_mean,
                    "jump_std": params.jump_std,
                },
                simulation=simulation,
            )
        )
    return results


def write_walk_forward_artifacts(
    results: list[WalkForwardResult],
    output_dir: str | Path,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    simulations = []
    for idx, result in enumerate(results, start=1):
        split_dir = output_dir / f"split_{idx:03d}_{result.simulation.agent_id}"
        write_result_artifacts(result.simulation, split_dir)
        (split_dir / "calibration.csv").write_text(
            "parameter,value\n"
            + "\n".join(f"{key},{value}" for key, value in result.calibration.items())
            + "\n",
            encoding="utf-8",
        )
        simulations.append(result.simulation)
    return write_comparison_report(simulations, output_dir, title="Walk-Forward Validation")
