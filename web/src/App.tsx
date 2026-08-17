import { useState, useEffect, useCallback } from "react";
import type { SimulationConfig, SimulationResult } from "./types";
import { fetchConfigs, runSimulation } from "./api";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import MetricCard from "./components/MetricCard";
import OverviewTab from "./components/OverviewTab";
import ExecutionTab from "./components/ExecutionTab";
import RiskTab from "./components/RiskTab";
import LedgerTab from "./components/LedgerTab";

type Tab = "overview" | "execution" | "risk" | "ledger";

export default function App() {
  const [configs, setConfigs] = useState<Record<string, SimulationConfig>>({});
  const [selectedConfig, setSelectedConfig] = useState<string>("");
  const [config, setConfig] = useState<SimulationConfig | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  useEffect(() => {
    fetchConfigs().then((c) => {
      setConfigs(c);
      const names = Object.keys(c);
      if (names.length > 0) {
        const def = names.includes("baseline_naive") ? "baseline_naive" : names[0];
        setSelectedConfig(def);
        setConfig(c[def]);
      }
    });
  }, []);

  const handleConfigChange = useCallback(
    (name: string) => {
      setSelectedConfig(name);
      setConfig(configs[name]);
      setResult(null);
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
    if (!config) return;
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
  }, [config]);

  const fmt = {
    money: (v: number) => {
      const sign = v < 0 ? "-" : "";
      return `${sign}$${Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    },
    num: (v: number, d = 2) => v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }),
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
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        configs={configs}
        selectedConfig={selectedConfig}
        config={config}
        onConfigChange={handleConfigChange}
        onParamChange={handleParamChange}
        onRun={handleRun}
        loading={loading}
      />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[1600px] mx-auto px-6 py-5">
          {result ? (
            <>
              <Header result={result} selectedConfig={selectedConfig} configHash={result.config_hash} />

              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-5">
                <MetricCard label="P&L" value={fmt.money(Number(result.summary.total_pnl))} positive={Number(result.summary.total_pnl) >= 0} />
                <MetricCard label="Sharpe" value={fmt.num(Number(result.summary.sharpe))} positive={Number(result.summary.sharpe) >= 0} />
                <MetricCard label="Drawdown" value={fmt.money(Number(result.summary.max_drawdown))} positive={false} />
                <MetricCard label="CVaR 95" value={fmt.money(Number(result.summary.cvar_95))} positive={false} />
                <MetricCard label="Hit Rate" value={fmt.pct(Number(result.summary.hit_rate))} />
                <MetricCard label="Fills" value={String(Math.round(Number(result.summary.fill_count)))} />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
                <MetricCard label="Max Inv" value={String(Math.round(Number(result.summary.max_inventory)))} />
                <MetricCard label="Fill Rate" value={fmt.pct(Number(result.summary.fill_rate))} />
                <MetricCard label="Eff Spread" value={fmt.bps(Number(result.summary.effective_spread_bps))} />
                <MetricCard label="Realized 5" value={fmt.bps(Number(result.summary.realized_spread_5_bps))} />
                <MetricCard label="Markout 5" value={fmt.bps(Number(result.summary.markout_5_bps))} />
                <MetricCard label="Maker Ratio" value={fmt.pct(Number(result.summary.maker_fill_ratio))} />
              </div>

              <div className="flex gap-1 mb-5 border-b border-[var(--color-border)]">
                {tabs.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setActiveTab(t.id)}
                    className={`px-4 py-2.5 text-sm font-medium transition-colors relative ${
                      activeTab === t.id
                        ? "text-[var(--color-accent)]"
                        : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                    }`}
                  >
                    {t.label}
                    {activeTab === t.id && (
                      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-accent)] rounded-full" />
                    )}
                  </button>
                ))}
              </div>

              {activeTab === "overview" && <OverviewTab result={result} />}
              {activeTab === "execution" && <ExecutionTab result={result} />}
              {activeTab === "risk" && <RiskTab result={result} />}
              {activeTab === "ledger" && <LedgerTab result={result} />}
            </>
          ) : (
            <div className="flex items-center justify-center h-[60vh]">
              <div className="text-center">
                {loading ? (
                  <div className="flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
                    <p className="text-[var(--color-text-muted)]">Running simulation...</p>
                  </div>
                ) : error ? (
                  <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-6 py-4">
                    <p className="text-red-400">{error}</p>
                  </div>
                ) : (
                  <p className="text-[var(--color-text-dim)]">Select a strategy and run a simulation</p>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
