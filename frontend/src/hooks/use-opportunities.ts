"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { DashboardStats, Opportunity } from "@/lib/types";
import { getOpportunities, getStats } from "@/lib/api";
import { wsClient } from "@/lib/websocket";

export function useOpportunities(filters?: {
  exchange?: string;
  pair?: string;
  min_score?: number;
  movement_type?: string;
  sort_by?: string;
}) {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const filtersRef = useRef(filters);
  filtersRef.current = filters;

  const fetchData = useCallback(async () => {
    try {
      const [opps, dashStats] = await Promise.all([
        getOpportunities(filtersRef.current),
        getStats(),
      ]);
      setOpportunities(opps);
      setStats(dashStats);
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
        setOpportunities(message.data);
        // Refresh stats too
        getStats().then(setStats).catch(() => {});
      }
    });

    // Fallback polling every 30s
    const interval = setInterval(fetchData, 30000);

    return () => {
      unsubscribe();
      clearInterval(interval);
    };
  }, [fetchData]);

  return { opportunities, stats, loading, error, refetch: fetchData };
}
