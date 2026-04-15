export type Exchange = "novadax" | "mercado_bitcoin" | "binance";

export type MovementType = "strong_range" | "spike" | "weak" | "trap";

export interface Kline {
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  close_time?: string;
}

export interface Opportunity {
  id: string;
  exchange: Exchange;
  pair: string;
  score: number;
  volatility_pct: number;
  volume_24h: number;
  quote_volume_24h: number;
  liquidity_units: number;
  spread_pct: number;
  movement_type: MovementType;
  last_price: number;
  change_pct: number;
  detected_at: string;
  duration_minutes: number;
  cross_exchange_gap_pct: number;
  cross_exchange_reference_exchange?: Exchange | null;
  cross_exchange_reference_price?: number | null;
  arbitrage_available: boolean;
  historical_confidence: number;
  klines?: Kline[];
}

export interface DashboardStats {
  total_opportunities: number;
  active_opportunities: number;
  monitored_pairs: number;
  total_volume_24h: number;
  best_score: number;
  exchanges_online: number;
  arbitrage_opportunities: number;
  last_scan: string | null;
}

export interface FilterThresholds {
  min_volatility_pct: number;
  min_volume_brl: number;
  min_volume_brl_small: number;
  min_liquidity_units: number;
  max_spread_pct: number;
}

export interface ScoreWeights {
  volatility: number;
  volume: number;
  liquidity: number;
  spread: number;
  repetition: number;
}

export interface AppConfig {
  thresholds: FilterThresholds;
  weights: ScoreWeights;
  enabled_exchanges: Exchange[];
  enabled_pairs: string[];
  scan_interval_seconds: number;
  telegram_enabled: boolean;
  telegram_bot_token: string;
  telegram_chat_id: string;
  novadax_api_key: string;
  novadax_api_secret: string;
  mb_api_key: string;
  mb_api_secret: string;
  binance_api_key: string;
  binance_api_secret: string;
}

export interface HistoryRecord {
  id: string;
  exchange: Exchange;
  pair: string;
  score: number;
  volatility_pct: number;
  volume_24h: number;
  quote_volume_24h: number;
  liquidity_units: number;
  spread_pct: number;
  movement_type: MovementType;
  last_price: number;
  change_pct: number;
  detected_at: string;
  duration_minutes: number;
  cross_exchange_gap_pct: number;
  cross_exchange_reference_exchange?: Exchange | null;
  cross_exchange_reference_price?: number | null;
  arbitrage_available: boolean;
  historical_confidence: number;
}

export interface Analytics {
  total_records: number;
  top_pairs: { pair: string; count: number }[];
  avg_score_by_exchange: { exchange: string; avg_score: number }[];
  score_distribution: Record<string, number>;
  movement_distribution: Record<string, number>;
  hourly_distribution: Record<string, number>;
  arbitrage_count: number;
  avg_cross_exchange_gap_pct: number;
}

export interface WorkspaceSummary {
  id: string;
  slug: string;
  name: string;
  role: string;
  is_active: boolean;
}

export interface AdminSessionInfo {
  user_id: string;
  username: string;
  role: string;
  auth_mode: string;
  token_version: number;
  password_last_changed_at: string | null;
  workspaces: WorkspaceSummary[];
}

export interface AuditLogEntry {
  id: string;
  actor_user_id?: string | null;
  actor_username: string | null;
  workspace_id?: string | null;
  action: string;
  status: string;
  details: Record<string, unknown>;
  created_at: string;
}
