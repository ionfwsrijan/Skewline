from __future__ import annotations

import csv
import json
from pathlib import Path
import sqlite3
from typing import Any


class ExperimentLogger:
    def __init__(self, run_dir: str | Path = "runs") -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.run_dir / "experiments.csv"
        self.sqlite_path = self.run_dir / "experiments.sqlite"

    def log(
        self,
        run_name: str,
        params: dict[str, Any],
        metrics: dict[str, float],
        run_hash: str | None = None,
    ) -> None:
        row = {
            "run_name": run_name,
            "run_hash": run_hash or "",
            "params_json": json.dumps(params, sort_keys=True),
            **{k: float(v) for k, v in metrics.items()},
        }
        self._append_csv(row)
        self._append_sqlite(row)

    def _append_csv(self, row: dict[str, Any]) -> None:
        rows: list[dict[str, Any]] = []
        fieldnames = list(row.keys())
        if self.csv_path.exists() and self.csv_path.stat().st_size > 0:
            with self.csv_path.open("r", newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                existing_fieldnames = reader.fieldnames or []
                fieldnames = list(dict.fromkeys(existing_fieldnames + fieldnames))
                rows = list(reader)
        rows.append(row)
        with self.csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _append_sqlite(self, row: dict[str, Any]) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            metric_columns = [k for k in row if k not in {"run_name", "run_hash", "params_json"}]
            conn.execute(
                "CREATE TABLE IF NOT EXISTS experiments "
                "(run_name TEXT, run_hash TEXT, params_json TEXT, metrics_json TEXT)"
            )
            columns = {info[1] for info in conn.execute("PRAGMA table_info(experiments)")}
            if "run_hash" not in columns:
                conn.execute("ALTER TABLE experiments ADD COLUMN run_hash TEXT DEFAULT ''")
            conn.execute(
                "INSERT INTO experiments "
                "(run_name, run_hash, params_json, metrics_json) VALUES (?, ?, ?, ?)",
                (
                    row["run_name"],
                    row["run_hash"],
                    row["params_json"],
                    json.dumps({k: row[k] for k in metric_columns}, sort_keys=True),
                ),
            )
