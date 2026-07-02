"use client";

import { useDeferredValue, useState } from "react";
import { Search, SlidersHorizontal } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  formatBps,
  formatCurrency,
  formatCurrencyCompact,
  formatOperationStatus,
  formatOperabilitySizeLabel,
  formatOpportunityFamily,
  formatNotionalOrFallback,
  formatSignedPercent,
  getExecutabilityHighlight,
  getExecutabilityScore,
  getOperationalScore,
  getOperationStatusTone,
  getOperabilityReasons,
  getReasonToneClasses,
  getSortValue,
  getTechnicalScore,
  hasExecutability,
  isInterestingSignal,
  isOperableSignal,
  type OpportunityListItem,
  type OpportunitySortMode,
} from "@/lib/opportunity-operability";
import { cn } from "@/lib/utils";

interface OpportunitiesTableProps {
  opportunities: OpportunityListItem[];
  loading?: boolean;
  onSelect?: (opportunity: OpportunityListItem) => void;
  title?: string;
  description?: string;
  emptyMessage?: string;
  compact?: boolean;
}

function movementBadge(type: string) {
  const map: Record<string, { label: string; variant: string }> = {
    strong_range: { label: "Forte", variant: "bg-emerald-500/15 text-emerald-500" },
    spike: { label: "Spike", variant: "bg-yellow-500/15 text-yellow-500" },
    weak: { label: "Fraco", variant: "bg-muted text-muted-foreground" },
    trap: { label: "Armadilha", variant: "bg-red-500/15 text-red-500" },
  };
  const info = map[type] || { label: type, variant: "bg-muted text-muted-foreground" };
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", info.variant)}>
      {info.label}
    </span>
  );
}

function movementPhaseBadge(phase?: string | null, late?: boolean) {
  if (!phase || phase === "neutral") return null;
  const map: Record<string, { label: string; variant: string }> = {
    accumulation: { label: "Acumulacao", variant: "bg-slate-500/15 text-slate-500" },
    early_breakout: { label: "Rompimento inicial", variant: "bg-emerald-500/15 text-emerald-500" },
    continuation: { label: "Continuacao", variant: "bg-blue-500/15 text-blue-500" },
    extended: { label: "Esticado", variant: "bg-amber-500/15 text-amber-500" },
    distribution_or_profit_zone: { label: "Realizacao", variant: "bg-orange-500/15 text-orange-500" },
    exhaustion: { label: "Esgotamento", variant: "bg-red-500/15 text-red-500" },
  };
  const info = map[phase] || { label: phase, variant: "bg-muted text-muted-foreground" };
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", info.variant)}>
      {late ? `${info.label} / tarde` : info.label}
    </span>
  );
}

function operationalRangeBadge(quality?: string | null, marginPct?: number | null) {
  if (!quality || quality === "none") return null;
  const map: Record<string, { label: string; variant: string }> = {
    weak: { label: "Faixa fraca", variant: "bg-amber-500/15 text-amber-500" },
    valid_small_trade: { label: "Faixa pequena", variant: "bg-sky-500/15 text-sky-500" },
    valid_medium_trade: { label: "Faixa media", variant: "bg-blue-500/15 text-blue-500" },
    valid_large_trade: { label: "Faixa grande", variant: "bg-emerald-500/15 text-emerald-500" },
    high_quality_reusable_range: { label: "Faixa reutilizavel", variant: "bg-emerald-500/15 text-emerald-500" },
  };
  const info = map[quality] || { label: quality, variant: "bg-muted text-muted-foreground" };
  const suffix = marginPct != null ? ` ${marginPct.toFixed(1)}%` : "";
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", info.variant)}>
      {info.label}{suffix}
    </span>
  );
}

function exchangeLabel(exchange: string): string {
  const map: Record<string, string> = {
    novadax: "NovaDAX",
    mercado_bitcoin: "Mercado BTC",
    binance: "Binance",
  };
  return map[exchange] || exchange;
}

function sortLabel(sortBy: OpportunitySortMode): string {
  switch (sortBy) {
    case "executability":
      return "operabilidade";
    case "gap":
      return "gap";
    case "volume":
      return "volume";
    case "volatility":
      return "volatilidade";
    case "spread":
      return "spread";
    case "score":
    default:
      return "score operacional";
  }
}

export function OpportunitiesTable({
  opportunities,
  loading,
  onSelect,
  title = "Oportunidades Detectadas",
  description,
  emptyMessage = "Nenhuma oportunidade encontrada",
  compact = false,
}: OpportunitiesTableProps) {
  const [search, setSearch] = useState("");
  const [exchangeFilter, setExchangeFilter] = useState<string>("all");
  const [movementFilter, setMovementFilter] = useState<string>("all");
  const [minScore, setMinScore] = useState("0");
  const [sortBy, setSortBy] = useState<OpportunitySortMode>("score");
  const [arbitrageOnly, setArbitrageOnly] = useState(false);
  const [operableOnly, setOperableOnly] = useState(false);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  const deferredSearch = useDeferredValue(search);
  const executabilityAvailable = opportunities.some(hasExecutability);

  const filtered = opportunities.filter((opportunity) => {
    if (deferredSearch && !opportunity.pair.toLowerCase().includes(deferredSearch.toLowerCase())) return false;
    if (exchangeFilter !== "all" && opportunity.exchange !== exchangeFilter) return false;
    if (movementFilter !== "all" && opportunity.movement_type !== movementFilter) return false;
    if (Number(minScore) > 0 && getOperationalScore(opportunity) < Number(minScore)) return false;
    if (arbitrageOnly && !opportunity.arbitrage_available) return false;
    if (operableOnly && !isOperableSignal(opportunity)) return false;
    return true;
  });

  const sorted = [...filtered].sort((left, right) => {
    const primaryDelta = getSortValue(right, sortBy) - getSortValue(left, sortBy);
    if (primaryDelta !== 0) {
      return primaryDelta;
    }

    const technicalDelta = getTechnicalScore(right) - getTechnicalScore(left);
    if (technicalDelta !== 0) {
      return technicalDelta;
    }

    const executabilityDelta = (getExecutabilityScore(right) ?? -1) - (getExecutabilityScore(left) ?? -1);
    if (executabilityDelta !== 0) {
      return executabilityDelta;
    }

    return Date.parse(right.detected_at) - Date.parse(left.detected_at);
  });

  const activeFiltersCount = [
    deferredSearch.trim().length > 0,
    Number(minScore) > 0,
    exchangeFilter !== "all",
    movementFilter !== "all",
    sortBy !== "score",
    arbitrageOnly,
    operableOnly,
  ].filter(Boolean).length;

  const topOperationalScore = sorted[0] ? getOperationalScore(sorted[0]) : 0;
  const topExecutabilityScore = sorted[0] ? getExecutabilityScore(sorted[0]) : null;
  const operableCount = opportunities.filter(isOperableSignal).length;
  const interestingCount = opportunities.filter(isInterestingSignal).length;

  const tableHeight = compact ? "h-[360px]" : "h-[540px]";

  return (
    <Card className="rounded-2xl">
      <CardHeader className="space-y-4 pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg">{title}</CardTitle>
            <p className="text-sm text-muted-foreground">
              {description ??
                (loading
                  ? "Atualizando sinais em tempo real..."
                  : `${sorted.length} sinais visiveis - ordenado por ${sortLabel(sortBy)}${
                      sortBy === "executability" && topExecutabilityScore != null
                        ? ` - melhor operabilidade ${topExecutabilityScore.toFixed(1)}`
                        : ` - melhor score operacional ${topOperationalScore.toFixed(1)}`
                    }`)}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-2 sm:flex">
            <SummaryCard label="Resultados" value={String(sorted.length)} />
            <SummaryCard label="Operaveis" value={String(operableCount)} />
            <SummaryCard label="Interessantes" value={String(interestingCount)} />
          </div>
        </div>

        <div className="flex flex-col gap-3 rounded-2xl border border-border/70 bg-muted/20 p-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
                Ranking principal
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant={sortBy === "score" ? "default" : "outline"}
                  onClick={() => setSortBy("score")}
                >
                  Score operacional
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={sortBy === "executability" ? "default" : "outline"}
                  disabled={!executabilityAvailable}
                  onClick={() => setSortBy("executability")}
                >
                  Operabilidade
                </Button>
              </div>
            </div>

            {!executabilityAvailable ? (
              <div className="rounded-xl border border-dashed px-3 py-2 text-xs text-muted-foreground">
                Payload atual ainda nao traz executabilidade. Mantendo leitura tecnica.
              </div>
            ) : null}
          </div>

          <div className="flex items-center justify-between gap-3 sm:hidden">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Search className="h-3.5 w-3.5" />
              <span>Busca e refinamento</span>
            </div>
            <button
              type="button"
              onClick={() => setMobileFiltersOpen((current) => !current)}
              className="inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium"
            >
              <SlidersHorizontal className="h-4 w-4" />
              {mobileFiltersOpen ? "Ocultar filtros" : "Mostrar filtros"}
            </button>
          </div>

          <div className={cn("hidden sm:block", mobileFiltersOpen && "block sm:block")}>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
              <Input
                placeholder="Buscar par..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className="h-10 sm:h-9 lg:col-span-2"
              />
              <Input
                placeholder="Score min."
                type="number"
                value={minScore}
                onChange={(event) => setMinScore(event.target.value)}
                className="h-10 sm:h-9"
              />
              <Select value={exchangeFilter} onValueChange={(value) => setExchangeFilter(value ?? "all")}>
                <SelectTrigger className="h-10 sm:h-9">
                  <SelectValue placeholder="Exchange" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  <SelectItem value="novadax">NovaDAX</SelectItem>
                  <SelectItem value="mercado_bitcoin">Mercado BTC</SelectItem>
                  <SelectItem value="binance">Binance</SelectItem>
                </SelectContent>
              </Select>
              <Select value={movementFilter} onValueChange={(value) => setMovementFilter(value ?? "all")}>
                <SelectTrigger className="h-10 sm:h-9">
                  <SelectValue placeholder="Movimento" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="strong_range">Forte</SelectItem>
                  <SelectItem value="spike">Spike</SelectItem>
                  <SelectItem value="weak">Fraco</SelectItem>
                  <SelectItem value="trap">Armadilha</SelectItem>
                </SelectContent>
              </Select>
              <Select value={sortBy} onValueChange={(value) => setSortBy((value as OpportunitySortMode) ?? "score")}>
                <SelectTrigger className="h-10 sm:h-9">
                  <SelectValue placeholder="Ordenar" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="score">Score operacional</SelectItem>
                  <SelectItem value="executability" disabled={!executabilityAvailable}>
                    Operabilidade
                  </SelectItem>
                  <SelectItem value="gap">Gap</SelectItem>
                  <SelectItem value="volume">Volume</SelectItem>
                  <SelectItem value="volatility">Volatilidade</SelectItem>
                  <SelectItem value="spread">Spread</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="mt-2 flex flex-wrap gap-2">
              <label className="inline-flex h-10 items-center gap-2 rounded-xl border px-3 text-sm text-muted-foreground sm:h-9">
                <input
                  type="checkbox"
                  checked={operableOnly}
                  disabled={!executabilityAvailable}
                  onChange={(event) => setOperableOnly(event.target.checked)}
                />
                Operaveis
              </label>
              <label className="inline-flex h-10 items-center gap-2 rounded-xl border px-3 text-sm text-muted-foreground sm:h-9">
                <input
                  type="checkbox"
                  checked={arbitrageOnly}
                  onChange={(event) => setArbitrageOnly(event.target.checked)}
                />
                Arbitragem
              </label>
              <div className="inline-flex h-10 items-center gap-2 rounded-xl border border-dashed px-3 text-sm text-muted-foreground sm:h-9">
                <span>{activeFiltersCount} filtros ativos</span>
              </div>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <div className="space-y-3 px-4 pb-4 sm:hidden">
          {loading ? (
            Array.from({ length: 5 }).map((_, index) => (
              <div key={index} className="rounded-2xl border p-4">
                <div className="space-y-3">
                  <div className="h-5 w-24 animate-pulse rounded bg-muted" />
                  <div className="h-4 w-32 animate-pulse rounded bg-muted" />
                  <div className="grid grid-cols-2 gap-2">
                    {Array.from({ length: 6 }).map((__, cellIndex) => (
                      <div key={cellIndex} className="h-16 animate-pulse rounded-xl bg-muted" />
                    ))}
                  </div>
                </div>
              </div>
            ))
          ) : sorted.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-center text-sm text-muted-foreground">
              {emptyMessage}
            </div>
          ) : (
            sorted.map((opportunity) => {
              const executabilityScore = getExecutabilityScore(opportunity);
              const reasons = getOperabilityReasons(opportunity);
              const statusTone = getOperationStatusTone(opportunity.operation_status);

              return (
                <button
                  key={opportunity.id}
                  type="button"
                  data-testid={`opportunity-${opportunity.id}`}
                  className={cn(
                    "w-full rounded-2xl border p-4 text-left transition-colors",
                    statusTone === "positive" && "bg-emerald-500/5 hover:bg-emerald-500/10",
                    statusTone === "warning" && "bg-amber-500/5 hover:bg-amber-500/10",
                    statusTone === "negative" && "bg-red-500/5 hover:bg-red-500/10",
                    opportunity.arbitrage_available && "ring-1 ring-blue-500/20",
                  )}
                  onClick={() => onSelect?.(opportunity)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-lg font-semibold leading-none">{opportunity.pair.replace("_", "/")}</p>
                      <p className="text-sm text-muted-foreground">{exchangeLabel(opportunity.exchange)}</p>
                      <Badge
                        variant="outline"
                        className={cn("w-fit border px-2 py-0.5 text-xs", getReasonToneClasses(getOperationStatusTone(opportunity.operation_status)))}
                      >
                        {formatOperationStatus(opportunity.operation_status)}
                      </Badge>
                      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                        Detectado{" "}
                        {new Date(opportunity.detected_at).toLocaleTimeString("pt-BR", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <Badge variant="outline" className="rounded-full px-2.5 py-1">
                        {formatOpportunityFamily(opportunity.opportunity_family)}
                      </Badge>
                      {executabilityScore != null ? (
                        <Badge
                          variant="outline"
                          className={cn(
                            "rounded-full px-2.5 py-1 font-bold tabular-nums",
                            getExecutabilityHighlight(opportunity),
                          )}
                        >
                          Op {executabilityScore.toFixed(1)}
                        </Badge>
                      ) : null}
                    </div>
                  </div>

                  <div className="mt-3 rounded-2xl border bg-muted/20 p-3 text-sm">
                    <p className="font-medium">{opportunity.main_reason ?? "Ativo em observacao"}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Entrada: {opportunity.entry_zone ?? "n/d"} - Saida: {opportunity.exit_zone ?? "n/d"} - Tamanho:{" "}
                      {opportunity.suggested_capital_range_brl ?? "n/d"}
                    </p>
                  </div>

                  <div className="mt-4 flex flex-wrap items-center gap-2">
                    {movementBadge(opportunity.movement_type)}
                    {movementPhaseBadge(opportunity.movement_phase, opportunity.is_late_entry_risk)}
                    {operationalRangeBadge(opportunity.operational_range_quality, opportunity.operational_range_margin_pct)}
                    {reasons.map((reason) => (
                      <Badge
                        key={`${opportunity.id}-${reason.label}`}
                        variant="outline"
                        className={cn("border px-2 py-0.5 text-[11px]", getReasonToneClasses(reason.tone))}
                      >
                        {reason.label}
                      </Badge>
                    ))}
                    {opportunity.arbitrage_available ? (
                      <Badge variant="outline" className="border-blue-500/20 text-blue-500">
                        Gap {opportunity.cross_exchange_gap_pct.toFixed(2)}%
                      </Badge>
                    ) : null}
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <MobileMetric label="Preco" value={formatCurrency(opportunity.last_price)} highlight />
                    <MobileMetric
                      label="Variacao"
                      value={formatSignedPercent(opportunity.change_pct)}
                      valueClass={opportunity.change_pct >= 0 ? "text-emerald-500" : "text-red-500"}
                      highlight
                    />
                    <MobileMetric label="Volume 24h" value={formatCurrencyCompact(opportunity.quote_volume_24h)} />
                    <MobileMetric label="Liquidez" value={formatNotionalOrFallback(opportunity)} />
                    <MobileMetric
                      label="Capacidade"
                      value={
                        opportunity.max_operable_order_notional_brl != null
                          ? `${formatOperabilitySizeLabel(opportunity.operability_size_label)} - ${formatCurrencyCompact(opportunity.max_operable_order_notional_brl)}`
                          : formatOperabilitySizeLabel(opportunity.operability_size_label)
                      }
                    />
                    <MobileMetric label="Spread" value={`${opportunity.spread_pct.toFixed(4)}%`} />
                    <MobileMetric
                      label="Faixa operacional"
                      value={
                        opportunity.operational_range_margin_pct != null
                          ? `${opportunity.operational_range_margin_pct.toFixed(2)}%`
                          : "n/d"
                      }
                    />
                    <MobileMetric
                      label={executabilityScore != null ? "Slippage saida" : "Volatilidade"}
                      value={
                        executabilityScore != null
                          ? formatBps(opportunity.estimated_sell_slippage_bps)
                          : `${opportunity.volatility_pct.toFixed(2)}%`
                      }
                    />
                  </div>

                  <div className="mt-4 flex items-center justify-between border-t border-border/60 pt-3 text-xs text-muted-foreground">
                    <span>Toque para abrir os detalhes</span>
                    <span>Ordenado por {sortLabel(sortBy)}</span>
                  </div>
                </button>
              );
            })
          )}
        </div>

        <div className="hidden sm:block">
          <ScrollArea className={tableHeight}>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-44">Status</TableHead>
                  <TableHead>Par</TableHead>
                  <TableHead>Exchange</TableHead>
                  <TableHead>Tese operacional</TableHead>
                  <TableHead>Entrada / Saida</TableHead>
                  <TableHead>Volume 24h</TableHead>
                  <TableHead>Liquidez</TableHead>
                  <TableHead>Spread</TableHead>
                  <TableHead>Operabilidade</TableHead>
                  <TableHead>Movimento</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={i}>
                      {Array.from({ length: 10 }).map((__, j) => (
                        <TableCell key={j}>
                          <div className="h-4 w-full animate-pulse rounded bg-muted" />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : sorted.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="h-32 text-center text-muted-foreground">
                      {emptyMessage}
                    </TableCell>
                  </TableRow>
                ) : (
                  sorted.map((opportunity) => {
                    const executabilityScore = getExecutabilityScore(opportunity);
                    const reasons = getOperabilityReasons(opportunity);
                    const statusTone = getOperationStatusTone(opportunity.operation_status);

                    return (
                      <TableRow
                        key={opportunity.id}
                        data-testid={`opportunity-${opportunity.id}`}
                        className={cn(
                          "cursor-pointer transition-colors",
                          statusTone === "positive" && "bg-emerald-500/5 hover:bg-emerald-500/10",
                          statusTone === "warning" && "hover:bg-amber-500/5",
                          statusTone === "negative" && "hover:bg-red-500/5",
                          opportunity.arbitrage_available && "ring-1 ring-blue-500/20",
                        )}
                        onClick={() => onSelect?.(opportunity)}
                      >
                        <TableCell>
                          <div className="flex flex-col gap-1.5">
                            <Badge
                              variant="outline"
                              className={cn("w-fit font-semibold", getReasonToneClasses(getOperationStatusTone(opportunity.operation_status)))}
                            >
                              {formatOperationStatus(opportunity.operation_status)}
                            </Badge>
                            <span className="text-[11px] text-muted-foreground">
                              {formatOpportunityFamily(opportunity.opportunity_family)}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="font-medium">{opportunity.pair}</TableCell>
                        <TableCell className="text-muted-foreground">
                          {exchangeLabel(opportunity.exchange)}
                        </TableCell>
                        <TableCell>
                          <div className="max-w-[280px]">
                            <p className="text-sm font-medium">{opportunity.main_reason ?? "Ativo em observacao"}</p>
                            <p className="text-[11px] text-muted-foreground">
                              Risco {opportunity.risk_label ?? "n/d"} - {opportunity.liquidity_label?.replaceAll("_", " ") ?? "liquidez n/d"}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col text-xs">
                            <span>Entrada: {opportunity.entry_zone ?? "n/d"}</span>
                            <span className="text-muted-foreground">Saida: {opportunity.exit_zone ?? "n/d"}</span>
                          </div>
                        </TableCell>
                        <TableCell className="tabular-nums">
                          <div className="flex flex-col">
                            <span>{formatCurrencyCompact(opportunity.quote_volume_24h)}</span>
                            <span className="text-[11px] text-muted-foreground">
                              Vol {opportunity.volatility_pct.toFixed(2)}%
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="tabular-nums">
                          <div className="flex flex-col">
                            <span>{formatNotionalOrFallback(opportunity)}</span>
                            <span className="text-[11px] text-muted-foreground">
                              {opportunity.liquidity_units.toLocaleString("pt-BR")} un.
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="tabular-nums">{opportunity.spread_pct.toFixed(4)}%</TableCell>
                        <TableCell>
                          {executabilityScore != null ? (
                            <div className="flex flex-col gap-1">
                              <Badge
                                variant="outline"
                                className={cn("w-fit font-semibold", getExecutabilityHighlight(opportunity))}
                              >
                                {executabilityScore.toFixed(1)}
                              </Badge>
                              <span className="text-[11px] text-muted-foreground">
                                {isOperableSignal(opportunity) ? "Operavel" : "Monitorar"} - saida{" "}
                                {formatBps(opportunity.estimated_sell_slippage_bps)}
                              </span>
                              <span className="text-[11px] text-muted-foreground">
                                {formatOperabilitySizeLabel(opportunity.operability_size_label)}
                                {opportunity.max_operable_order_notional_brl != null
                                  ? ` ate ${formatCurrencyCompact(opportunity.max_operable_order_notional_brl)}`
                                  : ""}
                              </span>
                            </div>
                          ) : (
                            <div className="flex flex-col gap-1">
                              <span className="text-sm font-medium text-muted-foreground">Tecnico</span>
                              <span className="text-[11px] text-muted-foreground">Payload legado</span>
                            </div>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-1.5">
                            <div className="flex flex-wrap items-center gap-1.5">
                              {movementBadge(opportunity.movement_type)}
                              {movementPhaseBadge(opportunity.movement_phase, opportunity.is_late_entry_risk)}
                              {operationalRangeBadge(opportunity.operational_range_quality, opportunity.operational_range_margin_pct)}
                              {opportunity.arbitrage_available ? (
                                <span className="text-[11px] font-medium text-blue-500">
                                  Gap {opportunity.cross_exchange_gap_pct.toFixed(2)}%
                                </span>
                              ) : null}
                            </div>
                            <div className="flex flex-wrap gap-1">
                              {reasons.map((reason) => (
                                <span
                                  key={`${opportunity.id}-desktop-${reason.label}`}
                                  className={cn(
                                    "rounded-full border px-2 py-0.5 text-[11px]",
                                    getReasonToneClasses(reason.tone),
                                  )}
                                >
                                  {reason.label}
                                </span>
                              ))}
                            </div>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border bg-muted/25 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold">{value}</p>
    </div>
  );
}

function MobileMetric({
  label,
  value,
  valueClass,
  highlight = false,
}: {
  label: string;
  value: string;
  valueClass?: string;
  highlight?: boolean;
}) {
  return (
    <div className={cn("rounded-xl border border-border/60 bg-muted/35 p-3", highlight && "bg-background/70")}>
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={cn("mt-1 text-sm font-semibold", valueClass)}>{value}</p>
    </div>
  );
}
