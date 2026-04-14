import type {
  AppConfig,
  Analytics,
  DashboardStats,
  HistoryRecord,
  Opportunity,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

// Dashboard
export function getStats(): Promise<DashboardStats> {
  return fetchJSON("/dashboard/stats");
}

// Opportunities
export function getOpportunities(params?: {
  exchange?: string;
  pair?: string;
  min_score?: number;
  movement_type?: string;
  sort_by?: string;
  limit?: number;
}): Promise<Opportunity[]> {
  const query = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") query.set(k, String(v));
    });
  }
  const qs = query.toString();
  return fetchJSON(`/opportunities${qs ? `?${qs}` : ""}`);
}

export function getOpportunity(id: string): Promise<Opportunity | null> {
  return fetchJSON(`/opportunities/${id}`);
}

// History
export function getHistory(params?: {
  limit?: number;
  offset?: number;
  exchange?: string;
  pair?: string;
  min_score?: number;
  hours?: number;
}): Promise<HistoryRecord[]> {
  const query = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") query.set(k, String(v));
    });
  }
  const qs = query.toString();
  return fetchJSON(`/history${qs ? `?${qs}` : ""}`);
}

export function getAnalytics(): Promise<Analytics> {
  return fetchJSON("/analytics");
}

// Config
export function getConfig(): Promise<AppConfig> {
  return fetchJSON("/config");
}

export function updateConfig(config: Partial<AppConfig>): Promise<AppConfig> {
  return fetchJSON("/config", {
    method: "PUT",
    body: JSON.stringify(config),
  });
}

// Health
export function getHealth(): Promise<{
  status: string;
  last_scan: string | null;
  opportunities_count: number;
}> {
  return fetchJSON("/health");
}
