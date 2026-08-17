from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.rl_agent import TabularRLAgent
from config import deep_merge
from engine.simulation_engine import SimulationEngine, SimulationResult


def train_tabular_agent(
    base_config: dict[str, Any],
    episodes: int,
    output_path: str | Path,
    epsilon_start: float = 0.25,
    epsilon_end: float = 0.02,
) -> tuple[TabularRLAgent, list[SimulationResult]]:
    agent_cfg = dict(base_config.get("agent", {}))
    agent_cfg["type"] = "rl"
    agent = TabularRLAgent(
        epsilon=epsilon_start,
        alpha=float(agent_cfg.get("alpha", 0.05)),
        gamma_discount=float(agent_cfg.get("gamma_discount", 0.95)),
        order_size=int(agent_cfg.get("order_size", 1)),
        seed=int(base_config.get("seed", 1)),
    )
    results: list[SimulationResult] = []
    for episode in range(max(1, episodes)):
        progress = episode / max(1, episodes - 1)
        agent.epsilon = epsilon_start + progress * (epsilon_end - epsilon_start)
        config = deep_merge(
            base_config,
            {
                "seed": int(base_config.get("seed", 1)) + episode,
                "agent": {"type": "rl"},
            },
        )
        results.append(SimulationEngine(config, agent_override=agent).run())
    agent.save_q_values(output_path)
    return agent, results
