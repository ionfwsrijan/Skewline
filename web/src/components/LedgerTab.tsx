import type { SimulationResult } from "../types";

interface Props {
  result: SimulationResult;
}

function Table({
  columns,
  rows,
}: {
  columns: string[];
  rows: Record<string, unknown>[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-[var(--color-border)]">
            {columns.map((col) => (
              <th
                key={col}
                className="text-left py-2 px-2 text-[var(--color-text-muted)] font-medium uppercase tracking-wider"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className="border-b border-[var(--color-border)]/50 hover:bg-[var(--color-bg-card-hover)]"
            >
              {columns.map((col) => (
                <td
                  key={col}
                  className="py-1.5 px-2 font-mono text-[var(--color-text)]"
                >
                  {typeof row[col] === "number"
                    ? (row[col] as number).toFixed(
                        row[col] === Math.round(row[col] as number) ? 0 : 4
                      )
                    : String(row[col] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function LedgerTab({ result }: Props) {
  const audit = result.audit;

  const auditRows = [
    { check: "cash_error", value: audit.cash_error },
    { check: "inventory_error", value: audit.inventory_error },
    { check: "equity_identity_error", value: audit.equity_identity_error },
    { check: "event_count", value: audit.event_count },
  ];

  const eventColumns = [
    "timestamp",
    "event_type",
    "price",
    "quantity",
    "cash_delta",
    "inventory_delta",
    "fee",
  ];
  const eventRows = result.accounting_events.slice(-60).map((e) => ({
    timestamp: Number(e.timestamp),
    event_type: String(e.event_type),
    price: Number(e.price),
    quantity: Number(e.quantity),
    cash_delta: Number(e.cash_delta),
    inventory_delta: Number(e.inventory_delta),
    fee: Number(e.fee),
  }));

  return (
    <div className="space-y-4">
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-4">
        <div className="flex items-center gap-3 mb-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-dim)]">
            Accounting Audit
          </h3>
          <span
            className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
              audit.passed
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : "bg-red-500/10 text-red-400 border border-red-500/20"
            }`}
          >
            {audit.passed ? "PASSED" : "FAILED"}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {auditRows.map((r) => (
            <div
              key={r.check}
              className="bg-[var(--color-bg)] rounded-lg p-3 border border-[var(--color-border)]"
            >
              <div className="text-[10px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-1">
                {r.check}
              </div>
              <div className="text-sm font-bold font-mono text-[var(--color-text)]">
                {typeof r.value === "number"
                  ? r.value === Math.round(r.value)
                    ? String(r.value)
                    : r.value.toFixed(8)
                  : String(r.value)}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-xl p-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-dim)] mb-3">
          Event Ledger (last 60)
        </h3>
        <Table columns={eventColumns} rows={eventRows} />
      </div>
    </div>
  );
}
