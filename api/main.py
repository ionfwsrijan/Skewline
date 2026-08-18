from __future__ import annotations

import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import config_hash, load_config, validate_config, ConfigError
from engine.simulation_engine import run_config
from metrics.accounting_audit import audit_result


app = FastAPI(
    title="Skewline API",
    description="REST API for the Skewline market-making research simulator. "
    "Run simulations with configurable strategies, risk controls, and market conditions.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SimulateRequest(BaseModel):
    """Configuration for a market-making simulation run."""
    config: dict[str, Any] = Field(
        ...,
        description="Full simulation config (seed, horizon_steps, price_process, agent, risk, etc.)",
        examples=[{
            "seed": 7,
            "horizon_steps": 1200,
            "dt": 0.01,
            "initial_price": 100.0,
            "price_process": {"sigma": 0.18, "drift": 0.0, "jump_intensity": 0.02, "jump_mean": 0.0, "jump_std": 0.012},
            "order_flow": {"noise_intensity": 5.0, "informed_intensity": 0.6, "max_market_order_size": 3},
            "latency": {"quote_latency_steps": 2, "jitter_steps": 1, "spike_probability": 0.02, "spike_steps": 5},
            "fees": {"maker_rebate_bps": 0.1, "taker_fee_bps": 0.5},
            "risk": {"max_position": 50, "max_drawdown": 2500.0},
            "agent": {"type": "naive", "base_spread_bps": 8.0, "order_size": 1},
        }],
    )


class FillModel(BaseModel):
    maker_agent_id: str
    taker_agent_id: str
    price: float
    quantity: int
    maker_side: str
    taker_side: str
    timestamp: int


class BookSnapshotModel(BaseModel):
    timestamp: int
    best_bid: float | None
    best_ask: float | None
    bid_depth: int
    ask_depth: int
    spread: float | None


class AuditModel(BaseModel):
    passed: bool
    cash_error: float
    inventory_error: float
    equity_identity_error: float
    event_count: int


class BenchmarkModel(BaseModel):
    wall_time_ms: float = Field(description="Wall-clock time for the simulation in milliseconds")
    steps_per_sec: float = Field(description="Simulation steps processed per second")
    fills_count: int
    events_count: int


class SimulateResponse(BaseModel):
    """Full simulation result with curves, fills, metrics, audit, and benchmark."""
    agent_id: str
    equity_curve: list[float]
    inventory_curve: list[int]
    cash_curve: list[float]
    mid_prices: list[float]
    fills: list[FillModel]
    order_flow: list[dict[str, float]]
    quote_history: list[dict[str, float]]
    book_snapshots: list[BookSnapshotModel]
    hedge_prices: list[float]
    accounting_events: list[dict[str, Any]]
    summary: dict[str, Any]
    audit: AuditModel
    benchmark: BenchmarkModel
    config_hash: str


class ConfigSummary(BaseModel):
    """Summary of an available experiment configuration."""
    name: str
    agent_type: str
    horizon_steps: int
    seed: int


class HealthResponse(BaseModel):
    status: str
    version: str
    configs_count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check",
)
def health_check():
    """Returns API status, version, and number of available configs."""
    configs = _discover_configs()
    return HealthResponse(status="ok", version="1.0.0", configs_count=len(configs))


@app.get(
    "/api/configs",
    response_model=dict[str, dict[str, Any]],
    tags=["Configs"],
    summary="List all experiment configurations",
)
def list_configs():
    """Return all valid YAML experiment configs keyed by name."""
    return _discover_configs()


@app.get(
    "/api/configs/{name}",
    response_model=dict[str, Any],
    tags=["Configs"],
    summary="Get a specific configuration",
)
def get_config(name: str):
    """Load and validate a single config by name (without .yaml extension)."""
    path = ROOT / "configs" / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Config '{name}' not found")
    try:
        raw = load_config(path)
        validate_config(raw, source=str(path))
    except ConfigError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return raw


@app.post(
    "/api/simulate",
    response_model=SimulateResponse,
    tags=["Simulation"],
    summary="Run a market-making simulation",
    response_description="Full simulation result with equity curve, fills, metrics, audit, and benchmark timing",
)
def simulate(req: SimulateRequest):
    """
    Run a complete market-making simulation with the provided config.

    Returns equity curve, inventory curve, mid prices, fills, order flow,
    quote history, book snapshots, P&L decomposition, risk metrics,
    accounting audit, and wall-clock benchmark timing.
    """
    config = req.config
    try:
        validate_config(config)
    except ConfigError as e:
        raise HTTPException(status_code=422, detail=str(e))

    t0 = time.perf_counter()
    result = run_config(config)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    audit = audit_result(result)
    steps = len(result.equity_curve)

    return SimulateResponse(
        agent_id=result.agent_id,
        equity_curve=result.equity_curve,
        inventory_curve=result.inventory_curve,
        cash_curve=result.cash_curve,
        mid_prices=result.mid_prices,
        fills=[
            FillModel(
                maker_agent_id=f.maker_agent_id,
                taker_agent_id=f.taker_agent_id,
                price=f.price,
                quantity=f.quantity,
                maker_side=f.maker_side,
                taker_side=f.taker_side,
                timestamp=f.timestamp,
            )
            for f in result.fills
        ],
        order_flow=result.order_flow,
        quote_history=result.quote_history,
        book_snapshots=[
            BookSnapshotModel(
                timestamp=s.timestamp,
                best_bid=s.best_bid,
                best_ask=s.best_ask,
                bid_depth=s.bid_depth,
                ask_depth=s.ask_depth,
                spread=s.spread,
            )
            for s in result.book_snapshots
        ],
        hedge_prices=result.hedge_prices,
        accounting_events=result.accounting_events,
        summary=result.summary,
        audit=AuditModel(
            passed=audit.passed,
            cash_error=audit.cash_error,
            inventory_error=audit.inventory_error,
            equity_identity_error=audit.equity_identity_error,
            event_count=audit.event_count,
        ),
        benchmark=BenchmarkModel(
            wall_time_ms=round(elapsed_ms, 2),
            steps_per_sec=round(steps / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0,
            fills_count=len(result.fills),
            events_count=len(result.accounting_events),
        ),
        config_hash=config_hash(config),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _discover_configs() -> dict[str, dict]:
    configs: dict[str, dict] = {}
    for path in sorted((ROOT / "configs").glob("*.yaml")):
        try:
            raw = load_config(path)
            if "agent" not in raw:
                continue
            validate_config(raw, source=str(path))
            configs[path.stem] = raw
        except Exception:
            continue
    return configs
