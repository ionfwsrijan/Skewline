import { Sun, Moon } from "lucide-react";
import { motion } from "framer-motion";

interface ThemeToggleProps {
  theme: "dark" | "light";
  onToggle: () => void;
  className?: string;
}

export default function ThemeToggle({ theme, onToggle, className }: ThemeToggleProps) {
  return (
    <button
      onClick={onToggle}
      className={`relative p-2 rounded-lg glass border border-border/50 text-foreground hover:bg-accent/50 transition-colors ${className ?? ""}`}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      <motion.div
        key={theme}
        initial={{ rotate: -90, opacity: 0, scale: 0.5 }}
        animate={{ rotate: 0, opacity: 1, scale: 1 }}
        exit={{ rotate: 90, opacity: 0, scale: 0.5 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
      >
        {theme === "dark" ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
      </motion.div>
    </button>
  );
}
