from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.rl_agent import TabularRLAgent
from agents.dqn_agent import DQNAgent
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


def train_dqn_agent(
    base_config: dict[str, Any],
    episodes: int,
    output_path: str | Path,
    epsilon_start: float = 0.3,
    epsilon_end: float = 0.02,
) -> tuple[DQNAgent, list[SimulationResult]]:
    agent_cfg = dict(base_config.get("agent", {}))
    agent = DQNAgent(
        hidden=int(agent_cfg.get("hidden", 32)),
        lr=float(agent_cfg.get("lr", 5e-4)),
        gamma_discount=float(agent_cfg.get("gamma_discount", 0.97)),
        batch_size=int(agent_cfg.get("batch_size", 32)),
        target_update_freq=int(agent_cfg.get("target_update_freq", 50)),
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
                "agent": {"type": "dqn"},
            },
        )
        results.append(SimulationEngine(config, agent_override=agent).run())
    agent.save_q_values(output_path)
    return agent, results
