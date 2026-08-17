import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  Bar,
} from "recharts";
import { motion } from "framer-motion";
import type { SimulationResult } from "../types";

interface Props {
  result: SimulationResult;
}

function ChartCard({
  title,
  children,
  delay = 0,
}: {
  title: string;
  children: React.ReactNode;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: "easeOut" }}
      className="glass rounded-2xl p-5 hover:shadow-lg hover:shadow-primary/5 transition-shadow duration-300"
    >
      <h3 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mb-4">
        {title}
      </h3>
      {children}
    </motion.div>
  );
}

function DataTable({
  columns,
  rows,
  delay = 0,
}: {
  columns: { key: string; label: string; mono?: boolean }[];
  rows: Record<string, unknown>[];
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: "easeOut" }}
      className="glass rounded-2xl p-5 overflow-hidden"
    >
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-border/50">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="text-left py-2.5 px-3 text-[9px] font-bold uppercase tracking-widest text-muted-foreground/60"
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                className="border-b border-border/30 hover:bg-white/[0.02] transition-colors"
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`py-2 px-3 text-foreground/80 ${col.mono ? "font-mono tabular-nums" : ""}`}
                  >
                    {typeof row[col.key] === "number"
                      ? (row[col.key] as number).toFixed(
                          row[col.key] === Math.round(row[col.key] as number) ? 0 : 2
                        )
                      : String(row[col.key] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

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

export default function ExecutionTab({ result }: Props) {
  const spreadData = result.quote_history.map((q, i) => ({
    t: q.timestamp ?? i,
    quoted_spread: (q.ask_price ?? 0) - (q.bid_price ?? 0),
    lit_spread: result.book_snapshots[i]?.spread ?? 0,
    latency_delay: q.latency_delay_steps ?? 0,
  }));

  const fillColumns = [
    { key: "timestamp", label: "Time", mono: true },
    { key: "maker_side", label: "Side" },
    { key: "price", label: "Price", mono: true },
    { key: "quantity", label: "Qty", mono: true },
    { key: "maker_agent_id", label: "Maker" },
    { key: "taker_agent_id", label: "Taker" },
  ];
  const fillRows = result.fills.slice(-20).map((f) => ({
    timestamp: f.timestamp,
    maker_side: f.maker_side,
    price: f.price,
    quantity: f.quantity,
    maker_agent_id: f.maker_agent_id,
    taker_agent_id: f.taker_agent_id,
  }));

  const bookColumns = [
    { key: "timestamp", label: "Time", mono: true },
    { key: "best_bid", label: "Bid", mono: true },
    { key: "best_ask", label: "Ask", mono: true },
    { key: "spread", label: "Spread", mono: true },
    { key: "bid_depth", label: "Bid Depth", mono: true },
    { key: "ask_depth", label: "Ask Depth", mono: true },
  ];
  const bookRows = result.book_snapshots.slice(-20).map((s) => ({
    timestamp: s.timestamp,
    best_bid: s.best_bid,
    best_ask: s.best_ask,
    spread: s.spread,
    bid_depth: s.bid_depth,
    ask_depth: s.ask_depth,
  }));

  return (
    <div className="space-y-4">
      <ChartCard title="Spread & Latency" delay={0}>
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={spreadData}>
            <defs>
              <linearGradient id="spreadGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
            <XAxis dataKey="t" stroke="transparent" tick={{ fontSize: 10, fill: "#64748b" }} />
            <YAxis stroke="transparent" tick={{ fontSize: 10, fill: "#64748b" }} />
            <Tooltip {...tooltipStyle} />
            <Area type="monotone" dataKey="quoted_spread" stroke="#6366f1" strokeWidth={1.5} fill="url(#spreadGrad)" dot={false} name="Quoted Spread" />
            <Line type="monotone" dataKey="lit_spread" stroke="#22c55e" dot={false} strokeWidth={1.5} name="Lit Spread" />
            <Bar dataKey="latency_delay" fill="rgba(239, 68, 68, 0.3)" barSize={2} name="Latency" />
          </ComposedChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DataTable columns={fillColumns} rows={fillRows} delay={0.05} />
        <DataTable columns={bookColumns} rows={bookRows} delay={0.1} />
      </div>
    </div>
  );
}
