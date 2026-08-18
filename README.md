<div align="center">

<!-- Animated Logo -->
<img src="https://raw.githubusercontent.com/ionfwsrijan/Skewline/main/web/public/logo.svg" width="120" alt="Skewline Logo" />

# Skewline

### Research-Grade Market Making Simulator

**Compare classical, signal-driven, deep RL, and hedged quoting strategies
under realistic microstructure constraints — with production-ready tooling.**

[![CI](https://github.com/ionfwsrijan/Skewline/actions/workflows/ci.yml/badge.svg)](https://github.com/ionfwsrijan/Skewline/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

<br />

<img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
<img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
<img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" />
<img src="https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white" />
<img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />

</div>

---

<br />

## Features

<table>
<tr>
<td align="center" width="33%">

### Strategy Zoo
**7 strategies** head-to-head:
Naive, Avellaneda-Stoikov, GLFT,
Flow Imbalance, Tabular RL, **DQN**,
Hedged Multi-Asset

</td>
<td align="center" width="33%">

### Realistic Engine
Limit order book, stochastic latency,
maker/taker fees, adverse selection,
partial fills, risk controls

</td>
<td align="center" width="33%">

### Deep Analytics
P&L decomposition, accounting audits,
Sharpe/CVaR/drawdown, execution quality,
effective spread, markout analysis

</td>
</tr>
<tr>
<td align="center" width="33%">

### Live Dashboard
React + Tailwind glassmorphism UI,
Recharts animations, WebSocket
streaming, real-time progress

</td>
<td align="center" width="33%">

### Binance Compare
Fetch real BTC/ETH/SOL trades,
run KS tests and correlation analysis,
overlay synthetic vs real distributions

</td>
<td align="center" width="33%">

### Production Ready
Docker compose, OpenAPI/Swagger docs,
CI pipelines, Railway/Vercel deploy,
benchmark timing on every run

</td>
</tr>
</table>

---

<br />

## Architecture

```mermaid
graph LR
    subgraph Engine
        A[Price Process<br/>Jump Diffusion] --> B[Order Flow<br/>Noise + Informed]
        B --> C[Latency Queue<br/>Stochastic Delay]
        C --> D[Limit Order Book<br/>Price-Time Priority]
        D --> E[Agent<br/>Quote Logic]
        E --> F[Risk Manager<br/>Position + Drawdown]
        F --> D
    end

    subgraph Metrics
        D --> G[P&L Decomposition]
        D --> H[Execution Quality]
        G --> I[Accounting Audit]
        H --> I
    end

    subgraph Dashboard
        I --> J[FastAPI REST<br/>+ WebSocket]
        J --> K[React + Tailwind UI]
        K --> L["Overview / Execution / Risk / Ledger / vs Binance"]
    end

    style A fill:#6366f1,stroke:#818cf8,color:#fff
    style E fill:#8b5cf6,stroke:#a78bfa,color:#fff
    style K fill:#06b6d4,stroke:#22d3ee,color:#fff
    style L fill:#f59e0b,stroke:#fbbf24,color:#000
```

<br />

---

## Strategy Zoo

<table>
<tr>
<td align="center">
<b>Naive Fixed-Spread</b><br/>
<sub>Baseline benchmark</sub>
</td>
<td align="center">
<b>Avellaneda-Stoikov</b><br/>
<sub>Optimal reservation price</sub>
</td>
<td align="center">
<b>GLFT</b><br/>
<sub>Finite inventory extension</sub>
</td>
</tr>
<tr>
<td align="center">
<b>Flow Imbalance</b><br/>
<sub>Order flow signal</sub>
</td>
<td align="center">
<b>Tabular RL</b><br/>
<sub>Q-learning (discrete)</sub>
</td>
<td align="center">
<b>DQN</b> <img src="https://img.shields.io/badge/-NEW-red" width="40" /><br/>
<sub>Numpy MLP, replay, target net</sub>
</td>
</tr>
<tr>
<td align="center" colspan="2">
<b>Hedged Multi-Asset</b><br/>
<sub>Cross-asset beta hedging</sub>
</td>
<td></td>
</tr>
</table>

<br />

---

## Quick Start

### One-command Docker launch
```bash
git clone https://github.com/ionfwsrijan/Skewline.git && cd Skewline
docker-compose up --build
```
Dashboard at `http://localhost:3000` · API docs at `http://localhost:8000/docs`

<br />

### Local development

```bash
# Backend
py -m pip install -e ".[dev]"
py -m pytest -q                         # 28+ tests

# API server
py -m uvicorn api.main:app --reload --port 8000

# React dashboard
cd web && npm install && npm run dev
```

Open **http://localhost:5173** — pick a strategy, tweak parameters, hit **Run Simulation** (or `Ctrl+Enter`).

<br />

### CLI usage
```bash
py main.py run --config configs/baseline_naive.yaml
py main.py compare --base-config configs/baseline_naive.yaml
py main.py sweep --base-config configs/avellaneda_stoikov.yaml
py main.py monte-carlo --config configs/baseline_naive.yaml --runs 20
py main.py train-rl --config configs/rl_agent.yaml --episodes 25
py main.py train-rl --config configs/dqn_agent.yaml --episodes 25
py main.py walk-forward --config configs/baseline_naive.yaml
py main.py stress --config configs/baseline_naive.yaml
py main.py scenario-matrix --config configs/baseline_naive.yaml
py main.py optimize --spec configs/optimization_avellaneda.yaml
```

<br />

---

## REST API

| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/api/health` | `GET` | Health check, version, config count |
| `/api/configs` | `GET` | List all YAML experiment configs |
| `/api/configs/{name}` | `GET` | Load a specific config |
| `/api/simulate` | `POST` | Run full simulation, return curves + metrics |
| `/ws/simulate` | `WS` | WebSocket with live progress streaming |
| `/api/compare` | `POST` | Compare against real Binance market data |
| `/docs` | `GET` | Interactive Swagger UI |

<details>
<summary><b>Example simulate request</b></summary>

```json
POST /api/simulate
{
  "config": {
    "seed": 7,
    "horizon_steps": 1200,
    "dt": 0.01,
    "initial_price": 100.0,
    "price_process": { "sigma": 0.18, "jump_intensity": 0.02 },
    "agent": { "type": "dqn", "hidden": 32, "lr": 0.0005 },
    "risk": { "max_position": 50, "max_drawdown": 2500 }
  }
}
```
</details>

<br />

---

## Metrics Reported

<table>
<tr>
<td>

**Risk Metrics**
- Sharpe Ratio
- Sortino Ratio
- VaR / CVaR (95%)
- Max Drawdown
- Hit Rate

</td>
<td>

**Execution Quality**
- Effective Spread (bps)
- Realized Spread (bps)
- Markout (5-step)
- Maker Fill Ratio
- Fill Rate

</td>
<td>

**Accounting**
- Total P&L
- Fee and Rebate Attribution
- Inventory Mark-to-Market
- Cash Reconstruction Audit
- Equity Identity Check

</td>
<td>

**Performance**
- Wall-clock time (ms)
- Steps per second
- Fill count
- Event count
- Config hash

</td>
</tr>
</table>

<br />

---

## Repository Structure

```
Skewline/
├── configs/                    YAML experiment definitions (7 strategies)
├── src/
│   ├── agents/                 Strategy zoo + DQN with numpy MLP
│   ├── engine/                 Simulation loop + risk manager
│   ├── market/                 Price process, LOB, calibration
│   ├── order_flow/             Noise + informed traders
│   ├── metrics/                P&L decomposition, execution quality
│   └── research/               Monte Carlo, walk-forward, scenarios
├── api/                        FastAPI REST + WebSocket backend
├── web/                        React + Tailwind + shadcn/ui frontend
├── tests/                      28+ pytest tests
├── data/                       Binance ingest + parquet pipeline
├── docker-compose.yml          Full stack orchestration
├── Dockerfile                  Python API image
├── railway.json                Railway deploy config
└── vercel.json                 Vercel deploy config
```

<br />

---

## Data Pipeline

```bash
# Download real Binance trades
py data/ingest.py --download-binance-symbol BTCUSDT --pages 5 --freq 1s

# Or use any CSV with timestamp + price columns
py data/ingest.py data/raw/ticks.csv --freq 1s --price-col price

# Calibrate flow parameters
py main.py calibrate-flow --data data/raw/ticks.csv
```

The pipeline resamples to the simulation grid, writes parquet, fits volatility and jump parameters via method-of-moments, and generates a calibration report.

<br />

---

<div align="center">

### Built with precision for quantitative research

Python 3.11+ &nbsp;&middot;&nbsp; FastAPI &nbsp;&middot;&nbsp; React &nbsp;&middot;&nbsp; NumPy &nbsp;&middot;&nbsp; Docker

<br />

*Skewline is a research simulator, not a production trading system.*

</div>
