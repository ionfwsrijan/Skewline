import math

from market.calibration import fit_price_process_from_prices, microstructure_stats
from market.price_process import PriceProcessParams, simulate_jump_diffusion


def test_simulated_price_path_has_expected_lengths():
    path = simulate_jump_diffusion(
        25,
        PriceProcessParams(initial_price=100.0, sigma=0.2, dt=0.01),
        seed=1,
    )

    assert len(path.prices) == 26
    assert len(path.returns) == 25
    assert len(path.jump_flags) == 25
    assert all(price > 0 for price in path.prices)


def test_calibration_recovers_positive_volatility():
    prices = [100 * math.exp(0.001 * i + 0.01 * math.sin(i)) for i in range(50)]
    params = fit_price_process_from_prices(prices, dt=1.0)

    assert params.initial_price == prices[0]
    assert params.sigma > 0


def test_microstructure_stats_reports_spread_and_autocorr():
    stats = microstructure_stats([100, 101, 100.5, 102], [0.02, 0.03, 0.02, 0.04])

    assert stats["mean_spread"] == 0.0275
    assert "return_autocorrelation_lag1" in stats
