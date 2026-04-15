import type {
  AdminSessionInfo,
  AppConfig,
  Analytics,
  AuditLogEntry,
  DashboardStats,
  HistoryRecord,
  Opportunity,
  WorkspaceSummary,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
export const AUTH_TOKEN_STORAGE_KEY = "crypto-analytics-admin-token";
export const ACTIVE_WORKSPACE_STORAGE_KEY = "crypto-analytics-active-workspace";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

function adminHeaders(adminToken?: string): HeadersInit | undefined {
  const token = adminToken ?? getStoredAuthToken();
  const workspaceId = getStoredWorkspaceId();
  const headers: HeadersInit = {};

  if (token) {
    Object.assign(headers, {
      "X-Admin-Token": token,
      Authorization: `Bearer ${token}`,
    });
  }
  if (workspaceId) {
    Object.assign(headers, {
      "X-Workspace-Id": workspaceId,
    });
  }

  return Object.keys(headers).length > 0 ? headers : undefined;
}

export function getStoredAuthToken(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || "";
}

export function setStoredAuthToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
}

export function clearStoredAuthToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

export function getStoredWorkspaceId(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY) || "";
}

export function setStoredWorkspaceId(workspaceId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, workspaceId);
}

export function clearStoredWorkspaceId() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
}

function workspaceHeaders(): HeadersInit | undefined {
  const workspaceId = getStoredWorkspaceId();
  return workspaceId ? { "X-Workspace-Id": workspaceId } : undefined;
}

function sessionHeaders(adminToken?: string): HeadersInit | undefined {
  if (adminToken) {
    return adminHeaders(adminToken);
  }

  const headers = {
    ...(workspaceHeaders() ?? {}),
    ...(adminHeaders() ?? {}),
  };
  return Object.keys(headers).length > 0 ? headers : undefined;
}

// Dashboard
export function getStats(): Promise<DashboardStats> {
  return fetchJSON("/dashboard/stats", { headers: sessionHeaders() });
}

// Opportunities
export function getOpportunities(params?: {
  exchange?: string;
  pair?: string;
  min_score?: number;
  movement_type?: string;
  arbitrage_only?: boolean;
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
  return fetchJSON(`/opportunities${qs ? `?${qs}` : ""}`, { headers: sessionHeaders() });
}

export function getOpportunity(id: string): Promise<Opportunity | null> {
  return fetchJSON(`/opportunities/${id}`, { headers: sessionHeaders() });
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
  return fetchJSON(`/history${qs ? `?${qs}` : ""}`, { headers: sessionHeaders() });
}

export function getAnalytics(params?: {
  exchange?: string;
  pair?: string;
  min_score?: number;
  hours?: number;
}): Promise<Analytics> {
  const query = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") query.set(k, String(v));
    });
  }
  const qs = query.toString();
  return fetchJSON(`/analytics${qs ? `?${qs}` : ""}`, { headers: sessionHeaders() });
}

// Config
export function adminLogin(username: string, password: string): Promise<{
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
  session: AdminSessionInfo;
}> {
  return fetchJSON("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function getAdminSession(adminToken?: string): Promise<AdminSessionInfo> {
  return fetchJSON("/auth/session", { headers: adminHeaders(adminToken) });
}

export function changeAdminPassword(
  currentPassword: string,
  newPassword: string,
  adminToken?: string,
): Promise<{
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
  session: AdminSessionInfo;
}> {
  return fetchJSON("/auth/change-password", {
    method: "POST",
    headers: adminHeaders(adminToken),
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export function getAdminAuditLog(limit = 25, adminToken?: string): Promise<AuditLogEntry[]> {
  return fetchJSON(`/admin/audit-log?limit=${limit}`, { headers: adminHeaders(adminToken) });
}

export function getWorkspaces(adminToken?: string): Promise<WorkspaceSummary[]> {
  return fetchJSON("/workspaces", { headers: adminHeaders(adminToken) });
}

export function createWorkspace(name: string, adminToken?: string): Promise<WorkspaceSummary> {
  return fetchJSON("/workspaces", {
    method: "POST",
    headers: adminHeaders(adminToken),
    body: JSON.stringify({ name }),
  });
}

export function getConfig(adminToken?: string): Promise<AppConfig> {
  return fetchJSON("/config", { headers: adminHeaders(adminToken) });
}

export function updateConfig(config: Partial<AppConfig>, adminToken?: string): Promise<AppConfig> {
  return fetchJSON("/config", {
    method: "PUT",
    headers: adminHeaders(adminToken),
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
