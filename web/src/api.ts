import type { SimulationConfig, SimulationResult, ComparisonResult } from "./types";

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

export function createSimulationSocket(
  config: SimulationConfig,
  onProgress: (data: {
    step: number;
    total: number;
    equity: number;
    inventory: number;
    mid: number;
    elapsed_ms: number;
  }) => void,
  onComplete: (data: { wall_time_ms: number; steps_per_sec: number }) => void,
  onError: (detail: string) => void
): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${window.location.hostname}:8000/ws/simulate`);

  ws.onopen = () => {
    ws.send(JSON.stringify(config));
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === "progress") {
      onProgress(msg);
    } else if (msg.type === "complete") {
      onComplete(msg);
    } else if (msg.type === "error") {
      onError(msg.detail);
    }
  };

  ws.onerror = () => onError("WebSocket connection failed");
  return ws;
}

export async function runComparison(
  symbol: string,
  config: SimulationConfig,
  sampleCount: number = 500
): Promise<ComparisonResult> {
  const res = await fetch(`${API_BASE}/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symbol,
      simulation_config: config,
      sample_count: sampleCount,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Comparison failed");
  }
  return res.json();
}
