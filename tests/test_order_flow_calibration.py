from pathlib import Path

import pytest

from order_flow.calibration import (
    calibrate_order_flow,
    calibrate_order_flow_csv,
    write_order_flow_calibration,
)


def test_order_flow_calibration_estimates_arrivals_and_imbalance():
    calibration = calibrate_order_flow(
        timestamps=[0, 1, 2, 3],
        sides=["buy", "buy", "sell", "buy"],
        quantities=[1, 2, 1, 1],
        prices=[100.0, 100.1, 100.0, 100.2],
        mid_prices=[100.0, 100.05, 100.1, 100.15],
    )

    assert calibration.total_intensity == pytest.approx(4 / 3)
    assert calibration.buy_sell_imbalance == pytest.approx(3 / 5)
    assert calibration.observations == 4
    assert calibration.fill_decay_kappa > 0


def test_order_flow_csv_supports_binance_buyer_maker_flag(tmp_path: Path):
    path = tmp_path / "trades.csv"
    path.write_text(
        "timestamp,price,quantity,is_buyer_maker\n"
        "0,100,1,false\n"
        "1,101,2,true\n",
        encoding="utf-8",
    )

    calibration = calibrate_order_flow_csv(path)
    out = tmp_path / "calibration.csv"
    write_order_flow_calibration(out, calibration)

    assert calibration.buy_intensity == pytest.approx(1.0)
    assert calibration.sell_intensity == pytest.approx(1.0)
    assert out.exists()
