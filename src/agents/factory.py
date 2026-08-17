from __future__ import annotations

from typing import Any

from agents.avellaneda_stoikov import AvellanedaStoikovAgent
from agents.flow_imbalance_agent import FlowImbalanceAgent
from agents.glft import GLFTAgent
from agents.hedged_multi_asset_agent import HedgedMultiAssetAgent
from agents.naive_fixed_spread import NaiveFixedSpreadAgent
from agents.rl_agent import TabularRLAgent


def build_agent(config: dict[str, Any]):
    cfg = dict(config)
    agent_type = cfg.pop("type", "naive")
    mapping = {
        "naive": NaiveFixedSpreadAgent,
        "avellaneda_stoikov": AvellanedaStoikovAgent,
        "glft": GLFTAgent,
        "flow_imbalance": FlowImbalanceAgent,
        "rl": TabularRLAgent,
        "hedged_multi_asset": HedgedMultiAssetAgent,
    }
    if agent_type not in mapping:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return mapping[agent_type](**cfg)
