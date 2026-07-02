import type { Exchange } from "./types";

export const ALL_EXCHANGES: { id: Exchange; label: string }[] = [
  { id: "novadax", label: "NovaDAX" },
  { id: "mercado_bitcoin", label: "Mercado Bitcoin" },
  { id: "binance", label: "Binance" },
];

export type MissedSignalWindow = "1" | "4" | "24" | "72" | "custom";

export function normalizePairInput(value: string): string {
  return value.trim().toUpperCase().replace("/", "_").replace("-", "_");
}

export function formatExchangeDisplay(exchange: Exchange | string | null | undefined) {
  return ALL_EXCHANGES.find((item) => item.id === exchange)?.label ?? exchange ?? "-";
}

export function formatReasonCounts(reasons: Record<string, number>): string {
  return Object.entries(reasons)
    .slice(0, 4)
    .map(([reason, count]) => `${formatPipelineReason(reason)} (${count})`)
    .join(", ");
}

export function formatPipelineStage(stage: string): string {
  const labels: Record<string, string> = {
    light_scan: "Scan leve",
    promotion: "Promocao",
    deep_scan: "Analise profunda",
    ranking: "Ranking",
    workspace_projection: "Workspace",
    alert: "Alerta",
  };
  return labels[stage] ?? stage;
}

export function formatPipelineStatus(status: string): string {
  const labels: Record<string, string> = {
    candidate: "candidato",
    promoted: "promovido",
    discarded: "descartado",
    blocked: "bloqueado",
    ranked: "ranqueado",
    opportunity: "sinal",
    visible: "visivel",
    sent: "enviado",
    error: "erro",
  };
  return labels[status] ?? status;
}

export function formatPipelineReason(reason?: string | null): string {
  if (!reason) return "-";
  const labels: Record<string, string> = {
    accumulation_only: "acumulacao sem gatilho",
    below_alert_threshold: "abaixo do limite de alerta",
    below_min_executability: "executabilidade abaixo do minimo",
    cache_empty: "catalogo vazio",
    cache_stale: "catalogo desatualizado",
    candidate: "candidato",
    candidate_limit_lower_priority: "prioridade menor no limite de candidatos",
    config_match: "passou nos filtros do workspace",
    cooldown_active: "cooldown ativo",
    daily_alert_limit_reached: "limite diario de alertas atingido",
    entered_cycle_ranking: "entrou no ranking do ciclo",
    exchange_disabled: "exchange desabilitada no workspace",
    exchange_not_in_alert_scope: "exchange fora do alerta",
    high_operational_risk: "risco operacional alto",
    incomplete_operational_thesis: "tese operacional incompleta",
    insufficient_alert_worthiness: "sem urgencia suficiente para alerta",
    insufficient_exit_liquidity: "liquidez de saida insuficiente",
    insufficient_liquidity: "liquidez insuficiente",
    insufficient_movement: "movimento insuficiente",
    insufficient_volume: "volume insuficiente",
    lower_than_competing_signals: "ficou fora do top de alertas",
    missing_candles: "candles ausentes",
    missing_order_book: "book ausente",
    missing_required_market_data: "dados de mercado insuficientes",
    missing_ticker: "ticker ausente",
    movement_type_not_supported: "tipo de movimento nao suportado",
    no_actionable_operation: "sem operacao acionavel",
    not_brl_pair: "par nao BRL",
    not_operable_for_alert_scope: "nao operavel para alerta",
    opportunity_type_not_alertable: "tipo de oportunidade nao alertavel",
    pair_inactive: "par inativo",
    pair_not_enabled: "par fora da lista do workspace",
    pair_not_in_alert_scope: "par fora do alerta",
    pair_not_in_catalog: "par fora do catalogo",
    pair_not_tradable: "par nao negociavel",
    preparation_without_trigger: "preparacao sem gatilho",
    selected_for_deep_scan: "selecionado para analise profunda",
    spread_above_threshold: "spread acima do limite",
    spread_unfavorable: "spread desfavoravel",
    telegram_disabled: "Telegram desativado",
    telegram_not_configured: "Telegram nao configurado",
    telegram_sent: "Telegram enviado",
    volume_below_minimum: "volume abaixo do minimo",
    volatility_below_threshold: "volatilidade abaixo do limite",
    workspace_alert_scope_mismatch: "fora do escopo de alerta",
  };

  const baseReason = reason.split(":")[0];
  const baseLabel = labels[baseReason] ?? baseReason.replaceAll("_", " ");
  if (!reason.includes(":")) return baseLabel;
  return `${baseLabel}: ${reason.split(":").slice(1).join(":").replaceAll("_", " ")}`;
}

export function formatMissedSignalFinalState(state: string): string {
  const labels: Record<string, string> = {
    alerted: "Alerta enviado.",
    alert_blocked: "Sinal chegou ao alerta, mas foi bloqueado.",
    audited_without_terminal_decision: "Houve auditoria, mas sem decisao final clara.",
    discarded_before_alert: "Sinal descartado antes de virar alerta.",
    insufficient_audit_data: "Sem trilha auditavel no periodo.",
    not_monitorable: "Par nao monitoravel no periodo.",
    not_visible_for_workspace: "Sinal nao ficou visivel para este workspace.",
    provider_error: "Falha ou dado incompleto na exchange.",
    technical_signal_created: "Sinal tecnico criado, sem alerta registrado.",
    visible_not_alerted: "Sinal visivel, mas nao alertado.",
  };
  return labels[state] ?? state.replaceAll("_", " ");
}

export function formatCatalogStatus(status?: string | null): string {
  if (!status) return "indeterminado";
  const labels: Record<string, string> = {
    ok: "ok",
    warning: "atencao",
    error: "erro",
  };
  return labels[status] ?? status;
}

export function formatEventDetails(details: Record<string, unknown>): string {
  const compactEntries = Object.entries(details)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .slice(0, 4);

  if (!compactEntries.length) return "-";

  return compactEntries
    .map(([key, value]) => {
      const formattedValue = typeof value === "number" ? Number(value.toFixed(4)) : String(value);
      return `${key.replaceAll("_", " ")}: ${formattedValue}`;
    })
    .join(" · ");
}
