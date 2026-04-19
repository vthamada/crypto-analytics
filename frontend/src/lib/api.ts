import type {
  AdminSessionInfo,
  AppConfig,
  ConfigResponse,
  AvailablePairsResponse,
  Analytics,
  AuthResponse,
  AuditLogEntry,
  DashboardStats,
  ExchangeCredentialValidationResponse,
  HistoryRecord,
  InvitePreview,
  InviteRecord,
  Opportunity,
  UserCreateResult,
  UserRecord,
  WorkspaceStatus,
  WorkspaceSummary,
} from "./types";
import { emitAppError } from "./app-errors";
import type { OpportunitySortMode } from "./opportunity-operability";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
export const AUTH_TOKEN_STORAGE_KEY = "crypto-analytics-admin-token";
export const REFRESH_TOKEN_STORAGE_KEY = "crypto-analytics-refresh-token";
export const ACTIVE_WORKSPACE_STORAGE_KEY = "crypto-analytics-active-workspace";
export const SESSION_STORAGE_EVENT = "crypto-analytics-session-changed";

type ApiRequestInit = RequestInit & {
  skipAuthRefresh?: boolean;
  skipGlobalErrorToast?: boolean;
};

let refreshPromise: Promise<string | null> | null = null;

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function emitSessionStorageEvent() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(SESSION_STORAGE_EVENT));
}

function normalizeHeaders(headers?: HeadersInit): Headers {
  return new Headers(headers);
}

function attachStoredSessionHeaders(headers: Headers) {
  const token = getStoredAuthToken();
  const workspaceId = getStoredWorkspaceId();

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (token && !headers.has("X-Admin-Token")) {
    headers.set("X-Admin-Token", token);
  }
  if (workspaceId && !headers.has("X-Workspace-Id")) {
    headers.set("X-Workspace-Id", workspaceId);
  }
}

function buildHeaders(init?: ApiRequestInit): Headers {
  const headers = normalizeHeaders(init?.headers);
  if (!(init?.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  attachStoredSessionHeaders(headers);
  return headers;
}

async function buildApiError(response: Response): Promise<ApiError> {
  let message = `API error: ${response.status} ${response.statusText}`;

  try {
    const body = await response.json();
    if (typeof body?.detail === "string" && body.detail) {
      message = body.detail;
    }
  } catch {
    // ignore invalid json error payloads
  }

  return new ApiError(message, response.status);
}

function emitRequestError(error: ApiError, init?: ApiRequestInit) {
  if (init?.skipGlobalErrorToast) {
    return;
  }
  emitAppError({
    message: error.message,
    source: "api",
    status: error.status,
  });
}

async function performRequest(path: string, init?: ApiRequestInit): Promise<Response> {
  try {
    return await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: buildHeaders(init),
    });
  } catch {
    const error = new ApiError("Nao foi possivel conectar ao backend.", 0);
    emitRequestError(error, init);
    throw error;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;

  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return null;

  if (!refreshPromise) {
    refreshPromise = (async () => {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        clearStoredSession();
        return null;
      }

      const payload = (await response.json()) as AuthResponse;
      setStoredAuthToken(payload.access_token);
      setStoredRefreshToken(payload.refresh_token);
      return payload.access_token;
    })().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

async function fetchJSON<T>(path: string, init?: ApiRequestInit): Promise<T> {
  const res = await performRequest(path, init);

  if (res.status === 401 && !init?.skipAuthRefresh && path !== "/auth/login" && path !== "/auth/refresh") {
    const refreshedToken = await refreshAccessToken();
    if (refreshedToken) {
      const retry = await performRequest(path, init);
      if (!retry.ok) {
        const error = await buildApiError(retry);
        emitRequestError(error, init);
        throw error;
      }
      if (retry.status === 204) {
        return undefined as T;
      }
      return retry.json();
    }
  }

  if (!res.ok) {
    const error = await buildApiError(res);
    emitRequestError(error, init);
    throw error;
  }

  if (res.status === 204) {
    return undefined as T;
  }

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
  emitSessionStorageEvent();
}

export function clearStoredAuthToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  emitSessionStorageEvent();
}

export function getStoredRefreshToken(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY) || "";
}

export function setStoredRefreshToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
  emitSessionStorageEvent();
}

export function clearStoredRefreshToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
  emitSessionStorageEvent();
}

export function clearStoredSession() {
  clearStoredAuthToken();
  clearStoredRefreshToken();
  clearStoredWorkspaceId();
}

export function getStoredWorkspaceId(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY) || "";
}

export function setStoredWorkspaceId(workspaceId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, workspaceId);
  emitSessionStorageEvent();
}

export function clearStoredWorkspaceId() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  emitSessionStorageEvent();
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
  operable_only?: boolean;
  sort_by?: OpportunitySortMode;
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

export function getOperationalAnalytics(params?: {
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
  return fetchJSON(`/analytics/operational${qs ? `?${qs}` : ""}`, { headers: sessionHeaders() });
}

// Config
export function adminLogin(username: string, password: string): Promise<{
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_seconds: number;
  refresh_expires_in_seconds: number;
  session: AdminSessionInfo;
}> {
  return fetchJSON("/auth/login", {
    method: "POST",
    skipAuthRefresh: true,
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
): Promise<AuthResponse> {
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

export function getWorkspaceStatus(adminToken?: string): Promise<WorkspaceStatus> {
  return fetchJSON("/workspace/status", { headers: sessionHeaders(adminToken) });
}

export function completeOnboarding(adminToken?: string): Promise<{ completed: boolean; completed_at: string }> {
  return fetchJSON("/onboarding/complete", {
    method: "POST",
    headers: sessionHeaders(adminToken),
  });
}

export function createWorkspace(name: string, adminToken?: string): Promise<WorkspaceSummary> {
  return fetchJSON("/workspaces", {
    method: "POST",
    headers: adminHeaders(adminToken),
    body: JSON.stringify({ name }),
  });
}

export function listUsers(adminToken?: string): Promise<UserRecord[]> {
  return fetchJSON("/users", { headers: adminHeaders(adminToken) });
}

export function createUser(
  payload: { username: string; temporary_password?: string; role?: string },
  adminToken?: string,
): Promise<UserCreateResult> {
  return fetchJSON("/users", {
    method: "POST",
    headers: adminHeaders(adminToken),
    body: JSON.stringify(payload),
  });
}

export function updateUserActiveState(
  userId: string,
  isActive: boolean,
  adminToken?: string,
): Promise<UserRecord> {
  return fetchJSON(`/users/${userId}`, {
    method: "PATCH",
    headers: adminHeaders(adminToken),
    body: JSON.stringify({ is_active: isActive }),
  });
}

export function resetUserPassword(userId: string, adminToken?: string): Promise<UserCreateResult> {
  return fetchJSON(`/users/${userId}/reset-password`, {
    method: "POST",
    headers: adminHeaders(adminToken),
  });
}

export function listInvites(adminToken?: string): Promise<InviteRecord[]> {
  return fetchJSON("/invites", { headers: adminHeaders(adminToken) });
}

export function createInvite(
  payload: { email: string; role?: string; expires_in_days?: number },
  adminToken?: string,
): Promise<InviteRecord> {
  return fetchJSON("/invites", {
    method: "POST",
    headers: adminHeaders(adminToken),
    body: JSON.stringify(payload),
  });
}

export function getInvitePreview(code: string): Promise<InvitePreview> {
  return fetchJSON(`/invites/${encodeURIComponent(code)}`, { skipAuthRefresh: true });
}

export function acceptInvite(payload: {
  code: string;
  email: string;
  password: string;
}): Promise<AuthResponse> {
  return fetchJSON("/invites/accept", {
    method: "POST",
    skipAuthRefresh: true,
    body: JSON.stringify(payload),
  });
}

export function getAvailablePairs(): Promise<AvailablePairsResponse> {
  return fetchJSON("/pairs/available", { skipAuthRefresh: true });
}

export function getConfig(adminToken?: string): Promise<ConfigResponse> {
  return fetchJSON("/config", { headers: adminHeaders(adminToken) });
}

export function updateConfig(
  config: Partial<AppConfig>,
  adminToken?: string,
  options?: { skipAudit?: boolean },
): Promise<ConfigResponse> {
  const headers = new Headers(normalizeHeaders(adminHeaders(adminToken)));
  if (options?.skipAudit) {
    headers.set("X-Config-Audit-Mode", "skip");
  }

  return fetchJSON("/config", {
    method: "PUT",
    headers,
    body: JSON.stringify(config),
  });
}

export function validateExchangeCredentials(
  payload: Partial<Pick<AppConfig, "novadax_api_key" | "novadax_api_secret" | "mb_api_key" | "mb_api_secret" | "binance_api_key" | "binance_api_secret">>,
  adminToken?: string,
): Promise<ExchangeCredentialValidationResponse> {
  return fetchJSON("/config/validate-exchanges", {
    method: "POST",
    headers: adminHeaders(adminToken),
    body: JSON.stringify(payload),
  });
}

export function sendTelegramTestMessage(
  payload: { telegram_bot_token?: string; telegram_chat_id?: string },
  adminToken?: string,
): Promise<{ delivered: boolean }> {
  return fetchJSON("/config/telegram/test", {
    method: "POST",
    headers: adminHeaders(adminToken),
    body: JSON.stringify(payload),
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
