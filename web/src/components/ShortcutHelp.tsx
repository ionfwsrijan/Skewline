import { motion, AnimatePresence } from "framer-motion";
import { X, Keyboard } from "lucide-react";

interface ShortcutHelpProps {
  open: boolean;
  onClose: () => void;
}

const shortcuts = [
  { keys: ["Ctrl", "Enter"], desc: "Run simulation" },
  { keys: ["1"], desc: "Overview tab" },
  { keys: ["2"], desc: "Execution tab" },
  { keys: ["3"], desc: "Risk tab" },
  { keys: ["4"], desc: "Ledger tab" },
  { keys: ["5"], desc: "Compare tab" },
  { keys: ["D"], desc: "Toggle dark/light theme" },
  { keys: ["?"], desc: "Show this help" },
  { keys: ["Esc"], desc: "Close modal / sidebar" },
];

export default function ShortcutHelp({ open, onClose }: ShortcutHelpProps) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="glass-strong rounded-2xl border border-border/50 p-6 w-full max-w-sm gradient-border" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <Keyboard className="w-4 h-4 text-primary" />
                  <h2 className="text-sm font-bold text-foreground">Keyboard Shortcuts</h2>
                </div>
                <button onClick={onClose} className="p-1 rounded-lg hover:bg-accent/50 text-muted-foreground transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="space-y-2.5">
                {shortcuts.map((s) => (
                  <div key={s.desc} className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">{s.desc}</span>
                    <div className="flex items-center gap-1">
                      {s.keys.map((k) => (
                        <kbd key={k} className="px-1.5 py-0.5 rounded bg-muted border border-border/50 font-mono text-[10px] text-foreground/70 min-w-[1.5rem] text-center">
                          {k}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
