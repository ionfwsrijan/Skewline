from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AccountingAudit:
    cash_error: float
    inventory_error: float
    equity_identity_error: float
    event_count: int

    @property
    def passed(self) -> bool:
        return (
            abs(self.cash_error) < 1e-8
            and abs(self.inventory_error) < 1e-8
            and abs(self.equity_identity_error) < 1e-8
        )


def audit_result(result: Any) -> AccountingAudit:
    reconstructed_cash = sum(float(event.get("cash_delta", 0.0)) for event in result.accounting_events)
    reconstructed_inventory = sum(
        float(event.get("inventory_delta", 0.0)) for event in result.accounting_events
    )
    final_cash = result.cash_curve[-1] if result.cash_curve else 0.0
    final_inventory = result.inventory_curve[-1] if result.inventory_curve else 0.0
    final_mid = result.mid_prices[-1] if result.mid_prices else 0.0
    hedge_value = float(result.summary.get("hedge_value", 0.0) or 0.0)
    final_equity = result.equity_curve[-1] if result.equity_curve else 0.0
    identity_equity = final_cash + final_inventory * final_mid + hedge_value
    return AccountingAudit(
        cash_error=reconstructed_cash - final_cash,
        inventory_error=reconstructed_inventory - final_inventory,
        equity_identity_error=identity_equity - final_equity,
        event_count=len(result.accounting_events),
    )
