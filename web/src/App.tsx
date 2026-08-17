import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { SimulationConfig, SimulationResult } from "./types";
import { fetchConfigs, runSimulation } from "./api";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import MetricCard from "./components/MetricCard";
import OverviewTab from "./components/OverviewTab";
import ExecutionTab from "./components/ExecutionTab";
import RiskTab from "./components/RiskTab";
import LedgerTab from "./components/LedgerTab";
import { Activity, AlertCircle } from "lucide-react";

type Tab = "overview" | "execution" | "risk" | "ledger";

export default function App() {
  const [configs, setConfigs] = useState<Record<string, SimulationConfig>>({});
  const [selectedConfig, setSelectedConfig] = useState<string>("");
  const [config, setConfig] = useState<SimulationConfig | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [configsLoading, setConfigsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  useEffect(() => {
    setConfigsLoading(true);
    fetchConfigs()
      .then((c) => {
        setConfigs(c);
        const names = Object.keys(c);
        if (names.length > 0) {
          const def = names.includes("baseline_naive") ? "baseline_naive" : names[0];
          setSelectedConfig(def);
          setConfig(c[def]);
        }
      })
      .catch(() => setError("Failed to connect to API. Is the backend running?"))
      .finally(() => setConfigsLoading(false));
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleRun();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  const handleConfigChange = useCallback(
    (name: string) => {
      setSelectedConfig(name);
      setConfig(configs[name]);
      setResult(null);
      setError(null);
    },
    [configs]
  );

  const handleParamChange = useCallback(
    (path: string, value: number | boolean) => {
      setConfig((prev) => {
        if (!prev) return prev;
        const next: Record<string, unknown> = JSON.parse(JSON.stringify(prev));
        const keys = path.split(".");
        let obj = next;
        for (let i = 0; i < keys.length - 1; i++) {
          obj = obj[keys[i]] as Record<string, unknown>;
        }
        obj[keys[keys.length - 1]] = value;
        return next as unknown as SimulationConfig;
      });
    },
    []
  );

  const handleRun = useCallback(async () => {
    if (!config || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await runSimulation(config);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  }, [config, loading]);

  const fmt = {
    money: (v: number) => {
      const sign = v < 0 ? "-" : "";
      return `${sign}$${Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    },
    num: (v: number, d = 2) =>
      v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }),
    pct: (v: number) => `${(v * 100).toFixed(1)}%`,
    bps: (v: number) => `${v.toFixed(2)} bps`,
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "execution", label: "Execution" },
    { id: "risk", label: "Risk" },
    { id: "ledger", label: "Ledger" },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar
        configs={configs}
        selectedConfig={selectedConfig}
        config={config}
        onConfigChange={handleConfigChange}
        onParamChange={handleParamChange}
        onRun={handleRun}
        loading={loading}
        configsLoading={configsLoading}
      />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[1600px] mx-auto px-6 py-5">
          <AnimatePresence mode="wait">
            {result ? (
              <motion.div
                key="results"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Header result={result} selectedConfig={selectedConfig} configHash={result.config_hash} />

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-5">
                  <MetricCard label="P&L" value={fmt.money(Number(result.summary.total_pnl))} positive={Number(result.summary.total_pnl) >= 0} delay={0} />
                  <MetricCard label="Sharpe" value={fmt.num(Number(result.summary.sharpe))} positive={Number(result.summary.sharpe) >= 0} delay={0.02} />
                  <MetricCard label="Drawdown" value={fmt.money(Number(result.summary.max_drawdown))} positive={false} delay={0.04} />
                  <MetricCard label="CVaR 95" value={fmt.money(Number(result.summary.cvar_95))} positive={false} delay={0.06} />
                  <MetricCard label="Hit Rate" value={fmt.pct(Number(result.summary.hit_rate))} delay={0.08} />
                  <MetricCard label="Fills" value={String(Math.round(Number(result.summary.fill_count)))} delay={0.1} />
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
                  <MetricCard label="Max Inv" value={String(Math.round(Number(result.summary.max_inventory)))} delay={0.12} />
                  <MetricCard label="Fill Rate" value={fmt.pct(Number(result.summary.fill_rate))} delay={0.14} />
                  <MetricCard label="Eff Spread" value={fmt.bps(Number(result.summary.effective_spread_bps))} delay={0.16} />
                  <MetricCard label="Realized 5" value={fmt.bps(Number(result.summary.realized_spread_5_bps))} delay={0.18} />
                  <MetricCard label="Markout 5" value={fmt.bps(Number(result.summary.markout_5_bps))} delay={0.2} />
                  <MetricCard label="Maker Ratio" value={fmt.pct(Number(result.summary.maker_fill_ratio))} delay={0.22} />
                </div>

                <div className="flex gap-1 mb-5 border-b border-border/50">
                  {tabs.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => setActiveTab(t.id)}
                      className={`px-5 py-3 text-sm font-semibold transition-all relative ${
                        activeTab === t.id
                          ? "text-foreground"
                          : "text-muted-foreground hover:text-foreground/70"
                      }`}
                    >
                      {t.label}
                      {activeTab === t.id && (
                        <motion.div
                          layoutId="activeTab"
                          className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                          transition={{ type: "spring", stiffness: 500, damping: 30 }}
                        />
                      )}
                    </button>
                  ))}
                </div>

                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeTab}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2 }}
                  >
                    {activeTab === "overview" && <OverviewTab result={result} />}
                    {activeTab === "execution" && <ExecutionTab result={result} />}
                    {activeTab === "risk" && <RiskTab result={result} />}
                    {activeTab === "ledger" && <LedgerTab result={result} />}
                  </motion.div>
                </AnimatePresence>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center justify-center h-[60vh]"
              >
                <div className="text-center max-w-md">
                  {loading ? (
                    <div className="flex flex-col items-center gap-5">
                      <div className="relative">
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center">
                          <Activity className="w-8 h-8 text-primary animate-pulse" />
                        </div>
                        <div className="absolute inset-0 rounded-2xl border border-primary/20 animate-ping opacity-20" />
                      </div>
                      <div>
                        <p className="text-foreground font-semibold text-lg">Running simulation</p>
                        <p className="text-muted-foreground text-sm mt-1">
                          Processing {config?.horizon_steps ?? "\u2026"} steps
                        </p>
                      </div>
                      <div className="w-48 h-1.5 bg-muted rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                          initial={{ width: "0%" }}
                          animate={{ width: "100%" }}
                          transition={{ duration: 3, ease: "easeInOut" }}
                        />
                      </div>
                    </div>
                  ) : error ? (
                    <div className="flex flex-col items-center gap-4">
                      <div className="w-16 h-16 rounded-2xl bg-red-500/10 flex items-center justify-center glow-red">
                        <AlertCircle className="w-8 h-8 text-red-400" />
                      </div>
                      <div>
                        <p className="text-red-400 font-medium">{error}</p>
                        <p className="text-muted-foreground text-xs mt-2">
                          Start the API with:{" "}
                          <code className="glass px-2 py-1 rounded-lg text-[11px] font-mono text-foreground/80">
                            py -m uvicorn api.main:app --port 8000
                          </code>
                        </p>
                      </div>
                    </div>
                  ) : configsLoading ? (
                    <div className="flex flex-col items-center gap-4">
                      <div className="w-12 h-12 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                      <p className="text-muted-foreground text-sm">Loading strategies\u2026</p>
                    </div>
                  ) : (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5 }}
                      className="flex flex-col items-center gap-5"
                    >
                      <div className="relative">
                        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-2xl shadow-indigo-500/30">
                          <svg className="w-10 h-10 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                            <path d="M3 3v18h18" strokeLinecap="round" strokeLinejoin="round" />
                            <path d="M7 16l4-8 4 4 4-10" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </div>
                        <div className="absolute -inset-4 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-3xl blur-2xl" />
                      </div>
                      <div>
                        <h2 className="text-2xl font-bold text-foreground mb-2">
                          Market Making{" "}
                          <span className="gradient-text">Research Terminal</span>
                        </h2>
                        <p className="text-muted-foreground text-sm leading-relaxed">
                          Select a strategy, adjust parameters, and run to see diagnostics.
                        </p>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground/60">
                        <kbd className="glass px-2.5 py-1 rounded-lg font-mono text-foreground/60 border border-border/50">
                          Ctrl+Enter
                        </kbd>
                        <span>to run</span>
                      </div>
                    </motion.div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
