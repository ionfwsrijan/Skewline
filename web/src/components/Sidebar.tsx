import type { SimulationConfig } from "../types";

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
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-[var(--color-text-muted)]">{label}</span>
        <span className="text-[var(--color-text)] font-mono">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1 bg-[var(--color-border)] rounded-full appearance-none cursor-pointer accent-[var(--color-accent)]"
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
    <aside className="w-72 bg-[var(--color-bg-sidebar)] border-r border-[var(--color-border)] flex flex-col h-screen overflow-y-auto shrink-0">
      <div className="px-4 py-5 border-b border-[var(--color-border)]">
        <h1 className="text-base font-bold text-white tracking-tight">
          MM Sim
        </h1>
        <p className="text-xs text-[var(--color-text-dim)] mt-0.5">
          Market Making Research Terminal
        </p>
      </div>

      <div className="px-4 py-4 border-b border-[var(--color-border)]">
        <label className="text-xs font-medium text-[var(--color-text-muted)] mb-1.5 block">
          Strategy
        </label>
        {configsLoading ? (
          <div className="w-full h-9 bg-[var(--color-bg)] border border-[var(--color-border)] rounded-md px-3 py-2 flex items-center">
            <div className="w-4 h-4 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
        <select
          value={selectedConfig}
          onChange={(e) => onConfigChange(e.target.value)}
          className="w-full bg-[var(--color-bg)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-border-focus)]"
        >
          {Object.keys(configs).map((name) => (
            <option key={name} value={name}>
              {name.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        )}
        {agentType && (
          <div className="mt-2 inline-flex items-center gap-1.5 bg-[var(--color-accent)]/10 text-[var(--color-accent)] text-xs font-medium px-2 py-0.5 rounded-full">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent)]" />
            {agentType}
          </div>
        )}
      </div>

      {config && (
        <div className="flex-1 px-4 py-4 space-y-5">
          <div>
            <h3 className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-dim)] mb-3">
              Run
            </h3>
            <Slider
              label="Steps"
              value={config.horizon_steps}
              min={100}
              max={5000}
              step={100}
              onChange={(v) => onParamChange("horizon_steps", v)}
            />
            <div className="mb-3">
              <label className="text-xs text-[var(--color-text-muted)] mb-1 block">
                Seed
              </label>
              <input
                type="number"
                value={config.seed}
                onChange={(e) => onParamChange("seed", Number(e.target.value))}
                className="w-full bg-[var(--color-bg)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text)] font-mono focus:outline-none focus:border-[var(--color-border-focus)]"
              />
            </div>
          </div>

          <div>
            <h3 className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-dim)] mb-3">
              Risk
            </h3>
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

          <div>
            <h3 className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-dim)] mb-3">
              Market
            </h3>
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

          {(hasBaseSpread || hasGamma) && (
            <div>
              <h3 className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-dim)] mb-3">
                Agent
              </h3>
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
                  label="Risk Aversion (γ)"
                  value={config.agent.gamma as number}
                  min={0.01}
                  max={0.3}
                  step={0.01}
                  onChange={(v) => onParamChange("agent.gamma", v)}
                />
              )}
            </div>
          )}
        </div>
      )}

      <div className="px-4 py-4 border-t border-[var(--color-border)]">
        <button
          onClick={onRun}
          disabled={loading || !config}
          className="w-full py-2.5 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Running...
            </>
          ) : (
            "Run Simulation"
          )}
        </button>
        <p className="text-[10px] text-[var(--color-text-dim)] text-center mt-2">
          Ctrl+Enter
        </p>
      </div>
    </aside>
  );
}
