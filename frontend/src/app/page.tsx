"use client";

import { useState } from "react";
import { KPICards } from "@/components/kpi-cards";
import { InlineErrorState } from "@/components/inline-error-state";
import { OnboardingChecklist } from "@/components/onboarding-checklist";
import { OpportunitiesTable } from "@/components/opportunities-table";
import { SessionRequiredState } from "@/components/session-required-state";
import { SignalDetailModal } from "@/components/signal-detail-modal";
import { useHasAuthenticatedWorkspace } from "@/hooks/use-has-authenticated-workspace";
import { useOpportunities } from "@/hooks/use-opportunities";
import { getOpportunity } from "@/lib/api";
import type { Opportunity } from "@/lib/types";
import {
  getOperationalDashboardBucket,
  type OpportunityListItem,
} from "@/lib/opportunity-operability";

function DashboardContent() {
  const { opportunities, auditOpportunities, stats, loading, error, refetch } = useOpportunities();
  const [selected, setSelected] = useState<Opportunity | null>(null);
  const nowOpportunities = opportunities.filter((opportunity) => getOperationalDashboardBucket(opportunity) === "now");
  const observeOpportunities = opportunities.filter((opportunity) => getOperationalDashboardBucket(opportunity) === "observe");
  const visibleAuditOpportunities = opportunities.filter((opportunity) => getOperationalDashboardBucket(opportunity) === "audit");
  const auditSectionOpportunities = [...visibleAuditOpportunities, ...auditOpportunities]
    .filter((opportunity, index, all) => all.findIndex((item) => item.id === opportunity.id) === index)
    .slice(0, 20);

  async function openOpportunityDetail(opportunity: OpportunityListItem) {
    try {
      const fullOpportunity = await getOpportunity(opportunity.id);
      setSelected(fullOpportunity ?? null);
    } catch {
      setSelected(null);
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 pt-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Monitoramento em tempo real de oportunidades em criptomoedas
        </p>
      </div>

      <KPICards stats={stats} loading={loading} />

      {error ? <InlineErrorState message={error} onRetry={() => void refetch()} /> : null}

      <OnboardingChecklist />

      <OpportunitiesTable
        title="Oportunidades agora"
        description="Somente sinais com tese operacional concreta: entrada, saida, tamanho, risco e motivo para agir."
        emptyMessage="Nenhuma oportunidade acionavel agora. Isso e melhor do que alertar ruido."
        opportunities={nowOpportunities}
        loading={loading}
        onSelect={(opportunity) => void openOpportunityDetail(opportunity)}
      />

      <OpportunitiesTable
        title="So observar"
        description="Ativos saudaveis ou em preparacao, mas ainda sem gatilho suficiente para alerta."
        emptyMessage="Nenhum ativo relevante apenas para observacao no momento."
        opportunities={observeOpportunities}
        loading={loading}
        compact
        onSelect={(opportunity) => void openOpportunityDetail(opportunity)}
      />

      <OpportunitiesTable
        title="Auditoria / Evitar"
        description="Sinais bloqueados, sem liquidez, atrasados ou tecnicamente vistos mas fora da oportunidade principal."
        emptyMessage="Nenhum item de auditoria recente carregado."
        opportunities={auditSectionOpportunities}
        loading={loading}
        compact
        onSelect={(opportunity) => void openOpportunityDetail(opportunity)}
      />

      <SignalDetailModal
        opportunity={selected}
        open={!!selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}


export default function DashboardPage() {
  const hasAuthenticatedWorkspace = useHasAuthenticatedWorkspace();

  if (hasAuthenticatedWorkspace === null) {
    return <div className="mx-auto max-w-7xl p-4 pt-6" />;
  }

  if (!hasAuthenticatedWorkspace) {
    return (
      <SessionRequiredState
        title="Dashboard restrito ao workspace autenticado"
        description="O monitoramento em tempo real agora exige uma sessao autenticada e um workspace ativo para manter o isolamento multi-tenant."
      />
    );
  }

  return <DashboardContent />;
}
