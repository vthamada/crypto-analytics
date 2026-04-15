"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  completeOnboarding,
  getAdminSession,
  getStoredAuthToken,
  getWorkspaceStatus,
} from "@/lib/api";
import type { AdminSessionInfo, WorkspaceStatus } from "@/lib/types";
import { Check, Loader2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";


export function OnboardingChecklist() {
  const [session, setSession] = useState<AdminSessionInfo | null>(null);
  const [workspaceStatus, setWorkspaceStatus] = useState<WorkspaceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [finishing, setFinishing] = useState(false);
  const [understoodScores, setUnderstoodScores] = useState(false);

  useEffect(() => {
    const token = getStoredAuthToken();
    if (!token) {
      setLoading(false);
      return;
    }

    void Promise.all([getAdminSession(token), getWorkspaceStatus(token)])
      .then(([nextSession, nextWorkspaceStatus]) => {
        setSession(nextSession);
        setWorkspaceStatus(nextWorkspaceStatus);
      })
      .catch(() => {
        setSession(null);
        setWorkspaceStatus(null);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading || !session || !workspaceStatus) {
    return null;
  }

  const onboardingCompleted = Boolean(
    session.onboarding_completed_at || workspaceStatus.onboarding_completed_at,
  );
  if (onboardingCompleted) {
    return null;
  }

  const isAdmin = session.role === "admin";
  const telegramReady = workspaceStatus.telegram_configured;
  const pairsReady = workspaceStatus.configured_pairs_count > 0;
  const canFinish = telegramReady && pairsReady && understoodScores;

  async function handleComplete() {
    const token = getStoredAuthToken();
    if (!token || !canFinish) return;

    setFinishing(true);
    try {
      await completeOnboarding(token);
      setSession((current) =>
        current ? { ...current, onboarding_completed_at: new Date().toISOString() } : current,
      );
    } finally {
      setFinishing(false);
    }
  }

  return (
    <Card className="border-emerald-500/20 bg-emerald-500/[0.04]">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Sparkles className="h-4 w-4" />
              Primeiros passos
            </CardTitle>
            <CardDescription>
              {workspaceStatus.organization?.name
                ? `Seu acesso está dentro da organização ${workspaceStatus.organization.name}.`
                : "Finalize os itens abaixo para deixar o workspace pronto para uso."}
            </CardDescription>
          </div>
          <Badge variant="outline">{isAdmin ? "admin" : "membro"}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <ChecklistRow
          checked={telegramReady}
          title="Configurar Telegram"
          description={
            isAdmin
              ? "Cadastre bot token e chat ID para receber alertas no canal certo."
              : "Confirme com o administrador se o Telegram do workspace ja foi configurado."
          }
        />
        <ChecklistRow
          checked={pairsReady}
          title="Selecionar pares monitorados"
          description={`${workspaceStatus.configured_pairs_count} pares ativos no workspace atual.`}
        />
        <ChecklistRow
          checked={understoodScores}
          title="Entender os scores"
          description="Scores altos combinam volatilidade, volume, liquidez, spread e repetição do movimento."
          action={
            <Button
              type="button"
              size="sm"
              variant={understoodScores ? "default" : "outline"}
              onClick={() => setUnderstoodScores((current) => !current)}
            >
              {understoodScores ? "Entendido" : "Marcar como entendido"}
            </Button>
          }
        />

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-muted-foreground">
            Ajustes operacionais ficam em Configurações. Depois disso, o dashboard passa a refletir o workspace ativo.
          </p>
          <div className="flex gap-2">
            <Link href="/settings" className={cn(buttonVariants({ variant: "outline" }))}>
              Abrir configurações
            </Link>
            <Button type="button" onClick={handleComplete} disabled={!canFinish || finishing} className="gap-2">
              {finishing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              Concluir onboarding
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ChecklistRow({
  checked,
  title,
  description,
  action,
}: {
  checked: boolean;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-background/70 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <div className="flex items-center gap-2">
          <Badge variant={checked ? "default" : "outline"}>{checked ? "feito" : "pendente"}</Badge>
          <p className="text-sm font-semibold">{title}</p>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      </div>
      {action ? action : null}
    </div>
  );
}