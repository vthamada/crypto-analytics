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
import { Input } from "@/components/ui/input";
import { InlineErrorState } from "@/components/inline-error-state";
import { SessionRequiredState } from "@/components/session-required-state";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getHistorySummary, getOperationalAnalytics, getOutcomeBucketAnalytics, getWorkspaceStatus } from "@/lib/api";
import { useHasAuthenticatedWorkspace } from "@/hooks/use-has-authenticated-workspace";
import type {
  Analytics,
  HistorySummaryRecord,
  HistoryVisibility,
  OutcomeBucketAnalytics,
  OutcomeBucketRow,
  WorkspaceStatus,
} from "@/lib/types";
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

const PIPELINE_STATUS_LABELS: Record<string, string> = {
  alerted_opportunity: "alertado",
  blocked_signal: "bloqueado",
  candidate: "candidato",
  discarded_observation: "descartado",
  evaluated_signal: "avaliado",
  operational_opportunity: "oportunidade",
  published_opportunity: "publicado",
  technical_audit_event: "auditoria",
};

const PHASE_LABELS: Record<string, string> = {
  accumulation: "acumulacao",
  continuation: "continuacao",
  distribution_or_profit_zone: "realizacao",
  early_breakout: "rompimento inicial",
  exhaustion: "exaustao",
  extended: "esticado",
  neutral: "neutro",
};

const OPPORTUNITY_TYPE_LABELS: Record<string, string> = {
  avoid: "evitar",
  hold: "hold",
  observe: "observar",
  trade: "trade",
};

const OUTCOME_LABELS: Record<string, string> = {
  excellent: "excelente",
  good: "bom",
  late: "atrasado",
  neutral: "neutro",
  false_positive: "falso positivo",
  pending: "pendente",
};

const FEEDBACK_LABELS: Record<string, string> = {
  useful: "util",
  weak: "fraco",
  late: "atrasado",
  no_liquidity: "sem liquidez",
  good_for_trade: "bom para trade",
  good_for_hold: "bom para hold",
  ignore: "ignorar",
  false_positive: "falso positivo",
  good_margin: "boa margem",
  insufficient_margin: "margem insuficiente",
  trapped_risk: "risco de prisao",
};

const BLOCK_REASON_LABELS: Record<string, string> = {
  accumulation_only: "acumulacao sem gatilho",
  below_alert_threshold: "abaixo do alerta",
  high_operational_risk: "risco alto",
  incomplete_operational_thesis: "tese incompleta",
  insufficient_alert_worthiness: "sem urgencia",
  insufficient_exit_liquidity: "saida insuficiente",
  no_actionable_operation: "sem acao",
  preparation_without_trigger: "preparacao sem gatilho",
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

function formatKnownLabel(value: string | null | undefined, labels: Record<string, string>, fallback = "-"): string {
  if (!value) return fallback;
  return labels[value] ?? value.replace(/_/g, " ");
}

function formatOutcomePct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function formatOutcomeBucketName(group: string, value: string): string {
  if (group === "exchange") return EXCHANGE_LABELS[value] ?? value.replace(/_/g, " ");
  if (group === "opportunity_type") return formatKnownLabel(value, OPPORTUNITY_TYPE_LABELS);
  if (group === "movement_phase") return formatKnownLabel(value, PHASE_LABELS);
  if (group === "alert_moment_type") return value.replace(/_/g, " ");
  return value.replace(/_/g, " ");
}

function HistoryContent() {
  const [records, setRecords] = useState<HistorySummaryRecord[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [outcomeAnalytics, setOutcomeAnalytics] = useState<OutcomeBucketAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsLoaded, setAnalyticsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hours, setHours] = useState<string>("24");
  const [visibility, setVisibility] = useState<HistoryVisibility>("operational");
  const [exchangeFilter, setExchangeFilter] = useState("all");
  const [pairFilter, setPairFilter] = useState("");
  const [minScoreFilter, setMinScoreFilter] = useState("0");
  const [pipelineStatusFilter, setPipelineStatusFilter] = useState("all");
  const [opportunityTypeFilter, setOpportunityTypeFilter] = useState("all");
  const [movementPhaseFilter, setMovementPhaseFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [blockReasonFilter, setBlockReasonFilter] = useState("all");
  const [outcomeFilter, setOutcomeFilter] = useState("all");
  const [feedbackFilter, setFeedbackFilter] = useState("all");
  const [page, setPage] = useState(0);
  const [workspaceStatus, setWorkspaceStatus] = useState<WorkspaceStatus | null>(null);
  const durableStorageEnabled = workspaceStatus?.durable_storage_enabled ?? true;

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const hist = await getHistorySummary({
        hours: parseInt(hours, 10),
        limit: 100,
        offset: page * 100,
        visibility,
        exchange: exchangeFilter === "all" ? undefined : exchangeFilter,
        pair: pairFilter.trim() ? pairFilter.trim().toUpperCase().replace("/", "_") : undefined,
        min_score: Number(minScoreFilter) > 0 ? Number(minScoreFilter) : undefined,
      });
      setRecords(hist);
      setError(null);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Falha ao carregar historico.");
    } finally {
      setLoading(false);
    }
  }, [exchangeFilter, hours, minScoreFilter, page, pairFilter, visibility]);

  const fetchAnalytics = useCallback(async () => {
    setAnalyticsLoading(true);
    try {
      const [anal, outcomes] = await Promise.all([
        getOperationalAnalytics({ hours: parseInt(hours, 10) }),
        getOutcomeBucketAnalytics({ hours: parseInt(hours, 10) }),
      ]);
      setAnalytics(anal);
      setOutcomeAnalytics(outcomes);
      setAnalyticsLoaded(true);
      setError(null);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Falha ao carregar analytics.");
    } finally {
      setAnalyticsLoading(false);
    }
  }, [hours, visibility]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    void getWorkspaceStatus()
      .then(setWorkspaceStatus)
      .catch(() => setWorkspaceStatus(null));
  }, []);

  useEffect(() => {
    setAnalytics(null);
    setOutcomeAnalytics(null);
    setAnalyticsLoaded(false);
  }, [hours]);

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
  const filteredRecords = records.filter((record) => {
    if (pipelineStatusFilter !== "all" && record.pipeline_status !== pipelineStatusFilter) return false;
    if (opportunityTypeFilter !== "all" && record.opportunity_type !== opportunityTypeFilter) return false;
    if (movementPhaseFilter !== "all" && record.movement_phase !== movementPhaseFilter) return false;
    if (riskFilter !== "all" && (record.risk_label ?? "sem_risco") !== riskFilter) return false;
    if (blockReasonFilter !== "all" && (record.alert_block_reason ?? record.visibility_reason ?? "sem_motivo") !== blockReasonFilter) return false;
    if (outcomeFilter !== "all" && (record.outcome_label ?? "sem_outcome") !== outcomeFilter) return false;
    if (feedbackFilter !== "all" && (record.feedback_label ?? "sem_feedback") !== feedbackFilter) return false;
    return true;
  });
  const outcomeBucketGroups: { key: keyof OutcomeBucketAnalytics["buckets"]; title: string; rows: OutcomeBucketRow[] }[] =
    outcomeAnalytics
      ? [
          { key: "exchange", title: "Por exchange", rows: outcomeAnalytics.buckets.exchange.slice(0, 5) },
          { key: "pair", title: "Por par", rows: outcomeAnalytics.buckets.pair.slice(0, 5) },
          { key: "opportunity_type", title: "Por tipo", rows: outcomeAnalytics.buckets.opportunity_type.slice(0, 5) },
          { key: "movement_phase", title: "Por fase", rows: outcomeAnalytics.buckets.movement_phase.slice(0, 5) },
          { key: "alert_moment_type", title: "Por momento", rows: outcomeAnalytics.buckets.alert_moment_type.slice(0, 5) },
        ]
      : [];

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 pt-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Histórico & Analytics</h1>
          <p className="text-sm text-muted-foreground">
            {filteredRecords.length} de {records.length} registros nesta pagina
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Select
            value={visibility}
            onValueChange={(value) => {
              setVisibility((value ?? "operational") as HistoryVisibility);
              setPage(0);
            }}
          >
            <SelectTrigger className="h-9 w-full sm:w-56">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="operational">Historico operacional</SelectItem>
              <SelectItem value="technical">Auditoria tecnica</SelectItem>
              <SelectItem value="all">Todos os registros</SelectItem>
            </SelectContent>
          </Select>
          <Select value={hours} onValueChange={(value) => setHours(value ?? "24")}>
          <SelectTrigger className="h-9 w-full sm:w-40">
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
      </div>

      <Card className="rounded-2xl border-dashed">
        <CardContent className="p-4 text-sm text-muted-foreground">
          {visibility === "operational"
            ? "Mostrando apenas oportunidades operacionais publicaveis. Descartes, bloqueios e sinais fracos ficam fora desta visao."
            : visibility === "technical"
              ? "Mostrando registros tecnicos bloqueados ou descartados para auditoria e calibragem."
              : "Mostrando oportunidades e registros tecnicos juntos. Use com cuidado para nao confundir ruido com oportunidade."}
        </CardContent>
      </Card>

      {!durableStorageEnabled ? (
        <Card className="rounded-2xl border-amber-500/30 bg-amber-500/5">
          <CardContent className="p-4 text-sm text-muted-foreground">
            <span className="font-semibold text-amber-600 dark:text-amber-300">Modo sem banco ativo.</span>{" "}
            Historico persistente, outcomes e analytics longos ficam indisponiveis. O produto principal continua no
            Dashboard com oportunidades atuais, Telegram e auditoria recente em memoria.
          </CardContent>
        </Card>
      ) : null}

      <Card className="rounded-2xl">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Filtros operacionais</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          <Select
            value={exchangeFilter}
            onValueChange={(value) => {
              setExchangeFilter(value ?? "all");
              setPage(0);
            }}
          >
            <SelectTrigger className="h-9">
              <SelectValue placeholder="Exchange" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas as exchanges</SelectItem>
              {Object.entries(EXCHANGE_LABELS).map(([id, label]) => (
                <SelectItem key={id} value={id}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Input
            value={pairFilter}
            onChange={(event) => {
              setPairFilter(event.target.value);
              setPage(0);
            }}
            placeholder="Par, ex: SOL_BRL"
            className="h-9"
          />

          <Select
            value={minScoreFilter}
            onValueChange={(value) => {
              setMinScoreFilter(value ?? "0");
              setPage(0);
            }}
          >
            <SelectTrigger className="h-9">
              <SelectValue placeholder="Score minimo" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="0">Qualquer score</SelectItem>
              <SelectItem value="40">Score 40+</SelectItem>
              <SelectItem value="55">Score 55+</SelectItem>
              <SelectItem value="70">Score 70+</SelectItem>
              <SelectItem value="85">Score 85+</SelectItem>
            </SelectContent>
          </Select>

          <Select value={pipelineStatusFilter} onValueChange={(value) => setPipelineStatusFilter(value ?? "all")}>
            <SelectTrigger className="h-9">
              <SelectValue placeholder="Estado" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os estados</SelectItem>
              {Object.entries(PIPELINE_STATUS_LABELS).map(([id, label]) => (
                <SelectItem key={id} value={id}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={opportunityTypeFilter} onValueChange={(value) => setOpportunityTypeFilter(value ?? "all")}>
            <SelectTrigger className="h-9">
              <SelectValue placeholder="Tipo" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os tipos</SelectItem>
              {Object.entries(OPPORTUNITY_TYPE_LABELS).map(([id, label]) => (
                <SelectItem key={id} value={id}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={movementPhaseFilter} onValueChange={(value) => setMovementPhaseFilter(value ?? "all")}>
            <SelectTrigger className="h-9">
              <SelectValue placeholder="Fase" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas as fases</SelectItem>
              {Object.entries(PHASE_LABELS).map(([id, label]) => (
                <SelectItem key={id} value={id}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={riskFilter} onValueChange={(value) => setRiskFilter(value ?? "all")}>
            <SelectTrigger className="h-9">
              <SelectValue placeholder="Risco" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os riscos</SelectItem>
              <SelectItem value="baixo">Risco baixo</SelectItem>
              <SelectItem value="medio">Risco medio</SelectItem>
              <SelectItem value="alto">Risco alto</SelectItem>
              <SelectItem value="sem_risco">Sem rotulo de risco</SelectItem>
            </SelectContent>
          </Select>

          <Select value={blockReasonFilter} onValueChange={(value) => setBlockReasonFilter(value ?? "all")}>
            <SelectTrigger className="h-9">
              <SelectValue placeholder="Motivo de bloqueio" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os motivos</SelectItem>
              <SelectItem value="sem_motivo">Sem motivo</SelectItem>
              {Object.entries(BLOCK_REASON_LABELS).map(([id, label]) => (
                <SelectItem key={id} value={id}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={outcomeFilter} onValueChange={(value) => setOutcomeFilter(value ?? "all")}>
            <SelectTrigger className="h-9">
              <SelectValue placeholder="Outcome" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os outcomes</SelectItem>
              <SelectItem value="sem_outcome">Sem outcome</SelectItem>
              {Object.entries(OUTCOME_LABELS).map(([id, label]) => (
                <SelectItem key={id} value={id}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={feedbackFilter} onValueChange={(value) => setFeedbackFilter(value ?? "all")}>
            <SelectTrigger className="h-9">
              <SelectValue placeholder="Feedback" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os feedbacks</SelectItem>
              <SelectItem value="sem_feedback">Sem feedback</SelectItem>
              {Object.entries(FEEDBACK_LABELS).map(([id, label]) => (
                <SelectItem key={id} value={id}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            onClick={() => {
              setExchangeFilter("all");
              setPairFilter("");
              setMinScoreFilter("0");
              setPipelineStatusFilter("all");
              setOpportunityTypeFilter("all");
              setMovementPhaseFilter("all");
              setRiskFilter("all");
              setBlockReasonFilter("all");
              setOutcomeFilter("all");
              setFeedbackFilter("all");
              setPage(0);
            }}
          >
            Limpar filtros
          </Button>
        </CardContent>
      </Card>

      {error ? <InlineErrorState message={error} onRetry={() => void fetchData()} /> : null}

      {!analyticsLoaded ? (
        <Card className="rounded-2xl border-dashed">
          <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium">Analytics operacional sob demanda</p>
              <p className="text-sm text-muted-foreground">
                Graficos e agregados pesados ficam desligados por padrao para reduzir leitura e egress do Supabase.
              </p>
            </div>
            <Button onClick={() => void fetchAnalytics()} disabled={analyticsLoading}>
              {analyticsLoading ? "Carregando..." : "Carregar analytics"}
            </Button>
          </CardContent>
        </Card>
      ) : null}

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
          <Card className="rounded-2xl">
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">Outcomes</p>
              <p className="mt-1 text-2xl font-bold text-emerald-500">{outcomeAnalytics?.total_outcomes ?? 0}</p>
              <p className="text-xs text-muted-foreground">Sinais com avaliacao posterior</p>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {outcomeAnalytics ? (
        <Card className="rounded-2xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Outcomes por bucket</CardTitle>
            <p className="text-sm text-muted-foreground">
              Mostra quais grupos de sinais estao gerando resultado depois do alerta. Use isto para calibrar ranking, bloqueios e ruido.
            </p>
          </CardHeader>
          <CardContent className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
            {outcomeBucketGroups.map((group) => (
              <div key={group.key} className="rounded-xl border p-3">
                <p className="mb-3 text-sm font-semibold">{group.title}</p>
                <div className="space-y-2">
                  {group.rows.length === 0 ? (
                    <p className="text-xs text-muted-foreground">Sem outcomes suficientes.</p>
                  ) : (
                    group.rows.map((row) => (
                      <div key={`${group.key}-${row.bucket}`} className="rounded-lg bg-muted/30 p-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-sm font-medium">
                            {formatOutcomeBucketName(group.key, row.bucket)}
                          </span>
                          <Badge variant="outline">{row.count}</Badge>
                        </div>
                        <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-muted-foreground">
                          <span>Acerto {(row.success_rate * 100).toFixed(0)}%</span>
                          <span>1h {formatOutcomePct(row.avg_return_1h_pct)}</span>
                          <span>4h {formatOutcomePct(row.avg_return_4h_pct)}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {analytics ? (
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
      ) : null}

      {analytics ? (
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
      ) : null}

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
                  <TableHead>Estado</TableHead>
                  <TableHead>Motivo</TableHead>
                  <TableHead>Resultado</TableHead>
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
                      {Array.from({ length: 10 }).map((_, j) => (
                        <TableCell key={j}>
                          <div className="h-4 w-full animate-pulse rounded bg-muted" />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : filteredRecords.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="h-32 text-center text-muted-foreground">
                      Nenhum registro encontrado
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredRecords.map((record) => (
                    <TableRow key={record.id}>
                      <TableCell className="text-xs text-muted-foreground">
                        {parseUtcDate(record.detected_at).toLocaleString("pt-BR")}
                      </TableCell>
                      <TableCell className="text-xs">
                        <Badge
                          variant="outline"
                          className={cn(
                            "capitalize",
                            record.operationally_visible
                              ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-500"
                              : "border-muted bg-muted/30 text-muted-foreground"
                          )}
                        >
                          {(record.pipeline_status ?? "evaluated_signal").replace(/_/g, " ")}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[12rem] truncate text-xs text-muted-foreground">
                        {formatKnownLabel(record.alert_block_reason ?? record.visibility_reason, BLOCK_REASON_LABELS)}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        <div>{formatKnownLabel(record.outcome_label, OUTCOME_LABELS)}</div>
                        {record.feedback_label ? (
                          <div className="text-[11px] text-primary">
                            {formatKnownLabel(record.feedback_label, FEEDBACK_LABELS)}
                          </div>
                        ) : null}
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
