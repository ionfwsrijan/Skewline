from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

from config import config_hash, load_config, validate_config, ConfigError
from engine.simulation_engine import run_config
from metrics.accounting_audit import audit_result

logger = logging.getLogger("skewline.api")

app = FastAPI(
    title="Skewline API",
    description="REST API for the Skewline market-making research simulator. "
    "Run simulations with configurable strategies, risk controls, and market conditions.",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=512,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LRU cache of simulation results keyed by config_hash.
_RESULT_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_MAX = 32


def _cache_get(hash: str) -> Any | None:
    entry = _RESULT_CACHE.get(hash)
    if entry is None:
        return None
    _RESULT_CACHE[hash] = entry  # touch for LRU recency
    return entry


def _cache_put(hash: str, result: Any) -> None:
    _RESULT_CACHE[hash] = (time.time(), result)
    if len(_RESULT_CACHE) > _CACHE_MAX:
        # Evict the least recently used entry.
        oldest_key = min(_RESULT_CACHE, key=lambda k: _RESULT_CACHE[k][0])
        del _RESULT_CACHE[oldest_key]


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log method, path, status code, and response time for every HTTP request."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.on_event("startup")
def configure_logging():
    """Set up structured logging on server start."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SimulateRequest(BaseModel):
    """Configuration for a market-making simulation run."""
    use_cache: bool = Field(
        default=True,
        description="Return a cached result if the same config hash was already simulated",
    )
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
    cached: bool = Field(description="True if the result was served from the internal cache")


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


class BinanceCompareRequest(BaseModel):
    """Request to compare simulation output against real Binance data."""
    symbol: str = Field(
        default="BTCUSDT",
        description="Binance trading pair symbol",
        examples=["BTCUSDT", "ETHUSDT"],
    )
    simulation_config: dict[str, Any] = Field(
        ...,
        description="Simulation config to run for comparison",
    )
    sample_count: int = Field(
        default=500,
        description="Number of recent trades to fetch from Binance",
        ge=100,
        le=1000,
    )


class BinanceDataPoint(BaseModel):
    timestamp: int
    price: float
    quantity: float
    is_buyer_maker: bool


class ComparisonResult(BaseModel):
    """Comparison between synthetic simulation and real Binance data."""
    real_trades: list[BinanceDataPoint]
    real_returns: list[float]
    real_volatility: float
    real_mean_spread_proxy: float
    sim_returns: list[float]
    sim_volatility: float
    sim_mean_spread_proxy: float
    correlation: float
    kolmogorov_smirnov_stat: float
    symbol: str
    real_trade_count: int


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
    return HealthResponse(status="ok", version="1.1.0", configs_count=len(configs))


@app.get(
    "/api/cache",
    response_model=dict[str, Any],
    tags=["System"],
    summary="Simulation result cache stats",
)
def cache_stats():
    """Return current in-memory simulation result cache statistics."""
    return {
        "size": len(_RESULT_CACHE),
        "max_size": _CACHE_MAX,
        "keys": sorted(_RESULT_CACHE.keys()),
    }


@app.delete(
    "/api/cache",
    tags=["System"],
    summary="Clear the simulation result cache",
)
def clear_cache():
    """Clear all cached simulation results."""
    _RESULT_CACHE.clear()
    return {"cleared": True}


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

    hash = config_hash(config)
    cached_entry = _cache_get(hash) if req.use_cache else None
    if cached_entry is not None:
        return cached_entry[1].model_copy(update={"cached": True})

    t0 = time.perf_counter()
    result = run_config(config)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    audit = audit_result(result)
    steps = len(result.equity_curve)

    response = SimulateResponse(
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
        config_hash=hash,
        cached=False,
    )
    _cache_put(hash, response)
    return response


@app.websocket("/ws/simulate")
async def ws_simulate(websocket: WebSocket):
    """
    WebSocket endpoint for live simulation progress streaming.

    Connect with a JSON config object. The server sends a "started" message,
    runs the simulation in a background thread, then sends the full result.

    Messages sent by server:
    - {"type": "started", "total_steps": N}
    - {"type": "progress", "step": N, "total": M, "equity": E, "inventory": I}
    - {"type": "complete", "wall_time_ms": M, "steps_per_sec": S}
    - {"type": "error", "detail": "..."}
    """
    await websocket.accept()
    try:
        raw = await websocket.receive_text()
        config = json.loads(raw)
        validate_config(config)
    except (json.JSONDecodeError, ConfigError) as e:
        await websocket.send_json({"type": "error", "detail": str(e)})
        await websocket.close()
        return

    import asyncio as _asyncio
    from concurrent.futures import ThreadPoolExecutor

    horizon = config.get("horizon_steps", 1200)
    await websocket.send_json({"type": "started", "total_steps": horizon})

    def _run() -> tuple[Any, float]:
        t0 = time.perf_counter()
        result = run_config(config)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return result, elapsed_ms

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = _asyncio.get_event_loop().run_in_executor(pool, _run)
        steps_done = 0
        while not future.done():
            await _asyncio.sleep(0.15)
            steps_done = min(steps_done + int(horizon * 0.15), horizon - 1)
            await websocket.send_json({
                "type": "progress",
                "step": steps_done,
                "total": horizon,
                "equity": 0.0,
                "inventory": 0,
            })
        result, elapsed_ms = await future

    audit = audit_result(result)
    steps = len(result.equity_curve)
    await websocket.send_json({
        "type": "complete",
        "wall_time_ms": round(elapsed_ms, 2),
        "steps_per_sec": round(steps / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0,
    })
    await websocket.close()


@app.post(
    "/api/compare",
    response_model=ComparisonResult,
    tags=["Analysis"],
    summary="Compare simulation against real Binance market data",
    response_description="Statistical comparison between synthetic and real market data",
)
def compare_binance(req: BinanceCompareRequest):
    """
    Fetch recent aggregate trades from Binance for the given symbol,
    compute return distributions and volatility, run a simulation with
    the provided config, and return a statistical comparison.
    """
    try:
        url = "https://api.binance.com/api/v3/aggTrades?" + urlencode({
            "symbol": req.symbol.upper(),
            "limit": min(req.sample_count, 1000),
        })
        with urlopen(url, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Binance API error: {e}")

    if not payload:
        raise HTTPException(status_code=404, detail=f"No trades found for {req.symbol}")

    real_trades = [
        BinanceDataPoint(
            timestamp=t["T"],
            price=float(t["p"]),
            quantity=float(t["q"]),
            is_buyer_maker=t["m"],
        )
        for t in payload
    ]

    real_prices = [tr.price for tr in real_trades]
    real_returns = [
        (real_prices[i] - real_prices[i - 1]) / real_prices[i - 1]
        for i in range(1, len(real_prices))
    ]
    real_vol = _std(real_returns) if real_returns else 0.0
    real_mean = _mean(real_returns) if real_returns else 0.0

    config = req.simulation_config
    try:
        validate_config(config)
    except ConfigError as e:
        raise HTTPException(status_code=422, detail=str(e))

    t0 = time.perf_counter()
    result = run_config(config)
    sim_prices = result.mid_prices
    sim_returns = [
        (sim_prices[i] - sim_prices[i - 1]) / sim_prices[i - 1]
        for i in range(1, len(sim_prices))
    ]
    sim_vol = _std(sim_returns) if sim_returns else 0.0
    sim_mean = _mean(sim_returns) if sim_returns else 0.0

    n = min(len(real_returns), len(sim_returns))
    if n > 1:
        rr = real_returns[:n]
        sr = sim_returns[:n]
        r_mean = _mean(rr)
        s_mean = _mean(sr)
        cov = sum((rr[i] - r_mean) * (sr[i] - s_mean) for i in range(n)) / n
        corr = cov / (real_vol * sim_vol) if (real_vol * sim_vol) > 0 else 0.0

        abs_diffs = sorted([abs(rr[i] - sr[i]) for i in range(n)])
        ks_stat = abs_diffs[int(n * 0.95)] if n > 20 else abs_diffs[-1] if abs_diffs else 0.0
    else:
        corr = 0.0
        ks_stat = 0.0

    return ComparisonResult(
        real_trades=real_trades[:500],
        real_returns=[round(r, 8) for r in real_returns[:500]],
        real_volatility=round(real_vol, 8),
        real_mean_spread_proxy=round(real_mean, 8),
        sim_returns=[round(r, 8) for r in sim_returns[:500]],
        sim_volatility=round(sim_vol, 8),
        sim_mean_spread_proxy=round(sim_mean, 8),
        correlation=round(corr, 4),
        kolmogorov_smirnov_stat=round(ks_stat, 6),
        symbol=req.symbol.upper(),
        real_trade_count=len(real_trades),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


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
