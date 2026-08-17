import type { SimulationResult } from "../types";

interface HeaderProps {
  result: SimulationResult;
  selectedConfig: string;
  configHash: string;
}

export default function Header({ result, selectedConfig, configHash }: HeaderProps) {
  const pills = [
    { label: "strategy", value: result.agent_id },
    { label: "config", value: selectedConfig },
    { label: "seed", value: String(result.summary.seed ?? "") },
    { label: "steps", value: String(result.equity_curve.length) },
    { label: "hash", value: configHash },
  ];

  return (
    <div className="bg-gradient-to-r from-[#0f172a] to-[#1e293b] border border-[#1f2a44] rounded-xl px-6 py-5 mb-5">
      <h1 className="text-xl font-bold text-white mb-1">
        Market Making Research Terminal
      </h1>
      <p className="text-sm text-[var(--color-text-muted)] mb-3">
        Strategy diagnostics, execution quality, risk, inventory, and accounting audit.
      </p>
      <div className="flex flex-wrap gap-2">
        {pills.map((p) => (
          <span
            key={p.label}
            className="inline-flex items-center gap-1.5 bg-[#17233a] border border-[#334155] text-[#d9e4f5] text-xs font-medium px-2.5 py-1 rounded-full"
          >
            <span className="text-[var(--color-text-dim)]">{p.label}:</span>
            <span className="font-mono">{p.value}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
