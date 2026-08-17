from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from market.calibration import fit_price_process_from_prices, microstructure_stats, write_calibration_report


def download_binance_agg_trades(
    symbol: str,
    output: str | Path,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    pages: int = 1,
    limit: int = 1000,
) -> Path:
    """Download Binance aggregate trades into raw CSV."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    next_start = start_time_ms
    for _ in range(max(1, pages)):
        params: dict[str, object] = {"symbol": symbol.upper(), "limit": min(limit, 1000)}
        if next_start is not None:
            params["startTime"] = next_start
        if end_time_ms is not None:
            params["endTime"] = end_time_ms
        url = "https://api.binance.com/api/v3/aggTrades?" + urlencode(params)
        with urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not payload:
            break
        for trade in payload:
            rows.append(
                {
                    "timestamp": trade["T"],
                    "price": trade["p"],
                    "quantity": trade["q"],
                    "is_buyer_maker": trade["m"],
                    "agg_trade_id": trade["a"],
                }
            )
        next_start = int(payload[-1]["T"]) + 1
        if end_time_ms is not None and next_start >= end_time_ms:
            break
    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["timestamp", "price", "quantity", "is_buyer_maker", "agg_trade_id"],
        )
        writer.writeheader()
        writer.writerows(rows)
    return output


def ingest_csv(
    source: str | Path,
    output: str | Path = "data/processed/resampled.parquet",
    freq: str = "1s",
    price_col: str = "price",
    bid_col: str | None = None,
    ask_col: str | None = None,
) -> Path:
    import pandas as pd

    source = Path(source)
    output = Path(output)
    df = pd.read_csv(source)
    if "timestamp" in df.columns:
        numeric_ts = pd.to_numeric(df["timestamp"], errors="coerce")
        if numeric_ts.notna().all() and numeric_ts.max() > 10_000_000_000:
            df["timestamp"] = pd.to_datetime(numeric_ts, unit="ms", utc=True)
        else:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp")
    elif not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.date_range("2024-01-01", periods=len(df), freq=freq)
    resampled = df.resample(freq).last().ffill()
    if price_col not in resampled:
        if bid_col and ask_col and bid_col in resampled and ask_col in resampled:
            resampled[price_col] = (resampled[bid_col] + resampled[ask_col]) / 2
        else:
            raise ValueError(f"Could not find price column '{price_col}'.")
    if bid_col and ask_col and bid_col in resampled and ask_col in resampled:
        resampled["spread"] = resampled[ask_col] - resampled[bid_col]
    else:
        resampled["spread"] = 0.0
    output.parent.mkdir(parents=True, exist_ok=True)
    resampled.to_parquet(output)
    params = fit_price_process_from_prices(resampled[price_col].tolist(), dt=1.0)
    stats = microstructure_stats(resampled[price_col].tolist(), resampled["spread"].tolist())
    write_calibration_report(output.with_suffix(".calibration.csv"), params, stats)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest tick or L1 data into simulation-ready parquet.")
    parser.add_argument("source", nargs="?")
    parser.add_argument("--output", default="data/processed/resampled.parquet")
    parser.add_argument("--freq", default="1s")
    parser.add_argument("--price-col", default="price")
    parser.add_argument("--bid-col", default=None)
    parser.add_argument("--ask-col", default=None)
    parser.add_argument("--download-binance-symbol", default=None)
    parser.add_argument("--start-time-ms", type=int, default=None)
    parser.add_argument("--end-time-ms", type=int, default=None)
    parser.add_argument("--pages", type=int, default=1)
    args = parser.parse_args(argv)
    source = args.source
    if args.download_binance_symbol:
        source = str(
            download_binance_agg_trades(
                args.download_binance_symbol,
                f"data/raw/{args.download_binance_symbol.upper()}_agg_trades.csv",
                args.start_time_ms,
                args.end_time_ms,
                args.pages,
            )
        )
    if source is None:
        parser.error("provide a source CSV or --download-binance-symbol")
    path = ingest_csv(source, args.output, args.freq, args.price_col, args.bid_col, args.ask_col)
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
