"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
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
import type { Opportunity } from "@/lib/types";
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
  opportunity: opp,
  open,
  onClose,
}: SignalDetailModalProps) {
  if (!opp) return null;

  const chartData = (opp.klines || []).map((k) => ({
    time: new Date(k.open_time).toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
    }),
    price: k.close,
    volume: k.volume,
    high: k.high,
    low: k.low,
  }));

  return (
    <Dialog open={open} onOpenChange={() => onClose()}>
      <DialogContent className="max-w-2xl rounded-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <span className="text-xl font-bold">{opp.pair}</span>
            <Badge
              variant="outline"
              className={cn("text-sm font-bold", scoreColor(opp.score))}
            >
              Score {opp.score}
            </Badge>
            <span className="text-sm text-muted-foreground">
              {exchangeLabel(opp.exchange)}
            </span>
          </DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <DetailCard label="Preço" value={`R$ ${opp.last_price.toLocaleString("pt-BR")}`} />
          <DetailCard
            label="Variação"
            value={`${opp.change_pct >= 0 ? "+" : ""}${opp.change_pct.toFixed(2)}%`}
            valueClass={opp.change_pct >= 0 ? "text-emerald-500" : "text-red-500"}
          />
          <DetailCard label="Volatilidade" value={`${opp.volatility_pct.toFixed(2)}%`} />
          <DetailCard label="Spread" value={`${opp.spread_pct.toFixed(4)}%`} />
          <DetailCard label="Volume 24h" value={`R$ ${(opp.quote_volume_24h / 1000).toFixed(0)}K`} />
          <DetailCard label="Liquidez" value={`${opp.liquidity_units.toLocaleString("pt-BR")} un.`} />
          <DetailCard
            label="Gap Cross"
            value={`${opp.cross_exchange_gap_pct.toFixed(2)}%`}
            valueClass={opp.arbitrage_available ? "text-blue-500" : undefined}
          />
          <DetailCard
            label="Movimento"
            value={opp.movement_type.replace("_", " ")}
          />
          <DetailCard
            label="Detectado"
            value={new Date(opp.detected_at).toLocaleTimeString("pt-BR")}
          />
        </div>

        {opp.cross_exchange_reference_exchange || opp.cross_exchange_reference_price ? (
          <>
            <Separator className="my-2" />
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <DetailCard
                label="Exchange referência"
                value={opp.cross_exchange_reference_exchange ?? "-"}
              />
              <DetailCard
                label="Preço referência"
                value={
                  opp.cross_exchange_reference_price
                    ? `R$ ${opp.cross_exchange_reference_price.toLocaleString("pt-BR")}`
                    : "-"
                }
              />
              <DetailCard
                label="Confiança histórica"
                value={`${(opp.historical_confidence * 100).toFixed(1)}%`}
              />
            </div>
          </>
        ) : null}

        <Separator className="my-2" />

        {chartData.length > 0 && (
          <div className="space-y-4">
            <div>
              <h4 className="mb-2 text-sm font-medium text-muted-foreground">
                Preço Recente
              </h4>
              <ResponsiveContainer width="100%" height={200}>
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
                    tickFormatter={(v: number) => v.toLocaleString("pt-BR")}
                  />
                  <Tooltip
                    contentStyle={CHART_TOOLTIP_STYLE}
                    labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                    itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                    formatter={(value) => [
                      `R$ ${Number(value).toLocaleString("pt-BR")}`,
                      "Preço",
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
        )}
      </DialogContent>
    </Dialog>
  );
}

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
