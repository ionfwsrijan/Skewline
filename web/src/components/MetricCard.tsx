interface MetricCardProps {
  label: string;
  value: string;
  positive?: boolean;
}

export default function MetricCard({ label, value, positive }: MetricCardProps) {
  const colorClass =
    positive === true
      ? "text-[var(--color-green)]"
      : positive === false
        ? "text-[var(--color-red)]"
        : "text-[var(--color-text)]";

  return (
    <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-lg px-4 py-3 hover:border-[var(--color-border-focus)]/30 transition-colors">
      <div className="text-[11px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-1">
        {label}
      </div>
      <div className={`text-lg font-bold font-mono ${colorClass}`}>
        {value}
      </div>
    </div>
  );
}
