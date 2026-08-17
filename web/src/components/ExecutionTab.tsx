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

function ChartCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-4">
      <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-dim)] mb-3">
        {title}
      </h3>
      {children}
    </div>
  );
}

function Table({
  columns,
  rows,
}: {
  columns: string[];
  rows: Record<string, unknown>[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-[var(--color-border)]">
            {columns.map((col) => (
              <th
                key={col}
                className="text-left py-2 px-2 text-[var(--color-text-muted)] font-medium uppercase tracking-wider"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-[var(--color-border)]/50 hover:bg-[var(--color-bg-card-hover)]">
              {columns.map((col) => (
                <td key={col} className="py-1.5 px-2 font-mono text-[var(--color-text)]">
                  {typeof row[col] === "number"
                    ? (row[col] as number).toFixed(row[col] === Math.round(row[col] as number) ? 0 : 2)
                    : String(row[col] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const tooltipStyle = {
  contentStyle: {
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: "8px",
    fontSize: "12px",
    color: "#f1f5f9",
  },
};

export default function ExecutionTab({ result }: Props) {
  const quoteData = result.quote_history.map((q, i) => ({
    t: q.timestamp ?? i,
    quoted_spread: (q.ask_price ?? 0) - (q.bid_price ?? 0),
    latency_delay: q.latency_delay_steps ?? 0,
  }));

  const bookData = result.book_snapshots.map((s) => ({
    t: s.timestamp,
    lit_spread: s.spread ?? 0,
  }));

  const spreadData = quoteData.map((q, i) => ({
    ...q,
    lit_spread: bookData[i]?.lit_spread ?? 0,
  }));

  const fillColumns = ["timestamp", "maker_side", "price", "quantity", "maker_agent_id", "taker_agent_id"];
  const fillRows = result.fills.slice(-20).map((f) => ({
    timestamp: f.timestamp,
    maker_side: f.maker_side,
    price: f.price,
    quantity: f.quantity,
    maker_agent_id: f.maker_agent_id,
    taker_agent_id: f.taker_agent_id,
  }));

  const bookColumns = ["timestamp", "best_bid", "best_ask", "spread", "bid_depth", "ask_depth"];
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
      <ChartCard title="Spread & Latency">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={spreadData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="t" stroke="#64748b" tick={{ fontSize: 10 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
            <Tooltip {...tooltipStyle} />
            <Line type="monotone" dataKey="quoted_spread" stroke="#3b82f6" dot={false} strokeWidth={1.5} name="Quoted Spread" />
            <Line type="monotone" dataKey="lit_spread" stroke="#22c55e" dot={false} strokeWidth={1.5} name="Lit Spread" />
            <Line type="monotone" dataKey="latency_delay" stroke="#ef4444" dot={false} strokeWidth={1.5} name="Latency Delay" />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-dim)] mb-3">
            Recent Fills
          </h3>
          <Table columns={fillColumns} rows={fillRows} />
        </div>
        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-dim)] mb-3">
            Book Snapshots
          </h3>
          <Table columns={bookColumns} rows={bookRows} />
        </div>
      </div>
    </div>
  );
}
