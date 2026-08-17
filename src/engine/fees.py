from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeeModel:
    maker_rebate_bps: float = 0.0
    taker_fee_bps: float = 0.0

    def maker_cash_adjustment(self, notional: float) -> float:
        return notional * self.maker_rebate_bps / 10_000.0

    def taker_cash_adjustment(self, notional: float) -> float:
        return -notional * self.taker_fee_bps / 10_000.0
