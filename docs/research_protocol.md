# Research Protocol

Use this protocol when producing results for the README or interviews.

## 1. Data

1. Ingest real or synthetic L1/tick data.
2. Verify timestamp continuity, missing values, spread distribution, and return
   outliers.
3. Store processed parquet and the calibration report under `data/processed/`.

## 2. Calibration

1. Fit volatility and jump parameters on training windows only.
2. Compare simulated and realized spread, realized volatility, and return
   autocorrelation.
3. Keep calibrated parameters with the experiment artifacts.

## 3. Strategy Comparison

1. Run paired comparisons on identical price paths.
2. Report P&L, Sharpe, Sortino, VaR, CVaR, drawdown, fill rate, inventory, effective
   spread, realized spread, markout, and adverse-selection cost.
3. Inspect fill ledgers and `accounting_audit.csv` for accounting consistency before
   trusting aggregate P&L.

## 4. Robustness

1. Run Monte Carlo seed sweeps for confidence bands.
2. Run walk-forward validation so calibration and evaluation windows are separated.
3. Run stress replay on the worst realized-return windows.
4. Run scenario matrices for latency, fee, toxicity, liquidity, and jump-risk regimes.
5. Run parameter optimization only inside training windows or synthetic research
   regimes; evaluate selected parameters out of sample.
6. Use `pairwise_statistics.csv` to check paired differences, confidence intervals,
   and probability of outperformance.
7. Treat a strategy as promising only if it survives these checks.

## 5. Multi-Asset Hedging

1. Use correlated price paths for hedged strategy runs.
2. Report hedge beta and hedge value separately from spread-capture economics.
3. Compare hedged and unhedged drawdowns under the same scenario matrix.

## 6. Presentation

Use `runs/<workflow>/report.md`, `summary.csv`, equity plots, and per-agent ledgers
as the source of truth for README tables and discussion.
