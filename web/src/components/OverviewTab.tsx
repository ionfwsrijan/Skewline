import {
  LineChart,
  Line,
  BarChart,
  Bar,
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

const tooltipStyle = {
  contentStyle: {
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: "8px",
    fontSize: "12px",
    color: "#f1f5f9",
  },
};

export default function OverviewTab({ result }: Props) {
  const equityData = result.equity_curve.map((v, i) => ({
    t: i,
    equity: v,
  }));

  const inventoryData = result.inventory_curve.map((v, i) => ({
    t: i,
    inventory: v,
  }));

  const midData = result.mid_prices.map((v, i) => {
    const row: Record<string, number> = { t: i, mid_price: v };
    if (result.hedge_prices[i] !== undefined) {
      row.hedge_price = result.hedge_prices[i];
    }
    return row;
  });

  const breakdownData = [
    { component: "Spread Capture", value: Number(result.summary.spread_capture) },
    { component: "Inventory MTM", value: Number(result.summary.inventory_mark_to_market) },
    { component: "Adverse Selection", value: Number(result.summary.adverse_selection) },
    { component: "Fees & Rebates", value: Number(result.summary.fees_and_rebates) },
    { component: "Hedge Value", value: Number(result.summary.hedge_value) || 0 },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <ChartCard title="Equity Curve">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={equityData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="t" stroke="#64748b" tick={{ fontSize: 10 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
            <Tooltip {...tooltipStyle} />
            <Line type="monotone" dataKey="equity" stroke="#3b82f6" dot={false} strokeWidth={1.5} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Inventory">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={inventoryData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="t" stroke="#64748b" tick={{ fontSize: 10 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
            <Tooltip {...tooltipStyle} />
            <Line type="monotone" dataKey="inventory" stroke="#06b6d4" dot={false} strokeWidth={1.5} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Mid Price">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={midData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="t" stroke="#64748b" tick={{ fontSize: 10 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
            <Tooltip {...tooltipStyle} />
            <Line type="monotone" dataKey="mid_price" stroke="#22c55e" dot={false} strokeWidth={1.5} />
            {result.hedge_prices.length > 0 && (
              <Line type="monotone" dataKey="hedge_price" stroke="#f59e0b" dot={false} strokeWidth={1.5} />
            )}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="P&L Breakdown">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={breakdownData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="component" stroke="#64748b" tick={{ fontSize: 10 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
            <Tooltip {...tooltipStyle} />
            <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
