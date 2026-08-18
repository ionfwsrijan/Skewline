import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string;
  positive?: boolean;
  delay?: number;
}

export default function MetricCard({ label, value, positive, delay = 0 }: MetricCardProps) {
  const colorClass =
    positive === true
      ? "gradient-text-green"
      : positive === false
        ? "gradient-text-red"
        : "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: "easeOut" }}
      className={cn(
        "relative glass rounded-xl px-4 py-3.5 group transition-all duration-300",
        "hover:scale-[1.02]",
        positive === true && "hover:shadow-lg hover:shadow-emerald-500/10",
        positive === false && "hover:shadow-lg hover:shadow-red-500/10",
        !positive && positive !== false && "hover:shadow-lg hover:shadow-primary/5",
      )}
    >
      <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none gradient-border" />
      <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mb-1.5">
        {label}
      </div>
      <div className={cn("text-lg font-bold font-mono tabular-nums tracking-tight", colorClass)}>
        {value}
      </div>
    </motion.div>
  );
}
