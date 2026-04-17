import type { Opportunity } from "./types";

export type OpportunitySortMode =
  | "score"
  | "executability"
  | "gap"
  | "volume"
  | "volatility"
  | "spread";

type ReasonTone = "positive" | "warning" | "negative" | "neutral";

export interface OpportunityReason {
  label: string;
  tone: ReasonTone;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function getTechnicalScore(opportunity: Opportunity): number {
  return opportunity.technical_score ?? opportunity.score;
}

export function getExecutabilityScore(opportunity: Opportunity): number | null {
  return typeof opportunity.executability_score === "number"
    ? opportunity.executability_score
    : null;
}

export function hasExecutability(opportunity: Opportunity): boolean {
  return (
    getExecutabilityScore(opportunity) !== null ||
    opportunity.total_notional_top_n != null ||
    opportunity.estimated_buy_slippage_bps != null ||
    opportunity.estimated_sell_slippage_bps != null ||
    opportunity.fillable_notional_within_slippage_cap != null
  );
}

export function getExecutabilityBand(opportunity: Opportunity): string | null {
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

export function getExecutabilityBandLabel(opportunity: Opportunity): string {
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

export function isInterestingSignal(opportunity: Opportunity): boolean {
  return opportunity.interesting_signal ?? true;
}

export function isOperableSignal(opportunity: Opportunity): boolean {
  return opportunity.operable_signal ?? false;
}

export function getSortValue(opportunity: Opportunity, sortBy: OpportunitySortMode): number {
  switch (sortBy) {
    case "executability":
      return getExecutabilityScore(opportunity) ?? -1;
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
      return getTechnicalScore(opportunity);
  }
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

export function formatNotionalOrFallback(opportunity: Opportunity): string {
  if (opportunity.total_notional_top_n != null) {
    return formatCurrencyCompact(opportunity.total_notional_top_n);
  }
  return `${opportunity.liquidity_units.toLocaleString("pt-BR")} un.`;
}

export function getOperabilityReasons(opportunity: Opportunity): OpportunityReason[] {
  const reasons: OpportunityReason[] = [];

  if (isOperableSignal(opportunity)) {
    reasons.push({ label: "Operavel", tone: "positive" });
  } else if (isInterestingSignal(opportunity)) {
    reasons.push({ label: "Interessante", tone: "neutral" });
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

export function getExecutabilityHighlight(opportunity: Opportunity): string {
  const score = getExecutabilityScore(opportunity);
  if (score === null) {
    return "border-border bg-muted/30 text-muted-foreground";
  }
  if (score >= 80) return "border-emerald-500/20 bg-emerald-500/10 text-emerald-500";
  if (score >= 60) return "border-sky-500/20 bg-sky-500/10 text-sky-500";
  if (score >= 40) return "border-amber-500/20 bg-amber-500/10 text-amber-500";
  return "border-red-500/20 bg-red-500/10 text-red-500";
}

export function getOperabilityFillRatio(opportunity: Opportunity, baselineOrderNotional = 1000): number | null {
  if (opportunity.fillable_notional_within_slippage_cap == null) {
    return null;
  }
  return clamp(opportunity.fillable_notional_within_slippage_cap / baselineOrderNotional, 0, 1);
}
