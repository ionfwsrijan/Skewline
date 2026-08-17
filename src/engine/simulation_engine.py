from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from agents.base_agent import AgentContext
from agents.factory import build_agent
from agents.hedged_multi_asset_agent import HedgedMultiAssetAgent
from engine.fees import FeeModel
from engine.risk_manager import RiskManager, RiskState
from market.lob import BookSnapshot, Fill, LimitOrderBook
from market.multi_asset import simulate_correlated_paths
from market.price_process import PricePath, PriceProcessParams, simulate_jump_diffusion
from metrics.pnl_decomposition import decompose_pnl
from metrics.execution_quality import summarize_execution_quality
from metrics.risk_stats import summarize_risk
from order_flow.informed_traders import InformedTraderFlow
from order_flow.latency import LatencyQueue
from order_flow.noise_traders import MarketOrder, NoiseTraderFlow


@dataclass
class SimulationResult:
    agent_id: str
    equity_curve: list[float]
    inventory_curve: list[int]
    cash_curve: list[float]
    mid_prices: list[float]
    fills: list[Fill]
    order_flow: list[dict[str, float]]
    quote_history: list[dict[str, float]]
    book_snapshots: list[BookSnapshot]
    hedge_prices: list[float]
    accounting_events: list[dict[str, float | str]]
    summary: dict[str, float | str | None]


class SimulationEngine:
    def __init__(
        self,
        config: dict[str, Any],
        price_path: PricePath | None = None,
        agent_override: Any | None = None,
    ) -> None:
        self.config = config
        self.agent_override = agent_override
        self.dt = float(config.get("dt", 0.01))
        self.steps = int(config.get("horizon_steps", 1000))
        self.seed = int(config.get("seed", 1))
        process_cfg = config.get("price_process", {})
        params = PriceProcessParams(
            initial_price=float(config.get("initial_price", 100.0)),
            drift=float(process_cfg.get("drift", 0.0)),
            sigma=float(process_cfg.get("sigma", 0.2)),
            jump_intensity=float(process_cfg.get("jump_intensity", 0.0)),
            jump_mean=float(process_cfg.get("jump_mean", 0.0)),
            jump_std=float(process_cfg.get("jump_std", 0.0)),
            dt=self.dt,
        )
        hedge_cfg = config.get("multi_asset", {})
        self.hedge_beta = 0.0
        self.hedge_path: PricePath | None = None
        if price_path is None and hedge_cfg.get("enabled", False):
            hedge_params = PriceProcessParams(
                initial_price=float(hedge_cfg.get("hedge_initial_price", params.initial_price)),
                drift=float(hedge_cfg.get("hedge_drift", params.drift)),
                sigma=float(hedge_cfg.get("hedge_sigma", params.sigma)),
                jump_intensity=float(hedge_cfg.get("hedge_jump_intensity", params.jump_intensity)),
                jump_mean=float(hedge_cfg.get("hedge_jump_mean", params.jump_mean)),
                jump_std=float(hedge_cfg.get("hedge_jump_std", params.jump_std)),
                dt=self.dt,
            )
            paths = simulate_correlated_paths(
                self.steps,
                params,
                hedge_params,
                correlation=float(hedge_cfg.get("correlation", 0.75)),
                beta=float(hedge_cfg.get("beta", 1.0)),
                seed=self.seed,
            )
            self.price_path = paths.primary
            self.hedge_path = paths.hedge
            self.hedge_beta = paths.beta
        else:
            self.price_path = price_path or simulate_jump_diffusion(self.steps, params, seed=self.seed)
            if hedge_cfg.get("enabled", False):
                self.hedge_path = _scaled_hedge_path(
                    self.price_path,
                    initial_price=float(hedge_cfg.get("hedge_initial_price", params.initial_price)),
                    beta=float(hedge_cfg.get("beta", 1.0)),
                )
                self.hedge_beta = float(hedge_cfg.get("beta", 1.0))
        self.volatility = params.sigma

    def run(self) -> SimulationResult:
        agent = self.agent_override or build_agent(self.config.get("agent", {}))
        book = LimitOrderBook()
        latency_cfg = self.config.get("latency", {})
        latency = LatencyQueue(
            latency_cfg.get("quote_latency_steps", 0),
            jitter_steps=latency_cfg.get("jitter_steps", 0),
            spike_probability=latency_cfg.get("spike_probability", 0.0),
            spike_steps=latency_cfg.get("spike_steps", 0),
            seed=self.seed + 303,
        )
        fees = FeeModel(**self.config.get("fees", {}))
        risk = RiskManager(**self.config.get("risk", {}))
        flow_cfg = self.config.get("order_flow", {})
        noise = NoiseTraderFlow(
            float(flow_cfg.get("noise_intensity", 5.0)),
            int(flow_cfg.get("max_market_order_size", 3)),
            seed=self.seed + 101,
        )
        informed = InformedTraderFlow(
            float(flow_cfg.get("informed_intensity", 0.0)),
            int(flow_cfg.get("max_market_order_size", 3)),
            seed=self.seed + 202,
        )

        cash = 0.0
        inventory = 0
        peak_equity = 0.0
        fee_rebate_cash = 0.0
        fills: list[Fill] = []
        equity_curve: list[float] = []
        inventory_curve: list[int] = []
        cash_curve: list[float] = []
        order_flow_log: list[dict[str, float]] = []
        quote_history: list[dict[str, float]] = []
        book_snapshots: list[BookSnapshot] = []
        accounting_events: list[dict[str, float | str]] = []
        risk_state = RiskState(True, None)
        lob_cfg = self.config.get("external_lob", {})
        background_liquidity = bool(lob_cfg.get("enabled", True))
        background_levels = int(lob_cfg.get("levels", 4))
        background_qty = int(lob_cfg.get("quantity", 15))
        background_half_spread_bps = float(lob_cfg.get("half_spread_bps", 12.0))
        background_ttl = int(lob_cfg.get("ttl_steps", 5))

        for t in range(self.steps):
            mid = self.price_path.prices[t]
            hedge_mid = self.hedge_path.prices[t] if self.hedge_path is not None else None
            for order in latency.release(t):
                _, limit_fills = book.submit_limit_order(order)
                for fill in limit_fills:
                    if fill.maker_agent_id == agent.agent_id:
                        before_cash, before_inventory = cash, inventory
                        cash, inventory, fee_delta = self._apply_maker_fill(
                            cash, inventory, fill, fees
                        )
                        _record_fill_event(
                            accounting_events,
                            fill,
                            "maker_fill",
                            before_cash,
                            before_inventory,
                            cash,
                            inventory,
                            fee_delta,
                        )
                        fee_rebate_cash += fee_delta
                        fills.append(fill)
                    elif fill.taker_agent_id == agent.agent_id:
                        before_cash, before_inventory = cash, inventory
                        cash, inventory, fee_delta = self._apply_taker_fill(
                            cash, inventory, fill, fees
                        )
                        _record_fill_event(
                            accounting_events,
                            fill,
                            "taker_fill",
                            before_cash,
                            before_inventory,
                            cash,
                            inventory,
                            fee_delta,
                        )
                        fee_rebate_cash += fee_delta
                        fills.append(fill)

            if background_liquidity:
                book.cancel_stale_orders(t, background_ttl, agent_id="external_liquidity")
                book.seed_liquidity_around_mid(
                    mid,
                    t,
                    levels=background_levels,
                    quantity=background_qty,
                    half_spread_bps=background_half_spread_bps,
                    rng=noise.rng,
                    jitter=0.15,
                )

            orders = self._sample_order_flow(noise, informed, t)
            buy_qty = sum(order.quantity for order in orders if order.side == "buy")
            sell_qty = sum(order.quantity for order in orders if order.side == "sell")
            informed_qty = sum(order.quantity for order in orders if order.informed)
            for market_order in orders:
                step_fills = book.match_market_order(
                    market_order.trader_id,
                    market_order.side,
                    market_order.quantity,
                    timestamp=t,
                )
                for fill in step_fills:
                    if fill.maker_agent_id == agent.agent_id:
                        before_cash, before_inventory = cash, inventory
                        cash, inventory, fee_delta = self._apply_maker_fill(
                            cash, inventory, fill, fees
                        )
                        _record_fill_event(
                            accounting_events,
                            fill,
                            "maker_fill",
                            before_cash,
                            before_inventory,
                            cash,
                            inventory,
                            fee_delta,
                        )
                        fee_rebate_cash += fee_delta
                        fills.append(fill)

            agent.observe_order_flow(orders)
            book.cancel_agent_orders(agent.agent_id)

            hedge_value = (
                agent.hedge_value(mid, hedge_mid)
                if isinstance(agent, HedgedMultiAssetAgent)
                else 0.0
            )
            equity = cash + inventory * mid + hedge_value
            peak_equity = max(peak_equity, equity)
            risk_state = risk.check(inventory, equity, peak_equity)
            if not risk_state.active:
                before_cash, before_inventory = cash, inventory
                cash, fee_delta = self._flatten_inventory(cash, inventory, mid, fees)
                fee_rebate_cash += fee_delta
                accounting_events.append(
                    {
                        "timestamp": float(t),
                        "event_type": "risk_flatten",
                        "price": mid,
                        "quantity": float(abs(before_inventory)),
                        "cash_delta": cash - before_cash,
                        "inventory_delta": float(-before_inventory),
                        "cash_after": cash,
                        "inventory_after": 0.0,
                        "fee": fee_delta,
                    }
                )
                inventory = 0
                book.cancel_agent_orders(agent.agent_id)
                equity = cash + hedge_value

            equity_curve.append(equity)
            inventory_curve.append(inventory)
            cash_curve.append(cash)
            order_flow_log.append(
                {
                    "timestamp": float(t),
                    "buy_qty": float(buy_qty),
                    "sell_qty": float(sell_qty),
                    "informed_qty": float(informed_qty),
                }
            )
            book_snapshots.append(book.snapshot(t))

            if not risk_state.active:
                break

            if hasattr(agent, "learn"):
                agent.learn(equity, inventory, self.volatility)

            context = AgentContext(
                timestamp=t,
                mid_price=mid,
                volatility=self.volatility,
                inventory=inventory,
                cash=cash,
                remaining_steps=self.steps - t,
                dt=self.dt,
                hedge_mid_price=hedge_mid,
                hedge_beta=self.hedge_beta,
            )
            quote = agent.quote(context)
            quote_row = {
                "timestamp": float(t),
                "bid_price": quote.bid_price,
                "ask_price": quote.ask_price,
                "bid_size": float(quote.bid_size),
                "ask_size": float(quote.ask_size),
                "inventory": float(inventory),
                "latency_delay_steps": 0.0,
            }
            for order in quote.to_orders(agent.agent_id, t):
                latency.submit(t, order)
                quote_row["latency_delay_steps"] = max(
                    quote_row["latency_delay_steps"],
                    float(latency.last_delay_steps),
                )
            quote_history.append(quote_row)

        final_mid = self.price_path.prices[min(len(equity_curve), len(self.price_path.prices) - 1)]
        pnl_breakdown = decompose_pnl(
            fills,
            self.price_path.prices,
            fee_rebate_cash,
            inventory,
            final_mid,
        )
        summary: dict[str, float | str | None] = {
            "agent": agent.agent_id,
            "total_pnl": equity_curve[-1] if equity_curve else 0.0,
            "cash": cash,
            "final_inventory": float(inventory),
            "spread_capture": pnl_breakdown.spread_capture,
            "inventory_mark_to_market": pnl_breakdown.inventory_mark_to_market,
            "adverse_selection": pnl_breakdown.adverse_selection,
            "fees_and_rebates": pnl_breakdown.fees_and_rebates,
            "hedge_value": (
                agent.hedge_value(final_mid, self.hedge_path.prices[min(len(equity_curve), len(self.hedge_path.prices) - 1)])
                if isinstance(agent, HedgedMultiAssetAgent) and self.hedge_path is not None
                else 0.0
            ),
            "hedge_beta": self.hedge_beta,
            "risk_stop": risk_state.reason,
            "avg_quoted_spread": _average_spread(quote_history),
            "avg_lit_spread": _average_lit_spread(book_snapshots),
            **summarize_execution_quality(fills, self.price_path.prices, agent.agent_id),
            **summarize_risk(equity_curve, inventory_curve, len(fills)),
        }
        return SimulationResult(
            agent_id=agent.agent_id,
            equity_curve=equity_curve,
            inventory_curve=inventory_curve,
            cash_curve=cash_curve,
            mid_prices=self.price_path.prices[: len(equity_curve)],
            fills=fills,
            order_flow=order_flow_log,
            quote_history=quote_history,
            book_snapshots=book_snapshots,
            hedge_prices=self.hedge_path.prices[: len(equity_curve)] if self.hedge_path else [],
            accounting_events=accounting_events,
            summary=summary,
        )

    def _sample_order_flow(
        self,
        noise: NoiseTraderFlow,
        informed: InformedTraderFlow,
        t: int,
    ) -> list[MarketOrder]:
        future_return = (
            self.price_path.returns[t]
            if t < len(self.price_path.returns)
            else 0.0
        )
        jump_flag = self.price_path.jump_flags[t] if t < len(self.price_path.jump_flags) else False
        orders = noise.sample(self.dt, t)
        orders.extend(informed.sample(self.dt, t, future_return, jump_flag))
        return orders

    @staticmethod
    def _apply_maker_fill(
        cash: float,
        inventory: int,
        fill: Fill,
        fees: FeeModel,
    ) -> tuple[float, int, float]:
        notional = fill.price * fill.quantity
        rebate = fees.maker_cash_adjustment(notional)
        if fill.maker_side == "buy":
            inventory += fill.quantity
            cash -= notional
        else:
            inventory -= fill.quantity
            cash += notional
        cash += rebate
        return cash, inventory, rebate

    @staticmethod
    def _apply_taker_fill(
        cash: float,
        inventory: int,
        fill: Fill,
        fees: FeeModel,
    ) -> tuple[float, int, float]:
        notional = fill.price * fill.quantity
        fee = fees.taker_cash_adjustment(notional)
        if fill.taker_side == "buy":
            inventory += fill.quantity
            cash -= notional
        else:
            inventory -= fill.quantity
            cash += notional
        cash += fee
        return cash, inventory, fee

    @staticmethod
    def _flatten_inventory(
        cash: float,
        inventory: int,
        mid: float,
        fees: FeeModel,
    ) -> tuple[float, float]:
        if inventory == 0:
            return cash, 0.0
        notional = abs(inventory) * mid
        fee = fees.taker_cash_adjustment(notional)
        cash += inventory * mid + fee
        return cash, fee


def run_config(config: dict[str, Any]) -> SimulationResult:
    return SimulationEngine(config).run()


def compare_agents(base_config: dict[str, Any], agent_configs: list[dict[str, Any]]) -> list[SimulationResult]:
    seed = int(base_config.get("seed", 1))
    steps = int(base_config.get("horizon_steps", 1000))
    process_cfg = base_config.get("price_process", {})
    params = PriceProcessParams(
        initial_price=float(base_config.get("initial_price", 100.0)),
        drift=float(process_cfg.get("drift", 0.0)),
        sigma=float(process_cfg.get("sigma", 0.2)),
        jump_intensity=float(process_cfg.get("jump_intensity", 0.0)),
        jump_mean=float(process_cfg.get("jump_mean", 0.0)),
        jump_std=float(process_cfg.get("jump_std", 0.0)),
        dt=float(base_config.get("dt", 0.01)),
    )
    shared_path = simulate_jump_diffusion(steps, params, seed=seed)
    results: list[SimulationResult] = []
    for agent_cfg in agent_configs:
        cfg = {**base_config, "agent": agent_cfg}
        results.append(SimulationEngine(cfg, price_path=shared_path).run())
    return results


def _average_spread(quote_history: list[dict[str, float]]) -> float:
    if not quote_history:
        return 0.0
    return sum(row["ask_price"] - row["bid_price"] for row in quote_history) / len(quote_history)


def _average_lit_spread(snapshots: list[BookSnapshot]) -> float:
    spreads = [snap.spread for snap in snapshots if snap.spread is not None]
    return sum(spreads) / len(spreads) if spreads else 0.0


def _record_fill_event(
    events: list[dict[str, float | str]],
    fill: Fill,
    event_type: str,
    before_cash: float,
    before_inventory: int,
    after_cash: float,
    after_inventory: int,
    fee: float,
) -> None:
    events.append(
        {
            "timestamp": float(fill.timestamp),
            "event_type": event_type,
            "maker_agent_id": fill.maker_agent_id,
            "taker_agent_id": fill.taker_agent_id,
            "maker_side": fill.maker_side,
            "taker_side": fill.taker_side,
            "price": fill.price,
            "quantity": float(fill.quantity),
            "cash_delta": after_cash - before_cash,
            "inventory_delta": float(after_inventory - before_inventory),
            "cash_after": after_cash,
            "inventory_after": float(after_inventory),
            "fee": fee,
        }
    )


def _scaled_hedge_path(price_path: PricePath, initial_price: float, beta: float) -> PricePath:
    prices = [initial_price]
    for ret in price_path.returns:
        prices.append(max(0.01, prices[-1] * (1.0 + beta * ret)))
    returns = [
        0.0 if prices[i - 1] <= 0 else math.log(prices[i] / prices[i - 1])
        for i in range(1, len(prices))
    ]
    return PricePath(prices=prices, returns=returns, jump_flags=list(price_path.jump_flags))
