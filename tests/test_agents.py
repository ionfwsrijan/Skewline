from agents.base_agent import AgentContext
from agents.factory import build_agent
from agents.rl_agent import TabularRLAgent
from agents.rl_training import train_tabular_agent
from config import deep_merge, load_validated_config
from order_flow.noise_traders import MarketOrder


def context(inventory=0):
    return AgentContext(
        timestamp=1,
        mid_price=100.0,
        volatility=0.2,
        inventory=inventory,
        cash=0.0,
        remaining_steps=100,
        dt=0.01,
    )


def test_all_configured_agents_emit_valid_non_crossing_quotes():
    configs = [
        {"type": "naive"},
        {"type": "avellaneda_stoikov"},
        {"type": "glft"},
        {"type": "flow_imbalance"},
        {"type": "rl", "epsilon": 0.0},
        {"type": "hedged_multi_asset"},
    ]

    for cfg in configs:
        agent = build_agent(cfg)
        quote = agent.quote(context())
        assert quote.bid_price < 100.0
        assert quote.ask_price > 100.0
        assert quote.bid_size >= 0
        assert quote.ask_size >= 0


def test_flow_imbalance_agent_moves_center_after_buy_pressure():
    agent = build_agent({"type": "flow_imbalance", "base_spread_bps": 8.0})
    before = agent.quote(context())
    agent.observe_order_flow([MarketOrder("buy", 5, "buyer", informed=True)])
    after = agent.quote(context())

    assert after.bid_price > before.bid_price
    assert after.ask_price > before.ask_price


def test_tabular_rl_training_saves_and_loads_policy(tmp_path):
    config = deep_merge(
        load_validated_config("configs/rl_agent.yaml"),
        {"horizon_steps": 30, "external_lob": {"quantity": 3, "levels": 2}},
    )
    policy_path = tmp_path / "policy.json"

    agent, results = train_tabular_agent(config, episodes=2, output_path=policy_path)
    loaded = TabularRLAgent(q_values_path=str(policy_path))

    assert policy_path.exists()
    assert results
    assert loaded.q_values == agent.q_values
