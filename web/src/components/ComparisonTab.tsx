import { useState } from "react";
import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { runComparison, fetchConfigs } from "../api";
import type { ComparisonResult } from "../types";
import { BarChart3, TrendingUp, Activity } from "lucide-react";

const container = { hidden: {}, show: { transition: { staggerChildren: 0.06 } } };
const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 200, damping: 20 } },
};

const symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"];

function buildHistBins(data: number[], bins: number = 30) {
  if (!data.length) return [];
  const min = Math.min(...data);
  const max = Math.max(...data);
  const step = (max - min) / bins || 1;
  const counts = Array.from({ length: bins }, (_, i) => ({
    bin: Number((min + i * step).toFixed(6)),
    count: 0,
    binLabel: `${(min + i * step).toFixed(5)}`,
  }));
  for (const v of data) {
    const idx = Math.min(bins - 1, Math.floor((v - min) / step));
    counts[idx].count++;
  }
  return counts;
}

interface ComparisonTabProps {
  selectedConfig: string;
}

export default function ComparisonTab({ selectedConfig }: ComparisonTabProps) {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCompare = async () => {
    setLoading(true);
    setError(null);
    try {
      const configs = await fetchConfigs();
      const config = configs[selectedConfig];
      if (!config) throw new Error("Config not found");
      const res = await runComparison(symbol, config, 500);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  };

  const realHist = result ? buildHistBins(result.real_returns, 40) : [];
  const simHist = result ? buildHistBins(result.sim_returns, 40) : [];
  const histData = realHist.map((r, i) => ({
    bin: r.binLabel,
    Real: r.count,
    Sim: simHist[i]?.count ?? 0,
  }));

  const priceTimeSeries = result
    ? result.real_trades.slice(0, 200).map((t, i) => ({
        i,
        price: t.price,
      }))
    : [];

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-5">
      <motion.div variants={item}>
        <Card className="glass gradient-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-primary" />
              Binance Real Data Comparison
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3 flex-wrap">
              <div>
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Symbol</label>
                <select
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="glass border border-border/50 rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                >
                  {symbols.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleCompare}
                disabled={loading}
                className="mt-4 px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-sm font-semibold hover:shadow-lg hover:shadow-indigo-500/25 transition-all disabled:opacity-50"
              >
                {loading ? "Fetching & comparing..." : "Run Comparison"}
              </button>
              {error && (
                <p className="text-red-400 text-xs mt-4">{error}</p>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {result && (
        <>
          <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Real Volatility", value: (result.real_volatility * 100).toFixed(3) + "%", color: "text-amber-400" },
              { label: "Sim Volatility", value: (result.sim_volatility * 100).toFixed(3) + "%", color: "text-indigo-400" },
              { label: "Correlation", value: result.correlation.toFixed(4), color: "text-emerald-400" },
              { label: "KS Statistic", value: result.kolmogorov_smirnov_stat.toFixed(5), color: "text-rose-400" },
            ].map((m) => (
              <Card key={m.label} className="glass gradient-border">
                <CardContent className="p-3">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{m.label}</p>
                  <p className={`text-lg font-bold mt-1 ${m.color}`}>{m.value}</p>
                </CardContent>
              </Card>
            ))}
          </motion.div>

          <motion.div variants={item}>
            <Card className="glass gradient-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold flex items-center gap-2">
                  <TrendingUp className="w-3.5 h-3.5 text-amber-500" />
                  Return Distribution (Real vs Simulated)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={histData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="bin" tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }} interval={Math.floor(histData.length / 8)} />
                    <YAxis tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }} />
                    <Tooltip
                      contentStyle={{
                        background: "rgba(15,15,25,0.95)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 12,
                        fontSize: 11,
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Bar dataKey="Real" fill="rgba(245,158,11,0.6)" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="Sim" fill="rgba(99,102,241,0.6)" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div variants={item}>
            <Card className="glass gradient-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold flex items-center gap-2">
                  <Activity className="w-3.5 h-3.5 text-amber-500" />
                  Binance Real Price Series ({result.symbol})
                  <Badge variant="secondary" className="ml-auto text-[9px]">{result.real_trade_count} trades</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={priceTimeSeries}>
                    <defs>
                      <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="i" tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }} />
                    <YAxis
                      domain={["dataMin", "dataMax"]}
                      tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }}
                      tickFormatter={(v: number) => v.toFixed(0)}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "rgba(15,15,25,0.95)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 12,
                        fontSize: 11,
                      }}
                      formatter={(v) => [`$${Number(v).toFixed(2)}`, "Price"]}
                    />
                    <Area
                      type="monotone"
                      dataKey="price"
                      stroke="#f59e0b"
                      strokeWidth={1.5}
                      fill="url(#priceGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div variants={item}>
            <Card className="glass gradient-border">
              <CardContent className="p-4">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Method</p>
                    <p className="text-xs text-foreground/70 mt-1">KS two-sample test + Pearson correlation</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Interpretation</p>
                    <p className="text-xs text-foreground/70 mt-1">
                      {result.correlation > 0.7
                        ? "Strong correlation - sim closely tracks real"
                        : result.correlation > 0.3
                          ? "Moderate correlation - directional alignment present"
                          : "Weak correlation - distributions differ significantly"}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Real Trades</p>
                    <p className="text-xs text-foreground/70 mt-1">{result.real_trade_count} agg trades from Binance</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </>
      )}
    </motion.div>
  );
}
