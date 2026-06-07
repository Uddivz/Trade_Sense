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
  quantity: number;
  avg_cost_basis: number;
  current_price: number;
  current_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface DispositionEffect {
  pgr: number | null;
  plr: number | null;
  de_score: number | null;
  classification: string | null;
  realized_gains_count: number;
  realized_losses_count: number;
  paper_gains_count: number;
  paper_losses_count: number;
  status: string;
}

export interface Overtrading {
  portfolio_turnover_ratio: number | null;
  trade_frequency_per_month: number | null;
  total_trades: number;
  cost_drag_pct: number | null;
  classification: string | null;
  status: string;
}

export interface HoldingBreakdown {
  symbol: string;
  weight: number;
  value: number;
}

export interface Concentration {
  hhi: number | null;
  effective_n: number | null;
  top1_holding_pct: number | null;
  top3_holding_pct: number | null;
  num_holdings: number;
  holdings_breakdown: HoldingBreakdown[];
  classification: string | null;
  status: string;
}

export interface BehavioralSummary {
  status: string;
  message?: string;
  computed_at: string | null;
  behavioral_risk_score: number | null;
  disposition_effect: DispositionEffect | null;
  overtrading: Overtrading | null;
  concentration: Concentration | null;
  details: Record<string, unknown> | null;
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
