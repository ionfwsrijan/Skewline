import { useState, useEffect, useCallback, lazy, Suspense } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { SimulationConfig, SimulationResult } from "./types";
import { fetchConfigs, runSimulation } from "./api";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import MetricCard from "./components/MetricCard";
import { Activity, AlertCircle, Zap, Menu } from "lucide-react";
import { useTheme } from "./hooks/useTheme";
import ThemeToggle from "./components/ThemeToggle";

const OverviewTab = lazy(() => import("./components/OverviewTab"));
const ExecutionTab = lazy(() => import("./components/ExecutionTab"));
const RiskTab = lazy(() => import("./components/RiskTab"));
const LedgerTab = lazy(() => import("./components/LedgerTab"));
const ComparisonTab = lazy(() => import("./components/ComparisonTab"));

function TabLoader() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

type Tab = "overview" | "execution" | "risk" | "ledger" | "compare";

export default function App() {
  const [configs, setConfigs] = useState<Record<string, SimulationConfig>>({});
  const [selectedConfig, setSelectedConfig] = useState<string>("");
  const [config, setConfig] = useState<SimulationConfig | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [configsLoading, setConfigsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();

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
    { id: "compare", label: "vs Binance" },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed lg:static inset-y-0 left-0 z-50 transform transition-transform duration-200 ease-in-out
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
      `}>
        <Sidebar
          configs={configs}
          selectedConfig={selectedConfig}
          config={config}
          onConfigChange={(name) => { handleConfigChange(name); setSidebarOpen(false); }}
          onParamChange={handleParamChange}
          onRun={() => { handleRun(); setSidebarOpen(false); }}
          loading={loading}
          configsLoading={configsLoading}
        />
      </div>

      <main className="flex-1 overflow-y-auto mesh-bg dot-grid min-w-0 relative">
        {/* Desktop theme toggle */}
        <div className="hidden lg:block fixed top-5 right-5 z-30">
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
        </div>
        {/* Mobile top bar */}
        <div className="lg:hidden flex items-center gap-3 px-4 py-3 border-b border-border/50">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg glass border border-border/50 text-foreground"
          >
            <Menu className="w-5 h-5" />
          </button>
          <h1 className="text-sm font-bold text-foreground">Skewline</h1>
          <div className="ml-auto">
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
          </div>
        </div>

        <div className="max-w-[1600px] mx-auto px-4 md:px-6 py-5">
          <AnimatePresence mode="wait">
            {result ? (
              <motion.div
                key="results"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Header result={result} selectedConfig={selectedConfig} />

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

                <div className="flex gap-1 mb-5 border-b border-border/50 overflow-x-auto scrollbar-none">
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
                    <Suspense fallback={<TabLoader />}>
                      {activeTab === "overview" && <OverviewTab result={result} />}
                      {activeTab === "execution" && <ExecutionTab result={result} />}
                      {activeTab === "risk" && <RiskTab result={result} />}
                      {activeTab === "ledger" && <LedgerTab result={result} />}
                      {activeTab === "compare" && <ComparisonTab selectedConfig={selectedConfig} />}
                    </Suspense>
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
                <div className="text-center max-w-lg">
                  {loading ? (
                    <div className="flex flex-col items-center gap-5">
                      <div className="relative">
                        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center gradient-border">
                          <Activity className="w-9 h-9 text-primary animate-pulse" />
                        </div>
                        <div className="absolute inset-0 rounded-2xl border border-primary/10 animate-ping opacity-20" />
                      </div>
                      <div>
                        <p className="text-foreground font-semibold text-lg">Running simulation</p>
                        <p className="text-muted-foreground text-sm mt-1">
                          Processing {config?.horizon_steps ?? "\u2026"} steps
                        </p>
                      </div>
                      <div className="w-56 h-1.5 bg-muted rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500 rounded-full"
                          initial={{ width: "0%" }}
                          animate={{ width: "100%" }}
                          transition={{ duration: 3, ease: "easeInOut" }}
                        />
                      </div>
                      <p className="text-[10px] text-muted-foreground/40 font-mono">this may take a moment</p>
                    </div>
                  ) : error ? (
                    <div className="flex flex-col items-center gap-4">
                      <div className="w-16 h-16 rounded-2xl bg-red-500/10 flex items-center justify-center glow-red gradient-border">
                        <AlertCircle className="w-8 h-8 text-red-400" />
                      </div>
                      <div>
                        <p className="text-red-400 font-medium text-lg">{error}</p>
                        <p className="text-muted-foreground text-sm mt-2">
                          Start the API server first:
                        </p>
                        <code className="inline-block mt-2 glass px-3 py-1.5 rounded-xl text-xs font-mono text-foreground/80">
                          py -m uvicorn api.main:app --port 8000
                        </code>
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
                      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                      className="flex flex-col items-center gap-6"
                    >
                      <div className="relative">
                        <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-indigo-500 via-purple-600 to-indigo-700 flex items-center justify-center shadow-2xl shadow-indigo-500/30">
                          <svg className="w-12 h-12 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                            <path d="M3 3v18h18" strokeLinecap="round" strokeLinejoin="round" />
                            <path d="M7 16l4-8 4 4 4-10" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </div>
                        <div className="absolute -inset-8 bg-gradient-to-r from-indigo-500/20 via-purple-500/10 to-indigo-500/20 rounded-[2rem] blur-2xl animate-pulse-slow" />
                      </div>

                      <div className="space-y-2 text-center">
                        <h1 className="text-3xl font-bold text-foreground tracking-tight">
                          <span className="gradient-text">Skewline</span>
                        </h1>
                        <p className="text-muted-foreground text-sm leading-relaxed max-w-sm">
                          Research-grade market-making simulator with strategy diagnostics,
                          execution quality analysis, and accounting audits.
                        </p>
                      </div>

                      <div className="flex items-center gap-6 text-xs text-muted-foreground/60">
                        <div className="flex items-center gap-2">
                          <Zap className="w-3.5 h-3.5 text-amber-500/60" />
                          <span>6 strategies</span>
                        </div>
                        <div className="w-px h-3 bg-border" />
                        <div className="flex items-center gap-2">
                          <Activity className="w-3.5 h-3.5 text-indigo-500/60" />
                          <span>Real-time analytics</span>
                        </div>
                        <div className="w-px h-3 bg-border" />
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[10px] bg-primary/10 text-primary/60 px-1.5 py-0.5 rounded">Ctrl+Enter</span>
                          <span>to run</span>
                        </div>
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
