from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import config_hash, load_config, validate_config
from engine.simulation_engine import run_config
from metrics.accounting_audit import audit_result


app = FastAPI(title="MM Sim API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulateRequest(BaseModel):
    config: dict


class SimulateResponse(BaseModel):
    agent_id: str
    equity_curve: list[float]
    inventory_curve: list[int]
    cash_curve: list[float]
    mid_prices: list[float]
    fills: list[dict]
    order_flow: list[dict]
    quote_history: list[dict]
    book_snapshots: list[dict]
    hedge_prices: list[float]
    accounting_events: list[dict]
    summary: dict
    audit: dict
    config_hash: str


@app.get("/api/configs")
def list_configs():
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


@app.get("/api/configs/{name}")
def get_config(name: str):
    path = ROOT / "configs" / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Config '{name}' not found")
    raw = load_config(path)
    validate_config(raw, source=str(path))
    return raw


@app.post("/api/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest):
    config = req.config
    try:
        validate_config(config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = run_config(config)
    audit = audit_result(result)

    return SimulateResponse(
        agent_id=result.agent_id,
        equity_curve=result.equity_curve,
        inventory_curve=result.inventory_curve,
        cash_curve=result.cash_curve,
        mid_prices=result.mid_prices,
        fills=[
            {
                "maker_agent_id": f.maker_agent_id,
                "taker_agent_id": f.taker_agent_id,
                "price": f.price,
                "quantity": f.quantity,
                "maker_side": f.maker_side,
                "taker_side": f.taker_side,
                "timestamp": f.timestamp,
            }
            for f in result.fills
        ],
        order_flow=result.order_flow,
        quote_history=result.quote_history,
        book_snapshots=[
            {
                "timestamp": s.timestamp,
                "best_bid": s.best_bid,
                "best_ask": s.best_ask,
                "bid_depth": s.bid_depth,
                "ask_depth": s.ask_depth,
                "spread": s.spread,
            }
            for s in result.book_snapshots
        ],
        hedge_prices=result.hedge_prices,
        accounting_events=result.accounting_events,
        summary=result.summary,
        audit={
            "passed": audit.passed,
            "cash_error": audit.cash_error,
            "inventory_error": audit.inventory_error,
            "equity_identity_error": audit.equity_identity_error,
            "event_count": audit.event_count,
        },
        config_hash=config_hash(config),
    )
