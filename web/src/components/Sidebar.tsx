import type { SimulationConfig } from "../types";
import { cn } from "@/lib/utils";

interface SidebarProps {
  configs: Record<string, SimulationConfig>;
  selectedConfig: string;
  config: SimulationConfig | null;
  onConfigChange: (name: string) => void;
  onParamChange: (path: string, value: number | boolean) => void;
  onRun: () => void;
  loading: boolean;
  configsLoading: boolean;
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-[11px] font-medium text-muted-foreground">{label}</span>
        <span className="text-[11px] font-mono font-semibold text-foreground tabular-nums">
          {step < 1 ? value.toFixed(2) : value}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className={cn(
          "w-full h-1.5 rounded-full appearance-none cursor-pointer",
          "bg-muted",
          "[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:w-3.5",
          "[&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary",
          "[&::-webkit-slider-thumb]:shadow-[0_0_0_3px_rgba(99,102,241,0.2)]",
          "[&::-webkit-slider-thumb]:hover:bg-primary/90 [&::-webkit-slider-thumb]:transition-all",
          "[&::-webkit-slider-thumb]:hover:shadow-[0_0_0_5px_rgba(99,102,241,0.25)]",
          "[&::-moz-range-thumb]:h-3.5 [&::-moz-range-thumb]:w-3.5 [&::-moz-range-thumb]:rounded-full",
          "[&::-moz-range-thumb]:bg-primary [&::-moz-range-thumb]:border-0",
          "[&::-moz-range-thumb]:shadow-[0_0_0_3px_rgba(99,102,241,0.2)]",
        )}
      />
    </div>
  );
}

export default function Sidebar({
  configs,
  selectedConfig,
  config,
  onConfigChange,
  onParamChange,
  onRun,
  loading,
  configsLoading,
}: SidebarProps) {
  const agentType = config?.agent?.type ?? "";
  const hasBaseSpread = "base_spread_bps" in (config?.agent ?? {});
  const hasGamma = "gamma" in (config?.agent ?? {});

  return (
    <aside className="w-80 glass-sidebar flex flex-col h-screen shrink-0">
      <div className="px-5 py-6 border-b border-border/50">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 3v18h18" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M7 16l4-8 4 4 4-10" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-bold text-foreground tracking-tight">Skewline</h1>
            <p className="text-[10px] text-muted-foreground font-medium">Market Making Research</p>
          </div>
        </div>
      </div>

      <div className="px-5 py-4 border-b border-border/50">
        <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2 block">
          Strategy
        </label>
        {configsLoading ? (
          <div className="w-full h-9 glass rounded-xl flex items-center px-3">
            <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <select
            value={selectedConfig}
            onChange={(e) => onConfigChange(e.target.value)}
            className="w-full glass rounded-xl px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-medium cursor-pointer appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2216%22%20height%3D%2216%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%2394a3b8%22%20stroke-width%3D%222%22%3E%3Cpath%20d%3D%22m6%209%206%206%206-6%22/%3E%3C/svg%3E')] bg-[length:16px] bg-[right_8px_center] bg-no-repeat pr-8"
          >
            {Object.keys(configs).map((name) => (
              <option key={name} value={name}>
                {name.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        )}
        {agentType && !configsLoading && (
          <div className="mt-2.5 inline-flex items-center gap-1.5 bg-primary/10 text-primary text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-lg border border-primary/20">
            <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse-slow" />
            {agentType.replace(/_/g, " ")}
          </div>
        )}
      </div>

      {config && (
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
          <div>
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mb-4 flex items-center gap-2">
              <div className="w-1 h-1 rounded-full bg-primary" />
              Run Parameters
            </h3>
            <div className="space-y-4">
              <Slider
                label="Steps"
                value={config.horizon_steps}
                min={100}
                max={5000}
                step={100}
                onChange={(v) => onParamChange("horizon_steps", v)}
              />
              <div>
                <label className="text-[11px] font-medium text-muted-foreground mb-1.5 block">Seed</label>
                <input
                  type="number"
                  value={config.seed}
                  onChange={(e) => onParamChange("seed", Number(e.target.value))}
                  className="w-full glass rounded-xl px-3 py-2 text-sm text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                />
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mb-4 flex items-center gap-2">
              <div className="w-1 h-1 rounded-full bg-red-500" />
              Risk Controls
            </h3>
            <div className="space-y-4">
              <Slider
                label="Max Position"
                value={config.risk.max_position}
                min={5}
                max={200}
                step={1}
                onChange={(v) => onParamChange("risk.max_position", v)}
              />
              <Slider
                label="Max Drawdown"
                value={config.risk.max_drawdown}
                min={100}
                max={10000}
                step={100}
                onChange={(v) => onParamChange("risk.max_drawdown", v)}
              />
            </div>
          </div>

          <div>
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mb-4 flex items-center gap-2">
              <div className="w-1 h-1 rounded-full bg-emerald-500" />
              Market Conditions
            </h3>
            <div className="space-y-4">
              <Slider
                label="Informed Flow"
                value={config.order_flow.informed_intensity}
                min={0}
                max={5}
                step={0.1}
                onChange={(v) => onParamChange("order_flow.informed_intensity", v)}
              />
              <Slider
                label="Latency"
                value={config.latency.quote_latency_steps}
                min={0}
                max={20}
                step={1}
                onChange={(v) => onParamChange("latency.quote_latency_steps", v)}
              />
              <Slider
                label="Jitter"
                value={config.latency.jitter_steps}
                min={0}
                max={10}
                step={1}
                onChange={(v) => onParamChange("latency.jitter_steps", v)}
              />
            </div>
          </div>

          {(hasBaseSpread || hasGamma) && (
            <div>
              <h3 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mb-4 flex items-center gap-2">
                <div className="w-1 h-1 rounded-full bg-amber-500" />
                Agent Settings
              </h3>
              <div className="space-y-4">
                {hasBaseSpread && (
                  <Slider
                    label="Spread (bps)"
                    value={config.agent.base_spread_bps as number}
                    min={1}
                    max={40}
                    step={0.5}
                    onChange={(v) => onParamChange("agent.base_spread_bps", v)}
                  />
                )}
                {hasGamma && (
                  <Slider
                    label="Risk Aversion (\u03B3)"
                    value={config.agent.gamma as number}
                    min={0.01}
                    max={0.3}
                    step={0.01}
                    onChange={(v) => onParamChange("agent.gamma", v)}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="px-5 py-4 border-t border-border/50">
        <button
          onClick={onRun}
          disabled={loading || !config}
          className={cn(
            "w-full py-3 rounded-xl text-sm font-bold transition-all relative overflow-hidden",
            "disabled:opacity-40 disabled:cursor-not-allowed",
            loading
              ? "bg-primary/20 text-primary"
              : "bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 hover:scale-[1.01] active:scale-[0.99]"
          )}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
              Running...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polygon points="5 3 19 12 5 21 5 3" fill="currentColor" />
              </svg>
              Run Simulation
            </span>
          )}
        </button>
        <p className="text-[9px] text-muted-foreground/40 text-center mt-2 font-mono tracking-wider">
          CTRL + ENTER
        </p>
      </div>
    </aside>
  );
}
