import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
  Line,
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

export default function OverviewTab({ result }: Props) {
  const equityData = result.equity_curve.map((v, i) => ({ t: i, equity: v }));
  const inventoryData = result.inventory_curve.map((v, i) => ({ t: i, inventory: v }));

  const midData = result.mid_prices.map((v, i) => {
    const row: Record<string, number> = { t: i, mid_price: v };
    if (result.hedge_prices[i] !== undefined) row.hedge_price = result.hedge_prices[i];
    return row;
  });

  const breakdownData = [
    { component: "Spread", value: Number(result.summary.spread_capture), fill: "#818cf8" },
    { component: "Inventory", value: Number(result.summary.inventory_mark_to_market), fill: "#a78bfa" },
    { component: "Adverse Sel.", value: Number(result.summary.adverse_selection), fill: "#f87171" },
    { component: "Fees", value: Number(result.summary.fees_and_rebates), fill: "#fbbf24" },
    { component: "Hedge", value: Number(result.summary.hedge_value) || 0, fill: "#22d3ee" },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <ChartCard title="Equity Curve" delay={0}>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={equityData}>
            <defs>
              <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
            <XAxis dataKey="t" stroke="transparent" tick={{ fontSize: 10, fill: "#64748b" }} />
            <YAxis stroke="transparent" tick={{ fontSize: 10, fill: "#64748b" }} tickFormatter={(v: number) => `$${v.toFixed(0)}`} />
            <Tooltip {...tooltipStyle} formatter={(value) => [`$${Number(value).toFixed(2)}`, "Equity"]} />
            <Area type="monotone" dataKey="equity" stroke="#6366f1" strokeWidth={2} fill="url(#equityGradient)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Inventory" delay={0.05}>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={inventoryData}>
            <defs>
              <linearGradient id="invGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
            <XAxis dataKey="t" stroke="transparent" tick={{ fontSize: 10, fill: "#64748b" }} />
            <YAxis stroke="transparent" tick={{ fontSize: 10, fill: "#64748b" }} />
            <Tooltip {...tooltipStyle} formatter={(value) => [String(value), "Inventory"]} />
            <Area type="monotone" dataKey="inventory" stroke="#06b6d4" strokeWidth={2} fill="url(#invGradient)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Mid Price" delay={0.1}>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={midData}>
            <defs>
              <linearGradient id="midGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
            <XAxis dataKey="t" stroke="transparent" tick={{ fontSize: 10, fill: "#64748b" }} />
            <YAxis stroke="transparent" tick={{ fontSize: 10, fill: "#64748b" }} tickFormatter={(v: number) => `$${v.toFixed(1)}`} />
            <Tooltip {...tooltipStyle} />
            <Area type="monotone" dataKey="mid_price" stroke="#22c55e" strokeWidth={1.5} fill="url(#midGradient)" dot={false} name="Mid Price" />
            {result.hedge_prices.length > 0 && (
              <Line type="monotone" dataKey="hedge_price" stroke="#f59e0b" dot={false} strokeWidth={1.5} strokeDasharray="4 4" name="Hedge Price" />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="P&L Breakdown" delay={0.15}>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={breakdownData} barCategoryGap="20%">
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.06)" />
            <XAxis dataKey="component" stroke="transparent" tick={{ fontSize: 9, fill: "#64748b" }} />
            <YAxis stroke="transparent" tick={{ fontSize: 10, fill: "#64748b" }} tickFormatter={(v: number) => `$${v.toFixed(0)}`} />
            <Tooltip {...tooltipStyle} formatter={(value) => [`$${Number(value).toFixed(2)}`, "Value"]} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {breakdownData.map((entry, idx) => (
                <rect key={idx} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
