import type { SimulationConfig, SimulationResult } from "./types";

const API_BASE = "/api";

export async function fetchConfigs(): Promise<
  Record<string, SimulationConfig>
> {
  const res = await fetch(`${API_BASE}/configs`);
  if (!res.ok) throw new Error("Failed to fetch configs");
  return res.json();
}

export async function runSimulation(
  config: SimulationConfig
): Promise<SimulationResult> {
  const res = await fetch(`${API_BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Simulation failed");
  }
  return res.json();
}
