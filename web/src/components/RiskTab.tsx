import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { motion } from "framer-motion";
import type { SimulationResult } from "../types";

interface Props {
  result: SimulationResult;
}

export default function RiskTab({ result }: Props) {
  const riskMetrics = [
    { metric: "VaR 95", value: Number(result.summary.var_95).toFixed(2), icon: "!" },
    { metric: "CVaR 95", value: Number(result.summary.cvar_95).toFixed(2), icon: "!!" },
    { metric: "Max Drawdown", value: Number(result.summary.max_drawdown).toFixed(2), icon: "\u2193" },
    { metric: "Max Inventory", value: String(Math.round(Number(result.summary.max_inventory))), icon: "\u03A3" },
    { metric: "Sortino", value: Number(result.summary.sortino).toFixed(4), icon: "\u03C3" },
    { metric: "Hit Rate", value: `${(Number(result.summary.hit_rate) * 100).toFixed(1)}%`, icon: "\u2713" },
  ];

  const flowData = result.order_flow.map((f) => ({
    t: f.timestamp,
    net_qty: (f.buy_qty ?? 0) - (f.sell_qty ?? 0),
  }));

  const tooltipStyle = {
    contentStyle: {
      background: "rgba(17, 24, 39, 0.95)",
      border: "1px solid rgba(148, 163, 184, 0.1)",
      borderRadius: "12px",
      fontSize: "11px",
      color: "#f9fafb",
      backdropFilter: "blur(16px)",
      boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
    },
    cursor: { stroke: "rgba(99, 102, 241, 0.3)", strokeWidth: 1 },
  };

  return (
    <div className="space-y-4">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="glass rounded-2xl p-5"
      >
        <h3 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mb-4">
          Risk Surface
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {riskMetrics.map((m, i) => (
            <motion.div
              key={m.metric}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
              className="glass rounded-xl p-3.5 hover:bg-white/[0.03] transition-colors group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/50">
                  {m.metric}
                </div>
                <span className="text-[10px] font-mono text-primary/40 opacity-0 group-hover:opacity-100 transition-opacity">
                  {m.icon}
                </span>
              </div>
              <div className="text-sm font-bold font-mono tabular-nums text-foreground">
                {m.value}
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1, ease: "easeOut" }}
        className="glass rounded-2xl p-5"
      >
        <h3 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mb-4">
          Order Flow (Net Buy - Sell)
        </h3>
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={flowData}>
            <defs>
              <linearGradient id="flowGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
            <XAxis dataKey="t" stroke="transparent" tick={{ fontSize: 10, fill: "#64748b" }} />
            <YAxis stroke="transparent" tick={{ fontSize: 10, fill: "#64748b" }} />
            <Tooltip {...tooltipStyle} formatter={(value) => [String(Number(value).toFixed(1)), "Net Qty"]} />
            <Area type="monotone" dataKey="net_qty" stroke="#06b6d4" strokeWidth={1.5} fill="url(#flowGrad)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </motion.div>
    </div>
  );
}
