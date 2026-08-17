from __future__ import annotations

from dataclasses import dataclass

from market.lob import Fill


@dataclass
class PnLBreakdown:
    spread_capture: float = 0.0
    inventory_mark_to_market: float = 0.0
    adverse_selection: float = 0.0
    fees_and_rebates: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.spread_capture
            + self.inventory_mark_to_market
            + self.adverse_selection
            + self.fees_and_rebates
        )


def decompose_pnl(
    fills: list[Fill],
    mid_prices: list[float],
    fee_rebate_cash: float,
    final_inventory: int,
    final_mid: float,
) -> PnLBreakdown:
    spread_capture = 0.0
    adverse = 0.0
    for fill in fills:
        mid = mid_prices[min(fill.timestamp, len(mid_prices) - 1)]
        signed_inventory = fill.quantity if fill.maker_side == "buy" else -fill.quantity
        spread_capture += abs(fill.price - mid) * fill.quantity
        next_mid = mid_prices[min(fill.timestamp + 1, len(mid_prices) - 1)]
        adverse -= signed_inventory * (next_mid - fill.price)
    inventory_mtm = final_inventory * final_mid
    return PnLBreakdown(spread_capture, inventory_mtm, adverse, fee_rebate_cash)
