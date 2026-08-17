# Skewline

## What it is

Skewline is a reproducible market-making research environment for comparing classical,
signal-driven, learned, and hedged quoting strategies under realistic microstructure
constraints. The simulator combines calibrated jump-diffusion and correlated
multi-asset price paths, a price-time-priority limit order book, stochastic noise and
informed order flow, stochastic latency, maker/taker economics, risk controls, P&L
decomposition, execution-quality metrics, accounting audits, walk-forward validation,
scenario matrices, experiment tracking, and a Streamlit dashboard.

The goal is to answer a practical research question: when market makers face stale
quotes, adverse selection, finite inventory limits, and fees, which quoting policies
produce the best risk-adjusted P&L, and under which market regimes do they fail?

## Repository Map

```text
configs/                 YAML experiment definitions
data/ingest.py            CSV tick/L1 ingest, resampling, parquet output, calibration report
src/market/              price process, calibration, limit order book
src/order_flow/          noise traders, informed traders, latency queue
src/agents/              strategy zoo behind one common quote interface
src/engine/              simulation loop, risk manager, fees
src/metrics/             P&L decomposition, risk stats, validation helpers
src/research/            Monte Carlo, reports, synthetic data, walk-forward tools
src/experiment_tracking/ CSV and SQLite run logger
api/                      FastAPI REST backend for the React dashboard
web/                       React + Tailwind CSS frontend dashboard
dashboard/app.py           Streamlit interactive dashboard (legacy)
tests/                    pytest coverage for matching, P&L, agents, risk, price process
main.py                   CLI entry point
```

## Methodology

The engine runs a time-stepped event loop:

1. Delayed quotes reach the exchange through the latency queue.
2. Background displayed liquidity refreshes around the mid.
3. Noise and informed market orders arrive.
3. The limit order book matches orders using price-time priority with partial fills.
4. Maker inventory, cash, fees, rebates, and equity are updated.
5. The agent observes order flow, cancels stale resting quotes, and submits new quotes.
6. The risk manager checks position and drawdown limits and can flatten inventory.
7. Metrics and experiment records are written for comparison.

All experiment parameters live in `configs/*.yaml`; the code is deliberately driven
by config files rather than hardcoded strategy settings.

## Data And Calibration

`data/ingest.py` can either download Binance aggregate trades into `data/raw/` or
accept any CSV tick/L1 export with a `timestamp` and `price` column. Optional `bid`
and `ask` columns are used to compute realized spreads.

```bash
python data/ingest.py --download-binance-symbol ETHUSDT --pages 5 --freq 1s
python data/ingest.py data/raw/sample_ticks.csv --freq 1s --price-col price --bid-col bid --ask-col ask
python main.py calibrate-flow --data data/raw/sample_ticks.csv --output data/processed/order_flow_calibration.csv
```

The pipeline resamples to the simulation grid, writes parquet to `data/processed/`,
fits volatility and jump parameters using a method-of-moments routine, and writes a
calibration report next to the parquet file. The calibration module also compares
basic microstructure statistics such as spread, realized volatility, and lagged
return autocorrelation.

## Strategy Zoo

Implemented agents:

- Naive fixed-spread baseline.
- Avellaneda-Stoikov reservation-price and optimal-spread model.
- Gueant-Lehalle-Fernandez-Tapia-style finite-inventory extension.
- Order-flow-imbalance-aware signal strategy.
- Tabular Q-learning agent with online discrete-action updates.
- Hedged multi-asset agent that offsets inventory through a correlated second asset
  path with estimated beta and hedge P&L attribution.

Each agent implements the same interface and can be run against identical price and
order-flow conditions for paired comparison.

## Metrics

The simulator reports:

- Total P&L and equity curve.
- Spread capture.
- Inventory mark-to-market.
- Adverse-selection cost.
- Fees and rebates.
- Sharpe, Sortino, VaR, CVaR, hit rate, max drawdown, max inventory, fill count, and fill rate.
- Effective spread, realized spread, five-step markout, maker-fill ratio, and displayed-spread diagnostics.
- Per-run accounting ledgers with cash/inventory reconstruction audits.

Experiment results are logged to both `runs/experiments.csv` and
`runs/experiments.sqlite`.

## Quick Start

```bash
python -m pip install -e ".[dev]"
pytest -q
python main.py run --config configs/baseline_naive.yaml
python main.py compare --base-config configs/baseline_naive.yaml
python main.py sweep --base-config configs/avellaneda_stoikov.yaml
python main.py monte-carlo --config configs/baseline_naive.yaml --runs 20
python main.py train-rl --config configs/rl_agent.yaml --episodes 25
python main.py demo-data --output data/raw/synthetic_l1.csv --steps 3600
python main.py walk-forward --config configs/baseline_naive.yaml --data data/raw/synthetic_l1.csv --train-size 1000 --test-size 300
python main.py stress --config configs/baseline_naive.yaml --data data/raw/synthetic_l1.csv --window-size 300 --top-n 3
python main.py scenario-matrix --config configs/baseline_naive.yaml --scenarios configs/scenario_matrix.yaml
python main.py optimize --spec configs/optimization_avellaneda.yaml
streamlit run dashboard/app.py

# React Dashboard (recommended)
pip install fastapi uvicorn
cd web && npm install
# Terminal 1: API backend
py -m uvicorn api.main:app --reload --port 8000
# Terminal 2: React frontend
cd web && npm run dev
```

## Current Results Template

After running `python main.py batch`, review `runs/batch/report.md`,
`runs/batch/summary.csv`, and the per-agent fill/book/quote ledgers.

| Strategy | P&L | Sharpe | Max drawdown | Fill rate | Max inventory |
| --- | ---: | ---: | ---: | ---: | ---: |
| Naive fixed-spread | TBD | TBD | TBD | TBD | TBD |
| Avellaneda-Stoikov | TBD | TBD | TBD | TBD | TBD |
| GLFT | TBD | TBD | TBD | TBD | TBD |
| Flow imbalance | TBD | TBD | TBD | TBD | TBD |
| Tabular Q-learning RL | TBD | TBD | TBD | TBD | TBD |
| Hedged multi-asset | TBD | TBD | TBD | TBD | TBD |

## Validation Plan

- Walk-forward splits separate calibration/training windows from test windows.
- Stress tests replay the worst realized-return windows from ingested historical data.
- Monte Carlo sweeps estimate seed sensitivity and confidence bands.
- Scenario matrices compare named regimes: latency shock, toxic flow, fee shock,
  liquidity drought, and jumpy news.
- Parameter optimization runs YAML-defined grids and ranks candidates by objective
  metrics such as Sharpe or drawdown.
- Pairwise bootstrap statistics are written for comparison reports so strategy
  differences are evaluated with confidence intervals, not only leaderboards.
- RL policies are trained across episodes and persisted as JSON Q-tables.
- Accounting audit files reconstruct primary cash and inventory from event ledgers.
- Simulated spreads, volatility, and return autocorrelation are compared with the
  realized data sample before strategy conclusions are trusted.
- Sensitivity sweeps vary risk aversion, spread multiplier, informed-flow ratio,
  inventory limits, fee/rebate settings, and latency.

## Limitations

This is an intentionally compact research simulator, not a production exchange
replica. The order book models price-time priority and partial fills, but it does not
yet include every real exchange detail such as hidden liquidity, auction states,
self-trade prevention, order amendments, or venue-specific queue rules. The RL agent
does online tabular Q-learning; serious RL experiments should add held-out seeds,
richer state features, and a Stable-Baselines3 or similar backend.

## Future Work

- Add native Binance/Coinbase/Databento download connectors with cached raw files.
- Expand GLFT calibration of arrival intensities from empirical fill curves.
- Add market-impact-aware hedging and multi-asset covariance calibration.
- Train PPO and compare against the tabular policy and closed-form strategies.
- Add richer dashboard views for order-book depth, quote history, and stress replay.
