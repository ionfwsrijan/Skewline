from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean, stdev
from typing import Any

from config import deep_merge
from engine.simulation_engine import SimulationResult, run_config
from research.reporting import write_comparison_report, write_result_artifacts


def run_monte_carlo(
    base_config: dict[str, Any],
    runs: int,
    seed_start: int | None = None,
) -> list[SimulationResult]:
    seed_start = int(seed_start if seed_start is not None else base_config.get("seed", 1))
    results: list[SimulationResult] = []
    for offset in range(max(1, runs)):
        config = deep_merge(base_config, {"seed": seed_start + offset})
        results.append(run_config(config))
    return results


def summarize_monte_carlo(results: list[SimulationResult]) -> dict[str, float]:
    metrics = ["total_pnl", "sharpe", "max_drawdown", "fill_rate", "max_inventory", "cvar_95"]
    summary: dict[str, float] = {"runs": float(len(results))}
    for metric in metrics:
        values = [float(result.summary.get(metric, 0.0)) for result in results]
        summary[f"{metric}_mean"] = mean(values) if values else 0.0
        summary[f"{metric}_std"] = stdev(values) if len(values) > 1 else 0.0
        summary[f"{metric}_p05"] = _quantile(values, 0.05)
        summary[f"{metric}_p95"] = _quantile(values, 0.95)
    return summary


def write_monte_carlo_artifacts(
    results: list[SimulationResult],
    output_dir: str | Path,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for idx, result in enumerate(results, start=1):
        write_result_artifacts(result, output_dir / f"run_{idx:03d}")
    summary = summarize_monte_carlo(results)
    with (output_dir / "monte_carlo_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    return write_comparison_report(results, output_dir, title="Monte Carlo Seed Sweep")


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[idx]
