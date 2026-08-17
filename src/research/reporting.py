from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from engine.simulation_engine import SimulationResult
from metrics.accounting_audit import audit_result
from metrics.stat_tests import paired_comparison


SUMMARY_COLUMNS = [
    "agent",
    "total_pnl",
    "sharpe",
    "sortino",
    "max_drawdown",
    "max_inventory",
    "fill_count",
    "fill_rate",
    "avg_quoted_spread",
    "avg_lit_spread",
    "effective_spread_bps",
    "realized_spread_5_bps",
    "markout_5_bps",
    "maker_fill_ratio",
    "hedge_value",
    "hedge_beta",
    "spread_capture",
    "adverse_selection",
    "fees_and_rebates",
]


def write_result_artifacts(result: SimulationResult, output_dir: str | Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_curve(output_dir / "equity.csv", result.equity_curve, "equity")
    _write_curve(output_dir / "inventory.csv", result.inventory_curve, "inventory")
    _write_dict_rows(output_dir / "order_flow.csv", result.order_flow)
    _write_dict_rows(output_dir / "quotes.csv", result.quote_history)
    _write_book_snapshots(output_dir / "book_snapshots.csv", result.book_snapshots)
    _write_fills(output_dir / "fills.csv", result.fills)
    _write_dict_rows(output_dir / "accounting_events.csv", result.accounting_events)
    _write_accounting_audit(output_dir / "accounting_audit.csv", result)


def write_comparison_report(
    results: Iterable[SimulationResult],
    output_dir: str | Path,
    title: str = "Market Making Strategy Comparison",
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = list(results)
    summary_path = output_dir / "summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        for result in results:
            writer.writerow({key: result.summary.get(key, "") for key in SUMMARY_COLUMNS})
    _write_pairwise_statistics(output_dir / "pairwise_statistics.csv", results)
    plot_path = output_dir / "equity_curves.png"
    _plot_equity_curves(results, plot_path)
    report_path = output_dir / "report.md"
    report_path.write_text(_markdown_report(results, title, plot_path.name), encoding="utf-8")
    return report_path


def _markdown_report(results: list[SimulationResult], title: str, plot_name: str) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ranked = sorted(results, key=lambda r: float(r.summary.get("sharpe", 0.0)), reverse=True)
    best = ranked[0] if ranked else None
    lines = [
        f"# {title}",
        "",
        f"Generated: {generated}",
        "",
        "![Equity curves](equity_curves.png)",
        "",
        "## Summary",
        "",
        "| Agent | P&L | Sharpe | Drawdown | Fill rate | Max inventory |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in ranked:
        s = result.summary
        lines.append(
            "| {agent} | {pnl:.2f} | {sharpe:.2f} | {dd:.2f} | {fr:.3f} | {inv:.0f} |".format(
                agent=s.get("agent", result.agent_id),
                pnl=float(s.get("total_pnl", 0.0)),
                sharpe=float(s.get("sharpe", 0.0)),
                dd=float(s.get("max_drawdown", 0.0)),
                fr=float(s.get("fill_rate", 0.0)),
                inv=float(s.get("max_inventory", 0.0)),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                f"The best run by Sharpe was `{best.agent_id}`. "
                "Review the fill logs, adverse-selection component, and stress windows before "
                "treating that result as economically robust."
                if best
                else "No results were provided."
            ),
            "",
            "## Files",
            "",
            "- `summary.csv`: numeric comparison table.",
            f"- `{plot_name}`: equity curve comparison.",
            "- `<agent>/fills.csv`: maker/taker fill ledger.",
            "- `<agent>/book_snapshots.csv`: spread and displayed-depth diagnostics.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_curve(path: Path, values: list[float] | list[int], name: str) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["timestamp", name])
        writer.writeheader()
        for timestamp, value in enumerate(values):
            writer.writerow({"timestamp": timestamp, name: value})


def _write_dict_rows(path: Path, rows: list[dict[str, float]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_book_snapshots(path: Path, snapshots) -> None:
    fieldnames = ["timestamp", "best_bid", "best_ask", "bid_depth", "ask_depth", "spread"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for snapshot in snapshots:
            writer.writerow({key: getattr(snapshot, key) for key in fieldnames})


def _write_fills(path: Path, fills) -> None:
    fieldnames = [
        "timestamp",
        "maker_agent_id",
        "taker_agent_id",
        "maker_side",
        "taker_side",
        "price",
        "quantity",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for fill in fills:
            writer.writerow({key: getattr(fill, key) for key in fieldnames})


def _write_accounting_audit(path: Path, result: SimulationResult) -> None:
    audit = audit_result(result)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["passed", "cash_error", "inventory_error", "equity_identity_error", "event_count"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "passed": audit.passed,
                "cash_error": audit.cash_error,
                "inventory_error": audit.inventory_error,
                "equity_identity_error": audit.equity_identity_error,
                "event_count": audit.event_count,
            }
        )


def _write_pairwise_statistics(path: Path, results: list[SimulationResult]) -> None:
    fieldnames = [
        "left",
        "right",
        "mean_difference",
        "t_stat",
        "bootstrap_ci_low",
        "bootstrap_ci_high",
        "probability_left_better",
        "observations",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for i, left in enumerate(results):
            for right in results[i + 1 :]:
                comparison = paired_comparison(
                    left.agent_id,
                    left.equity_curve,
                    right.agent_id,
                    right.equity_curve,
                )
                writer.writerow({key: getattr(comparison, key) for key in fieldnames})


def _plot_equity_curves(results: list[SimulationResult], path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        path.write_text("matplotlib is not installed; equity plot unavailable.", encoding="utf-8")
        return
    plt.figure(figsize=(10, 6))
    for result in results:
        plt.plot(result.equity_curve, label=result.agent_id, linewidth=1.5)
    plt.title("Equity Curves")
    plt.xlabel("Step")
    plt.ylabel("Equity")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
