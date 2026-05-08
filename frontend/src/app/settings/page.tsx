"use client";

import { useDeferredValue, useEffect, useEffectEvent, useRef, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  adminLogin,
  changeAdminPassword,
  clearStoredRefreshToken,
  clearStoredSession,
  createInvite,
  createUser,
  createWorkspace,
  getAdminAuditLog,
  getAdminSession,
  getAvailablePairs,
  getConfig,
  getMissedSignalDiagnostic,
  getPairDiagnostic,
  getStoredAuthToken,
  getStoredWorkspaceId,
  listInvites,
  listUsers,
  resetUserPassword,
  sendTelegramTestMessage,
  setStoredAuthToken,
  setStoredRefreshToken,
  setStoredWorkspaceId,
  updateConfig,
  updateUserActiveState,
  validateExchangeCredentials,
} from "@/lib/api";
import type {
  AdminSessionInfo,
  AppConfig,
  AvailablePairRecord,
  AvailablePairsResponse,
  AuditLogEntry,
  ExchangeCredentialValidationResult,
  Exchange,
  InviteRecord,
  MissedSignalDiagnostic,
  PairExchangeDiagnostic,
  UserRecord,
  WorkspaceSummary,
} from "@/lib/types";
import {
  Building2,
  Check,
  Copy,
  Eye,
  EyeOff,
  FolderPlus,
  Info,
  KeyRound,
  Loader2,
  Lock,
  LogOut,
  MailPlus,
  RefreshCcw,
  Save,
  ShieldCheck,
  UserPlus,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";

const ALL_EXCHANGES: { id: Exchange; label: string }[] = [
  { id: "novadax", label: "NovaDAX" },
  { id: "mercado_bitcoin", label: "Mercado Bitcoin" },
  { id: "binance", label: "Binance" },
];

const FALLBACK_PAIRS = [
  "BTC_BRL",
  "ETH_BRL",
  "SOL_BRL",
  "ADA_BRL",
  "XRP_BRL",
  "DOGE_BRL",
  "DOT_BRL",
  "AVAX_BRL",
  "MATIC_BRL",
  "LINK_BRL",
  "LTC_BRL",
  "UNI_BRL",
  "ATOM_BRL",
  "NEAR_BRL",
  "APE_BRL",
];

const FALLBACK_AVAILABLE_PAIRS: AvailablePairRecord[] = FALLBACK_PAIRS.map((pair) => ({
  pair,
  display_name: pair.replace("_", "/"),
  availability: {
    novadax: false,
    mercado_bitcoin: false,
    binance: false,
  },
}));

const EXCHANGE_CRED_FIELDS: {
  exchange: Exchange;
  label: string;
  keyField: "novadax_api_key" | "mb_api_key" | "binance_api_key";
  secretField: "novadax_api_secret" | "mb_api_secret" | "binance_api_secret";
}[] = [
  {
    exchange: "novadax",
    label: "NovaDAX",
    keyField: "novadax_api_key",
    secretField: "novadax_api_secret",
  },
  {
    exchange: "mercado_bitcoin",
    label: "Mercado Bitcoin",
    keyField: "mb_api_key",
    secretField: "mb_api_secret",
  },
  {
    exchange: "binance",
    label: "Binance",
    keyField: "binance_api_key",
    secretField: "binance_api_secret",
  },
];

type CredentialNotice = {
  action: string;
  username: string;
  temporaryPassword: string;
};

type PairCatalogView = "active" | "discover";
type PairAvailabilityFilter = "active_exchanges" | "all" | Exchange;
type PairCatalogEntry = AvailablePairRecord & {
  isActive: boolean;
  availableExchangeCount: number;
  enabledExchangeMatches: number;
};
type TradingProfile = AppConfig["trading_profile"];
type AutoSaveStatus = "idle" | "saving" | "saved" | "error";
type DisplayAuditLogEntry = AuditLogEntry & {
  aggregatedCount: number;
  groupedOldestCreatedAt?: string;
};
type MissedSignalWindow = "1" | "4" | "24" | "72" | "custom";

const TRADING_PROFILE_OPTIONS: { value: TradingProfile; label: string; description: string }[] = [
  {
    value: "intraday_liquido",
    label: "Intraday liquido",
    description: "Equilibra volatilidade, volume e saida para trades de horas.",
  },
  {
    value: "conservador",
    label: "Conservador",
    description: "Prioriza liquidez e reduz tolerancia a slippage.",
  },
  {
    value: "agressivo",
    label: "Agressivo",
    description: "Aceita mais slippage para capturar movimentos fortes.",
  },
  {
    value: "scalp",
    label: "Scalp",
    description: "Exige spread menor e execucao mais rapida.",
  },
];

const TRADING_PROFILE_PRESETS: Record<
  TradingProfile,
  Pick<AppConfig, "order_notional_brl" | "max_entry_slippage_bps" | "max_exit_slippage_bps" | "min_quote_volume_brl">
> = {
  intraday_liquido: {
    order_notional_brl: 1000,
    max_entry_slippage_bps: 500,
    max_exit_slippage_bps: 500,
    min_quote_volume_brl: 3000,
  },
  conservador: {
    order_notional_brl: 1000,
    max_entry_slippage_bps: 300,
    max_exit_slippage_bps: 300,
    min_quote_volume_brl: 10000,
  },
  agressivo: {
    order_notional_brl: 300,
    max_entry_slippage_bps: 800,
    max_exit_slippage_bps: 800,
    min_quote_volume_brl: 3000,
  },
  scalp: {
    order_notional_brl: 200,
    max_entry_slippage_bps: 300,
    max_exit_slippage_bps: 300,
    min_quote_volume_brl: 5000,
  },
};

const OPERATIONAL_CONFIG_AUTOSAVE_DELAY_MS = 900;
const CONFIG_UPDATE_COLLAPSE_WINDOW_MS = 15 * 60 * 1000;
const CONFIG_UPDATE_FIELD_LABELS: Record<string, string> = {
  thresholds: "thresholds",
  weights: "pesos",
  trading_profile: "perfil operacional",
  order_notional_brl: "tamanho de ordem",
  max_entry_slippage_bps: "slippage de entrada",
  max_exit_slippage_bps: "slippage de saida",
  min_quote_volume_brl: "liquidez notional minima",
  pair_universe_mode: "universo de pares",
  enabled_exchanges: "exchanges",
  enabled_pairs: "pares",
  scan_interval_seconds: "intervalo do scanner",
  telegram_enabled: "Telegram",
  telegram_alert_threshold: "score minimo de alerta",
  telegram_alert_cooldown_seconds: "cooldown de alerta",
  telegram_alert_types: "tipos de alerta",
  telegram_operable_only: "alertas operaveis",
  telegram_min_executability_score: "mínimo de operabilidade no Telegram",
  telegram_alert_exchanges: "exchanges do Telegram",
  telegram_alert_pairs: "pares do Telegram",
  telegram_bot_token: "bot do Telegram",
  telegram_chat_id: "chat do Telegram",
  novadax_api_key: "API key NovaDAX",
  novadax_api_secret: "API secret NovaDAX",
  mb_api_key: "API key Mercado Bitcoin",
  mb_api_secret: "API secret Mercado Bitcoin",
  binance_api_key: "API key Binance",
  binance_api_secret: "API secret Binance",
};

type SensitiveField =
  | "telegram_bot_token"
  | "telegram_chat_id"
  | "novadax_api_key"
  | "novadax_api_secret"
  | "mb_api_key"
  | "mb_api_secret"
  | "binance_api_key"
  | "binance_api_secret";

function buildOperationalConfigPayload(config: AppConfig): Partial<AppConfig> {
  return {
    thresholds: config.thresholds,
    weights: config.weights,
    trading_profile: config.trading_profile,
    order_notional_brl: config.order_notional_brl,
    max_entry_slippage_bps: config.max_entry_slippage_bps,
    max_exit_slippage_bps: config.max_exit_slippage_bps,
    min_quote_volume_brl: config.min_quote_volume_brl,
    pair_universe_mode: config.pair_universe_mode ?? "all_brl",
    enabled_exchanges: config.enabled_exchanges,
    enabled_pairs: config.enabled_pairs,
    scan_interval_seconds: config.scan_interval_seconds,
    telegram_enabled: config.telegram_enabled,
    telegram_alert_threshold: config.telegram_alert_threshold,
    telegram_alert_cooldown_seconds: config.telegram_alert_cooldown_seconds,
    telegram_daily_alert_limit: config.telegram_daily_alert_limit,
    telegram_alert_types: config.telegram_alert_types,
    telegram_operable_only: config.telegram_operable_only,
    telegram_min_executability_score: config.telegram_min_executability_score,
    telegram_alert_exchanges: config.telegram_alert_exchanges,
    telegram_alert_pairs: config.telegram_alert_pairs,
  };
}

function serializeOperationalConfig(config: AppConfig): string {
  return JSON.stringify(buildOperationalConfigPayload(config));
}

function clampNumericValue(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function parseNumericValue(value: string, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function extractUpdatedFields(details: Record<string, unknown>): string[] {
  const rawFields = details.updated_fields;
  if (!Array.isArray(rawFields)) {
    return [];
  }

  return rawFields.filter((value): value is string => typeof value === "string");
}

function collapseAuditLogEntries(entries: AuditLogEntry[]): DisplayAuditLogEntry[] {
  const collapsed: DisplayAuditLogEntry[] = [];

  for (const entry of entries) {
    const previous = collapsed[collapsed.length - 1];
    const canCollapseConfigUpdate =
      entry.action === "workspace.config_updated" &&
      previous?.action === entry.action &&
      previous.actor_username === entry.actor_username &&
      previous.status === entry.status &&
      Math.abs(new Date(previous.created_at).getTime() - new Date(entry.created_at).getTime()) <=
        CONFIG_UPDATE_COLLAPSE_WINDOW_MS;

    if (canCollapseConfigUpdate && previous) {
      const mergedUpdatedFields = Array.from(
        new Set([...extractUpdatedFields(previous.details), ...extractUpdatedFields(entry.details)]),
      ).sort((left, right) => left.localeCompare(right, "pt-BR"));

      collapsed[collapsed.length - 1] = {
        ...previous,
        aggregatedCount: previous.aggregatedCount + 1,
        groupedOldestCreatedAt: entry.created_at,
        details: mergedUpdatedFields.length
          ? { ...previous.details, updated_fields: mergedUpdatedFields }
          : previous.details,
      };
      continue;
    }

    collapsed.push({
      ...entry,
      aggregatedCount: 1,
    });
  }

  return collapsed;
}


function isWorkspaceAdminRole(role: string | null | undefined): boolean {
  return role === "owner" || role === "admin";
}


function isWorkspaceOwnerRole(role: string | null | undefined): boolean {
  return role === "owner";
}


function resolveWorkspaceSummary(
  workspaces: WorkspaceSummary[],
  workspaceId: string,
): WorkspaceSummary | null {
  return workspaces.find((workspace) => workspace.id === workspaceId) ?? null;
}

export default function SettingsPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [adminToken, setAdminToken] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [authError, setAuthError] = useState<string | null>(null);
  const [adminSession, setAdminSession] = useState<AdminSessionInfo | null>(null);
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [invites, setInvites] = useState<InviteRecord[]>([]);
  const [availablePairsCatalog, setAvailablePairsCatalog] = useState<AvailablePairsResponse | null>(null);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState("");
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [inviteExpiryDays, setInviteExpiryDays] = useState("7");
  const [creatingInvite, setCreatingInvite] = useState(false);
  const [copiedInviteCode, setCopiedInviteCode] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [usersLoading, setUsersLoading] = useState(false);
  const [userActionId, setUserActionId] = useState<string | null>(null);
  const [newUserName, setNewUserName] = useState("");
  const [newUserPassword, setNewUserPassword] = useState("");
  const [newUserRole, setNewUserRole] = useState("member");
  const [credentialNotice, setCredentialNotice] = useState<CredentialNotice | null>(null);
  const [pairSearch, setPairSearch] = useState("");
  const [manualPairInput, setManualPairInput] = useState("");
  const [manualPairFeedback, setManualPairFeedback] = useState<string | null>(null);
  const [diagnosticPairInput, setDiagnosticPairInput] = useState("");
  const [diagnosticExchange, setDiagnosticExchange] = useState<Exchange>("novadax");
  const [pairDiagnostic, setPairDiagnostic] = useState<PairExchangeDiagnostic | null>(null);
  const [pairDiagnosticLoading, setPairDiagnosticLoading] = useState(false);
  const [pairDiagnosticError, setPairDiagnosticError] = useState<string | null>(null);
  const [missedSignalPairInput, setMissedSignalPairInput] = useState("");
  const [missedSignalExchange, setMissedSignalExchange] = useState<Exchange>("novadax");
  const [missedSignalWindowHours, setMissedSignalWindowHours] = useState<MissedSignalWindow>("24");
  const [missedSignalCustomFrom, setMissedSignalCustomFrom] = useState("");
  const [missedSignalCustomTo, setMissedSignalCustomTo] = useState("");
  const [missedSignalDiagnostic, setMissedSignalDiagnostic] = useState<MissedSignalDiagnostic | null>(null);
  const [missedSignalLoading, setMissedSignalLoading] = useState(false);
  const [missedSignalError, setMissedSignalError] = useState<string | null>(null);
  const [pairCatalogLoading, setPairCatalogLoading] = useState(false);
  const [pairCatalogError, setPairCatalogError] = useState<string | null>(null);
  const [pairCatalogView, setPairCatalogView] = useState<PairCatalogView>("active");
  const [pairAvailabilityFilter, setPairAvailabilityFilter] = useState<PairAvailabilityFilter>("active_exchanges");
  const [pairResultsLimit, setPairResultsLimit] = useState(40);
  const [autoSaveStatus, setAutoSaveStatus] = useState<AutoSaveStatus>("idle");
  const [telegramTesting, setTelegramTesting] = useState(false);
  const [telegramTestFeedback, setTelegramTestFeedback] = useState<{
    kind: "success" | "error";
    message: string;
  } | null>(null);
  const [credentialValidationResults, setCredentialValidationResults] = useState<
    ExchangeCredentialValidationResult[]
  >([]);
  const [configuredSecrets, setConfiguredSecrets] = useState<Record<string, boolean>>({});
  const [editingSecrets, setEditingSecrets] = useState<Record<string, boolean>>({});
  const [validatingCredentials, setValidatingCredentials] = useState(false);
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedOperationalConfigRef = useRef("");
  const activeWorkspace = resolveWorkspaceSummary(workspaces, activeWorkspaceId);
  const activeWorkspaceRole = activeWorkspace?.role ?? "";
  const canManageActiveWorkspace = isWorkspaceAdminRole(activeWorkspaceRole);
  const canManageWorkspaceMembers = isWorkspaceOwnerRole(activeWorkspaceRole);
  const canCreateWorkspaces = adminSession?.role === "admin";

  function clearWorkspaceManagementState() {
    setConfig(null);
    setConfiguredSecrets({});
    setEditingSecrets({});
    setAuditLog([]);
    setUsers([]);
    setInvites([]);
    setCredentialValidationResults([]);
    setCredentialNotice(null);
    setTelegramTestFeedback(null);
    setMissedSignalDiagnostic(null);
    setMissedSignalError(null);
    setUsersLoading(false);
    lastSavedOperationalConfigRef.current = "";
    setAutoSaveStatus("idle");
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
      autoSaveTimerRef.current = null;
    }
  }

  const initializeStoredSession = useEffectEvent(async (storedToken: string) => {
    await applyAuthenticatedState(storedToken);
    setLoading(false);
  });

  useEffect(() => {
    void (async () => {
      const storedToken = getStoredAuthToken();
      setAdminToken(storedToken);
      setActiveWorkspaceId(getStoredWorkspaceId());

      if (!storedToken) {
        setLoading(false);
        return;
      }

      await initializeStoredSession(storedToken);
    })();
  }, []);

  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    setPairResultsLimit(40);
  }, [pairCatalogView, pairAvailabilityFilter, pairSearch, activeWorkspaceId]);

  function syncSessionState(session: AdminSessionInfo): string {
    const storedWorkspaceId = getStoredWorkspaceId();
    const resolvedWorkspaceId =
      storedWorkspaceId && session.workspaces.some((workspace) => workspace.id === storedWorkspaceId)
        ? storedWorkspaceId
        : session.workspaces[0]?.id || "";

    setAdminSession(session);
    setWorkspaces(session.workspaces);
    setActiveWorkspaceId(resolvedWorkspaceId);
    if (resolvedWorkspaceId) {
      setStoredWorkspaceId(resolvedWorkspaceId);
    }
    return resolvedWorkspaceId;
  }

  async function loadAdminWorkspaceData(token: string): Promise<AppConfig | null> {
    const workspaceId = getStoredWorkspaceId();
    if (!workspaceId) {
      clearWorkspaceManagementState();
      return null;
    }

    setUsersLoading(true);
    try {
      const [data, audit, workspaceUsers, workspaceInvites] = await Promise.all([
        getConfig(token),
        getAdminAuditLog(40, token),
        listUsers(token),
        listInvites(token),
      ]);
      setConfig(data.config);
      setConfiguredSecrets(data.configured_secrets);
      setEditingSecrets({});
      lastSavedOperationalConfigRef.current = serializeOperationalConfig(data.config);
      setAutoSaveStatus("idle");
      setAuditLog(audit);
      setUsers(workspaceUsers);
      setInvites(workspaceInvites);
      setAuthError(null);
      return data.config;
    } catch (error) {
      clearWorkspaceManagementState();
      setAuthError(error instanceof Error ? error.message : "Falha ao carregar dados administrativos");
      return null;
    } finally {
      setUsersLoading(false);
    }
  }

  async function loadAvailablePairsCatalog(forceRefresh = false, enabledExchanges = config?.enabled_exchanges) {
    setPairCatalogLoading(true);
    try {
      const catalog = await getAvailablePairs({
        force_refresh: forceRefresh,
        enabled_exchanges: enabledExchanges,
      });
      setAvailablePairsCatalog(catalog);
      setPairCatalogError(null);
    } catch (error) {
      setPairCatalogError(error instanceof Error ? error.message : "Falha ao carregar pares disponíveis");
    } finally {
      setPairCatalogLoading(false);
    }
  }

  async function applyAuthenticatedState(token: string, sessionOverride?: AdminSessionInfo): Promise<boolean> {
    let session = sessionOverride;

    try {
      session = sessionOverride ?? (await getAdminSession(token));
    } catch (error) {
      clearSession();
      setAuthError(error instanceof Error ? error.message : "Falha ao autenticar");
      return false;
    }

    const resolvedWorkspaceId = syncSessionState(session);
    const resolvedWorkspace = resolveWorkspaceSummary(session.workspaces, resolvedWorkspaceId);
    setAuthError(null);

    if (isWorkspaceAdminRole(resolvedWorkspace?.role)) {
      const loadedConfig = await loadAdminWorkspaceData(token);
      await loadAvailablePairsCatalog(false, loadedConfig?.enabled_exchanges);
    } else {
      clearWorkspaceManagementState();
    }

    return true;
  }

  function clearSession() {
    clearStoredSession();
    setAdminToken("");
    setConfig(null);
    setAdminSession(null);
    setAuditLog([]);
    setWorkspaces([]);
    setUsers([]);
    setInvites([]);
    setAvailablePairsCatalog(null);
    setActiveWorkspaceId("");
    setConfiguredSecrets({});
    setEditingSecrets({});
    setAuthError(null);
    setPairCatalogError(null);
    setTelegramTestFeedback(null);
    setCredentialValidationResults([]);
    setPassword("");
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setCredentialNotice(null);
    setPairSearch("");
    setManualPairInput("");
    setManualPairFeedback(null);
    setMissedSignalPairInput("");
    setMissedSignalDiagnostic(null);
    setMissedSignalError(null);
    setPairCatalogView("active");
    setPairAvailabilityFilter("active_exchanges");
    setPairResultsLimit(40);
    setAutoSaveStatus("idle");
    lastSavedOperationalConfigRef.current = "";
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
      autoSaveTimerRef.current = null;
    }
    setInviteEmail("");
    setInviteRole("member");
    setInviteExpiryDays("7");
  }

  useEffect(() => {
    if (!config || !canManageActiveWorkspace || !adminToken) {
      return;
    }

    const currentSnapshot = serializeOperationalConfig(config);
    if (currentSnapshot === lastSavedOperationalConfigRef.current) {
      return;
    }

    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }

    autoSaveTimerRef.current = setTimeout(() => {
      setAutoSaveStatus("saving");
      void updateConfig(buildOperationalConfigPayload(config), adminToken, { skipAudit: true })
        .then((updated) => {
          setConfiguredSecrets(updated.configured_secrets);
          lastSavedOperationalConfigRef.current = serializeOperationalConfig(updated.config);
          setAutoSaveStatus("saved");
          setAuthError(null);
          window.setTimeout(() => {
            setAutoSaveStatus((current) => (current === "saved" ? "idle" : current));
          }, 1600);
        })
        .catch((error) => {
          setAutoSaveStatus("error");
          setAuthError(error instanceof Error ? error.message : "Falha ao salvar configuração operacional");
        });
    }, OPERATIONAL_CONFIG_AUTOSAVE_DELAY_MS);

    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, [adminToken, canManageActiveWorkspace, config]);

  async function handleUnlock() {
    if (!adminToken) {
      setAuthError("Informe o token administrativo.");
      return;
    }

    setLoading(true);
    const ok = await applyAuthenticatedState(adminToken);
    if (ok) {
      setStoredAuthToken(adminToken);
      clearStoredRefreshToken();
    }
    setLoading(false);
  }

  async function handleCredentialLogin() {
    if (!username || !password) {
      setAuthError("Informe usuário e senha administrativos.");
      return;
    }

    setLoading(true);
    try {
      const response = await adminLogin(username, password);
      setStoredAuthToken(response.access_token);
      setStoredRefreshToken(response.refresh_token);
      setAdminToken(response.access_token);
      await applyAuthenticatedState(response.access_token, response.session);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao autenticar");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!config || !canManageActiveWorkspace) return;

    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
      autoSaveTimerRef.current = null;
    }

    setSaving(true);
    try {
      const configSnapshot = { ...config };
      const updated = await updateConfig(configSnapshot, adminToken);
      setConfig(updated.config);
      setConfiguredSecrets(updated.configured_secrets);
      setEditingSecrets({});
      lastSavedOperationalConfigRef.current = serializeOperationalConfig(updated.config);
      setAuthError(null);
      setSaved(true);
      setAutoSaveStatus("saved");
      await handleValidateExchangeCredentials(configSnapshot);
      window.setTimeout(() => setSaved(false), 2000);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao salvar configuração");
    } finally {
      setSaving(false);
    }
  }

  async function handleChangePassword() {
    if (!adminToken) {
      setAuthError("Sessão autenticada ausente.");
      return;
    }
    if (!currentPassword || !newPassword) {
      setAuthError("Informe a senha atual e a nova senha.");
      return;
    }
    if (newPassword.length < 12) {
      setAuthError("A nova senha precisa ter pelo menos 12 caracteres.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setAuthError("A confirmação da nova senha não confere.");
      return;
    }

    setPasswordSaving(true);
    try {
      const response = await changeAdminPassword(currentPassword, newPassword, adminToken);
      setStoredAuthToken(response.access_token);
      setStoredRefreshToken(response.refresh_token);
      setAdminToken(response.access_token);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      await applyAuthenticatedState(response.access_token, response.session);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao trocar senha");
    } finally {
      setPasswordSaving(false);
    }
  }

  async function handleCreateWorkspace() {
    if (!adminToken || !newWorkspaceName.trim() || !canCreateWorkspaces) return;

    setCreatingWorkspace(true);
    try {
      const createdWorkspace = await createWorkspace(newWorkspaceName.trim(), adminToken);
      setStoredWorkspaceId(createdWorkspace.id);
      setActiveWorkspaceId(createdWorkspace.id);
      setNewWorkspaceName("");
      await applyAuthenticatedState(adminToken);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao criar workspace");
    } finally {
      setCreatingWorkspace(false);
    }
  }

  async function handleWorkspaceChange(workspaceId: string) {
    const workspace = resolveWorkspaceSummary(workspaces, workspaceId);

    setStoredWorkspaceId(workspaceId);
    setActiveWorkspaceId(workspaceId);
    setCredentialNotice(null);
    setPairCatalogView("active");
    setPairAvailabilityFilter("active_exchanges");
    setPairSearch("");

    if (adminToken && isWorkspaceAdminRole(workspace?.role)) {
      setLoading(true);
      await loadAdminWorkspaceData(adminToken);
      setLoading(false);
    } else {
      clearWorkspaceManagementState();
    }
  }

  async function handleCreateUser() {
    if (!adminToken || !canManageWorkspaceMembers) return;
    if (!newUserName.trim()) {
      setAuthError("Informe o usuário da nova conta.");
      return;
    }

    setUserActionId("create-user");
    try {
      const response = await createUser(
        {
          username: newUserName.trim(),
          temporary_password: newUserPassword.trim() || undefined,
          role: newUserRole,
        },
        adminToken,
      );
      setCredentialNotice({
        action: "Conta criada",
        username: response.user.username,
        temporaryPassword: response.temporary_password,
      });
      setNewUserName("");
      setNewUserPassword("");
      setNewUserRole("member");
      await loadAdminWorkspaceData(adminToken);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao criar usuário");
    } finally {
      setUserActionId(null);
    }
  }

  async function handleToggleUser(user: UserRecord) {
    if (!adminToken || !canManageWorkspaceMembers) return;

    setUserActionId(`toggle-${user.id}`);
    try {
      await updateUserActiveState(user.id, !user.is_active, adminToken);
      await loadAdminWorkspaceData(adminToken);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao atualizar usuário");
    } finally {
      setUserActionId(null);
    }
  }

  async function handleResetPassword(user: UserRecord) {
    if (!adminToken || !canManageWorkspaceMembers) return;

    setUserActionId(`reset-${user.id}`);
    try {
      const response = await resetUserPassword(user.id, adminToken);
      setCredentialNotice({
        action: "Senha redefinida",
        username: response.user.username,
        temporaryPassword: response.temporary_password,
      });
      await loadAdminWorkspaceData(adminToken);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao redefinir senha");
    } finally {
      setUserActionId(null);
    }
  }

  function buildInviteUrl(code: string) {
    if (typeof window === "undefined") return `/invite/${code}`;
    return `${window.location.origin}/invite/${code}`;
  }

  async function handleCreateInvite() {
    if (!adminToken || !canManageWorkspaceMembers) return;
    if (!inviteEmail.trim()) {
      setAuthError("Informe o email do convite.");
      return;
    }

    setCreatingInvite(true);
    try {
      await createInvite(
        {
          email: inviteEmail.trim(),
          role: inviteRole,
          expires_in_days: Number(inviteExpiryDays) || 7,
        },
        adminToken,
      );
      setInviteEmail("");
      setInviteRole("member");
      setInviteExpiryDays("7");
      await loadAdminWorkspaceData(adminToken);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao criar convite");
    } finally {
      setCreatingInvite(false);
    }
  }

  async function handleCopyInvite(code: string) {
    try {
      await navigator.clipboard.writeText(buildInviteUrl(code));
      setCopiedInviteCode(code);
      window.setTimeout(() => setCopiedInviteCode(""), 1500);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao copiar link do convite");
    }
  }

  function buildCredentialValidationPayload(currentConfig: AppConfig) {
    return {
      novadax_api_key: currentConfig.novadax_api_key || undefined,
      novadax_api_secret: currentConfig.novadax_api_secret || undefined,
      mb_api_key: currentConfig.mb_api_key || undefined,
      mb_api_secret: currentConfig.mb_api_secret || undefined,
      binance_api_key: currentConfig.binance_api_key || undefined,
      binance_api_secret: currentConfig.binance_api_secret || undefined,
    };
  }

  async function handleValidateExchangeCredentials(configOverride?: AppConfig) {
    const effectiveConfig = configOverride ?? config;
    if (!adminToken || !canManageActiveWorkspace || !effectiveConfig) return;

    setValidatingCredentials(true);
    try {
      const response = await validateExchangeCredentials(
        buildCredentialValidationPayload(effectiveConfig),
        adminToken,
      );
      setCredentialValidationResults(response.results);
      setAuthError(null);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao validar credenciais das exchanges");
    } finally {
      setValidatingCredentials(false);
    }
  }

  function toggleExchange(exchange: Exchange) {
    setConfig((current) => {
      if (!current) return current;

      const exchanges = current.enabled_exchanges.includes(exchange)
        ? current.enabled_exchanges.filter((item) => item !== exchange)
        : [...current.enabled_exchanges, exchange];

      const catalogPairs = availablePairsCatalog?.pairs ?? [];
      const pairs = catalogPairs.length
        ? current.enabled_pairs.filter((pair) => {
            const catalogEntry = catalogPairs.find((item) => item.pair === pair);
            if (!catalogEntry) {
              return true;
            }
            return exchanges.some((enabledExchange) => catalogEntry.availability[enabledExchange]);
          })
        : current.enabled_pairs;

      return {
        ...current,
        enabled_exchanges: exchanges,
        enabled_pairs: pairs,
      };
    });
  }

  function togglePair(pair: string) {
    if (!config) return;
    const pairs = config.enabled_pairs.includes(pair)
      ? config.enabled_pairs.filter((item) => item !== pair)
      : [...config.enabled_pairs, pair];
    setConfig({ ...config, enabled_pairs: pairs });
  }

  function normalizeManualPair(value: string): string {
    return value
      .trim()
      .toUpperCase()
      .replace(/[^A-Z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "");
  }

  function addManualPair() {
    if (!config) return;

    const pair = normalizeManualPair(manualPairInput);
    if (!/^[A-Z0-9]{2,15}_[A-Z0-9]{2,10}$/.test(pair)) {
      setManualPairFeedback("Use o formato BASE_COTACAO, por exemplo SOL_BRL, WBTC_BRL ou BTC_USDT.");
      return;
    }

    if (config.enabled_pairs.includes(pair)) {
      setManualPairFeedback(`${pair.replace("_", "/")} ja esta ativo neste workspace.`);
      return;
    }

    const catalogEntry = pairCatalog.find((item) => item.pair === pair);
    const hasEnabledExchange = catalogEntry
      ? config.enabled_exchanges.some((exchange) => catalogEntry.availability[exchange])
      : true;

    setConfig({ ...config, enabled_pairs: [...config.enabled_pairs, pair] });
    setManualPairInput("");
    setManualPairFeedback(
      catalogEntry && !hasEnabledExchange
        ? `${pair.replace("_", "/")} foi adicionado, mas nao aparece disponivel nas exchanges ativas. Ative a exchange correta antes do scan.`
        : `${pair.replace("_", "/")} adicionado. Se o par nao existir na exchange ativa, o scanner vai ignorar/falhar sem bloquear os demais.`,
    );
  }

  async function diagnosePair() {
    const pair = normalizeManualPair(diagnosticPairInput || manualPairInput);
    if (!/^[A-Z0-9]{2,20}_[A-Z0-9]{2,10}$/.test(pair)) {
      setPairDiagnosticError("Informe um par no formato BASE_COTACAO, por exemplo LAB_BRL ou TON_BRL.");
      return;
    }

    setPairDiagnosticLoading(true);
    setPairDiagnosticError(null);
    try {
      const diagnostic = await getPairDiagnostic(diagnosticExchange, pair);
      setPairDiagnostic(diagnostic);
      setDiagnosticPairInput(pair);
    } catch (error) {
      setPairDiagnostic(null);
      setPairDiagnosticError(error instanceof Error ? error.message : "Falha ao diagnosticar o par.");
    } finally {
      setPairDiagnosticLoading(false);
    }
  }

  async function diagnoseMissedSignal() {
    const pair = normalizeManualPair(missedSignalPairInput || diagnosticPairInput || manualPairInput);
    if (!/^[A-Z0-9]{2,20}_[A-Z0-9]{2,10}$/.test(pair)) {
      setMissedSignalError("Informe um par no formato BASE_COTACAO, por exemplo SOL_BRL ou WBTC_BRL.");
      return;
    }

    let to = new Date();
    let from: Date;
    if (missedSignalWindowHours === "custom") {
      from = new Date(missedSignalCustomFrom);
      to = missedSignalCustomTo ? new Date(missedSignalCustomTo) : to;
      if (Number.isNaN(from.getTime()) || Number.isNaN(to.getTime()) || from >= to) {
        setMissedSignalError("Informe um periodo customizado valido, com inicio anterior ao fim.");
        return;
      }
    } else {
      const windowHours = Number(missedSignalWindowHours) || 24;
      from = new Date(to.getTime() - windowHours * 60 * 60 * 1000);
    }

    setMissedSignalLoading(true);
    setMissedSignalError(null);
    try {
      const diagnostic = await getMissedSignalDiagnostic({
        exchange: missedSignalExchange,
        pair,
        from: from.toISOString(),
        to: to.toISOString(),
      });
      setMissedSignalDiagnostic(diagnostic);
      setMissedSignalPairInput(pair);
    } catch (error) {
      setMissedSignalDiagnostic(null);
      setMissedSignalError(error instanceof Error ? error.message : "Falha ao buscar auditoria do sinal.");
    } finally {
      setMissedSignalLoading(false);
    }
  }

  function toggleShow(field: string) {
    setShowSecrets((prev) => ({ ...prev, [field]: !prev[field] }));
  }

  function toggleSecretEditing(field: SensitiveField) {
    setEditingSecrets((current) => {
      const nextEditing = !current[field];
      if (!nextEditing && config?.[field] === "") {
        return { ...current, [field]: false };
      }
      return { ...current, [field]: nextEditing };
    });
  }

  async function handleTelegramTest() {
    if (!adminToken || !canManageActiveWorkspace || !config) return;

    setTelegramTesting(true);
    setTelegramTestFeedback(null);

    try {
      await sendTelegramTestMessage(
        {
          telegram_bot_token: config.telegram_bot_token || undefined,
          telegram_chat_id: config.telegram_chat_id || undefined,
        },
        adminToken,
      );
      setTelegramTestFeedback({
        kind: "success",
        message: "Mensagem de teste enviada. Verifique o chat configurado no Telegram.",
      });
    } catch (error) {
      setTelegramTestFeedback({
        kind: "error",
        message: error instanceof Error ? error.message : "Falha ao enviar teste do Telegram",
      });
    } finally {
      setTelegramTesting(false);
    }
  }

  const deferredPairSearch = useDeferredValue(pairSearch);
  const pairCatalog = availablePairsCatalog?.pairs?.length
    ? availablePairsCatalog.pairs
    : FALLBACK_AVAILABLE_PAIRS;
  const discoveredPairs = new Set(pairCatalog.map((item) => item.pair));
  const activePairSet = new Set(config?.enabled_pairs ?? []);
  const enabledExchangeSet = new Set(config?.enabled_exchanges ?? []);
  const activeTradingPreset = config ? TRADING_PROFILE_PRESETS[config.trading_profile] : null;
  const normalizedPairSearch = deferredPairSearch.trim().toUpperCase();
  const pairCatalogEntries: PairCatalogEntry[] = [...pairCatalog]
    .map((item) => {
      const availableExchangeCount = ALL_EXCHANGES.reduce(
        (count, exchange) => count + (item.availability[exchange.id] ? 1 : 0),
        0,
      );
      const enabledExchangeMatches = ALL_EXCHANGES.reduce(
        (count, exchange) =>
          count + (enabledExchangeSet.has(exchange.id) && item.availability[exchange.id] ? 1 : 0),
        0,
      );

      return {
        ...item,
        isActive: activePairSet.has(item.pair),
        availableExchangeCount,
        enabledExchangeMatches,
      };
    })
    .sort((left, right) => {
      if (left.isActive !== right.isActive) {
        return left.isActive ? -1 : 1;
      }
      if (left.enabledExchangeMatches !== right.enabledExchangeMatches) {
        return right.enabledExchangeMatches - left.enabledExchangeMatches;
      }
      if (left.availableExchangeCount !== right.availableExchangeCount) {
        return right.availableExchangeCount - left.availableExchangeCount;
      }
      return left.display_name.localeCompare(right.display_name, "pt-BR");
    });
  const activePairRecords = pairCatalogEntries.filter((item) => item.isActive);
  const filteredPairCatalog = pairCatalogEntries.filter((item) => {
    const matchesSearch =
      !normalizedPairSearch ||
      item.pair.includes(normalizedPairSearch) ||
      item.display_name.toUpperCase().includes(normalizedPairSearch);
    const matchesAvailability =
      pairAvailabilityFilter === "all"
        ? true
        : pairAvailabilityFilter === "active_exchanges"
          ? item.enabledExchangeMatches > 0
          : item.availability[pairAvailabilityFilter];

    return matchesSearch && matchesAvailability;
  });
  const visibleFilteredPairCatalog = filteredPairCatalog.slice(0, pairResultsLimit);
  const hasMoreFilteredPairs = filteredPairCatalog.length > pairResultsLimit;
  const configuredLegacyPairs = config
    ? config.enabled_pairs.filter((pair) => !discoveredPairs.has(pair)).sort((left, right) => left.localeCompare(right))
    : [];
  const enabledExchangeColumns = config
    ? ALL_EXCHANGES.filter(({ id }) => config.enabled_exchanges.includes(id))
    : ALL_EXCHANGES;
  const catalogExchangeColumns =
    pairCatalogView === "discover" && pairAvailabilityFilter === "active_exchanges"
      ? enabledExchangeColumns
      : ALL_EXCHANGES;
  const visibleAuditLog = collapseAuditLogEntries(auditLog);
  const autoSaveMessage =
    autoSaveStatus === "saving"
      ? "Salvando filtros, pares e exchanges..."
      : autoSaveStatus === "saved"
        ? "Configuração operacional salva automaticamente."
        : autoSaveStatus === "error"
          ? "Falha ao salvar a configuração operacional."
          : "Filtros, pares, exchanges e intervalo salvam automaticamente.";

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!adminSession) {
    return (
      <div className="mx-auto max-w-xl space-y-6 p-4 pt-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Lock className="h-4 w-4" />
              Acesso administrativo
            </CardTitle>
            <CardDescription>
              Esta área exige uma sessão autenticada via credenciais ou o fallback legado com `ADMIN_TOKEN`.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <Input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Usuário ou e-mail admin"
              />
              <Input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Senha admin"
              />
            </div>
            <Button onClick={handleCredentialLogin} className="gap-2">
              <Lock className="h-4 w-4" />
              Login por credenciais
            </Button>

            <Separator />

            <div className="space-y-2">
              <p className="text-sm font-medium">Fallback com token manual</p>
              <div className="flex gap-2">
                <Input
                  type="password"
                  value={adminToken}
                  onChange={(event) => setAdminToken(event.target.value)}
                  placeholder="Cole o token administrativo"
                  className="font-mono"
                />
                <Button onClick={handleUnlock} className="gap-2">
                  <KeyRound className="h-4 w-4" />
                  Entrar
                </Button>
              </div>
            </div>
            {authError ? (
              <div
                className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-500"
                data-testid="settings-auth-error"
              >
                {authError}
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 pt-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{canManageActiveWorkspace ? "Configurações" : "Minha sessão"}</h1>
          <p className="text-sm text-muted-foreground">
            {canManageActiveWorkspace
              ? "Ajuste parâmetros operacionais, gerencie usuários e mantenha a sessão autenticada sem expor segredos."
              : "Use esta área para trocar a senha temporária e acompanhar os workspaces aos quais você tem acesso."}
          </p>
          {canManageActiveWorkspace ? (
            <p className={cn(
              "mt-1 text-xs",
              autoSaveStatus === "error" ? "text-red-500" : "text-muted-foreground",
            )}>
              {autoSaveMessage}
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={clearSession} className="gap-2">
            <LogOut className="h-4 w-4" />
            Sair
          </Button>
          {canManageActiveWorkspace && config ? (
            <Button onClick={handleSave} disabled={saving} className="gap-2" data-testid="settings-save-button">
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : saved ? (
                <Check className="h-4 w-4" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              {saved ? "Salvo" : "Salvar"}
            </Button>
          ) : null}
        </div>
      </div>

      {authError ? (
        <div
          className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-500"
          data-testid="settings-auth-error"
        >
          {authError}
        </div>
      ) : null}

      {adminSession.must_change_password ? (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-300">
          Esta conta está usando uma senha temporária. Troque a senha agora para encerrar o fluxo de primeiro acesso.
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base font-semibold">
            <ShieldCheck className="h-4 w-4" />
            Sessão autenticada
          </CardTitle>
          <CardDescription>
            {canManageActiveWorkspace
              ? "Sessão com refresh token de longa duração e revogação por token_version."
              : "Sessão vinculada aos workspaces liberados para sua conta."}
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
          <MetaCard label="Usuário" value={adminSession.username} />
          <MetaCard label="Email" value={adminSession.email || "Não informado"} />
          <MetaCard label="Modo" value={adminSession.auth_mode} />
          <MetaCard label="Role da conta" value={adminSession.role} />
          <MetaCard label="Role no workspace" value={activeWorkspaceRole || "Não definido"} />
          <MetaCard
            label="Última troca"
            value={
              adminSession.password_last_changed_at
                ? new Date(adminSession.password_last_changed_at).toLocaleString("pt-BR")
                : "Não registrada"
            }
          />
        </CardContent>
      </Card>

      {adminSession.organization ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Building2 className="h-4 w-4" />
              Organização
            </CardTitle>
            <CardDescription>
              A organização concentra billing, convites e os workspaces vinculados a esta conta.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <MetaCard label="Nome" value={adminSession.organization.name} />
            <MetaCard label="Status" value={adminSession.organization.subscription_status} />
            <MetaCard label="Plano" value={adminSession.organization.plan} />
            <MetaCard
              label="Trial ate"
              value={
                adminSession.organization.trial_ends_at
                  ? new Date(adminSession.organization.trial_ends_at).toLocaleDateString("pt-BR")
                  : "Não definido"
              }
            />
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Workspace ativo</CardTitle>
          <CardDescription>
            {canManageActiveWorkspace
              ? "Cada workspace tem configuração, auditoria e usuários isolados."
              : "Os dados do dashboard e histórico seguem o workspace selecionado aqui."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {workspaces.map((workspace) => (
              <Badge
                key={workspace.id}
                data-testid={`settings-workspace-${workspace.id}`}
                variant={workspace.id === activeWorkspaceId ? "default" : "outline"}
                className="cursor-pointer select-none"
                onClick={() => handleWorkspaceChange(workspace.id)}
              >
                {workspace.name}
              </Badge>
            ))}
          </div>
          {canCreateWorkspaces ? (
            <div className="flex gap-2">
              <Input
                value={newWorkspaceName}
                onChange={(event) => setNewWorkspaceName(event.target.value)}
                placeholder="Novo workspace"
              />
              <Button onClick={handleCreateWorkspace} disabled={creatingWorkspace} className="gap-2">
                {creatingWorkspace ? <Loader2 className="h-4 w-4 animate-spin" /> : <FolderPlus className="h-4 w-4" />}
                Criar
              </Button>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Segurança</CardTitle>
          <CardDescription>
            {adminSession.must_change_password
              ? "Troque a senha temporária para liberar o acesso normal da conta."
              : "Troque a senha para revogar tokens anteriores e encerrar qualquer sessão antiga."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <Input
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              placeholder="Senha atual"
            />
            <Input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="Nova senha"
            />
            <Input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Confirmar nova senha"
            />
          </div>
          <Button onClick={handleChangePassword} disabled={passwordSaving} className="gap-2">
            {passwordSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}
            Atualizar senha
          </Button>
        </CardContent>
      </Card>

      {canManageWorkspaceMembers ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <MailPlus className="h-4 w-4" />
              Convites do workspace
            </CardTitle>
            <CardDescription>
              Gere links de autocadastro para entrar direto no workspace ativo dentro da organização atual.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-[minmax(0,1.6fr),minmax(0,0.9fr),minmax(0,0.7fr),auto] md:items-center">
              <Input
                value={inviteEmail}
                onChange={(event) => setInviteEmail(event.target.value)}
                placeholder="Email do convidado"
              />
              <select
                value={inviteRole}
                onChange={(event) => setInviteRole(event.target.value)}
                className="h-9 rounded-lg border bg-background px-3 text-sm"
              >
                <option value="member">Membro</option>
                <option value="admin">Admin</option>
              </select>
              <Input
                type="number"
                min={1}
                max={30}
                value={inviteExpiryDays}
                onChange={(event) => setInviteExpiryDays(event.target.value)}
                placeholder="Dias"
              />
              <Button
                onClick={handleCreateInvite}
                disabled={creatingInvite}
                className="w-full gap-2 md:w-auto md:justify-self-start"
                data-testid="settings-create-invite-button"
              >
                {creatingInvite ? <Loader2 className="h-4 w-4 animate-spin" /> : <MailPlus className="h-4 w-4" />}
                Criar convite
              </Button>
            </div>

            <div className="space-y-3">
              {invites.length === 0 ? (
                <div className="rounded-xl border border-dashed p-4 text-sm text-muted-foreground">
                  Nenhum convite gerado para o workspace ativo.
                </div>
              ) : (
                invites.map((invite) => (
                  <div key={invite.id} className="rounded-xl border p-4">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold">{invite.email}</p>
                          <Badge variant={invite.status === "pending" ? "default" : "outline"}>{invite.status}</Badge>
                          <Badge variant="outline">{invite.role}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Criado em {new Date(invite.created_at).toLocaleString("pt-BR")} • expira em{" "}
                          {new Date(invite.expires_at).toLocaleString("pt-BR")}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Link: <span className="font-mono">{buildInviteUrl(invite.code)}</span>
                        </p>
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => handleCopyInvite(invite.code)}
                        className="gap-2"
                      >
                        <Copy className="h-3.5 w-3.5" />
                        {copiedInviteCode === invite.code ? "Copiado" : "Copiar link"}
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {canManageWorkspaceMembers ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Users className="h-4 w-4" />
              Usuários do workspace
            </CardTitle>
            <CardDescription>
              Contas criadas aqui entram no workspace ativo com senha temporária e podem ser desativadas ou redefinidas.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {credentialNotice ? (
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">
                  {credentialNotice.action}: {credentialNotice.username}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Entregue esta senha apenas ao usuário final. Ela deixa de valer quando a conta troca a senha ou for redefinida novamente.
                </p>
                <div className="mt-3 rounded-lg bg-muted/60 p-3 font-mono text-sm">
                  {credentialNotice.temporaryPassword}
                </div>
              </div>
            ) : null}

            <div className="grid gap-3 md:grid-cols-[minmax(0,1.6fr),minmax(0,1.6fr),minmax(0,0.9fr),auto] md:items-center">
              <Input
                value={newUserName}
                onChange={(event) => setNewUserName(event.target.value)}
                placeholder="Novo usuário"
              />
              <Input
                value={newUserPassword}
                onChange={(event) => setNewUserPassword(event.target.value)}
                placeholder="Senha temporária (opcional)"
              />
              <select
                value={newUserRole}
                onChange={(event) => setNewUserRole(event.target.value)}
                className="h-9 rounded-lg border bg-background px-3 text-sm"
              >
                <option value="member">Membro</option>
                <option value="admin">Admin</option>
              </select>
              <Button
                onClick={handleCreateUser}
                disabled={userActionId === "create-user"}
                className="w-full gap-2 md:w-auto md:justify-self-start"
                data-testid="settings-create-user-button"
              >
                {userActionId === "create-user" ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
                Criar usuário
              </Button>
            </div>

            <div className="overflow-hidden rounded-xl border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Usuário</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Senha</TableHead>
                    <TableHead>Atualização</TableHead>
                    <TableHead className="text-right">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {usersLoading ? (
                    Array.from({ length: 4 }).map((_, index) => (
                      <TableRow key={index}>
                        {Array.from({ length: 6 }).map((__, cellIndex) => (
                          <TableCell key={cellIndex}>
                            <div className="h-4 w-full animate-pulse rounded bg-muted" />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  ) : users.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="py-6 text-center text-sm text-muted-foreground">
                        Nenhum usuário vinculado ao workspace ativo.
                      </TableCell>
                    </TableRow>
                  ) : (
                    users.map((user) => {
                      const isSelf = user.id === adminSession.user_id;
                      const toggleActionId = `toggle-${user.id}`;
                      const resetActionId = `reset-${user.id}`;

                      return (
                        <TableRow key={user.id}>
                          <TableCell>
                            <div>
                              <p className="font-medium">{user.username}</p>
                              <p className="text-xs text-muted-foreground">
                                {user.email ? `${user.email} • ` : ""}token v{user.token_version}
                              </p>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant={user.role === "admin" ? "default" : "outline"}>{user.role}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={user.is_active ? "default" : "destructive"}>
                              {user.is_active ? "ativo" : "inativo"}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={user.must_change_password ? "secondary" : "outline"}>
                              {user.must_change_password ? "temporaria" : "ok"}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {user.updated_at ? new Date(user.updated_at).toLocaleString("pt-BR") : "-"}
                          </TableCell>
                          <TableCell>
                            <div className="flex justify-end gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleResetPassword(user)}
                                disabled={userActionId === toggleActionId || userActionId === resetActionId}
                                className="gap-2"
                              >
                                {userActionId === resetActionId ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCcw className="h-3.5 w-3.5" />}
                                Resetar
                              </Button>
                              <Button
                                size="sm"
                                variant={user.is_active ? "destructive" : "outline"}
                                onClick={() => handleToggleUser(user)}
                                disabled={isSelf || userActionId === toggleActionId || userActionId === resetActionId}
                              >
                                {userActionId === toggleActionId ? (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : user.is_active ? (
                                  "Desativar"
                                ) : (
                                  "Reativar"
                                )}
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {canManageActiveWorkspace && config ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Perfil operacional</CardTitle>
              <CardDescription>
                Define quando um sinal deixa de ser apenas interessante e passa a ser operavel para o tamanho de ordem escolhido.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <SettingRow
                label="Perfil de trading"
                description={TRADING_PROFILE_OPTIONS.find((item) => item.value === config.trading_profile)?.description ?? "Perfil usado para calibrar o scanner."}
              >
                <select
                  value={config.trading_profile}
                  onChange={(event) => {
                    const nextProfile = event.target.value as TradingProfile;
                    setConfig({
                      ...config,
                      trading_profile: nextProfile,
                      ...TRADING_PROFILE_PRESETS[nextProfile],
                    });
                  }}
                  className="h-9 w-full max-w-56 rounded-lg border bg-background px-3 text-sm font-medium"
                >
                  {TRADING_PROFILE_OPTIONS.map((profile) => (
                    <option key={profile.value} value={profile.value}>
                      {profile.label}
                    </option>
                  ))}
                </select>
              </SettingRow>

              <Separator />

              <SettingRow
                label="Tamanho de ordem estimado (R$)"
                description="Valor usado para simular entrada e saida no livro de ordens"
              >
                <Input
                  data-testid="settings-order-notional"
                  type="number"
                  min={25}
                  step={25}
                  value={config.order_notional_brl ?? activeTradingPreset?.order_notional_brl ?? 1000}
                  onChange={(event) =>
                    setConfig({ ...config, order_notional_brl: Number(event.target.value) })
                  }
                  className="h-9 w-36 font-medium"
                />
              </SettingRow>

              <Separator />

              <SettingRow
                label="Volume notional minimo (R$/24h)"
                description="Descarta ativo com pouco volume para reduzir risco de ficar preso"
              >
                <Input
                  data-testid="settings-min-quote-volume"
                  type="number"
                  min={0}
                  step={500}
                  value={config.min_quote_volume_brl ?? activeTradingPreset?.min_quote_volume_brl ?? 3000}
                  onChange={(event) =>
                    setConfig({ ...config, min_quote_volume_brl: Number(event.target.value) })
                  }
                  className="h-9 w-36 font-medium"
                />
              </SettingRow>

              <Separator />

              <div className="grid gap-4 lg:grid-cols-2">
                <SettingRow
                  label="Slippage max. entrada (%)"
                  description="Tolerancia para comprar sem o preco escapar demais"
                >
                  <SliderInputControl
                    testId="settings-entry-slippage"
                    value={(config.max_entry_slippage_bps ?? activeTradingPreset?.max_entry_slippage_bps ?? 500) / 100}
                    min={0.1}
                    max={10}
                    step={0.1}
                    suffix="%"
                    onChange={(nextValue) =>
                      setConfig({ ...config, max_entry_slippage_bps: Math.round(nextValue * 100) })
                    }
                  />
                </SettingRow>

                <SettingRow
                  label="Slippage max. saida (%)"
                  description="Tolerancia para vender sem perder executabilidade"
                >
                  <SliderInputControl
                    testId="settings-exit-slippage"
                    value={(config.max_exit_slippage_bps ?? activeTradingPreset?.max_exit_slippage_bps ?? 500) / 100}
                    min={0.1}
                    max={10}
                    step={0.1}
                    suffix="%"
                    onChange={(nextValue) =>
                      setConfig({ ...config, max_exit_slippage_bps: Math.round(nextValue * 100) })
                    }
                  />
                </SettingRow>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Filtros e thresholds</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <SettingRow
                label="Volatilidade mínima (%)"
                description="Variação percentual mínima para considerar um sinal"
              >
                <SliderInputControl
                  testId="settings-threshold-volatility"
                  value={config.thresholds.min_volatility_pct}
                  min={0.5}
                  max={10}
                  step={0.1}
                  suffix="%"
                  onChange={(nextValue) =>
                    setConfig({
                      ...config,
                      thresholds: { ...config.thresholds, min_volatility_pct: nextValue },
                    })
                  }
                />
              </SettingRow>

              <Separator />

              <SettingRow
                label="Volume mínimo (grandes)"
                description="Volume em BRL para pares principais"
              >
                <Input
                  type="number"
                  value={config.thresholds.min_volume_brl}
                  onChange={(event) =>
                    setConfig({
                      ...config,
                      thresholds: {
                        ...config.thresholds,
                        min_volume_brl: Number(event.target.value),
                      },
                    })
                  }
                  className="h-9 w-36 font-medium"
                />
              </SettingRow>

              <Separator />

              <SettingRow
                label="Volume mínimo (altcoins)"
                description="Volume em BRL para altcoins"
              >
                <Input
                  type="number"
                  value={config.thresholds.min_volume_brl_small}
                  onChange={(event) =>
                    setConfig({
                      ...config,
                      thresholds: {
                        ...config.thresholds,
                        min_volume_brl_small: Number(event.target.value),
                      },
                    })
                  }
                  className="h-9 w-36 font-medium"
                />
              </SettingRow>

              <Separator />

              <SettingRow
                label="Liquidez mínima (unidades)"
                description="Quantidade mínima no livro de ordens"
              >
                <Input
                  type="number"
                  value={config.thresholds.min_liquidity_units}
                  onChange={(event) =>
                    setConfig({
                      ...config,
                      thresholds: {
                        ...config.thresholds,
                        min_liquidity_units: Number(event.target.value),
                      },
                    })
                  }
                  className="h-9 w-36 font-medium"
                />
              </SettingRow>

              <Separator />

              <SettingRow
                label="Spread máximo (%)"
                description="Spread máximo entre compra e venda"
              >
                <SliderInputControl
                  testId="settings-threshold-spread"
                  value={config.thresholds.max_spread_pct}
                  min={0.1}
                  max={5}
                  step={0.1}
                  suffix="%"
                  onChange={(nextValue) =>
                    setConfig({
                      ...config,
                      thresholds: { ...config.thresholds, max_spread_pct: nextValue },
                    })
                  }
                />
              </SettingRow>
            </CardContent>
          </Card>

          {/*
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Perfil operacional</CardTitle>
              <CardDescription>
                Ajusta o tamanho de ordem, limites de slippage, persistência mínima e os filtros de alerta por workspace.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <SettingRow
                label="Perfil de trading"
                description="Preset base para operabilidade e filtros de execução"
              >
                <Select
                  value={config.trading_profile}
                  onValueChange={(value) =>
                    setConfig({
                      ...config,
                      trading_profile: (value as AppConfig["trading_profile"]) ?? "intraday_liquido",
                    })
                  }
                >
                  <SelectTrigger className="h-9 w-60">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="conservador">Conservador</SelectItem>
                    <SelectItem value="intraday_liquido">Intraday líquido</SelectItem>
                    <SelectItem value="agressivo">Agressivo</SelectItem>
                    <SelectItem value="scalp">Scalp</SelectItem>
                  </SelectContent>
                </Select>
              </SettingRow>

              <Separator />

              <SettingRow
                label="Notional por ordem (BRL)"
                description="Tamanho base usado para estimar slippage e operabilidade"
              >
                <Input
                  type="number"
                  value={config.order_notional_brl ?? ""}
                  onChange={(event) =>
                    setConfig({ ...config, order_notional_brl: Number(event.target.value) || null })
                  }
                  className="h-9 w-40 font-medium"
                />
              </SettingRow>

              <Separator />

              <SettingRow
                label="Slippage máximo de entrada (bps)"
                description="Limite aceitável para o lado comprador"
              >
                <Input
                  type="number"
                  value={config.max_entry_slippage_bps ?? ""}
                  onChange={(event) =>
                    setConfig({ ...config, max_entry_slippage_bps: Number(event.target.value) || null })
                  }
                  className="h-9 w-40 font-medium"
                />
              </SettingRow>

              <Separator />

              <SettingRow
                label="Slippage máximo de saída (bps)"
                description="Limite aceitável para o lado vendedor"
              >
                <Input
                  type="number"
                  value={config.max_exit_slippage_bps ?? ""}
                  onChange={(event) =>
                    setConfig({ ...config, max_exit_slippage_bps: Number(event.target.value) || null })
                  }
                  className="h-9 w-40 font-medium"
                />
              </SettingRow>

              <Separator />

              <SettingRow
                label="Volume mínimo do perfil (BRL)"
                description="Filtro adicional para volume de quote além dos thresholds gerais"
              >
                <Input
                  type="number"
                  value={config.min_quote_volume_brl ?? ""}
                  onChange={(event) =>
                    setConfig({ ...config, min_quote_volume_brl: Number(event.target.value) || null })
                  }
                  className="h-9 w-40 font-medium"
                />
              </SettingRow>

              <Separator />

              <SettingRow
                label="Somente operáveis no Telegram"
                description="Suprime alertas de sinais interessantes mas não executáveis"
              >
                <Switch
                  size="sm"
                  checked={!!config.telegram_operable_only}
                  onCheckedChange={(checked) => setConfig({ ...config, telegram_operable_only: checked })}
                />
              </SettingRow>

              <Separator />

              <SettingRow
                label="Mínimo de operabilidade no Telegram"
                description="Executability score mínimo para disparo de alertas"
              >
                <Input
                  type="number"
                  value={config.telegram_min_executability_score ?? ""}
                  onChange={(event) =>
                    setConfig({
                      ...config,
                      telegram_min_executability_score: Number(event.target.value) || null,
                    })
                  }
                  className="h-9 w-40 font-medium"
                />
              </SettingRow>
            </CardContent>
          </Card>
          */}

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr),22rem] xl:items-start">
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold">Pesos do score</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {(["volatility", "volume", "liquidity", "spread", "repetition"] as const).map(
                  (key) => {
                    const labels: Record<string, string> = {
                      volatility: "Volatilidade",
                      volume: "Volume",
                      liquidity: "Liquidez",
                      spread: "Spread",
                      repetition: "Repetição",
                    };

                    return (
                      <div
                        key={key}
                        className="grid gap-2 rounded-xl border bg-muted/15 p-3 md:grid-cols-[150px,minmax(0,1fr)] md:items-center md:gap-4"
                      >
                        <span className="text-sm font-medium">{labels[key]}</span>
                        <SliderInputControl
                          testId={`settings-weight-${key}`}
                          value={config.weights[key] * 100}
                          min={0}
                          max={50}
                          step={1}
                          suffix="%"
                          onChange={(nextValue) => {
                            setConfig({
                              ...config,
                              weights: { ...config.weights, [key]: nextValue / 100 },
                            });
                          }}
                        />
                      </div>
                    );
                  }
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold">Exchanges</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3">
                {ALL_EXCHANGES.map(({ id, label }) => (
                  <div key={id} className="flex items-center justify-between rounded-xl border bg-muted/15 px-3 py-3">
                    <span className="text-sm font-medium">{label}</span>
                    <Switch
                      size="sm"
                      checked={config.enabled_exchanges.includes(id)}
                      onCheckedChange={() => toggleExchange(id)}
                    />
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Watchlist de pares</CardTitle>
              <CardDescription>
                O scanner avalia o catalogo BRL das exchanges habilitadas. Esta lista destaca pares prioritarios e ajuda no diagnostico.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 rounded-xl border bg-muted/20 p-4 md:grid-cols-[minmax(0,1fr),220px] md:items-center">
                <div className="space-y-1">
                  <p className="text-sm font-semibold">Universo de monitoramento</p>
                  <p className="text-xs text-muted-foreground">
                    Use todos os pares BRL para descobrir oportunidades novas ou restrinja o scanner aos pares da watchlist.
                  </p>
                  {(config.pair_universe_mode ?? "all_brl") === "watchlist_only" && config.enabled_pairs.length === 0 ? (
                    <p className="text-xs text-amber-600 dark:text-amber-300">
                      Nenhum par na watchlist. Neste modo o scanner nao tera pares para avaliar.
                    </p>
                  ) : null}
                </div>
                <select
                  value={config.pair_universe_mode ?? "all_brl"}
                  onChange={(event) =>
                    setConfig({
                      ...config,
                      pair_universe_mode: event.target.value as AppConfig["pair_universe_mode"],
                    })
                  }
                  className="h-9 rounded-md border bg-background px-3 text-sm font-medium"
                >
                  <option value="all_brl">Todos os pares BRL</option>
                  <option value="watchlist_only">Apenas minha watchlist</option>
                </select>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant={pairCatalogView === "active" ? "secondary" : "ghost"}
                  onClick={() => setPairCatalogView("active")}
                >
                  Ativos ({activePairRecords.length})
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={pairCatalogView === "discover" ? "secondary" : "ghost"}
                  onClick={() => setPairCatalogView("discover")}
                >
                  Catálogo ({pairCatalog.length})
                </Button>
                <Badge variant="outline">
                  {config.enabled_exchanges.length} exchange{config.enabled_exchanges.length === 1 ? "" : "s"} habilitada{config.enabled_exchanges.length === 1 ? "" : "s"}
                </Badge>
                <Badge variant="outline">
                  {availablePairsCatalog?.generated_at
                    ? `Atualizado em ${new Date(availablePairsCatalog.generated_at).toLocaleString("pt-BR")}`
                    : "Usando fallback local"}
                </Badge>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => void loadAvailablePairsCatalog(true)}
                  disabled={pairCatalogLoading}
                  className="gap-2"
                >
                  {pairCatalogLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCcw className="h-3.5 w-3.5" />}
                  Atualizar catálogo
                </Button>
              </div>

              {pairCatalogError ? (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-700 dark:text-amber-300">
                  {pairCatalogError}
                </div>
              ) : null}

              {availablePairsCatalog?.provider_status?.length ? (
                <div className="grid gap-2 md:grid-cols-3">
                  {availablePairsCatalog.provider_status.map((providerStatus) => {
                    const exchangeLabel =
                      ALL_EXCHANGES.find((exchange) => exchange.id === providerStatus.exchange)?.label ??
                      providerStatus.exchange;
                    const statusLabel =
                      providerStatus.status === "ok"
                        ? "Catálogo OK"
                        : providerStatus.status === "empty"
                          ? "Sem pares retornados"
                          : providerStatus.status === "disabled"
                            ? "Desativada"
                            : providerStatus.status === "stale"
                              ? "Usando cache anterior"
                              : "Falha no catálogo";

                    return (
                      <div
                        key={providerStatus.exchange}
                        className={cn(
                          "rounded-xl border p-3 text-xs",
                          providerStatus.status === "ok"
                            ? "bg-emerald-500/5 text-emerald-700 dark:text-emerald-300"
                            : providerStatus.status === "disabled"
                              ? "bg-slate-500/5 text-slate-600 dark:text-slate-300"
                              : providerStatus.status === "stale"
                                ? "bg-blue-500/5 text-blue-700 dark:text-blue-300"
                              : "bg-amber-500/5 text-amber-700 dark:text-amber-300",
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-semibold">{exchangeLabel}</p>
                          <Badge variant={providerStatus.status === "ok" ? "default" : "outline"}>
                            {statusLabel}
                          </Badge>
                        </div>
                        <p className="mt-1 text-muted-foreground">
                          {providerStatus.returned_pairs} pares, {providerStatus.brl_pairs} BRL detectados.
                        </p>
                        {providerStatus.error_message ? (
                          <p className="mt-1 break-words text-muted-foreground">{providerStatus.error_message}</p>
                        ) : providerStatus.examples.length ? (
                          <p className="mt-1 truncate text-muted-foreground">
                            Exemplos: {providerStatus.examples.slice(0, 3).join(", ")}
                          </p>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              ) : null}

              <div className="rounded-xl border bg-muted/20 p-4">
                <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr),auto] lg:items-end">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold">Adicionar par manualmente</p>
                    <p className="text-xs text-muted-foreground">
                      Use quando o ativo existe na exchange, mas ainda nao apareceu no catalogo cacheado. A lista nao limita o dashboard; ela destaca pares para acompanhamento e diagnostico.
                    </p>
                    <Input
                      value={manualPairInput}
                      onChange={(event) => {
                        setManualPairInput(event.target.value);
                        setManualPairFeedback(null);
                      }}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          addManualPair();
                        }
                      }}
                      placeholder="Ex: SOL_BRL, WBTC_BRL, BTC_USDT"
                    />
                  </div>
                  <Button type="button" variant="outline" onClick={addManualPair} disabled={!manualPairInput.trim()}>
                    Adicionar par
                  </Button>
                </div>
                {manualPairFeedback ? (
                  <p className="mt-3 text-xs text-muted-foreground">{manualPairFeedback}</p>
                ) : null}
              </div>

              <div className="rounded-xl border bg-background p-4">
                <div className="grid gap-3 lg:grid-cols-[180px,minmax(0,1fr),auto] lg:items-end">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold">Diagnosticar par</p>
                    <select
                      value={diagnosticExchange}
                      onChange={(event) => setDiagnosticExchange(event.target.value as Exchange)}
                      className="h-9 w-full rounded-lg border bg-background px-3 text-sm"
                    >
                      {ALL_EXCHANGES.map(({ id, label }) => (
                        <option key={id} value={id}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <Input
                    value={diagnosticPairInput}
                    onChange={(event) => {
                      setDiagnosticPairInput(event.target.value);
                      setPairDiagnosticError(null);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        void diagnosePair();
                      }
                    }}
                    placeholder="Ex: LAB_BRL, TON_BRL"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void diagnosePair()}
                    disabled={pairDiagnosticLoading}
                    className="gap-2"
                  >
                    {pairDiagnosticLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Info className="h-3.5 w-3.5" />}
                    Diagnosticar
                  </Button>
                </div>

                {pairDiagnosticError ? (
                  <p className="mt-3 text-xs text-amber-600 dark:text-amber-300">{pairDiagnosticError}</p>
                ) : null}

                {pairDiagnostic ? (
                  <div className="mt-4 rounded-lg border bg-muted/20 p-3 text-xs">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="font-semibold">{pairDiagnostic.display_name} em {ALL_EXCHANGES.find((exchange) => exchange.id === pairDiagnostic.exchange)?.label ?? pairDiagnostic.exchange}</p>
                        <p className="text-muted-foreground">
                          Símbolo bruto: {pairDiagnostic.raw_symbol} · Catálogo: {pairDiagnostic.exists_in_catalog ? "encontrado" : "não encontrado"}
                        </p>
                      </div>
                      <Badge
                        variant={pairDiagnostic.overall_status === "ok" ? "default" : "outline"}
                        className={cn(
                          pairDiagnostic.overall_status === "error"
                            ? "border-amber-500/40 text-amber-700 dark:text-amber-300"
                            : "",
                        )}
                      >
                        {pairDiagnostic.overall_status === "ok"
                          ? "Operacional"
                          : pairDiagnostic.overall_status === "warning"
                            ? "Atenção"
                            : "Falha"}
                      </Badge>
                    </div>
                    <div className="mt-3 grid gap-2 md:grid-cols-4">
                      {pairDiagnostic.checks.map((check) => (
                        <div key={check.name} className="rounded-lg border bg-background p-2">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-medium">
                              {check.name === "order_book" ? "book" : check.name}
                            </span>
                            <Badge variant={check.status === "ok" ? "default" : "outline"}>
                              {check.status === "ok" ? "OK" : "Erro"}
                            </Badge>
                          </div>
                          {check.message ? (
                            <p className="mt-1 break-words text-muted-foreground">{check.message}</p>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>

              {configuredLegacyPairs.length > 0 ? (
                <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
                  <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
                    Pares ainda configurados, mas não encontrados no catálogo atual.
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Remova-os manualmente se o ativo mudou de ticker ou deixou de existir na exchange.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {configuredLegacyPairs.map((pair) => (
                      <Badge
                        key={pair}
                        variant="secondary"
                        className="cursor-pointer select-none font-semibold"
                        onClick={() => togglePair(pair)}
                      >
                        {pair.replace("_", "/")} • remover
                      </Badge>
                    ))}
                  </div>
                </div>
              ) : null}

              {pairCatalogView === "active" ? (
                activePairRecords.length === 0 ? (
                  <div className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
                    <p className="font-medium text-foreground">Nenhum par ativo neste workspace.</p>
                    <p className="mt-1">
                      Abra o catálogo para pesquisar ativos e adicionar apenas os pares que fazem sentido para a operação atual.
                    </p>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="mt-4"
                      onClick={() => setPairCatalogView("discover")}
                    >
                      Abrir catálogo
                    </Button>
                  </div>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {activePairRecords.map((pairRecord) => (
                      <div key={pairRecord.pair} className="rounded-xl border bg-muted/20 p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">{pairRecord.display_name}</p>
                            <p className="text-xs text-muted-foreground">{pairRecord.pair}</p>
                          </div>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => togglePair(pairRecord.pair)}
                          >
                            Remover
                          </Button>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {enabledExchangeColumns.map(({ id, label }) => (
                            <Badge key={id} variant={pairRecord.availability[id] ? "default" : "outline"}>
                              {label}
                            </Badge>
                          ))}
                        </div>
                        <p className="mt-3 text-xs text-muted-foreground">
                          Disponivel em {pairRecord.enabledExchangeMatches} exchange{pairRecord.enabledExchangeMatches === 1 ? "" : "s"} ativa{pairRecord.enabledExchangeMatches === 1 ? "" : "s"}.
                        </p>
                      </div>
                    ))}
                  </div>
                )
              ) : (
                <div className="space-y-4">
                  <div className="grid gap-3 xl:grid-cols-[minmax(0,1.3fr),240px,minmax(0,0.9fr)] xl:items-center">
                    <Input
                      value={pairSearch}
                      onChange={(event) => setPairSearch(event.target.value)}
                      placeholder="Buscar par por símbolo ou quote"
                    />
                    <select
                      value={pairAvailabilityFilter}
                      onChange={(event) => setPairAvailabilityFilter(event.target.value as PairAvailabilityFilter)}
                      className="h-9 rounded-lg border bg-background px-3 text-sm"
                    >
                      <option value="active_exchanges">Disponíveis nas exchanges ativas</option>
                      <option value="all">Todas as exchanges</option>
                      {ALL_EXCHANGES.map(({ id, label }) => (
                        <option key={id} value={id}>
                          Apenas {label}
                        </option>
                      ))}
                    </select>
                    <div className="text-xs text-muted-foreground xl:text-right">
                      {pairCatalogLoading
                        ? "Atualizando catálogo..."
                        : `Mostrando ${visibleFilteredPairCatalog.length} de ${filteredPairCatalog.length} pares neste filtro`}
                    </div>
                  </div>

                  <div className="rounded-lg border bg-muted/20 p-3 text-xs text-muted-foreground">
                    O catálogo completo fica paginado para evitar uma tabela gigante. Use a busca para chegar mais rápido ao ativo desejado e carregue mais resultados apenas quando precisar.
                  </div>

                  <div className="overflow-hidden rounded-xl border">
                    <ScrollArea className="h-[32rem]">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Par</TableHead>
                            {catalogExchangeColumns.map(({ id, label }) => (
                              <TableHead key={id}>{label}</TableHead>
                            ))}
                            <TableHead className="text-right">Seleção</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {pairCatalogLoading && !availablePairsCatalog ? (
                            Array.from({ length: 6 }).map((_, index) => (
                              <TableRow key={index}>
                                {Array.from({ length: catalogExchangeColumns.length + 2 }).map((__, cellIndex) => (
                                  <TableCell key={cellIndex}>
                                    <div className="h-4 w-full animate-pulse rounded bg-muted" />
                                  </TableCell>
                                ))}
                              </TableRow>
                            ))
                          ) : visibleFilteredPairCatalog.length === 0 ? (
                            <TableRow>
                              <TableCell colSpan={catalogExchangeColumns.length + 2} className="py-6 text-center text-sm text-muted-foreground">
                                Nenhum par encontrado para o filtro atual.
                              </TableCell>
                            </TableRow>
                          ) : (
                            visibleFilteredPairCatalog.map((pairRecord) => (
                              <TableRow key={pairRecord.pair}>
                                <TableCell>
                                  <div>
                                    <p className="font-medium">{pairRecord.display_name}</p>
                                    <p className="text-xs text-muted-foreground">{pairRecord.pair}</p>
                                  </div>
                                </TableCell>
                                {catalogExchangeColumns.map(({ id }) => (
                                  <TableCell key={id}>
                                    <div className="space-y-1">
                                      <Badge variant={pairRecord.availability[id] ? "default" : "outline"}>
                                        {pairRecord.availability[id] ? "Disponivel" : "-"}
                                      </Badge>
                                      {pairRecord.status?.[id] && pairRecord.status[id] !== "not_listed" ? (
                                        <p className="text-[11px] text-muted-foreground">
                                          {pairRecord.status[id] === "tradable"
                                            ? "Negociavel"
                                            : pairRecord.status[id] === "empty"
                                              ? "Catálogo vazio"
                                              : pairRecord.status[id] === "disabled"
                                                ? "Exchange desativada"
                                                : pairRecord.status[id] === "error"
                                                ? "Erro no provider"
                                                : pairRecord.status[id]}
                                        </p>
                                      ) : null}
                                      {pairRecord.error_message?.[id] ? (
                                        <p className="max-w-36 truncate text-[11px] text-amber-600 dark:text-amber-300">
                                          {pairRecord.error_message[id]}
                                        </p>
                                      ) : null}
                                    </div>
                                  </TableCell>
                                ))}
                                <TableCell className="text-right">
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant={pairRecord.isActive ? "default" : "outline"}
                                    onClick={() => togglePair(pairRecord.pair)}
                                  >
                                    {pairRecord.isActive ? "Ativo" : "Adicionar"}
                                  </Button>
                                </TableCell>
                              </TableRow>
                            ))
                          )}
                        </TableBody>
                      </Table>
                    </ScrollArea>
                  </div>

                  {hasMoreFilteredPairs ? (
                    <div className="flex justify-center">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setPairResultsLimit((current) => current + 40)}
                      >
                        Carregar mais 40 pares
                      </Button>
                    </div>
                  ) : null}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Geral</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <SettingRow
                label="Intervalo de varredura (seg)"
                description="Tempo entre cada ciclo de coleta"
              >
                <Input
                  data-testid="settings-scan-interval"
                  type="number"
                  value={config.scan_interval_seconds}
                  onChange={(event) =>
                    setConfig({ ...config, scan_interval_seconds: Number(event.target.value) })
                  }
                  className="h-9 w-36 font-medium"
                />
              </SettingRow>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Notificações Telegram</CardTitle>
              <CardDescription>
                Os valores sensíveis não são retornados pela API. Preencha apenas os campos que deseja atualizar.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold">Alertas ativos</p>
                  <p className="text-xs text-muted-foreground">Enviar notificações via bot</p>
                </div>
                <Switch
                  checked={config.telegram_enabled}
                  onCheckedChange={(value) => setConfig({ ...config, telegram_enabled: value })}
                />
              </div>

              <Separator />

              <SettingRow
                label="Score minimo para alerta"
                description="Permite receber sinais medios e bons sem depender apenas do ranking visual"
              >
                <SliderInputControl
                  testId="settings-telegram-threshold"
                  value={config.telegram_alert_threshold ?? 60}
                  min={20}
                  max={100}
                  step={5}
                  onChange={(nextValue) =>
                    setConfig({ ...config, telegram_alert_threshold: nextValue })
                  }
                />
              </SettingRow>

              <Separator />

              <SettingRow
                label="Cooldown por ativo (seg)"
                description="Evita spam repetido do mesmo par/exchange"
              >
                <Input
                  data-testid="settings-telegram-cooldown"
                  type="number"
                  min={0}
                  step={60}
                  value={config.telegram_alert_cooldown_seconds ?? 900}
                  onChange={(event) =>
                    setConfig({ ...config, telegram_alert_cooldown_seconds: Number(event.target.value) })
                  }
                  className="h-9 w-36 font-medium"
                />
              </SettingRow>

              <Separator />

              <SettingRow
                label="Limite diario de alertas"
                description="Quantidade maxima de alertas Telegram por workspace a cada dia UTC. Vazio remove o limite."
              >
                <Input
                  data-testid="settings-telegram-daily-limit"
                  type="number"
                  min={0}
                  step={1}
                  value={config.telegram_daily_alert_limit ?? ""}
                  onChange={(event) =>
                    setConfig({
                      ...config,
                      telegram_daily_alert_limit: event.target.value === "" ? null : Number(event.target.value),
                    })
                  }
                  className="h-9 w-36 font-medium"
                />
              </SettingRow>

              <Separator />

              <SettingRow
                label="Score minimo de operabilidade"
                description="Exige uma nota minima de executabilidade antes de disparar alertas"
              >
                <Input
                  data-testid="settings-telegram-min-exec"
                  type="number"
                  min={0}
                  max={100}
                  step={5}
                  value={config.telegram_min_executability_score ?? ""}
                  onChange={(event) =>
                    setConfig({
                      ...config,
                      telegram_min_executability_score: Number(event.target.value) || null,
                    })
                  }
                  className="h-9 w-36 font-medium"
                />
              </SettingRow>

              <Separator />

              <div className="space-y-3 rounded-xl border bg-muted/15 p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold">Enviar apenas sinais operaveis</p>
                    <p className="text-xs text-muted-foreground">
                      Mantem alertas focados em volume, liquidez, slippage e facilidade de saida.
                    </p>
                  </div>
                  <Switch
                    checked={!!config.telegram_operable_only}
                    onCheckedChange={(value) => setConfig({ ...config, telegram_operable_only: value })}
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  {[
                    { value: "operable", label: "Operaveis" },
                    { value: "high_score", label: "Score alto" },
                    { value: "arbitrage", label: "Arbitragem" },
                  ].map((alertType) => {
                    const active = (config.telegram_alert_types ?? []).includes(alertType.value);
                    return (
                      <Button
                        key={alertType.value}
                        type="button"
                        size="sm"
                        variant={active ? "secondary" : "outline"}
                        onClick={() => {
                          const nextTypes = active
                            ? (config.telegram_alert_types ?? []).filter((item) => item !== alertType.value)
                            : [...(config.telegram_alert_types ?? []), alertType.value];
                          setConfig({ ...config, telegram_alert_types: nextTypes });
                        }}
                      >
                        {alertType.label}
                      </Button>
                    );
                  })}
                </div>
              </div>

              <Separator />

              <div className="space-y-3">
                {(() => {
                  const telegramConfigured = isSecretConfigured(
                    configuredSecrets,
                    "telegram_bot_token",
                    "telegram_chat_id",
                  );
                  const telegramDraft = hasSecretDraft(config, "telegram_bot_token", "telegram_chat_id");
                  return (
                    <div className="rounded-xl border bg-muted/20 p-3">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant={telegramConfigured ? "default" : "outline"}>
                              {telegramConfigured ? "Telegram configurado" : "Telegram pendente"}
                            </Badge>
                            {telegramDraft ? <Badge variant="secondary">edicao em andamento</Badge> : null}
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {credentialStatusText(telegramConfigured, telegramDraft, "Credenciais do Telegram")}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={handleSave}
                            disabled={saving || !telegramDraft}
                            className="gap-2"
                          >
                            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                            Salvar credenciais
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setEditingSecrets((current) => {
                                const nextEditing = !(current.telegram_bot_token || current.telegram_chat_id);
                                return {
                                  ...current,
                                  telegram_bot_token: nextEditing,
                                  telegram_chat_id: nextEditing,
                                };
                              })
                            }
                          >
                            {editingSecrets.telegram_bot_token || editingSecrets.telegram_chat_id
                              ? "Cancelar edicao"
                              : "Editar credenciais"}
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })()}
                <CredentialField
                  label="Bot token"
                  placeholder={
                    configuredSecrets.telegram_bot_token && !editingSecrets.telegram_bot_token
                      ? "Credencial ja cadastrada"
                      : "Preencha para cadastrar ou atualizar"
                  }
                  value={config.telegram_bot_token}
                  show={!!showSecrets.telegram_bot_token}
                  onToggle={() => toggleShow("telegram_bot_token")}
                  onChange={(value) => setConfig({ ...config, telegram_bot_token: value })}
                  configured={!!configuredSecrets.telegram_bot_token}
                  editing={!!editingSecrets.telegram_bot_token || config.telegram_bot_token.length > 0}
                  onEditToggle={() => toggleSecretEditing("telegram_bot_token")}
                />
                <CredentialField
                  label="Chat ID"
                  placeholder={
                    configuredSecrets.telegram_chat_id && !editingSecrets.telegram_chat_id
                      ? "Credencial ja cadastrada"
                      : "Preencha para cadastrar ou atualizar"
                  }
                  value={config.telegram_chat_id}
                  show={!!showSecrets.telegram_chat_id}
                  onToggle={() => toggleShow("telegram_chat_id")}
                  onChange={(value) => setConfig({ ...config, telegram_chat_id: value })}
                  configured={!!configuredSecrets.telegram_chat_id}
                  editing={!!editingSecrets.telegram_chat_id || config.telegram_chat_id.length > 0}
                  onEditToggle={() => toggleSecretEditing("telegram_chat_id")}
                />
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <Button type="button" variant="outline" onClick={handleTelegramTest} disabled={telegramTesting} className="gap-2">
                  {telegramTesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
                  Enviar mensagem de teste
                </Button>
                <p className="text-xs text-muted-foreground">
                  Usa os valores preenchidos acima ou, se estiverem em branco, as credenciais já salvas no workspace.
                </p>
              </div>

              {telegramTestFeedback ? (
                <div
                  className={cn(
                    "rounded-lg border p-3 text-sm",
                    telegramTestFeedback.kind === "success"
                      ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300"
                      : "border-red-500/20 bg-red-500/5 text-red-600 dark:text-red-300",
                  )}
                >
                  {telegramTestFeedback.message}
                </div>
              ) : null}

              <div className="flex items-start gap-2 rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
                <p className="text-xs text-muted-foreground">
                  Campos em branco preservam os valores já armazenados no backend.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Chaves das exchanges</CardTitle>
              <CardDescription>
                Para leitura de mercado, as APIs públicas continuam suficientes. Preencha somente se quiser atualizar credenciais salvas ou validar permissões reais de conta.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {EXCHANGE_CRED_FIELDS.map(({ exchange, label, keyField, secretField }) => {
                const exchangeConfigured = isSecretConfigured(configuredSecrets, keyField, secretField);
                const exchangeDraft = hasSecretDraft(config, keyField, secretField);
                return (
                <div key={exchange} className="space-y-3">
                  <div className="rounded-xl border bg-muted/20 p-3">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-sm font-semibold text-muted-foreground">{label}</p>
                          <Badge variant={exchangeConfigured ? "default" : "outline"}>
                            {exchangeConfigured ? "credenciais salvas" : "sem credenciais"}
                          </Badge>
                          {exchangeDraft ? <Badge variant="secondary">edicao em andamento</Badge> : null}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {credentialStatusText(exchangeConfigured, exchangeDraft, `Credenciais da ${label}`)}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleSave}
                          disabled={saving || !exchangeDraft}
                          className="gap-2"
                        >
                          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                          Salvar chaves
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setEditingSecrets((current) => {
                              const nextEditing = !(current[keyField] || current[secretField]);
                              return {
                                ...current,
                                [keyField]: nextEditing,
                                [secretField]: nextEditing,
                              };
                            })
                          }
                        >
                          {editingSecrets[keyField] || editingSecrets[secretField] ? "Cancelar edicao" : "Editar"}
                        </Button>
                      </div>
                    </div>
                  </div>
                  <CredentialField
                    label="API key"
                    placeholder={
                      configuredSecrets[keyField] && !editingSecrets[keyField]
                        ? "Credencial ja cadastrada"
                        : "Preencha para cadastrar ou atualizar"
                    }
                    value={config[keyField]}
                    show={!!showSecrets[keyField]}
                    onToggle={() => toggleShow(keyField)}
                    onChange={(value) => setConfig({ ...config, [keyField]: value })}
                    configured={!!configuredSecrets[keyField]}
                    editing={!!editingSecrets[keyField] || config[keyField].length > 0}
                    onEditToggle={() => toggleSecretEditing(keyField)}
                  />
                  <CredentialField
                    label="API secret"
                    placeholder={
                      configuredSecrets[secretField] && !editingSecrets[secretField]
                        ? "Credencial ja cadastrada"
                        : "Preencha para cadastrar ou atualizar"
                    }
                    value={config[secretField]}
                    show={!!showSecrets[secretField]}
                    onToggle={() => toggleShow(secretField)}
                    onChange={(value) => setConfig({ ...config, [secretField]: value })}
                    configured={!!configuredSecrets[secretField]}
                    editing={!!editingSecrets[secretField] || config[secretField].length > 0}
                    onEditToggle={() => toggleSecretEditing(secretField)}
                  />
                  {exchange !== "binance" ? <Separator /> : null}
                </div>
                );
              })}

              <div className="flex flex-col gap-3 rounded-xl border bg-muted/20 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold">Validar acesso das exchanges</p>
                  <p className="text-xs text-muted-foreground">
                    Usa os valores digitados agora ou, se estiverem em branco, as credenciais persistidas no backend.
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void handleValidateExchangeCredentials()}
                  disabled={validatingCredentials}
                  className="gap-2"
                >
                  {validatingCredentials ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
                  Validar credenciais
                </Button>
              </div>

              {credentialValidationResults.length > 0 ? (
                <div className="space-y-3">
                  {credentialValidationResults.map((result) => (
                    <div key={result.exchange} className="rounded-xl border p-4">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-semibold">{formatExchangeLabel(result.exchange)}</p>
                            <Badge variant={validationBadgeVariant(result.state)}>{formatValidationStatus(result.state)}</Badge>
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground">{result.message}</p>
                        </div>
                        {typeof result.can_trade === "boolean" ? (
                          <Badge variant={result.can_trade ? "default" : "outline"}>
                            {result.can_trade ? "trade habilitado" : "sem trade"}
                          </Badge>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Auditoria recente</CardTitle>
              <CardDescription>
                Últimos eventos administrativos registrados para o workspace ativo.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded-xl border bg-muted/20 p-4">
                <div className="space-y-1">
                  <p className="text-sm font-semibold">Diagnosticar sinal perdido</p>
                  <p className="text-xs text-muted-foreground">
                    Use quando um ativo mexeu e o sistema nao avisou. A busca mostra se o par foi coletado, descartado, ranqueado, bloqueado ou alertado.
                  </p>
                </div>

                <div className="mt-4 grid gap-3 lg:grid-cols-[180px,minmax(0,1fr),150px,auto] lg:items-end">
                  <div className="space-y-1">
                    <span className="text-xs font-medium text-muted-foreground">Exchange</span>
                    <select
                      value={missedSignalExchange}
                      onChange={(event) => setMissedSignalExchange(event.target.value as Exchange)}
                      className="h-9 w-full rounded-lg border bg-background px-3 text-sm"
                    >
                      {ALL_EXCHANGES.map(({ id, label }) => (
                        <option key={id} value={id}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-medium text-muted-foreground">Par</span>
                    <Input
                      value={missedSignalPairInput}
                      onChange={(event) => {
                        setMissedSignalPairInput(event.target.value);
                        setMissedSignalError(null);
                      }}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          void diagnoseMissedSignal();
                        }
                      }}
                      placeholder="Ex: SOL_BRL, WBTC_BRL"
                    />
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-medium text-muted-foreground">Janela</span>
                    <select
                      value={missedSignalWindowHours}
                      onChange={(event) => setMissedSignalWindowHours(event.target.value as MissedSignalWindow)}
                      className="h-9 w-full rounded-lg border bg-background px-3 text-sm"
                    >
                      <option value="1">Ultima 1h</option>
                      <option value="4">Ultimas 4h</option>
                      <option value="24">Ultimas 24h</option>
                      <option value="72">Ultimos 3 dias</option>
                      <option value="custom">Periodo customizado</option>
                    </select>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void diagnoseMissedSignal()}
                    disabled={missedSignalLoading}
                    className="gap-2"
                  >
                    {missedSignalLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Info className="h-3.5 w-3.5" />}
                    Investigar
                  </Button>
                </div>

                {missedSignalWindowHours === "custom" ? (
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    <div className="space-y-1">
                      <span className="text-xs font-medium text-muted-foreground">Inicio</span>
                      <Input
                        type="datetime-local"
                        value={missedSignalCustomFrom}
                        onChange={(event) => setMissedSignalCustomFrom(event.target.value)}
                      />
                    </div>
                    <div className="space-y-1">
                      <span className="text-xs font-medium text-muted-foreground">Fim</span>
                      <Input
                        type="datetime-local"
                        value={missedSignalCustomTo}
                        onChange={(event) => setMissedSignalCustomTo(event.target.value)}
                      />
                    </div>
                  </div>
                ) : null}

                {missedSignalError ? (
                  <p className="mt-3 text-xs text-amber-600 dark:text-amber-300">{missedSignalError}</p>
                ) : null}

                {missedSignalDiagnostic ? (
                  <div className="mt-4 space-y-3">
                    <div
                      className={cn(
                        "rounded-lg border p-3 text-xs",
                        missedSignalDiagnostic.status === "events_found"
                          ? "border-emerald-500/20 bg-emerald-500/5"
                          : "border-amber-500/20 bg-amber-500/5",
                      )}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold">
                            {missedSignalDiagnostic.pair.replace("_", "/")} em {formatExchangeDisplay(missedSignalDiagnostic.exchange)}
                          </p>
                          <p className="mt-1 text-muted-foreground">{missedSignalDiagnostic.message}</p>
                        </div>
                        <Badge variant={missedSignalDiagnostic.status === "events_found" ? "default" : "outline"}>
                          {missedSignalDiagnostic.status === "events_found" ? "eventos encontrados" : "sem trilha"}
                        </Badge>
                      </div>
                    </div>

                    <div className="grid gap-2 md:grid-cols-3">
                      <div className="rounded-lg border bg-background p-3 text-xs">
                        <p className="font-semibold">Conclusao</p>
                        <p className="mt-1 text-muted-foreground">{formatMissedSignalFinalState(missedSignalDiagnostic.final_state)}</p>
                        {missedSignalDiagnostic.root_cause_reason ? (
                          <p className="mt-2 text-muted-foreground">
                            Causa: {formatPipelineReason(missedSignalDiagnostic.root_cause_reason)}
                          </p>
                        ) : null}
                      </div>
                      <div className="rounded-lg border bg-background p-3 text-xs">
                        <p className="font-semibold">Workspace</p>
                        {missedSignalDiagnostic.workspace_status ? (
                          <div className="mt-1 space-y-1 text-muted-foreground">
                            <p>Exchange: {missedSignalDiagnostic.workspace_status.exchange_enabled ? "habilitada" : "bloqueada"}</p>
                            <p>Par: {missedSignalDiagnostic.workspace_status.pair_selected ? "na watchlist" : "fora da watchlist, mas elegivel pelo catalogo"}</p>
                            <p>Telegram: {missedSignalDiagnostic.workspace_status.telegram_enabled ? "ativo" : "desativado"}</p>
                            <p>Ultimo alerta: {formatPipelineReason(missedSignalDiagnostic.workspace_status.latest_alert_reason)}</p>
                          </div>
                        ) : (
                          <p className="mt-1 text-muted-foreground">Sem contexto de workspace.</p>
                        )}
                      </div>
                      <div className="rounded-lg border bg-background p-3 text-xs">
                        <p className="font-semibold">Catalogo da exchange</p>
                        {missedSignalDiagnostic.catalog_status ? (
                          <div className="mt-1 space-y-1 text-muted-foreground">
                            <p>Status: {formatCatalogStatus(missedSignalDiagnostic.catalog_status.overall_status)}</p>
                            <p>Monitoravel: {missedSignalDiagnostic.catalog_status.monitorable === false ? "nao" : "sim/indeterminado"}</p>
                            <p>Motivo: {formatPipelineReason(missedSignalDiagnostic.catalog_status.monitorability_reason)}</p>
                            <p>Existe: {missedSignalDiagnostic.catalog_status.exists_in_catalog === false ? "nao" : "sim/indeterminado"}</p>
                            {missedSignalDiagnostic.catalog_status.error ? <p>Erro: {missedSignalDiagnostic.catalog_status.error}</p> : null}
                          </div>
                        ) : (
                          <p className="mt-1 text-muted-foreground">Catalogo nao consultado.</p>
                        )}
                      </div>
                    </div>

                    {missedSignalDiagnostic.cycle_summaries.length > 0 ? (
                      <div className="grid gap-2 md:grid-cols-2">
                        {missedSignalDiagnostic.cycle_summaries.slice(0, 4).map((cycle) => (
                          <div key={cycle.cycle_id} className="rounded-lg border bg-background p-3 text-xs">
                            <div className="flex items-center justify-between gap-2">
                              <p className="font-semibold">{cycle.cycle_id}</p>
                              <Badge variant={cycle.status === "completed" ? "default" : "outline"}>{cycle.status}</Badge>
                            </div>
                            <div className="mt-2 grid grid-cols-2 gap-2 text-muted-foreground">
                              <span>Pares BRL: {cycle.brl_pairs}</span>
                              <span>Candidatos: {cycle.light_candidates}</span>
                              <span>Deep scan: {cycle.deep_completed}/{cycle.deep_candidates}</span>
                              <span>Alertas: {cycle.alerts_sent}/{cycle.alerts_created}</span>
                            </div>
                            {Object.keys(cycle.discard_reasons).length > 0 ? (
                              <p className="mt-2 text-muted-foreground">
                                Descartes: {formatReasonCounts(cycle.discard_reasons)}
                              </p>
                            ) : null}
                            {Object.keys(cycle.block_reasons).length > 0 ? (
                              <p className="mt-1 text-muted-foreground">
                                Bloqueios: {formatReasonCounts(cycle.block_reasons)}
                              </p>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    ) : null}

                    {missedSignalDiagnostic.timeline.length > 0 ? (
                      <div className="overflow-hidden rounded-xl border">
                        <ScrollArea className="max-h-80">
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
                              {missedSignalDiagnostic.timeline.map((event, index) => (
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
                                  <TableCell className="max-w-[18rem] truncate text-xs text-muted-foreground">
                                    {formatEventDetails(event.details)}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </ScrollArea>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>

              {visibleAuditLog.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nenhum evento registrado ainda.</p>
              ) : (
                visibleAuditLog.map((entry) => (
                  <AuditLogEntryCard key={entry.id} entry={entry} />
                ))
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}

function SettingRow({
  label,
  description,
  children,
}: {
  label: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <p className="text-sm font-semibold">{label}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      {children}
    </div>
  );
}

function SliderInputControl({
  value,
  min,
  max,
  step,
  suffix,
  testId,
  onChange,
}: {
  value: number;
  min: number;
  max: number;
  step: number;
  suffix?: string;
  testId?: string;
  onChange: (value: number) => void;
}) {
  return (
    <div data-testid={testId} className="flex w-full max-w-[22rem] items-center gap-3 self-start">
      <Slider
        value={[value]}
        min={min}
        max={max}
        step={step}
        className="min-w-0 flex-1"
        onValueChange={(nextValues) => {
          const nextValue = Array.isArray(nextValues) ? nextValues[0] : nextValues;
          onChange(nextValue);
        }}
      />
      <div className="flex w-28 items-center gap-2">
        <Input
          type="number"
          min={min}
          max={max}
          step={step}
          inputMode="decimal"
          value={value}
          onChange={(event) => {
            const nextValue = clampNumericValue(parseNumericValue(event.target.value, value), min, max);
            onChange(nextValue);
          }}
          className="h-9 w-20 text-right font-medium tabular-nums"
        />
        {suffix ? <span className="text-sm font-semibold text-muted-foreground">{suffix}</span> : null}
      </div>
    </div>
  );
}

function CredentialField({
  label,
  placeholder,
  value,
  show,
  onToggle,
  onChange,
  configured = false,
  editing = true,
  onEditToggle,
}: {
  label: string;
  placeholder: string;
  value: string;
  show: boolean;
  onToggle: () => void;
  onChange: (value: string) => void;
  configured?: boolean;
  editing?: boolean;
  onEditToggle?: () => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-24 shrink-0 text-xs font-medium text-muted-foreground">{label}</span>
      <div className="relative flex-1">
        <Input
          type={show ? "text" : "password"}
          placeholder={placeholder}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="pr-20 font-mono text-sm"
          autoComplete="off"
          disabled={configured && !editing && value === ""}
        />
        <div className="absolute right-2.5 top-1/2 flex -translate-y-1/2 items-center gap-1">
          {configured && !editing && value === "" && onEditToggle ? (
            <button
              type="button"
              onClick={onEditToggle}
              className="text-[11px] font-medium text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
              tabIndex={-1}
            >
              editar
            </button>
          ) : null}
          <button
            type="button"
            onClick={onToggle}
            className="text-muted-foreground hover:text-foreground"
            tabIndex={-1}
          >
            {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}

function formatExchangeLabel(exchange: ExchangeCredentialValidationResult["exchange"]) {
  return EXCHANGE_CRED_FIELDS.find((item) => item.exchange === exchange)?.label ?? exchange;
}

function formatExchangeDisplay(exchange: Exchange | string | null | undefined) {
  return ALL_EXCHANGES.find((item) => item.id === exchange)?.label ?? exchange ?? "-";
}

function formatReasonCounts(reasons: Record<string, number>): string {
  return Object.entries(reasons)
    .slice(0, 4)
    .map(([reason, count]) => `${formatPipelineReason(reason)} (${count})`)
    .join(", ");
}

function formatPipelineStage(stage: string): string {
  const labels: Record<string, string> = {
    light_scan: "Scan leve",
    promotion: "Promocao",
    deep_scan: "Analise profunda",
    ranking: "Ranking",
    workspace_projection: "Workspace",
    alert: "Alerta",
  };
  return labels[stage] ?? stage;
}

function formatPipelineStatus(status: string): string {
  const labels: Record<string, string> = {
    candidate: "candidato",
    promoted: "promovido",
    discarded: "descartado",
    blocked: "bloqueado",
    ranked: "ranqueado",
    opportunity: "sinal",
    visible: "visivel",
    sent: "enviado",
    error: "erro",
  };
  return labels[status] ?? status;
}

function formatPipelineReason(reason?: string | null): string {
  if (!reason) return "-";
  const labels: Record<string, string> = {
    below_alert_threshold: "abaixo do limite de alerta",
    below_min_executability: "executabilidade abaixo do minimo",
    candidate: "candidato",
    candidate_limit_lower_priority: "prioridade menor no limite de candidatos",
    config_match: "passou nos filtros do workspace",
    cooldown_active: "cooldown ativo",
    entered_cycle_ranking: "entrou no ranking do ciclo",
    exchange_disabled: "exchange desabilitada no workspace",
    exchange_not_in_alert_scope: "exchange fora do alerta",
    insufficient_liquidity: "liquidez insuficiente",
    insufficient_movement: "movimento insuficiente",
    insufficient_volume: "volume insuficiente",
    lower_than_competing_signals: "ficou fora do top 5",
    missing_candles: "candles ausentes",
    missing_order_book: "book ausente",
    missing_ticker: "ticker ausente",
    movement_type_not_supported: "tipo de movimento nao suportado",
    cache_empty: "catalogo vazio",
    cache_stale: "catalogo desatualizado",
    daily_alert_limit_reached: "limite diario de alertas atingido",
    not_brl_pair: "par nao BRL",
    pair_inactive: "par inativo",
    not_operable_for_alert_scope: "nao operavel para alerta",
    opportunity_type_not_alertable: "tipo de oportunidade nao alertavel",
    pair_not_enabled: "par fora da lista do workspace",
    pair_not_in_catalog: "par fora do catalogo",
    pair_not_in_alert_scope: "par fora do alerta",
    pair_not_tradable: "par nao negociavel",
    selected_for_deep_scan: "selecionado para analise profunda",
    spread_above_threshold: "spread acima do limite",
    spread_unfavorable: "spread desfavoravel",
    telegram_sent: "Telegram enviado",
    telegram_disabled: "Telegram desativado",
    telegram_not_configured: "Telegram nao configurado",
    volume_below_minimum: "volume abaixo do minimo",
    volatility_below_threshold: "volatilidade abaixo do limite",
    workspace_alert_scope_mismatch: "fora do escopo de alerta",
  };
  return labels[reason] ?? reason.replaceAll("_", " ");
}

function formatMissedSignalFinalState(state: string): string {
  const labels: Record<string, string> = {
    alerted: "Alerta enviado.",
    alert_blocked: "Sinal chegou ao alerta, mas foi bloqueado.",
    audited_without_terminal_decision: "Houve auditoria, mas sem decisao final clara.",
    discarded_before_alert: "Sinal descartado antes de virar alerta.",
    insufficient_audit_data: "Sem trilha auditavel no periodo.",
    not_monitorable: "Par nao monitoravel no periodo.",
    not_visible_for_workspace: "Sinal nao ficou visivel para este workspace.",
    provider_error: "Falha ou dado incompleto na exchange.",
    technical_signal_created: "Sinal tecnico criado, sem alerta registrado.",
    visible_not_alerted: "Sinal visivel, mas nao alertado.",
  };
  return labels[state] ?? state.replaceAll("_", " ");
}

function formatCatalogStatus(status?: string | null): string {
  if (!status) return "indeterminado";
  const labels: Record<string, string> = {
    ok: "ok",
    warning: "atencao",
    error: "erro",
  };
  return labels[status] ?? status;
}

function formatEventDetails(details: Record<string, unknown>): string {
  const compactEntries = Object.entries(details)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .slice(0, 4);

  if (!compactEntries.length) return "-";

  return compactEntries
    .map(([key, value]) => `${key.replaceAll("_", " ")}: ${typeof value === "number" ? Number(value.toFixed(4)) : String(value)}`)
    .join(" · ");
}

function isSecretConfigured(
  configuredSecrets: Record<string, boolean>,
  ...fields: SensitiveField[]
): boolean {
  return fields.some((field) => configuredSecrets[field]);
}

function hasSecretDraft(config: AppConfig, ...fields: SensitiveField[]): boolean {
  return fields.some((field) => Boolean(config[field]));
}

function credentialStatusText(configured: boolean, hasDraft: boolean, configuredLabel: string): string {
  if (hasDraft) {
    return "Alterações pendentes. Clique em salvar para gravar no workspace.";
  }
  if (configured) {
    return `${configuredLabel} salvas no workspace.`;
  }
  return "Nenhuma credencial salva ainda.";
}

function formatValidationStatus(status: ExchangeCredentialValidationResult["state"]) {
  switch (status) {
    case "valid":
      return "válida";
    case "invalid":
      return "inválida";
    case "missing":
      return "ausente";
    case "no_trading_permission":
      return "sem permissão de trade";
    default:
      return "erro";
  }
}

function validationBadgeVariant(
  status: ExchangeCredentialValidationResult["state"],
): "default" | "secondary" | "outline" | "destructive" {
  switch (status) {
    case "valid":
      return "default";
    case "missing":
      return "outline";
    case "no_trading_permission":
      return "secondary";
    default:
      return "destructive";
  }
}

function MetaCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-muted/50 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-sm font-semibold">{value}</p>
    </div>
  );
}

const AUDIT_ACTION_LABELS: Record<string, string> = {
  "auth.login": "Login realizado",
  "auth.logout": "Logout realizado",
  "auth.password_changed": "Senha alterada",
  "user.created": "Usuário criado",
  "user.activated": "Usuário ativado",
  "user.deactivated": "Usuário desativado",
  "user.password_reset": "Senha redefinida",
  "user.onboarding_completed": "Onboarding concluído",
  "invite.created": "Convite criado",
  "workspace.config_updated": "Configuração atualizada",
  "workspace.created": "Workspace criado",
  "workspace.exchange_credentials_validated": "Credenciais validadas",
};

function formatAuditStatus(status: string) {
  return status === "success" ? "sucesso" : status;
}

function formatAuditTimestamp(entry: DisplayAuditLogEntry) {
  const newest = new Date(entry.created_at).toLocaleString("pt-BR");
  if (!entry.groupedOldestCreatedAt) {
    return newest;
  }

  const oldest = new Date(entry.groupedOldestCreatedAt).toLocaleString("pt-BR");
  return `${oldest} até ${newest}`;
}

function formatConfigUpdateSummary(entry: DisplayAuditLogEntry) {
  const updatedFields = extractUpdatedFields(entry.details);
  if (updatedFields.length === 0) {
    return null;
  }

  return updatedFields
    .map((field) => CONFIG_UPDATE_FIELD_LABELS[field] ?? field)
    .join(", ");
}

function AuditLogEntryCard({ entry }: { entry: DisplayAuditLogEntry }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = Object.keys(entry.details ?? {}).length > 0;
  const label = AUDIT_ACTION_LABELS[entry.action] ?? entry.action;
  const configUpdateSummary =
    entry.action === "workspace.config_updated" ? formatConfigUpdateSummary(entry) : null;
  const showDetailsToggle = hasDetails && !configUpdateSummary;

  return (
    <div className="rounded-xl border p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="truncate text-sm font-semibold">{label}</p>
            {entry.aggregatedCount > 1 ? (
              <Badge variant="secondary">{entry.aggregatedCount} alterações</Badge>
            ) : null}
          </div>
          <p className="text-xs text-muted-foreground">
            {entry.actor_username ?? "sistema"} • {formatAuditTimestamp(entry)}
          </p>
          {configUpdateSummary ? (
            <p className="mt-1 text-xs text-muted-foreground">Campos: {configUpdateSummary}</p>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge variant={entry.status === "success" ? "default" : "destructive"}>
            {formatAuditStatus(entry.status)}
          </Badge>
          {showDetailsToggle ? (
            <button
              type="button"
              onClick={() => setExpanded((current) => !current)}
              className="text-xs text-muted-foreground underline-offset-2 hover:underline"
            >
              {expanded ? "ocultar" : "detalhes"}
            </button>
          ) : null}
        </div>
      </div>
      {expanded && showDetailsToggle ? (
        <pre className="mt-2 overflow-x-auto rounded-lg bg-muted/60 p-2 text-[11px]">
          {JSON.stringify(entry.details, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}
