"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import {
  adminLogin,
  AUTH_TOKEN_STORAGE_KEY,
  ACTIVE_WORKSPACE_STORAGE_KEY,
  changeAdminPassword,
  createWorkspace,
  getAdminAuditLog,
  getAdminSession,
  getWorkspaces,
  getConfig,
  getStoredWorkspaceId,
  setStoredAuthToken,
  setStoredWorkspaceId,
  updateConfig,
} from "@/lib/api";
import type { AdminSessionInfo, AppConfig, AuditLogEntry, Exchange, WorkspaceSummary } from "@/lib/types";
import { Check, Eye, EyeOff, FolderPlus, Info, KeyRound, Loader2, Lock, LogOut, Save, ShieldCheck } from "lucide-react";

const ALL_EXCHANGES: { id: Exchange; label: string }[] = [
  { id: "novadax", label: "NovaDAX" },
  { id: "mercado_bitcoin", label: "Mercado Bitcoin" },
  { id: "binance", label: "Binance" },
];

const ALL_PAIRS = [
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
  const [activeWorkspaceId, setActiveWorkspaceId] = useState("");
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);

  useEffect(() => {
    void (async () => {
      const storedToken = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || "";
      setAdminToken(storedToken);
      setActiveWorkspaceId(getStoredWorkspaceId());

      if (!storedToken) {
        setLoading(false);
        return;
      }

      try {
        const [data, session, audit] = await Promise.all([
          getConfig(storedToken),
          getAdminSession(storedToken),
          getAdminAuditLog(12, storedToken),
        ]);
        setConfig(data);
        setAdminSession(session);
        setAuditLog(audit);
        setAuthError(null);
      } catch (error) {
        setConfig(null);
        setAdminSession(null);
        setAuditLog([]);
        setAuthError(error instanceof Error ? error.message : "Falha ao autenticar");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function loadAdminContext(token: string): Promise<void> {
      const [session, audit, availableWorkspaces] = await Promise.all([
        getAdminSession(token),
        getAdminAuditLog(12, token),
        getWorkspaces(token),
      ]);
      const nextWorkspaceId =
        getStoredWorkspaceId() ||
        availableWorkspaces[0]?.id ||
        "";
      if (nextWorkspaceId) {
        setStoredWorkspaceId(nextWorkspaceId);
        setActiveWorkspaceId(nextWorkspaceId);
      }
      setAdminSession(session);
      setAuditLog(audit);
      setWorkspaces(availableWorkspaces);
    }

  async function loadConfig(token: string): Promise<boolean> {
    try {
      const [data] = await Promise.all([getConfig(token), loadAdminContext(token)]);
      setConfig(data);
      setAuthError(null);
      return true;
    } catch (error) {
      setConfig(null);
      setAdminSession(null);
      setAuditLog([]);
      setWorkspaces([]);
      setAuthError(error instanceof Error ? error.message : "Falha ao autenticar");
      return false;
    }
  }

  function clearSession() {
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
    setAdminToken("");
    setConfig(null);
    setAdminSession(null);
    setAuditLog([]);
    setWorkspaces([]);
    setActiveWorkspaceId("");
    setAuthError(null);
    setPassword("");
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
  }

  async function handleUnlock() {
    if (!adminToken) {
      setAuthError("Informe o token administrativo.");
      return;
    }

    setLoading(true);
    const ok = await loadConfig(adminToken);
    if (ok) {
      setStoredAuthToken(adminToken);
    }
    setLoading(false);
  }

  async function handleCredentialLogin() {
    if (!username || !password) {
      setAuthError("Informe usuario e senha administrativos.");
      return;
    }

    setLoading(true);
    try {
      const session = await adminLogin(username, password);
      setAdminToken(session.access_token);
      setStoredAuthToken(session.access_token);
      const nextWorkspaceId = session.session.workspaces[0]?.id || "";
      if (nextWorkspaceId) {
        setStoredWorkspaceId(nextWorkspaceId);
        setActiveWorkspaceId(nextWorkspaceId);
      }
      const ok = await loadConfig(session.access_token);
      if (!ok) {
        window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
        window.localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao autenticar");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!config) return;

    setSaving(true);
    try {
      const updated = await updateConfig(config, adminToken);
      setConfig(updated);
      setAuthError(null);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2000);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao salvar configuracao");
    } finally {
      setSaving(false);
    }
  }

  async function handleChangePassword() {
    if (!adminToken) {
      setAuthError("Sessao administrativa ausente.");
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
      setAuthError("A confirmacao da nova senha nao confere.");
      return;
    }

    setPasswordSaving(true);
    try {
      const response = await changeAdminPassword(currentPassword, newPassword, adminToken);
      setAdminToken(response.access_token);
      setStoredAuthToken(response.access_token);
      setAdminSession(response.session);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      await loadConfig(response.access_token);
      setAuthError(null);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao trocar senha");
    } finally {
      setPasswordSaving(false);
    }
  }

  async function handleCreateWorkspace() {
    if (!adminToken || !newWorkspaceName.trim()) return;

    setCreatingWorkspace(true);
    try {
      const createdWorkspace = await createWorkspace(newWorkspaceName.trim(), adminToken);
      const nextWorkspaces = await getWorkspaces(adminToken);
      setWorkspaces(nextWorkspaces);
      setStoredWorkspaceId(createdWorkspace.id);
      setActiveWorkspaceId(createdWorkspace.id);
      setNewWorkspaceName("");
      await loadConfig(adminToken);
      setAuthError(null);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Falha ao criar workspace");
    } finally {
      setCreatingWorkspace(false);
    }
  }

  async function handleWorkspaceChange(workspaceId: string) {
    setStoredWorkspaceId(workspaceId);
    setActiveWorkspaceId(workspaceId);
    if (adminToken) {
      setLoading(true);
      await loadConfig(adminToken);
      setLoading(false);
    }
  }

  function toggleExchange(exchange: Exchange) {
    if (!config) return;
    const exchanges = config.enabled_exchanges.includes(exchange)
      ? config.enabled_exchanges.filter((item) => item !== exchange)
      : [...config.enabled_exchanges, exchange];
    setConfig({ ...config, enabled_exchanges: exchanges });
  }

  function togglePair(pair: string) {
    if (!config) return;
    const pairs = config.enabled_pairs.includes(pair)
      ? config.enabled_pairs.filter((item) => item !== pair)
      : [...config.enabled_pairs, pair];
    setConfig({ ...config, enabled_pairs: pairs });
  }

  function toggleShow(field: string) {
    setShowSecrets((prev) => ({ ...prev, [field]: !prev[field] }));
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!config) {
    return (
      <div className="mx-auto max-w-xl space-y-6 p-4 pt-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <Lock className="h-4 w-4" />
              Acesso administrativo
            </CardTitle>
            <CardDescription>
              Esta area exige uma sessao administrativa via credenciais ou o fallback legado com `ADMIN_TOKEN`.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <Input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Usuario admin"
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
              <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-500">
                {authError}
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-4 pt-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Configuracoes</h1>
          <p className="text-sm text-muted-foreground">
            Ajuste parametros operacionais sem expor segredos na interface.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={clearSession} className="gap-2">
            <LogOut className="h-4 w-4" />
            Sair
          </Button>
          <Button onClick={handleSave} disabled={saving} className="gap-2">
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : saved ? (
              <Check className="h-4 w-4" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {saved ? "Salvo" : "Salvar"}
          </Button>
        </div>
      </div>

      {authError ? (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-500">
          {authError}
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base font-semibold">
            <ShieldCheck className="h-4 w-4" />
            Sessao administrativa
          </CardTitle>
          <CardDescription>
            Camada atual preparada para um unico operador com auditoria e revogacao por versao de token.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetaCard label="Usuario" value={adminSession?.username ?? "-"} />
          <MetaCard label="Modo" value={adminSession?.auth_mode ?? "-"} />
          <MetaCard label="Role" value={adminSession?.role ?? "-"} />
          <MetaCard
            label="Ultima troca"
            value={
              adminSession?.password_last_changed_at
                ? new Date(adminSession.password_last_changed_at).toLocaleString("pt-BR")
                : "Nao registrada"
            }
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Workspace ativo</CardTitle>
          <CardDescription>
            Cada workspace tem configuracao, preferencias e trilha de auditoria isoladas.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {workspaces.map((workspace) => (
              <Badge
                key={workspace.id}
                variant={workspace.id === activeWorkspaceId ? "default" : "outline"}
                className="cursor-pointer select-none"
                onClick={() => handleWorkspaceChange(workspace.id)}
              >
                {workspace.name}
              </Badge>
            ))}
          </div>
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Seguranca</CardTitle>
          <CardDescription>
            Troque a senha administrativa para revogar tokens anteriores e mover o acesso para hash persistido no banco.
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

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Filtros e thresholds</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <SettingRow
            label="Volatilidade minima (%)"
            description="Variacao percentual minima para considerar um sinal"
          >
            <div className="flex items-center gap-3">
              <Slider
                value={[config.thresholds.min_volatility_pct]}
                min={0.5}
                max={10}
                step={0.5}
                className="w-48"
                onValueChange={(value) => {
                  const nextValue = Array.isArray(value) ? value[0] : value;
                  setConfig({
                    ...config,
                    thresholds: { ...config.thresholds, min_volatility_pct: nextValue },
                  });
                }}
              />
              <span className="w-12 text-right text-sm font-semibold tabular-nums">
                {config.thresholds.min_volatility_pct}%
              </span>
            </div>
          </SettingRow>

          <Separator />

          <SettingRow
            label="Volume minimo (grandes)"
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
            label="Volume minimo (altcoins)"
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
            label="Liquidez minima (unidades)"
            description="Quantidade minima no livro de ordens"
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
            label="Spread maximo (%)"
            description="Spread maximo entre compra e venda"
          >
            <div className="flex items-center gap-3">
              <Slider
                value={[config.thresholds.max_spread_pct]}
                min={0.1}
                max={5}
                step={0.1}
                className="w-48"
                onValueChange={(value) => {
                  const nextValue = Array.isArray(value) ? value[0] : value;
                  setConfig({
                    ...config,
                    thresholds: { ...config.thresholds, max_spread_pct: nextValue },
                  });
                }}
              />
              <span className="w-12 text-right text-sm font-semibold tabular-nums">
                {config.thresholds.max_spread_pct.toFixed(1)}%
              </span>
            </div>
          </SettingRow>
        </CardContent>
      </Card>

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
                repetition: "Repeticao",
              };

              return (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-sm font-medium">{labels[key]}</span>
                  <div className="flex items-center gap-3">
                    <Slider
                      value={[config.weights[key] * 100]}
                      min={0}
                      max={50}
                      step={5}
                      className="w-48"
                      onValueChange={(value) => {
                        const nextValue = Array.isArray(value) ? value[0] : value;
                        setConfig({
                          ...config,
                          weights: { ...config.weights, [key]: nextValue / 100 },
                        });
                      }}
                    />
                    <span className="w-12 text-right text-sm font-semibold tabular-nums">
                      {(config.weights[key] * 100).toFixed(0)}%
                    </span>
                  </div>
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
        <CardContent className="space-y-3">
          {ALL_EXCHANGES.map(({ id, label }) => (
            <div key={id} className="flex items-center justify-between">
              <span className="text-sm font-medium">{label}</span>
              <Switch
                checked={config.enabled_exchanges.includes(id)}
                onCheckedChange={() => toggleExchange(id)}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Pares monitorados</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {ALL_PAIRS.map((pair) => {
              const active = config.enabled_pairs.includes(pair);
              return (
                <Badge
                  key={pair}
                  variant={active ? "default" : "outline"}
                  className="cursor-pointer select-none font-semibold"
                  onClick={() => togglePair(pair)}
                >
                  {pair.replace("_", "/")}
                </Badge>
              );
            })}
          </div>
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
          <CardTitle className="text-base font-semibold">Notificacoes Telegram</CardTitle>
          <CardDescription>
            Os valores sensiveis nao sao retornados pela API. Preencha apenas os campos que deseja
            atualizar.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold">Alertas ativos</p>
              <p className="text-xs text-muted-foreground">Enviar notificacoes via bot</p>
            </div>
            <Switch
              checked={config.telegram_enabled}
              onCheckedChange={(value) => setConfig({ ...config, telegram_enabled: value })}
            />
          </div>

          <Separator />

          <div className="space-y-3">
            <CredentialField
              label="Bot token"
              placeholder="Preencha apenas para atualizar"
              value={config.telegram_bot_token}
              show={!!showSecrets.telegram_bot_token}
              onToggle={() => toggleShow("telegram_bot_token")}
              onChange={(value) => setConfig({ ...config, telegram_bot_token: value })}
            />
            <CredentialField
              label="Chat ID"
              placeholder="Preencha apenas para atualizar"
              value={config.telegram_chat_id}
              show={!!showSecrets.telegram_chat_id}
              onToggle={() => toggleShow("telegram_chat_id")}
              onChange={(value) => setConfig({ ...config, telegram_chat_id: value })}
            />
          </div>

          <div className="flex items-start gap-2 rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
            <p className="text-xs text-muted-foreground">
              Campos em branco preservam os valores ja armazenados no backend.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Chaves das exchanges</CardTitle>
          <CardDescription>
            Para leitura de mercado, as APIs publicas continuam suficientes. Preencha somente se
            quiser atualizar credenciais salvas.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {EXCHANGE_CRED_FIELDS.map(({ exchange, label, keyField, secretField }) => (
            <div key={exchange} className="space-y-3">
              <p className="text-sm font-semibold text-muted-foreground">{label}</p>
              <CredentialField
                label="API key"
                placeholder="Preencha apenas para atualizar"
                value={config[keyField]}
                show={!!showSecrets[keyField]}
                onToggle={() => toggleShow(keyField)}
                onChange={(value) => setConfig({ ...config, [keyField]: value })}
              />
              <CredentialField
                label="API secret"
                placeholder="Preencha apenas para atualizar"
                value={config[secretField]}
                show={!!showSecrets[secretField]}
                onToggle={() => toggleShow(secretField)}
                onChange={(value) => setConfig({ ...config, [secretField]: value })}
              />
              {exchange !== "binance" ? <Separator /> : null}
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Auditoria recente</CardTitle>
          <CardDescription>
            Ultimos eventos administrativos registrados pelo backend.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {auditLog.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum evento registrado ainda.</p>
          ) : (
            auditLog.map((entry) => (
              <div key={entry.id} className="rounded-xl border p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold">{entry.action}</p>
                    <p className="text-xs text-muted-foreground">
                      {entry.actor_username ?? "sistema"} • {new Date(entry.created_at).toLocaleString("pt-BR")}
                    </p>
                  </div>
                  <Badge variant={entry.status === "success" ? "default" : "destructive"}>
                    {entry.status}
                  </Badge>
                </div>
                {Object.keys(entry.details ?? {}).length > 0 ? (
                  <pre className="mt-2 overflow-x-auto rounded-lg bg-muted/60 p-2 text-[11px]">
                    {JSON.stringify(entry.details, null, 2)}
                  </pre>
                ) : null}
              </div>
            ))
          )}
        </CardContent>
      </Card>
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
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-semibold">{label}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      {children}
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
}: {
  label: string;
  placeholder: string;
  value: string;
  show: boolean;
  onToggle: () => void;
  onChange: (value: string) => void;
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
          className="pr-9 font-mono text-sm"
          autoComplete="off"
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          tabIndex={-1}
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

function MetaCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-muted/50 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-sm font-semibold">{value}</p>
    </div>
  );
}
