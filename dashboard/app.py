from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import streamlit as st

from config import config_hash, load_config, validate_config
from engine.simulation_engine import run_config
from metrics.accounting_audit import audit_result


st.set_page_config(page_title="MM Sim Dashboard", layout="wide", initial_sidebar_state="expanded")


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --bg: #f5f7fb;
  --panel: #ffffff;
  --ink: #172033;
  --muted: #647084;
  --line: #dbe2ec;
  --blue: #2563eb;
  --cyan: #0891b2;
  --green: #0f9f6e;
  --amber: #b7791f;
  --red: #c24141;
}

.stApp {
  background: var(--bg);
  color: var(--ink);
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

[data-testid="stSidebar"] {
  background: #101828;
  border-right: 1px solid #243043;
}

[data-testid="stSidebar"] * {
  color: #eef4ff;
}

[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p {
  color: #cbd5e1;
}

.block-container {
  padding-top: 1.35rem;
  padding-bottom: 2.25rem;
  max-width: 1500px;
}

h1, h2, h3 {
  letter-spacing: 0;
}

div[data-testid="stMetric"] {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

div[data-testid="stMetricLabel"] {
  color: var(--muted);
  font-size: 0.78rem;
}

div[data-testid="stMetricValue"] {
  color: var(--ink);
  font-weight: 750;
}

.terminal-header {
  background: #0f172a;
  border: 1px solid #1f2a44;
  border-radius: 8px;
  padding: 18px 20px;
  color: #e5eefc;
  margin-bottom: 16px;
}

.terminal-header h1 {
  color: #ffffff;
  font-size: 1.55rem;
  margin: 0 0 6px 0;
  font-weight: 800;
}

.terminal-header .subline {
  color: #b8c4d8;
  font-size: 0.92rem;
}

.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.status-pill {
  border: 1px solid #334155;
  background: #17233a;
  color: #d9e4f5;
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 0.78rem;
  font-weight: 600;
}

.section-title {
  font-size: 0.86rem;
  font-weight: 800;
  color: #273449;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 20px 0 10px;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.audit-pass {
  color: #065f46;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.78rem;
  font-weight: 800;
}

.audit-fail {
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.78rem;
  font-weight: 800;
}

[data-testid="stDataFrame"] {
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}

button[kind="secondary"] {
  border-radius: 8px;
}
</style>
"""


st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _experiment_config_paths() -> dict[str, str]:
    configs: dict[str, str] = {}
    for path in sorted((ROOT / "configs").glob("*.yaml")):
        raw = load_config(path)
        if "agent" not in raw:
            continue
        try:
            validate_config(raw, source=str(path))
        except Exception:
            continue
        configs[path.stem] = str(path)
    return configs


@st.cache_data(show_spinner="Running simulation...")
def _run_cached(config_payload: str):
    return run_config(json.loads(config_payload))


def _fmt_money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def _fmt_num(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}"


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _section(label: str) -> None:
    st.markdown(f'<div class="section-title">{label}</div>', unsafe_allow_html=True)


def _fills_frame(result) -> pd.DataFrame:
    rows = [
        {
            "time": fill.timestamp,
            "maker": fill.maker_agent_id,
            "taker": fill.taker_agent_id,
            "maker_side": fill.maker_side,
            "price": fill.price,
            "quantity": fill.quantity,
        }
        for fill in result.fills
    ]
    return pd.DataFrame(rows)


def _book_frame(result) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "time": snap.timestamp,
                "best_bid": snap.best_bid,
                "best_ask": snap.best_ask,
                "spread": snap.spread,
                "bid_depth": snap.bid_depth,
                "ask_depth": snap.ask_depth,
            }
            for snap in result.book_snapshots
        ]
    )


def _event_frame(result) -> pd.DataFrame:
    return pd.DataFrame(result.accounting_events)


configs = _experiment_config_paths()
if not configs:
    st.error("No valid experiment configs found.")
    st.stop()

with st.sidebar:
    st.markdown("### MM Sim")
    selected = st.selectbox("Strategy", list(configs), index=list(configs).index("baseline_naive") if "baseline_naive" in configs else 0)
    config = deepcopy(load_config(configs[selected]))

    st.divider()
    st.markdown("#### Run")
    config["horizon_steps"] = st.slider(
        "Steps",
        100,
        5000,
        int(config.get("horizon_steps", 1200)),
        100,
    )
    config["seed"] = st.number_input("Seed", value=int(config.get("seed", 7)), step=1)

    st.markdown("#### Risk")
    config["risk"]["max_position"] = st.slider(
        "Max position",
        5,
        200,
        int(config.get("risk", {}).get("max_position", 50)),
    )
    config["risk"]["max_drawdown"] = st.slider(
        "Max drawdown",
        100.0,
        10000.0,
        float(config.get("risk", {}).get("max_drawdown", 2500.0)),
        100.0,
    )

    st.markdown("#### Market")
    config["order_flow"]["informed_intensity"] = st.slider(
        "Informed flow",
        0.0,
        5.0,
        float(config["order_flow"].get("informed_intensity", 0.0)),
        0.1,
    )
    config["latency"]["quote_latency_steps"] = st.slider(
        "Latency",
        0,
        20,
        int(config["latency"].get("quote_latency_steps", 0)),
    )
    config["latency"]["jitter_steps"] = st.slider(
        "Jitter",
        0,
        10,
        int(config["latency"].get("jitter_steps", 0)),
    )

    if "base_spread_bps" in config["agent"]:
        config["agent"]["base_spread_bps"] = st.slider(
            "Spread bps",
            1.0,
            40.0,
            float(config["agent"]["base_spread_bps"]),
            0.5,
        )
    if "gamma" in config["agent"]:
        config["agent"]["gamma"] = st.slider(
            "Risk aversion",
            0.01,
            0.30,
            float(config["agent"]["gamma"]),
            0.01,
        )

payload = json.dumps(config, sort_keys=True)
result = _run_cached(payload)
summary = result.summary
audit = audit_result(result)

st.markdown(
    f"""
    <div class="terminal-header">
      <h1>Market Making Research Terminal</h1>
      <div class="subline">Strategy diagnostics, execution quality, risk, inventory, and accounting audit.</div>
      <div class="status-row">
        <span class="status-pill">strategy: {result.agent_id}</span>
        <span class="status-pill">config: {selected}</span>
        <span class="status-pill">seed: {config["seed"]}</span>
        <span class="status-pill">steps: {len(result.equity_curve)}</span>
        <span class="status-pill">hash: {config_hash(config)}</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

top = st.columns(6)
top[0].metric("P&L", _fmt_money(float(summary["total_pnl"])))
top[1].metric("Sharpe", _fmt_num(float(summary["sharpe"])))
top[2].metric("Drawdown", _fmt_money(float(summary["max_drawdown"])))
top[3].metric("CVaR 95", _fmt_money(float(summary["cvar_95"])))
top[4].metric("Hit rate", _fmt_pct(float(summary["hit_rate"])))
top[5].metric("Fills", f"{float(summary['fill_count']):,.0f}")

second = st.columns(6)
second[0].metric("Max inv", f"{float(summary['max_inventory']):,.0f}")
second[1].metric("Fill rate", _fmt_pct(float(summary["fill_rate"])))
second[2].metric("Eff spread", f"{float(summary['effective_spread_bps']):.2f} bps")
second[3].metric("Realized 5", f"{float(summary['realized_spread_5_bps']):.2f} bps")
second[4].metric("Markout 5", f"{float(summary['markout_5_bps']):.2f} bps")
second[5].metric("Maker ratio", _fmt_pct(float(summary["maker_fill_ratio"])))

overview, execution, risk, ledger = st.tabs(["Overview", "Execution", "Risk", "Ledger"])

with overview:
    _section("Portfolio")
    left, right = st.columns([1.35, 1.0])
    with left:
        equity = pd.DataFrame({"equity": result.equity_curve})
        st.line_chart(equity, height=340)
    with right:
        inventory = pd.DataFrame({"inventory": result.inventory_curve})
        st.line_chart(inventory, height=340)

    _section("Market State")
    m1, m2 = st.columns([1.2, 1.0])
    with m1:
        market = pd.DataFrame({"mid_price": result.mid_prices})
        if result.hedge_prices:
            market["hedge_price"] = result.hedge_prices[: len(market)]
        st.line_chart(market, height=300)
    with m2:
        breakdown = pd.DataFrame(
            {
                "component": [
                    "spread_capture",
                    "inventory_mark_to_market",
                    "adverse_selection",
                    "fees_and_rebates",
                    "hedge_value",
                ],
                "value": [
                    summary["spread_capture"],
                    summary["inventory_mark_to_market"],
                    summary["adverse_selection"],
                    summary["fees_and_rebates"],
                    summary.get("hedge_value", 0.0),
                ],
            }
        )
        st.bar_chart(breakdown.set_index("component"), height=300)

with execution:
    _section("Spreads And Latency")
    quote_df = pd.DataFrame(result.quote_history)
    book_df = _book_frame(result)
    spread_df = pd.DataFrame(
        {
            "quoted_spread": quote_df["ask_price"] - quote_df["bid_price"] if not quote_df.empty else [],
            "lit_spread": book_df["spread"].fillna(0.0) if not book_df.empty else [],
            "latency_delay": quote_df["latency_delay_steps"] if not quote_df.empty else [],
        }
    )
    st.line_chart(spread_df, height=330)

    c1, c2 = st.columns([1.0, 1.0])
    with c1:
        _section("Recent Fills")
        fills_df = _fills_frame(result)
        st.dataframe(fills_df.tail(20), use_container_width=True, hide_index=True)
    with c2:
        _section("Book Snapshots")
        st.dataframe(book_df.tail(20), use_container_width=True, hide_index=True)

with risk:
    _section("Risk Surface")
    risk_df = pd.DataFrame(
        [
            {"metric": "VaR 95", "value": summary["var_95"]},
            {"metric": "CVaR 95", "value": summary["cvar_95"]},
            {"metric": "max_drawdown", "value": summary["max_drawdown"]},
            {"metric": "max_inventory", "value": summary["max_inventory"]},
            {"metric": "sortino", "value": summary["sortino"]},
            {"metric": "hit_rate", "value": summary["hit_rate"]},
        ]
    )
    st.dataframe(risk_df, use_container_width=True, hide_index=True)

    _section("Order Flow")
    flow_df = pd.DataFrame(result.order_flow)
    if not flow_df.empty:
        flow_df["net_qty"] = flow_df["buy_qty"] - flow_df["sell_qty"]
    st.line_chart(flow_df.set_index("timestamp") if not flow_df.empty else flow_df, height=320)

with ledger:
    _section("Accounting Audit")
    badge = "audit-pass" if audit.passed else "audit-fail"
    label = "PASSED" if audit.passed else "FAILED"
    st.markdown(f'<span class="{badge}">{label}</span>', unsafe_allow_html=True)
    audit_df = pd.DataFrame(
        [
            {"check": "cash_error", "value": audit.cash_error},
            {"check": "inventory_error", "value": audit.inventory_error},
            {"check": "equity_identity_error", "value": audit.equity_identity_error},
            {"check": "event_count", "value": audit.event_count},
        ]
    )
    st.dataframe(audit_df, use_container_width=True, hide_index=True)

    _section("Event Ledger")
    events_df = _event_frame(result)
    st.dataframe(events_df.tail(60), use_container_width=True, hide_index=True)
