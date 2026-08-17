import pytest

from engine.fees import FeeModel
from engine.simulation_engine import SimulationEngine
from market.lob import Fill
from config import deep_merge, load_validated_config
from metrics.accounting_audit import audit_result
from metrics.pnl_decomposition import decompose_pnl
from research.reporting import write_result_artifacts


def test_round_trip_maker_accounting_with_rebates():
    fees = FeeModel(maker_rebate_bps=1.0)
    cash = 0.0
    inventory = 0
    cash, inventory, rebate_1 = SimulationEngine._apply_maker_fill(
        cash,
        inventory,
        Fill("mm", "t1", 99.0, 1, "buy", "sell", 0),
        fees,
    )
    cash, inventory, rebate_2 = SimulationEngine._apply_maker_fill(
        cash,
        inventory,
        Fill("mm", "t2", 101.0, 1, "sell", "buy", 1),
        fees,
    )

    assert inventory == 0
    assert cash == pytest.approx(2.0 + 0.0099 + 0.0101)
    assert rebate_1 + rebate_2 == pytest.approx(0.02)


def test_flatten_inventory_charges_taker_fee():
    fees = FeeModel(taker_fee_bps=10.0)

    cash, fee = SimulationEngine._flatten_inventory(-99.0, 1, 100.0, fees)

    assert cash == pytest.approx(0.9)
    assert fee == pytest.approx(-0.1)


def test_pnl_decomposition_tracks_spread_and_adverse_selection():
    fills = [
        Fill("mm", "t1", 99.0, 1, "buy", "sell", 0),
        Fill("mm", "t2", 101.0, 1, "sell", "buy", 1),
    ]

    breakdown = decompose_pnl(fills, [100.0, 100.5, 101.0], 0.02, 0, 101.0)

    assert breakdown.spread_capture == pytest.approx(1.5)
    assert breakdown.fees_and_rebates == pytest.approx(0.02)
    assert breakdown.inventory_mark_to_market == 0.0


def test_simulation_accounting_ledger_reconstructs_primary_cash_and_inventory(tmp_path):
    config = deep_merge(
        load_validated_config("configs/baseline_naive.yaml"),
        {"horizon_steps": 80, "external_lob": {"quantity": 5, "levels": 2}},
    )
    result = SimulationEngine(config).run()

    audit = audit_result(result)
    write_result_artifacts(result, tmp_path / "run")

    assert audit.passed
    assert audit.event_count == len(result.accounting_events)
    assert (tmp_path / "run" / "accounting_events.csv").exists()
    assert (tmp_path / "run" / "accounting_audit.csv").exists()
