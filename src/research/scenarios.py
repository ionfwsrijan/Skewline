from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import deep_merge, validate_config
from engine.simulation_engine import SimulationResult, run_config
from research.reporting import write_comparison_report, write_result_artifacts


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    overrides: dict[str, Any]
    simulation: SimulationResult


def run_scenario_matrix(
    base_config: dict[str, Any],
    scenarios: list[dict[str, Any]],
) -> list[ScenarioResult]:
    results: list[ScenarioResult] = []
    for raw in scenarios:
        name = str(raw.get("name", f"scenario_{len(results) + 1}"))
        overrides = dict(raw.get("overrides", {}))
        config = deep_merge(base_config, overrides)
        validate_config(config, source=f"scenario:{name}")
        results.append(ScenarioResult(name=name, overrides=overrides, simulation=run_config(config)))
    return results


def write_scenario_artifacts(results: list[ScenarioResult], output_dir: str | Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "scenario",
        "agent",
        "total_pnl",
        "sharpe",
        "max_drawdown",
        "cvar_95",
        "fill_rate",
        "effective_spread_bps",
        "markout_5_bps",
        "risk_stop",
    ]
    with (output_dir / "scenario_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row = {"scenario": result.name}
            row.update(
                {
                    key: result.simulation.summary.get(key, "")
                    for key in fieldnames
                    if key != "scenario"
                }
            )
            writer.writerow(row)
            write_result_artifacts(result.simulation, output_dir / result.name)
    return write_comparison_report(
        [result.simulation for result in results],
        output_dir,
        title="Scenario Matrix",
    )
