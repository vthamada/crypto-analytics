export type Exchange = "novadax" | "mercado_bitcoin" | "binance";

export type MovementType = "strong_range" | "spike" | "weak" | "trap";
export type MovementRegime =
  | "trend_continuation"
  | "breakout_clean"
  | "breakout_exhaustion"
  | "mean_reversion_candidate"
  | "illiquid_spike";
export type OpportunityType = "trade" | "hold" | "observe" | "avoid";

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
  technical_score?: number | null;
  score_version?: string;
  executability_version?: string;
  movement_version?: string;
  profile_version?: string;
  reweighting_version?: string;
  technical_signal_id?: string | null;
  semantic_signal_key?: string | null;
  executability_score?: number | null;
  executability_band?: string | null;
  interesting_signal?: boolean | null;
  operable_signal?: boolean | null;
  estimated_trade_margin_pct?: number | null;
  operational_friction_pct?: number | null;
  estimated_net_trade_edge_pct?: number | null;
  trade_margin_score?: number | null;
  opportunity_type?: OpportunityType | null;
  volatility_pct: number;
  volume_24h: number;
  quote_volume_24h: number;
  liquidity_units: number;
  bid_notional_top_n?: number | null;
  ask_notional_top_n?: number | null;
  total_notional_top_n?: number | null;
  spread_pct: number;
  estimated_buy_slippage_bps?: number | null;
  estimated_sell_slippage_bps?: number | null;
  fillable_notional_within_slippage_cap?: number | null;
  baseline_order_notional_brl?: number | null;
  movement_type: MovementType;
  movement_regime?: MovementRegime | null;
  movement_persistence_score?: number | null;
  last_price: number;
  change_pct: number;
  detected_at: string;
  duration_minutes: number;
  cross_exchange_gap_pct: number;
  cross_exchange_reference_exchange?: Exchange | null;
  cross_exchange_reference_price?: number | null;
  arbitrage_available: boolean;
  historical_confidence: number;
  volatility_score?: number;
  volume_score?: number;
  liquidity_score?: number;
  spread_score?: number;
  repetition_score?: number;
  movement_multiplier?: number;
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
  operable_opportunities?: number;
  trade_opportunities?: number;
  hold_opportunities?: number;
  observe_opportunities?: number;
  avoid_opportunities?: number;
  last_scan: string | null;
}

export interface DashboardPayload {
  stats: DashboardStats;
  opportunities: Opportunity[];
}

export type OpportunitySummary = Pick<
  Opportunity,
  | "id"
  | "exchange"
  | "pair"
  | "score"
  | "technical_score"
  | "executability_score"
  | "executability_band"
  | "trade_margin_score"
  | "estimated_net_trade_edge_pct"
  | "opportunity_type"
  | "interesting_signal"
  | "operable_signal"
  | "volatility_pct"
  | "volume_24h"
  | "quote_volume_24h"
  | "liquidity_units"
  | "bid_notional_top_n"
  | "ask_notional_top_n"
  | "total_notional_top_n"
  | "spread_pct"
  | "estimated_buy_slippage_bps"
  | "estimated_sell_slippage_bps"
  | "fillable_notional_within_slippage_cap"
  | "last_price"
  | "change_pct"
  | "movement_type"
  | "movement_regime"
  | "detected_at"
  | "cross_exchange_gap_pct"
  | "cross_exchange_reference_exchange"
  | "cross_exchange_reference_price"
  | "arbitrage_available"
  | "historical_confidence"
>;

export interface DashboardSummaryPayload {
  stats: DashboardStats;
  shortlist: OpportunitySummary[];
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
  trading_profile: "conservador" | "intraday_liquido" | "agressivo" | "scalp";
  order_notional_brl?: number | null;
  max_entry_slippage_bps?: number | null;
  max_exit_slippage_bps?: number | null;
  min_quote_volume_brl?: number | null;
  enabled_exchanges: Exchange[];
  enabled_pairs: string[];
  scan_interval_seconds: number;
  telegram_enabled: boolean;
  telegram_alert_threshold?: number;
  telegram_alert_cooldown_seconds?: number;
  telegram_alert_types?: string[];
  telegram_operable_only?: boolean;
  telegram_min_executability_score?: number | null;
  telegram_alert_exchanges?: Exchange[];
  telegram_alert_pairs?: string[];
  telegram_bot_token: string;
  telegram_chat_id: string;
  novadax_api_key: string;
  novadax_api_secret: string;
  mb_api_key: string;
  mb_api_secret: string;
  binance_api_key: string;
  binance_api_secret: string;
}

export interface ConfigResponse {
  config: AppConfig;
  configured_secrets: Record<string, boolean>;
}

export interface HistoryRecord {
  id: string;
  exchange: Exchange;
  pair: string;
  score: number;
  technical_score?: number | null;
  score_version?: string;
  executability_version?: string;
  movement_version?: string;
  profile_version?: string;
  reweighting_version?: string;
  technical_signal_id?: string | null;
  semantic_signal_key?: string | null;
  executability_score?: number | null;
  executability_band?: string | null;
  interesting_signal?: boolean | null;
  operable_signal?: boolean | null;
  estimated_trade_margin_pct?: number | null;
  operational_friction_pct?: number | null;
  estimated_net_trade_edge_pct?: number | null;
  trade_margin_score?: number | null;
  opportunity_type?: OpportunityType | null;
  volatility_pct: number;
  volume_24h: number;
  quote_volume_24h: number;
  liquidity_units: number;
  bid_notional_top_n?: number | null;
  ask_notional_top_n?: number | null;
  total_notional_top_n?: number | null;
  spread_pct: number;
  estimated_buy_slippage_bps?: number | null;
  estimated_sell_slippage_bps?: number | null;
  fillable_notional_within_slippage_cap?: number | null;
  baseline_order_notional_brl?: number | null;
  movement_type: MovementType;
  movement_regime?: MovementRegime | null;
  movement_persistence_score?: number | null;
  last_price: number;
  change_pct: number;
  detected_at: string;
  duration_minutes: number;
  cross_exchange_gap_pct: number;
  cross_exchange_reference_exchange?: Exchange | null;
  cross_exchange_reference_price?: number | null;
  arbitrage_available: boolean;
  historical_confidence: number;
  volatility_score?: number;
  volume_score?: number;
  liquidity_score?: number;
  spread_score?: number;
  repetition_score?: number;
  movement_multiplier?: number;
}

export interface HistorySummaryRecord {
  id: string;
  exchange: Exchange;
  pair: string;
  score: number;
  executability_score?: number | null;
  trade_margin_score?: number | null;
  estimated_net_trade_edge_pct?: number | null;
  opportunity_type?: OpportunityType | null;
  spread_pct: number;
  last_price: number;
  change_pct: number;
  movement_type: MovementType;
  detected_at: string;
}

export interface Analytics {
  total_records: number;
  top_pairs: { pair: string; count: number }[];
  avg_score_by_exchange: { exchange: string; avg_score: number }[];
  score_distribution: Record<string, number>;
  executability_distribution?: Record<string, number>;
  movement_distribution: Record<string, number>;
  movement_regime_distribution?: Record<string, number>;
  opportunity_type_distribution?: Record<OpportunityType, number>;
  avg_net_trade_edge_by_type?: Partial<Record<OpportunityType, number>>;
  hourly_distribution: Record<string, number>;
  arbitrage_count: number;
  avg_cross_exchange_gap_pct: number;
  profile_distribution?: Record<string, number>;
}

export interface WorkspaceSummary {
  id: string;
  slug: string;
  name: string;
  role: string;
  is_active: boolean;
}

export interface OrganizationSummary {
  id: string;
  name: string;
  slug: string;
  plan: string;
  stripe_customer_id?: string | null;
  subscription_status: string;
  trial_ends_at?: string | null;
}

export interface AdminSessionInfo {
  user_id: string;
  username: string;
  email?: string | null;
  role: string;
  auth_mode: string;
  token_version: number;
  password_last_changed_at: string | null;
  must_change_password: boolean;
  onboarding_completed_at?: string | null;
  organization?: OrganizationSummary | null;
  workspaces: WorkspaceSummary[];
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_seconds: number;
  refresh_expires_in_seconds: number;
  session: AdminSessionInfo;
}

export interface UserRecord {
  id: string;
  username: string;
  email?: string | null;
  role: string;
  is_active: boolean;
  must_change_password: boolean;
  created_at: string | null;
  updated_at: string | null;
  password_last_changed_at: string | null;
  created_by_user_id: string | null;
  token_version: number;
}

export interface UserCreateResult {
  user: UserRecord;
  temporary_password: string;
}

export interface AvailablePairRecord {
  pair: string;
  display_name: string;
  availability: Record<Exchange, boolean>;
  normalized_symbol?: string | null;
  base_asset?: string | null;
  quote_asset?: string | null;
  is_brl_pair?: boolean;
  raw_symbols?: Partial<Record<Exchange, string | null>>;
  is_active?: Partial<Record<Exchange, boolean>>;
  is_tradable?: Partial<Record<Exchange, boolean>>;
  status?: Partial<Record<Exchange, string>>;
  error_message?: Partial<Record<Exchange, string | null>>;
}

export interface AvailablePairProviderStatus {
  exchange: Exchange;
  returned_pairs: number;
  brl_pairs: number;
  status: "ok" | "empty" | "error" | "disabled";
  checked_at: string;
  error_message?: string | null;
  examples: string[];
}

export interface AvailablePairsResponse {
  generated_at: string;
  expires_at: string;
  pairs: AvailablePairRecord[];
  provider_status: AvailablePairProviderStatus[];
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

export interface InviteRecord {
  id: string;
  code: string;
  email: string;
  workspace_id: string;
  workspace_name: string;
  organization_id: string;
  organization_name: string;
  role: string;
  status: "pending" | "used" | "expired";
  expires_at: string;
  used_at?: string | null;
  created_at: string;
}

export interface InvitePreview {
  code: string;
  email: string;
  workspace_name: string;
  organization_name: string;
  role: string;
  status: "pending" | "used" | "expired";
  expires_at: string;
}

export interface WorkspaceStatus {
  workspace: WorkspaceSummary;
  organization?: OrganizationSummary | null;
  configured_pairs_count: number;
  enabled_exchange_count: number;
  telegram_configured: boolean;
  exchange_credentials_configured: Record<Exchange, boolean>;
  onboarding_completed_at?: string | null;
}

export interface ExchangeCredentialValidationResult {
  exchange: Exchange;
  state: "missing" | "valid" | "invalid" | "no_trading_permission" | "error";
  checked_at: string;
  can_trade?: boolean | null;
  message: string;
}

export interface ExchangeCredentialValidationResponse {
  results: ExchangeCredentialValidationResult[];
}
