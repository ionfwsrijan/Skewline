import { motion } from "framer-motion";
import type { SimulationResult } from "../types";

interface Props {
  result: SimulationResult;
}

function DataTable({
  columns,
  rows,
  delay = 0,
}: {
  columns: { key: string; label: string; mono?: boolean }[];
  rows: Record<string, unknown>[];
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: "easeOut" }}
      className="glass rounded-2xl p-5 overflow-hidden"
    >
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-border/50">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="text-left py-2.5 px-3 text-[9px] font-bold uppercase tracking-widest text-muted-foreground/60"
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                className="border-b border-border/30 hover:bg-white/[0.02] transition-colors"
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`py-2 px-3 text-foreground/80 ${col.mono ? "font-mono tabular-nums" : ""}`}
                  >
                    {typeof row[col.key] === "number"
                      ? (row[col.key] as number).toFixed(
                          row[col.key] === Math.round(row[col.key] as number) ? 0 : 4
                        )
                      : String(row[col.key] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
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
    { key: "timestamp", label: "Time", mono: true },
    { key: "event_type", label: "Event" },
    { key: "price", label: "Price", mono: true },
    { key: "quantity", label: "Qty", mono: true },
    { key: "cash_delta", label: "Cash \u0394", mono: true },
    { key: "inventory_delta", label: "Inv \u0394", mono: true },
    { key: "fee", label: "Fee", mono: true },
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
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="glass rounded-2xl p-5"
      >
        <div className="flex items-center gap-3 mb-4">
          <h3 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60">
            Accounting Audit
          </h3>
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 400, damping: 15, delay: 0.2 }}
            className={`text-[10px] font-bold px-3 py-1 rounded-lg border ${
              audit.passed
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-lg shadow-emerald-500/10"
                : "bg-red-500/10 text-red-400 border-red-500/20 shadow-lg shadow-red-500/10"
            }`}
          >
            {audit.passed ? "PASSED" : "FAILED"}
          </motion.span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {auditRows.map((r, i) => (
            <motion.div
              key={r.check}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: 0.1 + i * 0.05 }}
              className="glass rounded-xl p-3.5 hover:bg-white/[0.03] transition-colors"
            >
              <div className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/50 mb-1.5">
                {r.check}
              </div>
              <div className="text-sm font-bold font-mono tabular-nums text-foreground">
                {typeof r.value === "number"
                  ? r.value === Math.round(r.value)
                    ? String(r.value)
                    : r.value.toFixed(8)
                  : String(r.value)}
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      <DataTable columns={eventColumns} rows={eventRows} delay={0.15} />
    </div>
  );
}
