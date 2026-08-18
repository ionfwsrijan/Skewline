import type { SimulationResult } from "../types";
import { motion } from "framer-motion";

interface HeaderProps {
  result: SimulationResult;
  selectedConfig: string;
}

export default function Header({ result, selectedConfig }: HeaderProps) {
  const pills = [
    { label: "strategy", value: result.agent_id, color: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20" },
    { label: "config", value: selectedConfig, color: "bg-purple-500/10 text-purple-400 border-purple-500/20" },
    { label: "seed", value: String(result.summary.seed ?? ""), color: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20" },
    { label: "steps", value: String(result.equity_curve.length), color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
    { label: "time", value: `${result.benchmark.wall_time_ms.toFixed(0)}ms`, color: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
    { label: "perf", value: `${(result.benchmark.steps_per_sec / 1000).toFixed(1)}k/s`, color: "bg-rose-500/10 text-rose-400 border-rose-500/20" },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="relative overflow-hidden rounded-2xl mb-6"
    >
      <div className="absolute inset-0 bg-gradient-to-r from-indigo-600/10 via-purple-600/5 to-cyan-600/5" />
      <div className="absolute top-0 right-0 w-80 h-80 bg-indigo-500/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
      <div className="absolute bottom-0 left-1/3 w-40 h-40 bg-purple-500/5 rounded-full blur-2xl translate-y-1/2" />
      <div className="relative glass-strong rounded-2xl px-6 py-5 gradient-border">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-foreground mb-1 tracking-tight">
              <span className="gradient-text">Skewline</span>{" "}
              Research Terminal
            </h1>
            <p className="text-sm text-muted-foreground">
              Strategy diagnostics, execution quality, risk, inventory & accounting audit
            </p>
          </div>
          <div className="flex items-center gap-2 mt-1 glass px-2.5 py-1 rounded-lg">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-slow shadow-lg shadow-emerald-400/50" />
            <span className="text-[9px] font-bold text-emerald-400 uppercase tracking-widest">Live</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 mt-4">
          {pills.map((p, i) => (
            <motion.span
              key={p.label}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: 0.1 + i * 0.05 }}
              className={`inline-flex items-center gap-1.5 text-[10px] font-semibold px-2.5 py-1 rounded-lg border ${p.color}`}
            >
              <span className="opacity-50">{p.label}</span>
              <span className="font-mono">{p.value}</span>
            </motion.span>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
