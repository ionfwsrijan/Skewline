import pytest

from market.lob import Fill
from metrics.execution_quality import (
    effective_spread_bps,
    maker_fill_ratio,
    markout_bps,
    realized_spread_bps,
    summarize_execution_quality,
)


def test_execution_quality_metrics_for_maker_fill():
    fills = [Fill("mm", "taker", 101.0, 1, "sell", "buy", 0)]
    mids = [100.0, 100.5, 100.75, 101.25, 101.0, 100.5]

    assert effective_spread_bps(fills, mids, "mm") == pytest.approx(200.0)
    assert realized_spread_bps(fills, mids, "mm", horizon_steps=5) == pytest.approx(100.0)
    assert markout_bps(fills, mids, "mm", horizon_steps=5) == pytest.approx(50.0)
    assert maker_fill_ratio(fills, "mm") == 1.0


def test_execution_quality_summary_handles_no_fills():
    summary = summarize_execution_quality([], [100.0], "mm")

    assert summary["effective_spread_bps"] == 0.0
    assert summary["maker_fill_ratio"] == 0.0
