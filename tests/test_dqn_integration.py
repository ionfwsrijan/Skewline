import json

import pytest

from agents.dqn_agent import DQNAgent, SmallMLP, ReplayBuffer
from agents.base_agent import AgentContext
from config import load_validated_config, deep_merge


def context(mid=100.0, inv=0, vol=0.2, cash=0.0):
    return AgentContext(
        timestamp=1,
        mid_price=mid,
        volatility=vol,
        inventory=inv,
        cash=cash,
        remaining_steps=100,
        dt=0.01,
    )


class TestSmallMLP:
    def test_forward_output_shape(self):
        net = SmallMLP(input_dim=4, hidden=16, output_dim=5, seed=0)
        import numpy as np
        x = np.zeros((1, 4))
        q, _ = net.forward(x)
        assert q.shape == (1, 5)

    def test_train_step_reduces_loss(self):
        net = SmallMLP(input_dim=4, hidden=16, output_dim=5, lr=0.01, seed=42)
        import numpy as np
        x = np.random.randn(8, 4)
        target = np.random.randn(8, 5)
        q1, _ = net.forward(x)
        loss1 = float(np.mean((q1 - target) ** 2))
        net.train_step(x, target)
        q2, _ = net.forward(x)
        loss2 = float(np.mean((q2 - target) ** 2))
        assert loss2 < loss1


class TestReplayBuffer:
    def test_push_and_sample(self):
        buf = ReplayBuffer(capacity=100)
        import numpy as np
        for _ in range(50):
            buf.push(np.zeros(4), 0, 1.0, np.zeros(4), False)
        assert len(buf) == 50
        batch = buf.sample(10, __import__("random").Random(0))
        assert len(batch) == 10

    def test_capacity_overflow(self):
        buf = ReplayBuffer(capacity=10)
        import numpy as np
        for _ in range(20):
            buf.push(np.zeros(4), 0, 1.0, np.zeros(4), False)
        assert len(buf) == 10


class TestDQNAgent:
    def test_quote_non_crossing(self):
        agent = DQNAgent(seed=1)
        q = agent.quote(context())
        assert q.bid_price < q.ask_price
        assert q.bid_size >= 0
        assert q.ask_size >= 0

    def test_quote_responds_to_inventory(self):
        agent = DQNAgent(seed=1)
        q_flat = agent.quote(context(inv=0))
        q_long = agent.quote(context(inv=15))
        assert q_long.bid_price <= q_flat.bid_price or q_long.ask_price <= q_flat.ask_price

    def test_learn_updates_network(self):
        agent = DQNAgent(seed=1, batch_size=4)
        agent.quote(context())
        w_before = agent._q_net.W3.copy()
        for i in range(10):
            agent.quote(context(inv=i))
            agent.learn(100.0 + i, i, 0.2)
        w_after = agent._q_net.W3.copy()
        assert not (w_before == w_after).all()

    def test_save_and_load(self, tmp_path):
        agent = DQNAgent(seed=1)
        agent.quote(context())
        agent.learn(100.0, 0, 0.2)
        path = tmp_path / "dqn.json"
        agent.save_q_values(path)
        assert path.exists()

        agent2 = DQNAgent(seed=2)
        agent2.load_q_values(path)
        import numpy as np
        assert np.allclose(agent._q_net.W1, agent2._q_net.W1)
        assert np.allclose(agent._q_net.W3, agent2._q_net.W3)

    def test_epsilon_greedy(self):
        agent = DQNAgent(seed=42)
        agent.epsilon = 1.0
        actions = set()
        for _ in range(100):
            state = import_numpy().array([0, 0.2, 0.0, 0.5])
            actions.add(agent._choose_action(state))
        assert len(actions) > 1

    def test_spread_actions_in_range(self):
        agent = DQNAgent(seed=1)
        for _ in range(50):
            q = agent.quote(context())
            spread_bps = (q.ask_price - q.bid_price) / q.bid_price * 10000
            assert 1.0 < spread_bps < 25.0


def import_numpy():
    import numpy as np
    return np


class TestDQNIntegration:
    def test_dqn_runs_in_engine(self):
        from engine.simulation_engine import run_config
        config = deep_merge(
            load_validated_config("configs/dqn_agent.yaml"),
            {"horizon_steps": 50, "external_lob": {"quantity": 3, "levels": 2}},
        )
        result = run_config(config)
        assert result.agent_id == "dqn"
        assert len(result.equity_curve) == 50
