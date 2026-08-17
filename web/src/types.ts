export interface SimulationConfig {
  seed: number;
  horizon_steps: number;
  dt: number;
  initial_price: number;
  price_process: {
    sigma: number;
    drift: number;
    jump_intensity: number;
    jump_mean: number;
    jump_std: number;
  };
  order_flow: {
    noise_intensity: number;
    informed_intensity: number;
    max_market_order_size: number;
  };
  latency: {
    quote_latency_steps: number;
    jitter_steps: number;
    spike_probability: number;
    spike_steps: number;
  };
  external_lob: {
    enabled: boolean;
    levels: number;
    quantity: number;
    half_spread_bps: number;
    ttl_steps: number;
  };
  fees: {
    maker_rebate_bps: number;
    taker_fee_bps: number;
  };
  risk: {
    max_position: number;
    max_drawdown: number;
  };
  agent: {
    type: string;
    [key: string]: unknown;
  };
}

export interface Fill {
  maker_agent_id: string;
  taker_agent_id: string;
  price: number;
  quantity: number;
  maker_side: string;
  taker_side: string;
  timestamp: number;
}

export interface BookSnapshot {
  timestamp: number;
  best_bid: number | null;
  best_ask: number | null;
  bid_depth: number;
  ask_depth: number;
  spread: number | null;
}

export interface AuditResult {
  passed: boolean;
  cash_error: number;
  inventory_error: number;
  equity_identity_error: number;
  event_count: number;
}

export interface SimulationResult {
  agent_id: string;
  equity_curve: number[];
  inventory_curve: number[];
  cash_curve: number[];
  mid_prices: number[];
  fills: Fill[];
  order_flow: Record<string, number>[];
  quote_history: Record<string, number>[];
  book_snapshots: BookSnapshot[];
  hedge_prices: number[];
  accounting_events: Record<string, unknown>[];
  summary: Record<string, number | string | null>;
  audit: AuditResult;
  config_hash: string;
}
