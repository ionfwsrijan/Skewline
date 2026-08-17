# Architecture

MM Sim is organized as a flat `src/` Python project with small modules that map to
market-simulation concerns.

## Runtime Flow

1. `config.py` loads and validates YAML experiment definitions.
2. `engine/simulation_engine.py` builds the agent, price path, latency queue, order
   flow generators, fee model, risk manager, and limit order book.
3. The engine advances one step at a time:
   delayed quotes arrive, background liquidity refreshes, order flow crosses the
   book, fills update inventory/cash, risk controls run, and the agent submits the
   next quote.
4. Metrics summarize risk, P&L decomposition, execution quality, and accounting
   reconstruction errors.
5. Research utilities export fills, quotes, book snapshots, equity curves, summary
   tables, plots, and markdown reports.

## Core Boundaries

- `market/`: price process, calibration, and exchange-style book mechanics.
- `order_flow/`: stochastic and informed flow plus latency.
- `agents/`: interchangeable strategy implementations.
- `engine/`: simulation orchestration, fees, risk, and accounting updates.
- `metrics/`: reusable measurement functions.
- `research/`: experiment workflows such as batch, Monte Carlo, walk-forward, stress
  replay, scenario matrices, parameter optimization, synthetic data, and reporting.
- `dashboard/`: interactive Streamlit inspection layer.

## Reproducibility

Every validated config can be hashed with `config_hash`. CLI workflows log run
parameters, run hashes, and numeric metrics to CSV and SQLite. Research commands
write per-run ledgers under `runs/` so results can be audited after the fact.
