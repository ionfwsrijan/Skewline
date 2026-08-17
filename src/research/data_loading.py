from __future__ import annotations

import csv
from pathlib import Path


def load_price_series(path: str | Path, price_col: str = "price") -> list[float]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        try:
            import pandas as pd
        except ModuleNotFoundError as exc:
            raise RuntimeError("pandas and pyarrow are required to read parquet files") from exc
        frame = pd.read_parquet(path)
        if price_col not in frame.columns:
            raise ValueError(f"Column '{price_col}' not found in {path}")
        return [float(value) for value in frame[price_col].dropna().tolist()]
    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or price_col not in reader.fieldnames:
            raise ValueError(f"Column '{price_col}' not found in {path}")
        return [float(row[price_col]) for row in reader if row.get(price_col)]
