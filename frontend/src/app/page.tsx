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
import type { Opportunity } from "@/lib/types";

function DashboardContent() {
  const { opportunities, stats, loading, error, refetch } = useOpportunities();
  const [selected, setSelected] = useState<Opportunity | null>(null);

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
        opportunities={opportunities}
        loading={loading}
        onSelect={setSelected}
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
