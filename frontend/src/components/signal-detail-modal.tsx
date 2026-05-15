"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { submitSignalFeedback } from "@/lib/api";
import type { Opportunity, SignalFeedbackLabel } from "@/lib/types";
import {
  formatBps,
  formatCurrency,
  formatCurrencyCompact,
  formatSignedPercent,
  getExecutabilityBandLabel,
  getExecutabilityHighlight,
  getExecutabilityScore,
  getOperabilityFillRatio,
  getOperabilityReasons,
  getReasonToneClasses,
  getTechnicalScore,
  hasExecutability,
  isInterestingSignal,
  isOperableSignal,
} from "@/lib/opportunity-operability";
import { cn } from "@/lib/utils";

interface SignalDetailModalProps {
  opportunity: Opportunity | null;
  open: boolean;
  onClose: () => void;
}

function scoreColor(score: number): string {
  if (score >= 70) return "bg-emerald-500/15 text-emerald-500 border-emerald-500/20";
  if (score >= 40) return "bg-yellow-500/15 text-yellow-500 border-yellow-500/20";
  return "bg-red-500/15 text-red-500 border-red-500/20";
}

function exchangeLabel(exchange: string): string {
  const map: Record<string, string> = {
    novadax: "NovaDAX",
    mercado_bitcoin: "Mercado Bitcoin",
    binance: "Binance",
  };
  return map[exchange] || exchange;
}

const CHART_GRID_STROKE = "var(--border)";
const CHART_AXIS_TICK = {
  fill: "var(--muted-foreground)",
  fontSize: 11,
} as const;
const CHART_TOOLTIP_STYLE = {
  backgroundColor: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: "8px",
  color: "var(--card-foreground)",
  fontSize: "12px",
} as const;
const CHART_TOOLTIP_LABEL_STYLE = {
  color: "var(--card-foreground)",
} as const;
const CHART_TOOLTIP_ITEM_STYLE = {
  color: "var(--card-foreground)",
} as const;

export function SignalDetailModal({
  opportunity: opportunity,
  open,
  onClose,
}: SignalDetailModalProps) {
  const [feedbackStatus, setFeedbackStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  if (!opportunity) return null;

  const technicalScore = getTechnicalScore(opportunity);
  const executabilityScore = getExecutabilityScore(opportunity);
  const showExecutability = hasExecutability(opportunity);
  const reasons = getOperabilityReasons(opportunity);
  const fillRatio = getOperabilityFillRatio(opportunity);
  const chartData = (opportunity.klines || []).map((kline) => ({
    time: new Date(kline.open_time).toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
    }),
    price: kline.close,
    volume: kline.volume,
    high: kline.high,
    low: kline.low,
  }));

  async function handleFeedback(feedbackLabel: SignalFeedbackLabel) {
    if (!opportunity) return;
    setFeedbackStatus("saving");
    try {
      await submitSignalFeedback({
        signal_id: opportunity.technical_signal_id,
        opportunity_id: opportunity.id,
        feedback_label: feedbackLabel,
      });
      setFeedbackStatus("saved");
    } catch {
      setFeedbackStatus("error");
    }
  }

  return (
    <Dialog open={open} onOpenChange={() => onClose()}>
      <DialogContent className="max-h-[90vh] max-w-4xl overflow-y-auto rounded-2xl">
        <DialogHeader className="space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-2">
              <DialogTitle className="flex flex-wrap items-center gap-3">
                <span className="text-xl font-bold">{opportunity.pair.replace("_", "/")}</span>
                <span className="text-sm text-muted-foreground">{exchangeLabel(opportunity.exchange)}</span>
              </DialogTitle>
              <div className="flex flex-wrap gap-2">
                <Badge
                  variant="outline"
                  className={cn("text-sm font-bold", scoreColor(technicalScore))}
                >
                  Score tecnico {technicalScore.toFixed(1)}
                </Badge>
                {executabilityScore != null ? (
                  <Badge
                    variant="outline"
                    className={cn("text-sm font-bold", getExecutabilityHighlight(opportunity))}
                  >
                    Operabilidade {executabilityScore.toFixed(1)}
                  </Badge>
                ) : null}
                <Badge variant="outline" className="text-sm">
                  {isOperableSignal(opportunity)
                    ? "Operavel"
                    : isInterestingSignal(opportunity)
                      ? "Interessante"
                      : "Nao classificado"}
                </Badge>
              </div>
            </div>

            <div className="rounded-2xl border bg-muted/20 px-4 py-3 text-sm">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Leitura rapida</p>
              <p className="mt-1 font-semibold">
                {showExecutability
                  ? `${getExecutabilityBandLabel(opportunity)} • saida ${formatBps(opportunity.estimated_sell_slippage_bps)}`
                  : "Payload tecnico sem camada de operabilidade"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Detectado em{" "}
                {new Date(opportunity.detected_at).toLocaleString("pt-BR", {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
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
        </DialogHeader>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <DetailCard label="Preco" value={formatCurrency(opportunity.last_price)} />
          <DetailCard
            label="Variacao"
            value={formatSignedPercent(opportunity.change_pct)}
            valueClass={opportunity.change_pct >= 0 ? "text-emerald-500" : "text-red-500"}
          />
          <DetailCard label="Spread" value={`${opportunity.spread_pct.toFixed(4)}%`} />
          <DetailCard label="Volatilidade" value={`${opportunity.volatility_pct.toFixed(2)}%`} />
          <DetailCard label="Volume 24h" value={formatCurrencyCompact(opportunity.quote_volume_24h)} />
          <DetailCard
            label="Liquidez"
            value={
              opportunity.total_notional_top_n != null
                ? formatCurrencyCompact(opportunity.total_notional_top_n)
                : `${opportunity.liquidity_units.toLocaleString("pt-BR")} un.`
            }
          />
          <DetailCard
            label="Movimento"
            value={opportunity.movement_type.replace("_", " ")}
          />
          <DetailCard
            label="Gap Cross"
            value={`${opportunity.cross_exchange_gap_pct.toFixed(2)}%`}
            valueClass={opportunity.arbitrage_available ? "text-blue-500" : undefined}
          />
        </div>

        <Separator className="my-4" />

        {showExecutability ? (
          <div className="space-y-4">
            <div className="flex flex-col gap-1">
              <h4 className="text-sm font-semibold">Leitura operacional</h4>
              <p className="text-sm text-muted-foreground">
                Esta camada separa o que apenas chama atencao do que parece executavel para uma ordem baseline.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <DetailCard
                label="Bid top N"
                value={
                  opportunity.bid_notional_top_n != null
                    ? formatCurrencyCompact(opportunity.bid_notional_top_n)
                    : "n/d"
                }
              />
              <DetailCard
                label="Ask top N"
                value={
                  opportunity.ask_notional_top_n != null
                    ? formatCurrencyCompact(opportunity.ask_notional_top_n)
                    : "n/d"
                }
              />
              <DetailCard
                label="Slippage compra"
                value={formatBps(opportunity.estimated_buy_slippage_bps)}
              />
              <DetailCard
                label="Slippage saida"
                value={formatBps(opportunity.estimated_sell_slippage_bps)}
                valueClass={
                  opportunity.estimated_sell_slippage_bps != null && opportunity.estimated_sell_slippage_bps > 25
                    ? "text-red-500"
                    : undefined
                }
              />
              <DetailCard
                label="Executabilidade"
                value={
                  executabilityScore != null
                    ? `${executabilityScore.toFixed(1)} • ${getExecutabilityBandLabel(opportunity)}`
                    : "n/d"
                }
              />
              <DetailCard
                label="Fillable no cap"
                value={
                  opportunity.fillable_notional_within_slippage_cap != null
                    ? formatCurrencyCompact(opportunity.fillable_notional_within_slippage_cap)
                    : "n/d"
                }
              />
              <DetailCard
                label="Cobertura da ordem"
                value={fillRatio != null ? `${Math.round(fillRatio * 100)}%` : "n/d"}
              />
              <DetailCard
                label="Versoes"
                value={[
                  opportunity.score_version ?? "score n/d",
                  opportunity.executability_version ?? "exec n/d",
                ].join(" • ")}
              />
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed bg-muted/20 p-4 text-sm text-muted-foreground">
            Este sinal veio de um payload legado. O dashboard preserva a leitura tecnica, mas a explicacao de
            operabilidade so aparece quando o backend enviar a nova camada de executabilidade.
          </div>
        )}

        {opportunity.cross_exchange_reference_exchange || opportunity.cross_exchange_reference_price ? (
          <>
            <Separator className="my-4" />
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <DetailCard
                label="Exchange referencia"
                value={opportunity.cross_exchange_reference_exchange ?? "-"}
              />
              <DetailCard
                label="Preco referencia"
                value={
                  opportunity.cross_exchange_reference_price != null
                    ? formatCurrency(opportunity.cross_exchange_reference_price)
                    : "-"
                }
              />
              <DetailCard
                label="Confianca historica"
                value={`${(opportunity.historical_confidence * 100).toFixed(1)}%`}
              />
            </div>
          </>
        ) : null}

        <Separator className="my-4" />

        <div className="space-y-4">
          <div className="flex flex-col gap-1">
            <h4 className="text-sm font-semibold">Faixa e momento operacional</h4>
            <p className="text-sm text-muted-foreground">
              Use esta leitura para separar entrada, continuidade, realizacao e sinal atrasado.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <DetailCard
              label="Fase"
              value={opportunity.movement_phase?.replaceAll("_", " ") ?? "neutral"}
              valueClass={opportunity.is_late_entry_risk ? "text-amber-500" : undefined}
            />
            <DetailCard
              label="Momento"
              value={opportunity.alert_moment_type?.replaceAll("_", " ") ?? "neutral"}
            />
            <DetailCard
              label="Margem faixa"
              value={
                opportunity.operational_range_margin_pct != null
                  ? `${opportunity.operational_range_margin_pct.toFixed(2)}%`
                  : "n/d"
              }
            />
            <DetailCard
              label="Capacidade estimada"
              value={
                opportunity.capital_capacity_estimate_brl != null
                  ? formatCurrencyCompact(opportunity.capital_capacity_estimate_brl)
                  : "n/d"
              }
            />
            <DetailCard
              label="Zona compra"
              value={
                opportunity.operational_buy_zone_low != null && opportunity.operational_buy_zone_high != null
                  ? `${formatCurrency(opportunity.operational_buy_zone_low)} - ${formatCurrency(opportunity.operational_buy_zone_high)}`
                  : "n/d"
              }
            />
            <DetailCard
              label="Zona venda"
              value={
                opportunity.operational_sell_zone_low != null && opportunity.operational_sell_zone_high != null
                  ? `${formatCurrency(opportunity.operational_sell_zone_low)} - ${formatCurrency(opportunity.operational_sell_zone_high)}`
                  : "n/d"
              }
            />
            <DetailCard
              label="Qualidade faixa"
              value={opportunity.operational_range_quality?.replaceAll("_", " ") ?? "none"}
            />
            <DetailCard
              label="Motivo"
              value={opportunity.alert_reason ?? opportunity.phase_reason ?? "n/d"}
            />
            <DetailCard
              label="Valor de alerta"
              value={
                opportunity.alert_worthiness_score != null
                  ? `${opportunity.alert_worthiness_score.toFixed(1)}${opportunity.has_actionable_trigger ? " • acionavel" : " • sem gatilho"}`
                  : "n/d"
              }
              valueClass={opportunity.has_actionable_trigger ? "text-emerald-500" : "text-amber-500"}
            />
            <DetailCard
              label="Gatilho"
              value={opportunity.alert_trigger_type?.replaceAll("_", " ") ?? "nenhum"}
            />
            <DetailCard
              label="Bloqueio alerta"
              value={opportunity.alert_block_reason?.replaceAll("_", " ") ?? "n/d"}
              valueClass={opportunity.alert_block_reason ? "text-amber-500" : undefined}
            />
            <DetailCard
              label="Estado alerta"
              value={opportunity.alert_state_key?.replaceAll("|", " • ") ?? "n/d"}
            />
          </div>
        </div>

        <Separator className="my-4" />

        <div className="space-y-3">
          <div>
            <h4 className="text-sm font-semibold">Feedback do sinal</h4>
            <p className="text-sm text-muted-foreground">
              Marque rapidamente se este sinal foi util, atrasado ou pouco operacional.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {FEEDBACK_ACTIONS.map((action) => (
              <Button
                key={action.label}
                type="button"
                size="sm"
                variant="outline"
                disabled={feedbackStatus === "saving"}
                onClick={() => void handleFeedback(action.value)}
              >
                {action.label}
              </Button>
            ))}
          </div>
          {feedbackStatus === "saved" ? (
            <p className="text-xs text-emerald-500">Feedback registrado.</p>
          ) : feedbackStatus === "error" ? (
            <p className="text-xs text-red-500">Nao foi possivel registrar o feedback.</p>
          ) : null}
        </div>

        {chartData.length > 0 ? (
          <>
            <Separator className="my-4" />
            <div className="space-y-4">
              <div>
                <h4 className="mb-2 text-sm font-medium text-muted-foreground">
                  Preco recente
                </h4>
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--primary)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} />
                    <XAxis
                      dataKey="time"
                      tick={CHART_AXIS_TICK}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={CHART_AXIS_TICK}
                      axisLine={false}
                      tickLine={false}
                      domain={["auto", "auto"]}
                      tickFormatter={(value: number) => value.toLocaleString("pt-BR")}
                    />
                    <Tooltip
                      contentStyle={CHART_TOOLTIP_STYLE}
                      labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                      itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                      formatter={(value) => [
                        formatCurrency(Number(value)),
                        "Preco",
                      ]}
                    />
                    <Area
                      type="monotone"
                      dataKey="price"
                      stroke="var(--primary)"
                      fill="url(#priceGradient)"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div>
                <h4 className="mb-2 text-sm font-medium text-muted-foreground">
                  Volume
                </h4>
                <ResponsiveContainer width="100%" height={120}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} />
                    <XAxis
                      dataKey="time"
                      tick={CHART_AXIS_TICK}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={CHART_AXIS_TICK}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={CHART_TOOLTIP_STYLE}
                      labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                      itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                    />
                    <Bar
                      dataKey="volume"
                      fill="var(--primary)"
                      opacity={0.7}
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

const FEEDBACK_ACTIONS: { label: string; value: SignalFeedbackLabel }[] = [
  { label: "Util", value: "useful" },
  { label: "Atrasada", value: "late" },
  { label: "Sem liquidez", value: "illiquid" },
  { label: "Boa margem", value: "good_margin" },
  { label: "Falso positivo", value: "false_positive" },
  { label: "Risco de prender", value: "trapped_risk" },
];

function DetailCard({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="rounded-xl bg-muted/50 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={cn("mt-0.5 text-sm font-semibold", valueClass)}>{value}</p>
    </div>
  );
}
