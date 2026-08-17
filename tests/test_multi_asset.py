from config import deep_merge, load_validated_config, validate_config, ConfigError
from engine.simulation_engine import run_config
from market.multi_asset import estimate_correlation, estimate_hedge_beta, simulate_correlated_paths
from market.price_process import PriceProcessParams


def test_correlated_path_estimation_is_reasonable():
    params = PriceProcessParams(initial_price=100.0, sigma=0.2, dt=0.01)
    hedge_params = PriceProcessParams(initial_price=50.0, sigma=0.15, dt=0.01)

    paths = simulate_correlated_paths(
        500,
        params,
        hedge_params,
        correlation=0.85,
        beta=1.0,
        seed=5,
    )
    estimated_corr = estimate_correlation(paths.primary.returns, paths.hedge.returns)
    estimated_beta = estimate_hedge_beta(paths.primary.returns, paths.hedge.returns)

    assert estimated_corr > 0.70
    assert estimated_beta > 0.0
    assert paths.hedge.prices[0] == 50.0


def test_hedged_multi_asset_config_generates_hedge_telemetry():
    config = deep_merge(
        load_validated_config("configs/multi_asset_hedged.yaml"),
        {"horizon_steps": 40, "external_lob": {"quantity": 3, "levels": 2}},
    )

    result = run_config(config)

    assert result.hedge_prices
    assert result.summary["hedge_beta"] != 0.0
    assert "hedge_value" in result.summary


def test_multi_asset_validation_rejects_bad_correlation():
    config = deep_merge(
        load_validated_config("configs/multi_asset_hedged.yaml"),
        {"multi_asset": {"correlation": 2.0}},
    )

    try:
        validate_config(config)
    except ConfigError:
        return
    raise AssertionError("Expected ConfigError")
