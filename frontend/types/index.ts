/**
 * TradeSense — TypeScript Type Definitions
 * Shared interfaces used across the frontend application.
 */

// ── Auth ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

/** Generic paginated envelope matching backend PaginatedResponse[T]. */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Transaction {
  id: string;
  portfolio_id: string;
  symbol: string;
  isin: string | null;
  exchange: string;
  transaction_type: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  total_value: number;
  brokerage: number;
  stt: number;
  other_charges: number;
  fees: number;
  net_value: number;
  trade_date: string;       // ISO date string "YYYY-MM-DD"
  notes: string | null;
  broker_trade_id: string | null;
  external_trade_id: string | null;
  broker: string | null;
  raw_data: Record<string, unknown> | null;
  created_at: string;
  updated_at: string | null;
}

// ── Portfolio ─────────────────────────────────────────────────────────────────

export interface Portfolio {
  id: string;
  user_id: string;
  name: string;
  broker_name: string | null;
  currency: string;
  cost_basis_method: string;
  is_default: boolean;
  created_at: string;
}

export interface Holding {
  id: string;
  portfolio_id: string;
  symbol: string;
  isin: string | null;
  exchange: string;
  quantity: number;
  // BUG-05 FIX: Field names aligned with backend HoldingResponse schema.
  // Week-2 migration renamed: avg_cost_basis→average_cost, current_price→market_price, current_value→market_value
  average_cost: number;
  market_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  realized_pnl: number;
  updated_at: string;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface BehavioralMetricResponse {
  id: string;
  portfolio_id: string;
  period_type: string;
  pgr: number | null;
  plr: number | null;
  disposition_effect_score: number | null;
  portfolio_turnover_ratio: number | null;
  hhi: number | null;
  cost_drag_pct: number | null;
  metric_details: Record<string, any> | null;
  computed_at: string;
}

// ── Recommendations ───────────────────────────────────────────────────────────

export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface Recommendation {
  id: string;
  rule_id: string;
  category: string;
  severity: Severity;
  title: string;
  body: string;
  status: string;
  generated_at: string;
}

// ── Upload ────────────────────────────────────────────────────────────────────

export interface UploadResponse {
  status: string;
  records_parsed: number;
  records_inserted: number;
  records_skipped: number;
  message: string;
}

// ── API Error ─────────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string;
}
