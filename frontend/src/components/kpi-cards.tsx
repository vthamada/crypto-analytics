"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { DashboardStats } from "@/lib/types";

interface KPICardsProps {
  stats: DashboardStats | null;
  loading?: boolean;
}

export function KPICards({ stats, loading }: KPICardsProps) {
  const cards = [
    {
      id: "opportunities",
      title: "Oportunidades",
      value: stats?.total_opportunities ?? 0,
      subtitle: `${stats?.active_opportunities ?? 0} ativas (score >= 40)`,
      emoji: "📈",
      color: "text-emerald-500",
    },
    {
      id: "best-score",
      title: "Melhor Score",
      value: stats?.best_score?.toFixed(1) ?? "0",
      subtitle: "Maior pontuação atual",
      emoji: "⭐",
      color: "text-yellow-500",
    },
    {
      id: "arbitrage",
      title: "Arbitragem",
      value: stats?.arbitrage_opportunities ?? 0,
      subtitle: "Sinais com gap cross-exchange",
      emoji: "↔",
      color: "text-blue-500",
    },
    {
      id: "volume-24h",
      title: "Volume Total 24h",
      value: stats ? `R$ ${(stats.total_volume_24h / 1_000_000).toFixed(1)}M` : "R$ 0",
      subtitle: "Volume agregado",
      emoji: "💰",
      color: "text-purple-500",
    },
    {
      id: "monitored-pairs",
      title: "Pares Monitorados",
      value: stats?.monitored_pairs ?? 0,
      subtitle: `${stats?.exchanges_online ?? 0} exchanges online`,
      emoji: "📡",
      color: "text-cyan-500",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
      {cards.map((card) => (
        <Card key={card.title} className="relative overflow-hidden rounded-2xl" data-testid={`kpi-card-${card.id}`}>
          <CardContent className="p-5">
            {loading ? (
              <div className="space-y-2">
                <div className="h-4 w-24 animate-pulse rounded bg-muted" />
                <div className="h-8 w-16 animate-pulse rounded bg-muted" />
                <div className="h-3 w-32 animate-pulse rounded bg-muted" />
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-muted-foreground">{card.title}</span>
                  <span className="text-lg">{card.emoji}</span>
                </div>
                <div className={`mt-1 text-2xl font-bold ${card.color}`} data-testid={`kpi-value-${card.id}`}>
                  {card.value}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{card.subtitle}</p>
              </>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
