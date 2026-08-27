import type { SimulationResult } from "./types";

export function exportSimulationCSV(result: SimulationResult): void {
  const rows: string[] = [];

  rows.push(
    [
      "step",
      "mid_price",
      "equity",
      "cash",
      "inventory",
      "hedge_price",
      "best_bid",
      "best_ask",
      "spread",
      "bid_depth",
      "ask_depth",
    ].join(",")
  );

  const n = result.equity_curve.length;
  for (let i = 0; i < n; i++) {
    const snap = result.book_snapshots[i];
    rows.push(
      [
        i,
        result.mid_prices[i]?.toFixed(6) ?? "",
        result.equity_curve[i]?.toFixed(2) ?? "",
        result.cash_curve[i]?.toFixed(2) ?? "",
        result.inventory_curve[i] ?? "",
        result.hedge_prices[i]?.toFixed(6) ?? "",
        snap?.best_bid?.toFixed(6) ?? "",
        snap?.best_ask?.toFixed(6) ?? "",
        snap?.spread?.toFixed(6) ?? "",
        snap?.bid_depth ?? "",
        snap?.ask_depth ?? "",
      ].join(",")
    );
  }

  if (result.fills.length > 0) {
    rows.push("");
    rows.push("--- fills ---");
    rows.push("timestamp,price,quantity,maker_side,taker_side,maker_agent,taker_agent");
    for (const f of result.fills) {
      rows.push(
        [
          f.timestamp,
          f.price.toFixed(6),
          f.quantity,
          f.maker_side,
          f.taker_side,
          f.maker_agent_id,
          f.taker_agent_id,
        ].join(",")
      );
    }
  }

  const blob = new Blob([rows.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `skewline_${result.agent_id}_${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
