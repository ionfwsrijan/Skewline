from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskState:
    active: bool = True
    reason: str | None = None


@dataclass
class RiskManager:
    max_position: int = 50
    max_drawdown: float = 2_500.0

    def check(self, inventory: int, equity: float, peak_equity: float) -> RiskState:
        if abs(inventory) > self.max_position:
            return RiskState(False, "position_limit")
        if peak_equity - equity > self.max_drawdown:
            return RiskState(False, "drawdown_limit")
        return RiskState(True, None)
