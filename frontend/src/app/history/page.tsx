"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { InlineErrorState } from "@/components/inline-error-state";
import { SessionRequiredState } from "@/components/session-required-state";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getHistory, getOperationalAnalytics } from "@/lib/api";
import { useHasAuthenticatedWorkspace } from "@/hooks/use-has-authenticated-workspace";
import type { Analytics, HistoryRecord } from "@/lib/types";
import { cn } from "@/lib/utils";

const CHART_COLORS = [
  "#22c55e",
  "#6366f1",
  "#a855f7",
  "#eab308",
  "#ef4444",
  "#3b82f6",
  "#f97316",
  "#14b8a6",
];

const HOURS_DATA = Array.from({ length: 24 }).map((_, hour) => ({
  hour: `${hour}h`,
  key: String(hour),
}));

const MOVEMENT_LABELS: Record<string, string> = {
  strong_range: "Forte",
  spike: "Spike",
  weak: "Fraco",
  trap: "Armadilha",
};

const EXCHANGE_LABELS: Record<string, string> = {
  novadax: "NovaDAX",
  mercado_bitcoin: "Mercado Bitcoin",
  binance: "Binance",
};

function parseUtcDate(value: string): Date {
  const normalized = /[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  return new Date(normalized);
}

function mapHourlyDistributionToLocalHours(distribution: Record<string, number>) {
  const localDistribution = Object.fromEntries(
    Array.from({ length: 24 }, (_, hour) => [String(hour), 0]),
  ) as Record<string, number>;

  for (const [utcHour, count] of Object.entries(distribution)) {
    const localHour = new Date(Date.UTC(2026, 0, 1, Number(utcHour), 0, 0)).getHours();
    localDistribution[String(localHour)] += Number(count ?? 0);
  }

  return localDistribution;
}

const CHART_GRID_STROKE = "var(--border)";
const CHART_AXIS_TICK = {
  fill: "var(--muted-foreground)",
  fontSize: 12,
} as const;
const CHART_TOOLTIP_STYLE = {
  backgroundColor: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: "8px",
  color: "var(--card-foreground)",
} as const;
const CHART_TOOLTIP_LABEL_STYLE = {
  color: "var(--card-foreground)",
} as const;
const CHART_TOOLTIP_ITEM_STYLE = {
  color: "var(--card-foreground)",
} as const;
const CHART_TOOLTIP_CURSOR = {
  fill: "rgba(148, 163, 184, 0.08)",
} as const;

function scoreColor(score: number): string {
  if (score >= 70) return "bg-emerald-500/15 text-emerald-500 border-emerald-500/20";
  if (score >= 40) return "bg-yellow-500/15 text-yellow-500 border-yellow-500/20";
  return "bg-red-500/15 text-red-500 border-red-500/20";
}

function HistoryContent() {
  const [records, setRecords] = useState<HistoryRecord[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hours, setHours] = useState<string>("24");
  const [page, setPage] = useState(0);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [hist, anal] = await Promise.all([
        getHistory({ hours: parseInt(hours, 10), limit: 100, offset: page * 100 }),
        getOperationalAnalytics({ hours: parseInt(hours, 10) }),
      ]);
      setRecords(hist);
      setAnalytics(anal);
      setError(null);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Falha ao carregar histórico e analytics.");
    } finally {
      setLoading(false);
    }
  }, [hours, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const scoreDistData = analytics
    ? Object.entries(analytics.score_distribution).map(([range, count]) => ({ range, count }))
    : [];
  const topPairsData = analytics?.top_pairs.slice(0, 8) || [];
  const movementData = analytics
    ? Object.entries(analytics.movement_distribution).map(([movement, count]) => ({
        movement,
        count,
      }))
    : [];
  const localHourlyDistribution = analytics
    ? mapHourlyDistributionToLocalHours(analytics.hourly_distribution)
    : null;
  const hourlyData = analytics
    ? HOURS_DATA.map((item) => ({
        hour: item.hour,
        count: Number(localHourlyDistribution?.[item.key] ?? 0),
      }))
    : [];

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 pt-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Histórico & Analytics</h1>
          <p className="text-sm text-muted-foreground">
            {analytics?.total_records ?? 0} sinais registrados
          </p>
        </div>
        <Select value={hours} onValueChange={(value) => setHours(value ?? "24")}>
          <SelectTrigger className="h-9 w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1">Última hora</SelectItem>
            <SelectItem value="6">Últimas 6h</SelectItem>
            <SelectItem value="24">Últimas 24h</SelectItem>
            <SelectItem value="72">Últimos 3 dias</SelectItem>
            <SelectItem value="168">Última semana</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {error ? <InlineErrorState message={error} onRetry={() => void fetchData()} /> : null}

      {analytics ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="rounded-2xl">
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">Arbitragem</p>
              <p className="mt-1 text-2xl font-bold text-blue-500">{analytics.arbitrage_count}</p>
              <p className="text-xs text-muted-foreground">Registros com gap aproveitável</p>
            </CardContent>
          </Card>
          <Card className="rounded-2xl">
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">Gap médio</p>
              <p className="mt-1 text-2xl font-bold">
                {analytics.avg_cross_exchange_gap_pct.toFixed(2)}%
              </p>
              <p className="text-xs text-muted-foreground">Diferença média entre exchanges</p>
            </CardContent>
          </Card>
          <Card className="rounded-2xl">
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">Perfil ativo</p>
              <p className="mt-1 text-lg font-bold">
                {Object.keys(analytics.profile_distribution ?? {})[0]?.replace("_", " ") ?? "workspace"}
              </p>
              <p className="text-xs text-muted-foreground">Agregados recalculados para o workspace atual</p>
            </CardContent>
          </Card>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="rounded-2xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Distribuição de Scores</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={scoreDistData}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} />
                <XAxis dataKey="range" tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
                <YAxis tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={CHART_TOOLTIP_CURSOR}
                  contentStyle={CHART_TOOLTIP_STYLE}
                  labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                  itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                  formatter={(value) => [value, "Quantidade"]}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {scoreDistData.map((_, index) => (
                    <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="rounded-2xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Top Pares por Oportunidades</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={topPairsData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} />
                <XAxis type="number" tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
                <YAxis
                  type="category"
                  dataKey="pair"
                  width={80}
                  tick={CHART_AXIS_TICK}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  cursor={CHART_TOOLTIP_CURSOR}
                  contentStyle={CHART_TOOLTIP_STYLE}
                  labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                  itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                  formatter={(value) => [value, "Quantidade"]}
                />
                <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                  {topPairsData.map((_, index) => (
                    <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="rounded-2xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Movimentos por Tipo</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={movementData}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} />
                <XAxis
                  dataKey="movement"
                  tick={CHART_AXIS_TICK}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(value: string) => MOVEMENT_LABELS[value] ?? value}
                />
                <YAxis tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={CHART_TOOLTIP_CURSOR}
                  contentStyle={CHART_TOOLTIP_STYLE}
                  labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                  itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                  formatter={(value, _name, item) => [value, MOVEMENT_LABELS[item?.payload?.movement] ?? "Movimento"]}
                  labelFormatter={(label) => MOVEMENT_LABELS[String(label)] ?? String(label)}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {movementData.map((_, index) => (
                    <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="rounded-2xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Distribuicao por Hora</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} />
                <XAxis dataKey="hour" tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
                <YAxis tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={CHART_TOOLTIP_CURSOR}
                  contentStyle={CHART_TOOLTIP_STYLE}
                  labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                  itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                  formatter={(value) => [value, "Quantidade"]}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {analytics && analytics.avg_score_by_exchange.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {analytics.avg_score_by_exchange.map((item) => (
            <Card key={item.exchange} className="rounded-2xl">
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground capitalize">
                  {item.exchange.replace("_", " ")}
                </p>
                <p className="mt-1 text-2xl font-bold">{item.avg_score}</p>
                <p className="text-xs text-muted-foreground">Score médio</p>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      <Card className="rounded-2xl">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Registros</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[400px]">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Data/Hora</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Par</TableHead>
                  <TableHead>Exchange</TableHead>
                  <TableHead>Preço</TableHead>
                  <TableHead>Variação</TableHead>
                  <TableHead>Movimento</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={i}>
                      {Array.from({ length: 7 }).map((_, j) => (
                        <TableCell key={j}>
                          <div className="h-4 w-full animate-pulse rounded bg-muted" />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : records.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="h-32 text-center text-muted-foreground">
                      Nenhum registro encontrado
                    </TableCell>
                  </TableRow>
                ) : (
                  records.map((record) => (
                    <TableRow key={record.id}>
                      <TableCell className="text-xs text-muted-foreground">
                        {parseUtcDate(record.detected_at).toLocaleString("pt-BR")}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={cn("font-bold tabular-nums", scoreColor(record.score))}
                        >
                          {record.score}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{record.pair}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {EXCHANGE_LABELS[record.exchange] ?? record.exchange}
                      </TableCell>
                      <TableCell className="tabular-nums">
                        R$ {record.last_price.toLocaleString("pt-BR")}
                      </TableCell>
                      <TableCell>
                        <span
                          className={cn(
                            "tabular-nums font-medium",
                            record.change_pct >= 0 ? "text-emerald-500" : "text-red-500"
                          )}
                        >
                          {record.change_pct >= 0 ? "+" : ""}
                          {record.change_pct.toFixed(2)}%
                        </span>
                      </TableCell>
                      <TableCell className="text-xs font-medium">
                        {MOVEMENT_LABELS[record.movement_type] ?? record.movement_type}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </ScrollArea>
          <div className="flex items-center justify-end gap-2 border-t p-3">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0}
              onClick={() => setPage((currentPage) => Math.max(0, currentPage - 1))}
            >
              Anterior
            </Button>
            <span className="text-sm text-muted-foreground">Página {page + 1}</span>
            <Button
              variant="outline"
              size="sm"
              disabled={records.length < 100}
              onClick={() => setPage((currentPage) => currentPage + 1)}
            >
              Proxima
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


export default function HistoryPage() {
  const hasAuthenticatedWorkspace = useHasAuthenticatedWorkspace();

  if (!hasAuthenticatedWorkspace) {
    return (
      <SessionRequiredState
        title="Historico restrito ao workspace autenticado"
        description="Os registros e analytics agora exigem sessao autenticada e workspace ativo para evitar leitura cruzada entre tenants."
      />
    );
  }

  return <HistoryContent />;
}
