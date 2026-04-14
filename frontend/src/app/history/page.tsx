"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
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
import { ScrollArea } from "@/components/ui/scroll-area";
import { getHistory, getAnalytics } from "@/lib/api";
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

function scoreColor(score: number): string {
  if (score >= 70) return "bg-emerald-500/15 text-emerald-500 border-emerald-500/20";
  if (score >= 40) return "bg-yellow-500/15 text-yellow-500 border-yellow-500/20";
  return "bg-red-500/15 text-red-500 border-red-500/20";
}

export default function HistoryPage() {
  const [records, setRecords] = useState<HistoryRecord[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [hours, setHours] = useState<string>("24");
  const [page, setPage] = useState(0);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [hist, anal] = await Promise.all([
        getHistory({ hours: parseInt(hours), limit: 100, offset: page * 100 }),
        getAnalytics(),
      ]);
      setRecords(hist);
      setAnalytics(anal);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [hours, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const scoreDistData = analytics
    ? Object.entries(analytics.score_distribution).map(([range, count]) => ({
        range,
        count,
      }))
    : [];

  const topPairsData = analytics?.top_pairs.slice(0, 8) || [];

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 pt-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Historico & Analytics
          </h1>
          <p className="text-sm text-muted-foreground">
            {analytics?.total_records ?? 0} sinais registrados
          </p>
        </div>
        <Select value={hours} onValueChange={(v) => setHours(v ?? "24")}>
          <SelectTrigger className="h-9 w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1">Ultima hora</SelectItem>
            <SelectItem value="6">Ultimas 6h</SelectItem>
            <SelectItem value="24">Ultimas 24h</SelectItem>
            <SelectItem value="72">Ultimos 3 dias</SelectItem>
            <SelectItem value="168">Ultima semana</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Analytics Charts */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="rounded-2xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Distribuicao de Scores</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={scoreDistData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="range" fontSize={12} stroke="hsl(var(--muted-foreground))" />
                <YAxis fontSize={12} stroke="hsl(var(--muted-foreground))" />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                  }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {scoreDistData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
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
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff18" />
                <XAxis type="number" fontSize={12} tick={{ fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <YAxis
                  type="category"
                  dataKey="pair"
                  fontSize={12}
                  width={80}
                  tick={{ fill: "#94a3b8" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: "#ffffff08" }}
                  contentStyle={{
                    background: "#1e293b",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    color: "#f1f5f9",
                  }}
                />
                <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                  {topPairsData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Avg Score by Exchange */}
      {analytics && analytics.avg_score_by_exchange.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {analytics.avg_score_by_exchange.map((item) => (
            <Card key={item.exchange} className="rounded-2xl">
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground capitalize">
                  {item.exchange.replace("_", " ")}
                </p>
                <p className="mt-1 text-2xl font-bold">{item.avg_score}</p>
                <p className="text-xs text-muted-foreground">Score medio</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* History Table */}
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
                  <TableHead>Preco</TableHead>
                  <TableHead>Variacao</TableHead>
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
                  records.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="text-xs text-muted-foreground">
                        {new Date(r.detected_at).toLocaleString("pt-BR")}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={cn("font-bold tabular-nums", scoreColor(r.score))}
                        >
                          {r.score}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{r.pair}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {EXCHANGE_LABELS[r.exchange] ?? r.exchange}
                      </TableCell>
                      <TableCell className="tabular-nums">
                        R$ {r.last_price.toLocaleString("pt-BR")}
                      </TableCell>
                      <TableCell>
                        <span
                          className={cn(
                            "tabular-nums font-medium",
                            r.change_pct >= 0 ? "text-emerald-500" : "text-red-500"
                          )}
                        >
                          {r.change_pct >= 0 ? "+" : ""}
                          {r.change_pct.toFixed(2)}%
                        </span>
                      </TableCell>
                      <TableCell className="text-xs font-medium">
                        {MOVEMENT_LABELS[r.movement_type] ?? r.movement_type}
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
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              Anterior
            </Button>
            <span className="text-sm text-muted-foreground">Pagina {page + 1}</span>
            <Button
              variant="outline"
              size="sm"
              disabled={records.length < 100}
              onClick={() => setPage((p) => p + 1)}
            >
              Proxima
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
