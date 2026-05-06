"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { DashboardStats, Opportunity } from "@/lib/types";
import { getDashboard, getOpportunities, getStats } from "@/lib/api";
import type { OpportunitySortMode } from "@/lib/opportunity-operability";
import { wsClient } from "@/lib/websocket";

export function useOpportunities(filters?: {
  exchange?: string;
  pair?: string;
  min_score?: number;
  movement_type?: string;
  arbitrage_only?: boolean;
  operable_only?: boolean;
  sort_by?: OpportunitySortMode;
}) {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const filtersRef = useRef(filters);
  filtersRef.current = filters;

  const deriveStats = useCallback((items: Opportunity[], previous: DashboardStats | null): DashboardStats => {
    const active = items.filter((opportunity) => opportunity.score >= 40);
    return {
      total_opportunities: items.length,
      active_opportunities: active.length,
      monitored_pairs: previous?.monitored_pairs ?? 0,
      total_volume_24h: items.reduce((total, opportunity) => total + opportunity.quote_volume_24h, 0),
      best_score: Math.max(0, ...items.map((opportunity) => opportunity.score)),
      exchanges_online: new Set(items.map((opportunity) => opportunity.exchange)).size,
      arbitrage_opportunities: items.filter((opportunity) => opportunity.arbitrage_available).length,
      operable_opportunities: items.filter((opportunity) => opportunity.operable_signal).length,
      trade_opportunities: items.filter((opportunity) => opportunity.opportunity_type === "trade").length,
      hold_opportunities: items.filter((opportunity) => opportunity.opportunity_type === "hold").length,
      observe_opportunities: items.filter((opportunity) => opportunity.opportunity_type === "observe").length,
      avoid_opportunities: items.filter((opportunity) => opportunity.opportunity_type === "avoid").length,
      last_scan: previous?.last_scan ?? null,
    };
  }, []);

  const fetchData = useCallback(async () => {
    try {
      if (!filtersRef.current) {
        const dashboard = await getDashboard();
        setOpportunities(dashboard.opportunities);
        setStats(dashboard.stats);
      } else {
        const [opps, dashStats] = await Promise.all([
          getOpportunities(filtersRef.current),
          getStats(),
        ]);
        setOpportunities(opps);
        setStats(dashStats);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();

    const unsubscribe = wsClient.subscribe((message) => {
      if (message.type === "opportunities_update" && message.data) {
        const nextOpportunities = message.data;
        setOpportunities(nextOpportunities);
        setStats((previous) => deriveStats(nextOpportunities, previous));
      }
    });

    // Fallback polling reconciles workspace projection without refetching stats on every websocket event.
    const interval = setInterval(fetchData, 60000);

    return () => {
      unsubscribe();
      clearInterval(interval);
    };
  }, [deriveStats, fetchData]);

  return { opportunities, stats, loading, error, refetch: fetchData };
}
