"use client";

import { useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  ClipboardList,
  Info,
  Loader2,
  Search,
  Send,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getFunnelQualityDiagnostic, getMissedSignalDiagnostic, getNearMissesDiagnostic } from "@/lib/api";
import {
  ALL_EXCHANGES,
  formatCatalogStatus,
  formatEventDetails,
  formatExchangeDisplay,
  formatMissedSignalFinalState,
  formatPipelineReason,
  formatPipelineStage,
  formatPipelineStatus,
  formatReasonCounts,
  normalizePairInput,
type MissedSignalWindow,
} from "@/lib/diagnostics";
import type { Exchange, FunnelQualityDiagnostic, MissedSignalDiagnostic, NearMissesDiagnostic } from "@/lib/types";
import { cn } from "@/lib/utils";

type DiagnosticMode = "global" | "pair";
type ExchangeFilter = Exchange | "all";

function toDatetimeLocal(date: Date): string {
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

function diagnosticTone(finalState?: string): "good" | "warning" | "danger" {
  if (finalState === "alerted") return "good";
  if (finalState === "provider_error" || finalState === "not_monitorable") return "danger";
  return "warning";
}

function operationalConclusion(diagnostic: MissedSignalDiagnostic): string {
  const reason = diagnostic.root_cause_reason
    ? ` Motivo principal: ${formatPipelineReason(diagnostic.root_cause_reason)}.`
    : "";
  const finalState = formatMissedSignalFinalState(diagnostic.final_state);
  return `${finalState}${reason}`;
}

function nextAction(diagnostic: MissedSignalDiagnostic): string {
  if (diagnostic.final_state === "alerted") {
    return "O sistema alertou no periodo. Se o Telegram nao chegou, verifique destino, bot e bloqueios do aplicativo.";
  }
  if (diagnostic.final_state === "not_monitorable") {
    return "Corrija catalogo, status negociavel ou habilitacao da exchange antes de esperar alertas.";
  }
  if (diagnostic.final_state === "provider_error") {
    return "Prioridade: estabilizar provider, endpoint ou regiao do worker para voltar a coletar dados confiaveis.";
  }
  if (diagnostic.root_cause_reason?.includes("without_trigger") || diagnostic.root_cause_reason === "no_actionable_operation") {
    return "O sistema viu o ativo, mas nao encontrou gatilho acionavel. Ele deve ficar em observacao, nao em alerta.";
  }
  if (diagnostic.root_cause_reason?.includes("liquidity") || diagnostic.root_cause_reason?.includes("volume")) {
    return "O ativo falhou em volume/liquidez. Isso protege contra moeda que mexe mas prende na saida.";
  }
  if (diagnostic.final_state === "insufficient_audit_data") {
    return "Nao ha trilha suficiente no periodo. Tente uma janela maior ou confirme se o worker estava ativo.";
  }
  return "Use a timeline para identificar a primeira etapa em que o sinal saiu do funil.";
}

function formatPct(value?: number): string {
  if (value === undefined || value === null) return "-";
  return `${Math.round(value * 100)}%`;
}

function summarizeFunnelBottleneck(funnel: FunnelQualityDiagnostic | null): string {
  if (!funnel) return "Execute uma busca para ver os gargalos do periodo.";
  const topAlertBlock = funnel.top_alert_block_reasons[0];
  const topDiscard = funnel.top_discard_reasons[0];
  if (topAlertBlock) {
    return `Principal bloqueio de alerta: ${formatPipelineReason(topAlertBlock.reason)} (${topAlertBlock.count}).`;
  }
  if (topDiscard) {
    return `Principal descarte do scanner: ${formatPipelineReason(topDiscard.reason)} (${topDiscard.count}).`;
  }
  if (funnel.cycle_totals.provider_errors > 0) {
    return `Foram registrados ${funnel.cycle_totals.provider_errors} erros de provider no periodo.`;
  }
  if (!funnel.cycle_totals.cycles) {
    return "Nenhum ciclo auditavel encontrado no periodo.";
  }
  return "Nao ha gargalo dominante registrado no periodo.";
}

function ReasonList({
  title,
  reasons,
}: {
  title: string;
  reasons: { reason: string; count: number }[];
}) {
  return (
    <div className="rounded-xl border bg-muted/20 p-4">
      <p className="text-sm font-semibold">{title}</p>
      {reasons.length > 0 ? (
        <div className="mt-3 space-y-2">
          {reasons.slice(0, 5).map((item) => (
            <div key={item.reason} className="flex items-start justify-between gap-3 text-xs">
              <span className="text-muted-foreground">{formatPipelineReason(item.reason)}</span>
              <Badge variant="outline">{item.count}</Badge>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-xs text-muted-foreground">Sem ocorrencias relevantes.</p>
      )}
    </div>
  );
}

export default function DiagnosticsPage() {
  const [mode, setMode] = useState<DiagnosticMode>("global");
  const [exchange, setExchange] = useState<ExchangeFilter>("all");
  const [pairInput, setPairInput] = useState("SOL_BRL");
  const [windowHours, setWindowHours] = useState<MissedSignalWindow>("24");
  const [customFrom, setCustomFrom] = useState(() => toDatetimeLocal(new Date(Date.now() - 24 * 60 * 60 * 1000)));
  const [customTo, setCustomTo] = useState(() => toDatetimeLocal(new Date()));
  const [diagnostic, setDiagnostic] = useState<MissedSignalDiagnostic | null>(null);
  const [funnelQuality, setFunnelQuality] = useState<FunnelQualityDiagnostic | null>(null);
  const [nearMisses, setNearMisses] = useState<NearMissesDiagnostic | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function investigate() {
    const selectedExchange = exchange === "all" ? undefined : exchange;
    const pair = normalizePairInput(pairInput);
    if (mode === "pair") {
      if (!selectedExchange) {
        setError("Escolha uma exchange especifica para investigar um par.");
        return;
      }
      if (!pair || !pair.includes("_")) {
        setError("Informe um par no formato BASE_BRL, por exemplo SOL_BRL ou WBTC_BRL.");
        return;
      }
    }

    setLoading(true);
    setError(null);
    try {
      const now = new Date();
      const from =
        windowHours === "custom"
          ? new Date(customFrom)
          : new Date(now.getTime() - Number(windowHours) * 60 * 60 * 1000);
      const to = windowHours === "custom" ? new Date(customTo) : now;
      const fromIso = from.toISOString();
      const toIso = to.toISOString();
      const [signalResponse, funnelResponse, nearMissesResponse] = await Promise.all([
        mode === "pair" && selectedExchange
          ? getMissedSignalDiagnostic({
              exchange: selectedExchange,
              pair,
              from: fromIso,
              to: toIso,
            })
          : Promise.resolve(null),
        getFunnelQualityDiagnostic({
          exchange: selectedExchange,
          pair: mode === "pair" ? pair : undefined,
          from: fromIso,
          to: toIso,
        }),
        getNearMissesDiagnostic({
          exchange: selectedExchange,
          pair: mode === "pair" ? pair : undefined,
          from: fromIso,
          to: toIso,
          limit: mode === "global" ? 50 : 25,
        }),
      ]);
      setDiagnostic(signalResponse);
      setFunnelQuality(funnelResponse);
      setNearMisses(nearMissesResponse);
      if (mode === "pair") setPairInput(pair);
    } catch (requestError) {
      setDiagnostic(null);
      setFunnelQuality(null);
      setNearMisses(null);
      setError(requestError instanceof Error ? requestError.message : "Falha ao investigar sinal perdido.");
    } finally {
      setLoading(false);
    }
  }

  const tone = diagnosticTone(diagnostic?.final_state);
  const isPairMode = mode === "pair";

  return (
    <main className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6">
      <section className="overflow-hidden rounded-3xl border bg-[radial-gradient(circle_at_top_right,rgba(59,130,246,0.18),transparent_30%),linear-gradient(135deg,rgba(15,23,42,0.05),transparent)] p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl space-y-3">
            <Badge variant="outline" className="w-fit gap-1">
              <Search className="h-3.5 w-3.5" />
              Por que nao alertou?
            </Badge>
            <div>
              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Diagnostico operacional de sinal perdido
              </h1>
              <p className="mt-3 text-sm leading-6 text-muted-foreground sm:text-base">
                Use esta tela quando um ativo mexeu e o sistema nao avisou. Ela mostra se o par foi monitorado,
                coletado, descartado, bloqueado, ranqueado ou enviado para o Telegram.
              </p>
            </div>
          </div>
          <div className="rounded-2xl border bg-background/70 p-4 text-sm text-muted-foreground">
            Regra central: se nao existe operacao explicavel com entrada, saida, tamanho, risco e motivo,
            o sistema deve bloquear o alerta.
          </div>
        </div>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>{isPairMode ? "Investigar par e periodo" : "Investigar funil do periodo"}</CardTitle>
          <CardDescription>
            A busca consulta a auditoria compacta. Use a visao geral para achar gargalos do workspace ou o modo por par para explicar um sinal perdido especifico.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant={mode === "global" ? "default" : "outline"}
              onClick={() => {
                setMode("global");
                setDiagnostic(null);
                setError(null);
              }}
            >
              Visao geral
            </Button>
            <Button
              type="button"
              variant={mode === "pair" ? "default" : "outline"}
              onClick={() => {
                setMode("pair");
                if (exchange === "all") setExchange("novadax");
                setError(null);
              }}
            >
              Par especifico
            </Button>
          </div>

          <div
            className={cn(
              "grid gap-3 lg:items-end",
              isPairMode
                ? "lg:grid-cols-[190px,minmax(0,1fr),170px,auto]"
                : "lg:grid-cols-[190px,170px,auto]",
            )}
          >
            <label className="space-y-1">
              <span className="text-xs font-medium text-muted-foreground">Exchange</span>
              <select
                value={exchange}
                onChange={(event) => setExchange(event.target.value as ExchangeFilter)}
                className="h-9 w-full rounded-lg border bg-background px-3 text-sm"
              >
                {!isPairMode ? <option value="all">Todas</option> : null}
                {ALL_EXCHANGES.map(({ id, label }) => (
                  <option key={id} value={id}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            {isPairMode ? (
              <label className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground">Par</span>
                <Input
                  value={pairInput}
                  onChange={(event) => {
                    setPairInput(event.target.value);
                    setError(null);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      void investigate();
                    }
                  }}
                  placeholder="Ex: SOL_BRL, WBTC_BRL, USDT_BRL"
                />
              </label>
            ) : null}
            <label className="space-y-1">
              <span className="text-xs font-medium text-muted-foreground">Janela</span>
              <select
                value={windowHours}
                onChange={(event) => setWindowHours(event.target.value as MissedSignalWindow)}
                className="h-9 w-full rounded-lg border bg-background px-3 text-sm"
              >
                <option value="1">Ultima 1h</option>
                <option value="4">Ultimas 4h</option>
                <option value="24">Ultimas 24h</option>
                <option value="72">Ultimos 3 dias</option>
                <option value="custom">Periodo customizado</option>
              </select>
            </label>
            <Button type="button" onClick={() => void investigate()} disabled={loading} className="gap-2">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Investigar
            </Button>
          </div>

          {windowHours === "custom" ? (
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground">Inicio</span>
                <Input type="datetime-local" value={customFrom} onChange={(event) => setCustomFrom(event.target.value)} />
              </label>
              <label className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground">Fim</span>
                <Input type="datetime-local" value={customTo} onChange={(event) => setCustomTo(event.target.value)} />
              </label>
            </div>
          ) : null}

          {error ? (
            <div className="rounded-xl border border-amber-500/25 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-200">
              {error}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {funnelQuality ? (
        <section className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                Qualidade do funil
              </CardTitle>
              <CardDescription>
                Mostra onde o scanner perdeu mais sinais no periodo filtrado.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-xl border bg-muted/20 p-4 text-sm">
                <p className="font-semibold">Gargalo principal</p>
                <p className="mt-2 text-muted-foreground">{summarizeFunnelBottleneck(funnelQuality)}</p>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-xl border p-3">
                  <p className="text-xs text-muted-foreground">Ciclos</p>
                  <p className="mt-1 text-xl font-semibold">{funnelQuality.cycle_totals.cycles}</p>
                </div>
                <div className="rounded-xl border p-3">
                  <p className="text-xs text-muted-foreground">Pares BRL vistos</p>
                  <p className="mt-1 text-xl font-semibold">{funnelQuality.cycle_totals.brl_pairs}</p>
                </div>
                <div className="rounded-xl border p-3">
                  <p className="text-xs text-muted-foreground">Candidatos leves</p>
                  <p className="mt-1 text-xl font-semibold">{funnelQuality.cycle_totals.light_candidates}</p>
                </div>
                <div className="rounded-xl border p-3">
                  <p className="text-xs text-muted-foreground">Alertas enviados</p>
                  <p className="mt-1 text-xl font-semibold">{funnelQuality.cycle_totals.alerts_sent}</p>
                </div>
              </div>
              <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
                <p>Promocao leve: {formatPct(funnelQuality.rates.light_candidate_rate)}</p>
                <p>Deep scan: {formatPct(funnelQuality.rates.deep_promotion_rate)}</p>
                <p>Criacao de sinal: {formatPct(funnelQuality.rates.signal_creation_rate)}</p>
                <p>Envio de alerta: {formatPct(funnelQuality.rates.alert_send_rate)}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Motivos mais frequentes</CardTitle>
              <CardDescription>
                Ajuda a separar problema de provider, filtro, ranking, workspace ou Telegram.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <ReasonList title="Descartes do scanner" reasons={funnelQuality.top_discard_reasons} />
              <ReasonList title="Bloqueios de alerta" reasons={funnelQuality.top_alert_block_reasons} />
              <ReasonList title="Bloqueios do workspace" reasons={funnelQuality.top_workspace_block_reasons} />
              <ReasonList title="Eventos tecnicos" reasons={funnelQuality.top_event_reasons} />
            </CardContent>
          </Card>
        </section>
      ) : null}

      {nearMisses && nearMisses.near_misses.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Near misses</CardTitle>
            <CardDescription>
              Candidatos que quase passaram, mas perderam prioridade ou falharam em algum criterio.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-hidden rounded-xl border">
              <ScrollArea className="max-h-72">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Horario</TableHead>
                      <TableHead>Par</TableHead>
                      <TableHead>Etapa</TableHead>
                      <TableHead>Motivo</TableHead>
                      <TableHead>Detalhes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {nearMisses.near_misses.map((nearMiss, index) => (
                      <TableRow key={`${nearMiss.cycle_id}-${nearMiss.pair}-${index}`}>
                        <TableCell className="whitespace-nowrap text-xs">
                          {nearMiss.created_at ? new Date(nearMiss.created_at).toLocaleString("pt-BR") : "-"}
                        </TableCell>
                        <TableCell className="text-xs font-medium">
                          {formatExchangeDisplay(nearMiss.exchange)} · {nearMiss.pair.replace("_", "/")}
                        </TableCell>
                        <TableCell className="text-xs">{formatPipelineStage(nearMiss.stage)}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{formatPipelineReason(nearMiss.reason)}</TableCell>
                        <TableCell className="max-w-[20rem] truncate text-xs text-muted-foreground">
                          {formatEventDetails(nearMiss.details)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {diagnostic ? (
        <>
          <Card
            className={cn(
              tone === "good" && "border-emerald-500/30 bg-emerald-500/5",
              tone === "warning" && "border-amber-500/30 bg-amber-500/5",
              tone === "danger" && "border-destructive/30 bg-destructive/5",
            )}
          >
            <CardHeader>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    {tone === "good" ? <ShieldCheck className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
                    {diagnostic.pair.replace("_", "/")} em {formatExchangeDisplay(diagnostic.exchange)}
                  </CardTitle>
                  <CardDescription className="mt-2">{diagnostic.message}</CardDescription>
                </div>
                <Badge variant={diagnostic.status === "events_found" ? "default" : "outline"}>
                  {diagnostic.status === "events_found" ? "trilha encontrada" : "sem trilha suficiente"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="grid gap-3 lg:grid-cols-[1fr_1fr]">
              <div className="rounded-xl border bg-background/70 p-4">
                <p className="text-sm font-semibold">Conclusao operacional</p>
                <p className="mt-2 text-sm text-muted-foreground">{operationalConclusion(diagnostic)}</p>
              </div>
              <div className="rounded-xl border bg-background/70 p-4">
                <p className="text-sm font-semibold">Proximo passo recomendado</p>
                <p className="mt-2 text-sm text-muted-foreground">{nextAction(diagnostic)}</p>
              </div>
            </CardContent>
          </Card>

          <section className="grid gap-4 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ClipboardList className="h-4 w-4" />
                  Workspace
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-muted-foreground">
                {diagnostic.workspace_status ? (
                  <>
                    <p>Exchange: {diagnostic.workspace_status.exchange_enabled ? "habilitada" : "bloqueada"}</p>
                    <p>
                      Par:{" "}
                      {diagnostic.workspace_status.pair_selected
                        ? "na watchlist"
                        : "fora da watchlist, mas elegivel pelo catalogo"}
                    </p>
                    <p>Telegram: {diagnostic.workspace_status.telegram_enabled ? "ativo" : "desativado"}</p>
                    <p>Destino Telegram: {diagnostic.workspace_status.telegram_destination_configured ? "configurado" : "pendente"}</p>
                    <p>Ultimo alerta: {formatPipelineReason(diagnostic.workspace_status.latest_alert_reason)}</p>
                  </>
                ) : (
                  <p>Sem contexto de workspace.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Info className="h-4 w-4" />
                  Catalogo
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-muted-foreground">
                {diagnostic.catalog_status ? (
                  <>
                    <p>Status: {formatCatalogStatus(diagnostic.catalog_status.overall_status)}</p>
                    <p>Monitoravel: {diagnostic.catalog_status.monitorable === false ? "nao" : "sim/indeterminado"}</p>
                    <p>Existe no catalogo: {diagnostic.catalog_status.exists_in_catalog === false ? "nao" : "sim/indeterminado"}</p>
                    <p>Motivo: {formatPipelineReason(diagnostic.catalog_status.monitorability_reason)}</p>
                    {diagnostic.catalog_status.error ? <p>Erro: {diagnostic.catalog_status.error}</p> : null}
                  </>
                ) : (
                  <p>Catalogo nao consultado.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Send className="h-4 w-4" />
                  Alerta
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-muted-foreground">
                <p>Estado final: {formatMissedSignalFinalState(diagnostic.final_state)}</p>
                <p>Etapa raiz: {diagnostic.root_cause_stage ? formatPipelineStage(diagnostic.root_cause_stage) : "-"}</p>
                <p>Motivo raiz: {formatPipelineReason(diagnostic.root_cause_reason)}</p>
                <p>Eventos na timeline: {diagnostic.timeline.length}</p>
              </CardContent>
            </Card>
          </section>

          {diagnostic.cycle_summaries.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Ciclos do scanner no periodo</CardTitle>
                <CardDescription>
                  Resumo compacto dos ciclos que ajudam a explicar se houve coleta, candidatos, sinais e alertas.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-2">
                {diagnostic.cycle_summaries.slice(0, 6).map((cycle) => (
                  <div key={cycle.cycle_id} className="rounded-xl border bg-muted/20 p-4 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-semibold">{cycle.cycle_id}</p>
                      <Badge variant={cycle.status === "completed" ? "default" : "outline"}>{cycle.status}</Badge>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                      <span>Pares BRL: {cycle.brl_pairs}</span>
                      <span>Candidatos: {cycle.light_candidates}</span>
                      <span>Deep scan: {cycle.deep_completed}/{cycle.deep_candidates}</span>
                      <span>Alertas: {cycle.alerts_sent}/{cycle.alerts_created}</span>
                    </div>
                    {Object.keys(cycle.discard_reasons).length > 0 ? (
                      <p className="mt-3 text-xs text-muted-foreground">
                        Descartes: {formatReasonCounts(cycle.discard_reasons)}
                      </p>
                    ) : null}
                    {Object.keys(cycle.block_reasons).length > 0 ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Bloqueios: {formatReasonCounts(cycle.block_reasons)}
                      </p>
                    ) : null}
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>Timeline do funil</CardTitle>
              <CardDescription>
                A primeira linha com descarte, bloqueio ou erro geralmente mostra onde o sinal se perdeu.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {diagnostic.timeline.length > 0 ? (
                <div className="overflow-hidden rounded-xl border">
                  <ScrollArea className="max-h-[440px]">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Horario</TableHead>
                          <TableHead>Etapa</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Motivo</TableHead>
                          <TableHead>Detalhes</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {diagnostic.timeline.map((event, index) => (
                          <TableRow key={`${event.cycle_id}-${event.stage}-${index}`}>
                            <TableCell className="whitespace-nowrap text-xs">
                              {event.created_at ? new Date(event.created_at).toLocaleString("pt-BR") : "-"}
                            </TableCell>
                            <TableCell className="text-xs font-medium">{formatPipelineStage(event.stage)}</TableCell>
                            <TableCell>
                              <Badge variant={event.status === "error" || event.status === "blocked" ? "outline" : "default"}>
                                {formatPipelineStatus(event.status)}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-xs text-muted-foreground">
                              {formatPipelineReason(event.reason)}
                            </TableCell>
                            <TableCell className="max-w-[22rem] truncate text-xs text-muted-foreground">
                              {formatEventDetails(event.details)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Nenhum evento encontrado para o par no periodo informado.</p>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </main>
  );
}
