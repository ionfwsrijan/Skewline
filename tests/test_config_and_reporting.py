from pathlib import Path

import pytest

from config import ConfigError, config_hash, deep_merge, load_validated_config, validate_config
from engine.simulation_engine import run_config
from market.price_process import price_path_from_prices
from research.data_loading import load_price_series
from research.monte_carlo import run_monte_carlo, summarize_monte_carlo, write_monte_carlo_artifacts
from research.optimization import apply_dot_overrides, run_grid_search, write_optimization_artifacts
from research.stress import find_stress_windows, run_stress_replay, write_stress_artifacts
from research.reporting import write_comparison_report, write_result_artifacts
from research.scenarios import run_scenario_matrix, write_scenario_artifacts
from research.synthetic_data import write_synthetic_l1_csv
from research.walk_forward import run_walk_forward_prices, write_walk_forward_artifacts


def test_config_validation_and_hash_are_stable():
    config = load_validated_config("configs/baseline_naive.yaml")

    assert config_hash(config) == config_hash(load_validated_config("configs/baseline_naive.yaml"))

    broken = deep_merge(config, {"dt": 0})
    with pytest.raises(ConfigError):
        validate_config(broken)


def test_reporting_writes_research_artifacts(tmp_path: Path):
    config = deep_merge(
        load_validated_config("configs/baseline_naive.yaml"),
        {"horizon_steps": 25, "external_lob": {"quantity": 3, "levels": 2}},
    )
    result = run_config(config)

    write_result_artifacts(result, tmp_path / "naive")
    report = write_comparison_report([result], tmp_path)

    assert (tmp_path / "naive" / "fills.csv").exists()
    assert (tmp_path / "summary.csv").exists()
    assert report.exists()
    assert "Market Making Strategy Comparison" in report.read_text(encoding="utf-8")


def test_synthetic_l1_writer_creates_ingestable_csv(tmp_path: Path):
    path = write_synthetic_l1_csv(tmp_path / "synthetic.csv", steps=5, seed=1)

    text = path.read_text(encoding="utf-8")
    assert "timestamp,bid,ask,price,quantity" in text
    assert len(text.splitlines()) == 6


def test_price_path_from_prices_marks_jumps():
    path = price_path_from_prices([100, 100.1, 100.2, 120, 120.1], jump_z=1.0)

    assert len(path.prices) == 5
    assert len(path.returns) == 4
    assert any(path.jump_flags)


def test_walk_forward_validation_writes_outputs(tmp_path: Path):
    csv_path = write_synthetic_l1_csv(tmp_path / "synthetic.csv", steps=80, seed=3)
    prices = load_price_series(csv_path)
    config = deep_merge(
        load_validated_config("configs/baseline_naive.yaml"),
        {"external_lob": {"quantity": 3, "levels": 2}},
    )

    results = run_walk_forward_prices(config, prices, train_size=30, test_size=20)
    report = write_walk_forward_artifacts(results, tmp_path / "wf")

    assert len(results) >= 2
    assert report.exists()
    assert (tmp_path / "wf" / "summary.csv").exists()


def test_monte_carlo_writes_aggregate_summary(tmp_path: Path):
    config = deep_merge(
        load_validated_config("configs/baseline_naive.yaml"),
        {"horizon_steps": 20, "external_lob": {"quantity": 3, "levels": 2}},
    )

    results = run_monte_carlo(config, runs=3, seed_start=100)
    summary = summarize_monte_carlo(results)
    report = write_monte_carlo_artifacts(results, tmp_path / "mc")

    assert summary["runs"] == 3
    assert "total_pnl_mean" in summary
    assert report.exists()
    assert (tmp_path / "mc" / "monte_carlo_summary.csv").exists()


def test_stress_replay_selects_worst_windows_and_writes_outputs(tmp_path: Path):
    prices = [100, 101, 102, 80, 79, 90, 91, 70, 69, 95]
    config = deep_merge(
        load_validated_config("configs/baseline_naive.yaml"),
        {"external_lob": {"quantity": 3, "levels": 2}},
    )

    windows = find_stress_windows(prices, window_size=3, top_n=2)
    results = run_stress_replay(config, prices, window_size=3, top_n=2)
    report = write_stress_artifacts(results, tmp_path / "stress")

    assert len(windows) == 2
    assert windows[0].cumulative_return < 0
    assert len(results) == 2
    assert report.exists()


def test_scenario_matrix_runs_named_regimes(tmp_path: Path):
    config = deep_merge(
        load_validated_config("configs/baseline_naive.yaml"),
        {"horizon_steps": 25, "external_lob": {"quantity": 3, "levels": 2}},
    )
    scenarios = [
        {"name": "base", "overrides": {}},
        {"name": "latency", "overrides": {"latency": {"quote_latency_steps": 4}}},
    ]

    results = run_scenario_matrix(config, scenarios)
    report = write_scenario_artifacts(results, tmp_path / "scenarios")

    assert [result.name for result in results] == ["base", "latency"]
    assert report.exists()
    assert (tmp_path / "scenarios" / "scenario_summary.csv").exists()


def test_grid_search_optimization_ranks_candidates(tmp_path: Path):
    config = deep_merge(
        load_validated_config("configs/avellaneda_stoikov.yaml"),
        {"horizon_steps": 20, "external_lob": {"quantity": 3, "levels": 2}},
    )
    overridden = apply_dot_overrides(config, {"agent.gamma": 0.05})
    results = run_grid_search(
        config,
        {"agent.gamma": [0.04, 0.08], "agent.kappa": [1.0]},
        objective="sharpe",
    )
    report = write_optimization_artifacts(results, tmp_path / "opt")

    assert overridden["agent"]["gamma"] == 0.05
    assert [result.rank for result in results] == [1, 2]
    assert report.exists()
    assert (tmp_path / "opt" / "optimization_results.csv").exists()
