from __future__ import annotations

import csv
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any

from config import deep_merge, validate_config
from engine.simulation_engine import SimulationResult, run_config
from research.reporting import write_comparison_report, write_result_artifacts


@dataclass(frozen=True)
class OptimizationResult:
    rank: int
    objective: str
    objective_value: float
    parameters: dict[str, Any]
    simulation: SimulationResult


def run_grid_search(
    base_config: dict[str, Any],
    grid: dict[str, list[Any]],
    objective: str = "sharpe",
    maximize: bool = True,
) -> list[OptimizationResult]:
    raw_results: list[tuple[dict[str, Any], SimulationResult]] = []
    for parameters in _iter_grid(grid):
        config = apply_dot_overrides(base_config, parameters)
        validate_config(config, source="optimization")
        raw_results.append((parameters, run_config(config)))
    ranked = sorted(
        raw_results,
        key=lambda item: float(item[1].summary.get(objective, 0.0)),
        reverse=maximize,
    )
    return [
        OptimizationResult(
            rank=rank,
            objective=objective,
            objective_value=float(result.summary.get(objective, 0.0)),
            parameters=parameters,
            simulation=result,
        )
        for rank, (parameters, result) in enumerate(ranked, start=1)
    ]


def apply_dot_overrides(base_config: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for path, value in overrides.items():
        cursor = nested
        parts = path.split(".")
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = value
    return deep_merge(base_config, nested)


def write_optimization_artifacts(
    results: list[OptimizationResult],
    output_dir: str | Path,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rank",
        "objective",
        "objective_value",
        "parameters",
        "agent",
        "total_pnl",
        "sharpe",
        "max_drawdown",
        "fill_rate",
        "cvar_95",
    ]
    with (output_dir / "optimization_results.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            run_dir = output_dir / f"rank_{result.rank:03d}"
            write_result_artifacts(result.simulation, run_dir)
            writer.writerow(
                {
                    "rank": result.rank,
                    "objective": result.objective,
                    "objective_value": result.objective_value,
                    "parameters": result.parameters,
                    "agent": result.simulation.agent_id,
                    "total_pnl": result.simulation.summary.get("total_pnl", 0.0),
                    "sharpe": result.simulation.summary.get("sharpe", 0.0),
                    "max_drawdown": result.simulation.summary.get("max_drawdown", 0.0),
                    "fill_rate": result.simulation.summary.get("fill_rate", 0.0),
                    "cvar_95": result.simulation.summary.get("cvar_95", 0.0),
                }
            )
    return write_comparison_report(
        [result.simulation for result in results],
        output_dir,
        title="Parameter Optimization",
    )


def _iter_grid(grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    if not grid:
        return [{}]
    keys = list(grid.keys())
    values = [grid[key] for key in keys]
    return [dict(zip(keys, combination)) for combination in product(*values)]
