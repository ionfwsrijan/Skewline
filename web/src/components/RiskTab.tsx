import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { SimulationResult } from "../types";

interface Props {
  result: SimulationResult;
}

export default function RiskTab({ result }: Props) {
  const riskMetrics = [
    { metric: "VaR 95", value: Number(result.summary.var_95).toFixed(2) },
    { metric: "CVaR 95", value: Number(result.summary.cvar_95).toFixed(2) },
    { metric: "Max Drawdown", value: Number(result.summary.max_drawdown).toFixed(2) },
    { metric: "Max Inventory", value: String(Math.round(Number(result.summary.max_inventory))) },
    { metric: "Sortino", value: Number(result.summary.sortino).toFixed(4) },
    { metric: "Hit Rate", value: `${(Number(result.summary.hit_rate) * 100).toFixed(1)}%` },
  ];

  const flowData = result.order_flow.map((f) => ({
    t: f.timestamp,
    net_qty: (f.buy_qty ?? 0) - (f.sell_qty ?? 0),
    buy_qty: f.buy_qty ?? 0,
    sell_qty: f.sell_qty ?? 0,
  }));

  const tooltipStyle = {
    contentStyle: {
      background: "#1e293b",
      border: "1px solid #334155",
      borderRadius: "8px",
      fontSize: "12px",
      color: "#f1f5f9",
    },
  };

  return (
    <div className="space-y-4">
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-dim)] mb-3">
          Risk Surface
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {riskMetrics.map((m) => (
            <div key={m.metric} className="bg-[var(--color-bg)] rounded-lg p-3 border border-[var(--color-border)]">
              <div className="text-[10px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-1">
                {m.metric}
              </div>
              <div className="text-sm font-bold font-mono text-[var(--color-text)]">
                {m.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-dim)] mb-3">
          Order Flow (Net Buy - Sell)
        </h3>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={flowData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="t" stroke="#64748b" tick={{ fontSize: 10 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
            <Tooltip {...tooltipStyle} />
            <Line type="monotone" dataKey="net_qty" stroke="#06b6d4" dot={false} strokeWidth={1.5} name="Net Qty" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
