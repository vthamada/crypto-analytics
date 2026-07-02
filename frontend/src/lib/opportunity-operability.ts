import type { Opportunity, OpportunitySummary } from "./types";

export type OpportunitySortMode =
  | "score"
  | "executability"
  | "trade_margin"
  | "net_edge"
  | "gap"
  | "volume"
  | "volatility"
  | "spread";

type ReasonTone = "positive" | "warning" | "negative" | "neutral";

export interface OpportunityReason {
  label: string;
  tone: ReasonTone;
}

export type OpportunityListItem = Opportunity | OpportunitySummary;

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function getTechnicalScore(opportunity: OpportunityListItem): number {
  return opportunity.technical_score ?? opportunity.score;
}

export function getOperationalScore(opportunity: OpportunityListItem): number {
  return opportunity.operational_score ?? opportunity.score;
}

export function getExecutabilityScore(opportunity: OpportunityListItem): number | null {
  return typeof opportunity.executability_score === "number"
    ? opportunity.executability_score
    : null;
}

export function hasExecutability(opportunity: OpportunityListItem): boolean {
  return (
    getExecutabilityScore(opportunity) !== null ||
    opportunity.total_notional_top_n != null ||
    opportunity.estimated_buy_slippage_bps != null ||
    opportunity.estimated_sell_slippage_bps != null ||
    opportunity.fillable_notional_within_slippage_cap != null
  );
}

export function getExecutabilityBand(opportunity: OpportunityListItem): string | null {
  if (opportunity.executability_band) {
    return opportunity.executability_band;
  }
  const score = getExecutabilityScore(opportunity);
  if (score === null) {
    return null;
  }
  if (score >= 80) return "strong";
  if (score >= 60) return "good";
  if (score >= 40) return "fair";
  return "poor";
}

export function getExecutabilityBandLabel(opportunity: OpportunityListItem): string {
  const band = getExecutabilityBand(opportunity);
  switch (band) {
    case "strong":
      return "Forte";
    case "good":
      return "Boa";
    case "fair":
      return "Regular";
    case "poor":
      return "Fraca";
    default:
      return "Indisponivel";
  }
}

export function isInterestingSignal(opportunity: OpportunityListItem): boolean {
  return opportunity.interesting_signal ?? true;
}

export function isOperableSignal(opportunity: OpportunityListItem): boolean {
  return opportunity.operable_signal ?? false;
}

export function isOperationallyVisible(opportunity: OpportunityListItem): boolean {
  return opportunity.operationally_visible ?? (
    opportunity.opportunity_type === "trade" ||
    opportunity.opportunity_type === "hold" ||
    Boolean(opportunity.operable_signal)
  );
}

export function getSortValue(opportunity: OpportunityListItem, sortBy: OpportunitySortMode): number {
  switch (sortBy) {
    case "executability":
      return getExecutabilityScore(opportunity) ?? -1;
    case "trade_margin":
      return opportunity.trade_margin_score ?? -1;
    case "net_edge":
      return opportunity.estimated_net_trade_edge_pct ?? -999;
    case "gap":
      return opportunity.cross_exchange_gap_pct;
    case "volume":
      return opportunity.quote_volume_24h;
    case "volatility":
      return opportunity.volatility_pct;
    case "spread":
      return -opportunity.spread_pct;
    case "score":
    default:
      return getOperationalRankValue(opportunity);
  }
}

export function getOperationalRankValue(opportunity: OpportunityListItem): number {
  const phaseBonus: Record<string, number> = {
    early_breakout: 8,
    continuation: 5,
    accumulation: 2,
    extended: -4,
    distribution_or_profit_zone: -6,
    exhaustion: -8,
    neutral: 0,
  };
  const rangeBonus: Record<string, number> = {
    high_quality_reusable_range: 7,
    valid_large_trade: 5,
    valid_medium_trade: 3,
    valid_small_trade: 1.5,
    weak: -1,
    none: 0,
  };
  const typeBonus: Record<string, number> = {
    trade: 5,
    hold: 4,
    observe: -2,
    avoid: -12,
  };
  const quoteVolume = Math.max(opportunity.quote_volume_24h || 0, 1);
  const totalNotional = opportunity.total_notional_top_n ?? 0;
  const maxOrder = opportunity.max_operable_order_notional_brl ?? 0;
  const exitLiquidityBonus = clamp(Math.log10(quoteVolume / 1_000) * 5, -8, 14);
  const bookDepthBonus = clamp(totalNotional / 5_000, 0, 10) + clamp(maxOrder / 1_000, 0, 8);
  const marginBonus = clamp((opportunity.estimated_net_trade_edge_pct ?? 0) * 8, 0, 12);
  const slippagePenalty = clamp((opportunity.estimated_sell_slippage_bps ?? 0) / 20, 0, 12);
  const spreadPenalty = clamp((opportunity.spread_pct ?? 0) * 4, 0, 10);
  const noTriggerPenalty = opportunity.has_actionable_trigger ? 0 : -10;
  const poorSizePenalty = opportunity.operability_size_label === "not_operable" ? -12 : 0;

  return (
    getOperationalScore(opportunity) +
    (getExecutabilityScore(opportunity) ?? 0) * 0.18 +
    (opportunity.trade_margin_score ?? 0) * 0.1 +
    clamp(opportunity.operational_range_margin_pct ?? 0, 0, 20) * 0.3 +
    exitLiquidityBonus +
    bookDepthBonus +
    marginBonus +
    (phaseBonus[opportunity.movement_phase ?? "neutral"] ?? 0) +
    (rangeBonus[opportunity.operational_range_quality ?? "none"] ?? 0) +
    (typeBonus[opportunity.opportunity_type ?? "observe"] ?? 0) -
    (opportunity.is_late_entry_risk ? 8 : 0) +
    noTriggerPenalty +
    poorSizePenalty -
    slippagePenalty -
    spreadPenalty
  );
}

export type OperationalDashboardBucket = "now" | "observe" | "audit";

export function getOperationalDashboardBucket(opportunity: OpportunityListItem): OperationalDashboardBucket {
  const status = opportunity.operation_status;
  if (
    status === "vale_olhar_agora" &&
    Boolean(opportunity.has_actionable_trigger) &&
    Boolean(opportunity.entry_zone) &&
    Boolean(opportunity.exit_zone) &&
    Boolean(opportunity.suggested_capital_range_brl) &&
    opportunity.risk_label !== "alto"
  ) {
    return "now";
  }
  if (
    status === "evitar" ||
    status === "sem_liquidez" ||
    status === "ja_passou_do_ponto" ||
    opportunity.pipeline_status === "blocked_signal" ||
    opportunity.opportunity_type === "avoid"
  ) {
    return "audit";
  }
  return "observe";
}

export function formatCurrency(value: number, digits = 2): string {
  return `R$ ${value.toLocaleString("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
}

export function formatCurrencyCompact(value: number): string {
  const absolute = Math.abs(value);
  if (absolute >= 1_000_000) {
    return `R$ ${(value / 1_000_000).toFixed(1)}M`;
  }
  if (absolute >= 1_000) {
    return `R$ ${(value / 1_000).toFixed(1)}K`;
  }
  return formatCurrency(value);
}

export function formatSignedPercent(value: number, digits = 2): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}%`;
}

export function formatBps(value: number | null | undefined): string {
  if (value == null) {
    return "n/d";
  }
  const digits = Math.abs(value) >= 10 ? 0 : 1;
  return `${value.toFixed(digits)} bps`;
}

export function formatNotionalOrFallback(opportunity: OpportunityListItem): string {
  if (opportunity.total_notional_top_n != null) {
    return formatCurrencyCompact(opportunity.total_notional_top_n);
  }
  return `${opportunity.liquidity_units.toLocaleString("pt-BR")} un.`;
}

export function formatOperabilitySizeLabel(label?: string | null): string {
  switch (label) {
    case "large_operation":
      return "Opera maior";
    case "medium_operation":
      return "Opera medio";
    case "small_test_only":
      return "So teste pequeno";
    case "not_operable":
      return "Nao operavel";
    default:
      return "Capacidade n/d";
  }
}

export function formatOperationStatus(status?: string | null): string {
  switch (status) {
    case "vale_olhar_agora":
      return "Vale olhar agora";
    case "so_observar":
      return "So observar";
    case "aguardando_gatilho":
      return "Aguardando gatilho";
    case "evitar":
      return "Evitar";
    case "sem_liquidez":
      return "Sem liquidez";
    case "ja_passou_do_ponto":
      return "Ja passou do ponto";
    default:
      return "So observar";
  }
}

export function getOperationStatusTone(status?: string | null): ReasonTone {
  switch (status) {
    case "vale_olhar_agora":
      return "positive";
    case "aguardando_gatilho":
    case "so_observar":
    case "ja_passou_do_ponto":
      return "warning";
    case "evitar":
    case "sem_liquidez":
      return "negative";
    default:
      return "neutral";
  }
}

export function formatOpportunityFamily(family?: string | null): string {
  switch (family) {
    case "faixa_operacional":
      return "Faixa operacional";
    case "spread_interno":
      return "Spread interno";
    case "arbitragem":
      return "Arbitragem";
    case "rompimento":
      return "Rompimento";
    case "mudanca_de_regime":
      return "Mudanca de regime";
    case "realizacao":
      return "Realizacao";
    case "observacao":
    default:
      return "Observacao";
  }
}

export function getOperabilityReasons(opportunity: OpportunityListItem): OpportunityReason[] {
  const reasons: OpportunityReason[] = [];
  const netEdge = opportunity.estimated_net_trade_edge_pct;

  if (
    opportunity.pipeline_status === "blocked_signal" ||
    opportunity.opportunity_type === "avoid" ||
    (netEdge != null && netEdge < 0)
  ) {
    if (opportunity.opportunity_type === "avoid") {
      reasons.push({ label: "Bloqueado: evitar", tone: "negative" });
    } else if (netEdge != null && netEdge < 0) {
      reasons.push({ label: "Bloqueado: margem negativa", tone: "negative" });
    } else {
      reasons.push({ label: "Bloqueado", tone: "negative" });
    }
    if (opportunity.visibility_reason) {
      reasons.push({ label: opportunity.visibility_reason.replace(/_/g, " "), tone: "neutral" });
    }
    return reasons.slice(0, 3);
  }

  if (isOperableSignal(opportunity)) {
    reasons.push({ label: "Operavel", tone: "positive" });
  } else if (isInterestingSignal(opportunity)) {
    reasons.push({ label: "Interessante", tone: "neutral" });
  }

  if (opportunity.opportunity_type === "trade") {
    reasons.push({ label: "Trade", tone: "positive" });
  } else if (opportunity.opportunity_type === "hold") {
    reasons.push({ label: "Hold", tone: "warning" });
  }

  if (netEdge != null) {
    if (netEdge >= 0.3) {
      reasons.push({ label: `Margem +${netEdge.toFixed(2)}%`, tone: "positive" });
    } else if (netEdge < 0) {
      reasons.push({ label: "Margem negativa", tone: "negative" });
    }
  }

  if (opportunity.is_late_entry_risk) {
    reasons.push({ label: "Entrada tardia", tone: "warning" });
  }

  if (opportunity.alert_moment_type === "early_breakout") {
    reasons.push({ label: "Rompimento inicial", tone: "positive" });
  } else if (opportunity.alert_moment_type === "profit_zone" || opportunity.alert_moment_type === "extended") {
    reasons.push({ label: "Zona de realizacao", tone: "warning" });
  }

  if (
    opportunity.operational_range_quality === "high_quality_reusable_range" ||
    opportunity.operational_range_quality === "valid_large_trade"
  ) {
    reasons.push({ label: "Faixa forte", tone: "positive" });
  } else if (opportunity.operational_range_quality === "weak") {
    reasons.push({ label: "Faixa fraca", tone: "warning" });
  }

  const band = getExecutabilityBand(opportunity);
  if (band === "strong" || band === "good") {
    reasons.push({ label: "Liquidez OK", tone: "positive" });
  } else if (band === "poor") {
    reasons.push({ label: "Saida dificil", tone: "negative" });
  }

  const sellSlippage = opportunity.estimated_sell_slippage_bps;
  if (sellSlippage != null) {
    if (sellSlippage > 25) {
      reasons.push({ label: "Saida dificil", tone: "negative" });
    } else if (sellSlippage <= 10) {
      reasons.push({ label: "Saida leve", tone: "positive" });
    } else {
      reasons.push({ label: `Saida ${formatBps(sellSlippage)}`, tone: "warning" });
    }
  }

  const buySlippage = opportunity.estimated_buy_slippage_bps;
  if (buySlippage != null && buySlippage > 25) {
    reasons.push({ label: "Entrada cara", tone: "warning" });
  }

  const totalNotional = opportunity.total_notional_top_n;
  if (totalNotional != null) {
    if (totalNotional < 2_000) {
      reasons.push({ label: "Book raso", tone: "negative" });
    } else if (totalNotional >= 10_000) {
      reasons.push({ label: "Book profundo", tone: "positive" });
    }
  }

  if (opportunity.operability_size_label === "small_test_only") {
    reasons.push({ label: "So teste pequeno", tone: "warning" });
  } else if (opportunity.operability_size_label === "not_operable") {
    reasons.push({ label: "Sem tamanho operavel", tone: "negative" });
  }

  const deduped: OpportunityReason[] = [];
  const seen = new Set<string>();

  for (const reason of reasons) {
    if (seen.has(reason.label)) {
      continue;
    }
    seen.add(reason.label);
    deduped.push(reason);
  }

  return deduped.slice(0, 3);
}

export function getReasonToneClasses(tone: ReasonTone): string {
  switch (tone) {
    case "positive":
      return "border-emerald-500/20 bg-emerald-500/10 text-emerald-500";
    case "warning":
      return "border-amber-500/20 bg-amber-500/10 text-amber-500";
    case "negative":
      return "border-red-500/20 bg-red-500/10 text-red-500";
    case "neutral":
    default:
      return "border-border bg-muted/50 text-muted-foreground";
  }
}

export function getExecutabilityHighlight(opportunity: OpportunityListItem): string {
  const score = getExecutabilityScore(opportunity);
  if (score === null) {
    return "border-border bg-muted/30 text-muted-foreground";
  }
  if (score >= 80) return "border-emerald-500/20 bg-emerald-500/10 text-emerald-500";
  if (score >= 60) return "border-sky-500/20 bg-sky-500/10 text-sky-500";
  if (score >= 40) return "border-amber-500/20 bg-amber-500/10 text-amber-500";
  return "border-red-500/20 bg-red-500/10 text-red-500";
}

export function getOperabilityFillRatio(opportunity: OpportunityListItem, baselineOrderNotional = 1000): number | null {
  if (opportunity.fillable_notional_within_slippage_cap == null) {
    return null;
  }
  return clamp(opportunity.fillable_notional_within_slippage_cap / baselineOrderNotional, 0, 1);
}
