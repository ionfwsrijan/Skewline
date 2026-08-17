from engine.risk_manager import RiskManager
from engine.simulation_engine import run_config
from order_flow.latency import LatencyQueue


def test_position_limit_stops_risk():
    state = RiskManager(max_position=2).check(inventory=3, equity=0.0, peak_equity=0.0)

    assert not state.active
    assert state.reason == "position_limit"


def test_drawdown_limit_stops_risk():
    state = RiskManager(max_drawdown=10.0).check(inventory=0, equity=80.0, peak_equity=100.0)

    assert not state.active
    assert state.reason == "drawdown_limit"


def test_simulation_returns_summary():
    config = {
        "seed": 1,
        "horizon_steps": 50,
        "dt": 0.1,
        "initial_price": 100.0,
        "price_process": {"sigma": 0.1},
        "order_flow": {"noise_intensity": 10.0, "max_market_order_size": 1},
        "latency": {"quote_latency_steps": 0},
        "fees": {"maker_rebate_bps": 0.0, "taker_fee_bps": 0.0},
        "risk": {"max_position": 10, "max_drawdown": 1000.0},
        "agent": {"type": "naive", "base_spread_bps": 8.0, "order_size": 1},
    }

    result = run_config(config)

    assert result.summary["agent"] == "naive"
    assert len(result.equity_curve) > 0


def test_latency_queue_samples_jitter_and_spikes_deterministically():
    queue = LatencyQueue(
        latency_steps=2,
        jitter_steps=1,
        spike_probability=1.0,
        spike_steps=5,
        seed=1,
    )

    delays = [queue.sample_delay() for _ in range(5)]

    assert all(delay >= 7 for delay in delays)
    assert all(delay <= 8 for delay in delays)
